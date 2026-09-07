from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import NotificationMessage, User
from app.schemas import NotificationCreate, NotificationOut
from app.services.notifications import dispatch_queued_notifications, queue_notification, queue_operational_notifications

router = APIRouter()


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("notifications.read")),
) -> list[NotificationMessage]:
    stmt = select(NotificationMessage).order_by(NotificationMessage.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(NotificationMessage.status == status)
    return list(await session.scalars(stmt))


@router.post("", response_model=NotificationOut)
async def create_notification(
    payload: NotificationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("notifications.write")),
) -> NotificationMessage:
    message = await queue_notification(session, **payload.model_dump())
    await session.commit()
    await session.refresh(message)
    return message


@router.post("/dispatch")
async def dispatch_notifications(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("notifications.write")),
) -> dict[str, int]:
    result = await dispatch_queued_notifications(session)
    await session.commit()
    return result

@router.post("/generate-operational-reminders")
async def generate_operational_reminders(
    due_days: int = Query(default=3, ge=0, le=30),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("notifications.write")),
) -> dict[str, int]:
    result = await queue_operational_notifications(session, due_days=due_days)
    await session.commit()
    return result
