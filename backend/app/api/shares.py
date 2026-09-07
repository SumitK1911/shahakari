from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import Share, User
from app.schemas import DividendRunIn, DividendRunOut, ShareOut, SharePurchaseIn, ShareRefundIn, ShareTransferIn
from app.services.shares import post_dividends, purchase_shares, refund_shares, transfer_shares

router = APIRouter()


@router.get("", response_model=list[ShareOut])
async def list_shares(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("shares.read")),
) -> list[Share]:
    return list(await session.scalars(select(Share).order_by(Share.created_at.desc()).limit(100)))


@router.post("/purchase", response_model=ShareOut)
async def buy_shares(
    payload: SharePurchaseIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("shares.write")),
) -> Share:
    share = await purchase_shares(session, **payload.model_dump(), user_id=user.id)
    await session.commit()
    await session.refresh(share)
    return share


@router.post("/transfer", response_model=ShareOut)
async def move_shares(
    payload: ShareTransferIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("shares.write")),
) -> Share:
    share = await transfer_shares(session, **payload.model_dump(), user_id=user.id)
    await session.commit()
    await session.refresh(share)
    return share


@router.post("/refund", response_model=ShareOut)
async def return_shares(
    payload: ShareRefundIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("shares.write")),
) -> Share:
    share = await refund_shares(session, **payload.model_dump(), user_id=user.id)
    await session.commit()
    await session.refresh(share)
    return share


@router.post("/dividends", response_model=DividendRunOut)
async def pay_dividends(
    payload: DividendRunIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("shares.write")),
) -> dict:
    result = await post_dividends(session, **payload.model_dump(), user_id=user.id)
    await session.commit()
    return result
