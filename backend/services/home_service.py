"""首页数据服务"""
from datetime import datetime, date, timedelta
from typing import Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.tables import ImportBatch, FundEvent, Account, Entity, OperationLog, DailyReportRun


def get_overview(db: Session) -> Dict:
    """工作总览：待处理任务数、异常数、今日生成状态、重点账户变化"""
    # 待处理批次
    pending_batches = (
        db.query(ImportBatch)
        .filter(ImportBatch.status.in_(["uploaded", "parsing"]))
        .count()
    )

    # 异常行数
    abnormal_count = (
        db.query(FundEvent)
        .filter(FundEvent.parse_status == "abnormal")
        .count()
    )

    # 今日生成状态
    today = date.today()
    latest_report = (
        db.query(DailyReportRun)
        .order_by(DailyReportRun.created_at.desc())
        .first()
    )
    today_generated = False
    report_info = "尚未生成"
    if latest_report:
        report_info = f"最近生成: {latest_report.created_at.strftime('%Y-%m-%d %H:%M')}"
        if latest_report.start_date and latest_report.end_date:
            if latest_report.start_date <= today <= latest_report.end_date and latest_report.status == "confirmed":
                today_generated = True

    # 重点账户变化 (余额 TOP5)
    top_accounts = (
        db.query(
            Account.account_alias,
            Account.initial_balance,
            Entity.name.label("entity_name"),
        )
        .join(Entity, Account.entity_id == Entity.id)
        .filter(Account.status == "enabled")
        .order_by(Account.initial_balance.desc())
        .limit(5)
        .all()
    )
    account_changes = [
        {"account_name": a.account_alias, "entity_name": a.entity_name, "balance": float(a.initial_balance or 0)}
        for a in top_accounts
    ]

    # 各阶段进度
    total_batches = db.query(ImportBatch).count()
    committed_batches = db.query(ImportBatch).filter(ImportBatch.status == "committed").count()
    total_events = db.query(FundEvent).count()
    normal_events = db.query(FundEvent).filter(FundEvent.parse_status == "normal").count()

    return {
        "pending_tasks": pending_batches + abnormal_count,
        "abnormal_count": abnormal_count,
        "today_generated": today_generated,
        "report_info": report_info,
        "account_changes": account_changes,
        "progress": {
            "bank_import": min(100, int(committed_batches / max(1, total_batches) * 100)) if total_batches else 0,
            "manual_flow": 0,
            "abnormal_fix": min(100, int((total_events - abnormal_count) / max(1, total_events) * 100)) if total_events else 0,
            "base_data": 100 if total_events > 0 and abnormal_count == 0 else 0,
            "daily_report": 100 if today_generated else 0,
        },
    }


def get_todos(db: Session) -> Dict:
    """待办追踪：待导入/待确认/待生成"""
    # 待导入：状态为 uploaded 的批次
    to_import = (
        db.query(ImportBatch)
        .filter(ImportBatch.status == "uploaded")
        .all()
    )
    import_items = [
        {"batch_code": b.batch_code, "source_name": b.source_name or "未命名文件", "row_count": db.query(FundEvent).filter(FundEvent.batch_id == b.id).count()}
        for b in to_import
    ]

    # 待确认：异常行
    abnormal_events = (
        db.query(FundEvent)
        .filter(FundEvent.parse_status == "abnormal")
        .all()
    )
    confirm_items = [
        {"id": e.id, "summary": e.summary_text or "未填写摘要", "abnormal_code": e.abnormal_code}
        for e in abnormal_events[:20]
    ]

    # 待生成：检查基础数据表和日报
    to_generate = []
    total_events = db.query(FundEvent).filter(FundEvent.parse_status == "normal").count()
    if total_events == 0:
        to_generate.append("基础数据表未生成")
    today_report = db.query(DailyReportRun).filter(DailyReportRun.status == "confirmed").first()
    if not today_report:
        to_generate.append("资金日报未生成")

    return {
        "to_import": import_items,
        "to_confirm": confirm_items,
        "to_generate": to_generate,
        "counts": {
            "import": len(import_items),
            "confirm": len(abnormal_events),
            "generate": len(to_generate),
        },
    }


def get_quick_links(db: Session) -> Dict:
    """快捷入口"""
    abnormal_count = db.query(FundEvent).filter(FundEvent.parse_status == "abnormal").count()

    links = [
        {"name": "进入工作台", "desc": "开始今天的导入、录入和维护", "route": "/bank-import", "icon": "💼"},
        {"name": "查看基础数据表", "desc": "核对识别结果，确认是否可生成", "route": "/base-data", "icon": "📊"},
        {"name": "异常中心", "desc": f"集中处理待确认和规则未命中 ({abnormal_count})", "route": "/base-data", "icon": "⚠️"},
        {"name": "重点账户余额", "desc": "快速查看关键账户状态", "route": "/account-balance", "icon": "🏦"},
        {"name": "操作日志", "desc": "回看今天的主要动作", "route": "/operation-log", "icon": "📝"},
        {"name": "备份恢复", "desc": "创建或恢复系统备份", "route": "/backup-restore", "icon": "💾"},
    ]
    return {"links": links}


def get_system_status(db: Session) -> Dict:
    """系统提醒"""
    # 最近日报生成时间
    latest_report = (
        db.query(DailyReportRun)
        .order_by(DailyReportRun.created_at.desc())
        .first()
    )

    # 最近备份时间（从操作日志查）
    latest_backup = (
        db.query(OperationLog)
        .filter(OperationLog.action == "backup_create")
        .order_by(OperationLog.created_at.desc())
        .first()
    )

    # 最近操作
    recent_logs = (
        db.query(OperationLog)
        .order_by(OperationLog.created_at.desc())
        .limit(5)
        .all()
    )

    reminders = []

    if latest_report:
        reminders.append({
            "type": "ok",
            "message": f"最近一次日报生成时间：{latest_report.created_at.strftime('%Y-%m-%d %H:%M')}",
        })
    else:
        reminders.append({"type": "warn", "message": "尚未生成过资金日报"})

    if latest_backup:
        reminders.append({
            "type": "ok",
            "message": f"最近一次备份完成，时间：{latest_backup.created_at.strftime('%Y-%m-%d %H:%M')}",
        })
    else:
        reminders.append({"type": "info", "message": "尚未创建过系统备份，建议定期备份"})

    # 异常提醒
    abnormal_count = db.query(FundEvent).filter(FundEvent.parse_status == "abnormal").count()
    if abnormal_count > 0:
        reminders.append({
            "type": "warn",
            "message": f"有 {abnormal_count} 条异常数据待处理",
        })

    return {
        "reminders": reminders,
        "recent_actions": [
            {
                "action": log.action,
                "module": log.module,
                "time": log.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for log in recent_logs
        ],
    }
