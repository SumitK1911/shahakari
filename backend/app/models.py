import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    module: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text)


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), index=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id"), index=True)
    name: Mapped[str] = mapped_column(String(140))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Member(Base, TimestampMixin):
    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("member_no", name="uq_members_member_no"),
        Index("ix_members_search", "name", "phone", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    member_no: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(180), index=True)
    name_nepali: Mapped[str | None] = mapped_column(String(180))
    dob: Mapped[date | None] = mapped_column(Date)
    dob_bs: Mapped[str | None] = mapped_column(String(16))
    gender: Mapped[str | None] = mapped_column(String(32))
    marital_status: Mapped[str | None] = mapped_column(String(32))
    nationality: Mapped[str] = mapped_column(String(80), default="Nepali")
    phone: Mapped[str | None] = mapped_column(String(40), index=True)
    secondary_phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(180))
    emergency_contact_number: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(Text)
    address_profile: Mapped[dict | None] = mapped_column(JSONB)
    documents: Mapped[list[dict] | None] = mapped_column(JSONB)
    family_profile: Mapped[dict | None] = mapped_column(JSONB)
    guardian_profile: Mapped[dict | None] = mapped_column(JSONB)
    occupation_profile: Mapped[dict | None] = mapped_column(JSONB)
    income_sources: Mapped[list[dict] | None] = mapped_column(JSONB)
    membership_type: Mapped[str | None] = mapped_column(String(80))
    join_date: Mapped[date | None] = mapped_column(Date)
    risk_category: Mapped[str] = mapped_column(String(24), default="low", index=True)
    is_pep: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    media_profile: Mapped[dict | None] = mapped_column(JSONB)
    kyc_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)

    nominees: Mapped[list["MemberNominee"]] = relationship(back_populates="member", cascade="all, delete-orphan")


class MemberNominee(Base, TimestampMixin):
    __tablename__ = "member_nominees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    relation: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(Text)
    citizenship_number: Mapped[str | None] = mapped_column(String(80))

    member: Mapped[Member] = relationship(back_populates="nominees")


