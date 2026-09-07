# Sahakari Architecture

## Runtime

- Web dashboard: React, Vite, TypeScript, lucide icons.
- Backend API: FastAPI, async SQLAlchemy, PostgreSQL.
- Automation: Celery workers with Redis broker.
- Storage: PostgreSQL primary now, read replicas and object storage ready for production expansion.
- Financial calculations: Dedicated Financial Rules Engine service with rule tables, calculation results, scheduler jobs, and closing-period controls.

For the full cooperative finance target architecture, use `FINANCIAL_SYSTEM_BLUEPRINT.md`.

## Database Optimization

- UUID primary keys avoid branch-local collisions and support replication-friendly identifiers.
- High-traffic search fields are indexed: member number, phone, status, branch, loan status, installment due date, ledger account/date.
- Financial amounts use `NUMERIC`, never floating point.
- Ledger posting uses double-entry rows, allowing trial balance, P&L, and audit reconstruction.
- For scale, add monthly partitioning to `audit_logs`, `ledger_entries`, and transaction tables once volume grows.

## Security

- JWT bearer authentication is wired at the API boundary.
- Passwords are hashed with bcrypt through Passlib.
- Every module should call the RBAC layer before production release; the first cut has dependency hooks ready.
- Production deployments should rotate `SECRET_KEY`, enforce TLS, set private database networking, and move backups to encrypted object storage.

## Agent-To-Agent Workflow

The system is prepared around specialized workflow agents:

- KYC agent validates identity documents and queues approval tasks.
- Accounting agent posts balanced journals for financial events.
- Loan agent generates schedules, marks overdue installments, and applies penalties.
- Notification agent sends SMS/email reminders for maturity, due dates, and failed jobs.
- Report agent builds daily, monthly, and fiscal-period exports.

Each agent can run as a Celery task today and can later be promoted to an MCP-enabled service if external tools are needed.
