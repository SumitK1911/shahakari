from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CalculationResult,
    InterestRule,
    Loan,
    LoanInstallment,
    PenaltyRule,
    SavingsAccount,
)


Money = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(Money, ROUND_HALF_UP)


def frequency_days(frequency: str) -> Decimal:
    return {
        "daily": Decimal("1"),
        "weekly": Decimal("7"),
        "monthly": Decimal("30"),
        "quarterly": Decimal("91"),
        "yearly": Decimal("365"),
    }.get(frequency, Decimal("1"))


class FinancialRulesEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def active_interest_rule(
        self,
        *,
        scope_type: str,
        scope_code: str,
        calculation_date: date,
    ) -> InterestRule | None:
        return await self.session.scalar(
            select(InterestRule)
            .where(
                InterestRule.scope_type == scope_type,
                InterestRule.scope_code == scope_code,
                InterestRule.is_active.is_(True),
                InterestRule.effective_from_ad <= calculation_date,
                or_(InterestRule.effective_to_ad.is_(None), InterestRule.effective_to_ad >= calculation_date),
            )
            .order_by(InterestRule.effective_from_ad.desc())
            .limit(1)
        )

    async def active_penalty_rule(
        self,
        *,
        scope_type: str,
        scope_code: str,
        calculation_date: date,
    ) -> PenaltyRule | None:
        return await self.session.scalar(
            select(PenaltyRule)
            .where(
                PenaltyRule.scope_type == scope_type,
                PenaltyRule.scope_code == scope_code,
                PenaltyRule.is_active.is_(True),
                PenaltyRule.effective_from_ad <= calculation_date,
                or_(PenaltyRule.effective_to_ad.is_(None), PenaltyRule.effective_to_ad >= calculation_date),
            )
            .order_by(PenaltyRule.effective_from_ad.desc())
            .limit(1)
        )

    async def calculate_savings_interest(
        self,
        *,
        account: SavingsAccount,
        calculation_date: date,
    ) -> CalculationResult:
        rule = await self.active_interest_rule(
            scope_type="savings_product",
            scope_code=account.account_type,
            calculation_date=calculation_date,
        )
        method = rule.method if rule else "daily_balance"
        rate = rule.annual_rate if rule else account.interest_rate
        base_amount = account.balance
        days = int(frequency_days(rule.calculation_frequency if rule else "daily"))

        if method == "fixed_balance":
            base_amount = Decimal(str((rule.config or {}).get("fixed_balance", base_amount))) if rule else base_amount
        amount = money(base_amount * rate / Decimal("100") * Decimal(days) / Decimal("365"))

        result = CalculationResult(
            result_type="savings_interest",
            rule_id=rule.id if rule else None,
            target_type="savings_account",
            target_id=account.id,
            calculation_date_ad=calculation_date,
            base_amount=money(base_amount),
            rate=rate,
            days=days,
            amount=amount,
            details={
                "method": method,
                "posting_frequency": rule.posting_frequency if rule else "daily",
                "calculation_frequency": rule.calculation_frequency if rule else "daily",
            },
        )
        self.session.add(result)
        return result

    async def calculate_penalty(
        self,
        *,
        installment: LoanInstallment,
        loan: Loan | None,
        calculation_date: date,
        fallback_rate_percent: Decimal,
    ) -> CalculationResult:
        scope_code = loan.loan_type if loan else "default"
        rule = await self.active_penalty_rule(
            scope_type="loan_product",
            scope_code=scope_code,
            calculation_date=calculation_date,
        )
        overdue_days = max(0, (calculation_date - installment.due_date).days)
        grace_days = rule.grace_days if rule else 0
        chargeable_days = max(0, overdue_days - grace_days)
        frequency = rule.frequency if rule else "monthly"
        periods = Decimal(chargeable_days) / frequency_days(frequency)
        base_amount = installment.total

        if not rule:
            amount = money(base_amount * fallback_rate_percent / Decimal("100"))
            method = "percentage"
            rate = fallback_rate_percent
        elif rule.method == "fixed_amount":
            amount = money(rule.fixed_amount * max(Decimal("1"), periods))
            method = rule.method
            rate = Decimal("0")
        elif rule.is_compound:
            compound_base = base_amount * ((Decimal("1") + rule.percentage_rate / Decimal("100")) ** int(periods))
            amount = money(compound_base - base_amount)
            method = "compound_penalty"
            rate = rule.percentage_rate
        else:
            amount = money(base_amount * rule.percentage_rate / Decimal("100") * max(Decimal("1"), periods))
            method = rule.method
            rate = rule.percentage_rate

        result = CalculationResult(
            result_type="loan_penalty",
            rule_id=rule.id if rule else None,
            target_type="loan_installment",
            target_id=installment.id,
            calculation_date_ad=calculation_date,
            base_amount=money(base_amount),
            rate=rate,
            days=chargeable_days,
            amount=amount,
            details={
                "method": method,
                "frequency": frequency,
                "overdue_days": overdue_days,
                "grace_days": grace_days,
                "loan_id": str(installment.loan_id),
            },
        )
        self.session.add(result)
        return result