class Share(Base, TimestampMixin):
    __tablename__ = "shares"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    total_share: Mapped[int] = mapped_column(default=0)
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class ShareTransaction(Base, TimestampMixin):
    __tablename__ = "share_transactions"
    __table_args__ = (Index("ix_share_tx_member_date", "member_id", "trans_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    trans_type: Mapped[str] = mapped_column(String(24), index=True)
    shares: Mapped[int]
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    trans_date: Mapped[date] = mapped_column(Date, index=True)
    narration: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class TermDeposit(Base, TimestampMixin):
    __tablename__ = "term_deposits"
    __table_args__ = (
        UniqueConstraint("deposit_no", name="uq_term_deposits_deposit_no"),
        Index("ix_term_deposits_member_status", "member_id", "status"),
        Index("ix_term_deposits_maturity_status", "maturity_date", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    deposit_no: Mapped[str] = mapped_column(String(40), index=True)
    deposit_type: Mapped[str] = mapped_column(String(16), index=True)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    installment_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=0)
    opened_date: Mapped[date] = mapped_column(Date, index=True)
    maturity_date: Mapped[date] = mapped_column(Date, index=True)
    maturity_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class TermDepositTransaction(Base, TimestampMixin):
    __tablename__ = "term_deposit_transactions"
    __table_args__ = (Index("ix_term_deposit_tx_deposit_date", "deposit_id", "trans_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deposit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("term_deposits.id"), index=True)
    trans_type: Mapped[str] = mapped_column(String(24), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    balance: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    trans_date: Mapped[date] = mapped_column(Date, index=True)
    narration: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class SavingsAccount(Base, TimestampMixin):
    __tablename__ = "savings_accounts"
    __table_args__ = (UniqueConstraint("account_no", name="uq_savings_account_no"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    account_no: Mapped[str] = mapped_column(String(40), index=True)
    account_type: Mapped[str] = mapped_column(String(40), index=True)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=0)
    balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("product_type", "code", name="uq_products_type_code"),
        Index("ix_products_type_status", "product_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_type: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(160))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(9, 4), default=0)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    tenure_months: Mapped[int | None] = mapped_column(Integer)
    config: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class InterestRule(Base, TimestampMixin):
    __tablename__ = "interest_rules"
    __table_args__ = (
        Index("ix_interest_rules_scope_active", "scope_type", "scope_code", "is_active"),
        UniqueConstraint("scope_type", "scope_code", "effective_from_ad", name="uq_interest_rules_scope_effective"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_type: Mapped[str] = mapped_column(String(32), index=True)
    scope_code: Mapped[str] = mapped_column(String(80), index=True)
    method: Mapped[str] = mapped_column(String(40), index=True)
    posting_frequency: Mapped[str] = mapped_column(String(24), index=True)
    calculation_frequency: Mapped[str] = mapped_column(String(24), default="daily", index=True)
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(9, 4), default=0)
    config: Mapped[dict | None] = mapped_column(JSONB)
    effective_from_ad: Mapped[date] = mapped_column(Date, index=True)
    effective_from_bs: Mapped[str | None] = mapped_column(String(16), index=True)
    effective_to_ad: Mapped[date | None] = mapped_column(Date, index=True)
    effective_to_bs: Mapped[str | None] = mapped_column(String(16), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class PenaltyRule(Base, TimestampMixin):
    __tablename__ = "penalty_rules"
    __table_args__ = (
        Index("ix_penalty_rules_scope_active", "scope_type", "scope_code", "is_active"),
        UniqueConstraint("scope_type", "scope_code", "effective_from_ad", name="uq_penalty_rules_scope_effective"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_type: Mapped[str] = mapped_column(String(32), index=True)
    scope_code: Mapped[str] = mapped_column(String(80), index=True)
    method: Mapped[str] = mapped_column(String(40), index=True)
    frequency: Mapped[str] = mapped_column(String(24), index=True)
    fixed_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    percentage_rate: Mapped[Decimal] = mapped_column(Numeric(9, 4), default=0)
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False)
    grace_days: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict | None] = mapped_column(JSONB)
    effective_from_ad: Mapped[date] = mapped_column(Date, index=True)
    effective_from_bs: Mapped[str | None] = mapped_column(String(16), index=True)
    effective_to_ad: Mapped[date | None] = mapped_column(Date, index=True)
    effective_to_bs: Mapped[str | None] = mapped_column(String(16), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class AccrualRule(Base, TimestampMixin):
    __tablename__ = "accrual_rules"
    __table_args__ = (Index("ix_accrual_rules_scope_active", "scope_type", "scope_code", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_type: Mapped[str] = mapped_column(String(32), index=True)
    scope_code: Mapped[str] = mapped_column(String(80), index=True)
    accrual_type: Mapped[str] = mapped_column(String(40), index=True)
    frequency: Mapped[str] = mapped_column(String(24), default="daily", index=True)
    debit_account_code: Mapped[str | None] = mapped_column(String(40))
    credit_account_code: Mapped[str | None] = mapped_column(String(40))
    config: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class SchedulerJob(Base, TimestampMixin):
    __tablename__ = "scheduler_jobs"
    __table_args__ = (
        UniqueConstraint("name", name="uq_scheduler_jobs_name"),
        Index("ix_scheduler_jobs_due", "status", "next_run_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), index=True)
    job_type: Mapped[str] = mapped_column(String(60), index=True)
    cron_expression: Mapped[str] = mapped_column(String(80))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kathmandu")
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(120))
    config: Mapped[dict | None] = mapped_column(JSONB)


class CalculationResult(Base, TimestampMixin):
    __tablename__ = "calculation_results"
    __table_args__ = (
        Index("ix_calculation_results_target_date", "target_type", "target_id", "calculation_date_ad"),
        Index("ix_calculation_results_type_status", "result_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_type: Mapped[str] = mapped_column(String(40), index=True)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    target_type: Mapped[str] = mapped_column(String(40), index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    calculation_date_ad: Mapped[date] = mapped_column(Date, index=True)
    calculation_date_bs: Mapped[str | None] = mapped_column(String(16), index=True)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    rate: Mapped[Decimal] = mapped_column(Numeric(9, 4), default=0)
    days: Mapped[int] = mapped_column(Integer, default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(24), default="calculated", index=True)
    journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    details: Mapped[dict | None] = mapped_column(JSONB)


class SavingsTransaction(Base, TimestampMixin):
    __tablename__ = "savings_transactions"
    __table_args__ = (Index("ix_savings_tx_account_date", "account_id", "trans_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("savings_accounts.id"), index=True)
    trans_type: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    balance: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    trans_date: Mapped[date] = mapped_column(Date, index=True)
    narration: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class CollectorRoute(Base, TimestampMixin):
    __tablename__ = "collector_routes"
    __table_args__ = (Index("ix_collector_routes_collector_status", "assigned_collector_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    area: Mapped[str | None] = mapped_column(String(180))
    assigned_collector_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class FieldCollectionBatch(Base, TimestampMixin):
    __tablename__ = "field_collection_batches"
    __table_args__ = (
        Index("ix_field_collection_batches_collector_date", "collector_id", "collection_date"),
        Index("ix_field_collection_batches_status_date", "status", "collection_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    collector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    route_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collector_routes.id"), index=True)
    collection_date: Mapped[date] = mapped_column(Date, index=True)
    opening_cash: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    expected_total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    collected_total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    denomination_close: Mapped[dict | None] = mapped_column(JSONB)
    verification_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)


class FieldCollectionEntry(Base, TimestampMixin):
    __tablename__ = "field_collection_entries"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_field_collection_client_request"),
        UniqueConstraint("receipt_no", name="uq_field_collection_receipt_no"),
        Index("ix_field_collection_entries_batch_status", "batch_id", "status"),
        Index("ix_field_collection_entries_member_date", "member_id", "collected_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("field_collection_batches.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    savings_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("savings_accounts.id"), index=True)
    loan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("loans.id"), index=True)
    loan_installment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("loan_installments.id"), index=True)
    collection_type: Mapped[str] = mapped_column(String(32), index=True)
    payment_method: Mapped[str] = mapped_column(String(24), default="cash", index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    share_units: Mapped[int | None] = mapped_column(Integer)
    share_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    fee_code: Mapped[str | None] = mapped_column(String(60), index=True)
    receipt_no: Mapped[str] = mapped_column(String(60), index=True)
    client_request_id: Mapped[str] = mapped_column(String(80), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    gps_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    gps_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    device_id: Mapped[str | None] = mapped_column(String(120))
    narration: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    posted_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)


class Loan(Base, TimestampMixin):
    __tablename__ = "loans"
    __table_args__ = (Index("ix_loans_member_status", "member_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    loan_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    loan_type: Mapped[str] = mapped_column(String(60), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    tenure_months: Mapped[int]
    disburse_date: Mapped[date | None] = mapped_column(Date)
    outstanding_principal: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    applied_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    recommended_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    disbursed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disbursed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_limit_level: Mapped[str | None] = mapped_column(String(40))
    purpose: Mapped[str | None] = mapped_column(Text)
    interest_method: Mapped[str] = mapped_column(String(32), default="flat_monthly", index=True)
    repayment_method: Mapped[str] = mapped_column(String(32), default="emi", index=True)


class LoanInstallment(Base, TimestampMixin):
    __tablename__ = "loan_installments"
    __table_args__ = (Index("ix_installments_due_status", "due_date", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loans.id"), index=True)
    installment_no: Mapped[int]
    due_date: Mapped[date] = mapped_column(Date, index=True)
    principal: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    interest: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    penalty: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)


class LoanPayment(Base, TimestampMixin):
    __tablename__ = "loan_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loans.id"), index=True)
    installment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("loan_installments.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    principal_paid: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    interest_paid: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    penalty_paid: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    total_paid: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    paid_by: Mapped[str | None] = mapped_column(String(140))


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"
    __table_args__ = (
        Index("ix_approval_status_module", "status", "module"),
        Index("ix_approval_record", "record_type", "record_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module: Mapped[str] = mapped_column(String(60), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    record_type: Mapped[str] = mapped_column(String(80), index=True)
    record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    decision_note: Mapped[str | None] = mapped_column(Text)


class CashSession(Base, TimestampMixin):
    __tablename__ = "cash_sessions"
    __table_args__ = (
        UniqueConstraint("cashier_id", "session_date", "status", name="uq_cash_sessions_cashier_date_status"),
        Index("ix_cash_sessions_status_date", "status", "session_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    cashier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    opening_cash: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    closing_cash: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    cash_in: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    cash_out: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    denomination_open: Mapped[dict | None] = mapped_column(JSONB)
    denomination_close: Mapped[dict | None] = mapped_column(JSONB)
    handover_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    type: Mapped[str] = mapped_column(String(40), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    narration: Mapped[str] = mapped_column(Text)
    ref_type: Mapped[str | None] = mapped_column(String(60), index=True)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class LedgerEntry(Base, TimestampMixin):
    __tablename__ = "ledger_entries"
    __table_args__ = (Index("ix_ledger_account_date", "account_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)


class FiscalYear(Base, TimestampMixin):
    __tablename__ = "fiscal_years"
    __table_args__ = (
        UniqueConstraint("code", name="uq_fiscal_years_code"),
        Index("ix_fiscal_years_period", "start_date_ad", "end_date_ad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(16), index=True)
    start_date_ad: Mapped[date] = mapped_column(Date, index=True)
    start_date_bs: Mapped[str] = mapped_column(String(16), index=True)
    end_date_ad: Mapped[date] = mapped_column(Date, index=True)
    end_date_bs: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class DayClosing(Base, TimestampMixin):
    __tablename__ = "day_closings"
    __table_args__ = (
        UniqueConstraint("branch_id", "closing_date_ad", name="uq_day_closings_branch_date"),
        Index("ix_day_closings_status_date", "status", "closing_date_ad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    fiscal_year_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fiscal_years.id"), index=True)
    closing_date_ad: Mapped[date] = mapped_column(Date, index=True)
    closing_date_bs: Mapped[str | None] = mapped_column(String(16), index=True)
    cashier_closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    cashier_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manager_verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    manager_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="cashier_pending", index=True)
    cash_summary: Mapped[dict | None] = mapped_column(JSONB)
    exception_summary: Mapped[dict | None] = mapped_column(JSONB)


class MonthClosing(Base, TimestampMixin):
    __tablename__ = "month_closings"
    __table_args__ = (
        UniqueConstraint("branch_id", "fiscal_year_id", "month_no", name="uq_month_closings_branch_month"),
        Index("ix_month_closings_status_date", "status", "month_end_ad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fiscal_years.id"), index=True)
    month_no: Mapped[int] = mapped_column(Integer, index=True)
    month_start_ad: Mapped[date] = mapped_column(Date)
    month_start_bs: Mapped[str | None] = mapped_column(String(16))
    month_end_ad: Mapped[date] = mapped_column(Date, index=True)
    month_end_bs: Mapped[str | None] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    posted_journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    summary: Mapped[dict | None] = mapped_column(JSONB)


class YearClosing(Base, TimestampMixin):
    __tablename__ = "year_closings"
    __table_args__ = (
        UniqueConstraint("branch_id", "fiscal_year_id", name="uq_year_closings_branch_fiscal_year"),
        Index("ix_year_closings_status_date", "status", "closed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fiscal_years.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    closing_trial_balance: Mapped[dict | None] = mapped_column(JSONB)
    reserve_allocation: Mapped[dict | None] = mapped_column(JSONB)
    dividend_summary: Mapped[dict | None] = mapped_column(JSONB)
    retained_earnings_journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    opening_balance_journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    module: Mapped[str] = mapped_column(String(80), index=True)
    record_id: Mapped[str | None] = mapped_column(String(80), index=True)
    diff: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class BackupRun(Base, TimestampMixin):
    __tablename__ = "backup_runs"
    __table_args__ = (Index("ix_backup_runs_status_created", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_type: Mapped[str] = mapped_column(String(40), default="database", index=True)
    file_path: Mapped[str | None] = mapped_column(Text)
    file_size: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class NotificationMessage(Base, TimestampMixin):
    __tablename__ = "notification_messages"
    __table_args__ = (
        Index("ix_notification_status_channel", "status", "channel"),
        Index("ix_notification_recipient", "recipient", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(24), index=True)
    recipient: Mapped[str] = mapped_column(String(180), index=True)
    subject: Mapped[str | None] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    template_code: Mapped[str | None] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(160))
    error_message: Mapped[str | None] = mapped_column(Text)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)


class IntegrationEndpoint(Base, TimestampMixin):
    __tablename__ = "integration_endpoints"
    __table_args__ = (UniqueConstraint("code", name="uq_integration_endpoints_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), index=True)
    integration_type: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(160))
    connection_uri: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportRun(Base, TimestampMixin):
    __tablename__ = "report_runs"
    __table_args__ = (
        Index("ix_report_runs_type_period", "report_type", "period_code"),
        Index("ix_report_runs_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type: Mapped[str] = mapped_column(String(60), index=True)
    period_code: Mapped[str] = mapped_column(String(40), index=True)
    file_path: Mapped[str | None] = mapped_column(Text)
    file_size: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24), default="generated", index=True)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    summary: Mapped[dict | None] = mapped_column(JSONB)

class WithdrawalRequest(Base, TimestampMixin):
    __tablename__ = "withdrawal_requests"
    __table_args__ = (
        Index("ix_withdrawal_requests_status_priority", "status", "priority", "requested_date"),
        Index("ix_withdrawal_requests_member_status", "member_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    savings_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("savings_accounts.id"), index=True)
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    approved_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    requested_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    needed_by_date: Mapped[date | None] = mapped_column(Date, index=True)
    priority: Mapped[str] = mapped_column(String(24), default="normal", index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    decision_note: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LiquiditySnapshot(Base, TimestampMixin):
    __tablename__ = "liquidity_snapshots"
    __table_args__ = (Index("ix_liquidity_snapshots_branch_date", "branch_id", "snapshot_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    bank_balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    liquid_assets: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    member_savings_liability: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    term_deposit_liability: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    pending_withdrawals: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    liquidity_ratio: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=0)
    status: Mapped[str] = mapped_column(String(24), default="normal", index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class ComplianceCase(Base, TimestampMixin):
    __tablename__ = "compliance_cases"
    __table_args__ = (UniqueConstraint("case_no", name="uq_compliance_cases_case_no"), Index("ix_compliance_cases_status_risk", "status", "risk_level"))

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_no: Mapped[str] = mapped_column(String(60), index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("members.id"), index=True)
    alert_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("compliance_alerts.id"), index=True)
    case_type: Mapped[str] = mapped_column(String(60), index=True)
    risk_level: Mapped[str] = mapped_column(String(24), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    narrative: Mapped[str] = mapped_column(Text)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class ComplianceAlert(Base, TimestampMixin):
    __tablename__ = "compliance_alerts"
    __table_args__ = (
        Index("ix_compliance_alerts_status_severity", "status", "severity", "created_at"),
        Index("ix_compliance_alerts_rule", "rule_code", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code: Mapped[str] = mapped_column(String(80), index=True)
    module: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(24), default="medium", index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    record_type: Mapped[str | None] = mapped_column(String(80), index=True)
    record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSONB)

class OrganizationPosition(Base, TimestampMixin):
    __tablename__ = "organization_positions"
    __table_args__ = (UniqueConstraint("code", name="uq_organization_positions_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(160))
    level: Mapped[str] = mapped_column(String(40), index=True)
    reports_to_code: Mapped[str | None] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class SystemPolicy(Base, TimestampMixin):
    __tablename__ = "system_policies"
    __table_args__ = (UniqueConstraint("code", name="uq_system_policies_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(160))
    policy_type: Mapped[str] = mapped_column(String(40), index=True)
    config: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class MembershipAccount(Base, TimestampMixin):
    __tablename__ = "membership_accounts"
    __table_args__ = (UniqueConstraint("member_id", name="uq_membership_accounts_member"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    membership_fee: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    required_share_units: Mapped[int] = mapped_column(Integer, default=0)
    required_savings_deposit: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    paid_fee: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoanRecoveryAction(Base, TimestampMixin):
    __tablename__ = "loan_recovery_actions"
    __table_args__ = (Index("ix_loan_recovery_actions_loan_date", "loan_id", "action_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loans.id"), index=True)
    action_date: Mapped[date] = mapped_column(Date, index=True)
    action_type: Mapped[str] = mapped_column(String(40), index=True)
    outcome: Mapped[str | None] = mapped_column(Text)
    promised_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    promised_date: Mapped[date | None] = mapped_column(Date)
    next_action_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class LoanGuarantor(Base, TimestampMixin):
    __tablename__ = "loan_guarantors"
    __table_args__ = (Index("ix_loan_guarantors_loan", "loan_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loans.id"), index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("members.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(40))
    citizenship_number: Mapped[str | None] = mapped_column(String(80))
    guarantee_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class LoanCollateral(Base, TimestampMixin):
    __tablename__ = "loan_collaterals"
    __table_args__ = (Index("ix_loan_collaterals_loan", "loan_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loans.id"), index=True)
    collateral_type: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text)
    assessed_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    document_ref: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class LoanReview(Base, TimestampMixin):
    __tablename__ = "loan_reviews"
    __table_args__ = (Index("ix_loan_reviews_loan_stage", "loan_id", "stage"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loans.id"), index=True)
    stage: Mapped[str] = mapped_column(String(40), index=True)
    recommendation: Mapped[str] = mapped_column(String(40), index=True)
    comments: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict | None] = mapped_column(JSONB)


class FieldVisit(Base, TimestampMixin):
    __tablename__ = "field_visits"
    __table_args__ = (Index("ix_field_visits_member_date", "member_id", "visit_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), index=True)
    loan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("loans.id"), index=True)
    visit_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    visited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    location: Mapped[str | None] = mapped_column(String(180))
    purpose: Mapped[str] = mapped_column(String(120), index=True)
    findings: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    photos: Mapped[list[dict] | None] = mapped_column(JSONB)


class GovernanceDecision(Base, TimestampMixin):
    __tablename__ = "governance_decisions"
    __table_args__ = (Index("ix_governance_decisions_body_date", "decision_body", "decision_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_body: Mapped[str] = mapped_column(String(80), index=True)
    meeting_no: Mapped[str | None] = mapped_column(String(80), index=True)
    decision_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    title: Mapped[str] = mapped_column(String(180))
    decision_text: Mapped[str] = mapped_column(Text)
    related_module: Mapped[str | None] = mapped_column(String(80), index=True)
    related_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    minuted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="approved", index=True)


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"
    __table_args__ = (Index("ix_expenses_date_status", "expense_date", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    vendor: Mapped[str | None] = mapped_column(String(180))
    narration: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="posted", index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("journal_entries.id"), index=True)


class FixedAsset(Base, TimestampMixin):
    __tablename__ = "fixed_assets"
    __table_args__ = (UniqueConstraint("asset_code", name="uq_fixed_assets_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180))
    asset_type: Mapped[str] = mapped_column(String(80), index=True)
    purchase_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    purchase_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    accumulated_depreciation: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    location: Mapped[str | None] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)


class Investment(Base, TimestampMixin):
    """External investments made by the cooperative (FDs in banks, shares, bonds, etc.)"""
    __tablename__ = "investments"
    __table_args__ = (UniqueConstraint("investment_no", name="uq_investments_no"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investment_no: Mapped[str] = mapped_column(String(60), index=True)
    # Type: fd (Fixed Deposit), share (Company Share), bond (Government Bond),
    #        mutual_fund, debenture, other
    investment_type: Mapped[str] = mapped_column(String(40), index=True)
    institution_name: Mapped[str] = mapped_column(String(200))   # e.g. "NIC Asia Bank"
    instrument_name: Mapped[str | None] = mapped_column(String(200))  # e.g. "NIC Asia FD-2081"
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))          # Invested amount
    current_value: Mapped[Decimal] = mapped_column(Numeric(16, 2))   # Latest valuation
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=0)  # Annual %
    invested_date: Mapped[date] = mapped_column(Date, index=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, index=True)
    maturity_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    # Status: active, matured, redeemed, written_off
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    transactions: Mapped[list["InvestmentTransaction"]] = relationship(
        "InvestmentTransaction", back_populates="investment", lazy="selectin"
    )


class InvestmentTransaction(Base, TimestampMixin):
    """Interest receipts, partial redemptions, revaluations for an investment"""
    __tablename__ = "investment_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investments.id", ondelete="CASCADE"), index=True)
    # trans_type: interest_received, principal_redeemed, revaluation, maturity_payout
    trans_type: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    trans_date: Mapped[date] = mapped_column(Date, index=True)
    narration: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    investment: Mapped["Investment"] = relationship("Investment", back_populates="transactions")



