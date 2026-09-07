"""add term deposits and share operation support

Revision ID: 20260609_1200
Revises: 20260606_1545
Create Date: 2026-06-09 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260609_1200"
down_revision = "20260606_1545"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "term_deposits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deposit_no", sa.String(length=40), nullable=False),
        sa.Column("deposit_type", sa.String(length=16), nullable=False),
        sa.Column("principal_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("installment_amount", sa.Numeric(16, 2), nullable=True),
        sa.Column("interest_rate", sa.Numeric(7, 4), nullable=False),
        sa.Column("opened_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=False),
        sa.Column("maturity_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("balance", sa.Numeric(16, 2), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deposit_no", name="uq_term_deposits_deposit_no"),
    )
    op.create_index("ix_term_deposits_member_status", "term_deposits", ["member_id", "status"], unique=False)
    op.create_index("ix_term_deposits_maturity_status", "term_deposits", ["maturity_date", "status"], unique=False)
    op.create_index(op.f("ix_term_deposits_deposit_no"), "term_deposits", ["deposit_no"], unique=False)
    op.create_index(op.f("ix_term_deposits_deposit_type"), "term_deposits", ["deposit_type"], unique=False)
    op.create_index(op.f("ix_term_deposits_opened_date"), "term_deposits", ["opened_date"], unique=False)

    op.create_table(
        "term_deposit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deposit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trans_type", sa.String(length=24), nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("balance", sa.Numeric(16, 2), nullable=False),
        sa.Column("trans_date", sa.Date(), nullable=False),
        sa.Column("narration", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["deposit_id"], ["term_deposits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_term_deposit_tx_deposit_date", "term_deposit_transactions", ["deposit_id", "trans_date"], unique=False)
    op.create_index(op.f("ix_term_deposit_transactions_deposit_id"), "term_deposit_transactions", ["deposit_id"], unique=False)
    op.create_index(op.f("ix_term_deposit_transactions_trans_date"), "term_deposit_transactions", ["trans_date"], unique=False)
    op.create_index(op.f("ix_term_deposit_transactions_trans_type"), "term_deposit_transactions", ["trans_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_term_deposit_transactions_trans_type"), table_name="term_deposit_transactions")
    op.drop_index(op.f("ix_term_deposit_transactions_trans_date"), table_name="term_deposit_transactions")
    op.drop_index(op.f("ix_term_deposit_transactions_deposit_id"), table_name="term_deposit_transactions")
    op.drop_index("ix_term_deposit_tx_deposit_date", table_name="term_deposit_transactions")
    op.drop_table("term_deposit_transactions")
    op.drop_index(op.f("ix_term_deposits_opened_date"), table_name="term_deposits")
    op.drop_index(op.f("ix_term_deposits_deposit_type"), table_name="term_deposits")
    op.drop_index(op.f("ix_term_deposits_deposit_no"), table_name="term_deposits")
    op.drop_index("ix_term_deposits_maturity_status", table_name="term_deposits")
    op.drop_index("ix_term_deposits_member_status", table_name="term_deposits")
    op.drop_table("term_deposits")
