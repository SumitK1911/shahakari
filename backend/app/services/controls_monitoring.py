from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Account,
    ComplianceAlert,
    LedgerEntry,
    LiquiditySnapshot,
    Loan,
    LoanInstallment,
    Member,
    SavingsAccount,
    SavingsTransaction,
    TermDeposit,
    User,
    WithdrawalRequest,
)
from app.services.audit import audit
from app.services.member_controls import require_financially_eligible_member


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal("100.0000")
    return (numerator / denominator * Decimal("100")).quantize(Decimal("0.0001"))


async def create_withdrawal_request(
    session: AsyncSession,
    *,
    member_id: UUID,
    savings_account_id: UUID | None,
    requested_amount: Decimal,
    needed_by_date: date | None,
    priority: str,
    reason: str | None,
    user: User,
) -> WithdrawalRequest:
    member = await require_financially_eligible_member(session, member_id)
    if savings_account_id:
        account = await session.get(SavingsAccount, savings_account_id)
        if account is None or account.member_id != member_id:
            raise HTTPException(status_code=404, detail="Savings account not found for member")
    request = WithdrawalRequest(
        member_id=member_id,
        savings_account_id=savings_account_id,
        requested_amount=requested_amount,
        needed_by_date=needed_by_date,
        priority=priority,
        reason=reason,
        requested_by=user.id,
    )
    session.add(request)
    await session.flush()
    await audit(session, user_id=user.id, action="controls.withdrawal.request", module="controls", record_id=str(request.id), diff={"amount": str(requested_amount)})
    return request


async def decide_withdrawal_request(
    session: AsyncSession,
    *,
    request_id: UUID,
    status: str,
    approved_amount: Decimal | None,
    decision_note: str | None,
    user: User,
) -> WithdrawalRequest:
    request = await session.get(WithdrawalRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="Withdrawal request already decided")
    request.status = status
    request.approved_amount = approved_amount if status == "approved" else None
    request.decision_note = decision_note
    request.decided_by = user.id
    request.decided_at = datetime.now(timezone.utc)
    await audit(session, user_id=user.id, action=f"controls.withdrawal.{status}", module="controls", record_id=str(request.id), diff={"approved_amount": str(request.approved_amount or 0)})
    return request


async def calculate_liquidity_snapshot(session: AsyncSession, *, branch_id: UUID | None = None) -> LiquiditySnapshot:
    # Liquidity must be based on cash/bank only.  Summing the whole ledger
    # always nets to zero in a double-entry system and creates false alerts.
    cash_debit = await session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.debit), 0))
        .join(Account, Account.id == LedgerEntry.account_id)
        .where(Account.code == "1000")
    ) or Decimal("0")
    cash_credit = await session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.credit), 0))
        .join(Account, Account.id == LedgerEntry.account_id)
        .where(Account.code == "1000")
    ) or Decimal("0")
    cash_balance = Decimal(cash_debit) - Decimal(cash_credit)
    savings = await session.scalar(select(func.coalesce(func.sum(SavingsAccount.balance), 0)).where(SavingsAccount.status == "active")) or Decimal("0")
    term_deposits = await session.scalar(select(func.coalesce(func.sum(TermDeposit.balance), 0)).where(TermDeposit.status.in_(["active", "matured"]))) or Decimal("0")
    pending_withdrawals = await session.scalar(select(func.coalesce(func.sum(WithdrawalRequest.requested_amount), 0)).where(WithdrawalRequest.status == "pending")) or Decimal("0")
    liquid_assets = cash_balance
    total_liability = Decimal(savings) + Decimal(term_deposits) + Decimal(pending_withdrawals)
    liquidity_ratio = ratio(liquid_assets, total_liability)
    status = "critical" if liquidity_ratio < Decimal("10") else "watch" if liquidity_ratio < Decimal("15") else "normal"
    snapshot = LiquiditySnapshot(
        branch_id=branch_id,
        snapshot_date=date.today(),
        cash_balance=cash_balance,
        bank_balance=Decimal("0"),
        liquid_assets=liquid_assets,
        member_savings_liability=savings,
        term_deposit_liability=term_deposits,
        pending_withdrawals=pending_withdrawals,
        liquidity_ratio=liquidity_ratio,
        status=status,
        notes="Auto-calculated from ledger, savings, term deposits, and pending withdrawal queue.",
    )
    session.add(snapshot)
    await session.flush()
    if status != "normal":
        await upsert_alert(
            session,
            rule_code="LIQUIDITY_RATIO_LOW",
            module="liquidity",
            severity="critical" if status == "critical" else "high",
            title="Liquidity ratio below safety threshold",
            description=f"Liquid assets cover {liquidity_ratio}% of member savings, term deposits, and pending withdrawals.",
            record_type="liquidity_snapshot",
            record_id=snapshot.id,
            details={"liquidity_ratio": str(liquidity_ratio), "status": status},
        )
    return snapshot


