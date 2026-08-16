"""Create the five-table Recruitment Mail Guard core schema.

Revision ID: 001_initial_core_schema
Revises: None
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "001_initial_core_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TARGET_TABLE_NAMES = (
    "candidates",
    "draft_revisions",
    "logical_send_operations",
    "provider_attempts",
    "audit_logs",
)


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("position", sa.String(length=255), nullable=True),
        sa.Column("stage", sa.String(length=80), server_default="CV_SCREENING", nullable=False),
        sa.Column("status", sa.String(length=80), server_default="PENDING", nullable=False),
        sa.Column("communicated_decision", sa.String(length=80), nullable=True),
        sa.Column("communicated_stage", sa.String(length=80), nullable=True),
        sa.Column("communicated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_updated_by", sa.String(length=255), nullable=True),
        sa.Column("interview_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interviewer", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(full_name)) >= 1", name="candidates_ck_name"),
        sa.CheckConstraint(
            r"email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'",
            name="candidates_ck_email",
        ),
        sa.CheckConstraint(
            "stage IN ('CV_SCREENING', 'INTERVIEW')", name="candidates_ck_stage"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PASS_CV', 'REJECT_CV', 'PASS_INTERVIEW', 'REJECT_INTERVIEW')",
            name="candidates_ck_status",
        ),
        sa.CheckConstraint(
            "communicated_decision IS NULL OR communicated_decision IN "
            "('PASS_CV', 'REJECT_CV', 'PASS_INTERVIEW', 'REJECT_INTERVIEW')",
            name="candidates_ck_communicated_decision",
        ),
        sa.CheckConstraint(
            "communicated_stage IS NULL OR communicated_stage IN ('CV_SCREENING', 'INTERVIEW')",
            name="candidates_ck_communicated_stage",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="candidates_uq_application_id"),
    )
    op.create_index(
        "idx_candidates_application_stage",
        "candidates",
        ["application_id", "stage"],
    )

    op.create_table(
        "draft_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("template_code", sa.String(length=80), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("decision", sa.String(length=80), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("decision_critical_content", sa.Text(), nullable=False),
        sa.Column("editable_content", sa.Text(), nullable=False),
        sa.Column("rendered_body", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), server_default="DRAFT_PENDING_CHECK", nullable=False
        ),
        sa.Column("is_correction", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("correction_rationale", sa.Text(), nullable=True),
        sa.Column("prior_operation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "risk_check_result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=255), server_default="demo_hr", nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("revision_number >= 1", name="draft_revisions_ck_positive_number"),
        sa.CheckConstraint(
            "template_code IN ('INTERVIEW_INVITATION', 'REJECTION_AFTER_CV', 'OFFER_EMAIL', "
            "'REJECTION_AFTER_INTERVIEW', 'DECISION_CORRECTION')",
            name="draft_revisions_ck_template_code",
        ),
        sa.CheckConstraint(
            "stage IN ('CV_SCREENING', 'INTERVIEW')", name="draft_revisions_ck_stage"
        ),
        sa.CheckConstraint(
            "decision IN ('PASS_CV', 'REJECT_CV', 'PASS_INTERVIEW', 'REJECT_INTERVIEW')",
            name="draft_revisions_ck_decision",
        ),
        sa.CheckConstraint(
            r"to_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'",
            name="draft_revisions_ck_to_email",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT_PENDING_CHECK', 'READY_TO_SEND', 'BLOCKED_DETERMINISTIC', "
            "'FROZEN_IN_FLIGHT', 'SUPERSEDED', 'CORRECTION_DRAFT', 'DISCARDED', 'FINALIZED')",
            name="draft_revisions_ck_status",
        ),
        sa.CheckConstraint(
            "is_correction = false OR (is_correction = true AND correction_rationale IS NOT NULL "
            "AND length(trim(correction_rationale)) >= 5)",
            name="draft_revisions_ck_correction_rationale",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_draft_revisions_candidate",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id", "revision_number", name="uq_draft_revisions_candidate_rev"
        ),
    )
    active_draft_predicate = sa.text(
        "status IN ('DRAFT_PENDING_CHECK', 'READY_TO_SEND', 'BLOCKED_DETERMINISTIC', "
        "'FROZEN_IN_FLIGHT', 'CORRECTION_DRAFT')"
    )
    op.create_index(
        "idx_draft_revisions_active",
        "draft_revisions",
        ["candidate_id", "stage"],
        postgresql_where=active_draft_predicate,
    )
    op.create_index(
        "idx_draft_revisions_history",
        "draft_revisions",
        ["candidate_id", sa.text("revision_number DESC")],
    )

    op.create_table(
        "logical_send_operations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("draft_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "operation_status",
            sa.String(length=50),
            server_default="SENDING_UNCONFIRMED",
            nullable=False,
        ),
        sa.Column("provider_name", sa.String(length=50), server_default="RESEND", nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("final_outcome", sa.String(length=50), nullable=True),
        sa.Column("failure_category", sa.String(length=50), nullable=True),
        sa.Column("resolution_mode", sa.String(length=50), nullable=True),
        sa.Column("resolution_rationale", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), server_default="demo_hr", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "operation_status IN ('SENDING_UNCONFIRMED', 'PROVIDER_ACCEPTED', "
            "'DEFINITIVE_FAILURE', 'DELIVERY_UNKNOWN', 'FAILED_TERMINAL')",
            name="send_ops_ck_status",
        ),
        sa.CheckConstraint(
            "final_outcome IS NULL OR final_outcome IN ('PROVIDER_ACCEPTED', "
            "'DEFINITIVE_FAILURE', 'DELIVERY_UNKNOWN', 'FAILED_TERMINAL')",
            name="send_ops_ck_final_outcome",
        ),
        sa.CheckConstraint(
            "failure_category IS NULL OR failure_category IN "
            "('TRANSIENT_RETRYABLE', 'VALIDATION_TERMINAL', 'QUOTA_EXCEEDED')",
            name="send_ops_ck_failure_category",
        ),
        sa.CheckConstraint(
            "resolution_mode IS NULL OR resolution_mode IN "
            "('AUTOMATIC_SYNC', 'PROVIDER_IDEMPOTENT_REPLAY', 'HR_MANUAL_OVERRIDE')",
            name="send_ops_ck_resolution_mode",
        ),
        sa.ForeignKeyConstraint(
            ["draft_revision_id"],
            ["draft_revisions.id"],
            name="fk_logical_send_operations_draft",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "draft_revision_id", name="logical_send_operations_uq_draft_rev"
        ),
    )
    op.create_index(
        "idx_logical_send_operations_unfinalized",
        "logical_send_operations",
        ["operation_status", "created_at"],
        postgresql_where=sa.text("operation_status = 'SENDING_UNCONFIRMED'"),
    )
    op.create_foreign_key(
        "fk_draft_revisions_prior_operation",
        "draft_revisions",
        "logical_send_operations",
        ["prior_operation_id"],
        ["id"],
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )

    op.create_table(
        "provider_attempts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("request_payload_digest", sa.String(length=64), nullable=False),
        sa.Column("attempt_status", sa.String(length=50), server_default="PREPARED", nullable=False),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_number >= 1", name="provider_attempts_ck_positive_number"),
        sa.CheckConstraint(
            "attempt_status IN ('PREPARED', 'IN_FLIGHT', 'ACCEPTED', 'DEFINITIVE_FAILURE', "
            "'UNCONFIRMED_TIMEOUT', 'ABORTED')",
            name="provider_attempts_ck_status",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["logical_send_operations.id"],
            name="fk_provider_attempts_operation",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "operation_id", "attempt_number", name="uq_provider_attempts_op_attempt"
        ),
    )
    op.create_index(
        "idx_provider_attempts_operation_attempt",
        "provider_attempts",
        ["operation_id", "attempt_number"],
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("event_name", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=True),
        sa.Column("actor", sa.String(length=255), server_default="demo_hr", nullable=False),
        sa.Column("action_outcome", sa.String(length=50), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(event_name)) >= 3", name="audit_logs_ck_event_name"),
        sa.CheckConstraint(
            "action_outcome IN ('SUCCESS', 'BLOCKED', 'FAILURE', 'UNCONFIRMED')",
            name="audit_logs_ck_action_outcome",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_audit_logs_application_created",
        "audit_logs",
        ["application_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_audit_logs_application_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("idx_provider_attempts_operation_attempt", table_name="provider_attempts")
    op.drop_table("provider_attempts")
    op.drop_constraint(
        "fk_draft_revisions_prior_operation", "draft_revisions", type_="foreignkey"
    )
    op.drop_index(
        "idx_logical_send_operations_unfinalized",
        table_name="logical_send_operations",
    )
    op.drop_table("logical_send_operations")
    op.drop_index("idx_draft_revisions_history", table_name="draft_revisions")
    op.drop_index("idx_draft_revisions_active", table_name="draft_revisions")
    op.drop_table("draft_revisions")
    op.drop_index("idx_candidates_application_stage", table_name="candidates")
    op.drop_table("candidates")
