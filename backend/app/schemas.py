from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: str
    password: str


class BranchCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str
    address: str | None = None


class BranchOut(BranchCreate):
    id: UUID
    status: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    branch_id: UUID | None = None
    role_id: UUID | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not (any(char.islower() for char in value) and any(char.isupper() for char in value) and any(char.isdigit() for char in value) and any(not char.isalnum() for char in value)):
            raise ValueError("Password must include upper-case, lower-case, digit, and symbol")
        return value


class UserOut(BaseModel):
    id: UUID
    name: str
    email: str
    status: str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)
    branch_id: UUID | None = None
    role_id: UUID | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|suspended)$")


    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str | None) -> str | None:
        if value is not None and not (any(char.islower() for char in value) and any(char.isupper() for char in value) and any(char.isdigit() for char in value) and any(not char.isalnum() for char in value)):
            raise ValueError("Password must include upper-case, lower-case, digit, and symbol")
        return value


class UserAdminOut(UserOut):
    branch_id: UUID | None = None
    role_id: UUID | None = None
    role_name: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime


class RoleOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


class UserSessionOut(UserOut):
    role: str | None = None
    branch_id: UUID | None = None
    permissions: list[str] = []


class AddressIn(BaseModel):
    province: str | None = None
    district: str | None = None
    municipality: str | None = None
    ward_no: int | None = Field(default=None, ge=1, le=35)
    tole: str | None = None


class AddressProfileIn(BaseModel):
    permanent: AddressIn
    temporary_same_as_permanent: bool = True
    temporary: AddressIn | None = None


class DocumentIn(BaseModel):
    document_type: str
    document_number: str
    issue_date: date | None = None
    issue_district: str | None = None
    expiry_date: date | None = None
    front_image: str | None = None
    back_image: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "DocumentIn":
        if self.issue_date and self.expiry_date and self.expiry_date <= self.issue_date:
            raise ValueError("Document expiry date must be after issue date")
        return self


class FamilyProfileIn(BaseModel):
    father_name: str
    mother_name: str
    grandfather_name: str | None = None
    spouse_name: str | None = None


class GuardianProfileIn(BaseModel):
    name: str
    relationship: str
    citizenship_number: str
    mobile_number: str
    address: str


class OccupationProfileIn(BaseModel):
    occupation_type: str
    employer_name: str | None = None
    job_position: str | None = None
    work_address: str | None = None
    monthly_income: Decimal = Field(default=Decimal("0"), ge=0)
    annual_income: Decimal | None = Field(default=None, ge=0)


class IncomeSourceIn(BaseModel):
    income_type: str
    monthly_amount: Decimal = Field(ge=0)
    description: str | None = None


class MediaProfileIn(BaseModel):
    profile_photo: str | None = None
    signature_image: str | None = None
    thumbprint: str | None = None


class MemberCreate(BaseModel):
    member_no: str
    name: str
    name_nepali: str | None = None
    branch_id: UUID | None = None
    dob: date | None = None
    dob_bs: str | None = None
    gender: str | None = None
    marital_status: str | None = None
    nationality: str = "Nepali"
    phone: str | None = None
    secondary_phone: str | None = None
    email: EmailStr | None = None
    emergency_contact_name: str | None = None
    emergency_contact_number: str | None = None
    address: str | None = None
    address_profile: AddressProfileIn | None = None
    documents: list[DocumentIn] | None = None
    family_profile: FamilyProfileIn | None = None
    guardian_profile: GuardianProfileIn | None = None
    occupation_profile: OccupationProfileIn | None = None
    income_sources: list[IncomeSourceIn] | None = None
    membership_type: str | None = None
    join_date: date | None = None
    risk_category: str = "low"
    is_pep: bool = False
    is_blacklisted: bool = False
    internal_notes: str | None = None
    media_profile: MediaProfileIn | None = None

    @model_validator(mode="after")
    def validate_contextual_requirements(self) -> "MemberCreate":
        if self.dob:
            today = date.today()
            if self.dob > today:
                raise ValueError("Date of birth cannot be in the future")
            age = today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
            if age < 18 and self.guardian_profile is None:
                raise ValueError("Guardian information is required for minors")
        if self.marital_status == "Married" and self.family_profile and not self.family_profile.spouse_name:
            raise ValueError("Spouse name is required when marital status is married")
        return self