async def upsert_alert(
    session: AsyncSession,
    *,
    rule_code: str,
    module: str,
    severity: str,
    title: str,
    description: str,
    record_type: str | None = None,
    record_id: UUID | None = None,
    details: dict | None = None,
) -> ComplianceAlert:
    alert = await session.scalar(
        select(ComplianceAlert).where(
            ComplianceAlert.rule_code == rule_code,
            ComplianceAlert.record_id == record_id,
            ComplianceAlert.status == "open",
        )
    )
    if alert is None:
        alert = ComplianceAlert(
            rule_code=rule_code,
            module=module,
            severity=severity,
            title=title,
            description=description,
            record_type=record_type,
            record_id=record_id,
            details=details,
        )
        session.add(alert)
    else:
        alert.severity = severity
        alert.title = title
        alert.description = description
        alert.details = details
    await session.flush()
    return alert


async def run_compliance_scan(session: AsyncSession) -> dict[str, int]:
    created = 0
    await calculate_liquidity_snapshot(session)

    overdue = list(await session.scalars(select(LoanInstallment).where(LoanInstallment.status == "overdue").limit(500)))
    for installment in overdue:
        await upsert_alert(
            session,
            rule_code="LOAN_OVERDUE",
            module="loans",
            severity="high",
            title="Loan installment overdue",
            description=f"Installment {installment.installment_no} is overdue with total due {installment.total}.",
            record_type="loan_installment",
            record_id=installment.id,
            details={"loan_id": str(installment.loan_id), "due_date": installment.due_date.isoformat()},
        )
        created += 1

    high_risk_members = list(await session.scalars(select(Member).where((Member.risk_category == "high") | (Member.is_pep.is_(True)) | (Member.is_blacklisted.is_(True))).limit(500)))
    for member in high_risk_members:
        await upsert_alert(
            session,
            rule_code="HIGH_RISK_MEMBER",
            module="members",
            severity="high" if member.is_blacklisted else "medium",
            title="High-risk member requires review",
            description=f"Member {member.member_no} is marked risk={member.risk_category}, PEP={member.is_pep}, blacklist={member.is_blacklisted}.",
            record_type="member",
            record_id=member.id,
            details={"member_no": member.member_no, "name": member.name},
        )
        created += 1

    large_transactions = list(await session.scalars(select(SavingsTransaction).where(SavingsTransaction.amount >= Decimal("100000")).order_by(SavingsTransaction.created_at.desc()).limit(200)))
    for tx in large_transactions:
        await upsert_alert(
            session,
            rule_code="LARGE_SAVINGS_TRANSACTION",
            module="savings",
            severity="medium",
            title="Large savings transaction needs maker-checker review",
            description=f"{tx.trans_type} transaction of {tx.amount} posted on {tx.trans_date}.",
            record_type="savings_transaction",
            record_id=tx.id,
            details={"account_id": str(tx.account_id), "amount": str(tx.amount)},
        )
        created += 1

    total_loans = await session.scalar(select(func.coalesce(func.sum(Loan.outstanding_principal), 0)).where(Loan.status == "active")) or Decimal("0")
    overdue_loan_ids = select(LoanInstallment.loan_id).where(LoanInstallment.status == "overdue").distinct()
    npl = await session.scalar(select(func.coalesce(func.sum(Loan.outstanding_principal), 0)).where(Loan.id.in_(overdue_loan_ids))) or Decimal("0")
    npl_ratio = ratio(Decimal(npl), Decimal(total_loans))
    if npl_ratio >= Decimal("5"):
        await upsert_alert(
            session,
            rule_code="NPL_RATIO_HIGH",
            module="loans",
            severity="critical" if npl_ratio >= Decimal("15") else "high",
            title="NPL ratio above safety threshold",
            description=f"NPL exposure is {npl_ratio}% of active loan outstanding.",
            record_type=None,
            record_id=None,
            details={"npl_ratio": str(npl_ratio), "npl": str(npl), "total_loans": str(total_loans)},
        )
        created += 1

    return {"alerts_scanned": created}
