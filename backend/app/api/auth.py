from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import create_access_token, verify_password
from app.dependencies import current_user
from app.models import Permission, Role, RolePermission, User
from app.schemas import LoginIn, TokenOut, UserSessionOut

router = APIRouter()


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, session: AsyncSession = Depends(get_session)) -> TokenOut:
    try:
        user = await session.scalar(select(User).where(User.email == payload.email.strip(), User.status == "active"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable",
        ) from exc
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenOut(access_token=create_access_token(str(user.id), {"email": user.email}))


@router.get("/me", response_model=UserSessionOut)
async def me(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> UserSessionOut:
    role_name = None
    permissions: list[str] = []
    if user.role_id:
        role = await session.get(Role, user.role_id)
        role_name = role.name if role else None
        rows = await session.scalars(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == user.role_id)
            .order_by(Permission.name)
        )
        permissions = list(rows)
    return UserSessionOut(
        id=user.id,
        name=user.name,
        email=user.email,
        status=user.status,
        role=role_name,
        branch_id=user.branch_id,
        permissions=permissions,
    )
