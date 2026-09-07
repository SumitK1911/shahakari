from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Member, Share, ShareTransaction, SavingsAccount, SavingsTransaction
from app.services.accounting import get_account_by_code, post_double_entry
from app.services.rules_engine import money
from app.services.audit import audit
from app.services.controls import ensure_period_open
from app.services.member_controls import require_financially_eligible_member


async def purchase_shares(
    session: AsyncSession,
    *,
    member_id: UUID,
    shares: int,
    rate: Decimal,
    narration: str | None,
    user_id: UUID | None,
) -> Share:
    await ensure_period_open(session, date.today())
    if shares <= 0:
        raise HTTPException(status_code=400, detail="Shares must be positive")
    await require_financially_eligible_member(session, member_id)

    share = await session.scalar(select(Share).where(Share.member_id == member_id).with_for_update())
    if share is None:
        share = Share(member_id=member_id, total_share=0, rate=rate, total_amount=0)
        session.add(share)
        await session.flush()

    amount = Decimal(shares) * rate
    before = share.total_amount
    share.total_share += shares
    share.rate = rate
    share.total_amount += amount

    transaction = ShareTransaction(
        member_id=member_id,
        trans_type="purchase",
        shares=shares,
        rate=rate,
        amount=amount,
        trans_date=date.today(),
        narration=narration,
        created_by=user_id,
    )
    session.add(transaction)
    await session.flush()

    debit_account = await get_account_by_code(session, "1000")
    credit_account = await get_account_by_code(session, "3000")
    await post_double_entry(
        session,
        narration=narration or "Share purchase",
        ref_type="share_transaction",
        ref_id=transaction.id,
        debit_account_id=debit_account.id,
        credit_account_id=credit_account.id,
        amount=amount,
        created_by=user_id,
    )
    await audit(
        session,
        user_id=user_id,
        action="shares.purchase",
        module="shares",
        record_id=str(transaction.id),
        diff={"member_id": str(member_id), "before": str(before), "after": str(share.total_amount)},
    )
    return share


async def transfer_shares(
    session: AsyncSession,
    *,
    from_member_id: UUID,
    to_member_id: UUID,
    shares: int,
    narration: str | None,
    user_id: UUID | None,
) -> Share:
    await ensure_period_open(session, date.today())
    if from_member_id == to_member_id:
        raise HTTPException(status_code=400, detail="Source and target members must be different")
    await require_financially_eligible_member(session, from_member_id)
    await require_financially_eligible_member(session, to_member_id)
    source = await session.scalar(select(Share).where(Share.member_id == from_member_id).with_for_update())
    if source is None or source.total_share < shares:
        raise HTTPException(status_code=409, detail="Insufficient shares to transfer")
    target = await session.scalar(select(Share).where(Share.member_id == to_member_id).with_for_update())
    if target is None:
        target = Share(member_id=to_member_id, total_share=0, rate=source.rate, total_amount=0)
        session.add(target)
        await session.flush()

    amount = Decimal(shares) * source.rate
    source.total_share -= shares
    source.total_amount -= amount
    target.total_share += shares
    target.rate = source.rate
    target.total_amount += amount
    session.add_all(
        [
            ShareTransaction(
                member_id=from_member_id,
                trans_type="transfer_out",
                shares=shares,
                rate=source.rate,
                amount=amount,
                trans_date=date.today(),
                narration=narration,
                created_by=user_id,
            ),
            ShareTransaction(
                member_id=to_member_id,
                trans_type="transfer_in",
                shares=shares,
                rate=source.rate,
                amount=amount,
                trans_date=date.today(),
                narration=narration,
                created_by=user_id,
            ),
        ]
    )
    await audit(
        session,
        user_id=user_id,
        action="shares.transfer",
        module="shares",
        record_id=str(source.id),
        diff={"from_member_id": str(from_member_id), "to_member_id": str(to_member_id), "shares": shares},
    )
    return source


