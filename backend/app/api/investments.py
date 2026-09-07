from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import Investment, InvestmentTransaction, User
from app.services.accounting import get_account_by_code, post_double_entry
from app.services.audit import audit
from app.services.rules_engine import money

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class InvestmentCreate(BaseModel):
    investment_no: str
    investment_type: str  # fd, share, bond, mutual_fund, debenture, other
    institution_name: str
    instrument_name: str | None = None
    amount: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    invested_date: date
    maturity_date: date | None = None
    notes: str | None = None


class InvestmentUpdate(BaseModel):
    instrument_name: str | None = None
    interest_rate: Decimal | None = None
    current_value: Decimal | None = None
    maturity_date: date | None = None
    notes: str | None = None
    status: str | None = None


class InvestmentTransactionCreate(BaseModel):
    trans_type: str  # interest_received, principal_redeemed, revaluation, maturity_payout
    amount: Decimal = Field(gt=0)
    trans_date: date
    narration: str | None = None


class InvestmentOut(BaseModel):
    id: UUID
    investment_no: str
    investment_type: str
    institution_name: str
    instrument_name: str | None
    amount: Decimal
    current_value: Decimal
    interest_rate: Decimal
    invested_date: date
    maturity_date: date | None
    maturity_amount: Decimal
    status: str
    notes: str | None

    class Config:
        from_attributes = True


class InvestmentTransactionOut(BaseModel):
    id: UUID
    investment_id: UUID
    trans_type: str
    amount: Decimal
    trans_date: date
    narration: str | None

    class Config:
        from_attributes = True


class InvestmentSummary(BaseModel):
    total_invested: Decimal
    total_current_value: Decimal
    total_interest_received: Decimal
    active_count: int
    matured_count: int
    maturing_within_30_days: int
    by_type: dict[str, Decimal]


# ── Helper ────────────────────────────────────────────────────────────────────

def _calc_maturity(amount: Decimal, rate: Decimal, invested: date, maturity: date | None) -> Decimal:
    if not maturity or rate <= 0:
        return amount
    days = max(0, (maturity - invested).days)
    interest = money(amount * rate / Decimal("100") * Decimal(days) / Decimal("365"))
    return money(amount + interest)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[InvestmentOut])
async def list_investments(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("investments.read")),
) -> list[Investment]:
    return list(await session.scalars(select(Investment).order_by(Investment.invested_date.desc())))


@router.get("/summary", response_model=InvestmentSummary)
async def investment_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("investments.read")),
) -> InvestmentSummary:
    investments = list(await session.scalars(select(Investment)))

    total_invested = Decimal("0")
    total_current = Decimal("0")
    active_count = 0
    matured_count = 0
    maturing_30 = 0
    by_type: dict[str, Decimal] = {}
    today = date.today()
    in_30 = date.fromordinal(today.toordinal() + 30)

    for inv in investments:
        total_invested += inv.amount
        total_current += inv.current_value
        if inv.status == "active":
            active_count += 1
            if inv.maturity_date and today <= inv.maturity_date <= in_30:
                maturing_30 += 1
        elif inv.status == "matured":
            matured_count += 1
        by_type[inv.investment_type] = by_type.get(inv.investment_type, Decimal("0")) + inv.amount

    # Total interest actually received
    interest_result = await session.scalar(
        select(func.sum(InvestmentTransaction.amount)).where(
            InvestmentTransaction.trans_type == "interest_received"
        )
    )
    total_interest = money(interest_result or Decimal("0"))

    return InvestmentSummary(
        total_invested=money(total_invested),
        total_current_value=money(total_current),
        total_interest_received=total_interest,
        active_count=active_count,
        matured_count=matured_count,
        maturing_within_30_days=maturing_30,
        by_type=by_type,
    )


@router.post("", response_model=InvestmentOut)
async def create_investment(
    payload: InvestmentCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("investments.write")),
) -> Investment:
    maturity_amount = _calc_maturity(
        payload.amount, payload.interest_rate, payload.invested_date, payload.maturity_date
    )
    inv = Investment(
        **payload.model_dump(),
        current_value=payload.amount,
        maturity_amount=maturity_amount,
        created_by=user.id,
    )
    session.add(inv)
    await session.flush()

    # Accounting: Debit Investments Asset (1300), Credit Cash (1000).
    # This is part of the same transaction: an investment must never be recorded
    # without its corresponding journal entry.
    inv_account = await get_account_by_code(session, "1300")
    cash_account = await get_account_by_code(session, "1000")
    await post_double_entry(
        session,
        narration=f"Investment outflow - {payload.investment_no} - {payload.institution_name}",
        ref_type="investment",
        ref_id=inv.id,
        debit_account_id=inv_account.id,
        credit_account_id=cash_account.id,
        amount=payload.amount,
        created_by=user.id,
    )

    await audit(
        session,
        user_id=user.id,
        action="investments.create",
        module="investments",
        record_id=str(inv.id),
        diff=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(inv)
    return inv


@router.patch("/{investment_id}", response_model=InvestmentOut)
async def update_investment(
    investment_id: UUID,
    payload: InvestmentUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("investments.write")),
) -> Investment:
    inv = await session.get(Investment, investment_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Investment not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(inv, k, v)
    await session.commit()
    await session.refresh(inv)
    return inv


@router.post("/{investment_id}/transactions", response_model=InvestmentTransactionOut)
async def record_transaction(
    investment_id: UUID,
    payload: InvestmentTransactionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("investments.write")),
) -> InvestmentTransaction:
    inv = await session.get(Investment, investment_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Investment not found")

    tx = InvestmentTransaction(
        investment_id=investment_id,
        trans_type=payload.trans_type,
        amount=money(payload.amount),
        trans_date=payload.trans_date,
        narration=payload.narration,
        created_by=user.id,
    )
    session.add(tx)
    await session.flush()

    # Update current_value on revaluation
    if payload.trans_type == "revaluation":
        inv.current_value = money(payload.amount)
    elif payload.trans_type == "maturity_payout":
        inv.status = "matured"
        inv.current_value = Decimal("0")

    # Accounting entries for interest received.
    if payload.trans_type == "interest_received":
        cash_acc = await get_account_by_code(session, "1000")
        income_acc = await get_account_by_code(session, "4200")
        await post_double_entry(
            session,
            narration=f"Investment interest - {inv.investment_no}",
            ref_type="investment_tx",
            ref_id=tx.id,
            debit_account_id=cash_acc.id,
            credit_account_id=income_acc.id,
            amount=money(payload.amount),
            created_by=user.id,
        )

    await audit(
        session,
        user_id=user.id,
        action="investments.transaction",
        module="investments",
        record_id=str(tx.id),
        diff={"investment_id": str(investment_id), "trans_type": payload.trans_type, "amount": str(payload.amount)},
    )
    await session.commit()
    await session.refresh(tx)
    return tx


@router.get("/{investment_id}/transactions", response_model=list[InvestmentTransactionOut])
async def list_transactions(
    investment_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("investments.read")),
) -> list[InvestmentTransaction]:
    return list(
        await session.scalars(
            select(InvestmentTransaction)
            .where(InvestmentTransaction.investment_id == investment_id)
            .order_by(InvestmentTransaction.trans_date.desc())
        )
    )
