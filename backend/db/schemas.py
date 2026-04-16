"""Pydantic 请求/响应 Schema

基础 Schema 定义，后续 Round 逐步补充。
"""
from datetime import date, datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# 通用响应包装
# ──────────────────────────────────────────
class ResponseBase(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any = None


class PaginationInfo(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0


class PaginatedResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: PaginationInfo


# ──────────────────────────────────────────
# 板块
# ──────────────────────────────────────────
class DivisionCreate(BaseModel):
    name: str = Field(..., max_length=100)
    sort_order: int = 0
    status: str = "enabled"


class DivisionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    status: Optional[str] = None


class DivisionOut(BaseModel):
    id: int
    name: str
    sort_order: Optional[int]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 法人实体
# ──────────────────────────────────────────
class EntityCreate(BaseModel):
    division_id: Optional[int] = None
    entity_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    short_name: str = Field(..., max_length=100)
    status: str = "enabled"


class EntityUpdate(BaseModel):
    division_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=200)
    short_name: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None


class EntityOut(BaseModel):
    id: int
    division_id: Optional[int]
    entity_code: str
    name: str
    short_name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 账户
# ──────────────────────────────────────────
class AccountCreate(BaseModel):
    entity_id: int
    account_code: str = Field(..., max_length=50)
    account_alias: str = Field(..., max_length=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    branch_name: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=100)
    account_type: str = Field(..., max_length=50)
    instrument_type: str = Field(..., max_length=50)
    input_method: str = "manual"
    currency: str = "CNY"
    initial_balance: float = 0
    balance_date: date
    status: str = "enabled"
    notes: Optional[str] = None


class AccountUpdate(BaseModel):
    entity_id: Optional[int] = None
    account_alias: Optional[str] = Field(None, max_length=100)
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    instrument_type: Optional[str] = None
    input_method: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class InitialBalanceSet(BaseModel):
    initial_balance: float
    balance_date: date


class AccountOut(BaseModel):
    id: int
    entity_id: int
    account_code: str
    account_alias: str
    bank_name: Optional[str]
    branch_name: Optional[str]
    account_number: Optional[str]
    account_type: str
    instrument_type: str
    input_method: str
    currency: str
    initial_balance: float
    balance_date: date
    status: str
    notes: Optional[str]
    entity_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 账户别名
# ──────────────────────────────────────────
class AliasCreate(BaseModel):
    alias_text: str = Field(..., max_length=100)
    alias_type: str = Field(..., max_length=50)


class AliasOut(BaseModel):
    id: int
    account_id: int
    alias_text: str
    alias_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountTreeNode(BaseModel):
    id: int
    account_code: str
    account_alias: str
    account_type: str
    status: str
    aliases: List[AliasOut] = []

    model_config = {"from_attributes": True}


class EntityTreeGroup(BaseModel):
    entity_id: int
    entity_name: str
    accounts: List[AccountTreeNode] = []


class PaginatedData(BaseModel):
    items: List[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0


# ──────────────────────────────────────────
# AI 配置
# ──────────────────────────────────────────
class AIConfigCreate(BaseModel):
    provider: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=100)
    api_key_encrypted: str
    base_url: Optional[str] = Field(None, max_length=255)
    model_name: Optional[str] = Field(None, max_length=100)
    is_default: bool = False
    status: str = "active"


class AIConfigUpdate(BaseModel):
    provider: Optional[str] = None
    display_name: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    is_default: Optional[bool] = None
    status: Optional[str] = None


class AIConfigOut(BaseModel):
    id: int
    provider: str
    display_name: str
    api_key_encrypted: str
    base_url: Optional[str]
    model_name: Optional[str]
    is_default: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Agent 配置
# ──────────────────────────────────────────
class AgentConfigCreate(BaseModel):
    agent_code: str = Field(..., max_length=50)
    agent_name: str = Field(..., max_length=100)
    agent_type: str = Field(..., max_length=30)
    workspace_dir: str = Field(..., max_length=200)
    ai_config_id: Optional[int] = None
    description: Optional[str] = None
    status: str = "active"


class AgentConfigOut(BaseModel):
    id: int
    agent_code: str
    agent_name: str
    agent_type: str
    workspace_dir: str
    ai_config_id: Optional[int]
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
