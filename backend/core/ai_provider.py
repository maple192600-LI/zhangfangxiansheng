"""AI Provider 统一调用入口

支持多种 AI 提供商的连接测试和模型列表查询。
模型信息来源于各提供商官方文档（2025年4月）。
"""
import json
import time
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


# ──────────────────────────────────────────
# 各提供商配置（基于官方文档）
# ──────────────────────────────────────────

PROVIDER_CONFIG = {
    "zhipu": {
        "label": "智谱 (GLM)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "models": [
            {"id": "glm-5.1", "name": "GLM-5.1", "desc": "最新旗舰，Coding对标Claude Opus 4.6"},
            {"id": "glm-5-turbo", "name": "GLM-5 Turbo", "desc": "快速推理版，复杂长任务连续性好"},
            {"id": "glm-5", "name": "GLM-5", "desc": "高智能基座，编程对标Claude Opus 4.5"},
            {"id": "glm-4.7", "name": "GLM-4.7", "desc": "通用对话推理全面升级"},
            {"id": "glm-4.7-flashx", "name": "GLM-4.7 FlashX", "desc": "轻量高速，中文写作翻译"},
            {"id": "glm-4.5-air", "name": "GLM-4.5 Air", "desc": "高性价比，推理编码强劲"},
            {"id": "glm-4.5-airx", "name": "GLM-4.5 AirX", "desc": "极速版，时效性要求场景"},
            {"id": "glm-4.7-flash", "name": "GLM-4.7 Flash", "desc": "免费模型，最新基座普惠版"},
            {"id": "glm-4.5-flash", "name": "GLM-4.5 Flash", "desc": "免费模型，支持深度思考"},
            {"id": "glm-4-flashx-250414", "name": "GLM-4 FlashX", "desc": "高速低价，高并发"},
        ],
    },
    "minimax": {
        "label": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "models": [
            {"id": "MiniMax-Text-01", "name": "MiniMax-Text-01", "desc": "456B MoE旗舰，超长上下文"},
            {"id": "abab6.5s", "name": "abab 6.5s", "desc": "高性价比对话模型"},
            {"id": "abab6.5g", "name": "abab 6.5g", "desc": "高质量对话模型"},
            {"id": "abab5.5s", "name": "abab 5.5s", "desc": "基础对话模型"},
        ],
    },
    "kimi": {
        "label": "Kimi (月之暗面)",
        "base_url": "https://api.moonshot.cn/v1",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "models": [
            {"id": "kimi-k2.5", "name": "Kimi K2.5", "desc": "最新主力，256K超长上下文，多模态"},
            {"id": "moonshot-v1-128k", "name": "Moonshot V1 128K", "desc": "128K上下文"},
            {"id": "moonshot-v1-32k", "name": "Moonshot V1 32K", "desc": "32K上下文"},
            {"id": "moonshot-v1-8k", "name": "Moonshot V1 8K", "desc": "8K上下文，高性价比"},
        ],
    },
    "qwen": {
        "label": "阿里百炼 (通义千问)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "models": [
            {"id": "qwen3-max", "name": "Qwen3 Max", "desc": "旗舰模型，复杂任务"},
            {"id": "qwen3-plus", "name": "Qwen3.5 Plus", "desc": "速度更快成本更低"},
            {"id": "qwen3-turbo", "name": "Qwen3 Turbo", "desc": "极速推理"},
            {"id": "qwen-plus", "name": "Qwen Plus", "desc": "高性价比"},
            {"id": "qwen-turbo", "name": "Qwen Turbo", "desc": "超快推理，超低价格"},
            {"id": "qwen-max", "name": "Qwen Max", "desc": "能力最强，适合复杂任务"},
            {"id": "qwen-long", "name": "Qwen Long", "desc": "超长上下文，文档处理"},
        ],
    },
    "openai": {
        "label": "OpenAI (ChatGPT)",
        "base_url": "https://api.openai.com/v1",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o", "desc": "多模态旗舰"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "desc": "高性价比"},
            {"id": "gpt-4.1", "name": "GPT-4.1", "desc": "最新旗舰，指令遵循强"},
            {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini", "desc": "平衡速度和质量"},
            {"id": "gpt-4.1-nano", "name": "GPT-4.1 Nano", "desc": "最快最便宜"},
            {"id": "o3-mini", "name": "o3-mini", "desc": "推理模型"},
        ],
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "base_url": "https://api.anthropic.com/v1",
        "chat_path": "/messages",
        "needs_api_key": True,
        "models": [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "desc": "最佳编码模型"},
            {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "desc": "最强推理"},
            {"id": "claude-haiku-3-5-20241022", "name": "Claude Haiku 3.5", "desc": "最快最便宜"},
        ],
    },
    "ollama": {
        "label": "Ollama (本地)",
        "base_url": "http://localhost:11434",
        "chat_path": "/api/chat",
        "needs_api_key": False,
        "models": [],  # 自动从本地检测
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "models": [
            {"id": "deepseek-v4-pro", "name": "DeepSeek V4 Pro", "desc": "旗舰推理模型，复杂任务首选"},
            {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash", "desc": "快速推理，高性价比"},
        ],
    },
    "openai_compatible": {
        "label": "OpenAI 兼容",
        "base_url": "",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "models": [],
    },
}


def get_provider_list() -> List[Dict[str, Any]]:
    """返回所有支持的提供商列表（供前端选择）"""
    result = []
    for code, cfg in PROVIDER_CONFIG.items():
        result.append({
            "code": code,
            "label": cfg["label"],
            "base_url": cfg["base_url"],
            "needs_api_key": cfg["needs_api_key"],
            "models": cfg["models"],
        })
    return result


def get_provider_models(provider: str) -> List[Dict[str, str]]:
    """获取某提供商的模型列表"""
    cfg = PROVIDER_CONFIG.get(provider, {})
    return cfg.get("models", [])


def detect_ollama_models(base_url: str = "http://localhost:11434") -> List[Dict[str, str]]:
    """自动检测 Ollama 本地已安装的模型"""
    models = []
    try:
        url = base_url.rstrip("/") + "/api/tags"
        req = Request(url, method="GET")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read())
        for m in data.get("models", []):
            name = m.get("name", "")
            size_mb = round(m.get("size", 0) / 1024 / 1024)
            models.append({
                "id": name,
                "name": name,
                "desc": f"本地模型 ({size_mb}MB)",
            })
    except Exception:
        pass
    return models


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
    cfg = PROVIDER_CONFIG.get(provider, {})
    url = (base_url or cfg.get("base_url", "")).rstrip("/")
    chat_path = cfg.get("chat_path", "/chat/completions")

    if not url:
        return {"connected": False, "latency_ms": 0, "model_info": "", "error": "缺少 base_url"}

    full_url = url + chat_path

    if provider == "ollama":
        body = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
            "options": {"num_predict": 1},
        }).encode()
        headers = {"Content-Type": "application/json"}
    elif provider == "anthropic":
        body = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
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
