"""恢复出厂服务 — 清空业务数据，保留主数据结构"""
from typing import Dict

from sqlalchemy import text
from sqlalchemy.orm import Session


def factory_reset(db: Session) -> Dict:
    """清空业务数据，保留种子主数据

    清空: fund_events, import_batches, daily_report_runs, operation_logs
    保留: divisions, entities, accounts, account_aliases, parser_templates,
          manual_field_pool, manual_template_schemes, ai_configs, users
    """
    # 按外键依赖顺序删除
    db.execute(text("DELETE FROM fund_events"))
    db.execute(text("DELETE FROM import_batches"))
    db.execute(text("DELETE FROM daily_report_runs"))
    db.execute(text("DELETE FROM operation_logs"))
    db.commit()
    return {"message": "恢复出厂设置成功，业务数据已清空"}
