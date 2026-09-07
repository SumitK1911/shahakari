from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import User
from app.schemas import AutomationRunIn, AutomationRunOut, AutomationTriggerOut, AutomationPostDividendsIn
from app.services.automation import run_finance_automation
from app.services.shares import post_dividends
from app.worker import daily_interest, mark_overdue_installments

router = APIRouter()


@router.post("/run", response_model=AutomationRunOut)
async def run_automation_now(
    payload: AutomationRunIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("automation.run")),
) -> AutomationRunOut:
    result = await run_finance_automation(
        session,
        run_date=payload.run_date or date.today(),
    )
    await session.commit()
    return AutomationRunOut(**result)

@router.post("/post-dividends")
async def distribute_dividends(
    payload: AutomationPostDividendsIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("automation.run")),
) -> dict:
    result = await post_dividends(
        session,
        dividend_rate_percent=payload.dividend_rate_percent,
        narration=payload.narration,
        user_id=user.id,
    )
    await session.commit()
    return result


@router.post("/daily-interest", response_model=AutomationTriggerOut)
async def trigger_daily_interest(
    user: User = Depends(require_permission("automation.run")),
) -> AutomationTriggerOut:
    task = daily_interest.delay()
    return AutomationTriggerOut(task_id=task.id, task_name="automation.daily_interest", status="queued")


@router.post("/mark-overdue", response_model=AutomationTriggerOut)
async def trigger_mark_overdue(
    user: User = Depends(require_permission("automation.run")),
) -> AutomationTriggerOut:
    task = mark_overdue_installments.delay()
    return AutomationTriggerOut(task_id=task.id, task_name="automation.mark_overdue_installments", status="queued")
