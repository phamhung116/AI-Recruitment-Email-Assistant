from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.validation import IssueSeverity, ValidationResult


class AgentReviewStatus(str, Enum):
    COMPLETED = "completed"
    DETERMINISTIC_BLOCKED = "deterministic_blocked"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


class AgentCandidateFacts(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    position: str | None = Field(default=None, max_length=255)
    status: str = Field(min_length=1, max_length=80)
    interview_time: str | None = Field(default=None, max_length=100)
    interviewer: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class AgentTemplateInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email_type: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=10_000)
    is_sensitive: bool

    model_config = ConfigDict(extra="forbid")


class AgentDraftInput(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=10_000)

    model_config = ConfigDict(extra="forbid")


class AgentReviewRequest(BaseModel):
    candidate: AgentCandidateFacts
    email_type: str = Field(min_length=1, max_length=80)
    template: AgentTemplateInput
    draft: AgentDraftInput
    deterministic_validation: ValidationResult
    company_policy: list[str] = Field(default_factory=list, max_length=20)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_email_type_alignment(self) -> "AgentReviewRequest":
        if self.email_type != self.template.email_type:
            raise ValueError("Request email_type must match template.email_type.")
        if any(len(policy) > 500 for policy in self.company_policy):
            raise ValueError("Each company policy must be at most 500 characters.")
        return self


class ReviewQueuedDraftRequest(BaseModel):
    queue_id: int = Field(gt=0)
    actor: str = Field(default="demo_hr", min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")


class AgentSemanticIssue(BaseModel):
    rule_id: str = Field(pattern=r"^AI_[A-Z0-9_]+$", max_length=100)
    severity: IssueSeverity
    message: str = Field(min_length=1, max_length=500)
    evidence: str = Field(min_length=1, max_length=1_000)
    requires_human_review: bool

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_review_for_material_issue(self) -> "AgentSemanticIssue":
        if self.severity in {IssueSeverity.WARNING, IssueSeverity.ERROR, IssueSeverity.BLOCKER}:
            if not self.requires_human_review:
                raise ValueError("Material semantic issues must require human review.")
        return self


class AgentUncertainty(BaseModel):
    has_uncertainty: bool
    reason: str | None = Field(default=None, max_length=1_000)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_uncertainty_reason(self) -> "AgentUncertainty":
        if self.has_uncertainty and not (self.reason and self.reason.strip()):
            raise ValueError("Uncertainty requires a reason.")
        if not self.has_uncertainty:
            self.reason = None
        return self


class AgentModelOutput(BaseModel):
    draft_subject: str = Field(min_length=1, max_length=500)
    draft_body: str = Field(min_length=1, max_length=10_000)
    issues: list[AgentSemanticIssue] = Field(default_factory=list, max_length=20)
    uncertainty: AgentUncertainty
    review_summary: str = Field(min_length=1, max_length=1_000)

    model_config = ConfigDict(extra="forbid")


class AgentModelMetadata(BaseModel):
    provider: str
    model: str
    prompt_version: str
    skill_name: str
    skill_version: str
    attempts: int = Field(ge=0, le=3)

    model_config = ConfigDict(extra="forbid")


class AgentTraceStep(BaseModel):
    step: str
    status: str
    detail: str

    model_config = ConfigDict(extra="forbid")


class AgentReviewResult(BaseModel):
    status: AgentReviewStatus
    draft_subject: str
    draft_body: str
    issues: list[AgentSemanticIssue] = Field(default_factory=list)
    uncertainty: AgentUncertainty
    review_summary: str
    requires_human_review: bool
    semantic_review_available: bool
    model_metadata: AgentModelMetadata
    trace: list[AgentTraceStep] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


def pydantic_error_summary(errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Reduce validation errors to bounded, non-sensitive correction feedback."""
    return [
        {
            "path": ".".join(str(part) for part in error.get("loc", ())),
            "type": str(error.get("type", "validation_error")),
        }
        for error in errors[:20]
    ]
