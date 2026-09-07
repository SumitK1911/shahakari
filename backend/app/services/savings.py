from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SavingsAccount, SavingsTransaction
from app.services.accounting import get_account_by_code, post_double_entry
from app.services.member_controls import require_financially_eligible_member
from app.services.audit import audit
from app.services.controls import ensure_period_open


async def get_locked_savings_account(session: AsyncSession, account_id: UUID) -> SavingsAccount:
    account = await session.scalar(
        select(SavingsAccount).where(SavingsAccount.id == account_id).with_for_update()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Savings account not found")
    if account.status != "active":
        raise HTTPException(status_code=409, detail="Savings account is not active")
    return account


async def post_savings_transaction(
    session: AsyncSession,
    *,
    account_id: UUID,
    trans_type: str,
    amount: Decimal,
    narration: str | None,
    user_id: UUID | None,
) -> SavingsAccount:
    await ensure_period_open(session, date.today())
    account = await get_locked_savings_account(session, account_id)
    await require_financially_eligible_member(session, account.member_id)
    previous_balance = account.balance

    if trans_type == "deposit":
        account.balance += amount
        debit_code, credit_code = "1000", "2100"
    elif trans_type == "withdraw":
        if account.balance < amount:
            raise HTTPException(status_code=409, detail="Insufficient balance")
        account.balance -= amount
        debit_code, credit_code = "2100", "1000"
    else:
        raise HTTPException(status_code=400, detail="Unsupported savings transaction type")

    transaction = SavingsTransaction(
        account_id=account.id,
        trans_type=trans_type,
        amount=amount,
        balance=account.balance,
        trans_date=date.today(),
        narration=narration,
        created_by=user_id,
    )
    session.add(transaction)
    await session.flush()

    debit_account = await get_account_by_code(session, debit_code)
    credit_account = await get_account_by_code(session, credit_code)
    await post_double_entry(
        session,
        narration=narration or f"Savings {trans_type}",
        ref_type="savings_transaction",
        ref_id=transaction.id,
        debit_account_id=debit_account.id,
        credit_account_id=credit_account.id,
        amount=amount,
        created_by=user_id,
    )
    await audit(
        session,
        user_id=user_id,
        action=f"savings.{trans_type}",
        module="savings",
        record_id=str(transaction.id),
        diff={"account_id": str(account.id), "before": str(previous_balance), "after": str(account.balance)},
    )
    return account
