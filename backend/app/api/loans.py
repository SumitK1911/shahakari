from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import Loan, LoanCollateral, LoanGuarantor, LoanInstallment, LoanPayment, LoanRecoveryAction, LoanReview, User
from app.schemas import (
    LoanApplicationCreate,
    LoanApprovalIn,
    LoanCollateralCreate,
    LoanCollateralOut,
    LoanCreate,
    LoanGuarantorCreate,
    LoanGuarantorOut,
    LoanInstallmentOut,
    LoanOut,
    LoanPaymentIn,
    LoanPaymentOut,
    LoanRecoveryActionCreate,
    LoanRecalculateIn,
    LoanReviewCreate,
    LoanReviewOut,
)
from app.services.audit import audit
from app.services.loans import add_loan_review, approve_loan_application, create_loan_application, disburse_approved_loan, repay_installment, recalculate_pending_installments

router = APIRouter()


@router.get("", response_model=list[LoanOut])
async def list_loans(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.read")),
) -> list[Loan]:
    return list(await session.scalars(select(Loan).order_by(Loan.created_at.desc()).limit(100)))


@router.post("", response_model=LoanOut)
async def create_loan(
    payload: LoanApplicationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.application.create")),
) -> Loan:
    loan = await create_loan_application(session, **payload.model_dump(), user_id=user.id)
    await session.commit()
    await session.refresh(loan)
    return loan


@router.post("/{loan_id}/reviews", response_model=LoanReviewOut)
async def review_loan(
    loan_id: UUID,
    payload: LoanReviewCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.review")),
) -> LoanReview:
    review = await add_loan_review(session, loan_id=loan_id, **payload.model_dump(), user_id=user.id)
    await session.commit()
    await session.refresh(review)
    return review


@router.post("/{loan_id}/approve", response_model=LoanOut)
async def approve_loan(
    loan_id: UUID,
    payload: LoanApprovalIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.approve")),
) -> Loan:
    loan = await approve_loan_application(session, loan_id=loan_id, **payload.model_dump(), user_id=user.id)
    await session.commit()
    await session.refresh(loan)
    return loan


@router.post("/{loan_id}/disburse", response_model=LoanOut)
async def disburse_loan(
    loan_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.disburse")),
) -> Loan:
    loan = await disburse_approved_loan(session, loan_id=loan_id, user_id=user.id)
    await session.commit()
    await session.refresh(loan)
    return loan


@router.get("/{loan_id}/installments", response_model=list[LoanInstallmentOut])
async def list_installments(
    loan_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.read")),
) -> list[LoanInstallment]:
    stmt = select(LoanInstallment).where(LoanInstallment.loan_id == loan_id).order_by(LoanInstallment.installment_no)
    return list(await session.scalars(stmt))


@router.post("/{loan_id}/payments", response_model=LoanPaymentOut)
async def pay_installment(
    loan_id: UUID,
    payload: LoanPaymentIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.write")),
) -> LoanPayment:
    payment = await repay_installment(
        session,
        loan_id=loan_id,
        installment_id=payload.installment_id,
        paid_by=payload.paid_by,
        user_id=user.id,
    )
    await session.commit()
    await session.refresh(payment)
    return payment


@router.post("/{loan_id}/recalculate", response_model=LoanOut)
async def recalculate_loan_installments(
    loan_id: UUID,
    payload: LoanRecalculateIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.write")),
) -> Loan:
    loan = await recalculate_pending_installments(
        session,
        loan_id=loan_id,
        new_interest_rate=payload.new_interest_rate,
        user_id=user.id,
    )
    await session.commit()
    await session.refresh(loan)
    return loan


@router.get("/{loan_id}/recovery-actions")
async def list_recovery_actions(
    loan_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.recovery.read")),
) -> list[dict]:
    rows = list(await session.scalars(select(LoanRecoveryAction).where(LoanRecoveryAction.loan_id == loan_id).order_by(LoanRecoveryAction.action_date.desc())))
    return [{"id": str(row.id), "action_date": row.action_date.isoformat(), "action_type": row.action_type, "outcome": row.outcome, "promised_amount": str(row.promised_amount) if row.promised_amount else None, "promised_date": row.promised_date.isoformat() if row.promised_date else None, "next_action_date": row.next_action_date.isoformat() if row.next_action_date else None, "status": row.status} for row in rows]


@router.post("/{loan_id}/recovery-actions")
async def create_recovery_action(
    loan_id: UUID,
    payload: LoanRecoveryActionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.recovery.write")),
) -> dict:
    loan = await session.get(Loan, loan_id)
    if loan is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Loan not found")
    record = LoanRecoveryAction(loan_id=loan_id, created_by=user.id, **payload.model_dump())
    session.add(record)
    await session.flush()
    await audit(session, user_id=user.id, action="loans.recovery.action", module="loans", record_id=str(record.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    return {"id": str(record.id), "loan_id": str(loan_id), "status": record.status}


@router.post("/{loan_id}/guarantors", response_model=LoanGuarantorOut)
async def add_guarantor(
    loan_id: UUID,
    payload: LoanGuarantorCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.write")),
) -> LoanGuarantor:
    guarantor = LoanGuarantor(loan_id=loan_id, **payload.model_dump())
    session.add(guarantor)
    await session.flush()
    await audit(session, user_id=user.id, action="loans.guarantor.add", module="loans", record_id=str(guarantor.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(guarantor)
    return guarantor


@router.post("/{loan_id}/collaterals", response_model=LoanCollateralOut)
async def add_collateral(
    loan_id: UUID,
    payload: LoanCollateralCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("loans.write")),
) -> LoanCollateral:
    collateral = LoanCollateral(loan_id=loan_id, **payload.model_dump())
    session.add(collateral)
    await session.flush()
    await audit(session, user_id=user.id, action="loans.collateral.add", module="loans", record_id=str(collateral.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(collateral)
    return collateral
