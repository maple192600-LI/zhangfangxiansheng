from __future__ import annotations

from datetime import date

from db.tables import FundEvent, OperationLog


def _session(env):
    return env["SessionLocal"]()


def _seed_exception_event(env, state="待确认", amount_in=100, amount_out=0):
    with _session(env) as db:
        event = FundEvent(
            business_date=date(2026, 4, 25),
            entity_code="E001",
            entity_name="示例科技有限公司",
            account_code="A001",
            account_name="工行主账户",
            summary="待补充摘要",
            counterparty="示例客户",
            amount_in=amount_in,
            amount_out=amount_out,
            rolling_balance=100100,
            state=state,
            source="网银导入",
        )
        db.add(event)
        db.commit()
        return event.id


def test_exception_center_resolves_pending_event(e2e_client, e2e_env):
    event_id = _seed_exception_event(e2e_env)

    listed = e2e_client.get("/api/events/pending").json()
    assert listed["code"] == 0
    assert listed["data"]["total"] == 1
    assert listed["data"]["summary"]["pending_count"] == 1

    resolved = e2e_client.put(f"/api/events/{event_id}/resolve", json={
        "fixes": {"summary": "已补充摘要", "amount_in": 120, "amount_out": 0},
        "note": "补充回单后确认",
    }).json()
    assert resolved["code"] == 0, resolved
    assert resolved["data"]["state"] == "正常"
    assert resolved["data"]["summary"] == "已补充摘要"
    assert resolved["data"]["amount_in"] == 120

    with _session(e2e_env) as db:
        assert db.query(FundEvent).filter(FundEvent.id == event_id).first().state == "正常"
        log = db.query(OperationLog).filter(OperationLog.action == "event_resolve").first()
        assert log is not None


def test_exception_center_voids_abnormal_event(e2e_client, e2e_env):
    event_id = _seed_exception_event(e2e_env, state="异常")

    voided = e2e_client.put(f"/api/events/{event_id}/void", json={
        "reason": "重复导入",
    }).json()
    assert voided["code"] == 0, voided
    assert voided["data"]["state"] == "已作废"

    relisted = e2e_client.get("/api/events/pending").json()
    assert relisted["code"] == 0
    assert relisted["data"]["total"] == 0

    with _session(e2e_env) as db:
        log = db.query(OperationLog).filter(OperationLog.action == "event_void").first()
        assert log is not None
