import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Account, Branch, IntegrationEndpoint, Permission, Role, RolePermission, SchedulerJob, User
from app.production_seed import seed_production_controls


PERMISSIONS = [
    ("dashboard.read", "dashboard", "View dashboard metrics"),
    ("users.read", "users", "View staff users and roles"),
    ("users.write", "users", "Create, assign, suspend, and reset staff users"),
    ("branches.read", "branches", "View branches"),
    ("branches.write", "branches", "Create and update branches"),
    ("approvals.read", "approvals", "View approval workflow queue"),
    ("approvals.write", "approvals", "Request approvals"),
    ("approvals.decide", "approvals", "Approve and reject workflow requests"),
    ("members.read", "members", "View members"),
    ("members.write", "members", "Create and update members"),
    ("members.kyc.approve", "members", "Approve or reject member KYC"),
    ("shares.read", "shares", "View shares"),
    ("shares.write", "shares", "Post share transactions"),
    ("savings.read", "savings", "View savings accounts"),
    ("savings.write", "savings", "Post savings transactions"),
    ("deposits.read", "deposits", "View fixed and recurring deposits"),
    ("deposits.write", "deposits", "Open, mature, and pay fixed and recurring deposits"),
    ("loans.read", "loans", "View loans"),
    ("loans.write", "loans", "Disburse and repay loans"),
    ("loans.recovery.read", "loans", "View loan recovery actions"),
    ("loans.recovery.write", "loans", "Record loan recovery actions"),
    ("products.read", "products", "View financial products"),
    ("products.write", "products", "Create and update financial products"),
    ("cash.read", "cash", "View cash sessions and cashbook"),
    ("cash.write", "cash", "Open and close cash sessions"),
    ("controls.read", "controls", "View liquidity, withdrawal queue, and compliance alerts"),
    ("controls.write", "controls", "Create withdrawal requests, liquidity snapshots, and scans"),
    ("controls.decide", "controls", "Approve withdrawals and resolve compliance alerts"),
    ("compliance.cases.read", "controls", "View AML and compliance investigation cases"),
    ("compliance.cases.write", "controls", "Create and decide AML and compliance investigation cases"),
    ("accounting.read", "accounting", "View accounting reports"),
    ("reports.read", "reports", "View management reports"),
    ("reports.write", "reports", "Generate management report files"),
    ("automation.run", "automation", "Run automation jobs"),
    ("rules.read", "rules", "View financial rules and calculation results"),
    ("rules.write", "rules", "Create and update financial rules"),
    ("backup.read", "backup", "View backup runs"),
    ("backup.write", "backup", "Create and validate backup runs"),
    ("notifications.read", "notifications", "View SMS and email notifications"),
    ("notifications.write", "notifications", "Queue and dispatch notifications"),
    ("integrations.read", "integrations", "View external service integrations"),
    ("integrations.write", "integrations", "Configure external service integrations"),
    ("field_collections.read", "field_collections", "View field collection routes, batches, and entries"),
    ("field_collections.write", "field_collections", "Create field collection batches and entries"),
    ("field_collections.submit", "field_collections", "Submit field collection batches"),
    ("field_collections.verify", "field_collections", "Verify or reject submitted field collection cash"),
    ("field_collections.post", "field_collections", "Post verified field collections to member ledgers"),
    ("field_collections.manage", "field_collections", "Manage collection routes and assignments"),
]

ACCOUNTS = [
    ("1000", "Cash and Bank", "asset"),
    ("1200", "Loan Receivable", "asset"),
    ("1300", "Investments", "asset"),
    ("2100", "Member Savings Liability", "liability"),
    ("2200", "Fixed and Recurring Deposit Liability", "liability"),
    ("3000", "Share Capital", "equity"),
    ("4100", "Loan Interest Income", "income"),
    ("4200", "Fee Income", "income"),
    ("5100", "Interest Expense", "expense"),
    ("5300", "Dividend Expense", "expense"),
]

