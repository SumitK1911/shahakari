import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Loan, LoanInstallment, Member, ReportRun, SavingsAccount, Share

REPORT_DIR = Path("generated_reports")


async def generate_management_report(
    session: AsyncSession,
    *,
    report_type: str,
    period_code: str | None = None,
    generated_by=None,
) -> ReportRun:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    period = period_code or date.today().isoformat()
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "members": await session.scalar(select(func.count()).select_from(Member)) or 0,
        "active_savings_accounts": await session.scalar(select(func.count()).select_from(SavingsAccount).where(SavingsAccount.status == "active")) or 0,
        "share_capital": str(await session.scalar(select(func.coalesce(func.sum(Share.total_amount), 0))) or 0),
        "loan_outstanding": str(await session.scalar(select(func.coalesce(func.sum(Loan.outstanding_principal), 0))) or 0),
        "overdue_installments": await session.scalar(select(func.count()).select_from(LoanInstallment).where(LoanInstallment.status == "overdue")) or 0,
    }
    content = json.dumps({"report_type": report_type, "period_code": period, "summary": summary}, indent=2).encode("utf-8")
    file_path = REPORT_DIR / f"{report_type}_{period}.json"
    file_path.write_bytes(content)
    record = ReportRun(
        report_type=report_type,
        period_code=period,
        file_path=str(file_path),
        file_size=len(content),
        checksum=hashlib.sha256(content).hexdigest(),
        status="generated",
        generated_by=generated_by,
        summary=summary,
    )
    session.add(record)
    await session.flush()
    return record
