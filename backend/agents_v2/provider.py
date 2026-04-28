"""Provider 抽象层 — 适配多提供商流式调用

支持 Ollama 原生格式 + OpenAI 兼容格式（智谱/DeepSeek/Kimi/通义/OpenAI 等）的流式输出。
复用 core/ai_provider.py 的配置。
"""
import json
import time
from typing import Any, AsyncGenerator, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from core.ai_provider import PROVIDER_CONFIG


async def stream_chat(
    provider: str,
    api_key: str,
    base_url: Optional[str],
    model_name: str,
    messages: list[dict],
    tools: Optional[list[dict]] = None,
    max_tokens: int = 4096,
    timeout: int = 120,
) -> AsyncGenerator[dict, None]:
    """流式 chat 请求，yield 事件字典

    事件类型：
      {"type": "text", "text": "..."}
      {"type": "tool_call", "tool_call": {"name": "...", "arguments": {...}}}
      {"type": "done", "stop_reason": "..."}
      {"type": "error", "error": "..."}
    """
    cfg = PROVIDER_CONFIG.get(provider, {})
    url = (base_url or cfg.get("base_url", "")).rstrip("/")

    if not url:
        yield {"type": "error", "error": "缺少 AI 配置的 base_url"}
        return

    if provider == "ollama":
        async for evt in _stream_ollama(url, model_name, messages, tools, timeout):
            yield evt
    elif provider == "anthropic":
        # Anthropic 使用非流式 fallback（格式不同）
        async for evt in _non_stream_fallback(
            provider, url, api_key, model_name, messages, tools, max_tokens, timeout, cfg
        ):
            yield evt
    else:
        # OpenAI 兼容端点：智谱/DeepSeek/Kimi/通义/OpenAI/openai_compatible 等
        async for evt in _stream_openai_compatible(
            url, api_key, model_name, messages, tools, max_tokens, timeout, cfg
        ):
            yield evt


async def _stream_ollama(
    url: str,
    model_name: str,
    messages: list[dict],
    tools: Optional[list[dict]],
    timeout: int,
) -> AsyncGenerator[dict, None]:
    """Ollama /api/chat 流式调用"""
    full_url = f"{url}/api/chat"
    body: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": True,
    }
    if tools:
        body["tools"] = tools

    req_data = json.dumps(body).encode()
    req = Request(full_url, data=req_data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        resp = urlopen(req, timeout=timeout)
        full_text = ""
        tool_calls_acc: dict[int, dict] = {}  # index -> {name, arguments_str}

        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue

            # 处理文本内容
            msg = chunk.get("message", {})
            content = msg.get("content", "")
            if content:
                full_text += content
                yield {"type": "text", "text": content}

            # 处理 tool calls（ollama 格式）
            tc_list = msg.get("tool_calls", [])
            if tc_list:
                for tc in tc_list:
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    args_str = func.get("arguments", {})
                    if isinstance(args_str, str):
                        try:
                            args = json.loads(args_str)
                        except json.JSONDecodeError:
                            args = {"_raw": args_str}
                    else:
                        args = args_str if isinstance(args_str, dict) else {}
                    tool_call = {"name": name, "arguments": args}
                    if tc.get("id"):
                        tool_call["id"] = tc["id"]
                    yield {"type": "tool_call", "tool_call": tool_call}

            if chunk.get("done", False):
                # 如果没有 tool_call 且没产生文本，给个 done
                if not tool_calls_acc and not full_text:
                    yield {"type": "text", "text": ""}
                yield {"type": "done", "stop_reason": "end_turn"}
                return

    except HTTPError as e:
        error_detail = _read_http_error_body(e)
        yield {"type": "error", "error": f"连接 AI 服务失败: HTTP {e.code} — {error_detail}"}
    except (TimeoutError, URLError) as e:
        reason = str(e)
        yield {"type": "error", "error": f"连接 AI 服务失败: {reason}"}
    except Exception as e:
        yield {"type": "error", "error": f"AI 调用异常: {str(e)}"}


async def _stream_openai_compatible(
    url: str,
    api_key: str,
    model_name: str,
    messages: list[dict],
    tools: Optional[list[dict]],
    max_tokens: int,
    timeout: int,
    cfg: dict,
) -> AsyncGenerator[dict, None]:
    """OpenAI 兼容端点流式调用（智谱/DeepSeek/Kimi/通义/OpenAI 等）

    解析 SSE 格式：每行 `data: {...}`，末尾 `data: [DONE]`
    """
    chat_path = cfg.get("chat_path", "/chat/completions")
    full_url = url + chat_path

    body: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if tools:
        body["tools"] = tools

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if api_key else "",
    }

    req_data = json.dumps(body).encode()
    req = Request(full_url, data=req_data, headers=headers, method="POST")

    full_text = ""
    reasoning_text = ""
    tool_calls_acc: dict[int, dict] = {}  # index -> {name, arguments_str, id}

    try:
        resp = urlopen(req, timeout=timeout)
        buffer = ""

        for raw_chunk in resp:
            buffer += raw_chunk.decode("utf-8", errors="replace")

            # 按行处理 SSE
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()

                if not line or not line.startswith("data:"):
                    continue

                data_str = line[len("data:"):].strip()

                if data_str == "[DONE]":
                    # 流结束 — 输出剩余的 tool calls
                    for idx in sorted(tool_calls_acc.keys()):
                        yield _emit_tool_call(tool_calls_acc[idx])

                    if not full_text and not tool_calls_acc:
                        yield {"type": "text", "text": ""}
                    yield {"type": "done", "stop_reason": "end_turn", "reasoning_content": reasoning_text}
                    return

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})

                # 文本内容
                content = delta.get("content", "")
                if content:
                    full_text += content
                    yield {"type": "text", "text": content}

                # 推理内容（思考模式模型如 DeepSeek V4 Flash）
                rc = delta.get("reasoning_content", "")
                if rc:
                    reasoning_text += rc

                # tool calls（增量拼接）
                tc_deltas = delta.get("tool_calls", [])
                for tc_delta in tc_deltas:
                    idx = tc_delta.get("index", 0)
                    func = tc_delta.get("function", {})

                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"name": "", "arguments_str": "", "id": ""}

                    if tc_delta.get("id"):
                        tool_calls_acc[idx]["id"] = tc_delta["id"]
                    if func.get("name"):
                        tool_calls_acc[idx]["name"] = func["name"]
                    if func.get("arguments"):
                        tool_calls_acc[idx]["arguments_str"] += func["arguments"]

        # 流意外结束（没有 [DONE]）— 尝试从 buffer 解析剩余数据
        if buffer.strip().startswith("data:"):
            data_str = buffer.strip()[len("data:"):].strip()
            if data_str == "[DONE]":
                for idx in sorted(tool_calls_acc.keys()):
                    yield _emit_tool_call(tool_calls_acc[idx])
                yield {"type": "done", "stop_reason": "end_turn", "reasoning_content": reasoning_text}
                return

        # 如果有内容但没收到 [DONE]，仍然发出 done
        if full_text or tool_calls_acc:
            for idx in sorted(tool_calls_acc.keys()):
                yield _emit_tool_call(tool_calls_acc[idx])
            yield {"type": "done", "stop_reason": "end_turn", "reasoning_content": reasoning_text}
        else:
            # 没有收到任何内容 — 可能是非流式响应，尝试 fallback
            async for evt in _non_stream_fallback_fallback(
                full_url, headers, body, timeout
            ):
                yield evt

    except HTTPError as e:
        # 读取响应体获取真实错误信息
        error_detail = _read_http_error_body(e)
        # 400 + 有 tools → 可能是模型不支持 function calling，降级重试
        if e.code == 400 and tools:
            async for evt in _stream_openai_compatible(
                url, api_key, model_name, messages, None, max_tokens, timeout, cfg
            ):
                yield evt
            return
        yield {"type": "error", "error": f"连接 AI 服务失败: HTTP {e.code} — {error_detail}"}
    except (TimeoutError, URLError) as e:
        reason = str(e)
        yield {"type": "error", "error": f"连接 AI 服务失败: {reason}"}
    except Exception as e:
        yield {"type": "error", "error": f"AI 调用异常: {str(e)}"}


