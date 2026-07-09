"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


approval_status = sa.Enum(
    "pending", "approved", "rejected", "cancelled", name="approvalstatus"
)
source_type = sa.Enum("publication", "scenario", "edit", "external", name="sourcetype")


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reviewer_user_ids", sa.JSON(), nullable=False),
        sa.Column("status", approval_status, nullable=False, server_default="pending"),
        sa.Column("created_by_user_id", sa.String(64), nullable=False),
        sa.Column("decided_by_user_id", sa.String(64), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_approval_requests_workspace_status",
        "approval_requests",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_approval_requests_workspace_id", "approval_requests", ["workspace_id"]
    )

    op.create_table(
        "audit_log_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column(
            "approval_request_id",
            sa.String(36),
            sa.ForeignKey("approval_requests.id"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_audit_log_entries_workspace_id", "audit_log_entries", ["workspace_id"]
    )
    op.create_index(
        "ix_audit_log_entries_approval_request_id",
        "audit_log_entries",
        ["approval_request_id"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_outbox_events_workspace_id", "outbox_events", ["workspace_id"])
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("endpoint", sa.String(64), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_idempotency_workspace_key_endpoint",
        "idempotency_records",
        ["workspace_id", "idempotency_key", "endpoint"],
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_table("outbox_events")
    op.drop_table("audit_log_entries")
    op.drop_index("ix_approval_requests_workspace_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_workspace_id", table_name="approval_requests")
    op.drop_table("approval_requests")
    approval_status.drop(op.get_bind(), checkfirst=True)
    source_type.drop(op.get_bind(), checkfirst=True)
