from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def audit(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    module: str,
    record_id: str | None = None,
    diff: dict | None = None,
) -> None:
    session.add(AuditLog(user_id=user_id, action=action, module=module, record_id=record_id, diff=jsonable_encoder(diff)))
