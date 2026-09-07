from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import (
    CalculationResult,
    Loan,
    LoanInstallment,
    LoanPayment,
    Member,
    MemberNominee,
    SavingsAccount,
    SavingsTransaction,
    Share,
    ShareTransaction,
    User,
)
from app.schemas import KycDecisionIn, MemberCreate, MemberOut, MemberUpdate, NomineeCreate, NomineeOut
from app.services.audit import audit

router = APIRouter()

JSON_MEMBER_FIELDS = {
    "address_profile",
    "documents",
    "family_profile",
    "guardian_profile",
    "occupation_profile",
    "income_sources",
    "media_profile",
}


def member_payload(payload: MemberCreate | MemberUpdate, *, exclude_unset: bool = False) -> dict:
    values = payload.model_dump(exclude_unset=exclude_unset)
    json_values = payload.model_dump(mode="json", exclude_unset=exclude_unset)
    for field in JSON_MEMBER_FIELDS:
        if field in json_values:
            values[field] = json_values[field]
    return values


@router.get("", response_model=list[MemberOut])
async def list_members(
    q: str | None = Query(default=None, min_length=2),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("members.read")),
) -> list[Member]:
    stmt = select(Member).order_by(Member.created_at.desc()).offset(skip).limit(limit)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Member.name.ilike(like), Member.phone.ilike(like), Member.member_no.ilike(like)))
    return list(await session.scalars(stmt))


@router.get("/count")
async def count_members(
    q: str | None = Query(default=None, min_length=2),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("members.read")),
) -> dict[str, int]:
    stmt = select(func.count()).select_from(Member)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Member.name.ilike(like), Member.phone.ilike(like), Member.member_no.ilike(like)))
    return {"total": await session.scalar(stmt) or 0}


@router.get("/{member_id}/profile")
async def member_profile(
    member_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("members.read")),
) -> dict:
    member = await session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    nominees = list(await session.scalars(select(MemberNominee).where(MemberNominee.member_id == member_id)))
    shares = list(await session.scalars(select(Share).where(Share.member_id == member_id).order_by(Share.created_at.desc())))
    share_transactions = list(
        await session.scalars(
            select(ShareTransaction).where(ShareTransaction.member_id == member_id).order_by(ShareTransaction.trans_date.desc()).limit(100)
        )
    )
    savings_accounts = list(await session.scalars(select(SavingsAccount).where(SavingsAccount.member_id == member_id).order_by(SavingsAccount.created_at.desc())))
    loans = list(await session.scalars(select(Loan).where(Loan.member_id == member_id).order_by(Loan.created_at.desc())))
    account_ids = [account.id for account in savings_accounts]
    loan_ids = [loan.id for loan in loans]
    savings_transactions = []
    installments = []
    payments = []
    calculation_results = []
    if account_ids:
        savings_transactions = list(
            await session.scalars(
                select(SavingsTransaction)
                .where(SavingsTransaction.account_id.in_(account_ids))
                .order_by(SavingsTransaction.trans_date.desc(), SavingsTransaction.created_at.desc())
                .limit(200)
            )
        )
        calculation_results.extend(
            list(
                await session.scalars(
                    select(CalculationResult)
                    .where(CalculationResult.target_type == "savings_account", CalculationResult.target_id.in_(account_ids))
                    .order_by(CalculationResult.created_at.desc())
                    .limit(100)
                )
            )
        )
    if loan_ids:
        installments = list(
            await session.scalars(
                select(LoanInstallment)
                .where(LoanInstallment.loan_id.in_(loan_ids))
                .order_by(LoanInstallment.due_date, LoanInstallment.installment_no)
                .limit(300)
            )
        )
        payments = list(
            await session.scalars(
                select(LoanPayment)
                .where(LoanPayment.loan_id.in_(loan_ids))
                .order_by(LoanPayment.payment_date.desc(), LoanPayment.created_at.desc())
                .limit(200)
            )
        )
        installment_ids = [installment.id for installment in installments]
        if installment_ids:
            calculation_results.extend(
                list(
                    await session.scalars(
                        select(CalculationResult)
                        .where(CalculationResult.target_type == "loan_installment", CalculationResult.target_id.in_(installment_ids))
                        .order_by(CalculationResult.created_at.desc())
                        .limit(100)
                    )
                )
            )
    return {
        "member": MemberOut.model_validate(member).model_dump(mode="json"),
        "nominees": [NomineeOut.model_validate(nominee).model_dump(mode="json") for nominee in nominees],
        "shares": [
            {
                "id": str(share.id),
                "member_id": str(share.member_id),
                "total_share": share.total_share,
                "rate": str(share.rate),
                "total_amount": str(share.total_amount),
                "status": share.status,
            }
            for share in shares
        ],
        "share_transactions": [
            {
                "id": str(transaction.id),
                "trans_type": transaction.trans_type,
                "shares": transaction.shares,
                "rate": str(transaction.rate),
                "amount": str(transaction.amount),
                "trans_date": transaction.trans_date.isoformat(),
                "narration": transaction.narration,
            }
            for transaction in share_transactions
        ],
        "savings_accounts": [
            {
                "id": str(account.id),
                "member_id": str(account.member_id),
                "account_no": account.account_no,
                "account_type": account.account_type,
                "interest_rate": str(account.interest_rate),
                "balance": str(account.balance),
                "status": account.status,
            }
            for account in savings_accounts
        ],
        "savings_transactions": [
            {
                "id": str(transaction.id),
                "account_id": str(transaction.account_id),
                "trans_type": transaction.trans_type,
                "amount": str(transaction.amount),
                "balance": str(transaction.balance),
                "trans_date": transaction.trans_date.isoformat(),
                "narration": transaction.narration,
            }
            for transaction in savings_transactions
        ],
        "loans": [
            {
                "id": str(loan.id),
                "member_id": str(loan.member_id),
                "loan_no": loan.loan_no,
                "loan_type": loan.loan_type,
                "amount": str(loan.amount),
                "interest_rate": str(loan.interest_rate),
                "tenure_months": loan.tenure_months,
                "outstanding_principal": str(loan.outstanding_principal),
                "status": loan.status,
            }
            for loan in loans
        ],
        "loan_installments": [
            {
                "id": str(installment.id),
                "loan_id": str(installment.loan_id),
                "installment_no": installment.installment_no,
                "due_date": installment.due_date.isoformat(),
                "principal": str(installment.principal),
                "interest": str(installment.interest),
                "penalty": str(installment.penalty),
                "total": str(installment.total),
                "status": installment.status,
            }
            for installment in installments
        ],
        "loan_payments": [
            {
                "id": str(payment.id),
                "loan_id": str(payment.loan_id),
                "installment_id": str(payment.installment_id) if payment.installment_id else None,
                "payment_date": payment.payment_date.isoformat(),
                "principal_paid": str(payment.principal_paid),
                "interest_paid": str(payment.interest_paid),
                "penalty_paid": str(payment.penalty_paid),
                "total_paid": str(payment.total_paid),
                "paid_by": payment.paid_by,
            }
            for payment in payments
        ],
        "calculation_results": [
            {
                "id": str(result.id),
                "result_type": result.result_type,
                "target_type": result.target_type,
                "calculation_date_ad": result.calculation_date_ad.isoformat(),
                "base_amount": str(result.base_amount),
                "rate": str(result.rate),
                "days": result.days,
                "amount": str(result.amount),
                "status": result.status,
            }
            for result in calculation_results[:150]
        ],
    }


