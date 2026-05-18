"""Pydantic 请求/响应 Schema

基础 Schema 定义，后续 Round 逐步补充。
"""
from datetime import date, datetime
from enum import Enum
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
    division_code: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., max_length=100)
    sort_order: int = 0
    status: str = "enabled"


class DivisionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    status: Optional[str] = None


class DivisionOut(BaseModel):
    id: int
    division_code: Optional[str] = None
    name: str
    sort_order: Optional[int]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 通用状态切换
# ──────────────────────────────────────────
class StatusToggle(BaseModel):
    status: str  # "enabled" 或 "disabled"


# ──────────────────────────────────────────
# 法人实体
# ──────────────────────────────────────────
class EntityCreate(BaseModel):
    division_id: Optional[int] = None
    entity_code: Optional[str] = Field(None, max_length=50)
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
# 银行
# ──────────────────────────────────────────
class BankCreate(BaseModel):
    bank_code: Optional[str] = Field(None, max_length=50)
    bank_name: str = Field(..., max_length=100)
    short_name: Optional[str] = Field(None, max_length=50)
    cnaps_code: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    status: str = "enabled"
    sort_order: int = 0


class BankUpdate(BaseModel):
    bank_name: Optional[str] = None
    short_name: Optional[str] = None
    cnaps_code: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None


class BankOut(BaseModel):
    id: int
    bank_code: str
    bank_name: str
    short_name: Optional[str]
    cnaps_code: Optional[str]
    contact_phone: Optional[str]
    website: Optional[str]
    notes: Optional[str]
    status: str
    sort_order: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 账户
# ──────────────────────────────────────────
class AccountCreate(BaseModel):
    entity_id: int
    account_code: Optional[str] = Field(None, max_length=50)
    account_alias: Optional[str] = Field(None, max_length=100)
    bank_id: Optional[int] = None
    bank_name: Optional[str] = Field(None, max_length=100)
    branch_name: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=100)
    account_last_four: Optional[str] = None
    account_type: str = Field(..., max_length=50)
    instrument_type: str = Field(..., max_length=50)
    input_method: str = "manual"
    has_online_banking: bool = False
    include_in_daily_report: bool = True
    allow_manual_entry: bool = True
    currency: str = "CNY"
    initial_balance: float = 0
    balance_date: Optional[date] = None
    status: str = "enabled"
    notes: Optional[str] = None


class AccountUpdate(BaseModel):
    entity_id: Optional[int] = None
    account_alias: Optional[str] = Field(None, max_length=100)
    bank_id: Optional[int] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    account_number: Optional[str] = None
    account_last_four: Optional[str] = None
    account_type: Optional[str] = None
    instrument_type: Optional[str] = None
    input_method: Optional[str] = None
    has_online_banking: Optional[bool] = None
    include_in_daily_report: Optional[bool] = None
    allow_manual_entry: Optional[bool] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class InitialBalanceSet(BaseModel):
    initial_balance: float
    balance_date: date


class AccountOut(BaseModel):
    id: int
    entity_id: int
    bank_id: Optional[int] = None
    account_code: str
    account_alias: str
    bank_name: Optional[str]
    branch_name: Optional[str]
    account_number: Optional[str]
    account_last_four: Optional[str] = None
    account_type: str
    instrument_type: str
    input_method: str
    has_online_banking: bool = False
    include_in_daily_report: bool = True
    allow_manual_entry: bool = True
    currency: str
    initial_balance: float
    balance_date: date
    status: str
    notes: Optional[str]
    entity_name: Optional[str] = None
    bank_short_name: Optional[str] = None
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
    entity_full_name: str
    entity_short_name: str
    entity_display_name: str
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
    api_key_local: str
    base_url: Optional[str] = Field(None, max_length=255)
    model_name: Optional[str] = Field(None, max_length=100)
    is_default: bool = False
    privacy_mode: str = "standard"
    status: str = "active"


class AIConfigUpdate(BaseModel):
    provider: Optional[str] = None
    display_name: Optional[str] = None
    api_key_local: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    is_default: Optional[bool] = None
    privacy_mode: Optional[str] = None
    status: Optional[str] = None


