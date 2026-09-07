from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import Loan, LoanInstallment, Member, SavingsAccount, User, FieldCollectionEntry, SavingsTransaction
from app.schemas import DashboardMetrics

router = APIRouter()


@router.get("/metrics", response_model=DashboardMetrics)
async def metrics(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("dashboard.read")),
) -> DashboardMetrics:
    total_members = await session.scalar(select(func.count()).select_from(Member))
    active_savings = await session.scalar(select(func.count()).select_from(SavingsAccount).where(SavingsAccount.status == "active"))
    total_savings = await session.scalar(select(func.coalesce(func.sum(SavingsAccount.balance), 0)))
    active_loans = await session.scalar(select(func.count()).select_from(Loan).where(Loan.status == "active"))
    loan_outstanding = await session.scalar(select(func.coalesce(func.sum(Loan.outstanding_principal), 0)))
    overdue = await session.scalar(select(func.count()).select_from(LoanInstallment).where(LoanInstallment.status == "overdue"))
    pending = await session.scalar(select(func.count()).select_from(LoanInstallment).where(LoanInstallment.status == "pending"))
    penalty = await session.scalar(select(func.coalesce(func.sum(LoanInstallment.penalty), 0)))
    
    from datetime import date
    today = date.today()
    collection_today = await session.scalar(
        select(func.coalesce(func.sum(FieldCollectionEntry.amount), 0))
        .where(func.date(FieldCollectionEntry.collected_at) == today)
    )
    
    recent_txs = list(await session.scalars(
        select(SavingsTransaction)
        .order_by(SavingsTransaction.trans_date.desc())
        .limit(10)
    ))
    recent_transactions = [
        {"id": str(t.id), "amount": str(t.amount), "type": t.trans_type, "date": t.trans_date.isoformat()}
        for t in recent_txs
    ]

    return DashboardMetrics(
        total_members=total_members or 0,
        active_savings_accounts=active_savings or 0,
        total_savings=total_savings or Decimal("0"),
        active_loans=active_loans or 0,
        loan_outstanding=loan_outstanding or Decimal("0"),
        overdue_installments=overdue or 0,
        pending_installments=pending or 0,
        penalty_receivable=penalty or Decimal("0"),
        collection_today=collection_today or Decimal("0"),
        recent_transactions=recent_transactions,
    )
