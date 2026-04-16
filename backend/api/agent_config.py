"""Agent 配置 API 路由

GET /api/agent-configs
PUT /api/agent-configs/{id}
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from core.response import error, success
from database import get_db
from services import ai_config_service as svc

router = APIRouter()


class AgentConfigUpdateBody(BaseModel):
    agent_name: Optional[str] = Field(None, max_length=100)
    ai_config_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None


@router.get("/agent-configs")
def get_agent_configs(db: Session = Depends(get_db)):
    items = svc.list_agent_configs(db)
    return success(items)


@router.put("/agent-configs/{agent_id}")
def update_agent_config(
    agent_id: int, body: AgentConfigUpdateBody, db: Session = Depends(get_db),
):
    try:
        result = svc.update_agent_config(db, agent_id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        return error(2001, str(e))
    return success(result)
