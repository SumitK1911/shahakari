# Sahakari Financial System Blueprint

## 1. Domain Analysis

The application must behave as an offline-first cooperative banking system for a local office network. Financial transactions are immutable, every money movement creates balanced double-entry ledger rows, and operational dates are stored in both AD and Nepali BS forms. Product modules collect facts; the Financial Rules Engine calculates interest, penalty, accrual, dividend, overdue state, and closing effects.

Core domains:

- Identity and access: users, roles, permissions, sessions, branch scope.
- Cooperative membership: persons, members, KYC, nominees, documents.
- Share capital: share products, purchases, transfers, certificates, dividends.
- Savings and FD: products, accounts, transactions, accruals, interest posting, maturity.
- Loans: products, applications, approval, disbursement, schedules, guarantors, collateral, repayment, overdue.
- Accounting: chart of accounts, journals, ledger entries, fiscal periods, trial balance.
- Cash operations: counters, cashier handover, vault movement, day closing.
- Rules and automation: configurable interest, penalty, accrual, dividend, scheduled jobs, calculation results.
- Audit and compliance: append-only audit logs, adjustment/reversal workflow, period locks.
- Reports and backup: daily, monthly, yearly reports, database backup and restore.

## 2. Entity List

Implemented or foundation-ready entities:

- `branches`, `users`, `roles`, `permissions`, `role_permissions`
- `members`, `member_nominees`
- `shares`, `share_transactions`
- `savings_accounts`, `savings_transactions`
- `loans`, `loan_installments`, `loan_payments`
- `accounts`, `journal_entries`, `ledger_entries`
- `audit_logs`
- `interest_rules`, `penalty_rules`, `accrual_rules`
- `scheduler_jobs`, `calculation_results`
- `fiscal_years`, `day_closings`, `month_closings`, `year_closings`

Planned expansion entities:

- `persons`, `documents`, `member_documents`, `sessions`
- `savings_products`, `fixed_deposits`, `loan_products`
- `loan_applications`, `loan_approvals`, `loan_guarantors`, `loan_collaterals`
- `cash_counters`, `cash_sessions`, `cash_movements`
- `collectors`, `collector_assignments`
- `backup_runs`, `report_runs`, `notification_outbox`

## 3. Database Schema

Use PostgreSQL with UUID primary keys, `NUMERIC` for money, `JSONB` for rule snapshots and audit diffs, and indexed AD/BS date fields for financial periods.

Required dedicated tables are now represented in SQLAlchemy models:

- `interest_rules`: product-scoped methods such as daily balance, minimum monthly balance, average monthly balance, fixed balance, quarterly posting, yearly posting.
- `penalty_rules`: fixed, percentage, daily, weekly, monthly, yearly, and compound penalties with grace days.
- `accrual_rules`: daily accrual configuration for savings interest, loan interest, FD interest, and penalties.
- `scheduler_jobs`: persistent job registry for nightly, month-end, and year-end automation.
- `calculation_results`: immutable calculation ledger for rule outputs before/after journal posting.
- `fiscal_years`, `day_closings`, `month_closings`, `year_closings`: BS/AD period control and locking.

Important indexes:

- Member search: `members(name, phone, status)`, `members(member_no)`.
- Product/account lookup: `savings_accounts(account_no)`, `loans(loan_no)`.
- Due work: `loan_installments(due_date, status)`, `scheduler_jobs(status, next_run_at)`.
- Rule resolution: `interest_rules(scope_type, scope_code, is_active)`, `penalty_rules(scope_type, scope_code, is_active)`.
- Audit and reporting: `ledger_entries(account_id, created_at)`, `audit_logs(user_id, created_at)`.

Constraints:

- Unique member number, savings account number, loan number, fiscal year code.
- Unique rule scope/effective date to avoid overlapping accidental duplicates.
- Unique branch/date day closing and branch/fiscal-period closing records.
- Application-level validation must prevent editing locked-period transactions.

Partitioning strategy:

- Monthly range partitions for `ledger_entries`, `audit_logs`, `calculation_results`, savings transactions, loan payments, and share transactions after production volume grows.
- Keep current plain tables for early deployment to reduce operational complexity.

Audit strategy:

- Never physically delete financial records.
- Use reversal or adjustment journal entries.
- Store old value, new value, user, timestamp, IP, device, module, action, and record id.
- Persist rule snapshots in `calculation_results.details` so historical calculations remain explainable after rules change.

Ledger strategy:

- `journal_entries` is the transaction header.
- `ledger_entries` stores debit and credit lines.
- Every financial event must balance before commit.
- Month/year closing posts generated journals for accruals, reserves, dividend payable, retained earnings, and opening balances.

## 4. ERD Description

- Branch owns users, members, day closings, month closings, and year closings.
- User belongs to one role; role has many permissions through `role_permissions`.
- Member owns savings accounts, share records, loans, nominees, and documents.
- Savings account has many savings transactions and many calculation results.
- Loan has many installments and payments; installments receive penalty calculation results.
- Journal entry has many ledger entries and can be referenced by calculation results and closing records.
- Fiscal year has many day/month/year closing records.
- Rules are product-scoped and referenced by calculation results, not by direct hard-coded module logic.

## 5. API Design

Current APIs should be extended into these groups:

