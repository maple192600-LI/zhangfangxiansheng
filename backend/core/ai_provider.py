"""AI Provider 统一调用入口

支持多种 AI 提供商的连接测试和基础调用。
V1 仅实现测试连接功能。
"""
import json
import time
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


# 各提供商的默认 base_url 和测试 prompt
PROVIDER_DEFAULTS = {
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "test_path": "/chat/completions",
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "test_path": "/chat/completions",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "test_path": "/chat/completions",
    },
    "openai_compatible": {
        "base_url": "",
        "test_path": "/chat/completions",
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "test_path": "/api/chat",
    },
}


def test_connection(
    provider: str,
    api_key: str,
    base_url: Optional[str],
    model_name: str,
    timeout: int = 15,
) -> Dict[str, Any]:
    """测试 AI Provider 连接

    返回:
        {"connected": bool, "latency_ms": int, "model_info": str, "error": str|None}
    """
    defaults = PROVIDER_DEFAULTS.get(provider, {})
    url = (base_url or defaults.get("base_url", "")).rstrip("/")
    test_path = defaults.get("test_path", "/chat/completions")

    if not url:
        return {"connected": False, "latency_ms": 0, "model_info": "", "error": "缺少 base_url"}

    full_url = url + test_path

    # 构建最小化测试请求
    if provider == "ollama":
        body = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
            "options": {"num_predict": 1},
        }).encode()
        headers = {"Content-Type": "application/json"}
    else:
        body = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "stream": False,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    req = Request(full_url, data=body, headers=headers, method="POST")

    start = time.time()
    try:
        resp = urlopen(req, timeout=timeout)
        elapsed_ms = int((time.time() - start) * 1000)
        _ = resp.read()
        return {
            "connected": True,
            "latency_ms": elapsed_ms,
            "model_info": model_name,
            "error": None,
        }
    except URLError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        reason = str(e.reason) if hasattr(e, "reason") else str(e)
        if "timed out" in reason.lower():
            return {
                "connected": False,
                "latency_ms": elapsed_ms,
                "model_info": model_name,
                "error": f"连接超时（>{timeout}s）",
            }
        return {
            "connected": False,
            "latency_ms": elapsed_ms,
            "model_info": model_name,
            "error": f"连接失败: {reason}",
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "connected": False,
            "latency_ms": elapsed_ms,
            "model_info": model_name,
            "error": f"异常: {str(e)}",
        }
