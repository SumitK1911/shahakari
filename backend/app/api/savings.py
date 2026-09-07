from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import Member, SavingsAccount, SavingsTransaction, User
from app.schemas import DepositWithdrawIn, SavingsAccountCreate, SavingsAccountOut
from app.services.audit import audit
from app.services.member_controls import require_financially_eligible_member
from app.services.savings import post_savings_transaction

router = APIRouter()


@router.get("/accounts", response_model=list[SavingsAccountOut])
async def list_accounts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("savings.read")),
) -> list[SavingsAccount]:
    return list(await session.scalars(select(SavingsAccount).order_by(SavingsAccount.created_at.desc()).limit(100)))


@router.get("/accounts/{account_id}/statement")
async def account_statement(
    account_id: UUID,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("savings.read")),
) -> dict:
    account = await session.get(SavingsAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Savings account not found")
    stmt = select(SavingsTransaction).where(SavingsTransaction.account_id == account_id)
    if from_date:
        stmt = stmt.where(SavingsTransaction.trans_date >= from_date)
    if to_date:
        stmt = stmt.where(SavingsTransaction.trans_date <= to_date)
    rows = list(await session.scalars(stmt.order_by(SavingsTransaction.trans_date, SavingsTransaction.created_at)))
    return {
        "account": SavingsAccountOut.model_validate(account).model_dump(mode="json"),
        "period": {"from": from_date.isoformat() if from_date else None, "to": to_date.isoformat() if to_date else None},
        "transactions": [
            {"id": str(row.id), "date": row.trans_date.isoformat(), "type": row.trans_type, "amount": str(row.amount), "balance": str(row.balance), "narration": row.narration}
            for row in rows
        ],
    }


@router.post("/accounts", response_model=SavingsAccountOut)
async def create_account(
    payload: SavingsAccountCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("savings.write")),
) -> SavingsAccount:
    await require_financially_eligible_member(session, payload.member_id)
    account = SavingsAccount(**payload.model_dump())
    session.add(account)
    await session.flush()
    await audit(
        session,
        user_id=user.id,
        action="savings.account.create",
        module="savings",
        record_id=str(account.id),
        diff=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(account)
    return account


@router.post("/accounts/{account_id}/deposit", response_model=SavingsAccountOut)
async def deposit(
    account_id: UUID,
    payload: DepositWithdrawIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("savings.write")),
) -> SavingsAccount:
    account = await post_savings_transaction(
        session,
        account_id=account_id,
        trans_type="deposit",
        amount=payload.amount,
        narration=payload.narration,
        user_id=user.id,
    )
    await session.commit()
    await session.refresh(account)
    return account


@router.post("/accounts/{account_id}/withdraw", response_model=SavingsAccountOut)
async def withdraw(
    account_id: UUID,
    payload: DepositWithdrawIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("savings.write")),
) -> SavingsAccount:
    account = await post_savings_transaction(
        session,
        account_id=account_id,
        trans_type="withdraw",
        amount=payload.amount,
        narration=payload.narration,
        user_id=user.id,
    )
    await session.commit()
    await session.refresh(account)
    return account
