from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Loan, LoanInstallment, LoanPayment, SavingsAccount, SavingsTransaction, TermDeposit
from app.services.deposits import mature_term_deposit
from app.services.rules_engine import FinancialRulesEngine, money


def period_name(run_date: date) -> str:
    if run_date.month == 7 and run_date.day == 16:
        return "fiscal-year-start"
    if run_date.day == 1:
        return "monthly-opening"
    return "daily-closing"


async def run_finance_automation(
    session: AsyncSession,
    *,
    run_date: date,
) -> dict[str, Decimal | int | str | date]:
    rules_engine = FinancialRulesEngine(session)
    
    # 1. Savings Interest Calculation
    savings_accounts = await session.scalars(
        select(SavingsAccount)
        .where(
            SavingsAccount.status == "active",
            SavingsAccount.balance > 0,
            SavingsAccount.interest_rate > 0,
        )
        .with_for_update()
    )
    savings_interest_transactions = 0
    savings_interest_amount = Decimal("0")
    for account in savings_accounts:
        result = await rules_engine.calculate_savings_interest(account=account, calculation_date=run_date)
        interest = result.amount
        if interest <= 0:
            continue
        account.balance = money(account.balance + interest)
        savings_interest_amount += interest
        savings_interest_transactions += 1
        session.add(
            SavingsTransaction(
                account_id=account.id,
                trans_type="interest",
                amount=interest,
                balance=account.balance,
                trans_date=run_date,
                narration=f"Automated {period_name(run_date)} savings interest",
            )
        )

    # 2. Auto-Deduct Loan Installments
    # Find all pending or overdue installments due up to today
    due_installments = await session.scalars(
        select(LoanInstallment)
        .where(LoanInstallment.due_date <= run_date, LoanInstallment.status.in_(["pending", "overdue"]))
        .order_by(LoanInstallment.due_date)
        .with_for_update()
    )
    auto_deducted_count = 0
    auto_deducted_amount = Decimal("0")
    for installment in due_installments:
        loan = await session.get(Loan, installment.loan_id)
        if loan.status != "active":
            continue
            
        # Try to find a primary active savings account for this member with enough balance
        savings = await session.scalar(
            select(SavingsAccount)
            .where(SavingsAccount.member_id == loan.member_id, SavingsAccount.status == "active", SavingsAccount.balance >= installment.total)
            .order_by(SavingsAccount.created_at)
            .limit(1)
            .with_for_update()
        )
        if savings:
            # Deduct from savings
            savings.balance = money(savings.balance - installment.total)
            session.add(
                SavingsTransaction(
                    account_id=savings.id,
                    trans_type="withdraw",
                    amount=installment.total,
                    balance=savings.balance,
                    trans_date=run_date,
                    narration=f"Auto-deduction for loan {loan.loan_no} installment {installment.installment_no}",
                )
            )
            # Pay installment
            installment.status = "paid"
            loan.outstanding_principal = money(loan.outstanding_principal - installment.principal)
            session.add(
                LoanPayment(
                    loan_id=loan.id,
                    payment_date=run_date,
                    principal_paid=installment.principal,
                    interest_paid=installment.interest,
                    penalty_paid=installment.penalty,
                    total_paid=installment.total,
                )
            )
            auto_deducted_count += 1
            auto_deducted_amount += installment.total
            
            # If loan is fully paid
            if loan.outstanding_principal <= 0:
                loan.status = "closed"

    # 3. Mark Overdue & Apply Penalties
    installments = await session.scalars(
        select(LoanInstallment)
        .where(LoanInstallment.due_date < run_date, LoanInstallment.status.in_(["pending", "overdue"]))
        .with_for_update()
    )
    overdue_installments = 0
    penalty_amount = Decimal("0")
    for installment in installments:
        loan = await session.get(Loan, installment.loan_id)
        result = await rules_engine.calculate_penalty(
            installment=installment,
            loan=loan,
            calculation_date=run_date,
            fallback_rate_percent=Decimal("0"),
        )
        
        overdue_days = int(result.details.get("overdue_days", 0))
        grace_days = int(result.details.get("grace_days", 0))
        
        if overdue_days > grace_days:
            expected_penalty = result.amount
            added_penalty = max(Decimal("0"), expected_penalty - installment.penalty)
            installment.status = "overdue"
            installment.penalty = expected_penalty
            installment.total = money(installment.principal + installment.interest + installment.penalty)
            penalty_amount += added_penalty
            overdue_installments += 1

    # 4. Mature Term Deposits
    mature_deposits = await session.scalars(
        select(TermDeposit)
        .where(TermDeposit.maturity_date <= run_date, TermDeposit.status == "active")
        .with_for_update()
    )
    matured_deposits = 0
    for deposit in mature_deposits:
        await mature_term_deposit(session, deposit_id=deposit.id, user_id=None)
        matured_deposits += 1

    return {
        "run_date": run_date,
        "savings_interest_transactions": savings_interest_transactions,
        "savings_interest_amount": money(savings_interest_amount),
        "auto_deducted_installments": auto_deducted_count,
        "auto_deducted_amount": money(auto_deducted_amount),
        "overdue_installments": overdue_installments,
        "penalty_amount": money(penalty_amount),
        "matured_deposits": matured_deposits,
        "period": period_name(run_date),
        "message": "Automation completed and posted to live records.",
    }
