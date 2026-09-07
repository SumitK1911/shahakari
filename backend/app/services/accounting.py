from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, JournalEntry, LedgerEntry


async def get_account_by_code(session: AsyncSession, code: str) -> Account:
    account = await session.scalar(select(Account).where(Account.code == code, Account.is_active.is_(True)))
    if account is None:
        raise HTTPException(status_code=500, detail=f"Accounting account {code} is not configured")
    return account


async def post_double_entry(
    session: AsyncSession,
    *,
    narration: str,
    ref_type: str,
    ref_id: UUID,
    debit_account_id: UUID,
    credit_account_id: UUID,
    amount: Decimal,
    created_by: UUID | None,
    entry_date: date | None = None,
) -> JournalEntry:
    if amount <= 0:
        raise ValueError("Amount must be positive")

    if debit_account_id == credit_account_id:
        raise ValueError("Debit and credit account cannot be the same")

    journal = JournalEntry(
        entry_date=entry_date or date.today(),
        narration=narration,
        ref_type=ref_type,
        ref_id=ref_id,
        created_by=created_by,
    )
    session.add(journal)
    await session.flush()
    session.add_all(
        [
            LedgerEntry(journal_id=journal.id, account_id=debit_account_id, debit=amount, credit=0),
            LedgerEntry(journal_id=journal.id, account_id=credit_account_id, debit=0, credit=amount),
        ]
    )
    return journal
