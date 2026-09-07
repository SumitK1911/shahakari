"""add controls monitoring tables

Revision ID: 20260619_0900
Revises: 20260609_1300
Create Date: 2026-06-19 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260619_0900"
down_revision = "20260609_1300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "withdrawal_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("savings_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(16, 2), nullable=True),
        sa.Column("requested_date", sa.Date(), nullable=False),
        sa.Column("needed_by_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["savings_account_id"], ["savings_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_withdrawal_requests_status_priority", "withdrawal_requests", ["status", "priority", "requested_date"])
    op.create_index("ix_withdrawal_requests_member_status", "withdrawal_requests", ["member_id", "status"])

    op.create_table(
        "liquidity_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("cash_balance", sa.Numeric(16, 2), nullable=False),
        sa.Column("bank_balance", sa.Numeric(16, 2), nullable=False),
        sa.Column("liquid_assets", sa.Numeric(16, 2), nullable=False),
        sa.Column("member_savings_liability", sa.Numeric(16, 2), nullable=False),
        sa.Column("term_deposit_liability", sa.Numeric(16, 2), nullable=False),
        sa.Column("pending_withdrawals", sa.Numeric(16, 2), nullable=False),
        sa.Column("liquidity_ratio", sa.Numeric(7, 4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_liquidity_snapshots_branch_date", "liquidity_snapshots", ["branch_id", "snapshot_date"])

    op.create_table(
        "compliance_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_code", sa.String(length=80), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("record_type", sa.String(length=80), nullable=True),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_alerts_status_severity", "compliance_alerts", ["status", "severity", "created_at"])
    op.create_index("ix_compliance_alerts_rule", "compliance_alerts", ["rule_code", "status"])


def downgrade() -> None:
    op.drop_index("ix_compliance_alerts_rule", table_name="compliance_alerts")
    op.drop_index("ix_compliance_alerts_status_severity", table_name="compliance_alerts")
    op.drop_table("compliance_alerts")
    op.drop_index("ix_liquidity_snapshots_branch_date", table_name="liquidity_snapshots")
    op.drop_table("liquidity_snapshots")
    op.drop_index("ix_withdrawal_requests_member_status", table_name="withdrawal_requests")
    op.drop_index("ix_withdrawal_requests_status_priority", table_name="withdrawal_requests")
    op.drop_table("withdrawal_requests")
