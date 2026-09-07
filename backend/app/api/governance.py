from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import FieldVisit, GovernanceDecision, OrganizationPosition, SystemPolicy, User
from app.schemas import FieldVisitCreate, FieldVisitOut, GovernanceDecisionCreate, GovernanceDecisionOut, SystemPolicyCreate, SystemPolicyOut
from app.services.audit import audit

router = APIRouter()


@router.get("/policies", response_model=list[SystemPolicyOut])
async def list_policies(
    policy_type: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("governance.read")),
) -> list[SystemPolicy]:
    stmt = select(SystemPolicy).order_by(SystemPolicy.policy_type, SystemPolicy.code)
    if policy_type:
        stmt = stmt.where(SystemPolicy.policy_type == policy_type)
    return list(await session.scalars(stmt))


@router.post("/policies", response_model=SystemPolicyOut)
async def upsert_policy(
    payload: SystemPolicyCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("governance.write")),
) -> SystemPolicy:
    policy = await session.scalar(select(SystemPolicy).where(SystemPolicy.code == payload.code))
    if policy is None:
        policy = SystemPolicy(**payload.model_dump())
        session.add(policy)
        action = "governance.policy.create"
    else:
        for key, value in payload.model_dump().items():
            setattr(policy, key, value)
        action = "governance.policy.update"
    await session.flush()
    await audit(session, user_id=user.id, action=action, module="governance", record_id=str(policy.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(policy)
    return policy


@router.get("/decisions", response_model=list[GovernanceDecisionOut])
async def list_decisions(
    decision_body: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("governance.read")),
) -> list[GovernanceDecision]:
    stmt = select(GovernanceDecision).order_by(GovernanceDecision.decision_date.desc()).limit(500)
    if decision_body:
        stmt = stmt.where(GovernanceDecision.decision_body == decision_body)
    return list(await session.scalars(stmt))


@router.post("/decisions", response_model=GovernanceDecisionOut)
async def create_decision(
    payload: GovernanceDecisionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("governance.write")),
) -> GovernanceDecision:
    values = payload.model_dump()
    if values.get("decision_date") is None:
        values.pop("decision_date")
    decision = GovernanceDecision(**values, minuted_by=user.id)
    session.add(decision)
    await session.flush()
    await audit(session, user_id=user.id, action="governance.decision.create", module="governance", record_id=str(decision.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(decision)
    return decision


@router.get("/field-visits", response_model=list[FieldVisitOut])
async def list_field_visits(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_visits.read")),
) -> list[FieldVisit]:
    return list(await session.scalars(select(FieldVisit).order_by(FieldVisit.visit_date.desc(), FieldVisit.created_at.desc()).limit(500)))


@router.post("/field-visits", response_model=FieldVisitOut)
async def create_field_visit(
    payload: FieldVisitCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_visits.write")),
) -> FieldVisit:
    values = payload.model_dump()
    if values.get("visit_date") is None:
        values.pop("visit_date")
    visit = FieldVisit(**values, visited_by=user.id)
    session.add(visit)
    await session.flush()
    await audit(session, user_id=user.id, action="field_visit.create", module="field_visits", record_id=str(visit.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(visit)
    return visit


@router.get("/organization")
async def organization_chart(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("governance.read")),
) -> list[dict]:
    positions = list(await session.scalars(select(OrganizationPosition).order_by(OrganizationPosition.level, OrganizationPosition.code)))
    return [
        {"code": item.code, "title": item.title, "level": item.level, "reports_to_code": item.reports_to_code, "status": item.status}
        for item in positions
    ]
