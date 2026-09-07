from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import CashSession, SavingsTransaction, User
from app.schemas import CashSessionCloseIn, CashSessionOpenIn, CashSessionOut
from app.services.audit import audit

router = APIRouter()


@router.get("/sessions", response_model=list[CashSessionOut])
async def list_cash_sessions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("cash.read")),
) -> list[CashSession]:
    return list(await session.scalars(select(CashSession).order_by(CashSession.session_date.desc(), CashSession.created_at.desc()).limit(100)))


@router.post("/sessions/open", response_model=CashSessionOut)
async def open_cash_session(
    payload: CashSessionOpenIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("cash.write")),
) -> CashSession:
    existing = await session.scalar(
        select(CashSession).where(CashSession.cashier_id == user.id, CashSession.session_date == date.today())
    )
    if existing is not None:
        if existing.status == "open":
            return existing
        raise HTTPException(status_code=409, detail="A cash session has already been closed for this cashier today")
    record = CashSession(
        branch_id=user.branch_id,
        cashier_id=user.id,
        session_date=date.today(),
        opening_cash=payload.opening_cash,
        denomination_open=payload.denomination_open,
    )
    session.add(record)
    await session.flush()
    await audit(session, user_id=user.id, action="cash.session.open", module="cash", record_id=str(record.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(record)
    return record


@router.post("/sessions/{session_id}/close", response_model=CashSessionOut)
async def close_cash_session(
    session_id: UUID,
    payload: CashSessionCloseIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("cash.write")),
) -> CashSession:
    record = await session.get(CashSession, session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Cash session not found")
    if record.status != "open":
        raise HTTPException(status_code=409, detail="Cash session is not open")
    if record.cashier_id != user.id:
        raise HTTPException(status_code=403, detail="Only the session cashier can close this cash session")
    record.closing_cash = payload.closing_cash
    record.denomination_close = payload.denomination_close
    record.handover_to = payload.handover_to
    record.status = "closed"
    await audit(session, user_id=user.id, action="cash.session.close", module="cash", record_id=str(record.id), diff=payload.model_dump(mode="json"))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A cash session has already been closed for this cashier today") from exc
    await session.refresh(record)
    return record


@router.get("/sessions/summary")
async def cash_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("cash.read")),
) -> dict:
    sessions = list(await session.scalars(select(CashSession).where(CashSession.session_date == date.today()).order_by(CashSession.created_at.desc())))
    for record in sessions:
        cash_in = Decimal("0")
        cash_out = Decimal("0")
        # Savings transactions are physical cash only when posted by this session's
        # cashier. System postings (interest/dividends) and other cashiers must not
        # alter this counter's cashbook.
        txs = await session.scalars(
            select(SavingsTransaction).where(
                SavingsTransaction.trans_date == record.session_date,
                SavingsTransaction.created_by == record.cashier_id,
            )
        )
        for tx in txs:
            if tx.trans_type == "deposit":
                cash_in += tx.amount
            elif tx.trans_type == "withdraw":
                cash_out += tx.amount
        record.cash_in = cash_in
        record.cash_out = cash_out
    return {
        "open_sessions": sum(1 for item in sessions if item.status == "open"),
        "closed_sessions": sum(1 for item in sessions if item.status == "closed"),
        "cash_in": str(sum((item.cash_in for item in sessions), Decimal("0"))),
        "cash_out": str(sum((item.cash_out for item in sessions), Decimal("0"))),
        "sessions": [CashSessionOut.model_validate(item).model_dump(mode="json") for item in sessions],
    }
