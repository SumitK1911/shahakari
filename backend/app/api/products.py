from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import Product, User
from app.schemas import ProductCreate, ProductOut
from app.services.audit import audit

router = APIRouter()


@router.get("", response_model=list[ProductOut])
async def list_products(
    product_type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("products.read")),
) -> list[Product]:
    stmt = select(Product).order_by(Product.product_type, Product.code).limit(limit)
    if product_type:
        stmt = stmt.where(Product.product_type == product_type)
    if status:
        stmt = stmt.where(Product.status == status)
    return list(await session.scalars(stmt))


@router.post("", response_model=ProductOut)
async def create_product(
    payload: ProductCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("products.write")),
) -> Product:
    product = Product(**payload.model_dump())
    session.add(product)
    await session.flush()
    await audit(session, user_id=user.id, action="products.create", module="products", record_id=str(product.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID,
    payload: ProductCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("products.write")),
) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    before = ProductOut.model_validate(product).model_dump(mode="json")
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    await audit(session, user_id=user.id, action="products.update", module="products", record_id=str(product.id), diff={"before": before, "after": payload.model_dump(mode="json")})
    await session.commit()
    await session.refresh(product)
    return product
