from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import hash_password
from app.dependencies import require_permission
from app.models import Branch, Role, User
from app.schemas import RoleOut, UserAdminOut, UserCreate, UserUpdate
from app.services.audit import audit

router = APIRouter()


def serialize_user(user: User, role: Role | None) -> UserAdminOut:
    return UserAdminOut(
        id=user.id, name=user.name, email=user.email, status=user.status,
        branch_id=user.branch_id, role_id=user.role_id, role_name=role.name if role else None,
        last_login_at=user.last_login_at, created_at=user.created_at,
    )


async def validate_assignment(session: AsyncSession, role_id: UUID | None, branch_id: UUID | None) -> None:
    if role_id is not None and await session.get(Role, role_id) is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if branch_id is not None and await session.get(Branch, branch_id) is None:
        raise HTTPException(status_code=404, detail="Branch not found")


@router.get("", response_model=list[UserAdminOut])
async def list_users(session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("users.read"))) -> list[UserAdminOut]:
    users = list(await session.scalars(select(User).order_by(User.name).limit(500)))
    roles = {role.id: role for role in await session.scalars(select(Role))}
    return [serialize_user(item, roles.get(item.role_id)) for item in users]


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("users.read"))) -> list[Role]:
    return list(await session.scalars(select(Role).order_by(Role.name)))


@router.post("", response_model=UserAdminOut, status_code=201)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("users.write"))) -> UserAdminOut:
    await validate_assignment(session, payload.role_id, payload.branch_id)
    record = User(name=payload.name.strip(), email=str(payload.email).lower(), password_hash=hash_password(payload.password), branch_id=payload.branch_id, role_id=payload.role_id)
    session.add(record)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="User email already exists") from exc
    await audit(session, user_id=user.id, action="users.create", module="users", record_id=str(record.id), diff={"email": record.email, "role_id": str(record.role_id) if record.role_id else None})
    await session.commit()
    await session.refresh(record)
    return serialize_user(record, await session.get(Role, record.role_id) if record.role_id else None)


@router.patch("/{user_id}", response_model=UserAdminOut)
async def update_user(user_id: UUID, payload: UserUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("users.write"))) -> UserAdminOut:
    record = await session.get(User, user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    if "role_id" in changes or "branch_id" in changes:
        await validate_assignment(session, changes.get("role_id", record.role_id), changes.get("branch_id", record.branch_id))
    if "password" in changes:
        changes["password_hash"] = hash_password(changes.pop("password"))
    for key, value in changes.items():
        setattr(record, key, value)
    await audit(session, user_id=user.id, action="users.update", module="users", record_id=str(record.id), diff={key: str(value) for key, value in changes.items() if key != "password_hash"})
    await session.commit()
    await session.refresh(record)
    return serialize_user(record, await session.get(Role, record.role_id) if record.role_id else None)