class AIConfigOut(BaseModel):
    id: int
    provider: str
    display_name: str
    api_key_local: str
    base_url: Optional[str]
    model_name: Optional[str]
    is_default: bool
    privacy_mode: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 手工流水 — 字段池
# ──────────────────────────────────────────
class ManualFieldPoolOut(BaseModel):
    id: int
    field_code: str
    field_name_cn: str
    data_type: str
    is_core: bool
    is_default_visible: bool
    is_disable_allowed: bool
    is_parse_key: bool
    is_validation_key: bool
    is_batch_inheritable: bool
    options_json: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 手工流水 — 方案
# ──────────────────────────────────────────
class ManualSchemeCreate(BaseModel):
    scheme_code: str = Field(..., max_length=50)
    scheme_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    selected_fields: List[str]
    is_default: bool = False


class ManualSchemeUpdate(BaseModel):
    scheme_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    selected_fields: Optional[List[str]] = None
    is_default: Optional[bool] = None
    status: Optional[str] = None


class ManualSchemeOut(BaseModel):
    id: int
    scheme_code: str
    scheme_name: str
    description: Optional[str]
    selected_fields: List[str]
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 手工流水 — 快速录入
# ──────────────────────────────────────────
class QuickEntryRow(BaseModel):
    entity_match_key: str = ""
    account_match_key: str = ""
    business_date: str = ""
    summary_text: str = ""
    counterparty_name: str = ""
    income_amount: Optional[float] = None
    expense_amount: Optional[float] = None
    previous_balance_input: Optional[float] = None
    ending_balance_input: Optional[float] = None
    business_time: Optional[str] = None
    department_name: Optional[str] = None
    income_expense_type: Optional[str] = None
    handler_name: Optional[str] = None
    owner_name: Optional[str] = None
    note_text: Optional[str] = None
    pending_recovery_flag: Optional[bool] = None
    voucher_no: Optional[str] = None
    receipt_no: Optional[str] = None

    @classmethod
    def _coerce_empty_to_none(cls, v):
        if v == "" or v == " ":
            return None
        return v

    def __init__(self, **data):
        for field in ("income_amount", "expense_amount", "previous_balance_input", "ending_balance_input"):
            if field in data and isinstance(data[field], str):
                data[field] = self._coerce_empty_to_none(data[field])
        for field in ("pending_recovery_flag",):
            if field in data and isinstance(data[field], str):
                val = data[field].strip().lower()
                data[field] = True if val in ("true", "1", "yes") else (False if val in ("false", "0", "no") else None)
        super().__init__(**data)


class QuickEntrySave(BaseModel):
    scheme_code: str = "manual_multi_subject_basic"
    rows: List[QuickEntryRow]


# ──────────────────────────────────────────
# 手工流水 — 上传/预览/提交/导出
# ──────────────────────────────────────────
class ManualPreviewBody(BaseModel):
    batch_code: str
    scheme_code: Optional[str] = None


class ManualExportTemplateBody(BaseModel):
    scheme_code: str = "manual_multi_subject_basic"
    include_example_rows: bool = False


# ──────────────────────────────────────────
# 基础数据查询
# ──────────────────────────────────────────
class BaseDataRowOut(BaseModel):
    id: int
    business_date: Optional[str] = None
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    direction: Optional[str] = None
    income_amount: Optional[float] = None
    expense_amount: Optional[float] = None
    rolling_balance: Optional[float] = None
    counterparty_name: Optional[str] = None
    summary_text: Optional[str] = None
    abnormal_code: Optional[str] = None


class RebuildResult(BaseModel):
    affected_accounts: int = 0
    updated_events: int = 0


# ──────────────────────────────────────────
# 报表输出
# ──────────────────────────────────────────
class DailyReportEntityRow(BaseModel):
    entity_id: Optional[int] = None
    entity_name: str = ""
    opening_balance: float = 0
    total_income: float = 0
    total_expense: float = 0
    net_change: float = 0
    ending_balance: float = 0


class CashJournalDayRow(BaseModel):
    business_date: str = ""
    prev_balance: float = 0
    income: float = 0
    expense: float = 0
    day_balance: float = 0


