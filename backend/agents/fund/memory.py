"""Fund Agent 记忆层 — artifact CRUD + 别名库访问

管理 ParserArtifact、RuleArtifact、TemplateInferenceJob 的创建和审批。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from db.tables import ParserArtifact, RuleArtifact, TemplateInferenceJob


def create_parser_draft(
    db: Session,
    name: str,
    kind: str,
    account_code: str,
    code: str,
    primitives_imports: list[str],
    sample_check_log: dict,
    confidence: float,
    created_by: str = "agent",
) -> ParserArtifact:
    """创建 Parser artifact 草稿"""
    version = _next_parser_version(db, name)
    artifact = ParserArtifact(
        name=name,
        kind=kind,
        account_code=account_code,
        version=version,
        status="draft",
        code=code,
        primitives_imports=primitives_imports,
        sample_check_log=sample_check_log,
        confidence=confidence,
        created_by=created_by,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def approve_parser(db: Session, artifact_id: int, approver: str) -> ParserArtifact:
    """审批 Parser artifact"""
    artifact = db.query(ParserArtifact).filter(ParserArtifact.id == artifact_id).first()
    if not artifact:
        raise ValueError(f"Parser artifact {artifact_id} 不存在")
    # 将同账户同类型的 active 降级为 retired
    db.query(ParserArtifact).filter(
        ParserArtifact.account_code == artifact.account_code,
        ParserArtifact.kind == artifact.kind,
        ParserArtifact.status == "active",
    ).update({"status": "retired"})
    artifact.status = "active"
    artifact.approved_by = approver
    artifact.approved_at = datetime.now()
    db.commit()
    db.refresh(artifact)
    return artifact


def create_rule_draft(
    db: Session,
    name: str,
    template_id: Optional[int],
    placeholder_bindings: dict,
    loop_config: Optional[dict],
    primitives_imports: list[str],
    sample_check_log: dict,
    confidence: float,
    created_by: str = "agent",
) -> RuleArtifact:
    """创建 Rule artifact 草稿"""
    version = _next_rule_version(db, name)
    artifact = RuleArtifact(
        name=name,
        template_id=template_id,
        version=version,
        status="draft",
        placeholder_bindings=placeholder_bindings,
        loop_config=loop_config,
        primitives_imports=primitives_imports,
        sample_check_log=sample_check_log,
        confidence=confidence,
        created_by=created_by,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def approve_rule(db: Session, artifact_id: int, approver: str) -> RuleArtifact:
    """审批 Rule artifact"""
    artifact = db.query(RuleArtifact).filter(RuleArtifact.id == artifact_id).first()
    if not artifact:
        raise ValueError(f"Rule artifact {artifact_id} 不存在")
    artifact.status = "active"
    artifact.approved_by = approver
    artifact.approved_at = datetime.now()
    db.commit()
    db.refresh(artifact)
    return artifact


def create_inference_job(
    db: Session,
    template_file: str,
    original_filename: Optional[str] = None,
) -> TemplateInferenceJob:
    """创建模板推断任务"""
    job = TemplateInferenceJob(
        template_file=template_file,
        original_filename=original_filename,
        status="pending",
        stage="a",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_inference_job(
    db: Session,
    job_id: int,
    **kwargs,
) -> TemplateInferenceJob:
    """更新推断任务"""
    job = db.query(TemplateInferenceJob).filter(TemplateInferenceJob.id == job_id).first()
    if not job:
        raise ValueError(f"Inference job {job_id} 不存在")
    for k, v in kwargs.items():
        setattr(job, k, v)
    job.updated_at = datetime.now()
    db.commit()
    db.refresh(job)
    return job


def get_active_parser(db: Session, account_code: str, kind: str = "bank") -> Optional[ParserArtifact]:
    """获取账户的活跃解析器"""
    return db.query(ParserArtifact).filter(
        ParserArtifact.account_code == account_code,
        ParserArtifact.kind == kind,
        ParserArtifact.status == "active",
    ).first()


def get_field_dictionary() -> dict:
    """加载字段字典（从种子数据）"""
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed", "field_dictionary.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return _default_field_dictionary()


def get_alias_library() -> dict:
    """加载别名库"""
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed", "alias_library.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _next_parser_version(db: Session, name: str) -> int:
    latest = db.query(ParserArtifact).filter(
        ParserArtifact.name == name,
    ).order_by(ParserArtifact.version.desc()).first()
    return (latest.version + 1) if latest else 1


def _next_rule_version(db: Session, name: str) -> int:
    latest = db.query(RuleArtifact).filter(
        RuleArtifact.name == name,
    ).order_by(RuleArtifact.version.desc()).first()
    return (latest.version + 1) if latest else 1


def _default_field_dictionary() -> dict:
    return {
        "business_date": {"cn_name": "日期", "type": "DATE", "aliases": ["日期", "交易日期", "记账日期"]},
        "entity_code": {"cn_name": "单位编码", "type": "VARCHAR", "aliases": ["单位编码", "主体编码"]},
        "entity_name": {"cn_name": "单位名称", "type": "VARCHAR", "aliases": ["单位", "单位名称", "主体"]},
        "account_code": {"cn_name": "账户编码", "type": "VARCHAR", "aliases": ["账户编码", "账号"]},
        "account_name": {"cn_name": "账户名称", "type": "VARCHAR", "aliases": ["账户", "账户名称"]},
        "summary": {"cn_name": "摘要", "type": "TEXT", "aliases": ["摘要", "用途", "备注"]},
        "counterparty": {"cn_name": "对方", "type": "TEXT", "aliases": ["对方", "对方户名", "往来单位"]},
        "amount_in": {"cn_name": "收入", "type": "NUMERIC", "aliases": ["收入", "贷方", "进账"]},
        "amount_out": {"cn_name": "支出", "type": "NUMERIC", "aliases": ["支出", "借方", "出账"]},
        "rolling_balance": {"cn_name": "余额", "type": "NUMERIC", "aliases": ["余额", "账户余额"]},
    }
