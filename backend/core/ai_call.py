"""AI 调用工具 — 统一 chat 请求封装"""
import json
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from core.ai_provider import PROVIDER_CONFIG


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
        body = json.dumps({
            "model": model_name,
            "messages": messages,
            "stream": False,
        }).encode()
        headers = {"Content-Type": "application/json"}
    elif provider == "anthropic":
        body = json.dumps({
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    else:
        body = json.dumps({
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    req = Request(full_url, data=body, headers=headers, method="POST")

    try:
        resp = urlopen(req, timeout=timeout)
        data = json.loads(resp.read())

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

        return {"ok": True, "content": content}

    except URLError as e:
        reason = str(e.reason) if hasattr(e, "reason") else str(e)
        return {"ok": False, "error": f"连接失败: {reason}"}
    except Exception as e:
        return {"ok": False, "error": f"异常: {str(e)}"}
