"""AI 配置 API 路由

GET/POST/PUT /api/ai-configs
POST /api/ai-configs/{id}/test
POST /api/ai-configs/fetch-models — 用 API Key 动态获取模型列表
GET /api/ai-providers — 获取所有提供商和模型列表
GET /api/ai-providers/ollama/models — 自动检测 Ollama 本地模型
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from core.response import error, success
from core.ai_provider import get_provider_list, detect_ollama_models, fetch_remote_models, get_api_protocols
from database import get_db
from services import ai_config_service as svc

router = APIRouter()


class AIConfigCreateBody(BaseModel):
    provider: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=100)
    api_key: str
    base_url: Optional[str] = Field(None, max_length=255)
    model_name: str = Field("", max_length=100)
    protocol: str = "openai"
    note: Optional[str] = None
    website_url: Optional[str] = Field(None, max_length=255)
    send_user_agent: bool = False
    is_default: bool = False
    privacy_mode: str = "standard"


class AIConfigUpdateBody(BaseModel):
    provider: Optional[str] = None
    display_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    protocol: Optional[str] = None
    note: Optional[str] = None
    website_url: Optional[str] = None
    send_user_agent: Optional[bool] = None
    is_default: Optional[bool] = None
    privacy_mode: Optional[str] = None
    status: Optional[str] = None


class FetchModelsBody(BaseModel):
    base_url: str
    api_key: str
    protocol: str = "openai"


@router.get("/ai-configs")
def get_ai_configs(db: Session = Depends(get_db)):
    items = svc.list_ai_configs(db)
    return success(items)


@router.post("/ai-configs")
def create_ai_config(body: AIConfigCreateBody, db: Session = Depends(get_db)):
    try:
        result = svc.create_ai_config(db, body.model_dump())
    except ValueError as e:
        return error(2001, str(e))
    return success(result)


@router.put("/ai-configs/{config_id}")
def update_ai_config(
    config_id: int, body: AIConfigUpdateBody, db: Session = Depends(get_db),
):
    try:
        result = svc.update_ai_config(db, config_id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        return error(2001, str(e))
    return success(result)


@router.delete("/ai-configs/{config_id}")
def delete_ai_config(config_id: int, db: Session = Depends(get_db)):
    try:
        result = svc.delete_ai_config(db, config_id)
    except svc.AIConfigInUseError as e:
        return JSONResponse(
            status_code=409,
            content=error(2002, str(e), data={"references": e.references}),
        )
    except ValueError as e:
        return error(2001, str(e))
    return success(result)


@router.post("/ai-configs/{config_id}/test")
def test_ai_connection(config_id: int, db: Session = Depends(get_db)):
    try:
        result = svc.test_ai_connection(db, config_id)
    except ValueError as e:
        return error(2001, str(e))
    if not result.get("connected"):
        return error(5001, result.get("error", "连接失败"), data=result)
    return success(result)


@router.post("/ai-configs/fetch-models")
def fetch_models(body: FetchModelsBody):
    """用 API Key 动态从供应商获取可用模型列表"""
    try:
        models = fetch_remote_models(
            base_url=body.base_url,
            api_key=body.api_key,
            protocol=body.protocol,
        )
        return success(models)
    except Exception as e:
        return error(5001, f"获取模型列表失败: {str(e)}")


@router.get("/ai-providers")
def list_providers():
    """返回所有支持的 AI 提供商及其模型列表"""
    return success(get_provider_list())


@router.get("/api-protocols")
def list_protocols():
    """返回所有 API 协议类型"""
    return success(get_api_protocols())


@router.get("/ai-providers/ollama/models")
def detect_ollama():
    """自动检测本地 Ollama 已安装的模型"""
    models = detect_ollama_models()
    return success(models)


@router.get("/ai-call-logs")
def get_ai_call_logs(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return success(svc.list_ai_call_logs(db, limit=limit))
