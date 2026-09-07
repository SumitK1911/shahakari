from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import (
    AccrualRule,
    CalculationResult,
    InterestRule,
    PenaltyRule,
    SchedulerJob,
    User,
)
from app.schemas import (
    AccrualRuleCreate,
    AccrualRuleOut,
    AccrualRuleUpdate,
    CalculationResultOut,
    InterestRuleCreate,
    InterestRuleOut,
    InterestRuleUpdate,
    PenaltyRuleCreate,
    PenaltyRuleOut,
    PenaltyRuleUpdate,
    SchedulerJobOut,
)
from app.services.audit import audit

router = APIRouter()


async def get_or_404(session: AsyncSession, model: type, record_id: UUID):
    record = await session.get(model, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return record


def apply_updates(record, payload) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(record, key, value)
    return changes


@router.get("/interest-rules", response_model=list[InterestRuleOut])
async def list_interest_rules(
    scope_type: str | None = None,
    scope_code: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.read")),
) -> list[InterestRule]:
    stmt = select(InterestRule).order_by(InterestRule.created_at.desc()).limit(limit)
    if scope_type:
        stmt = stmt.where(InterestRule.scope_type == scope_type)
    if scope_code:
        stmt = stmt.where(InterestRule.scope_code == scope_code)
    if active_only:
        stmt = stmt.where(InterestRule.is_active.is_(True))
    return list(await session.scalars(stmt))


@router.post("/interest-rules", response_model=InterestRuleOut)
async def create_interest_rule(
    payload: InterestRuleCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> InterestRule:
    rule = InterestRule(**payload.model_dump())
    session.add(rule)
    await session.flush()
    await audit(
        session,
        user_id=user.id,
        action="rules.interest.create",
        module="rules",
        record_id=str(rule.id),
        diff=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.patch("/interest-rules/{rule_id}", response_model=InterestRuleOut)
async def update_interest_rule(
    rule_id: UUID,
    payload: InterestRuleUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> InterestRule:
    rule = await get_or_404(session, InterestRule, rule_id)
    changes = apply_updates(rule, payload)
    await audit(
        session,
        user_id=user.id,
        action="rules.interest.update",
        module="rules",
        record_id=str(rule.id),
        diff=changes,
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.post("/interest-rules/{rule_id}/deactivate", response_model=InterestRuleOut)
async def deactivate_interest_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> InterestRule:
    rule = await get_or_404(session, InterestRule, rule_id)
    rule.is_active = False
    await audit(session, user_id=user.id, action="rules.interest.deactivate", module="rules", record_id=str(rule.id))
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/penalty-rules", response_model=list[PenaltyRuleOut])
async def list_penalty_rules(
    scope_type: str | None = None,
    scope_code: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.read")),
) -> list[PenaltyRule]:
    stmt = select(PenaltyRule).order_by(PenaltyRule.created_at.desc()).limit(limit)
    if scope_type:
        stmt = stmt.where(PenaltyRule.scope_type == scope_type)
    if scope_code:
        stmt = stmt.where(PenaltyRule.scope_code == scope_code)
    if active_only:
        stmt = stmt.where(PenaltyRule.is_active.is_(True))
    return list(await session.scalars(stmt))


@router.post("/penalty-rules", response_model=PenaltyRuleOut)
async def create_penalty_rule(
    payload: PenaltyRuleCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> PenaltyRule:
    rule = PenaltyRule(**payload.model_dump())
    session.add(rule)
    await session.flush()
    await audit(
        session,
        user_id=user.id,
        action="rules.penalty.create",
        module="rules",
        record_id=str(rule.id),
        diff=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.patch("/penalty-rules/{rule_id}", response_model=PenaltyRuleOut)
async def update_penalty_rule(
    rule_id: UUID,
    payload: PenaltyRuleUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> PenaltyRule:
    rule = await get_or_404(session, PenaltyRule, rule_id)
    changes = apply_updates(rule, payload)
    await audit(
        session,
        user_id=user.id,
        action="rules.penalty.update",
        module="rules",
        record_id=str(rule.id),
        diff=changes,
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.post("/penalty-rules/{rule_id}/deactivate", response_model=PenaltyRuleOut)
async def deactivate_penalty_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> PenaltyRule:
    rule = await get_or_404(session, PenaltyRule, rule_id)
    rule.is_active = False
    await audit(session, user_id=user.id, action="rules.penalty.deactivate", module="rules", record_id=str(rule.id))
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/accrual-rules", response_model=list[AccrualRuleOut])
async def list_accrual_rules(
    scope_type: str | None = None,
    scope_code: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.read")),
) -> list[AccrualRule]:
    stmt = select(AccrualRule).order_by(AccrualRule.created_at.desc()).limit(limit)
    if scope_type:
        stmt = stmt.where(AccrualRule.scope_type == scope_type)
    if scope_code:
        stmt = stmt.where(AccrualRule.scope_code == scope_code)
    if active_only:
        stmt = stmt.where(AccrualRule.is_active.is_(True))
    return list(await session.scalars(stmt))


@router.post("/accrual-rules", response_model=AccrualRuleOut)
async def create_accrual_rule(
    payload: AccrualRuleCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> AccrualRule:
    rule = AccrualRule(**payload.model_dump())
    session.add(rule)
    await session.flush()
    await audit(
        session,
        user_id=user.id,
        action="rules.accrual.create",
        module="rules",
        record_id=str(rule.id),
        diff=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.patch("/accrual-rules/{rule_id}", response_model=AccrualRuleOut)
async def update_accrual_rule(
    rule_id: UUID,
    payload: AccrualRuleUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> AccrualRule:
    rule = await get_or_404(session, AccrualRule, rule_id)
    changes = apply_updates(rule, payload)
    await audit(
        session,
        user_id=user.id,
        action="rules.accrual.update",
        module="rules",
        record_id=str(rule.id),
        diff=changes,
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.post("/accrual-rules/{rule_id}/deactivate", response_model=AccrualRuleOut)
async def deactivate_accrual_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.write")),
) -> AccrualRule:
    rule = await get_or_404(session, AccrualRule, rule_id)
    rule.is_active = False
    await audit(session, user_id=user.id, action="rules.accrual.deactivate", module="rules", record_id=str(rule.id))
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/scheduler-jobs", response_model=list[SchedulerJobOut])
async def list_scheduler_jobs(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.read")),
) -> list[SchedulerJob]:
    stmt = select(SchedulerJob).order_by(SchedulerJob.name).limit(limit)
    if status:
        stmt = stmt.where(SchedulerJob.status == status)
    return list(await session.scalars(stmt))


@router.get("/calculation-results", response_model=list[CalculationResultOut])
async def list_calculation_results(
    result_type: str | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("rules.read")),
) -> list[CalculationResult]:
    stmt = select(CalculationResult).order_by(CalculationResult.created_at.desc()).limit(limit)
    if result_type:
        stmt = stmt.where(CalculationResult.result_type == result_type)
    if target_type:
        stmt = stmt.where(CalculationResult.target_type == target_type)
    if target_id:
        stmt = stmt.where(CalculationResult.target_id == target_id)
    return list(await session.scalars(stmt))
