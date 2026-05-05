"""Provider 抽象层 — 适配多提供商流式调用

支持 Ollama 原生格式 + OpenAI 兼容格式（智谱/DeepSeek/Kimi/通义/OpenAI 等）的流式输出。
复用 core/ai_provider.py 的配置。
使用 httpx 替代 urllib，支持异步和流式，不阻塞事件循环。

增强：
- 超时自动重试（TimeoutException / HTTP 5xx，最多 2 次，指数退避）
- Anthropic SSE 流式支持
- 超时分级（根据 max_tokens 动态调整）
- 连接池复用（全局 httpx.AsyncClient）
"""
import json
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from core.ai_provider import PROVIDER_CONFIG

MAX_RETRIES = 2
RETRY_DELAYS = [1, 3]

# 全局连接池 — 复用 TCP 连接，避免每次请求都建新连接
_shared_client: httpx.AsyncClient | None = None


async def _get_client(timeout: int) -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(timeout=timeout)
    else:
        _shared_client.timeout = httpx.Timeout(timeout)
    return _shared_client


def _sanitize_messages(messages: list[dict], provider: str) -> list[dict]:
    """清洗消息列表，确保 API 兼容性

    - 移除 reasoning_content（仅 DeepSeek 支持）
    - 移除 _pending_pop 等内部标记
    - 移除 tool 消息上的非法字段（tool_calls, tool_result）
    - 确保 tool result 的 content 是 string
    """
    TOOL_ALLOWED_KEYS = {"role", "tool_call_id", "content"}

    cleaned = []
    for msg in messages:
        m = {}
        for k, v in msg.items():
            if k.startswith("_"):
                continue
            if k == "reasoning_content" and provider != "deepseek":
                continue
            m[k] = v

        if m.get("role") == "tool":
            m = {k: v for k, v in m.items() if k in TOOL_ALLOWED_KEYS}
            if not isinstance(m.get("content"), str):
                m["content"] = json.dumps(m.get("content", ""), ensure_ascii=False)

        if m.get("role") == "assistant" and m.get("content") == "":
            m["content"] = None

        if m.get("role") == "assistant" and not m.get("content") and not m.get("tool_calls"):
            m["content"] = "（继续处理）"
            if "reasoning_content" in m:
                del m["reasoning_content"]

        cleaned.append(m)
    return cleaned


def _compute_timeout(base_timeout: int, max_tokens: int) -> int:
    """根据 max_tokens 动态调整超时，避免长生成任务被截断"""
    return max(base_timeout, int(max_tokens * 0.1))


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
    provider_limit = cfg.get("max_tokens_limit", 0)
    if provider_limit > 0 and max_tokens > provider_limit:
        max_tokens = provider_limit
    url = (base_url or cfg.get("base_url", "")).rstrip("/")

    messages = _sanitize_messages(messages, provider)

    if not url:
        yield {"type": "error", "error": "缺少 AI 配置的 base_url"}
        return

    # 超时分级
    timeout = _compute_timeout(timeout, max_tokens)

    if provider == "ollama":
        async for evt in _with_retry(
            lambda: _stream_ollama(url, model_name, messages, tools, max_tokens, timeout)
        ):
            yield evt
    elif provider == "anthropic":
        async for evt in _with_retry(
            lambda: _stream_anthropic(url, api_key, model_name, messages, tools, max_tokens, timeout, cfg)
        ):
            yield evt
    else:
        async for evt in _with_retry(
            lambda: _stream_openai_compatible(url, api_key, model_name, messages, tools, max_tokens, timeout, cfg)
        ):
            yield evt


async def _with_retry(stream_fn, max_retries: int = MAX_RETRIES) -> AsyncGenerator[dict, None]:
    """自动重试包装器：对超时和 5xx 错误重试"""
    last_error = None
    for attempt in range(max_retries + 1):
        got_data = False
        try:
            async for evt in stream_fn():
                got_data = True
                if evt["type"] == "error":
                    error_msg = evt.get("error", "")
                    if _is_retryable_error(error_msg) and attempt < max_retries:
                        last_error = evt
                        break
                    yield evt
                    return
                yield evt
            if got_data or last_error is None:
                return
        except Exception as e:
            if attempt >= max_retries:
                yield {"type": "error", "error": f"AI 调用异常（已重试 {max_retries} 次）: {str(e)}"}
                return

        if attempt < max_retries:
            delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 3
            import asyncio
            await asyncio.sleep(delay)


def _is_retryable_error(error_msg: str) -> bool:
    """判断错误是否可重试"""
    retryable_patterns = ["超时", "timeout", "Timeout", "502", "503", "504", "连接"]
    return any(p in error_msg for p in retryable_patterns)


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
        client = await _get_client(timeout)
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

                tc_list = msg.get("tool_calls") or []
                if tc_list:
                    for tc in tc_list:
                        yield _emit_tool_call_from_ollama(tc)

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


