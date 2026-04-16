"""AI 配置 + Agent 配置 服务层"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.security import decrypt_key, encrypt_key
from core.ai_provider import test_connection
from db.tables import AIConfig, AgentConfig


# ──────────────────────────────────────────
# AI 配置
# ──────────────────────────────────────────

def list_ai_configs(db: Session) -> List[Dict[str, Any]]:
    rows = db.query(AIConfig).order_by(AIConfig.id).all()
    return [_ai_config_out(r) for r in rows]


def create_ai_config(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    encrypted_key = encrypt_key(data["api_key"])
    obj = AIConfig(
        provider=data["provider"],
        display_name=data["display_name"],
        api_key_encrypted=encrypted_key,
        base_url=data.get("base_url"),
        model_name=data.get("model_name", ""),
        is_default=data.get("is_default", False),
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
        obj.api_key_encrypted = encrypt_key(data["api_key"])
    if "provider" in data:
        obj.provider = data["provider"]
    if "display_name" in data:
        obj.display_name = data["display_name"]
    if "base_url" in data:
        obj.base_url = data["base_url"]
    if "model_name" in data:
        obj.model_name = data["model_name"]
    if "is_default" in data and data["is_default"]:
        _clear_default(db)
        obj.is_default = True
    if "status" in data:
        obj.status = data["status"]

    db.commit()
    db.refresh(obj)
    return _ai_config_out(obj)


def test_ai_connection(db: Session, config_id: int) -> Dict[str, Any]:
    obj = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not obj:
        raise ValueError("AI 配置不存在")
    api_key = decrypt_key(obj.api_key_encrypted)
    return test_connection(
        provider=obj.provider,
        api_key=api_key,
        base_url=obj.base_url,
        model_name=obj.model_name,
    )


def _clear_default(db: Session):
    db.query(AIConfig).filter(AIConfig.is_default == True).update({"is_default": False})


def _ai_config_out(r: AIConfig) -> Dict[str, Any]:
    return {
        "id": r.id,
        "provider": r.provider,
        "display_name": r.display_name,
        "base_url": r.base_url,
        "model_name": r.model_name,
        "is_default": r.is_default,
        "status": r.status,
        "created_at": r.created_at,
    }


# ──────────────────────────────────────────
# Agent 配置
# ──────────────────────────────────────────

def list_agent_configs(db: Session) -> List[Dict[str, Any]]:
    rows = db.query(AgentConfig).order_by(AgentConfig.id).all()
    return [_agent_config_out(r) for r in rows]


def update_agent_config(db: Session, agent_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    obj = db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    if not obj:
        raise ValueError("Agent 配置不存在")
    if "agent_name" in data:
        obj.agent_name = data["agent_name"]
    if "ai_config_id" in data:
        obj.ai_config_id = data["ai_config_id"]
    if "description" in data:
        obj.description = data["description"]
    if "status" in data:
        obj.status = data["status"]
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return _agent_config_out(obj)


def _agent_config_out(r: AgentConfig) -> Dict[str, Any]:
    return {
        "id": r.id,
        "agent_code": r.agent_code,
        "agent_name": r.agent_name,
        "agent_type": r.agent_type,
        "workspace_dir": r.workspace_dir,
        "ai_config_id": r.ai_config_id,
        "description": r.description,
        "status": r.status,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }
