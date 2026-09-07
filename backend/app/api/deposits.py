from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import TermDeposit, TermDepositTransaction, User
from app.schemas import TermDepositCreate, TermDepositOut, TermDepositTransactionOut
from app.services.deposits import create_term_deposit, mature_term_deposit, payout_term_deposit

router = APIRouter()


@router.get("", response_model=list[TermDepositOut])
async def list_term_deposits(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("deposits.read")),
) -> list[TermDeposit]:
    return list(await session.scalars(select(TermDeposit).order_by(TermDeposit.created_at.desc()).limit(200)))


@router.post("", response_model=TermDepositOut)
async def open_term_deposit(
    payload: TermDepositCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("deposits.write")),
) -> TermDeposit:
    deposit = await create_term_deposit(session, **payload.model_dump(), user_id=user.id)
    await session.commit()
    await session.refresh(deposit)
    return deposit


@router.post("/{deposit_id}/mature", response_model=TermDepositOut)
async def mature_deposit(
    deposit_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("deposits.write")),
) -> TermDeposit:
    deposit = await mature_term_deposit(session, deposit_id=deposit_id, user_id=user.id)
    await session.commit()
    await session.refresh(deposit)
    return deposit


@router.post("/{deposit_id}/payout", response_model=TermDepositOut)
async def payout_deposit(
    deposit_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("deposits.write")),
) -> TermDeposit:
    deposit = await payout_term_deposit(session, deposit_id=deposit_id, user_id=user.id)
    await session.commit()
    await session.refresh(deposit)
    return deposit


@router.get("/{deposit_id}/transactions", response_model=list[TermDepositTransactionOut])
async def list_term_deposit_transactions(
    deposit_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("deposits.read")),
) -> list[TermDepositTransaction]:
    stmt = (
        select(TermDepositTransaction)
        .where(TermDepositTransaction.deposit_id == deposit_id)
        .order_by(TermDepositTransaction.trans_date.desc(), TermDepositTransaction.created_at.desc())
    )
    return list(await session.scalars(stmt))
