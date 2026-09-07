from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Loan, LoanInstallment, LoanPayment, LoanReview
from app.services.accounting import get_account_by_code, post_double_entry
from app.services.audit import audit
from app.services.controls import ensure_period_open
from app.services.rules_engine import money
from app.services.member_controls import require_financially_eligible_member


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


async def generate_flat_installments(session: AsyncSession, loan: Loan, start_date: date) -> None:
    """Generate flat, reducing-balance EMI, or interest-only installments."""
    if loan.interest_method == "reducing_balance":
        monthly_rate = loan.interest_rate / Decimal("1200")
        if monthly_rate == 0:
            payment = money(loan.amount / Decimal(loan.tenure_months))
        else:
            factor = (Decimal("1") + monthly_rate) ** loan.tenure_months
            payment = money(loan.amount * monthly_rate * factor / (factor - Decimal("1")))
        remaining = loan.amount
        for index in range(1, loan.tenure_months + 1):
            interest = money(remaining * monthly_rate)
            principal = money(payment - interest)
            if index == loan.tenure_months or principal > remaining:
                principal = remaining
            session.add(LoanInstallment(loan_id=loan.id, installment_no=index, due_date=add_months(start_date, index), principal=principal, interest=interest, total=money(principal + interest)))
            remaining = money(remaining - principal)
        return

    monthly_interest = money(loan.amount * loan.interest_rate / Decimal("1200"))
    regular_principal = money(loan.amount / Decimal(loan.tenure_months))
    for index in range(1, loan.tenure_months + 1):
        if loan.repayment_method == "interest_only":
            principal = loan.amount if index == loan.tenure_months else Decimal("0")
        else:
            principal = regular_principal if index < loan.tenure_months else loan.amount - regular_principal * Decimal(loan.tenure_months - 1)
        session.add(LoanInstallment(loan_id=loan.id, installment_no=index, due_date=add_months(start_date, index), principal=money(principal), interest=monthly_interest, total=money(principal + monthly_interest)))


async def recalculate_pending_installments(
    session: AsyncSession,
    *,
    loan_id: UUID,
    new_interest_rate: Decimal,
    user_id: UUID | None,
) -> Loan:
    await ensure_period_open(session, date.today())
    loan = await session.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.status != "active":
        raise HTTPException(status_code=409, detail="Only active loans can be recalculated")
        
    loan.interest_rate = new_interest_rate
    
    pending_installments = await session.scalars(
        select(LoanInstallment)
        .where(LoanInstallment.loan_id == loan_id, LoanInstallment.status == "pending")
        .order_by(LoanInstallment.installment_no)
        .with_for_update()
    )
    
    new_monthly_interest = money((loan.amount * new_interest_rate / Decimal("100")) / Decimal("12"))
    
    for installment in pending_installments:
        installment.interest = new_monthly_interest
        installment.total = money(installment.principal + installment.interest + installment.penalty)
        
    await audit(
        session,
        user_id=user_id,
        action="loans.recalculate",
        module="loans",
        record_id=str(loan.id),
        diff={"new_interest_rate": str(new_interest_rate)},
    )
    return loan


async def create_disbursed_loan(
    session: AsyncSession,
    *,
    member_id: UUID,
    loan_no: str,
    loan_type: str,
    amount: Decimal,
    interest_rate: Decimal,
    tenure_months: int,
    user_id: UUID | None,
) -> Loan:
    await ensure_period_open(session, date.today())
    await require_financially_eligible_member(session, member_id)
    loan = Loan(
        member_id=member_id,
        loan_no=loan_no,
        loan_type=loan_type,
        amount=amount,
        interest_rate=interest_rate,
        tenure_months=tenure_months,
        outstanding_principal=amount,
        status="active",
        disburse_date=date.today(),
    )
    session.add(loan)
    await session.flush()
    await generate_flat_installments(session, loan, date.today())

    debit_account = await get_account_by_code(session, "1200")
    credit_account = await get_account_by_code(session, "1000")
    await post_double_entry(
        session,
        narration=f"Loan disbursement {loan_no}",
        ref_type="loan",
        ref_id=loan.id,
        debit_account_id=debit_account.id,
        credit_account_id=credit_account.id,
        amount=amount,
        created_by=user_id,
    )
    await audit(
        session,
        user_id=user_id,
        action="loans.disburse",
        module="loans",
        record_id=str(loan.id),
        diff={"loan_no": loan_no, "amount": str(amount)},
    )
    return loan


