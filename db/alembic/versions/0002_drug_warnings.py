"""Add cosmos_run_id to encounters and drug_interaction_warnings table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-01
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── drug_interaction_warnings ─────────────────────────────────────────
    # Stores warnings from the Drug Interaction Agent (Agent 6) per encounter.
    op.create_table(
        "drug_interaction_warnings",
        sa.Column("warning_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.encounter_id", ondelete="CASCADE"), nullable=False),
        sa.Column("drugs", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("severity", sa.Text, nullable=False),          # "major"|"moderate"|"minor"|"unknown"
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acknowledged_by", sa.Text, sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_diw_encounter_id", "drug_interaction_warnings", ["encounter_id"])
    op.create_index("ix_diw_severity", "drug_interaction_warnings", ["severity"])


def downgrade() -> None:
    op.drop_table("drug_interaction_warnings")
