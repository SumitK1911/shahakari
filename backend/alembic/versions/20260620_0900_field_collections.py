"""add field collection workflow

Revision ID: 20260620_0900
Revises: 20260619_1000
Create Date: 2026-06-20 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260620_0900"
down_revision = "20260619_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collector_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("area", sa.String(180), nullable=True),
        sa.Column("assigned_collector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_collector_routes_collector_status", "collector_routes", ["assigned_collector_id", "status"])
    op.create_index("ix_collector_routes_name", "collector_routes", ["name"])
    op.create_index("ix_collector_routes_branch_id", "collector_routes", ["branch_id"])

    op.create_table(
        "field_collection_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("collector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collector_routes.id"), nullable=True),
        sa.Column("collection_date", sa.Date(), nullable=False),
        sa.Column("opening_cash", sa.Numeric(16, 2), nullable=False),
        sa.Column("expected_total", sa.Numeric(16, 2), nullable=False),
        sa.Column("collected_total", sa.Numeric(16, 2), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("denomination_close", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_field_collection_batches_branch_id", "field_collection_batches", ["branch_id"])
    op.create_index("ix_field_collection_batches_collector_id", "field_collection_batches", ["collector_id"])
    op.create_index("ix_field_collection_batches_route_id", "field_collection_batches", ["route_id"])
    op.create_index("ix_field_collection_batches_collection_date", "field_collection_batches", ["collection_date"])
    op.create_index("ix_field_collection_batches_collector_date", "field_collection_batches", ["collector_id", "collection_date"])
    op.create_index("ix_field_collection_batches_status_date", "field_collection_batches", ["status", "collection_date"])

    op.create_table(
        "field_collection_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("field_collection_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("savings_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("savings_accounts.id"), nullable=True),
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id"), nullable=True),
        sa.Column("loan_installment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loan_installments.id"), nullable=True),
        sa.Column("collection_type", sa.String(32), nullable=False),
        sa.Column("payment_method", sa.String(24), nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("share_units", sa.Integer(), nullable=True),
        sa.Column("share_rate", sa.Numeric(14, 2), nullable=True),
        sa.Column("fee_code", sa.String(60), nullable=True),
        sa.Column("receipt_no", sa.String(60), nullable=False),
        sa.Column("client_request_id", sa.String(80), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("gps_lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("gps_lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("device_id", sa.String(120), nullable=True),
        sa.Column("narration", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("posted_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("client_request_id", name="uq_field_collection_client_request"),
        sa.UniqueConstraint("receipt_no", name="uq_field_collection_receipt_no"),
    )
    op.create_index("ix_field_collection_entries_batch_id", "field_collection_entries", ["batch_id"])
    op.create_index("ix_field_collection_entries_member_id", "field_collection_entries", ["member_id"])
    op.create_index("ix_field_collection_entries_savings_account_id", "field_collection_entries", ["savings_account_id"])
    op.create_index("ix_field_collection_entries_loan_id", "field_collection_entries", ["loan_id"])
    op.create_index("ix_field_collection_entries_loan_installment_id", "field_collection_entries", ["loan_installment_id"])
    op.create_index("ix_field_collection_entries_collection_type", "field_collection_entries", ["collection_type"])
    op.create_index("ix_field_collection_entries_payment_method", "field_collection_entries", ["payment_method"])
    op.create_index("ix_field_collection_entries_fee_code", "field_collection_entries", ["fee_code"])
    op.create_index("ix_field_collection_entries_receipt_no", "field_collection_entries", ["receipt_no"])
    op.create_index("ix_field_collection_entries_client_request_id", "field_collection_entries", ["client_request_id"])
    op.create_index("ix_field_collection_entries_collected_at", "field_collection_entries", ["collected_at"])
    op.create_index("ix_field_collection_entries_posted_transaction_id", "field_collection_entries", ["posted_transaction_id"])
    op.create_index("ix_field_collection_entries_status", "field_collection_entries", ["status"])
    op.create_index("ix_field_collection_entries_batch_status", "field_collection_entries", ["batch_id", "status"])
    op.create_index("ix_field_collection_entries_member_date", "field_collection_entries", ["member_id", "collected_at"])


def downgrade() -> None:
    op.drop_table("field_collection_entries")
    op.drop_table("field_collection_batches")
    op.drop_table("collector_routes")