async def repay_installment(
    session: AsyncSession,
    *,
    loan_id: UUID,
    installment_id: UUID,
    paid_by: str | None,
    user_id: UUID | None,
) -> LoanPayment:
    await ensure_period_open(session, date.today())
    loan = await session.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
    installment = await session.scalar(
        select(LoanInstallment).where(LoanInstallment.id == installment_id, LoanInstallment.loan_id == loan_id).with_for_update()
    )
    if loan is None or installment is None:
        raise HTTPException(status_code=404, detail="Loan or installment not found")
    if installment.status == "paid":
        raise HTTPException(status_code=409, detail="Installment is already paid")

    total_paid = installment.principal + installment.interest + installment.penalty
    before = loan.outstanding_principal
    loan.outstanding_principal = max(Decimal("0"), loan.outstanding_principal - installment.principal)
    installment.status = "paid"
    if loan.outstanding_principal == 0:
        loan.status = "closed"

    payment = LoanPayment(
        loan_id=loan.id,
        installment_id=installment.id,
        payment_date=date.today(),
        principal_paid=installment.principal,
        interest_paid=installment.interest,
        penalty_paid=installment.penalty,
        total_paid=total_paid,
        paid_by=paid_by,
    )
    session.add(payment)
    await session.flush()

    cash = await get_account_by_code(session, "1000")
    loan_receivable = await get_account_by_code(session, "1200")
    interest_income = await get_account_by_code(session, "4100")
    await post_double_entry(
        session,
        narration=f"Loan repayment {loan.loan_no}",
        ref_type="loan_payment",
        ref_id=payment.id,
        debit_account_id=cash.id,
        credit_account_id=loan_receivable.id,
        amount=installment.principal,
        created_by=user_id,
    )
    if installment.interest > 0:
        await post_double_entry(
            session,
            narration=f"Loan interest {loan.loan_no}",
            ref_type="loan_payment",
            ref_id=payment.id,
            debit_account_id=cash.id,
            credit_account_id=interest_income.id,
            amount=installment.interest + installment.penalty,
            created_by=user_id,
        )

    await audit(
        session,
        user_id=user_id,
        action="loans.repay",
        module="loans",
        record_id=str(payment.id),
        diff={"loan_id": str(loan.id), "before": str(before), "after": str(loan.outstanding_principal)},
    )
    return payment

async def create_loan_application(
    session: AsyncSession,
    *,
    member_id: UUID,
    loan_no: str,
    loan_type: str,
    amount: Decimal,
    interest_rate: Decimal,
    tenure_months: int,
    purpose: str | None,
    interest_method: str = "flat_monthly",
    repayment_method: str = "emi",
    user_id: UUID | None = None,
) -> Loan:
    await ensure_period_open(session, date.today())
    await require_financially_eligible_member(session, member_id)
    loan = Loan(
        member_id=member_id,
        loan_no=loan_no,
        loan_type=loan_type,
        amount=amount,
        interest_rate=interest_rate,
        tenure_months=tenure_months,
        outstanding_principal=Decimal("0"),
        status="application",
        applied_by=user_id,
        purpose=purpose,
        interest_method=interest_method,
        repayment_method=repayment_method,
    )
    session.add(loan)
    await session.flush()
    await audit(session, user_id=user_id, action="loans.application.create", module="loans", record_id=str(loan.id), diff={"loan_no": loan_no, "amount": str(amount)})
    return loan


async def add_loan_review(
    session: AsyncSession,
    *,
    loan_id: UUID,
    stage: str,
    recommendation: str,
    comments: str | None,
    risk_score: int | None,
    details: dict | None,
    user_id: UUID,
) -> LoanReview:
    loan = await session.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.applied_by == user_id:
        raise HTTPException(status_code=409, detail="Applicant creator cannot recommend/review the same loan")
    review = LoanReview(
        loan_id=loan_id,
        stage=stage,
        recommendation=recommendation,
        comments=comments,
        reviewed_by=user_id,
        reviewed_at=datetime.now(timezone.utc),
        risk_score=risk_score,
        details=details,
    )
    session.add(review)
    if recommendation in {"recommend", "recommended", "approve"}:
        loan.status = "recommended"
        loan.recommended_by = user_id
    elif recommendation in {"reject", "rejected"}:
        loan.status = "rejected"
    await session.flush()
    await audit(session, user_id=user_id, action="loans.review", module="loans", record_id=str(loan.id), diff={"recommendation": recommendation, "stage": stage})
    return review


async def approve_loan_application(
    session: AsyncSession,
    *,
    loan_id: UUID,
    approval_limit_level: str,
    comments: str | None,
    user_id: UUID,
) -> Loan:
    loan = await session.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.status not in {"application", "recommended"}:
        raise HTTPException(status_code=409, detail="Loan is not awaiting approval")
    if user_id in {loan.applied_by, loan.recommended_by}:
        raise HTTPException(status_code=409, detail="Same user cannot create/recommend and approve loan")
    loan.status = "approved"
    loan.approved_by = user_id
    loan.approved_at = datetime.now(timezone.utc)
    loan.approval_limit_level = approval_limit_level
    await audit(session, user_id=user_id, action="loans.approve", module="loans", record_id=str(loan.id), diff={"approval_limit_level": approval_limit_level, "comments": comments})
    return loan


async def disburse_approved_loan(session: AsyncSession, *, loan_id: UUID, user_id: UUID) -> Loan:
    await ensure_period_open(session, date.today())
    loan = await session.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.status != "approved":
        raise HTTPException(status_code=409, detail="Loan must be approved before disbursement")
    if user_id in {loan.applied_by, loan.recommended_by, loan.approved_by}:
        raise HTTPException(status_code=409, detail="Same user cannot create/recommend/approve and disburse loan")
    loan.status = "active"
    loan.disburse_date = date.today()
    loan.disbursed_by = user_id
    loan.disbursed_at = datetime.now(timezone.utc)
    loan.outstanding_principal = loan.amount
    await generate_flat_installments(session, loan, date.today())
    debit_account = await get_account_by_code(session, "1200")
    credit_account = await get_account_by_code(session, "1000")
    await post_double_entry(
        session,
        narration=f"Loan disbursement {loan.loan_no}",
        ref_type="loan",
        ref_id=loan.id,
        debit_account_id=debit_account.id,
        credit_account_id=credit_account.id,
        amount=loan.amount,
        created_by=user_id,
    )
    await audit(session, user_id=user_id, action="loans.disburse", module="loans", record_id=str(loan.id), diff={"loan_no": loan.loan_no, "amount": str(loan.amount)})
    return loan
