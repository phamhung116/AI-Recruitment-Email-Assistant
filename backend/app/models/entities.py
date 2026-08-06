from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class CandidateStatus(str, Enum):
    PENDING = "PENDING"
    PASS_CV = "PASS_CV"
    REJECT_CV = "REJECT_CV"
    INTERVIEW_CONFIRMED = "INTERVIEW_CONFIRMED"
    PASS_INTERVIEW = "PASS_INTERVIEW"
    REJECT_INTERVIEW = "REJECT_INTERVIEW"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"


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


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    position: Mapped[str | None] = mapped_column(String(255), index=True)
    stage: Mapped[str | None] = mapped_column(String(100), default="NEW", index=True)
    status: Mapped[str] = mapped_column(String(80), default=CandidateStatus.PENDING.value, index=True)
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_updated_by: Mapped[str | None] = mapped_column(String(255))
    interview_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interviewer: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    email_queue_items = relationship("EmailQueue", back_populates="candidate")
    email_history_items = relationship("EmailHistory", back_populates="candidate")


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate = relationship("Candidate", back_populates="email_queue_items")


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

    candidate = relationship("Candidate", back_populates="email_history_items")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    actor: Mapped[str | None] = mapped_column(String(255), default="demo_hr")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
