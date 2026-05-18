"""Account Resolution Audit 服务 — 保存账户归属判断结果和证据

每次对 SourceFile 执行账户归属判断时，
调用 record_account_resolution_attempt() 保存尝试记录和可解释证据。
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from db.tables import AccountResolutionAttempt, AccountResolutionEvidence, SourceFile


def record_account_resolution_attempt(
    db: Session,
    source_file: SourceFile,
    account_attribution: dict,
    identity_hints: Optional[dict] = None,
    bank_resolution: Optional[dict] = None,
) -> AccountResolutionAttempt:
    status = account_attribution.get("status", "unmatched")

    confidence = account_attribution.get("confidence", 0.0)
    if isinstance(confidence, (int, float)):
        confidence = Decimal(str(round(confidence, 4)))

    attempt = AccountResolutionAttempt(
        source_file_id=source_file.id,
        status=status,
        recommended_entity_code=account_attribution.get("entity_code") or None,
        recommended_account_code=account_attribution.get("account_code") or None,
        confidence=confidence,
        match_reason=account_attribution.get("match_reason", ""),
        error_code=account_attribution.get("error_code"),
        raw_hints=account_attribution.get("raw_hints"),
        candidates=account_attribution.get("candidates"),
        bank_resolution=bank_resolution,
    )
    db.add(attempt)
    db.flush()

    _generate_evidence(db, attempt, account_attribution, identity_hints)
    return attempt


def _generate_evidence(
    db: Session,
    attempt: AccountResolutionAttempt,
    account_attribution: dict,
    identity_hints: Optional[dict],
):
    hints = (identity_hints or {}).get("identity_hints", identity_hints or {})
    match_reason = account_attribution.get("match_reason", "")

    # Account number evidence
    account_number = hints.get("account_number", "")
    if account_number:
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="account_number",
            evidence_value=account_number,
            matched_account_code=attempt.recommended_account_code,
            weight=Decimal("0.9500") if match_reason == "account_number_exact" else Decimal("0.5000"),
            message=f"文件中提取到账号 {account_number[:6]}****{account_number[-4:]}",
        ))

    # Last four digits evidence
    last_four = hints.get("account_last_four", "")
    if last_four and not account_number:
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="account_last_four",
            evidence_value=last_four,
            matched_account_code=attempt.recommended_account_code,
            weight=Decimal("0.8500") if match_reason == "account_last_four" else Decimal("0.4000"),
            message=f"文件中提取到尾号 {last_four}",
        ))

    # Account name / holder evidence
    account_name = hints.get("account_name", "")
    if account_name:
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="account_name",
            evidence_value=account_name,
            matched_entity_code=attempt.recommended_entity_code,
            weight=Decimal("0.3000"),
            message=f"文件中提取到户名「{account_name}」",
        ))

    # Entity name evidence
    entity_name = hints.get("entity_name", "")
    if entity_name:
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="entity_name",
            evidence_value=entity_name,
            matched_entity_code=attempt.recommended_entity_code,
            weight=Decimal("0.7500") if match_reason == "entity_name_match" else Decimal("0.3000"),
            message=f"文件中提取到单位名称「{entity_name}」",
        ))

    # Bank name evidence
    bank_name = hints.get("bank_name", "")
    if bank_name:
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="bank",
            evidence_value=bank_name,
            weight=Decimal("0.2000"),
            message=f"文件中提取到银行「{bank_name}」",
        ))

    # Filename evidence
    filename_hint = hints.get("filename_hint", "")
    if filename_hint:
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="filename",
            evidence_value=filename_hint,
            weight=Decimal("0.1000"),
            message=f"文件名含尾号线索「{filename_hint}」",
        ))

    # Alias match evidence
    if match_reason == "alias_match":
        name_hint = hints.get("account_name") or hints.get("entity_name") or ""
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="alias",
            evidence_value=name_hint,
            matched_entity_code=attempt.recommended_entity_code,
            matched_account_code=attempt.recommended_account_code,
            weight=Decimal("0.8000"),
            message=f"通过别名匹配到账户「{account_attribution.get('account_name', '')}」",
        ))

    # Match summary evidence
    if attempt.status == "matched":
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="parser_hint",
            evidence_value=match_reason,
            matched_entity_code=attempt.recommended_entity_code,
            matched_account_code=attempt.recommended_account_code,
            weight=attempt.confidence or Decimal("0"),
            message=f"匹配方式：{match_reason}，置信度 {float(attempt.confidence or 0):.0%}",
        ))
    elif attempt.status in ("ambiguous", "conflict"):
        candidates = account_attribution.get("candidates", [])
        cand_desc = "、".join(
            f"「{c.get('entity_name', '')}/{c.get('account_name', '')}」"
            for c in candidates[:3]
        )
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="parser_hint",
            evidence_value=f"candidates: {len(candidates)}",
            weight=Decimal("0"),
            message=f"存在 {len(candidates)} 个候选：{cand_desc}，需要用户确认",
        ))
    elif attempt.status == "unmatched":
        error_code = account_attribution.get("error_code", "")
        db.add(AccountResolutionEvidence(
            attempt_id=attempt.id,
            evidence_type="parser_hint",
            evidence_value=error_code or "unmatched",
            weight=Decimal("0"),
            message=f"未能自动匹配：{account_attribution.get('match_reason', '原因未知')}",
        ))

    db.flush()