class CashJournalAccountBlock(BaseModel):
    account_id: Optional[int] = None
    account_name: str = ""
    entity_name: str = ""
    rows: List[CashJournalDayRow] = []


class AccountBalanceRow(BaseModel):
    entity_id: int
    entity_name: str
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    opening_balance: float = 0
    period_income: float = 0
    period_expense: float = 0
    ending_balance: float = 0
    is_subtotal: bool = False


# ──────────────────────────────────────────
# 报表模板
# ──────────────────────────────────────────
REPORT_TYPES = [
    {"code": "base_data", "name": "基础数据表"},
    {"code": "cash_journal", "name": "现金日记账"},
    {"code": "account_balance", "name": "账户余额表"},
    {"code": "income_list", "name": "收入明细表"},
    {"code": "expense_list", "name": "支出明细表"},
    {"code": "major_balance", "name": "主要账户余额表"},
    {"code": "month_check", "name": "月末盘点表"},
    {"code": "week_report", "name": "资金周报"},
    {"code": "month_report", "name": "资金月报"},
    {"code": "year_report", "name": "资金年报"},
]


class ColumnConfig(BaseModel):
    field_key: str
    header_name: str
    width: int = 100
    align: str = "left"
    visible: bool = True
    format: Optional[str] = None
    sort_order: int = 0


class ReportTemplateCreate(BaseModel):
    template_code: Optional[str] = Field(None, max_length=50)
    template_name: str = Field(..., max_length=100)
    report_type: str = Field(..., max_length=30)
    columns: List[ColumnConfig]
    group_by: Optional[str] = None
    is_default: bool = False
    remark: Optional[str] = None


class ReportTemplateUpdate(BaseModel):
    template_name: Optional[str] = Field(None, max_length=100)
    columns: Optional[List[ColumnConfig]] = None
    group_by: Optional[str] = None
    is_default: Optional[bool] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class ReportTemplateOut(BaseModel):
    id: int
    template_code: str
    template_name: str
    report_type: str
    columns: List[ColumnConfig]
    group_by: Optional[str] = None
    is_default: bool
    status: str
    created_by: str
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Artifact 枚举
# ──────────────────────────────────────────

class ArtifactKind(str, Enum):
    bank = "bank"
    manual = "manual"


class ArtifactDBStatus(str, Enum):
    draft = "draft"
    active = "active"
    retired = "retired"


class InferenceJobStatus(str, Enum):
    pending = "pending"
    reviewed = "reviewed"
    approved = "approved"
    rejected = "rejected"


# ──────────────────────────────────────────
# Artifact 请求
# ──────────────────────────────────────────

class ParserArtifactDraftCreate(BaseModel):
    name: str = Field(..., max_length=100)
    kind: ArtifactKind
    account_code: Optional[str] = Field(None, max_length=50)
    bank_id: Optional[int] = None
    format_key: Optional[str] = Field(None, max_length=100)
    match_rules: dict = {}
    code: str
    primitives_imports: list[str]
    sample_check_log: dict = {}
    confidence: Optional[float] = None
    created_by: str = "agent"


class RuleArtifactDraftCreate(BaseModel):
    name: str = Field(..., max_length=100)
    template_id: Optional[int] = None
    placeholder_bindings: dict
    loop_config: Optional[dict] = None
    primitives_imports: list[str]
    sample_check_log: dict = {}
    confidence: Optional[float] = None
    created_by: str = "agent"


class ArtifactReviewRequest(BaseModel):
    reviewer: str = "admin"
    reason: Optional[str] = None


# ──────────────────────────────────────────
# Artifact 响应
# ──────────────────────────────────────────

class ParserArtifactResponse(BaseModel):
    id: int
    name: str
    kind: str
    account_code: Optional[str] = None
    bank_id: Optional[int] = None
    format_key: Optional[str] = None
    match_rules: dict = {}
    version: int
    status: str
    code: Optional[str] = None
    primitives_imports: list
    sample_check_log: dict
    confidence: Optional[float] = None
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


