from datetime import datetime
from typing import Any

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
    status: str | None = None


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
