from datetime import date
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import DayClosing, Loan, LoanInstallment, Member, ReportRun, SavingsAccount, SavingsTransaction, Share, ShareTransaction, TermDeposit, User
from app.schemas import ReportRunOut, ReportSummary
from app.services.reports import generate_management_report

router = APIRouter()


@router.get("/portfolio-summary", response_model=ReportSummary)
async def portfolio_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> ReportSummary:
    share_capital = await session.scalar(select(func.coalesce(func.sum(Share.total_amount), 0)))
    savings = await session.scalar(select(func.coalesce(func.sum(SavingsAccount.balance), 0)))
    try:
        term_deposits = await session.scalar(
            select(func.coalesce(func.sum(TermDeposit.balance), 0)).where(TermDeposit.status.in_(["active", "matured"]))
        )
    except ProgrammingError:
        await session.rollback()
        term_deposits = Decimal("0")
    loan_outstanding = await session.scalar(select(func.coalesce(func.sum(Loan.outstanding_principal), 0)))
    overdue_principal = await session.scalar(
        select(func.coalesce(func.sum(LoanInstallment.principal), 0)).where(LoanInstallment.status == "overdue")
    )
    active_members = await session.scalar(select(func.count()).select_from(Member).where(Member.status == "active"))
    return ReportSummary(
        total_share_capital=share_capital or Decimal("0"),
        total_savings_liability=savings or Decimal("0"),
        total_term_deposit_liability=term_deposits or Decimal("0"),
        loan_principal_outstanding=loan_outstanding or Decimal("0"),
        overdue_principal=overdue_principal or Decimal("0"),
        active_members=active_members or 0,
    )


