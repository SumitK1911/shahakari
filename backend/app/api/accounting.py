from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import Account, JournalEntry, LedgerEntry, User
from app.schemas import AccountOut, TrialBalanceRow

router = APIRouter()


@router.get("/accounts", response_model=list[AccountOut])
async def chart_of_accounts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("accounting.read")),
) -> list[Account]:
    return list(await session.scalars(select(Account).order_by(Account.code)))


@router.get("/trial-balance", response_model=list[TrialBalanceRow])
async def trial_balance(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("accounting.read")),
) -> list[TrialBalanceRow]:
    stmt = (
        select(
            Account.code,
            Account.name,
            func.coalesce(func.sum(LedgerEntry.debit), 0).label("debit"),
            func.coalesce(func.sum(LedgerEntry.credit), 0).label("credit"),
        )
        .join(LedgerEntry, LedgerEntry.account_id == Account.id, isouter=True)
        .group_by(Account.id)
        .order_by(Account.code)
    )
    rows = await session.execute(stmt)
    return [
        TrialBalanceRow(
            account_code=code,
            account_name=name,
            debit=debit,
            credit=credit,
            balance=Decimal(debit) - Decimal(credit),
        )
        for code, name, debit, credit in rows
    ]


@router.get("/ledger/{account_code}")
async def ledger(
    account_code: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("accounting.read")),
) -> dict:
    account = await session.scalar(select(Account).where(Account.code == account_code))
    if account is None:
        return {"account_code": account_code, "rows": []}
    stmt = (
        select(JournalEntry.entry_date, JournalEntry.narration, JournalEntry.ref_type, LedgerEntry.debit, LedgerEntry.credit)
        .join(JournalEntry, JournalEntry.id == LedgerEntry.journal_id)
        .where(LedgerEntry.account_id == account.id)
        .order_by(JournalEntry.entry_date, LedgerEntry.created_at)
    )
    balance = Decimal("0")
    rows = []
    for entry_date, narration, ref_type, debit, credit in await session.execute(stmt):
        balance += Decimal(debit) - Decimal(credit)
        rows.append(
            {
                "entry_date": entry_date.isoformat(),
                "narration": narration,
                "ref_type": ref_type,
                "debit": str(debit),
                "credit": str(credit),
                "balance": str(balance),
            }
        )
    return {"account_code": account.code, "account_name": account.name, "account_type": account.type, "rows": rows}


@router.get("/profit-loss")
async def profit_loss(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("accounting.read")),
) -> dict:
    rows = await _statement_rows(session, ["income", "expense"])
    income = sum(Decimal(row["credit"]) - Decimal(row["debit"]) for row in rows if row["type"] == "income")
    expense = sum(Decimal(row["debit"]) - Decimal(row["credit"]) for row in rows if row["type"] == "expense")
    return {"statement_name": "Profit and Loss", "rows": rows, "totals": {"income": str(income), "expense": str(expense), "net_profit": str(income - expense)}}


@router.get("/balance-sheet")
async def balance_sheet(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("accounting.read")),
) -> dict:
    rows = await _statement_rows(session, ["asset", "liability", "equity"])
    assets = sum(Decimal(row["debit"]) - Decimal(row["credit"]) for row in rows if row["type"] == "asset")
    liabilities = sum(Decimal(row["credit"]) - Decimal(row["debit"]) for row in rows if row["type"] == "liability")
    equity = sum(Decimal(row["credit"]) - Decimal(row["debit"]) for row in rows if row["type"] == "equity")
    return {
        "statement_name": "Balance Sheet",
        "rows": rows,
        "totals": {"assets": str(assets), "liabilities": str(liabilities), "equity": str(equity), "check": str(assets - liabilities - equity)},
    }


async def _statement_rows(session: AsyncSession, account_types: list[str]) -> list[dict]:
    stmt = (
        select(
            Account.code,
            Account.name,
            Account.type,
            func.coalesce(func.sum(LedgerEntry.debit), 0).label("debit"),
            func.coalesce(func.sum(LedgerEntry.credit), 0).label("credit"),
        )
        .join(LedgerEntry, LedgerEntry.account_id == Account.id, isouter=True)
        .where(Account.type.in_(account_types))
        .group_by(Account.id)
        .order_by(Account.code)
    )
    return [
        {"account_code": code, "account_name": name, "type": account_type, "debit": str(debit), "credit": str(credit)}
        for code, name, account_type, debit, credit in await session.execute(stmt)
    ]
