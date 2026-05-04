"""AI 配置服务层"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.security import decrypt_key, encrypt_key
from core.ai_provider import test_connection
from core.privacy_pipeline import validate_privacy_mode
from db.tables import AICallLog, AIConfig


# ──────────────────────────────────────────
# AI 配置
# ──────────────────────────────────────────

def list_ai_configs(db: Session) -> List[Dict[str, Any]]:
    rows = db.query(AIConfig).order_by(AIConfig.id).all()
    return [_ai_config_out(r) for r in rows]


def create_ai_config(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    local_key = encrypt_key(data.get("api_key", ""))
    obj = AIConfig(
        provider=data.get("provider", ""),
        display_name=data["display_name"],
        api_key_local=local_key,
        base_url=data.get("base_url"),
        model_name=data.get("model_name", ""),
        protocol=data.get("protocol", "openai"),
        note=data.get("note"),
        website_url=data.get("website_url"),
        send_user_agent=data.get("send_user_agent", False),
        is_default=data.get("is_default", False),
        privacy_mode=validate_privacy_mode(data.get("privacy_mode")),
        status="active",
    )
    if obj.is_default:
        _clear_default(db)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _ai_config_out(obj)


def update_ai_config(db: Session, config_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    obj = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not obj:
        raise ValueError("AI 配置不存在")

    if "api_key" in data and data["api_key"]:
        obj.api_key_local = encrypt_key(data["api_key"])
    if "provider" in data:
        obj.provider = data["provider"]
    if "display_name" in data:
        obj.display_name = data["display_name"]
    if "base_url" in data:
        obj.base_url = data["base_url"]
    if "model_name" in data:
        obj.model_name = data["model_name"]
    if "protocol" in data:
        obj.protocol = data["protocol"]
    if "note" in data:
        obj.note = data["note"]
    if "website_url" in data:
        obj.website_url = data["website_url"]
    if "send_user_agent" in data:
        obj.send_user_agent = data["send_user_agent"]
    if "is_default" in data and data["is_default"]:
        _clear_default(db)
        obj.is_default = True
    if "privacy_mode" in data:
        obj.privacy_mode = validate_privacy_mode(data.get("privacy_mode"))
    if "status" in data:
        obj.status = data["status"]

    db.commit()
    db.refresh(obj)
    return _ai_config_out(obj)


def delete_ai_config(db: Session, config_id: int) -> Dict[str, Any]:
    obj = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not obj:
        raise ValueError("AI 配置不存在")
    if obj.is_default:
        raise ValueError("默认 AI 配置不能删除，请先设置其他配置为默认")

    db.delete(obj)
    db.commit()
    return {"deleted_id": config_id}


def test_ai_connection(db: Session, config_id: int) -> Dict[str, Any]:
    obj = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not obj:
        raise ValueError("AI 配置不存在")
    api_key = decrypt_key(obj.api_key_local)
    return test_connection(
        provider=obj.provider,
        api_key=api_key,
        base_url=obj.base_url,
        model_name=obj.model_name,
    )


def list_ai_call_logs(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    rows = (
        db.query(AICallLog)
        .order_by(AICallLog.created_at.desc(), AICallLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "model": r.model,
            "endpoint": r.endpoint,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "request_size": r.request_size,
            "response_size": r.response_size,
            "error_code": r.error_code,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def _clear_default(db: Session):
    db.query(AIConfig).filter(AIConfig.is_default == True).update({"is_default": False})


def _ai_config_out(r: AIConfig) -> Dict[str, Any]:
    return {
        "id": r.id,
        "provider": r.provider,
        "display_name": r.display_name,
        "base_url": r.base_url,
        "model_name": r.model_name,
        "protocol": r.protocol,
        "note": r.note,
        "website_url": r.website_url,
        "send_user_agent": r.send_user_agent,
        "is_default": r.is_default,
        "privacy_mode": r.privacy_mode,
        "status": r.status,
        "created_at": r.created_at,
    }
