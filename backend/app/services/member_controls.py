from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Member

ELIGIBLE_KYC_STATUSES = {"verified", "approved"}


async def require_financially_eligible_member(session: AsyncSession, member_id: UUID) -> Member:
    member = await session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.status != "active":
        raise HTTPException(status_code=409, detail="Member is not active")
    if member.is_blacklisted:
        raise HTTPException(status_code=409, detail="Blacklisted member cannot transact")
    if member.kyc_status not in ELIGIBLE_KYC_STATUSES:
        raise HTTPException(status_code=409, detail="Member KYC must be approved before financial transactions")
    return member
