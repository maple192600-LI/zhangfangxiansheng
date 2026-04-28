"""数据库 ORM 表定义。

严格按照 docs/30_contracts/20_database_schema.md 定义。
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, Date, DateTime,
    ForeignKey, Index, CheckConstraint, JSON
)
from sqlalchemy.orm import relationship
from database import Base


# ──────────────────────────────────────────
# 1. divisions — 板块
# ──────────────────────────────────────────
class Division(Base):
    __tablename__ = "divisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    division_code = Column(String(50), nullable=True, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    sort_order = Column(Integer, nullable=True, default=0)
    status = Column(String(20), nullable=False, default="enabled")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    entities = relationship("Entity", back_populates="division")


# ──────────────────────────────────────────
# 2. entities — 法人实体
# ──────────────────────────────────────────
class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    division_id = Column(Integer, ForeignKey("divisions.id", ondelete="SET NULL"), nullable=True)
    entity_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="enabled")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    division = relationship("Division", back_populates="entities")
    accounts = relationship("Account", back_populates="entity")
    fund_events = relationship("FundEvent", back_populates="entity")

    __table_args__ = (Index("idx_entities_division", "division_id"),)


# ──────────────────────────────────────────
# 2.5 banks — 银行
# ──────────────────────────────────────────
class Bank(Base):
    __tablename__ = "banks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_code = Column(String(50), nullable=False, unique=True)
    bank_name = Column(String(100), nullable=False, unique=True)
    short_name = Column(String(50), nullable=True)
    cnaps_code = Column(String(20), nullable=True)
    contact_phone = Column(String(30), nullable=True)
    website = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="enabled")
    sort_order = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    accounts = relationship("Account", back_populates="bank")

    __table_args__ = (Index("idx_banks_status", "status"),)


# ──────────────────────────────────────────
# 3. accounts — 账户
# ──────────────────────────────────────────
class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False)
    bank_id = Column(Integer, ForeignKey("banks.id", ondelete="SET NULL"), nullable=True)
    account_code = Column(String(50), nullable=False, unique=True)
    account_alias = Column(String(100), nullable=False)
    bank_name = Column(String(100), nullable=True)
    branch_name = Column(String(200), nullable=True)
    account_number = Column(String(100), nullable=True)
    account_last_four = Column(String(10), nullable=True)
    account_type = Column(String(50), nullable=False)
    instrument_type = Column(String(50), nullable=False)
    input_method = Column(String(50), nullable=False, default="manual")
    has_online_banking = Column(Boolean, nullable=False, default=False)
    include_in_daily_report = Column(Boolean, nullable=False, default=True)
    allow_manual_entry = Column(Boolean, nullable=False, default=True)
    currency = Column(String(20), nullable=False, default="CNY")
    initial_balance = Column(Numeric(18, 2), nullable=False, default=0)
    balance_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="enabled")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    entity = relationship("Entity", back_populates="accounts")
    bank = relationship("Bank", back_populates="accounts")
    aliases = relationship("AccountAlias", back_populates="account", cascade="all, delete-orphan")
    fund_events = relationship("FundEvent", back_populates="account")

    __table_args__ = (Index("idx_accounts_entity", "entity_id"),)


# ──────────────────────────────────────────
# 4. account_aliases — 账户别名
# ──────────────────────────────────────────
class AccountAlias(Base):
    __tablename__ = "account_aliases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    alias_text = Column(String(100), nullable=False)
    alias_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    account = relationship("Account", back_populates="aliases")

    __table_args__ = (
        Index("idx_account_aliases_account", "account_id"),
        Index("idx_account_aliases_text", "alias_text"),
    )


# ──────────────────────────────────────────
# 5. parser_templates — 已生效模板列表
# ──────────────────────────────────────────
class ParserTemplate(Base):
    __tablename__ = "parser_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String(100), nullable=False)
    template_type = Column(String(30), nullable=False)
    file_format = Column(String(20), nullable=False)
    header_row = Column(Integer, nullable=False)
    skip_rows = Column(Integer, nullable=False, default=0)
    sample_headers = Column(Text, nullable=False)
    mapping_json = Column(Text, nullable=False)
    created_by = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (Index("idx_parser_templates_type", "template_type", "status"),)


# ──────────────────────────────────────────
# 6. manual_field_pool — 手工字段池
# ──────────────────────────────────────────
class ManualFieldPool(Base):
    __tablename__ = "manual_field_pool"
    id = Column(Integer, primary_key=True, autoincrement=True)
    field_code = Column(String(50), nullable=False, unique=True)
    field_name_cn = Column(String(100), nullable=False)
    data_type = Column(String(30), nullable=False)
    is_core = Column(Boolean, nullable=False, default=False)
    is_default_visible = Column(Boolean, nullable=False, default=True)
    is_disable_allowed = Column(Boolean, nullable=False, default=True)
    is_parse_key = Column(Boolean, nullable=False, default=False)
    is_validation_key = Column(Boolean, nullable=False, default=False)
    is_batch_inheritable = Column(Boolean, nullable=False, default=False)
    options_json = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


# ──────────────────────────────────────────
# 7. manual_template_schemes — 手工模板方案
# ──────────────────────────────────────────
class ManualTemplateScheme(Base):
    __tablename__ = "manual_template_schemes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme_code = Column(String(50), nullable=False, unique=True)
    scheme_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    selected_fields_json = Column(Text, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


# ──────────────────────────────────────────
# 8. import_batches — 导入批次
# ──────────────────────────────────────────
class ImportBatch(Base):
    __tablename__ = "import_batches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_code = Column(String(50), nullable=False, unique=True)
    source_type = Column(String(30), nullable=False)
    source_name = Column(String(200), nullable=True)
    status = Column(String(30), nullable=False, default="uploaded")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    fund_events = relationship("FundEvent", back_populates="batch")

    __table_args__ = (
        Index("idx_import_batches_status", "status"),
        Index("idx_import_batches_source", "source_type"),
    )


# ──────────────────────────────────────────
# 9. fund_events — 资金流水事实表（CANONICAL_12）
# ──────────────────────────────────────────
class FundEvent(Base):
    __tablename__ = "fund_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_date = Column(Date, nullable=False)
    entity_code = Column(String(50), ForeignKey("entities.entity_code"), nullable=False)
    entity_name = Column(String(200), nullable=False)
    account_code = Column(String(50), ForeignKey("accounts.account_code"), nullable=False)
    account_name = Column(String(100), nullable=False)
    summary = Column(String(500), nullable=True)
    counterparty = Column(String(200), nullable=True)
    amount_in = Column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    amount_out = Column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    rolling_balance = Column(Numeric(18, 2), nullable=True)
    state = Column(String(20), nullable=False, default="正常", server_default="正常")
    source = Column(String(20), nullable=False)
    batch_id = Column(Integer, ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=True)
    parser_artifact_id = Column(Integer, ForeignKey("parser_artifacts.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)

    batch = relationship("ImportBatch", back_populates="fund_events")
    entity = relationship("Entity", back_populates="fund_events")
    account = relationship("Account", back_populates="fund_events")
    parser_artifact = relationship("ParserArtifact", back_populates="fund_events")

    __table_args__ = (
        CheckConstraint("NOT (amount_in > 0 AND amount_out > 0)", name="ck_fund_events_amount_mutex"),
        CheckConstraint("amount_in >= 0 AND amount_out >= 0", name="ck_fund_events_amount_nonneg"),
        CheckConstraint("state IN ('正常','待确认','异常','已作废')", name="ck_fund_events_state_enum"),
        CheckConstraint(
            "source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据')",
            name="ck_fund_events_source_enum",
        ),
        Index("idx_fund_events_date_account", "business_date", "account_code"),
        Index("idx_fund_events_state", "state"),
        Index("idx_fund_events_batch", "batch_id"),
    )


# ──────────────────────────────────────────
# 9.1 parser_artifacts — Fund Agent Parser 产物
# ──────────────────────────────────────────
class ParserArtifact(Base):
    __tablename__ = "parser_artifacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    kind = Column(String(20), nullable=False)
    account_code = Column(String(50), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    status = Column(String(20), nullable=False, default="draft", server_default="draft")
    code = Column(Text, nullable=False)
    primitives_imports = Column(JSON, nullable=False)
    sample_check_log = Column(JSON, nullable=False, default=dict, server_default="{}")
    confidence = Column(Numeric(5, 4), nullable=True)
    created_by = Column(String(50), nullable=False, default="agent", server_default="agent")
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)

    fund_events = relationship("FundEvent", back_populates="parser_artifact")

    __table_args__ = (
        CheckConstraint("kind IN ('bank','manual')", name="ck_parser_artifacts_kind"),
        CheckConstraint("status IN ('draft','active','retired')", name="ck_parser_artifacts_status"),
        Index("uq_parser_artifacts_name_version", "name", "version", unique=True),
        Index("idx_parser_artifacts_account", "account_code", "status"),
        Index("idx_parser_artifacts_kind", "kind", "status"),
    )


# ──────────────────────────────────────────
# 9.2 rule_artifacts — Fund Agent Rule 产物
# ──────────────────────────────────────────
class RuleArtifact(Base):
    __tablename__ = "rule_artifacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    status = Column(String(20), nullable=False, default="draft", server_default="draft")
    placeholder_bindings = Column(JSON, nullable=False)
    loop_spec = Column(JSON, nullable=True)
    loop_config = Column(JSON, nullable=True)
    primitives_imports = Column(JSON, nullable=False)
    sample_check_log = Column(JSON, nullable=False, default=dict, server_default="{}")
    confidence = Column(Numeric(5, 4), nullable=True)
    created_by = Column(String(50), nullable=False, default="agent", server_default="agent")
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)

    template = relationship("ReportTemplate")
    inference_jobs = relationship("TemplateInferenceJob", back_populates="rule_artifact")

    __table_args__ = (
        CheckConstraint("status IN ('draft','active','retired')", name="ck_rule_artifacts_status"),
        Index("idx_rule_artifacts_template", "template_id", "status"),
    )


# ──────────────────────────────────────────
# 9.3 template_inference_job — 模板推断任务
# ──────────────────────────────────────────
class TemplateInferenceJob(Base):
    __tablename__ = "template_inference_job"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_file = Column(String(255), nullable=True)
    original_filename = Column(String(300), nullable=True)
    file_path = Column(String(500), nullable=True)
    stage = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="pending", server_default="pending")
    stage_a_output = Column(JSON, nullable=True)
    stage_b_output = Column(JSON, nullable=True)
    stage_c_decision = Column(String(20), nullable=True)
    rule_artifact_id = Column(Integer, ForeignKey("rule_artifacts.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)

    rule_artifact = relationship("RuleArtifact", back_populates="inference_jobs")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','reviewed','approved','rejected')",
            name="ck_template_inference_job_status",
        ),
    )


# ──────────────────────────────────────────
# 10. daily_report_runs — 日报生成记录
# ──────────────────────────────────────────
class DailyReportRun(Base):
    __tablename__ = "daily_report_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_code = Column(String(50), nullable=False, unique=True)
    report_name = Column(String(200), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="draft")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (Index("idx_daily_report_runs_dates", "start_date", "end_date"),)


# ──────────────────────────────────────────
# 11. ai_configs — AI 配置
# ──────────────────────────────────────────
class AIConfig(Base):
    __tablename__ = "ai_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    api_key_local = Column(Text, nullable=False)
    base_url = Column(String(255), nullable=True)
    model_name = Column(String(100), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    privacy_mode = Column(String(20), nullable=False, default="standard")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)



# ──────────────────────────────────────────
# 11.5 ai_call_logs — AI 调用审计日志
# ──────────────────────────────────────────
class AICallLog(Base):
    __tablename__ = "ai_call_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=True)
    endpoint = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False)
    duration_ms = Column(Integer, nullable=False, default=0)
    request_size = Column(Integer, nullable=False, default=0)
    response_size = Column(Integer, nullable=False, default=0)
    error_code = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (Index("idx_ai_call_logs_created", "created_at"),)


# ──────────────────────────────────────────
# 12. operation_logs — 操作日志 (旧编号 13)
# ──────────────────────────────────────────
class OperationLog(Base):
    __tablename__ = "operation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50), nullable=False)
    module = Column(String(50), nullable=False)
    batch_id = Column(Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True)
    detail_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        Index("idx_operation_logs_module", "module", "created_at"),
        Index("idx_operation_logs_batch", "batch_id"),
    )


# ──────────────────────────────────────────
# 14. users — 用户（单用户认证）
# ──────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    must_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


# ──────────────────────────────────────────
# 15. report_templates — 报表模板
# ──────────────────────────────────────────
class ReportTemplate(Base):
    __tablename__ = "report_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_code = Column(String(50), nullable=False, unique=True)
    template_name = Column(String(100), nullable=False)
    report_type = Column(String(30), nullable=False)
    columns_json = Column(Text, nullable=False)
    layout_json = Column(Text, nullable=True)       # 完整Excel布局：标题/信息区/表头/数据模板/汇总
    source_file_path = Column(String(500), nullable=True)  # 上传的原 Excel 文件路径，用于完整渲染
    group_by = Column(String(50), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="active")
    created_by = Column(String(30), nullable=False, default="admin")
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_report_templates_type", "report_type", "status"),
        Index("idx_report_templates_default", "report_type", "is_default"),
    )


# ──────────────────────────────────────────
# 16. agents_v2 — AI 智能体（v2）
# ──────────────────────────────────────────
class AgentV2(Base):
    __tablename__ = "agents_v2"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_code = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    role_prompt = Column(Text, nullable=False, default="")
    ai_config_id = Column(Integer, ForeignKey("ai_configs.id", ondelete="SET NULL"), nullable=True)
    workspace_path = Column(String(500), nullable=False)
    llm_timeout = Column(Integer, nullable=False, default=300, server_default="300")
    llm_max_tokens = Column(Integer, nullable=False, default=4096, server_default="4096")
    permission_json = Column(Text, nullable=False, default="{}")
    status = Column(String(20), nullable=False, default="active")
    sort_order = Column(Integer, nullable=False, default=0)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    ai_config = relationship("AIConfig")
    sessions = relationship("AgentSession", back_populates="agent", order_by="AgentSession.last_active_at.desc()", passive_deletes=True)
    skills = relationship("SkillV2", back_populates="owner_agent", passive_deletes=True)
    memories = relationship("AgentMemory", back_populates="agent", passive_deletes=True)

    __table_args__ = (Index("idx_agents_v2_status", "status"),)


# ──────────────────────────────────────────
# 17. skills_v2 — 技能
# ──────────────────────────────────────────
class SkillV2(Base):
    __tablename__ = "skills_v2"
    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_code = Column(String(80), nullable=False, unique=True)
    display_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    owner_agent_id = Column(Integer, ForeignKey("agents_v2.id", ondelete="SET NULL"), nullable=True)
    manifest_json = Column(Text, nullable=False, default="{}")
    source_path = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    verified_at = Column(DateTime, nullable=True)
    test_pass_count = Column(Integer, nullable=False, default=0)
    test_fail_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    owner_agent = relationship("AgentV2", back_populates="skills")

    __table_args__ = (Index("idx_skills_v2_status", "status"),)


# ──────────────────────────────────────────
# 18. agent_sessions — 会话
# ──────────────────────────────────────────
class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents_v2.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=True)
    context_summary = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    last_active_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    agent = relationship("AgentV2", back_populates="sessions")
    messages = relationship("AgentMessage", back_populates="session", order_by="AgentMessage.id")

    __table_args__ = (Index("idx_agent_sessions_agent", "agent_id"),)


# ──────────────────────────────────────────
# 19. agent_messages — 消息
# ──────────────────────────────────────────
class AgentMessage(Base):
    __tablename__ = "agent_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=True)
    reasoning_content = Column(Text, nullable=True)
    tool_call_json = Column(Text, nullable=True)
    tool_result_json = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    session = relationship("AgentSession", back_populates="messages")

    __table_args__ = (Index("idx_agent_messages_session", "session_id"),)


# ──────────────────────────────────────────
# 20. agent_runs — 技能运行记录
# ──────────────────────────────────────────
class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(Integer, ForeignKey("skills_v2.id", ondelete="SET NULL"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agents_v2.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="SET NULL"), nullable=True)
    inputs_json = Column(Text, nullable=True)
    outputs_json = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (Index("idx_agent_runs_agent", "agent_id"),)


# ──────────────────────────────────────────
# 21. agent_memories — 记忆
# ──────────────────────────────────────────
class AgentMemory(Base):
    __tablename__ = "agent_memories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents_v2.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    scope = Column(String(30), nullable=False, default="agent")
    confidence = Column(Numeric(5, 4), nullable=False, default=1.0)
    source = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    last_used_at = Column(DateTime, nullable=False, default=datetime.now)

    agent = relationship("AgentV2", back_populates="memories")

    __table_args__ = (
        Index("idx_agent_memories_agent", "agent_id"),
        Index("idx_agent_memories_key", "agent_id", "key"),
    )