@router.post("", response_model=MemberOut)
async def create_member(
    payload: MemberCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("members.write")),
) -> Member:
    values = member_payload(payload)
    member = Member(**values)
    session.add(member)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Member number already exists") from exc
    await audit(
        session,
        user_id=user.id,
        action="members.create",
        module="members",
        record_id=str(member.id),
        diff=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(member)
    return member


@router.patch("/{member_id}", response_model=MemberOut)
async def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("members.write")),
) -> Member:
    member = await session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    changes = member_payload(payload, exclude_unset=True)
    if "kyc_status" in changes:
        raise HTTPException(status_code=403, detail="Use the dedicated KYC approval or rejection action")
    before = {key: getattr(member, key) for key in changes}
    for key, value in changes.items():
        setattr(member, key, value)
    await audit(
        session,
        user_id=user.id,
        action="members.update",
        module="members",
        record_id=str(member.id),
        diff={"before": before, "after": payload.model_dump(mode="json", exclude_unset=True)},
    )
    await session.commit()
    await session.refresh(member)
    return member


@router.post("/{member_id}/kyc/approve", response_model=MemberOut)
async def approve_kyc(
    member_id: UUID,
    payload: KycDecisionIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("members.kyc.approve")),
) -> Member:
    member = await session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.is_blacklisted:
        raise HTTPException(status_code=409, detail="Blacklisted member KYC cannot be approved")
    member.kyc_status = "approved"
    await audit(session, user_id=user.id, action="members.kyc.approve", module="members", record_id=str(member.id), diff={"decision_note": payload.decision_note})
    await session.commit()
    await session.refresh(member)
    return member


@router.post("/{member_id}/kyc/reject", response_model=MemberOut)
async def reject_kyc(
    member_id: UUID,
    payload: KycDecisionIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("members.kyc.approve")),
) -> Member:
    member = await session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    member.kyc_status = "rejected"
    await audit(session, user_id=user.id, action="members.kyc.reject", module="members", record_id=str(member.id), diff={"decision_note": payload.decision_note})
    await session.commit()
    await session.refresh(member)
    return member


@router.post("/{member_id}/nominees", response_model=NomineeOut)
async def add_nominee(
    member_id: UUID,
    payload: NomineeCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("members.write")),
) -> MemberNominee:
    member = await session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    nominee = MemberNominee(member_id=member_id, **payload.model_dump())
    session.add(nominee)
    await session.flush()
    await audit(
        session,
        user_id=user.id,
        action="members.nominee.create",
        module="members",
        record_id=str(nominee.id),
        diff=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(nominee)
    return nominee
