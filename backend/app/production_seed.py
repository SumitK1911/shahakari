from sqlalchemy import select

from app.models import OrganizationPosition, Permission, Role, RolePermission, SystemPolicy

POSITIONS = [
    ("board_chairman", "Chairman", "board", None, "Board leadership and strategic oversight"),
    ("board_vice_chairman", "Vice Chairman", "board", "board_chairman", "Deputy board leadership"),
    ("board_secretary", "Secretary", "board", "board_chairman", "Board minutes and governance records"),
    ("board_treasurer", "Treasurer", "board", "board_chairman", "Board financial oversight"),
    ("board_member", "Board Member", "board", "board_chairman", "Strategic and large-loan decisions"),
    ("ceo", "CEO / General Manager", "management", "board_chairman", "Executive management"),
    ("operations_manager", "Operations Manager", "management", "ceo", "Branch operations"),
    ("finance_manager", "Finance Manager", "management", "ceo", "Finance and accounting control"),
    ("credit_manager", "Credit Manager", "management", "ceo", "Credit approval and portfolio quality"),
    ("compliance_officer", "Compliance Officer", "control", "ceo", "KYC, AML, regulatory controls"),
    ("internal_auditor", "Internal Auditor", "control", "board_chairman", "Independent internal audit"),
    ("teller", "Teller", "operations", "operations_manager", "Cash counter transactions"),
    ("senior_teller", "Senior Teller", "operations", "operations_manager", "Limited teller approvals"),
    ("loan_officer", "Loan Officer", "credit", "credit_manager", "Loan applications and recommendations"),
    ("collection_officer", "Collection Officer", "credit", "credit_manager", "Collections and follow-up"),
    ("field_officer", "Field Officer", "credit", "credit_manager", "Field visits and verification"),
    ("accountant", "Accountant", "finance", "finance_manager", "Journal and ledger work"),
    ("customer_service", "Customer Service", "operations", "operations_manager", "Member service"),
    ("it_admin", "IT/Admin", "admin", "ceo", "System administration"),
]

POLICIES = [
    ("member_initial_state", "Member Initial Financial State", "membership", {"membership_fee": "100", "required_share_units": 20, "share_rate": "100", "required_savings_deposit": "10000", "currency": "NPR"}),
    ("maker_checker_loan", "Loan Maker Checker Rule", "approval", {"same_user_create_approve_disburse_allowed": False, "required_steps": ["application", "review", "approval", "disbursement"]}),
    ("cash_disbursement_limits", "Cash Disbursement Limits", "cash", {"teller": "25000", "senior_teller": "100000", "branch_manager": "500000", "board_required_above": "1000000"}),
]

ROLE_MATRIX = {
    "Teller": ["dashboard.read", "members.read", "members.write", "members.kyc.approve", "savings.read", "savings.write", "shares.read", "cash.read", "cash.write", "field_collections.read", "field_collections.verify", "field_collections.post", "notifications.read"],
    "Field Collector": ["dashboard.read", "members.read", "savings.read", "field_collections.read", "field_collections.write", "field_collections.submit", "notifications.read"],
    "Senior Teller": ["dashboard.read", "members.read", "members.write", "members.kyc.approve", "savings.read", "savings.write", "shares.read", "shares.write", "cash.read", "cash.write", "controls.read", "notifications.read"],
    "Loan Officer": ["dashboard.read", "members.read", "loans.read", "loans.application.create", "loans.review", "loans.write", "loans.recovery.read", "loans.recovery.write", "field_visits.read", "field_visits.write", "notifications.read"],
    "Credit Manager": ["dashboard.read", "members.read", "loans.read", "loans.review", "loans.approve", "loans.recovery.read", "loans.recovery.write", "field_visits.read", "reports.read", "controls.read", "controls.write"],
    "Branch Manager": ["dashboard.read", "branches.read", "members.read", "members.write", "shares.read", "shares.write", "savings.read", "savings.write", "cash.read", "cash.write", "field_collections.read", "field_collections.write", "field_collections.submit", "field_collections.verify", "field_collections.post", "field_collections.manage", "loans.read", "loans.approve", "loans.disburse", "reports.read", "automation.run", "controls.read", "controls.write", "controls.decide", "approvals.read", "approvals.decide", "notifications.read", "notifications.write"],
    "Accountant": ["dashboard.read", "cash.read", "accounting.read", "reports.read", "reports.write", "shares.read", "savings.read", "loans.read", "backup.read", "investments.read"],
    "Compliance Officer": ["dashboard.read", "members.read", "members.kyc.approve", "controls.read", "reports.read", "compliance.cases.read", "compliance.cases.write"],
    "Auditor": ["dashboard.read", "members.read", "shares.read", "savings.read", "cash.read", "loans.read", "accounting.read", "reports.read", "controls.read", "backup.read", "governance.read", "field_visits.read", "investments.read"],
    "Board": ["dashboard.read", "reports.read", "controls.read", "loans.read", "loans.approve", "governance.read", "governance.write", "investments.read"],
}

