from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"


class IssueSource(str, Enum):
    DETERMINISTIC = "deterministic"
    AGENT = "agent"


class ValidationIssue(BaseModel):
    rule_id: str
    severity: IssueSeverity
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    remediation: str
    is_blocking: bool
    source: IssueSource = IssueSource.DETERMINISTIC


class ValidationResult(BaseModel):
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_issues(cls, issues: list[ValidationIssue]) -> "ValidationResult":
        return cls(
            passed=not any(issue.is_blocking for issue in issues),
            issues=issues,
        )
