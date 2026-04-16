"""数据库 ORM 表定义

严格按照 docs/30_contracts/20_database_schema.md 定义。
12 张表 + 19 个索引。
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, Date, DateTime,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base


# ──────────────────────────────────────────
# 1. divisions — 板块
# ──────────────────────────────────────────
class Division(Base):
    __tablename__ = "divisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
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

    __table_args__ = (Index("idx_entities_division", "division_id"),)


# ──────────────────────────────────────────
# 3. accounts — 账户
# ──────────────────────────────────────────
class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False)
    account_code = Column(String(50), nullable=False, unique=True)
    account_alias = Column(String(100), nullable=False)
    bank_name = Column(String(100), nullable=True)
    branch_name = Column(String(200), nullable=True)
    account_number = Column(String(100), nullable=True)
    account_type = Column(String(50), nullable=False)
    instrument_type = Column(String(50), nullable=False)
    input_method = Column(String(50), nullable=False, default="manual")
    currency = Column(String(20), nullable=False, default="CNY")
    initial_balance = Column(Numeric(18, 2), nullable=False, default=0)
    balance_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="enabled")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    entity = relationship("Entity", back_populates="accounts")
    aliases = relationship("AccountAlias", back_populates="account", cascade="all, delete-orphan")

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
# 5. parser_templates — 解析模板
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
# 9. fund_events — 标准资金事件（核心表）
# ──────────────────────────────────────────
class FundEvent(Base):
    __tablename__ = "fund_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False)
    source_type = Column(String(30), nullable=False)
    business_date = Column(Date, nullable=False)
    business_time = Column(String(20), nullable=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="SET NULL"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    direction = Column(String(20), nullable=True)
    income_amount = Column(Numeric(18, 2), nullable=True)
    expense_amount = Column(Numeric(18, 2), nullable=True)
    counterparty_name = Column(String(200), nullable=True)
    summary_text = Column(String(500), nullable=False)
    previous_balance_input = Column(Numeric(18, 2), nullable=True)
    ending_balance_input = Column(Numeric(18, 2), nullable=True)
    rolling_balance = Column(Numeric(18, 2), nullable=True)
    parse_status = Column(String(30), nullable=False, default="pending")
    abnormal_code = Column(String(50), nullable=True)
    raw_data_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    batch = relationship("ImportBatch", back_populates="fund_events")
    entity = relationship("Entity")
    account = relationship("Account")

    __table_args__ = (
        Index("idx_fund_events_batch", "batch_id"),
        Index("idx_fund_events_date", "business_date"),
        Index("idx_fund_events_entity", "entity_id"),
        Index("idx_fund_events_account", "account_id"),
        Index("idx_fund_events_status", "parse_status"),
        Index("idx_fund_events_date_account", "business_date", "account_id"),
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
    api_key_encrypted = Column(Text, nullable=False)
    base_url = Column(String(255), nullable=True)
    model_name = Column(String(100), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    agents = relationship("AgentConfig", back_populates="ai_config")


# ──────────────────────────────────────────
# 12. agent_configs — Agent 配置
# ──────────────────────────────────────────
class AgentConfig(Base):
    __tablename__ = "agent_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_code = Column(String(50), nullable=False, unique=True)
    agent_name = Column(String(100), nullable=False)
    agent_type = Column(String(30), nullable=False)
    workspace_dir = Column(String(200), nullable=False)
    ai_config_id = Column(Integer, ForeignKey("ai_configs.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    ai_config = relationship("AIConfig", back_populates="agents")

    __table_args__ = (Index("idx_agent_configs_type", "agent_type", "status"),)


# ──────────────────────────────────────────
# 13. operation_logs — 操作日志
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