def _emit_tool_call_from_ollama(tc: dict) -> dict:
    """从 Ollama tool_call 格式提取标准格式"""
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
    return {"type": "tool_call", "tool_call": tool_call}


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
    """OpenAI 兼容端点流式调用（智谱/DeepSeek/Kimi/通义/OpenAI 等）"""
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
        client = await _get_client(timeout)
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
                    if "tool" in msg.lower() and "role" in msg.lower():
                        yield {"type": "error", "error": f"AI 服务返回 400（消息格式错误）: {msg}"}
                    else:
                        yield {"type": "error", "error": f"AI 服务返回 400（模型可能不支持 function calling）: {msg}"}
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

                    choices = chunk.get("choices") or []
                    if not choices:
                        continue

                    choice = choices[0] if choices[0] else {}
                    delta = choice.get("delta") or {}
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

                    tc_deltas = delta.get("tool_calls") or []
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

        if buffer.strip().startswith("data:"):
            data_str = buffer.strip()[len("data:"):].strip()
            if data_str == "[DONE]":
                for idx in sorted(tool_calls_acc.keys()):
                    yield _emit_tool_call(tool_calls_acc[idx])
                yield {"type": "done", "stop_reason": captured_finish_reason or "end_turn", "reasoning_content": reasoning_text}
                return

        if full_text or tool_calls_acc:
            for idx in sorted(tool_calls_acc.keys()):
                yield _emit_tool_call(tool_calls_acc[idx])
            yield {"type": "done", "stop_reason": captured_finish_reason or "end_turn", "reasoning_content": reasoning_text}
        else:
            yield {"type": "done", "stop_reason": "no_content"}

    except httpx.TimeoutException:
        yield {"type": "error", "error": "连接 AI 服务超时"}
    except httpx.ConnectError as e:
        yield {"type": "error", "error": f"连接 AI 服务失败: {e}"}
    except Exception as e:
        yield {"type": "error", "error": f"AI 调用异常: {str(e)}"}


async def _stream_anthropic(
    url: str,
    api_key: str,
    model_name: str,
    messages: list[dict],
    tools: Optional[list[dict]],
    max_tokens: int,
    timeout: int,
    cfg: dict,
) -> AsyncGenerator[dict, None]:
    """Anthropic SSE 流式调用（替代非流式 fallback）"""
    chat_path = cfg.get("chat_path", "/messages")
    full_url = url + chat_path

    body: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if tools:
        body["tools"] = _convert_to_anthropic_tools(tools)

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "x-api-key": api_key or "",
        "anthropic-version": "2023-06-01",
    }

    full_text = ""
    tool_calls_acc: dict[int, dict] = {}

    try:
        client = await _get_client(timeout)
        async with client.stream("POST", full_url, json=body, headers=headers) as resp:
            if resp.status_code >= 400:
                error_text = await resp.aread()
                try:
                    error_data = json.loads(error_text)
                    msg = error_data.get("error", {}).get("message", error_text.decode()[:200])
                except Exception:
                    msg = error_text.decode("utf-8", errors="replace")[:200]
                yield {"type": "error", "error": f"Anthropic 调用失败: HTTP {resp.status_code} — {msg}"}
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
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("type", "")

                    if event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                full_text += text
                                yield {"type": "text", "text": text}
                        elif delta.get("type") == "input_json_delta":
                            idx = event.get("index", 0)
                            partial = delta.get("partial_json", "")
                            if idx not in tool_calls_acc:
                                tool_calls_acc[idx] = {"arguments_str": ""}
                            tool_calls_acc[idx]["arguments_str"] += partial

                    elif event_type == "content_block_start":
                        cb = event.get("content_block", {})
                        if cb.get("type") == "tool_use":
                            idx = event.get("index", 0)
                            tool_calls_acc[idx] = {
                                "name": cb.get("name", ""),
                                "id": cb.get("id", ""),
                                "arguments_str": "",
                            }

                    elif event_type == "message_stop":
                        for idx in sorted(tool_calls_acc.keys()):
                            tc = tool_calls_acc[idx]
                            yield _emit_tool_call(tc)
                        if not full_text and not tool_calls_acc:
                            yield {"type": "text", "text": ""}
                        yield {"type": "done", "stop_reason": "end_turn"}
                        return

                    elif event_type == "error":
                        err_msg = event.get("error", {}).get("message", "未知错误")
                        yield {"type": "error", "error": f"Anthropic 错误: {err_msg}"}
                        return

        if full_text or tool_calls_acc:
            for idx in sorted(tool_calls_acc.keys()):
                yield _emit_tool_call(tool_calls_acc[idx])
            yield {"type": "done", "stop_reason": "end_turn"}

    except httpx.TimeoutException:
        yield {"type": "error", "error": "连接 AI 服务超时"}
    except httpx.ConnectError as e:
        yield {"type": "error", "error": f"连接 AI 服务失败: {e}"}
    except Exception as e:
        yield {"type": "error", "error": f"AI 调用异常: {str(e)}"}


def _convert_to_anthropic_tools(openai_tools: list[dict]) -> list[dict]:
    """将 OpenAI 格式工具转换为 Anthropic 格式"""
    result = []
    for t in openai_tools:
        func = t.get("function", {})
        result.append({
            "name": func.get("name", ""),
            "description": func.get("description", ""),
            "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
        })
    return result


def _emit_tool_call(tc: dict) -> dict:
    """构建 tool_call 事件"""
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
