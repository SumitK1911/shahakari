from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import ApprovalRequest, User
from app.schemas import ApprovalCreate, ApprovalDecisionIn, ApprovalOut
from app.services.audit import audit

router = APIRouter()


@router.get("", response_model=list[ApprovalOut])
async def list_approvals(
    status: str | None = "pending",
    module: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("approvals.read")),
) -> list[ApprovalRequest]:
    stmt = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(ApprovalRequest.status == status)
    if module:
        stmt = stmt.where(ApprovalRequest.module == module)
    return list(await session.scalars(stmt))


@router.post("", response_model=ApprovalOut)
async def create_approval(
    payload: ApprovalCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("approvals.write")),
) -> ApprovalRequest:
    request = ApprovalRequest(**payload.model_dump(), requested_by=user.id)
    session.add(request)
    await session.flush()
    await audit(session, user_id=user.id, action="approvals.request", module="approvals", record_id=str(request.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(request)
    return request


async def decide(
    approval_id: UUID,
    status: str,
    payload: ApprovalDecisionIn,
    session: AsyncSession,
    user: User,
) -> ApprovalRequest:
    request = await session.get(ApprovalRequest, approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="Approval request already decided")
    request.status = status
    request.approved_by = user.id
    request.approved_at = datetime.now(timezone.utc)
    request.decision_note = payload.decision_note
    await audit(session, user_id=user.id, action=f"approvals.{status}", module="approvals", record_id=str(request.id), diff={"decision_note": payload.decision_note})
    await session.commit()
    await session.refresh(request)
    return request


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
async def approve_request(
    approval_id: UUID,
    payload: ApprovalDecisionIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("approvals.decide")),
) -> ApprovalRequest:
    return await decide(approval_id, "approved", payload, session, user)


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
async def reject_request(
    approval_id: UUID,
    payload: ApprovalDecisionIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("approvals.decide")),
) -> ApprovalRequest:
    return await decide(approval_id, "rejected", payload, session, user)
