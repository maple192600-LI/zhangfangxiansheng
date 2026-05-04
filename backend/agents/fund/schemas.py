"""Fund Agent 输入/输出 Schema（Pydantic）

每个 skill 的输入和输出都有严格的 Schema 定义。
harness_strict 模式下，产物必须符合这些 Schema。
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── parser.bank / parser.manual 输入 ────────────────────

class ParserInput(BaseModel):
    account_code: str = Field(description="账户编码")
    sample_file: str = Field(description="样本文件路径")
    field_dictionary_snapshot: Optional[dict] = Field(default=None, description="字段字典快照")
    alias_library_snapshot: Optional[dict] = Field(default=None, description="别名库快照")
    privacy_mode: str = Field(default="standard", description="隐私模式")


class SampleCheckLog(BaseModel):
    sample_rows: int = Field(description="样本行数")
    parsed_rows: int = Field(description="解析行数")
    canonical_violations: int = Field(description="规范违反数")
    amount_sum_in: Optional[str] = Field(default=None, description="收入总额")
    amount_sum_out: Optional[str] = Field(default=None, description="支出总额")


class ParserOutput(BaseModel):
    name: str = Field(description="解析器名称")
    kind: str = Field(description="类型: bank/manual")
    account_code: str = Field(description="账户编码")
    code: str = Field(description="生成的 Python 解析代码")
    primitives_imports: list[str] = Field(default_factory=list, description="使用的基元列表")
    sample_check_log: Optional[SampleCheckLog] = Field(default=None, description="样本校验日志")
    confidence: float = Field(default=0.0, description="置信度")


# ── rule.template_fill 输入 ──────────────────────────────

class RuleInput(BaseModel):
    template_job_id: Optional[int] = Field(default=None, description="模板推断任务 ID")
    placeholder_list: list[str] = Field(default_factory=list, description="占位符列表")
    template_file: str = Field(description="模板文件路径")


class PlaceholderBinding(BaseModel):
    primitive: str = Field(description="基元名称")
    value: Optional[Any] = Field(default=None, description="固定值")
    params: Optional[dict] = Field(default=None, description="参数")


class RuleSampleCheckLog(BaseModel):
    placeholder_bound: int = Field(description="已绑定占位符数")
    placeholder_unbound: int = Field(description="未绑定占位符数")
    placeholder_extra: int = Field(default=0, description="多余占位符数")
    amount_match_rate: Optional[float] = Field(default=None, description="金额匹配率")


class RuleOutput(BaseModel):
    name: str = Field(description="规则名称")
    template_id: Optional[int] = Field(default=None, description="模板 ID")
    placeholder_bindings: dict[str, PlaceholderBinding] = Field(default_factory=dict)
    loop_config: Optional[dict] = Field(default=None, description="循环配置")
    primitives_imports: list[str] = Field(default_factory=list)
    sample_check_log: Optional[RuleSampleCheckLog] = Field(default=None)
    confidence: float = Field(default=0.0)


# ── rule.maintain 输入 ───────────────────────────────────

class RuleMaintainInput(BaseModel):
    rule_id: int = Field(description="要修改的规则 ID")
    change_request: str = Field(description="修改请求描述")
    user_id: str = Field(default="admin", description="操作用户")


# ── template.inference 输入 ──────────────────────────────

class TemplateInferenceInput(BaseModel):
    template_file: str = Field(description="模板文件路径")
    privacy_mode: str = Field(default="standard")
    user_id: str = Field(default="admin")


class StageAOutput(BaseModel):
    placeholders: list[str] = Field(default_factory=list)
    merged_cells: list[dict] = Field(default_factory=list)
    header_rows: list[int] = Field(default_factory=list)


class TemplateInferenceOutput(BaseModel):
    job_id: Optional[int] = Field(default=None)
    detected_placeholders: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0)
    rule_draft: Optional[dict] = Field(default=None)
    stage_a_output: Optional[StageAOutput] = Field(default=None)
