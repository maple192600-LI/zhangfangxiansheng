"""AI Provider 统一调用入口

支持多种 AI 提供商的连接测试和模型列表查询。
"""
import json
import time
from typing import Any, Dict, List, Optional

import httpx


# ──────────────────────────────────────────
# 各提供商配置（基于官方文档）
# ──────────────────────────────────────────

PROVIDER_CONFIG = {
    "zhipu": {
        "label": "智谱 (GLM)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 4095,
        "url_presets": [
            {"label": "官方 API (国内)", "url": "https://open.bigmodel.cn/api/paas/v4"},
            {"label": "Z.ai (国际)", "url": "https://api.z.ai/api/paas/v4"},
        ],
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
        "base_url": "https://api.minimaxi.com/v1",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 16384,
        "url_presets": [
            {"label": "官方 API (国内)", "url": "https://api.minimaxi.com/v1"},
            {"label": "官方 API (国际)", "url": "https://api.minimax.io/v1"},
        ],
        "models": [
            {"id": "MiniMax-M2.7", "name": "MiniMax-M2.7", "desc": "旗舰模型，编程/Agent SOTA，约60 TPS"},
            {"id": "MiniMax-M2.7-highspeed", "name": "MiniMax-M2.7-highspeed", "desc": "M2.7极速版，约100 TPS"},
            {"id": "MiniMax-M2.5", "name": "MiniMax-M2.5", "desc": "顶尖性能与极致性价比，约60 TPS"},
            {"id": "MiniMax-M2.5-highspeed", "name": "MiniMax-M2.5-highspeed", "desc": "M2.5极速版，约100 TPS"},
            {"id": "MiniMax-M2.1", "name": "MiniMax-M2.1", "desc": "强大多语言编程能力，约60 TPS"},
            {"id": "MiniMax-M2.1-highspeed", "name": "MiniMax-M2.1-highspeed", "desc": "M2.1极速版，约100 TPS"},
            {"id": "MiniMax-M2", "name": "MiniMax-M2", "desc": "专为高效编码与Agent工作流而生"},
        ],
    },
    "kimi": {
        "label": "Kimi (月之暗面)",
        "base_url": "https://api.moonshot.cn/v1",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 16384,
        "url_presets": [
            {"label": "官方 API", "url": "https://api.moonshot.cn/v1"},
        ],
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
        "max_tokens_limit": 8192,
        "url_presets": [
            {"label": "阿里百炼 DashScope", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
        ],
        "models": [
            {"id": "qwen3-max", "name": "Qwen3 Max", "desc": "旗舰模型，复杂任务"},
            {"id": "qwen3-plus", "name": "Qwen3.5 Plus", "desc": "速度更快成本更低"},
            {"id": "qwen3-turbo", "name": "Qwen3 Turbo", "desc": "极速推理"},
            {"id": "qwen-plus", "name": "Qwen Plus", "desc": "高性价比"},
            {"id": "qwen-turbo", "name": "Qwen Turbo", "desc": "超快推理，超低价格"},
            {"id": "qwen-max", "name": "Qwen Max", "desc": "能力最强，适合复杂任务"},
            {"id": "qwen-long", "name": "Qwen Long", "desc": "超长上下文，文档处理"},
            {"id": "qwen3-coder-plus", "name": "Qwen3 Coder Plus", "desc": "编程专用，Agent/Coding"},
            {"id": "qwen3-coder-flash", "name": "Qwen3 Coder Flash", "desc": "编程极速版"},
        ],
    },
    "doubao": {
        "label": "豆包 (字节跳动/火山引擎)",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 16384,
        "url_presets": [
            {"label": "火山引擎 (官方)", "url": "https://ark.cn-beijing.volces.com/api/v3"},
            {"label": "火山引擎 华南", "url": "https://ark.cn-guangzhou.volces.com/api/v3"},
        ],
        "models": [
            {"id": "doubao-seed-code-preview-latest", "name": "Doubao Seed Code", "desc": "编程专用预览版，Agent/Coding场景"},
            {"id": "doubao-1.5-pro-256k", "name": "Doubao 1.5 Pro 256K", "desc": "旗舰，256K超长上下文"},
            {"id": "doubao-1.5-pro-32k", "name": "Doubao 1.5 Pro 32K", "desc": "旗舰，平衡性能"},
            {"id": "doubao-1.5-lite-32k", "name": "Doubao 1.5 Lite 32K", "desc": "轻量高速"},
            {"id": "doubao-pro-128k", "name": "Doubao Pro 128K", "desc": "高性价比，长上下文"},
            {"id": "doubao-pro-32k", "name": "Doubao Pro 32K", "desc": "标准版"},
            {"id": "doubao-lite-128k", "name": "Doubao Lite 128K", "desc": "极速版"},
            {"id": "doubao-lite-32k", "name": "Doubao Lite 32K", "desc": "基础版"},
        ],
    },
    "ernie": {
        "label": "百度文心 (千帆)",
        "base_url": "https://qianfan.baidubce.com/v2",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 8192,
        "url_presets": [
            {"label": "千帆平台 (OpenAI兼容)", "url": "https://qianfan.baidubce.com/v2"},
            {"label": "千帆 Coding Plan", "url": "https://qianfan.baidubce.com/v2/coding"},
        ],
        "models": [
            {"id": "ernie-4.5-turbo-128k", "name": "ERNIE 4.5 Turbo 128K", "desc": "最新旗舰，128K上下文"},
            {"id": "ernie-4.5-turbo-0205", "name": "ERNIE 4.5 Turbo", "desc": "最新旗舰，快速推理"},
            {"id": "ernie-4.0-8k", "name": "ERNIE 4.0", "desc": "旗舰模型，复杂任务"},
            {"id": "ernie-3.5-8k", "name": "ERNIE 3.5", "desc": "高性价比通用模型"},
            {"id": "ernie-speed-128k", "name": "ERNIE Speed 128K", "desc": "超长上下文"},
            {"id": "ernie-lite-8k", "name": "ERNIE Lite", "desc": "轻量快速"},
        ],
    },
    "openai": {
        "label": "OpenAI (ChatGPT)",
        "base_url": "https://api.openai.com/v1",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 16384,
        "url_presets": [
            {"label": "官方 API", "url": "https://api.openai.com/v1"},
        ],
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
        "max_tokens_limit": 8192,
        "url_presets": [
            {"label": "官方 API", "url": "https://api.anthropic.com/v1"},
        ],
        "models": [
            {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "desc": "最强推理，复杂任务首选"},
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "desc": "最佳编码模型，速度与智能平衡"},
            {"id": "claude-haiku-3-5-20241022", "name": "Claude Haiku 3.5", "desc": "最快最便宜，简单任务"},
        ],
    },
    "ollama": {
        "label": "Ollama (本地)",
        "base_url": "http://localhost:11434",
        "chat_path": "/api/chat",
        "needs_api_key": False,
        "max_tokens_limit": 0,
        "url_presets": [
            {"label": "本地默认", "url": "http://localhost:11434"},
        ],
        "models": [],
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 16384,
        "url_presets": [
            {"label": "官方 API", "url": "https://api.deepseek.com"},
        ],
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek V3.2", "desc": "最新旗舰对话模型 (V3.2)，编程能力大幅提升"},
            {"id": "deepseek-reasoner", "name": "DeepSeek R1", "desc": "深度推理模型 (R1)，复杂推理任务首选"},
        ],
    },
    "xiaomimimo": {
        "label": "小米 MiMo",
        "base_url": "https://api.xiaomimimo.com/v1",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 8192,
        "url_presets": [
            {"label": "官方 API", "url": "https://api.xiaomimimo.com/v1"},
            {"label": "Token Plan (套餐)", "url": "https://token-plan-cn.xiaomimimo.com/v1"},
        ],
        "models": [
            {"id": "mimo-v2.5-pro", "name": "MiMo V2.5 Pro", "desc": "Agent/Coding旗舰，100万上下文"},
            {"id": "mimo-v2.5", "name": "MiMo V2.5", "desc": "全模态，100万上下文"},
            {"id": "mimo-v2-pro", "name": "MiMo V2 Pro", "desc": "高性能推理模型"},
            {"id": "mimo-v2-flash", "name": "MiMo V2 Flash", "desc": "开源，混合思考，极速"},
        ],
    },
    "openai_compatible": {
        "label": "OpenAI 兼容",
        "base_url": "",
        "chat_path": "/chat/completions",
        "needs_api_key": True,
        "max_tokens_limit": 0,
        "url_presets": [],
        "models": [],
    },
}