- `/auth`: login, refresh, logout, sessions.
- `/rbac`: roles, permissions, permission matrix.
- `/members`, `/persons`, `/documents`.
- `/shares`: purchase, transfer, refund, dividend.
- `/savings-products`, `/savings-accounts`, `/fixed-deposits`.
- `/loan-products`, `/loans`, `/loan-repayments`, `/guarantors`, `/collaterals`.
- `/accounting`: chart of accounts, journals, trial balance, ledgers.
- `/cash`: counters, deposits, withdrawals, handover, vault movement.
- `/rules`: interest rules, penalty rules, accrual rules, calculation previews.
- `/automation`: scheduler jobs, run history, failed job retry.
- `/closing`: day close, manager verify, lock, month close, fiscal year close.
- `/reports`: daily/monthly/yearly reports, audit exports, member statements.
- `/backup`: local backup, restore validation, backup schedule.

All write APIs should check permission, branch scope, locked period, validation schema, and audit context.

## 6. Backend Architecture

Recommended layers:

- API routers: request validation, permission dependency, response models.
- Application services: workflow orchestration and transaction boundaries.
- Financial Rules Engine: all financial calculations.
- Accounting service: balanced journal generation.
- Repository/query helpers: reusable SQLAlchemy queries.
- Scheduler workers: Celery beat and workers on the local network.
- Audit middleware/service: write audit records consistently.

The rules engine is now introduced at `backend/app/services/rules_engine.py`, and automation delegates savings interest and penalty calculations to it.

## 7. Frontend Architecture

Desktop-first React dashboard:

- Dense operations layout with sidebar modules and branch/current fiscal year context.
- Data tables for members, accounts, loans, vouchers, closings, and reports.
- Product configuration screens for savings, FD, loan, interest, penalty, and accrual rules.
- Maker-checker screens for day closing and fiscal year closing.
- Report viewer with export and print-friendly layouts.
- Offline local-network assumption: clear connection status, local API URL, and backup status.

## 8. Financial Rules Engine Design

Rules engine responsibilities:

- Savings interest: daily balance, minimum monthly balance, average monthly balance, fixed balance, quarterly posting, yearly posting.
- Loan interest: flat, EMI, reducing balance, diminishing balance with daily/weekly/monthly/quarterly/yearly frequency.
- Penalty: fixed amount, percentage, frequency-based, compound, actual overdue duration.
- Accrual: daily savings, loan, FD, and penalty accrual.
- Dividend: yearly profit/reserve/dividend allocation.
- Classification: overdue buckets and non-performing account flags.
- Closing: generated accrual, posting, carry-forward, and opening-balance calculations.

Design rule:

- Product modules submit account/loan facts.
- Rules engine calculates and stores `calculation_results`.
- Accounting service posts journals from approved/generated results.
- Modules update balances only through audited services.

## 9. Scheduler & Automation Design

Use Celery beat plus persistent `scheduler_jobs` records. Jobs run without manual buttons, but admin APIs can trigger/retry with audit logs.

Nightly:

- Interest accrual.
- Penalty accrual.
- Dormancy check.
- FD maturity check.
- Loan overdue check.
- Automatic journal generation.

Month-end:

- Post savings interest.
- Post loan interest.
- Generate accrual entries.
- Generate accounting summaries.

Year-end:

- Profit calculation.
- Reserve allocation.
- Dividend calculation.
- Retained earnings transfer.
- Opening balance creation.

## 10. Security Architecture

- JWT authentication with refresh/session tracking.
- RBAC permission matrix per module/action.
- Branch-scoped access checks.
- Password hashing with bcrypt.
- Rate limiting on login and sensitive endpoints.
- Pydantic input validation and SQLAlchemy parameterized queries.
- Field encryption for citizenship number, document numbers, phone if required, and backup secrets.
- Audit logs for create/update/reverse/approve/close/login events.
- Locked periods reject edits; authorized users must create reversal entries.

## 11. Deployment Architecture

Desktop/local-network first:

- Windows office PC or local server runs Docker Compose.
- PostgreSQL, Redis, API, worker, beat, and frontend run on the LAN.
- Workstations access the frontend by local IP.
- Daily encrypted local backup plus optional external drive/NAS backup.
- No cloud dependency for day-to-day operations.

Recommended production services:

- `postgres`
- `redis`
- `api`
- `worker`
- `beat`
- `frontend`
- `nginx`
- `backup`

## 12. Development Roadmap

Phase 1: Financial foundation

- Complete rules CRUD APIs.
- Add migrations for new rules/closing tables.
- Add calculation-result reports.
- Ensure Celery nightly jobs use the rules engine.

Phase 2: Closing controls

- Day-end cashier close, manager verify, lock.
- Locked-period edit prevention.
- Reversal/adjustment entries.
- Month closing and generated accrual journals.

Phase 3: Product depth

- Savings products and FD products.
- Loan products, EMI/reducing/diminishing schedules.
- Guarantor and collateral management.
- Dormancy, maturity, overdue classification.

Phase 4: Fiscal year

- Nepal fiscal year setup.
- Trial balance close.
- Reserve allocation, dividend, retained earnings.
- Opening balance carry-forward.

Phase 5: Compliance and operations

- Full audit viewer.
- Backup/restore UI.
- Rate limiting and session management.
- Report exports and print layouts.