EXTRA_PERMISSIONS = [
    ("loans.application.create", "loans", "Create loan applications only"),
    ("loans.review", "loans", "Review and recommend loan applications"),
    ("loans.approve", "loans", "Approve loan applications"),
    ("loans.disburse", "loans", "Disburse approved loans"),
    ("governance.read", "governance", "View organization, policies, and decisions"),
    ("governance.write", "governance", "Create policies and board/committee decisions"),
    ("field_visits.read", "field_visits", "View field visit records"),
    ("field_visits.write", "field_visits", "Create field visit records"),
    ("field_collections.read", "field_collections", "View field collection routes, batches, and entries"),
    ("field_collections.write", "field_collections", "Create field collection batches and entries"),
    ("field_collections.submit", "field_collections", "Submit field collection batches"),
    ("field_collections.verify", "field_collections", "Verify or reject submitted field collection cash"),
    ("field_collections.post", "field_collections", "Post verified field collections to member ledgers"),
    ("field_collections.manage", "field_collections", "Manage collection routes and assignments"),
    ("investments.read", "investments", "View investment portfolio and transactions"),
    ("investments.write", "investments", "Create and manage investment records"),
]


async def seed_production_controls(session):
    for name, module, description in EXTRA_PERMISSIONS:
        permission = await session.scalar(select(Permission).where(Permission.name == name))
        if permission is None:
            permission = Permission(name=name, module=module, description=description)
            session.add(permission)

    for code, title, level, reports_to_code, description in POSITIONS:
        position = await session.scalar(select(OrganizationPosition).where(OrganizationPosition.code == code))
        if position is None:
            session.add(OrganizationPosition(code=code, title=title, level=level, reports_to_code=reports_to_code, description=description))

    for code, name, policy_type, config in POLICIES:
        policy = await session.scalar(select(SystemPolicy).where(SystemPolicy.code == code))
        if policy is None:
            session.add(SystemPolicy(code=code, name=name, policy_type=policy_type, config=config))

    await session.flush()
    permission_by_name = {permission.name: permission for permission in await session.scalars(select(Permission))}
    for role_name, permission_names in ROLE_MATRIX.items():
        role = await session.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name, description=f"{role_name} operational role")
            session.add(role)
            await session.flush()
        for permission_name in permission_names:
            permission = permission_by_name.get(permission_name)
            if permission is None:
                continue
            existing = await session.scalar(select(RolePermission).where(RolePermission.role_id == role.id, RolePermission.permission_id == permission.id))
            if existing is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    super_admin = await session.scalar(select(Role).where(Role.name == "Super Admin"))
    if super_admin is not None:
        all_permissions = list(await session.scalars(select(Permission)))
        for permission in all_permissions:
            existing = await session.scalar(select(RolePermission).where(RolePermission.role_id == super_admin.id, RolePermission.permission_id == permission.id))
            if existing is None:
                session.add(RolePermission(role_id=super_admin.id, permission_id=permission.id))