# ──────────────────────────────────────────
# API 协议类型（与供应商无关的通信格式）
# ──────────────────────────────────────────
API_PROTOCOLS = [
    {"code": "openai", "label": "OpenAI Completions", "desc": "OpenAI Chat Completions 格式（绝大多数供应商兼容）"},
    {"code": "openai_responses", "label": "OpenAI Responses", "desc": "OpenAI Responses API 格式"},
    {"code": "anthropic", "label": "Anthropic Messages", "desc": "Anthropic Claude Messages 格式"},
    {"code": "google", "label": "Google Generative AI", "desc": "Google Gemini 格式"},
    {"code": "aws_bedrock", "label": "AWS Bedrock", "desc": "Amazon Bedrock 格式"},
]


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
            "url_presets": cfg.get("url_presets", []),
        })
    return result


def get_api_protocols() -> List[Dict[str, str]]:
    """返回所有 API 协议类型"""
    return API_PROTOCOLS


def get_provider_models(provider: str) -> List[Dict[str, str]]:
    """获取某提供商的模型列表"""
    cfg = PROVIDER_CONFIG.get(provider, {})
    return cfg.get("models", [])


def detect_ollama_models(base_url: str = "http://localhost:11434") -> List[Dict[str, str]]:
    """自动检测 Ollama 本地已安装的模型"""
    models = []
    try:
        url = base_url.rstrip("/") + "/api/tags"
        with httpx.Client(timeout=5) as client:
            resp = client.get(url)
            data = resp.json()
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


