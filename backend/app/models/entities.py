from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.db.database import Base


JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class RecruitmentStage(str, Enum):
    CV_SCREENING = "CV_SCREENING"
    INTERVIEW = "INTERVIEW"


class CandidateStatus(str, Enum):
    PENDING = "PENDING"
    PASS_CV = "PASS_CV"
    REJECT_CV = "REJECT_CV"
    PASS_INTERVIEW = "PASS_INTERVIEW"
    REJECT_INTERVIEW = "REJECT_INTERVIEW"

    # Compatibility-only values for the legacy workflow until SLICE-019.
    INTERVIEW_CONFIRMED = "INTERVIEW_CONFIRMED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"


class TemplateCode(str, Enum):
    INTERVIEW_INVITATION = "INTERVIEW_INVITATION"
    REJECTION_AFTER_CV = "REJECTION_AFTER_CV"
    OFFER_EMAIL = "OFFER_EMAIL"
    REJECTION_AFTER_INTERVIEW = "REJECTION_AFTER_INTERVIEW"
    DECISION_CORRECTION = "DECISION_CORRECTION"


class DraftStatus(str, Enum):
    DRAFT_PENDING_CHECK = "DRAFT_PENDING_CHECK"
    READY_TO_SEND = "READY_TO_SEND"
    BLOCKED_DETERMINISTIC = "BLOCKED_DETERMINISTIC"
    FROZEN_IN_FLIGHT = "FROZEN_IN_FLIGHT"
    SUPERSEDED = "SUPERSEDED"
    CORRECTION_DRAFT = "CORRECTION_DRAFT"
    DISCARDED = "DISCARDED"
    FINALIZED = "FINALIZED"


class OperationStatus(str, Enum):
    SENDING_UNCONFIRMED = "SENDING_UNCONFIRMED"
    PROVIDER_ACCEPTED = "PROVIDER_ACCEPTED"
    DEFINITIVE_FAILURE = "DEFINITIVE_FAILURE"
    DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"
    FAILED_TERMINAL = "FAILED_TERMINAL"


class FailureCategory(str, Enum):
    TRANSIENT_RETRYABLE = "TRANSIENT_RETRYABLE"
    VALIDATION_TERMINAL = "VALIDATION_TERMINAL"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


class ResolutionMode(str, Enum):
    AUTOMATIC_SYNC = "AUTOMATIC_SYNC"
    PROVIDER_IDEMPOTENT_REPLAY = "PROVIDER_IDEMPOTENT_REPLAY"
    HR_MANUAL_OVERRIDE = "HR_MANUAL_OVERRIDE"


class AttemptStatus(str, Enum):
    PREPARED = "PREPARED"
    IN_FLIGHT = "IN_FLIGHT"
    ACCEPTED = "ACCEPTED"
    DEFINITIVE_FAILURE = "DEFINITIVE_FAILURE"
    UNCONFIRMED_TIMEOUT = "UNCONFIRMED_TIMEOUT"
    ABORTED = "ABORTED"


class ActionOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    FAILURE = "FAILURE"
    UNCONFIRMED = "UNCONFIRMED"


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("application_id", name="candidates_uq_application_id"),
        CheckConstraint("length(trim(full_name)) >= 1", name="candidates_ck_name"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="candidates_ck_email",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "stage IN ('CV_SCREENING', 'INTERVIEW')", name="candidates_ck_stage"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'PASS_CV', 'REJECT_CV', 'PASS_INTERVIEW', 'REJECT_INTERVIEW')",
            name="candidates_ck_status",
        ),
        CheckConstraint(
            "communicated_decision IS NULL OR communicated_decision IN "
            "('PASS_CV', 'REJECT_CV', 'PASS_INTERVIEW', 'REJECT_INTERVIEW')",
            name="candidates_ck_communicated_decision",
        ),
        CheckConstraint(
            "communicated_stage IS NULL OR communicated_stage IN ('CV_SCREENING', 'INTERVIEW')",
            name="candidates_ck_communicated_stage",
        ),
        Index("idx_candidates_application_stage", "application_id", "stage"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    position: Mapped[str | None] = mapped_column(String(255))
    stage: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default=RecruitmentStage.CV_SCREENING.value,
        server_default=text("'CV_SCREENING'"),
    )
    status: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default=CandidateStatus.PENDING.value,
        server_default=text("'PENDING'"),
    )
    communicated_decision: Mapped[str | None] = mapped_column(String(80))
    communicated_stage: Mapped[str | None] = mapped_column(String(80))
    communicated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_updated_by: Mapped[str | None] = mapped_column(String(255))
    interview_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interviewer: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    draft_revisions: Mapped[list[DraftRevision]] = relationship(back_populates="candidate")
    email_queue_items: Mapped[list[EmailQueue]] = relationship(back_populates="candidate")
    email_history_items: Mapped[list[EmailHistory]] = relationship(back_populates="candidate")