class MemberUpdate(BaseModel):
    name: str | None = None
    name_nepali: str | None = None
    dob: date | None = None
    dob_bs: str | None = None
    gender: str | None = None
    marital_status: str | None = None
    nationality: str | None = None
    phone: str | None = None
    secondary_phone: str | None = None
    email: EmailStr | None = None
    emergency_contact_name: str | None = None
    emergency_contact_number: str | None = None
    address: str | None = None
    address_profile: AddressProfileIn | None = None
    documents: list[DocumentIn] | None = None
    family_profile: FamilyProfileIn | None = None
    guardian_profile: GuardianProfileIn | None = None
    occupation_profile: OccupationProfileIn | None = None
    income_sources: list[IncomeSourceIn] | None = None
    membership_type: str | None = None
    join_date: date | None = None
    risk_category: str | None = None
    is_pep: bool | None = None
    is_blacklisted: bool | None = None
    internal_notes: str | None = None
    media_profile: MediaProfileIn | None = None
    kyc_status: str | None = None
    status: str | None = None


class KycDecisionIn(BaseModel):
    decision_note: str | None = Field(default=None, max_length=2000)


class NomineeCreate(BaseModel):
    name: str
    relation: str
    phone: str | None = None
    address: str | None = None
    citizenship_number: str | None = None


class NomineeOut(NomineeCreate):
    id: UUID
    member_id: UUID

    class Config:
        from_attributes = True


class MemberOut(MemberCreate):
    id: UUID
    kyc_status: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SavingsAccountCreate(BaseModel):
    member_id: UUID
    account_no: str
    account_type: str
    interest_rate: Decimal = Decimal("0")


class SavingsAccountOut(SavingsAccountCreate):
    id: UUID
    balance: Decimal
    status: str

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    product_type: str = Field(min_length=2, max_length=32)
    code: str = Field(min_length=1, max_length=60)
    name: str
    interest_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    min_amount: Decimal = Field(default=Decimal("0"), ge=0)
    max_amount: Decimal | None = Field(default=None, ge=0)
    tenure_months: int | None = Field(default=None, ge=1, le=360)
    config: dict | None = None
    status: str = "active"


