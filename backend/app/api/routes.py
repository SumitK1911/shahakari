from fastapi import APIRouter

from app.api import (
    accounting,
    approvals,
    auth,
    automation,
    backup,
    branches,
    cash,
    controls,
    dashboard,
    deposits,
    field_collections,
    integrations,
    investments,
    governance,
    loans,
    members,
    notifications,
    products,
    reports,
    rules,
    savings,
    shares,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(branches.router, prefix="/branches", tags=["branches"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(members.router, prefix="/members", tags=["members"])
api_router.include_router(shares.router, prefix="/shares", tags=["shares"])
api_router.include_router(savings.router, prefix="/savings", tags=["savings"])
api_router.include_router(deposits.router, prefix="/deposits", tags=["deposits"])
api_router.include_router(field_collections.router, prefix="/field-collections", tags=["field_collections"])
api_router.include_router(loans.router, prefix="/loans", tags=["loans"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(cash.router, prefix="/cash", tags=["cash"])
api_router.include_router(controls.router, prefix="/controls", tags=["controls"])
api_router.include_router(accounting.router, prefix="/accounting", tags=["accounting"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(backup.router, prefix="/backup", tags=["backup"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(governance.router, prefix="/governance", tags=["governance"])
api_router.include_router(investments.router, prefix="/investments", tags=["investments"])



