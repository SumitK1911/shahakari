"""add member person onboarding fields

Revision ID: 20260606_1545
Revises:
Create Date: 2026-06-06 15:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260606_1545"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("members", sa.Column("name_nepali", sa.String(length=180), nullable=True))
    op.add_column("members", sa.Column("dob_bs", sa.String(length=16), nullable=True))
    op.add_column("members", sa.Column("marital_status", sa.String(length=32), nullable=True))
    op.add_column("members", sa.Column("nationality", sa.String(length=80), nullable=False, server_default="Nepali"))
    op.add_column("members", sa.Column("secondary_phone", sa.String(length=40), nullable=True))
    op.add_column("members", sa.Column("email", sa.String(length=180), nullable=True))
    op.add_column("members", sa.Column("emergency_contact_name", sa.String(length=180), nullable=True))
    op.add_column("members", sa.Column("emergency_contact_number", sa.String(length=40), nullable=True))
    op.add_column("members", sa.Column("address_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("members", sa.Column("documents", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("members", sa.Column("family_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("members", sa.Column("guardian_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("members", sa.Column("occupation_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("members", sa.Column("income_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("members", sa.Column("membership_type", sa.String(length=80), nullable=True))
    op.add_column("members", sa.Column("join_date", sa.Date(), nullable=True))
    op.add_column("members", sa.Column("risk_category", sa.String(length=24), nullable=False, server_default="low"))
    op.add_column("members", sa.Column("is_pep", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("members", sa.Column("is_blacklisted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("members", sa.Column("internal_notes", sa.Text(), nullable=True))
    op.add_column("members", sa.Column("media_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("member_nominees", sa.Column("citizenship_number", sa.String(length=80), nullable=True))
    op.create_index(op.f("ix_members_risk_category"), "members", ["risk_category"], unique=False)
    op.create_index(op.f("ix_members_is_pep"), "members", ["is_pep"], unique=False)
    op.create_index(op.f("ix_members_is_blacklisted"), "members", ["is_blacklisted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_members_is_blacklisted"), table_name="members")
    op.drop_index(op.f("ix_members_is_pep"), table_name="members")
    op.drop_index(op.f("ix_members_risk_category"), table_name="members")
    op.drop_column("member_nominees", "citizenship_number")
    op.drop_column("members", "media_profile")
    op.drop_column("members", "internal_notes")
    op.drop_column("members", "is_blacklisted")
    op.drop_column("members", "is_pep")
    op.drop_column("members", "risk_category")
    op.drop_column("members", "join_date")
    op.drop_column("members", "membership_type")
    op.drop_column("members", "income_sources")
    op.drop_column("members", "occupation_profile")
    op.drop_column("members", "guardian_profile")
    op.drop_column("members", "family_profile")
    op.drop_column("members", "documents")
    op.drop_column("members", "address_profile")
    op.drop_column("members", "emergency_contact_number")
    op.drop_column("members", "emergency_contact_name")
    op.drop_column("members", "email")
    op.drop_column("members", "secondary_phone")
    op.drop_column("members", "nationality")
    op.drop_column("members", "marital_status")
    op.drop_column("members", "dob_bs")
    op.drop_column("members", "name_nepali")