async def refund_shares(
    session: AsyncSession,
    *,
    member_id: UUID,
    shares: int,
    narration: str | None,
    user_id: UUID | None,
) -> Share:
    await ensure_period_open(session, date.today())
    share = await session.scalar(select(Share).where(Share.member_id == member_id).with_for_update())
    if share is None or share.total_share < shares:
        raise HTTPException(status_code=409, detail="Insufficient shares to refund")
    amount = Decimal(shares) * share.rate
    before = share.total_amount
    share.total_share -= shares
    share.total_amount -= amount
    transaction = ShareTransaction(
        member_id=member_id,
        trans_type="refund",
        shares=shares,
        rate=share.rate,
        amount=amount,
        trans_date=date.today(),
        narration=narration,
        created_by=user_id,
    )
    session.add(transaction)
    await session.flush()
    debit_account = await get_account_by_code(session, "3000")
    credit_account = await get_account_by_code(session, "1000")
    await post_double_entry(
        session,
        narration=narration or "Share refund",
        ref_type="share_transaction",
        ref_id=transaction.id,
        debit_account_id=debit_account.id,
        credit_account_id=credit_account.id,
        amount=amount,
        created_by=user_id,
    )
    await audit(
        session,
        user_id=user_id,
        action="shares.refund",
        module="shares",
        record_id=str(transaction.id),
        diff={"member_id": str(member_id), "before": str(before), "after": str(share.total_amount)},
    )
    return share


async def post_dividends(
    session: AsyncSession,
    *,
    dividend_rate_percent: Decimal,
    narration: str | None,
    user_id: UUID | None,
) -> dict:
    await ensure_period_open(session, date.today())
    dividend_expense = await get_account_by_code(session, "5300")
    savings_liability = await get_account_by_code(session, "2100")
    cash = await get_account_by_code(session, "1000")
    
    paid_to_savings = 0
    paid_to_cash = 0
    total = Decimal("0")
    shares = list(await session.scalars(select(Share).where(Share.status == "active", Share.total_amount > 0).with_for_update()))
    for share in shares:
        amount = money(share.total_amount * dividend_rate_percent / Decimal("100"))
        if amount <= 0:
            continue
            
        transaction = ShareTransaction(
            member_id=share.member_id,
            trans_type="dividend",
            shares=0,
            rate=dividend_rate_percent,
            amount=amount,
            trans_date=date.today(),
            narration=narration,
            created_by=user_id,
        )
        session.add(transaction)
        
        # Try to find a primary savings account
        savings = await session.scalar(
            select(SavingsAccount)
            .where(SavingsAccount.member_id == share.member_id, SavingsAccount.status == "active")
            .order_by(SavingsAccount.created_at)
            .limit(1)
            .with_for_update()
        )
        
        if savings:
            savings.balance = money(savings.balance + amount)
            session.add(
                SavingsTransaction(
                    account_id=savings.id,
                    trans_type="deposit",
                    amount=amount,
                    balance=savings.balance,
                    trans_date=date.today(),
                    narration=f"Share dividend for year {date.today().year}",
                )
            )
            await session.flush()
            await post_double_entry(
                session,
                narration=narration or "Share dividend to savings",
                ref_type="share_transaction",
                ref_id=transaction.id,
                debit_account_id=dividend_expense.id,
                credit_account_id=savings_liability.id,
                amount=amount,
                created_by=user_id,
            )
            paid_to_savings += 1
        else:
            await session.flush()
            await post_double_entry(
                session,
                narration=narration or "Share dividend payment (Cash)",
                ref_type="share_transaction",
                ref_id=transaction.id,
                debit_account_id=dividend_expense.id,
                credit_account_id=cash.id,
                amount=amount,
                created_by=user_id,
            )
            paid_to_cash += 1
            
        total += amount
        
    await audit(
        session,
        user_id=user_id,
        action="shares.dividend",
        module="shares",
        record_id=None,
        diff={"dividend_rate_percent": str(dividend_rate_percent), "paid_to_savings": paid_to_savings, "paid_to_cash": paid_to_cash, "total_dividend": str(total)},
    )
    return {"dividend_rate_percent": str(dividend_rate_percent), "paid_to_savings": paid_to_savings, "paid_to_cash": paid_to_cash, "total_dividend": str(total)}
