"""add production organization and loan control models

Revision ID: 20260619_1000
Revises: 20260619_0900
Create Date: 2026-06-19 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260619_1000"
down_revision = "20260619_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("loans", sa.Column("applied_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("loans", sa.Column("recommended_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("loans", sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("loans", sa.Column("disbursed_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("loans", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("loans", sa.Column("disbursed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("loans", sa.Column("approval_limit_level", sa.String(length=40), nullable=True))
    op.add_column("loans", sa.Column("purpose", sa.Text(), nullable=True))
    op.create_foreign_key("fk_loans_applied_by_users", "loans", "users", ["applied_by"], ["id"])
    op.create_foreign_key("fk_loans_recommended_by_users", "loans", "users", ["recommended_by"], ["id"])
    op.create_foreign_key("fk_loans_approved_by_users", "loans", "users", ["approved_by"], ["id"])
    op.create_foreign_key("fk_loans_disbursed_by_users", "loans", "users", ["disbursed_by"], ["id"])

    op.create_table("organization_positions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("code", sa.String(80), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("level", sa.String(40), nullable=False), sa.Column("reports_to_code", sa.String(80)), sa.Column("description", sa.Text()), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("code", name="uq_organization_positions_code"))
    op.create_table("system_policies", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("code", sa.String(80), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("policy_type", sa.String(40), nullable=False), sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("code", name="uq_system_policies_code"))
    op.create_table("membership_accounts", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("members.id"), nullable=False), sa.Column("membership_fee", sa.Numeric(16, 2), nullable=False), sa.Column("required_share_units", sa.Integer(), nullable=False), sa.Column("required_savings_deposit", sa.Numeric(16, 2), nullable=False), sa.Column("paid_fee", sa.Numeric(16, 2), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")), sa.Column("approved_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("member_id", name="uq_membership_accounts_member"))
    op.create_table("loan_guarantors", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id"), nullable=False), sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("members.id")), sa.Column("name", sa.String(180), nullable=False), sa.Column("phone", sa.String(40)), sa.Column("citizenship_number", sa.String(80)), sa.Column("guarantee_amount", sa.Numeric(16, 2), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("loan_collaterals", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id"), nullable=False), sa.Column("collateral_type", sa.String(80), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("assessed_value", sa.Numeric(16, 2), nullable=False), sa.Column("document_ref", sa.String(160)), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("loan_reviews", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id"), nullable=False), sa.Column("stage", sa.String(40), nullable=False), sa.Column("recommendation", sa.String(40), nullable=False), sa.Column("comments", sa.Text()), sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False), sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("risk_score", sa.Integer()), sa.Column("details", postgresql.JSONB(astext_type=sa.Text())), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("field_visits", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("members.id"), nullable=False), sa.Column("loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id")), sa.Column("visit_date", sa.Date(), nullable=False), sa.Column("visited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False), sa.Column("location", sa.String(180)), sa.Column("purpose", sa.String(120), nullable=False), sa.Column("findings", sa.Text()), sa.Column("recommendation", sa.Text()), sa.Column("photos", postgresql.JSONB(astext_type=sa.Text())), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("governance_decisions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("decision_body", sa.String(80), nullable=False), sa.Column("meeting_no", sa.String(80)), sa.Column("decision_date", sa.Date(), nullable=False), sa.Column("title", sa.String(180), nullable=False), sa.Column("decision_text", sa.Text(), nullable=False), sa.Column("related_module", sa.String(80)), sa.Column("related_record_id", postgresql.UUID(as_uuid=True)), sa.Column("minuted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("expenses", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("expense_date", sa.Date(), nullable=False), sa.Column("category", sa.String(80), nullable=False), sa.Column("amount", sa.Numeric(16, 2), nullable=False), sa.Column("vendor", sa.String(180)), sa.Column("narration", sa.Text(), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")), sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal_entries.id")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("fixed_assets", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("asset_code", sa.String(80), nullable=False), sa.Column("name", sa.String(180), nullable=False), sa.Column("asset_type", sa.String(80), nullable=False), sa.Column("purchase_date", sa.Date(), nullable=False), sa.Column("purchase_cost", sa.Numeric(16, 2), nullable=False), sa.Column("accumulated_depreciation", sa.Numeric(16, 2), nullable=False), sa.Column("location", sa.String(180)), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("asset_code", name="uq_fixed_assets_code"))


def downgrade() -> None:
    for table in ["fixed_assets", "expenses", "governance_decisions", "field_visits", "loan_reviews", "loan_collaterals", "loan_guarantors", "membership_accounts", "system_policies", "organization_positions"]:
        op.drop_table(table)
    op.drop_constraint("fk_loans_disbursed_by_users", "loans", type_="foreignkey")
    op.drop_constraint("fk_loans_approved_by_users", "loans", type_="foreignkey")
    op.drop_constraint("fk_loans_recommended_by_users", "loans", type_="foreignkey")
    op.drop_constraint("fk_loans_applied_by_users", "loans", type_="foreignkey")
    for column in ["purpose", "approval_limit_level", "disbursed_at", "approved_at", "disbursed_by", "approved_by", "recommended_by", "applied_by"]:
        op.drop_column("loans", column)