def _read_http_error_body(e: HTTPError) -> str:
    """读取 HTTPError 响应体中的真实错误信息"""
    try:
        raw = e.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        # OpenAI 兼容格式: {"error": {"message": "...", "type": "..."}}
        err_obj = data.get("error", {})
        if isinstance(err_obj, dict):
            return err_obj.get("message", raw[:200])
        return str(err_obj)[:200]
    except Exception:
        return f"HTTP {e.code}"


def _emit_tool_call(tc: dict) -> dict:
    """构建 tool_call 事件，确保包含 id"""
    args_str = tc.get("arguments_str", "")
    try:
        args = json.loads(args_str) if args_str else {}
    except json.JSONDecodeError:
        args = {"_raw": args_str}
    tool_call = {"name": tc.get("name", ""), "arguments": args}
    if tc.get("id"):
        tool_call["id"] = tc["id"]
    return {"type": "tool_call", "tool_call": tool_call}


async def _non_stream_fallback_fallback(
    full_url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: int,
) -> AsyncGenerator[dict, None]:
    """流式请求失败后的非流式兜底"""
    body["stream"] = False
    req_data = json.dumps(body).encode()
    req = Request(full_url, data=req_data, headers=headers, method="POST")

    try:
        resp = urlopen(req, timeout=timeout)
        raw = resp.read()
        data = json.loads(raw)

        choices = data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""

        if content:
            yield {"type": "text", "text": content}

        if choices:
            tool_calls = choices[0].get("message", {}).get("tool_calls", [])
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    args = {}
                tool_call = {"name": name, "arguments": args}
                if tc.get("id"):
                    tool_call["id"] = tc["id"]
                yield {"type": "tool_call", "tool_call": tool_call}

        yield {"type": "done", "stop_reason": "end_turn"}

    except HTTPError as e:
        error_detail = _read_http_error_body(e)
        yield {"type": "error", "error": f"AI 调用失败: HTTP {e.code} — {error_detail}"}
    except Exception as e:
        yield {"type": "error", "error": f"AI 调用失败: {str(e)}"}


async def _non_stream_fallback(
    provider: str,
    url: str,
    api_key: str,
    model_name: str,
    messages: list[dict],
    tools: Optional[list[dict]],
    max_tokens: int,
    timeout: int,
    cfg: dict,
) -> AsyncGenerator[dict, None]:
    """非流式 fallback（仅用于 Anthropic 等特殊格式提供商）"""
    chat_path = cfg.get("chat_path", "/messages")
    full_url = url + chat_path

    body: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if tools:
        body["tools"] = tools

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "x-api-key": api_key or "",
        "anthropic-version": "2023-06-01",
    }

    req_data = json.dumps(body).encode()
    req = Request(full_url, data=req_data, headers=headers, method="POST")

    try:
        resp = urlopen(req, timeout=timeout)
        raw = resp.read()
        data = json.loads(raw)

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        if content:
            yield {"type": "text", "text": content}

        yield {"type": "done", "stop_reason": "end_turn"}

    except HTTPError as e:
        error_detail = _read_http_error_body(e)
        yield {"type": "error", "error": f"AI 调用失败: HTTP {e.code} — {error_detail}"}
    except Exception as e:
        yield {"type": "error", "error": f"AI 调用失败: {str(e)}"}
