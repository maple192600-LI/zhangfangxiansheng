"""Parser Training API — rule center MVP endpoints (job_code driven)."""
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.response import error, success
from database import get_db
from services import parser_training_service, artifact_service

router = APIRouter(prefix="/parser-training", tags=["parser-training"])


class AgentSessionBody(BaseModel):
    agent_id: int


class SaveParserBody(BaseModel):
    name: str = Field(..., max_length=100)


@router.post("/jobs")
async def create_job(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload sample file and create a persistent training job."""
    file_data = await file.read()
    filename = file.filename or "sample.xlsx"
    try:
        result = parser_training_service.create_training_job(db, file_data, filename)
        return success(result)
    except ValueError as exc:
        return error(1001, str(exc))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("样本文件解析失败: %s", filename)
        return error(1001, "样本文件读取失败，请确认文件未损坏或另存为 xlsx 后重试")


@router.get("/jobs/{job_code}")
def get_job(job_code: str, db: Session = Depends(get_db)):
    """Get training job details by job_code."""
    result = parser_training_service.get_job(db, job_code)
    if not result:
        return error(1001, f"训练任务 {job_code} 不存在")
    return success(result)


@router.post("/jobs/{job_code}/run-candidate")
def run_candidate(job_code: str, db: Session = Depends(get_db)):
    """Trial-run the candidate code saved in the training job."""
    try:
        result = parser_training_service.run_candidate(db, job_code)
        return success(result)
    except Exception as exc:
        return error(5000, f"试运行失败: {exc}")


@router.post("/jobs/{job_code}/save-parser")
def save_parser(job_code: str, body: SaveParserBody, db: Session = Depends(get_db)):
    """Save the training job's candidate code as active ParserArtifact."""
    try:
        result = parser_training_service.save_parser(db, job_code, body.name)
        return success(result)
    except ValueError as exc:
        return error(2001, str(exc))


@router.get("/agents")
def list_active_agents(db: Session = Depends(get_db)):
    """List active agents for user to select."""
    from db.tables import Agent
    agents = db.query(Agent).filter(Agent.status == "active").all()
    return success([
        {
            "id": a.id,
            "agent_code": a.agent_code,
            "display_name": a.display_name,
        }
        for a in agents
    ])


@router.post("/jobs/{job_code}/agent-session")
def create_agent_session(job_code: str, body: AgentSessionBody, db: Session = Depends(get_db)):
    """Create a new agent session for the training job. Requires explicit agent_id."""
    from db.tables import Agent
    from agents import session_store

    agent = db.query(Agent).filter(Agent.id == body.agent_id, Agent.status == "active").first()
    if not agent:
        return error(2001, f"智能体 {body.agent_id} 不存在或未启用")

    job = parser_training_service.get_job(db, job_code)
    if not job:
        return error(1001, f"训练任务 {job_code} 不存在")

    session_data = session_store.create_session(
        db, agent.id,
        title=f"规则训练 {job['filename']} ({job_code})",
    )

    starter_prompt = _build_starter_prompt(job)
    session_store.save_message(
        db, session_data["id"], role="user",
        content=starter_prompt,
    )

    return success({
        "agent_id": agent.id,
        "agent_code": agent.agent_code,
        "agent_name": agent.display_name,
        "session_id": session_data["id"],
        "starter_prompt": starter_prompt,
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


@router.get("/parsers/{artifact_id}")
def get_parser_detail(artifact_id: int, db: Session = Depends(get_db)):
    """Get parser artifact detail (includes code)."""
    result = artifact_service.get_parser_artifact(db, artifact_id)
    if not result:
        return error(1001, f"Parser {artifact_id} 不存在")
    return success(result)


@router.post("/parsers/{artifact_id}/activate")
def activate_parser(artifact_id: int, db: Session = Depends(get_db)):
    try:
        result = artifact_service.activate_parser_artifact(db, artifact_id)
        return success(result)
    except ValueError as exc:
        return error(2001, str(exc))


@router.post("/parsers/{artifact_id}/retire")
def retire_parser(artifact_id: int, db: Session = Depends(get_db)):
    try:
        result = artifact_service.retire_parser_artifact(db, artifact_id)
        return success(result)
    except ValueError as exc:
        return error(2001, str(exc))


@router.delete("/parsers/{artifact_id}")
def delete_parser(artifact_id: int, db: Session = Depends(get_db)):
    try:
        artifact_service.delete_parser_artifact(db, artifact_id)
        return success({"deleted": artifact_id})
    except ValueError as exc:
        return error(2001, str(exc))


def _build_starter_prompt(job: dict) -> str:
    headers = job.get("headers", [])
    sample_rows = job.get("sample_rows", [])
    filename = job.get("filename", "")
    row_count = job.get("row_count", 0)
    context = job.get("context", {})
    job_code = job.get("job_code", "")

    prompt = f"""你是用户选中的现有智能体，被邀请协助为银行流水生成解析规则。你不是专用解析引擎，只是当前任务需要你帮忙。

## 样本信息
- 文件名: {filename}
- 总行数: {row_count}
- 表头: {', '.join(headers)}

## 前5行样本
"""
    for i, row in enumerate(sample_rows[:5], 1):
        prompt += f"第{i}行: {' | '.join(row)}\n"

    entities = context.get("entities", [])
    banks = context.get("banks", [])
    accounts = context.get("accounts", [])

    if entities:
        prompt += "\n## 系统中的法人单位（已由系统自动提供，不需要用户再提供）\n"
        for e in entities[:10]:
            prompt += f"- {e['entity_code']}: {e['name']}\n"

    if banks:
        prompt += "\n## 系统中的银行（已由系统自动提供）\n"
        for b in banks[:10]:
            prompt += f"- {b.get('bank_name', '')}"
            if b.get("short_name"):
                prompt += f" ({b['short_name']})"
            prompt += "\n"

    if accounts:
        prompt += "\n## 系统中的银行账户（已由系统自动提供）\n"
        for a in accounts[:10]:
            prompt += f"- {a['account_code']}: {a['account_alias']}"
            if a.get("account_last_four"):
                prompt += f" (后四位: {a['account_last_four']})"
            prompt += "\n"

    prompt += f"""
## 你的任务
根据样本文件结构和系统提供的主数据上下文，生成一个候选 parser。

## 输出要求
定义 parse(wb, ctx) 函数，返回 CANONICAL_12 字段列表:
business_date, entity_code, entity_name, account_code, account_name, summary, counterparty, amount_in, amount_out, rolling_balance, state, source

## 禁止事项
- 不允许硬编码 DEFAULT_ACCOUNT_CODE / DEFAULT_ENTITY_CODE
- 不允许固定 account_code / entity_code 作为默认值
- Parser 只负责读取文件结构和标准字段，不负责把某个单位/账户硬编码进去
- 不允许要求用户手工提供主数据，系统已经在上方给出受控主数据摘要

## 完成方式
完成后请调用 parser_training_update_candidate 工具提交候选代码：
parser_training_update_candidate(job_code="{job_code}", code=你的代码, notes=说明)

注意：用户最终审核的是解析结果表格，不是代码。
"""

    return prompt