class DraftRevision(Base):
    __tablename__ = "draft_revisions"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id", "revision_number", name="uq_draft_revisions_candidate_rev"
        ),
        CheckConstraint("revision_number >= 1", name="draft_revisions_ck_positive_number"),
        CheckConstraint(
            "template_code IN ('INTERVIEW_INVITATION', 'REJECTION_AFTER_CV', 'OFFER_EMAIL', "
            "'REJECTION_AFTER_INTERVIEW', 'DECISION_CORRECTION')",
            name="draft_revisions_ck_template_code",
        ),
        CheckConstraint(
            "stage IN ('CV_SCREENING', 'INTERVIEW')", name="draft_revisions_ck_stage"
        ),
        CheckConstraint(
            "decision IN ('PASS_CV', 'REJECT_CV', 'PASS_INTERVIEW', 'REJECT_INTERVIEW')",
            name="draft_revisions_ck_decision",
        ),
        CheckConstraint(
            "status IN ('DRAFT_PENDING_CHECK', 'READY_TO_SEND', 'BLOCKED_DETERMINISTIC', "
            "'FROZEN_IN_FLIGHT', 'SUPERSEDED', 'CORRECTION_DRAFT', 'DISCARDED', 'FINALIZED')",
            name="draft_revisions_ck_status",
        ),
        CheckConstraint(
            "is_correction = false OR (is_correction = true AND correction_rationale IS NOT NULL "
            "AND length(trim(correction_rationale)) >= 5)",
            name="draft_revisions_ck_correction_rationale",
        ),
        Index(
            "idx_draft_revisions_active",
            "candidate_id",
            "stage",
            postgresql_where=text(
                "status IN ('DRAFT_PENDING_CHECK', 'READY_TO_SEND', 'BLOCKED_DETERMINISTIC', "
                "'FROZEN_IN_FLIGHT', 'CORRECTION_DRAFT')"
            ),
            sqlite_where=text(
                "status IN ('DRAFT_PENDING_CHECK', 'READY_TO_SEND', 'BLOCKED_DETERMINISTIC', "
                "'FROZEN_IN_FLIGHT', 'CORRECTION_DRAFT')"
            ),
        ),
        Index("idx_draft_revisions_history", "candidate_id", text("revision_number DESC")),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    template_code: Mapped[str] = mapped_column(String(80), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    decision: Mapped[str] = mapped_column(String(80), nullable=False)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    decision_critical_content: Mapped[str] = mapped_column(Text, nullable=False)
    editable_content: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DraftStatus.DRAFT_PENDING_CHECK.value,
        server_default=text("'DRAFT_PENDING_CHECK'"),
    )
    is_correction: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    correction_rationale: Mapped[str | None] = mapped_column(Text)
    prior_operation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "logical_send_operations.id",
            name="fk_draft_revisions_prior_operation",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=True,
        )
    )
    risk_check_result: Mapped[dict] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_by: Mapped[str] = mapped_column(
        String(255), nullable=False, default="demo_hr", server_default=text("'demo_hr'")
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    candidate: Mapped[Candidate] = relationship(back_populates="draft_revisions")
    send_operation: Mapped[LogicalSendOperation | None] = relationship(
        back_populates="draft_revision",
        foreign_keys="LogicalSendOperation.draft_revision_id",
        uselist=False,
    )
    prior_operation: Mapped[LogicalSendOperation | None] = relationship(
        foreign_keys=[prior_operation_id]
    )


class LogicalSendOperation(Base):
    __tablename__ = "logical_send_operations"
    __table_args__ = (
        UniqueConstraint("draft_revision_id", name="logical_send_operations_uq_draft_rev"),
        CheckConstraint(
            "operation_status IN ('SENDING_UNCONFIRMED', 'PROVIDER_ACCEPTED', "
            "'DEFINITIVE_FAILURE', 'DELIVERY_UNKNOWN', 'FAILED_TERMINAL')",
            name="send_ops_ck_status",
        ),
        CheckConstraint(
            "final_outcome IS NULL OR final_outcome IN ('PROVIDER_ACCEPTED', "
            "'DEFINITIVE_FAILURE', 'DELIVERY_UNKNOWN', 'FAILED_TERMINAL')",
            name="send_ops_ck_final_outcome",
        ),
        CheckConstraint(
            "failure_category IS NULL OR failure_category IN "
            "('TRANSIENT_RETRYABLE', 'VALIDATION_TERMINAL', 'QUOTA_EXCEEDED')",
            name="send_ops_ck_failure_category",
        ),
        CheckConstraint(
            "resolution_mode IS NULL OR resolution_mode IN "
            "('AUTOMATIC_SYNC', 'PROVIDER_IDEMPOTENT_REPLAY', 'HR_MANUAL_OVERRIDE')",
            name="send_ops_ck_resolution_mode",
        ),
        Index(
            "idx_logical_send_operations_unfinalized",
            "operation_status",
            "created_at",
            postgresql_where=text("operation_status = 'SENDING_UNCONFIRMED'"),
            sqlite_where=text("operation_status = 'SENDING_UNCONFIRMED'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    draft_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("draft_revisions.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False
    )
    operation_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=OperationStatus.SENDING_UNCONFIRMED.value,
        server_default=text("'SENDING_UNCONFIRMED'"),
    )
    provider_name: Mapped[str] = mapped_column(
        String(50), nullable=False, default="RESEND", server_default=text("'RESEND'")
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    final_outcome: Mapped[str | None] = mapped_column(String(50))
    failure_category: Mapped[str | None] = mapped_column(String(50))
    resolution_mode: Mapped[str | None] = mapped_column(String(50))
    resolution_rationale: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(
        String(255), nullable=False, default="demo_hr", server_default=text("'demo_hr'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    draft_revision: Mapped[DraftRevision] = relationship(
        back_populates="send_operation", foreign_keys=[draft_revision_id]
    )
    attempts: Mapped[list[ProviderAttempt]] = relationship(back_populates="operation")


class ProviderAttempt(Base):
    __tablename__ = "provider_attempts"
    __table_args__ = (
        UniqueConstraint("operation_id", "attempt_number", name="uq_provider_attempts_op_attempt"),
        CheckConstraint("attempt_number >= 1", name="provider_attempts_ck_positive_number"),
        CheckConstraint(
            "attempt_status IN ('PREPARED', 'IN_FLIGHT', 'ACCEPTED', 'DEFINITIVE_FAILURE', "
            "'UNCONFIRMED_TIMEOUT', 'ABORTED')",
            name="provider_attempts_ck_status",
        ),
        Index("idx_provider_attempts_operation_attempt", "operation_id", "attempt_number"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("logical_send_operations.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    request_payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AttemptStatus.PREPARED.value,
        server_default=text("'PREPARED'"),
    )
    http_status_code: Mapped[int | None] = mapped_column(Integer)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    operation: Mapped[LogicalSendOperation] = relationship(back_populates="attempts")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("length(trim(event_name)) >= 3", name="audit_logs_ck_event_name"),
        CheckConstraint(
            "action_outcome IN ('SUCCESS', 'BLOCKED', 'FAILURE', 'UNCONFIRMED')",
            name="audit_logs_ck_action_outcome",
        ),
        Index("idx_audit_logs_application_created", "application_id", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), Identity(always=True), primary_key=True
    )
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    application_id: Mapped[str | None] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(
        String(255), nullable=False, default="demo_hr", server_default=text("'demo_hr'")
    )
    action_outcome: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ActionOutcome.SUCCESS.value
    )
    payload_json: Mapped[dict] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    action = synonym("event_name")
    metadata_json = synonym("payload_json")


# Compatibility-only persistence models retained until SLICE-019. They are
# excluded from the five-table target migration created in SLICE-004.
class EmailType(str, Enum):
    APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
    INTERVIEW_INVITATION = "INTERVIEW_INVITATION"
    INTERVIEW_REMINDER = "INTERVIEW_REMINDER"
    REJECTION_AFTER_CV = "REJECTION_AFTER_CV"
    REJECTION_AFTER_INTERVIEW = "REJECTION_AFTER_INTERVIEW"
    OFFER_EMAIL = "OFFER_EMAIL"
    ONBOARDING_EMAIL = "ONBOARDING_EMAIL"
    RESCHEDULE_RESPONSE = "RESCHEDULE_RESPONSE"
    NEXT_ROUND_EMAIL = "NEXT_ROUND_EMAIL"


class QueueStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    required_placeholders: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmailQueue(Base):
    __tablename__ = "email_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    email_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=QueueStatus.DRAFT.value, index=True)
    requires_hr_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_check_result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(255), default="demo_hr")
    approved_by: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    candidate: Mapped[Candidate] = relationship(back_populates="email_queue_items")


class EmailHistory(Base):
    __tablename__ = "email_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    email_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_by: Mapped[str | None] = mapped_column(String(255), default="demo_hr")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped[Candidate] = relationship(back_populates="email_history_items")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default=OutboxStatus.PENDING.value, nullable=False, index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
