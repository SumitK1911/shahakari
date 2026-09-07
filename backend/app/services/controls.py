from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DayClosing


async def ensure_period_open(session: AsyncSession, posting_date: date) -> None:
    closing = await session.scalar(
        select(DayClosing).where(
            DayClosing.closing_date_ad == posting_date,
            DayClosing.locked_at.is_not(None),
        )
    )
    if closing is not None:
        raise HTTPException(status_code=423, detail=f"Posting date {posting_date.isoformat()} is locked")