SCHEDULER_JOBS = [
    ("daily-interest-calculation", "daily_interest", "0 0 * * *", "Calculate daily/monthly interest for applicable accounts"),
    ("penalty-calculation", "penalty", "5 0 * * *", "Calculate penalty for overdue loans based on rules"),
    ("loan-overdue-check", "loan_overdue", "10 0 * * *", "Mark overdue loans and queue alerts"),
    ("maturity-processing", "maturity", "15 0 * * *", "Process FD/RD maturity and post interest"),
    ("emi-generation", "emi", "20 0 * * *", "Generate EMI schedules for approved loans"),
    ("notifications-dispatch", "notifications", "25 0 * * *", "Send due reminders, welcome messages, and alerts"),
    ("end-of-day", "eod", "30 0 * * *", "Auto closing, interest posting, and cashbook lock"),
    ("backup", "backup", "40 0 * * *", "Database and file backup automation"),
    ("reports-generation", "reports", "0 1 * * *", "Daily, monthly, and yearly report generation"),
    ("compliance-scan", "controls", "0 * * * *", "Liquidity, NPL, large transaction, and high-risk member monitoring"),
]

INTEGRATIONS = [
    ("receipt-printer-main", "receipt_printer", "Thermal Receipt Printer", None, {"driver": "escpos", "mode": "local"}),
    ("passbook-printer-main", "passbook_printer", "Passbook Printer", None, {"driver": "generic-text", "mode": "local"}),
    ("sms-gateway", "sms", "SMS Gateway", None, {"provider": "configure-provider", "dry_run": True}),
    ("whatsapp-cloud", "whatsapp", "WhatsApp Cloud API", None, {"provider": "meta-cloud-api", "dry_run": True, "api_version": "v20.0", "phone_number_id": "", "access_token": ""}),
    ("email-service", "email", "Email Service", None, {"provider": "smtp", "dry_run": True}),
    ("file-storage", "file_storage", "MinIO File Storage", None, {"bucket": "sahakari-files", "dry_run": True}),
    ("backup-storage", "backup_storage", "Local or Cloud Backup Storage", None, {"target": "local", "dry_run": True}),
]


async def main() -> None:
    async with SessionLocal() as session:
        branch = await session.scalar(select(Branch).where(Branch.code == "HQ"))
        if branch is None:
            branch = Branch(code="HQ", name="Head Office", address="Main branch")
            session.add(branch)

        role = await session.scalar(select(Role).where(Role.name == "Super Admin"))
        if role is None:
            role = Role(name="Super Admin", description="Full system access")
            session.add(role)
        await session.flush()

        for code, name, account_type in ACCOUNTS:
            account = await session.scalar(select(Account).where(Account.code == code))
            if account is None:
                session.add(Account(code=code, name=name, type=account_type))

        for name, module, description in PERMISSIONS:
            permission = await session.scalar(select(Permission).where(Permission.name == name))
            if permission is None:
                permission = Permission(name=name, module=module, description=description)
                session.add(permission)
                await session.flush()
            role_permission = await session.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if role_permission is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        for name, job_type, cron_expression, description in SCHEDULER_JOBS:
            job = await session.scalar(select(SchedulerJob).where(SchedulerJob.name == name))
            if job is None:
                session.add(
                    SchedulerJob(
                        name=name,
                        job_type=job_type,
                        cron_expression=cron_expression,
                        config={"description": description},
                    )
                )

        await seed_production_controls(session)

        for code, integration_type, name, connection_uri, config in INTEGRATIONS:
            endpoint = await session.scalar(select(IntegrationEndpoint).where(IntegrationEndpoint.code == code))
            if endpoint is None:
                session.add(
                    IntegrationEndpoint(
                        code=code,
                        integration_type=integration_type,
                        name=name,
                        connection_uri=connection_uri,
                        config=config,
                    )
                )

        user = await session.scalar(select(User).where(User.email == "admin@sahakari.local"))
        if user is None:
            session.add(
                User(
                    branch_id=branch.id,
                    role_id=role.id,
                    name="System Administrator",
                    email="admin@sahakari.local",
                    password_hash=hash_password("ChangeMe123!"),
                )
            )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())





