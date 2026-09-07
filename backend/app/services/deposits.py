from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Member, TermDeposit, TermDepositTransaction
from app.services.accounting import get_account_by_code, post_double_entry
from app.services.audit import audit
from app.services.controls import ensure_period_open
from app.services.loans import add_months
from app.services.member_controls import require_financially_eligible_member
from app.services.rules_engine import money


def calculate_maturity_amount(principal: Decimal, annual_rate: Decimal, opened_date: date, maturity_date: date) -> Decimal:
    days = max(0, (maturity_date - opened_date).days)
    interest = principal * annual_rate / Decimal("100") * Decimal(days) / Decimal("365")
    return money(principal + interest)


async def create_term_deposit(
    session: AsyncSession,
    *,
    member_id: UUID,
    deposit_no: str,
    deposit_type: str,
    principal_amount: Decimal,
    installment_amount: Decimal | None,
    interest_rate: Decimal,
    opened_date: date | None,
    tenure_months: int,
    user_id: UUID | None,
) -> TermDeposit:
    opened_on = opened_date or date.today()
    await ensure_period_open(session, opened_on)
    await require_financially_eligible_member(session, member_id)
    maturity_date = add_months(opened_on, tenure_months)
    maturity_amount = calculate_maturity_amount(principal_amount, interest_rate, opened_on, maturity_date)
    deposit = TermDeposit(
        member_id=member_id,
        deposit_no=deposit_no,
        deposit_type=deposit_type,
        principal_amount=principal_amount,
        installment_amount=installment_amount,
        interest_rate=interest_rate,
        opened_date=opened_on,
        maturity_date=maturity_date,
        maturity_amount=maturity_amount,
        balance=principal_amount,
        status="active",
    )
    session.add(deposit)
    await session.flush()
    session.add(
        TermDepositTransaction(
            deposit_id=deposit.id,
            trans_type="open",
            amount=principal_amount,
            balance=deposit.balance,
            trans_date=opened_on,
            narration="Term deposit opening",
            created_by=user_id,
        )
    )
    cash = await get_account_by_code(session, "1000")
    term_liability = await get_account_by_code(session, "2200")
    await post_double_entry(
        session,
        narration=f"{deposit_type.upper()} opening {deposit_no}",
        ref_type="term_deposit",
        ref_id=deposit.id,
        debit_account_id=cash.id,
        credit_account_id=term_liability.id,
        amount=principal_amount,
        created_by=user_id,
        entry_date=opened_on,
    )
    await audit(
        session,
        user_id=user_id,
        action="deposits.create",
        module="deposits",
        record_id=str(deposit.id),
        diff={"deposit_no": deposit_no, "deposit_type": deposit_type, "principal_amount": str(principal_amount)},
    )
    return deposit


async def mature_term_deposit(
    session: AsyncSession,
    *,
    deposit_id: UUID,
    user_id: UUID | None,
) -> TermDeposit:
    await ensure_period_open(session, date.today())
    deposit = await session.scalar(select(TermDeposit).where(TermDeposit.id == deposit_id).with_for_update())
    if deposit is None:
        raise HTTPException(status_code=404, detail="Term deposit not found")
    if deposit.status != "active":
        raise HTTPException(status_code=409, detail="Term deposit is not active")
    interest_amount = max(Decimal("0"), deposit.maturity_amount - deposit.balance)
    if interest_amount:
        deposit.balance += interest_amount
        session.add(
            TermDepositTransaction(
                deposit_id=deposit.id,
                trans_type="interest",
                amount=interest_amount,
                balance=deposit.balance,
                trans_date=date.today(),
                narration="Maturity interest",
                created_by=user_id,
            )
        )
        interest_expense = await get_account_by_code(session, "5100")
        term_liability = await get_account_by_code(session, "2200")
        await post_double_entry(
            session,
            narration=f"Term deposit interest {deposit.deposit_no}",
            ref_type="term_deposit",
            ref_id=deposit.id,
            debit_account_id=interest_expense.id,
            credit_account_id=term_liability.id,
            amount=interest_amount,
            created_by=user_id,
        )
    deposit.status = "matured"
    await audit(
        session,
        user_id=user_id,
        action="deposits.mature",
        module="deposits",
        record_id=str(deposit.id),
        diff={"deposit_no": deposit.deposit_no, "maturity_amount": str(deposit.balance)},
    )
    return deposit


async def payout_term_deposit(
    session: AsyncSession,
    *,
    deposit_id: UUID,
    user_id: UUID | None,
) -> TermDeposit:
    await ensure_period_open(session, date.today())
    deposit = await session.scalar(select(TermDeposit).where(TermDeposit.id == deposit_id).with_for_update())
    if deposit is None:
        raise HTTPException(status_code=404, detail="Term deposit not found")
    if deposit.status not in {"active", "matured"}:
        raise HTTPException(status_code=409, detail="Term deposit cannot be paid out")
    payout_amount = deposit.balance
    deposit.balance = Decimal("0")
    deposit.status = "paid"
    session.add(
        TermDepositTransaction(
            deposit_id=deposit.id,
            trans_type="payout",
            amount=payout_amount,
            balance=deposit.balance,
            trans_date=date.today(),
            narration="Term deposit payout",
            created_by=user_id,
        )
    )
    term_liability = await get_account_by_code(session, "2200")
    cash = await get_account_by_code(session, "1000")
    await post_double_entry(
        session,
        narration=f"Term deposit payout {deposit.deposit_no}",
        ref_type="term_deposit",
        ref_id=deposit.id,
        debit_account_id=term_liability.id,
        credit_account_id=cash.id,
        amount=payout_amount,
        created_by=user_id,
    )
    await audit(
        session,
        user_id=user_id,
        action="deposits.payout",
        module="deposits",
        record_id=str(deposit.id),
        diff={"deposit_no": deposit.deposit_no, "payout_amount": str(payout_amount)},
    )
    return deposit
