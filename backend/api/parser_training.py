"""Parser Training API — rule center MVP endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.response import error, success
from database import get_db
from services import parser_training_service, artifact_service

router = APIRouter(prefix="/parser-training", tags=["parser-training"])


class RunCandidateBody(BaseModel):
    file_path: str
    code: str


class SaveParserBody(BaseModel):
    name: str = Field(..., max_length=100)
    code: str
    bank_id: Optional[int] = None
    format_key: Optional[str] = Field(None, max_length=100)
    match_rules: dict = {}
    sample_check_log: dict = {}
    confidence: Optional[float] = None
    primitives_imports: list[str] = []


class AgentSessionBody(BaseModel):
    job_id: str


@router.post("/jobs")
async def create_job(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload sample file and create a training job."""
    file_data = await file.read()
    filename = file.filename or "sample.xlsx"
    try:
        result = parser_training_service.create_training_job(db, file_data, filename)
        return success(result)
    except ValueError as exc:
        return error(1001, str(exc))


@router.post("/run-candidate")
def run_candidate(body: RunCandidateBody, db: Session = Depends(get_db)):
    """Trial-run candidate parser code."""
    if not body.code.strip():
        return error(1001, "候选代码不能为空")
    try:
        result = parser_training_service.run_candidate(body.file_path, body.code)
        return success(result)
    except Exception as exc:
        return error(5000, f"试运行失败: {exc}")


@router.post("/save-parser")
def save_parser(body: SaveParserBody, db: Session = Depends(get_db)):
    """Save candidate code as active ParserArtifact."""
    try:
        result = parser_training_service.save_parser(
            db,
            name=body.name,
            code=body.code,
            bank_id=body.bank_id,
            format_key=body.format_key,
            match_rules=body.match_rules,
            sample_check_log=body.sample_check_log,
            confidence=body.confidence,
            primitives_imports=body.primitives_imports,
        )
        return success(result)
    except ValueError as exc:
        return error(2001, str(exc))


@router.post("/agent-session")
def create_agent_session(body: AgentSessionBody, db: Session = Depends(get_db)):
    """Create or reuse a rule center agent session."""
    from db.tables import Agent
    from agents import session_store

    rule_agent = db.query(Agent).filter(
        Agent.display_name.like("%规则%"),
        Agent.status == "active",
    ).first()

    if not rule_agent:
        default_agent = db.query(Agent).filter(Agent.status == "active").order_by(Agent.id).first()
        if not default_agent:
            return error(2001, "系统中没有可用的智能体，请先创建智能体并配置 AI")
        rule_agent = default_agent

    sessions = session_store.list_sessions(db, rule_agent.id)
    active_session = None
    for s in sessions:
        if s.get("status") == "active":
            active_session = s
            break

    if not active_session:
        active_session = session_store.create_session(
            db, rule_agent.id,
            title=f"银行流水规则训练 {body.job_id}",
        )

    return success({
        "agent_id": rule_agent.id,
        "agent_code": rule_agent.agent_code,
        "agent_name": rule_agent.display_name,
        "session_id": active_session["id"],
    })


@router.get("/context")
def get_context(db: Session = Depends(get_db)):
    """Get master data context for rule generation."""
    from services.parser_context_service import build_bank_parser_context
    return success(build_bank_parser_context(db))


@router.get("/parsers")
def list_parsers(kind: str = "bank", db: Session = Depends(get_db)):
    """List parser artifacts for the rule center."""
    data = artifact_service.list_parser_artifacts(db, kind=kind)
    return success(data)
