from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CandidateBase(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    position: str | None = None
    stage: str | None = "NEW"
    status: str = "PENDING"
    interview_time: datetime | None = None
    interviewer: str | None = None
    note: str | None = None


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    position: str | None = None
    stage: str | None = None
    status: str | None = None
    interview_time: datetime | None = None
    interviewer: str | None = None
    note: str | None = None


class CandidateRead(CandidateBase):
    id: int
    status_updated_at: datetime | None = None
    status_updated_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateListResponse(BaseModel):
    items: list[CandidateRead]
    total: int
    page: int
    page_size: int
    pages: int


class CandidateStatusUpdate(BaseModel):
    status: str
    actor: str = "demo_hr"


class BulkCandidateStatusUpdate(BaseModel):
    candidate_ids: list[int] = Field(min_length=1)
    status: str
    actor: str = "demo_hr"


class BulkCandidateDelete(BaseModel):
    candidate_ids: list[int] = Field(min_length=1)
    actor: str = "demo_hr"


class BulkActionResult(BaseModel):
    affected: int


class CandidateFilterOptions(BaseModel):
    positions: list[str]
    stages: list[str]
    statuses: list[str]


class EmailTemplateBase(BaseModel):
    name: str
    email_type: str
    subject: str
    body: str
    required_placeholders: list[str] = Field(default_factory=list)
    is_sensitive: bool = False


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    email_type: str | None = None
    subject: str | None = None
    body: str | None = None
    required_placeholders: list[str] | None = None
    is_sensitive: bool | None = None


class EmailTemplateRead(EmailTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerateEmailDraftRequest(BaseModel):
    candidate_id: int
    email_type: str | None = None
    created_by: str = "demo_hr"


class EmailQueueUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None

    model_config = ConfigDict(extra="forbid")


class EmailQueueRead(BaseModel):
    id: int
    candidate_id: int
    email_type: str
    to_email: str
    subject: str
    body: str
    status: str
    requires_hr_approval: bool
    risk_check_result: dict[str, Any]
    created_by: str | None
    approved_by: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
    candidate: CandidateRead | None = None

    model_config = ConfigDict(from_attributes=True)


class EmailHistoryRead(BaseModel):
    id: int
    candidate_id: int
    email_type: str
    to_email: str
    subject: str
    body: str
    sent_by: str | None
    sent_at: datetime
    candidate: CandidateRead | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogRead(BaseModel):
    id: int
    action: str
    entity_type: str | None
    entity_id: int | None
    actor: str | None
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    total_candidates: int
    pending_emails: int
    sent_emails: int
    failed_emails: int


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class ImportPreviewRow(BaseModel):
    row_number: int
    is_valid: bool
    reason: str | None = None
    candidate: dict[str, Any]


class ImportPreviewResult(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[ImportPreviewRow]


class ApiErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    request_id: UUID


class CandidateV1Read(BaseModel):
    id: int
    application_id: str
    full_name: str
    email: str
    phone: str | None
    position: str | None
    stage: str
    status: str
    communicated_decision: str | None
    communicated_stage: str | None
    communicated_at: datetime | None
    status_updated_at: datetime | None
    status_updated_by: str | None
    interview_time: datetime | None
    interviewer: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateV1ListResponse(BaseModel):
    items: list[CandidateV1Read]
    total: int
    page: int
    page_size: int
    pages: int


class DraftCreateRequest(BaseModel):
    application_id: str = Field(min_length=1, max_length=64)
    actor: str = Field(default="demo_hr", min_length=1, max_length=255)


class DraftReviseRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=500)
    editable_content: str | None = None
    actor: str = Field(default="demo_hr", min_length=1, max_length=255)


class CorrectionDraftRequest(BaseModel):
    new_decision: str
    rationale: str = Field(min_length=5)
    actor: str = Field(default="demo_hr", min_length=1, max_length=255)


class DraftRevisionRead(BaseModel):
    id: UUID
    candidate_id: int
    revision_number: int
    template_code: str
    stage: str
    decision: str
    to_email: str
    subject: str
    decision_critical_content: str
    editable_content: str
    rendered_body: str
    status: str
    is_correction: bool
    correction_rationale: str | None
    prior_operation_id: UUID | None
    risk_check_result: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DraftRevisionListResponse(BaseModel):
    items: list[DraftRevisionRead]
    total: int
    page: int
    page_size: int
    pages: int


class SendConfirmationRequest(BaseModel):
    actor: str = Field(default="demo_hr", min_length=1, max_length=255)
    confirmation_acknowledged: bool


class DeliveryResolutionRequest(BaseModel):
    resolution: str
    rationale: str = Field(min_length=5)
    actor: str = Field(min_length=1, max_length=255)
    warning_acknowledged: bool


class ProviderAttemptRead(BaseModel):
    id: UUID
    attempt_number: int
    attempt_status: str
    http_status_code: int | None
    provider_message_id: str | None
    error_code: str | None
    error_message: str | None
    latency_ms: int | None
    initiated_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SendOperationRead(BaseModel):
    id: UUID
    draft_revision_id: UUID
    operation_status: str
    provider_name: str
    provider_message_id: str | None
    final_outcome: str | None
    failure_category: str | None
    resolution_mode: str | None
    resolution_rationale: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    attempts: list[ProviderAttemptRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SendOperationListResponse(BaseModel):
    items: list[SendOperationRead]
    total: int
    page: int
    page_size: int
    pages: int


class AuditLogV1Read(BaseModel):
    id: int
    event_name: str
    entity_type: str
    entity_id: str
    application_id: str | None
    actor: str
    action_outcome: str
    payload_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogV1ListResponse(BaseModel):
    items: list[AuditLogV1Read]
    total: int
    page: int
    page_size: int
    pages: int