class RuleArtifactResponse(BaseModel):
    id: int
    name: str
    template_id: Optional[int] = None
    version: int
    status: str
    placeholder_bindings: Optional[dict] = None
    loop_config: Optional[dict] = None
    primitives_imports: list
    sample_check_log: dict
    confidence: Optional[float] = None
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


class TemplateInferenceJobResponse(BaseModel):
    id: int
    template_file: Optional[str] = None
    original_filename: Optional[str] = None
    stage: Optional[str] = None
    status: str
    stage_a_output: Optional[dict] = None
    stage_b_output: Optional[dict] = None
    stage_c_decision: Optional[str] = None
    rule_artifact_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ──────────────────────────────────────────
# Template analysis & field mapping
# ──────────────────────────────────────────

class TemplateAnalysisRequest(BaseModel):
    template_file: str = Field(..., description="模板文件路径")


class PlaceholderBindingItem(BaseModel):
    primitive: str = Field(default="const", description="基元类型: field / const")
    value: Optional[str] = None


class TemplateAnalysisResponse(BaseModel):
    placeholders: list[str] = Field(default_factory=list)
    merged_cells: list[dict] = Field(default_factory=list)
    header_rows: list[int] = Field(default_factory=list)


class FieldMappingResponse(BaseModel):
    placeholder_bindings: dict[str, PlaceholderBindingItem] = Field(default_factory=dict)
    confidence: float = 0.0
    matched_count: int = 0
    total_placeholders: int = 0


class ArtifactVersionQuery(BaseModel):
    name: str = Field(..., max_length=100)
    kind: Optional[str] = None


# ──────────────────────────────────────────
# Artifact Runtime input / output
# ──────────────────────────────────────────

class ParserRuntimeRow(BaseModel):
    """CANONICAL_12 — 每一行的标准输出格式。"""
    business_date: Optional[str] = None
    entity_code: str = ""
    entity_name: str = ""
    account_code: str = ""
    account_name: str = ""
    summary: str = ""
    counterparty: str = ""
    amount_in: float = 0.0
    amount_out: float = 0.0
    rolling_balance: Optional[float] = None
    state: str = "正常"
    source: str = ""


class ParserRuntimeInput(BaseModel):
    artifact_id: int
    file_path: str
    ctx: dict = {}


class ParserRuntimeResult(BaseModel):
    rows: list[ParserRuntimeRow] = []
    row_count: int = 0
    warnings: list[str] = []
    errors: list[str] = []


class RuleRuntimeInput(BaseModel):
    artifact_id: int
    ctx: dict = {}
    template_path: str = ""


class RuleRuntimeResult(BaseModel):
    output_path: Optional[str] = None
    placeholder_filled: int = 0
    warnings: list[str] = []
    errors: list[str] = []


class WorkflowStatus(str, Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class WorkflowRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    paused = "paused"
    cancelled = "cancelled"


class WorkflowCreate(BaseModel):
    workflow_code: str = Field(..., max_length=80)
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    graph: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "agent"


class WorkflowMetadataUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None


class WorkflowPatchRequest(BaseModel):
    patches: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str = "agent"
    change_summary: Optional[str] = None


class WorkflowRunCreate(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class WorkflowValidateRequest(BaseModel):
    graph_json: Optional[dict[str, Any]] = None


class WorkflowVersionResponse(BaseModel):
    id: int
    workflow_id: int
    version: int
    graph: dict[str, Any]
    change_summary: Optional[str] = None
    created_by: str
    created_at: Optional[str] = None


class WorkflowResponse(BaseModel):
    id: int
    workflow_code: str
    name: str
    description: Optional[str] = None
    status: str
    current_version: Optional[WorkflowVersionResponse] = None
    created_by: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkflowRunStepResponse(BaseModel):
    id: int
    run_id: int
    node_id: str
    node_type: str
    status: str
    input: dict[str, Any]
    output: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class WorkflowRunResponse(BaseModel):
    id: int
    workflow_id: int
    workflow_version_id: Optional[int] = None
    workflow_code: str
    workflow_version: int
    status: str
    input: dict[str, Any]
    output: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    steps: list[WorkflowRunStepResponse] = Field(default_factory=list)
