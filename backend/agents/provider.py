"""Provider 抽象层 — 适配多提供商流式调用

支持 Ollama 原生格式 + OpenAI 兼容格式（智谱/DeepSeek/Kimi/通义/OpenAI 等）的流式输出。
复用 core/ai_provider.py 的配置。
使用 httpx 替代 urllib，支持异步和流式，不阻塞事件循环。
"""
import json
import time
from typing import Any, AsyncGenerator, Optional

import httpx

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
        async for evt in _stream_ollama(url, model_name, messages, tools, max_tokens, timeout):
            yield evt
    elif provider == "anthropic":
        async for evt in _non_stream_fallback(
            provider, url, api_key, model_name, messages, tools, max_tokens, timeout, cfg
        ):
            yield evt
    else:
        async for evt in _stream_openai_compatible(
            url, api_key, model_name, messages, tools, max_tokens, timeout, cfg
        ):
            yield evt


async def _stream_ollama(
    url: str,
    model_name: str,
    messages: list[dict],
    tools: Optional[list[dict]],
    max_tokens: int,
    timeout: int,
) -> AsyncGenerator[dict, None]:
    """Ollama /api/chat 流式调用"""
    full_url = f"{url}/api/chat"
    body: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": True,
        "options": {"num_predict": max_tokens},
    }
    if tools:
        body["tools"] = tools

    headers = {"Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", full_url, json=body, headers=headers) as resp:
                resp.raise_for_status()
                full_text = ""

                async for raw_line in resp.aiter_lines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        full_text += content
                        yield {"type": "text", "text": content}

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
                        if not full_text:
                            yield {"type": "text", "text": ""}
                        yield {"type": "done", "stop_reason": "end_turn"}
                        return

    except httpx.HTTPStatusError as e:
        error_detail = _extract_error_detail(e)
        yield {"type": "error", "error": f"连接 AI 服务失败: HTTP {e.response.status_code} — {error_detail}"}
    except httpx.TimeoutException:
        yield {"type": "error", "error": "连接 AI 服务超时"}
    except httpx.ConnectError as e:
        yield {"type": "error", "error": f"连接 AI 服务失败: {e}"}
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

    full_text = ""
    reasoning_text = ""
    tool_calls_acc: dict[int, dict] = {}
    captured_finish_reason: str | None = None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", full_url, json=body, headers=headers) as resp:
                if resp.status_code >= 400:
                    error_text = await resp.aread()
                    try:
                        error_data = json.loads(error_text)
                        error_detail = error_data.get("error", {})
                        if isinstance(error_detail, dict):
                            msg = error_detail.get("message", error_text.decode()[:200])
                        else:
                            msg = str(error_detail)[:200]
                    except Exception:
                        msg = error_text.decode("utf-8", errors="replace")[:200]

                    if resp.status_code == 400 and tools:
                        # 模型可能不支持 function calling，降级重试
                        async for evt in _stream_openai_compatible(
                            url, api_key, model_name, messages, None, max_tokens, timeout, cfg
                        ):
                            yield evt
                        return
                    yield {"type": "error", "error": f"连接 AI 服务失败: HTTP {resp.status_code} — {msg}"}
                    return

                buffer = ""
                async for raw_chunk in resp.aiter_text():
                    buffer += raw_chunk

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line or not line.startswith("data:"):
                            continue

                        data_str = line[len("data:"):].strip()

                        if data_str == "[DONE]":
                            for idx in sorted(tool_calls_acc.keys()):
                                yield _emit_tool_call(tool_calls_acc[idx])
                            if not full_text and not tool_calls_acc:
                                yield {"type": "text", "text": ""}
                            yield {"type": "done", "stop_reason": captured_finish_reason or "end_turn", "reasoning_content": reasoning_text}
                            return

                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choices = chunk.get("choices", [])
                        if not choices:
                            continue

                        choice = choices[0]
                        delta = choice.get("delta", {})
                        finish_reason = choice.get("finish_reason")

                        content = delta.get("content", "")
                        if content:
                            full_text += content
                            yield {"type": "text", "text": content}

                        rc = delta.get("reasoning_content", "")
                        if rc:
                            reasoning_text += rc

                        if finish_reason:
                            captured_finish_reason = finish_reason

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

        # 流意外结束（没有 [DONE]）— 处理 buffer 残余
        if buffer.strip().startswith("data:"):
            data_str = buffer.strip()[len("data:"):].strip()
            if data_str == "[DONE]":
                for idx in sorted(tool_calls_acc.keys()):
                    yield _emit_tool_call(tool_calls_acc[idx])
                yield {"type": "done", "stop_reason": captured_finish_reason or "end_turn", "reasoning_content": reasoning_text}
                return

        # 有内容但没收到 [DONE]
        if full_text or tool_calls_acc:
            for idx in sorted(tool_calls_acc.keys()):
                yield _emit_tool_call(tool_calls_acc[idx])
            yield {"type": "done", "stop_reason": captured_finish_reason or "end_turn", "reasoning_content": reasoning_text}
        else:
            async for evt in _non_stream_fallback_fallback(
                full_url, headers, body, timeout
            ):
                yield evt

    except httpx.TimeoutException:
        yield {"type": "error", "error": "连接 AI 服务超时"}
    except httpx.ConnectError as e:
        yield {"type": "error", "error": f"连接 AI 服务失败: {e}"}
    except Exception as e:
        yield {"type": "error", "error": f"AI 调用异常: {str(e)}"}


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


def _extract_error_detail(exc: httpx.HTTPStatusError) -> str:
    """从 HTTP 错误响应中提取可读错误信息"""
    try:
        data = exc.response.json()
        err_obj = data.get("error", {})
        if isinstance(err_obj, dict):
            return err_obj.get("message", exc.response.text[:200])
        return str(err_obj)[:200]
    except Exception:
        return f"HTTP {exc.response.status_code}"


async def _non_stream_fallback_fallback(
    full_url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: int,
) -> AsyncGenerator[dict, None]:
    """流式请求失败后的非流式兜底"""
    body["stream"] = False

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(full_url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

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

    except httpx.HTTPStatusError as e:
        error_detail = _extract_error_detail(e)
        yield {"type": "error", "error": f"AI 调用失败: HTTP {e.response.status_code} — {error_detail}"}
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

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(full_url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        if content:
            yield {"type": "text", "text": content}

        stop = data.get("stop_reason", "end_turn")
        if stop == "max_tokens":
            stop = "length"
        yield {"type": "done", "stop_reason": stop}

    except httpx.HTTPStatusError as e:
        error_detail = _extract_error_detail(e)
        yield {"type": "error", "error": f"AI 调用失败: HTTP {e.response.status_code} — {error_detail}"}
    except Exception as e:
        yield {"type": "error", "error": f"AI 调用失败: {str(e)}"}
