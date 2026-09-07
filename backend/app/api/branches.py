from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import Branch, User
from app.schemas import BranchCreate, BranchOut
from app.services.audit import audit

router = APIRouter()


@router.get("", response_model=list[BranchOut])
async def list_branches(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("branches.read")),
) -> list[Branch]:
    return list(await session.scalars(select(Branch).order_by(Branch.name)))


@router.post("", response_model=BranchOut)
async def create_branch(
    payload: BranchCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("branches.write")),
) -> Branch:
    branch = Branch(**payload.model_dump())
    session.add(branch)
    await session.flush()
    await audit(
        session,
        user_id=user.id,
        action="branches.create",
        module="branches",
        record_id=str(branch.id),
        diff=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(branch)
    return branch
