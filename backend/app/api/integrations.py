from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import IntegrationEndpoint, User
from app.schemas import IntegrationEndpointCreate, IntegrationEndpointOut
from app.services.audit import audit

router = APIRouter()


@router.get("", response_model=list[IntegrationEndpointOut])
async def list_integrations(
    integration_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("integrations.read")),
) -> list[IntegrationEndpoint]:
    stmt = select(IntegrationEndpoint).order_by(IntegrationEndpoint.integration_type, IntegrationEndpoint.code).limit(limit)
    if integration_type:
        stmt = stmt.where(IntegrationEndpoint.integration_type == integration_type)
    return list(await session.scalars(stmt))


@router.post("", response_model=IntegrationEndpointOut)
async def upsert_integration(
    payload: IntegrationEndpointCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("integrations.write")),
) -> IntegrationEndpoint:
    endpoint = await session.scalar(select(IntegrationEndpoint).where(IntegrationEndpoint.code == payload.code))
    if endpoint is None:
        endpoint = IntegrationEndpoint(**payload.model_dump())
        session.add(endpoint)
        action = "integrations.create"
    else:
        for key, value in payload.model_dump().items():
            setattr(endpoint, key, value)
        action = "integrations.update"
    await session.flush()
    await audit(session, user_id=user.id, action=action, module="integrations", record_id=str(endpoint.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(endpoint)
    return endpoint


@router.post("/{endpoint_id}/check", response_model=IntegrationEndpointOut)
async def check_integration(
    endpoint_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("integrations.write")),
) -> IntegrationEndpoint:
    endpoint = await session.get(IntegrationEndpoint, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Integration endpoint not found")
    endpoint.last_checked_at = datetime.now(timezone.utc)
    await audit(session, user_id=user.id, action="integrations.check", module="integrations", record_id=str(endpoint.id), diff={"status": endpoint.status})
    await session.commit()
    await session.refresh(endpoint)
    return endpoint