class ProductOut(ProductCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DepositWithdrawIn(BaseModel):
    amount: Decimal = Field(gt=0)
    narration: str | None = None


class SharePurchaseIn(BaseModel):
    member_id: UUID
    shares: int = Field(gt=0)
    rate: Decimal = Field(gt=0)
    narration: str | None = None


class ShareTransferIn(BaseModel):
    from_member_id: UUID
    to_member_id: UUID
    shares: int = Field(gt=0)
    narration: str | None = None


class ShareRefundIn(BaseModel):
    member_id: UUID
    shares: int = Field(gt=0)
    narration: str | None = None


class DividendRunIn(BaseModel):
    dividend_rate_percent: Decimal = Field(gt=0, le=100)
    narration: str | None = None


class DividendRunOut(BaseModel):
    dividend_rate_percent: Decimal
    paid_to_savings: int
    paid_to_cash: int
    total_dividend: Decimal


class ShareOut(BaseModel):
    id: UUID
    member_id: UUID
    total_share: int
    rate: Decimal
    total_amount: Decimal
    status: str

    class Config:
        from_attributes = True


class TermDepositCreate(BaseModel):
    member_id: UUID
    deposit_no: str
    deposit_type: str = Field(pattern="^(fd|rd)$")
    principal_amount: Decimal = Field(gt=0)
    installment_amount: Decimal | None = Field(default=None, gt=0)
    interest_rate: Decimal = Field(ge=0, le=100)
    opened_date: date | None = None
    tenure_months: int = Field(gt=0, le=360)

    @model_validator(mode="after")
    def validate_rd_installment(self) -> "TermDepositCreate":
        if self.deposit_type == "rd" and self.installment_amount is None:
            raise ValueError("Recurring deposits require installment_amount")
        return self


class TermDepositOut(BaseModel):
    id: UUID
    member_id: UUID
    deposit_no: str
    deposit_type: str
    principal_amount: Decimal
    installment_amount: Decimal | None
    interest_rate: Decimal
    opened_date: date
    maturity_date: date
    maturity_amount: Decimal
    balance: Decimal
    status: str

    class Config:
        from_attributes = True


class TermDepositTransactionOut(BaseModel):
    id: UUID
    deposit_id: UUID
    trans_type: str
    amount: Decimal
    balance: Decimal
    trans_date: date
    narration: str | None

    class Config:
        from_attributes = True


class LoanCreate(BaseModel):
    member_id: UUID
    loan_no: str
    loan_type: str
    amount: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(ge=0)
    tenure_months: int = Field(gt=0, le=360)
    interest_method: str = "flat_monthly"
    repayment_method: str = "emi"


class LoanOut(LoanCreate):
    id: UUID
    outstanding_principal: Decimal
    status: str

    class Config:
        from_attributes = True


class LoanInstallmentOut(BaseModel):
    id: UUID
    loan_id: UUID
    installment_no: int
    due_date: date
    principal: Decimal
    interest: Decimal
    penalty: Decimal
    total: Decimal
    status: str

    class Config:
        from_attributes = True


class LoanRecalculateIn(BaseModel):
    new_interest_rate: Decimal = Field(gt=0, le=100)


class LoanPaymentIn(BaseModel):
    installment_id: UUID
    paid_by: str | None = None


class LoanPaymentOut(BaseModel):
    id: UUID
    loan_id: UUID
    installment_id: UUID | None
    payment_date: date
    principal_paid: Decimal
    interest_paid: Decimal
    penalty_paid: Decimal
    total_paid: Decimal
    paid_by: str | None

    class Config:
        from_attributes = True


class ApprovalCreate(BaseModel):
    module: str
    action: str
    record_type: str
    record_id: UUID | None = None
    reason: str | None = None
    payload: dict | None = None


class ApprovalDecisionIn(BaseModel):
    decision_note: str | None = None


class ApprovalOut(BaseModel):
    id: UUID
    module: str
    action: str
    record_type: str
    record_id: UUID | None
    requested_by: UUID | None
    approved_by: UUID | None
    approved_at: datetime | None
    status: str
    reason: str | None
    payload: dict | None
    decision_note: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class CashSessionOpenIn(BaseModel):
    opening_cash: Decimal = Field(default=Decimal("0"), ge=0)
    denomination_open: dict[str, int] | None = None

    @field_validator("denomination_open")
    @classmethod
    def validate_open_denominations(cls, value: dict[str, int] | None) -> dict[str, int] | None:
        return validate_denominations(value)


class CashSessionCloseIn(BaseModel):
    closing_cash: Decimal = Field(ge=0)
    denomination_close: dict[str, int] | None = None
    handover_to: UUID | None = None

    @field_validator("denomination_close")
    @classmethod
    def validate_close_denominations(cls, value: dict[str, int] | None) -> dict[str, int] | None:
        return validate_denominations(value)


def validate_denominations(value: dict[str, int] | None) -> dict[str, int] | None:
    if value is None:
        return value
    for denomination, count in value.items():
        if not denomination.isdigit() or int(denomination) <= 0:
            raise ValueError("Denomination keys must be positive whole-number strings")
        if count < 0:
            raise ValueError("Denomination counts cannot be negative")
    return value


class CashSessionOut(BaseModel):
    id: UUID
    branch_id: UUID | None
    cashier_id: UUID
    session_date: date
    opening_cash: Decimal
    closing_cash: Decimal | None
    cash_in: Decimal
    cash_out: Decimal
    denomination_open: dict | None
    denomination_close: dict | None
    handover_to: UUID | None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccountOut(BaseModel):
    id: UUID
    code: str
    name: str
    type: str
    is_active: bool

    class Config:
        from_attributes = True


class TrialBalanceRow(BaseModel):
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class ReportSummary(BaseModel):
    total_share_capital: Decimal
    total_savings_liability: Decimal
    total_term_deposit_liability: Decimal = Decimal("0")
    loan_principal_outstanding: Decimal
    overdue_principal: Decimal
    active_members: int


class FinancialStatement(BaseModel):
    statement_name: str
    as_of_date: date
    rows: list[dict]
    totals: dict


class AutomationTriggerOut(BaseModel):
    task_id: str
    task_name: str
    status: str


class AutomationPostDividendsIn(BaseModel):
    dividend_rate_percent: Decimal = Field(default=Decimal("10.0"), gt=0, le=100)
    narration: str | None = None


class AutomationRunIn(BaseModel):
    run_date: date | None = None


class AutomationRunOut(BaseModel):
    run_date: date
    savings_interest_transactions: int
    savings_interest_amount: Decimal
    auto_deducted_installments: int
    auto_deducted_amount: Decimal
    overdue_installments: int
    penalty_amount: Decimal
    matured_deposits: int
    period: str
    message: str


class InterestRuleCreate(BaseModel):
    scope_type: str = Field(min_length=2, max_length=32)
    scope_code: str = Field(min_length=1, max_length=80)
    method: str = Field(min_length=2, max_length=40)
    posting_frequency: str = Field(min_length=2, max_length=24)
    calculation_frequency: str = Field(default="daily", min_length=2, max_length=24)
    annual_rate: Decimal = Field(ge=0, le=100)
    config: dict | None = None
    effective_from_ad: date
    effective_from_bs: str | None = None
    effective_to_ad: date | None = None
    effective_to_bs: str | None = None
    is_active: bool = True


class InterestRuleUpdate(BaseModel):
    method: str | None = Field(default=None, min_length=2, max_length=40)
    posting_frequency: str | None = Field(default=None, min_length=2, max_length=24)
    calculation_frequency: str | None = Field(default=None, min_length=2, max_length=24)
    annual_rate: Decimal | None = Field(default=None, ge=0, le=100)
    config: dict | None = None
    effective_to_ad: date | None = None
    effective_to_bs: str | None = None
    is_active: bool | None = None


class InterestRuleOut(InterestRuleCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PenaltyRuleCreate(BaseModel):
    scope_type: str = Field(min_length=2, max_length=32)
    scope_code: str = Field(min_length=1, max_length=80)
    method: str = Field(min_length=2, max_length=40)
    frequency: str = Field(min_length=2, max_length=24)
    fixed_amount: Decimal = Field(default=Decimal("0"), ge=0)
    percentage_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    is_compound: bool = False
    grace_days: int = Field(default=0, ge=0)
    config: dict | None = None
    effective_from_ad: date
    effective_from_bs: str | None = None
    effective_to_ad: date | None = None
    effective_to_bs: str | None = None
    is_active: bool = True


class PenaltyRuleUpdate(BaseModel):
    method: str | None = Field(default=None, min_length=2, max_length=40)
    frequency: str | None = Field(default=None, min_length=2, max_length=24)
    fixed_amount: Decimal | None = Field(default=None, ge=0)
    percentage_rate: Decimal | None = Field(default=None, ge=0, le=100)
    is_compound: bool | None = None
    grace_days: int | None = Field(default=None, ge=0)
    config: dict | None = None
    effective_to_ad: date | None = None
    effective_to_bs: str | None = None
    is_active: bool | None = None


class PenaltyRuleOut(PenaltyRuleCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccrualRuleCreate(BaseModel):
    scope_type: str = Field(min_length=2, max_length=32)
    scope_code: str = Field(min_length=1, max_length=80)
    accrual_type: str = Field(min_length=2, max_length=40)
    frequency: str = Field(default="daily", min_length=2, max_length=24)
    debit_account_code: str | None = None
    credit_account_code: str | None = None
    config: dict | None = None
    is_active: bool = True


class AccrualRuleUpdate(BaseModel):
    accrual_type: str | None = Field(default=None, min_length=2, max_length=40)
    frequency: str | None = Field(default=None, min_length=2, max_length=24)
    debit_account_code: str | None = None
    credit_account_code: str | None = None
    config: dict | None = None
    is_active: bool | None = None


class AccrualRuleOut(AccrualRuleCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SchedulerJobOut(BaseModel):
    id: UUID
    name: str
    job_type: str
    cron_expression: str
    timezone: str
    status: str
    last_run_at: datetime | None
    next_run_at: datetime | None
    config: dict | None

    class Config:
        from_attributes = True


class CalculationResultOut(BaseModel):
    id: UUID
    result_type: str
    rule_id: UUID | None
    target_type: str
    target_id: UUID
    calculation_date_ad: date
    calculation_date_bs: str | None
    base_amount: Decimal
    rate: Decimal
    days: int
    amount: Decimal
    status: str
    journal_id: UUID | None
    details: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardMetrics(BaseModel):
    total_members: int
    active_savings_accounts: int
    total_savings: Decimal
    active_loans: int
    loan_outstanding: Decimal
    overdue_installments: int
    pending_installments: int = 0
    penalty_receivable: Decimal = Decimal("0")
    collection_today: Decimal = Decimal("0")
    recent_transactions: list[dict] = []


class BackupRunOut(BaseModel):
    id: UUID
    backup_type: str
    file_path: str | None
    file_size: int | None
    checksum: str | None
    status: str
    requested_by: UUID | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    channel: str = Field(pattern="^(sms|email|whatsapp)$")
    recipient: str
    subject: str | None = None
    body: str
    template_code: str | None = None
    scheduled_for: datetime | None = None
    metadata_json: dict | None = None


class NotificationOut(NotificationCreate):
    id: UUID
    status: str
    provider_message_id: str | None
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class IntegrationEndpointCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    integration_type: str = Field(pattern="^(receipt_printer|passbook_printer|sms|email|whatsapp|file_storage|backup_storage)$")
    name: str
    connection_uri: str | None = None
    config: dict | None = None
    status: str = "active"


class IntegrationEndpointOut(IntegrationEndpointCreate):
    id: UUID
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportRunOut(BaseModel):
    id: UUID
    report_type: str
    period_code: str
    file_path: str | None
    file_size: int | None
    checksum: str | None
    status: str
    generated_by: UUID | None
    summary: dict | None
    created_at: datetime

    class Config:
        from_attributes = True

class WithdrawalRequestCreate(BaseModel):
    member_id: UUID
    savings_account_id: UUID | None = None
    requested_amount: Decimal = Field(gt=0)
    needed_by_date: date | None = None
    priority: str = "normal"
    reason: str | None = None


class WithdrawalDecisionIn(BaseModel):
    approved_amount: Decimal | None = Field(default=None, gt=0)
    decision_note: str | None = None


class WithdrawalRequestOut(BaseModel):
    id: UUID
    member_id: UUID
    savings_account_id: UUID | None
    requested_amount: Decimal
    approved_amount: Decimal | None
    requested_date: date
    needed_by_date: date | None
    priority: str
    status: str
    reason: str | None
    decision_note: str | None
    requested_by: UUID | None
    decided_by: UUID | None
    decided_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class LiquiditySnapshotOut(BaseModel):
    id: UUID
    branch_id: UUID | None
    snapshot_date: date
    cash_balance: Decimal
    bank_balance: Decimal
    liquid_assets: Decimal
    member_savings_liability: Decimal
    term_deposit_liability: Decimal
    pending_withdrawals: Decimal
    liquidity_ratio: Decimal
    status: str
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceAlertOut(BaseModel):
    id: UUID
    rule_code: str
    module: str
    severity: str
    title: str
    description: str
    status: str
    record_type: str | None
    record_id: UUID | None
    assigned_to: UUID | None
    resolved_by: UUID | None
    resolved_at: datetime | None
    resolution_note: str | None
    details: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceCaseCreate(BaseModel):
    case_no: str = Field(min_length=4, max_length=60)
    member_id: UUID | None = None
    alert_id: UUID | None = None
    case_type: str = Field(min_length=3, max_length=60)
    risk_level: str = "medium"
    narrative: str = Field(min_length=10, max_length=5000)
    assigned_to: UUID | None = None


class ComplianceCaseDecisionIn(BaseModel):
    status: str
    resolution_note: str | None = Field(default=None, max_length=5000)


class ComplianceResolveIn(BaseModel):
    resolution_note: str


class LoanApplicationCreate(BaseModel):
    member_id: UUID
    loan_no: str
    loan_type: str
    amount: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(ge=0)
    tenure_months: int = Field(gt=0, le=360)
    purpose: str | None = None
    interest_method: str = "flat_monthly"
    repayment_method: str = "emi"


class LoanReviewCreate(BaseModel):
    stage: str = "officer_review"
    recommendation: str
    comments: str | None = None
    risk_score: int | None = Field(default=None, ge=0, le=100)
    details: dict | None = None


class LoanReviewOut(LoanReviewCreate):
    id: UUID
    loan_id: UUID
    reviewed_by: UUID
    reviewed_at: datetime

    class Config:
        from_attributes = True


class LoanApprovalIn(BaseModel):
    approval_limit_level: str = "branch_manager"
    comments: str | None = None


class LoanRecoveryActionCreate(BaseModel):
    action_date: date = Field(default_factory=date.today)
    action_type: str = Field(min_length=3, max_length=40)
    outcome: str | None = Field(default=None, max_length=3000)
    promised_amount: Decimal | None = Field(default=None, gt=0)
    promised_date: date | None = None
    next_action_date: date | None = None
    status: str = "open"


class LoanGuarantorCreate(BaseModel):
    member_id: UUID | None = None
    name: str
    phone: str | None = None
    citizenship_number: str | None = None
    guarantee_amount: Decimal = Field(default=Decimal("0"), ge=0)


class LoanGuarantorOut(LoanGuarantorCreate):
    id: UUID
    loan_id: UUID
    status: str

    class Config:
        from_attributes = True


class LoanCollateralCreate(BaseModel):
    collateral_type: str
    description: str
    assessed_value: Decimal = Field(default=Decimal("0"), ge=0)
    document_ref: str | None = None


class LoanCollateralOut(LoanCollateralCreate):
    id: UUID
    loan_id: UUID
    status: str

    class Config:
        from_attributes = True


class FieldVisitCreate(BaseModel):
    member_id: UUID
    loan_id: UUID | None = None
    visit_date: date | None = None
    location: str | None = None
    purpose: str
    findings: str | None = None
    recommendation: str | None = None
    photos: list[dict] | None = None


class FieldVisitOut(FieldVisitCreate):
    id: UUID
    visited_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class GovernanceDecisionCreate(BaseModel):
    decision_body: str
    meeting_no: str | None = None
    decision_date: date | None = None
    title: str
    decision_text: str
    related_module: str | None = None
    related_record_id: UUID | None = None


class GovernanceDecisionOut(GovernanceDecisionCreate):
    id: UUID
    minuted_by: UUID | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SystemPolicyCreate(BaseModel):
    code: str
    name: str
    policy_type: str
    config: dict
    status: str = "active"


class SystemPolicyOut(SystemPolicyCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectorRouteCreate(BaseModel):
    name: str
    area: str | None = None
    assigned_collector_id: UUID | None = None
    branch_id: UUID | None = None


class CollectorRouteOut(CollectorRouteCreate):
    id: UUID
    status: str

    class Config:
        from_attributes = True


class FieldCollectionBatchCreate(BaseModel):
    route_id: UUID | None = None
    collection_date: date | None = None
    opening_cash: Decimal = Field(default=Decimal("0"), ge=0)
    expected_total: Decimal = Field(default=Decimal("0"), ge=0)


class FieldCollectionBatchOut(BaseModel):
    id: UUID
    branch_id: UUID | None = None
    collector_id: UUID
    route_id: UUID | None = None
    collection_date: date
    opening_cash: Decimal
    expected_total: Decimal
    collected_total: Decimal
    submitted_at: datetime | None = None
    verified_by: UUID | None = None
    verified_at: datetime | None = None
    posted_by: UUID | None = None
    posted_at: datetime | None = None
    denomination_close: dict | None = None
    verification_note: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FieldCollectionEntryCreate(BaseModel):
    member_id: UUID
    savings_account_id: UUID | None = None
    loan_id: UUID | None = None
    loan_installment_id: UUID | None = None
    collection_type: str = "savings_deposit"
    payment_method: str = "cash"
    amount: Decimal = Field(gt=0)
    share_units: int | None = Field(default=None, gt=0)
    share_rate: Decimal | None = Field(default=None, gt=0)
    fee_code: str | None = None
    receipt_no: str | None = None
    client_request_id: str
    collected_at: datetime | None = None
    gps_lat: Decimal | None = None
    gps_lng: Decimal | None = None
    device_id: str | None = None
    narration: str | None = None
    metadata_json: dict | None = None


class FieldCollectionEntryOut(BaseModel):
    id: UUID
    batch_id: UUID
    member_id: UUID
    savings_account_id: UUID | None = None
    loan_id: UUID | None = None
    loan_installment_id: UUID | None = None
    collection_type: str
    payment_method: str
    amount: Decimal
    share_units: int | None = None
    share_rate: Decimal | None = None
    fee_code: str | None = None
    receipt_no: str
    client_request_id: str
    collected_at: datetime
    gps_lat: Decimal | None = None
    gps_lng: Decimal | None = None
    device_id: str | None = None
    narration: str | None = None
    metadata_json: dict | None = None
    posted_transaction_id: UUID | None = None
    status: str

    class Config:
        from_attributes = True


class FieldCollectionBatchDetail(BaseModel):
    batch: FieldCollectionBatchOut
    entries: list[FieldCollectionEntryOut]


class FieldCollectionSubmitIn(BaseModel):
    denomination_close: dict | None = None


class FieldCollectionVerifyIn(BaseModel):
    denomination_close: dict | None = None
    verification_note: str | None = None


class FieldCollectionRejectIn(BaseModel):
    verification_note: str


class FieldCollectionSummaryOut(BaseModel):
    total_batches: int
    draft_batches: int
    submitted_batches: int
    verified_batches: int
    posted_batches: int
    rejected_batches: int
    collected_total: Decimal
    pending_total: Decimal
    posted_total: Decimal
    by_type: dict[str, Decimal]
    by_status: dict[str, Decimal]
