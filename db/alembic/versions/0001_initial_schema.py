"""Phase 4 initial schema — users, encounters, notes, codes, approvals, audit_log.

Revision ID: 0001
Revises: (none)
Create Date: 2026-06-01
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # ── Enum types ────────────────────────────────────────────────────────
    encounter_status = postgresql.ENUM(
        "pending", "transcribing", "drafting", "complete", "failed",
        name="encounter_status",
    )
    encounter_status.create(op.get_bind())

    approval_status = postgresql.ENUM(
        "pending_review", "approved", "rejected", "amended",
        name="approval_status",
    )
    approval_status.create(op.get_bind())

    # ── users ─────────────────────────────────────────────────────────────
    # Thin mirror of Clerk user data — no PII stored here beyond Clerk user ID.
    # Populated on first sign-in via a Clerk webhook (Phase 6).
    op.create_table(
        "users",
        sa.Column("user_id", sa.Text, primary_key=True),       # Clerk user_id (user_xxx)
        sa.Column("email", sa.Text, nullable=True),             # display only
        sa.Column("display_name", sa.Text, nullable=True),
        sa.Column("role", sa.Text, nullable=False, server_default="clinician"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── encounters ────────────────────────────────────────────────────────
    op.create_table(
        "encounters",
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, sa.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", sa.Text, nullable=False),
        sa.Column("status", sa.Enum("pending", "transcribing", "drafting", "complete", "failed", name="encounter_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("blob_name", sa.Text, nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("soap_draft", postgresql.JSONB, nullable=True),     # SOAPSection JSON
        sa.Column("soap_final", postgresql.JSONB, nullable=True),     # Post-critic JSON
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("cosmos_run_id", postgresql.UUID(as_uuid=True), nullable=True),  # FK into Cosmos agent_runs
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_encounters_user_id", "encounters", ["user_id"])
    op.create_index("ix_encounters_patient_id", "encounters", ["patient_id"])
    op.create_index("ix_encounters_status", "encounters", ["status"])
    op.create_index("ix_encounters_created_at", "encounters", ["created_at"])

    # ── notes ─────────────────────────────────────────────────────────────
    # Clinician free-text additions / amendments to the SOAP note.
    op.create_table(
        "notes",
        sa.Column("note_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.encounter_id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", sa.Text, sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("soap_section", sa.Text, nullable=False),   # "subjective"|"objective"|"assessment"|"plan"|"general"
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_amendment", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notes_encounter_id", "notes", ["encounter_id"])

    # ── codes ─────────────────────────────────────────────────────────────
    # ICD-10 and CPT codes suggested by the Coder agent and optionally confirmed.
    op.create_table(
        "codes",
        sa.Column("code_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.encounter_id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.Text, nullable=False),            # e.g. "J18.9" or "99213"
        sa.Column("code_type", sa.Text, nullable=False),       # "icd10" | "cpt"
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("confidence", sa.Text, nullable=True),       # "high"|"medium"|"low"
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confirmed_by", sa.Text, sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_codes_encounter_id", "codes", ["encounter_id"])
    op.create_index("ix_codes_code", "codes", ["code"])

    # ── approvals ─────────────────────────────────────────────────────────
    # Mandatory clinician sign-off on each encounter before finalisation.
    op.create_table(
        "approvals",
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.encounter_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("reviewer_user_id", sa.Text, sa.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.Enum("pending_review", "approved", "rejected", "amended", name="approval_status", create_type=False), nullable=False, server_default="pending_review"),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_approvals_encounter_id", "approvals", ["encounter_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])

    # ── audit_log ─────────────────────────────────────────────────────────
    # Append-only audit trail for compliance (HIPAA audit controls).
    # Never updated or deleted — rows are immutable after insert.
    op.create_table(
        "audit_log",
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_user_id", sa.Text, nullable=True),        # null for system actions
        sa.Column("action", sa.Text, nullable=False),              # "encounter.created", "approval.approved", etc.
        sa.Column("resource_type", sa.Text, nullable=False),       # "encounter"|"approval"|"code"|"note"
        sa.Column("resource_id", sa.Text, nullable=False),         # UUID as text
        sa.Column("payload", postgresql.JSONB, nullable=True),     # diff or context snapshot
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_log_resource", "audit_log", ["resource_type", "resource_id"])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor_user_id"])
    op.create_index("ix_audit_log_occurred_at", "audit_log", ["occurred_at"])

    # ── Trigger: updated_at auto-maintenance ──────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;
    """)
    for tbl in ("users", "encounters", "approvals"):
        op.execute(f"""
            CREATE TRIGGER trg_{tbl}_updated_at
            BEFORE UPDATE ON {tbl}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """)


def downgrade() -> None:
    for tbl in ("users", "encounters", "approvals"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_updated_at ON {tbl}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_table("audit_log")
    op.drop_table("approvals")
    op.drop_table("codes")
    op.drop_table("notes")
    op.drop_table("encounters")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS approval_status")
    op.execute("DROP TYPE IF EXISTS encounter_status")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
