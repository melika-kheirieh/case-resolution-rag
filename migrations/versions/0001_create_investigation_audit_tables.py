"""Create investigation audit tables.

Revision ID: 0001_create_investigation_audit_tables
Revises:
Create Date: 2026-07-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0001_create_investigation_audit_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investigation_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=128), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("recommended_action", sa.String(length=64), nullable=False),
        sa.Column("automation_decision", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("customer_response_allowed", sa.Boolean(), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("audit_reference", sa.Text(), nullable=False),
    )
    op.create_index("ix_investigation_runs_case_id", "investigation_runs", ["case_id"])
    op.create_index("ix_investigation_runs_created_at", "investigation_runs", ["created_at"])
    op.create_index("ix_investigation_runs_request_id", "investigation_runs", ["request_id"])
    op.create_index(
        "ix_investigation_runs_correlation_id",
        "investigation_runs",
        ["correlation_id"],
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("investigation_run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_run_id"],
            ["investigation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "investigation_run_id",
            "sequence_number",
            name="uq_audit_events_run_sequence",
        ),
    )
    op.create_index(
        "ix_audit_events_investigation_run_id",
        "audit_events",
        ["investigation_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_investigation_run_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_investigation_runs_correlation_id", table_name="investigation_runs")
    op.drop_index("ix_investigation_runs_request_id", table_name="investigation_runs")
    op.drop_index("ix_investigation_runs_created_at", table_name="investigation_runs")
    op.drop_index("ix_investigation_runs_case_id", table_name="investigation_runs")
    op.drop_table("investigation_runs")
