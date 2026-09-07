import asyncio
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import func
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import BackupRun, DayClosing, Loan, LoanInstallment, Member, SavingsAccount, Share
from app.services.automation import run_finance_automation
from app.services.notifications import dispatch_queued_notifications, queue_notification, queue_operational_notifications
from app.services.reports import generate_management_report
from app.services.controls_monitoring import run_compliance_scan
from app.services.rules_engine import FinancialRulesEngine

settings = get_settings()
celery_app = Celery("sahakari", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.beat_schedule = {
    "daily-interest-0000": {
        "task": "automation.daily_interest",
        "schedule": crontab(hour=0, minute=0),
    },
    "penalty-calculation-0005": {
        "task": "automation.penalty_calculation",
        "schedule": crontab(hour=0, minute=5),
    },
    "loan-overdue-check-0010": {
        "task": "automation.mark_overdue_installments",
        "schedule": crontab(hour=0, minute=10),
    },
    "maturity-processing-0015": {
        "task": "automation.maturity_processing",
        "schedule": crontab(hour=0, minute=15),
    },
    "emi-generation-0020": {
        "task": "automation.emi_generation",
        "schedule": crontab(hour=0, minute=20),
    },
    "notifications-0025": {
        "task": "automation.dispatch_notifications",
        "schedule": crontab(hour=0, minute=25),
    },
    "end-of-day-0030": {
        "task": "automation.end_of_day",
        "schedule": crontab(hour=0, minute=30),
    },
    "backup-0040": {
        "task": "automation.backup",
        "schedule": crontab(hour=0, minute=40),
    },
    "reports-0100": {
        "task": "automation.generate_reports",
        "schedule": crontab(hour=1, minute=0),
    },
}
celery_app.conf.timezone = "Asia/Kathmandu"


@celery_app.task(name="automation.daily_interest")
def daily_interest() -> dict[str, int | str]:
    async def run() -> dict[str, int | str]:
        async with SessionLocal() as session:
            result = await run_finance_automation(
                session,
                run_date=date.today(),
                penalty_rate_percent=Decimal("2"),
            )
            await session.commit()
            return {
                "transactions": int(result["savings_interest_transactions"]),
                "overdue": int(result["overdue_installments"]),
                "period": str(result["period"]),
            }

    return asyncio.run(run())


@celery_app.task(name="automation.penalty_calculation")
def penalty_calculation() -> dict[str, int]:
    async def run() -> dict[str, int]:
        result = await _calculate_penalties()
        return result

    return asyncio.run(run())


@celery_app.task(name="automation.mark_overdue_installments")
def mark_overdue_installments() -> dict[str, int]:
    return asyncio.run(_calculate_penalties())


async def _calculate_penalties() -> dict[str, int]:
    today = date.today()
    async with SessionLocal() as session:
        rules_engine = FinancialRulesEngine(session)
        installments = await session.scalars(
            select(LoanInstallment)
            .where(LoanInstallment.due_date < today, LoanInstallment.status.in_(["pending", "overdue"]))
            .with_for_update()
        )
        overdue = 0
        for installment in installments:
            loan = await session.get(Loan, installment.loan_id)
            result = await rules_engine.calculate_penalty(
                installment=installment,
                loan=loan,
                calculation_date=today,
                fallback_rate_percent=Decimal("2"),
            )
            installment.status = "overdue"
            installment.penalty = max(installment.penalty, result.amount)
            overdue += 1
        await session.commit()
        return {"overdue": overdue}


@celery_app.task(name="automation.maturity_processing")
def maturity_processing() -> dict[str, int | str]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            result = await run_finance_automation(
                session,
                run_date=date.today(),
                penalty_rate_percent=Decimal("2"),
            )
            await session.commit()
            return {"matured_deposits": int(result["matured_deposits"])}

    return asyncio.run(run())


@celery_app.task(name="automation.emi_generation")
def emi_generation() -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            loans = list(await session.scalars(select(Loan).where(Loan.status == "active")))
            generated = 0
            for loan in loans:
                count = await session.scalar(select(func.count()).select_from(LoanInstallment).where(LoanInstallment.loan_id == loan.id))
                if count == 0:
                    generated += 1
            return {"loans_checked": len(loans), "missing_schedules": generated}

    return asyncio.run(run())


@celery_app.task(name="automation.dispatch_notifications")
def dispatch_notifications() -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            result = await dispatch_queued_notifications(session)
            await session.commit()
            return result

    return asyncio.run(run())


@celery_app.task(name="automation.end_of_day")
def end_of_day() -> dict[str, str]:
    async def run() -> dict[str, str]:
        async with SessionLocal() as session:
            closing = await session.scalar(select(DayClosing).where(DayClosing.closing_date_ad == date.today()))
            if closing is None:
                closing = DayClosing(closing_date_ad=date.today(), status="system_closed", cash_summary={}, exception_summary={})
                session.add(closing)
            else:
                closing.status = "system_closed"
            await session.commit()
            return {"status": "system_closed", "date": date.today().isoformat()}

    return asyncio.run(run())


@celery_app.task(name="automation.backup")
def backup() -> dict[str, str | int]:
    async def run() -> dict[str, str | int]:
        backup_dir = Path("backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        async with SessionLocal() as session:
            payload = {
                "created_at": date.today().isoformat(),
                "note": "Automated manifest backup. Configure pg_dump and object storage credentials for live backup files.",
                "counts": {
                    "members": await session.scalar(select(func.count()).select_from(Member)) or 0,
                    "savings_accounts": await session.scalar(select(func.count()).select_from(SavingsAccount)) or 0,
                    "loans": await session.scalar(select(func.count()).select_from(Loan)) or 0,
                    "shares": await session.scalar(select(func.count()).select_from(Share)) or 0,
                },
            }
            content = json.dumps(payload, indent=2).encode("utf-8")
            file_path = backup_dir / f"sahakari_auto_backup_{date.today().isoformat()}.json"
            file_path.write_bytes(content)
            checksum = hashlib.sha256(content).hexdigest()
            record = BackupRun(
                backup_type="automated_manifest",
                file_path=str(file_path),
                file_size=len(content),
                checksum=checksum,
                status="created",
                notes="Replace with encrypted pg_dump plus file-storage upload in production.",
            )
            session.add(record)
            await session.commit()
            return {"status": "created", "file_size": len(content), "checksum": checksum}

    return asyncio.run(run())


@celery_app.task(name="automation.generate_reports")
def generate_reports() -> dict[str, str]:
    async def run() -> dict[str, str]:
        async with SessionLocal() as session:
            run = await generate_management_report(session, report_type="daily_mis", period_code=date.today().isoformat())
            await session.commit()
            return {"status": run.status, "period_code": run.period_code}

    return asyncio.run(run())


@celery_app.task(name="automation.queue_due_notifications")
def queue_due_notifications() -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            result = await queue_operational_notifications(session, due_days=3)
            await session.commit()
            return result

    return asyncio.run(run())

@celery_app.task(name="automation.compliance_scan")
def compliance_scan() -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            result = await run_compliance_scan(session)
            await session.commit()
            return result

    return asyncio.run(run())



