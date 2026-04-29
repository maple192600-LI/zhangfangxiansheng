"""AI 调用工具 — 统一 chat 请求封装"""
import json
import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from core.ai_provider import PROVIDER_CONFIG


def _extract_error_detail(exc: httpx.HTTPStatusError) -> str:
    """从 HTTP 错误响应中提取可读错误信息"""
    try:
        data = exc.response.json()
        err_obj = data.get("error", {})
        if isinstance(err_obj, dict):
            return err_obj.get("message", exc.response.text[:300])
        return str(err_obj)[:300]
    except Exception:
        return exc.response.text[:300]


def chat(
    provider: str,
    api_key: str,
    base_url: Optional[str],
    model_name: str,
    messages: list,
    max_tokens: int = 1024,
    timeout: int = 30,
) -> Dict[str, Any]:
    """发送 chat 请求，返回解析后的响应。

    Returns:
        {"ok": True, "content": str} 或 {"ok": False, "error": str}
    """
    cfg = PROVIDER_CONFIG.get(provider, {})
    url = (base_url or cfg.get("base_url", "")).rstrip("/")
    chat_path = cfg.get("chat_path", "/chat/completions")

    if not url:
        return {"ok": False, "error": "缺少 base_url"}

    full_url = url + chat_path

    if provider == "ollama":
        body = {
            "model": model_name,
            "messages": messages,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
    elif provider == "anthropic":
        body = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    else:
        body = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    request_size = len(json.dumps(body).encode())

    started = time.time()
    last_error: Dict[str, Any] = {}
    for attempt in range(2):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(full_url, json=body, headers=headers)
            resp.raise_for_status()
            raw = resp.content
            data = resp.json()

            # 提取 content
            if provider == "anthropic":
                content = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")
            elif provider == "ollama":
                content = data.get("message", {}).get("content", "")
            else:
                choices = data.get("choices", [])
                content = choices[0].get("message", {}).get("content", "") if choices else ""

            _write_ai_call_log(
                provider=provider,
                model=model_name,
                endpoint=full_url,
                status="success",
                duration_ms=_duration_ms(started),
                request_size=request_size,
                response_size=len(raw),
                error_code=None,
            )
            return {"ok": True, "content": content}

        except json.JSONDecodeError as e:
            err = _error("AI_RESPONSE_JSON_INVALID", "parse", f"AI 响应不是合法 JSON: {e}")
            _log_failure(provider, model_name, full_url, started, request_size, err)
            return err
        except httpx.HTTPStatusError as e:
            detail = _extract_error_detail(e)
            category = "auth" if e.response.status_code in (401, 403) else "http"
            msg = f"AI 服务返回 HTTP {e.response.status_code}"
            if detail:
                msg += f": {detail}"
            err = _error(f"AI_HTTP_{e.response.status_code}", category, msg)
            _log_failure(provider, model_name, full_url, started, request_size, err)
            return err
        except httpx.TimeoutException:
            last_error = _error("AI_TIMEOUT", "timeout", f"AI 调用超时（>{timeout}s）")
        except httpx.ConnectError as e:
            last_error = _error("AI_CONNECTION_FAILED", "network", f"连接失败: {e}")
        except Exception as e:
            return _error("AI_CALL_FAILED", "unknown", f"AI 调用异常: {e}")

        if attempt == 0:
            time.sleep(1)

    _log_failure(provider, model_name, full_url, started, request_size, last_error)
    return last_error


def _error(error_code: str, category: str, message: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": message,
        "error_code": error_code,
        "error_category": category,
    }


def _duration_ms(started: float) -> int:
    return int((time.time() - started) * 1000)


def _log_failure(
    provider: str,
    model_name: str,
    endpoint: str,
    started: float,
    request_size: int,
    error_result: Dict[str, Any],
) -> None:
    _write_ai_call_log(
        provider=provider,
        model=model_name,
        endpoint=endpoint,
        status="failed",
        duration_ms=_duration_ms(started),
        request_size=request_size,
        response_size=0,
        error_code=error_result.get("error_code"),
    )


def _write_ai_call_log(
    provider: str,
    model: str,
    endpoint: str,
    status: str,
    duration_ms: int,
    request_size: int,
    response_size: int,
    error_code: Optional[str],
) -> None:
    try:
        from database import SessionLocal
        from db.tables import AICallLog

        with SessionLocal() as db:
            db.add(AICallLog(
                provider=provider,
                model=model,
                endpoint=endpoint,
                status=status,
                duration_ms=duration_ms,
                request_size=request_size,
                response_size=response_size,
                error_code=error_code,
                created_at=datetime.now(),
            ))
            db.commit()
    except Exception:
        pass