@router.get("/aging")
async def aging_report(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> dict:
    buckets = {"current": Decimal("0"), "1_30": Decimal("0"), "31_60": Decimal("0"), "61_90": Decimal("0"), "over_90": Decimal("0")}
    installments = await session.execute(select(LoanInstallment.due_date, LoanInstallment.principal, LoanInstallment.status))
    today = date.today()
    for due_date, principal, status in installments:
        if status == "paid":
            continue
        days = (today - due_date).days
        if days <= 0:
            buckets["current"] += Decimal(principal)
        elif days <= 30:
            buckets["1_30"] += Decimal(principal)
        elif days <= 60:
            buckets["31_60"] += Decimal(principal)
        elif days <= 90:
            buckets["61_90"] += Decimal(principal)
        else:
            buckets["over_90"] += Decimal(principal)
    return {key: str(value) for key, value in buckets.items()}


@router.get("/npl")
async def npl_report(
    as_of: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> dict:
    report_date = as_of or date.today()
    exposure = {"current": Decimal("0"), "watch": Decimal("0"), "substandard": Decimal("0"), "doubtful": Decimal("0"), "loss": Decimal("0")}
    provision_rates = {"current": Decimal("0.01"), "watch": Decimal("0.05"), "substandard": Decimal("0.25"), "doubtful": Decimal("0.50"), "loss": Decimal("1.00")}
    installments = await session.execute(select(LoanInstallment.loan_id, LoanInstallment.due_date, LoanInstallment.principal, LoanInstallment.status))
    by_loan: dict = {}
    for loan_id, due_date, principal, status in installments:
        if status == "paid":
            continue
        overdue_days = max(0, (report_date - due_date).days)
        bucket = "current" if overdue_days == 0 else "watch" if overdue_days <= 30 else "substandard" if overdue_days <= 90 else "doubtful" if overdue_days <= 180 else "loss"
        by_loan[loan_id] = max(by_loan.get(loan_id, (0, bucket)), (overdue_days, bucket), key=lambda item: item[0])
    loans = list(await session.scalars(select(Loan).where(Loan.status == "active")))
    for loan in loans:
        bucket = by_loan.get(loan.id, (0, "current"))[1]
        exposure[bucket] += Decimal(loan.outstanding_principal)
    provision = sum((amount * provision_rates[bucket] for bucket, amount in exposure.items()), Decimal("0"))
    total = sum(exposure.values(), Decimal("0"))
    npl = exposure["substandard"] + exposure["doubtful"] + exposure["loss"]
    return {"as_of": report_date.isoformat(), "loan_outstanding": str(total), "npl_outstanding": str(npl), "npl_ratio_percent": str(Decimal("0") if total == 0 else (npl / total * Decimal("100")).quantize(Decimal("0.01"))), "classification_exposure": {key: str(value) for key, value in exposure.items()}, "estimated_provision": str(provision.quantize(Decimal("0.01"))), "provision_rates": {key: str(value * Decimal("100")) for key, value in provision_rates.items()}}


@router.get("/tax")
async def tax_report(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> dict:
    savings_interest = await session.scalar(
        select(func.coalesce(func.sum(SavingsTransaction.amount), 0)).where(SavingsTransaction.trans_type == "interest")
    )
    dividends = await session.scalar(select(func.coalesce(func.sum(ShareTransaction.amount), 0)).where(ShareTransaction.trans_type == "dividend"))
    taxable_withholding_base = Decimal(savings_interest or 0) + Decimal(dividends or 0)
    estimated_tds = (taxable_withholding_base * Decimal("0.05")).quantize(Decimal("0.01"))
    return {
        "savings_interest_paid": str(savings_interest or Decimal("0")),
        "share_dividend_paid": str(dividends or Decimal("0")),
        "estimated_tds_5_percent": str(estimated_tds),
    }


@router.get("/daily-operations")
async def daily_operations(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> dict:
    savings_deposits = await session.scalar(
        select(func.coalesce(func.sum(SavingsTransaction.amount), 0)).where(SavingsTransaction.trans_type == "deposit")
    )
    savings_withdrawals = await session.scalar(
        select(func.coalesce(func.sum(SavingsTransaction.amount), 0)).where(SavingsTransaction.trans_type == "withdraw")
    )
    share_purchases = await session.scalar(select(func.coalesce(func.sum(ShareTransaction.amount), 0)))
    pending_kyc = await session.scalar(select(func.count()).select_from(Member).where(Member.kyc_status == "pending"))
    high_risk_members = await session.scalar(
        select(func.count()).select_from(Member).where((Member.risk_category == "high") | (Member.is_pep.is_(True)) | (Member.is_blacklisted.is_(True)))
    )
    overdue_installments = await session.scalar(select(func.count()).select_from(LoanInstallment).where(LoanInstallment.status == "overdue"))
    day_closings = list(await session.scalars(select(DayClosing).order_by(DayClosing.closing_date_ad.desc()).limit(10)))
    return {
        "cash_in": str(savings_deposits or Decimal("0")),
        "cash_out": str(savings_withdrawals or Decimal("0")),
        "share_cash_in": str(share_purchases or Decimal("0")),
        "pending_kyc": pending_kyc or 0,
        "high_risk_members": high_risk_members or 0,
        "overdue_installments": overdue_installments or 0,
        "day_closings": [
            {
                "id": str(closing.id),
                "closing_date_ad": closing.closing_date_ad.isoformat(),
                "closing_date_bs": closing.closing_date_bs,
                "status": closing.status,
                "cash_summary": closing.cash_summary,
                "exception_summary": closing.exception_summary,
            }
            for closing in day_closings
        ],
    }


@router.get("/approval-queue")
async def approval_queue(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> dict:
    pending_members = list(
        await session.scalars(select(Member).where(Member.kyc_status == "pending").order_by(Member.created_at.desc()).limit(50))
    )
    high_risk_members = list(
        await session.scalars(
            select(Member)
            .where((Member.risk_category == "high") | (Member.is_pep.is_(True)) | (Member.is_blacklisted.is_(True)))
            .order_by(Member.created_at.desc())
            .limit(50)
        )
    )
    overdue_installments = list(
        await session.scalars(select(LoanInstallment).where(LoanInstallment.status == "overdue").order_by(LoanInstallment.due_date).limit(100))
    )
    return {
        "pending_members": [
            {"id": str(member.id), "member_no": member.member_no, "name": member.name, "phone": member.phone, "risk_category": member.risk_category}
            for member in pending_members
        ],
        "high_risk_members": [
            {"id": str(member.id), "member_no": member.member_no, "name": member.name, "phone": member.phone, "risk_category": member.risk_category}
            for member in high_risk_members
        ],
        "overdue_installments": [
            {
                "id": str(item.id),
                "loan_id": str(item.loan_id),
                "installment_no": item.installment_no,
                "due_date": item.due_date.isoformat(),
                "total": str(item.total),
                "penalty": str(item.penalty),
                "status": item.status,
            }
            for item in overdue_installments
        ],
    }


@router.get("/portfolio-export.csv")
async def portfolio_export_csv(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> Response:
    members = list(await session.scalars(select(Member).order_by(Member.member_no).limit(5000)))
    output = StringIO()
    output.write("member_no,name,phone,kyc_status,status,risk_category\n")
    for member in members:
        output.write(
            f"{member.member_no},{member.name},{member.phone or ''},{member.kyc_status},{member.status},{member.risk_category}\n"
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sahakari-member-portfolio.csv"},
    )


@router.get("/runs", response_model=list[ReportRunOut])
async def report_runs(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> list[ReportRun]:
    return list(await session.scalars(select(ReportRun).order_by(ReportRun.created_at.desc()).limit(100)))


@router.post("/runs/{report_type}", response_model=ReportRunOut)
async def generate_report_run(
    report_type: str,
    period_code: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.write")),
) -> ReportRun:
    run = await generate_management_report(session, report_type=report_type, period_code=period_code, generated_by=user.id)
    await session.commit()
    await session.refresh(run)
    return run


@router.get("/activity-feed")
async def activity_feed(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("reports.read")),
) -> list[dict]:
    recent_members = list(await session.scalars(select(Member).order_by(Member.created_at.desc()).limit(10)))
    recent_savings = list(await session.scalars(select(SavingsTransaction).order_by(SavingsTransaction.created_at.desc()).limit(10)))
    
    feed = []
    for m in recent_members:
        feed.append({"type": "member", "title": f"New Member: {m.name}", "date": m.created_at.isoformat()})
    for s in recent_savings:
        feed.append({"type": "savings", "title": f"Savings {s.trans_type}: Rs.{s.amount}", "date": s.created_at.isoformat()})
    
    feed.sort(key=lambda x: x["date"], reverse=True)
    return feed[:10]

