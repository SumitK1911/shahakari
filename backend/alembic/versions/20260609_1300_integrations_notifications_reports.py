"""add integrations notifications and report runs

Revision ID: 20260609_1300
Revises: 20260609_1200
Create Date: 2026-06-09 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260609_1300"
down_revision = "20260609_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("integration_type", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("connection_uri", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_integration_endpoints_code"),
    )
    op.create_index(op.f("ix_integration_endpoints_code"), "integration_endpoints", ["code"], unique=False)
    op.create_index(op.f("ix_integration_endpoints_integration_type"), "integration_endpoints", ["integration_type"], unique=False)
    op.create_index(op.f("ix_integration_endpoints_status"), "integration_endpoints", ["status"], unique=False)

    op.create_table(
        "notification_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("recipient", sa.String(length=180), nullable=False),
        sa.Column("subject", sa.String(length=180), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("template_code", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider_message_id", sa.String(length=160), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_status_channel", "notification_messages", ["status", "channel"], unique=False)
    op.create_index("ix_notification_recipient", "notification_messages", ["recipient", "created_at"], unique=False)
    op.create_index(op.f("ix_notification_messages_channel"), "notification_messages", ["channel"], unique=False)
    op.create_index(op.f("ix_notification_messages_status"), "notification_messages", ["status"], unique=False)
    op.create_index(op.f("ix_notification_messages_template_code"), "notification_messages", ["template_code"], unique=False)
    op.create_index(op.f("ix_notification_messages_scheduled_for"), "notification_messages", ["scheduled_for"], unique=False)
    op.create_index(op.f("ix_notification_messages_sent_at"), "notification_messages", ["sent_at"], unique=False)

    op.create_table(
        "report_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(length=60), nullable=False),
        sa.Column("period_code", sa.String(length=40), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_runs_type_period", "report_runs", ["report_type", "period_code"], unique=False)
    op.create_index("ix_report_runs_status_created", "report_runs", ["status", "created_at"], unique=False)
    op.create_index(op.f("ix_report_runs_generated_by"), "report_runs", ["generated_by"], unique=False)
    op.create_index(op.f("ix_report_runs_report_type"), "report_runs", ["report_type"], unique=False)
    op.create_index(op.f("ix_report_runs_period_code"), "report_runs", ["period_code"], unique=False)
    op.create_index(op.f("ix_report_runs_status"), "report_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_runs_status"), table_name="report_runs")
    op.drop_index(op.f("ix_report_runs_period_code"), table_name="report_runs")
    op.drop_index(op.f("ix_report_runs_report_type"), table_name="report_runs")
    op.drop_index(op.f("ix_report_runs_generated_by"), table_name="report_runs")
    op.drop_index("ix_report_runs_status_created", table_name="report_runs")
    op.drop_index("ix_report_runs_type_period", table_name="report_runs")
    op.drop_table("report_runs")
    op.drop_index(op.f("ix_notification_messages_sent_at"), table_name="notification_messages")
    op.drop_index(op.f("ix_notification_messages_scheduled_for"), table_name="notification_messages")
    op.drop_index(op.f("ix_notification_messages_template_code"), table_name="notification_messages")
    op.drop_index(op.f("ix_notification_messages_status"), table_name="notification_messages")
    op.drop_index(op.f("ix_notification_messages_channel"), table_name="notification_messages")
    op.drop_index("ix_notification_recipient", table_name="notification_messages")
    op.drop_index("ix_notification_status_channel", table_name="notification_messages")
    op.drop_table("notification_messages")
    op.drop_index(op.f("ix_integration_endpoints_status"), table_name="integration_endpoints")
    op.drop_index(op.f("ix_integration_endpoints_integration_type"), table_name="integration_endpoints")
    op.drop_index(op.f("ix_integration_endpoints_code"), table_name="integration_endpoints")
    op.drop_table("integration_endpoints")