def fetch_remote_models(
    base_url: str,
    api_key: str,
    protocol: str = "openai",
) -> List[Dict[str, str]]:
    """用 API Key 从供应商服务器动态获取可用模型列表

    通过 GET {base_url}/models 端点获取模型列表（OpenAI 兼容格式）。
    大多数供应商（智谱、DeepSeek、MiniMax、Qwen、豆包等）都支持此端点。
    """
    url = base_url.rstrip("/")
    models = []

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    if protocol == "anthropic":
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        models_url = url + "/models"
    else:
        # OpenAI 兼容格式（绝大多数供应商）
        models_url = url + "/models"

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(models_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        for item in data.get("data", []):
            model_id = item.get("id", "")
            if model_id:
                models.append({
                    "id": model_id,
                    "name": model_id,
                    "desc": item.get("owned_by", ""),
                })

        models.sort(key=lambda m: m["id"])
    except httpx.HTTPStatusError as e:
        raise Exception(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
    except httpx.ConnectError:
        raise Exception("连接失败，请检查 API 端点地址")
    except httpx.TimeoutException:
        raise Exception("请求超时")
    except Exception as e:
        raise Exception(str(e))

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
        body = {
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
            "options": {"num_predict": 1},
        }
        headers = {"Content-Type": "application/json"}
    elif provider == "anthropic":
        body = {
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    else:
        body = {
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "stream": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    start = time.time()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(full_url, json=body, headers=headers)
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "connected": True,
            "latency_ms": elapsed_ms,
            "model_info": model_name,
            "error": None,
        }
    except httpx.TimeoutException:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "connected": False,
            "latency_ms": elapsed_ms,
            "model_info": model_name,
            "error": f"连接超时（>{timeout}s）",
        }
    except httpx.ConnectError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "connected": False,
            "latency_ms": elapsed_ms,
            "model_info": model_name,
            "error": f"连接失败: {e}",
        }
    except httpx.HTTPStatusError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "connected": False,
            "latency_ms": elapsed_ms,
            "model_info": model_name,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "connected": False,
            "latency_ms": elapsed_ms,
            "model_info": model_name,
            "error": f"异常: {str(e)}",
        }
