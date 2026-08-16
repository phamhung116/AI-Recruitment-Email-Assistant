"""Immutable, pre-seeded email templates for the approved MVP journey."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping


INTERVIEW_INVITATION: Final = "INTERVIEW_INVITATION"
REJECTION_AFTER_CV: Final = "REJECTION_AFTER_CV"
OFFER_EMAIL: Final = "OFFER_EMAIL"
REJECTION_AFTER_INTERVIEW: Final = "REJECTION_AFTER_INTERVIEW"
DECISION_CORRECTION: Final = "DECISION_CORRECTION"
DECISION_CRITICAL_MARKER: Final = "{{decision_critical_content}}"


@dataclass(frozen=True, slots=True)
class FixedTemplate:
    code: str
    subject_template: str
    decision_critical_template: str
    editable_template: str


DEFAULT_EDITABLE_TEMPLATE: Final = """Dear {{candidate_name}},

{{decision_critical_content}}

Please contact our recruitment team if you need any clarification.

Kind regards,
Recruitment Team"""


FIXED_TEMPLATE_CATALOG: Mapping[str, FixedTemplate] = MappingProxyType(
    {
        INTERVIEW_INVITATION: FixedTemplate(
            code=INTERVIEW_INVITATION,
            subject_template="Interview invitation — Application {{application_id}}",
            decision_critical_template=(
                "Application {{application_id}} has passed CV screening. We would like to "
                "invite you to the interview stage."
            ),
            editable_template=DEFAULT_EDITABLE_TEMPLATE,
        ),
        REJECTION_AFTER_CV: FixedTemplate(
            code=REJECTION_AFTER_CV,
            subject_template="Application update — {{application_id}}",
            decision_critical_template=(
                "After reviewing application {{application_id}}, we will not move forward "
                "beyond the CV screening stage."
            ),
            editable_template=DEFAULT_EDITABLE_TEMPLATE,
        ),
        OFFER_EMAIL: FixedTemplate(
            code=OFFER_EMAIL,
            subject_template="Offer update — Application {{application_id}}",
            decision_critical_template=(
                "Following the interview for application {{application_id}}, we are pleased "
                "to offer you the position associated with this application."
            ),
            editable_template=DEFAULT_EDITABLE_TEMPLATE,
        ),
        REJECTION_AFTER_INTERVIEW: FixedTemplate(
            code=REJECTION_AFTER_INTERVIEW,
            subject_template="Interview outcome — Application {{application_id}}",
            decision_critical_template=(
                "After completing the interview process for application {{application_id}}, "
                "we will not move forward with an offer."
            ),
            editable_template=DEFAULT_EDITABLE_TEMPLATE,
        ),
        DECISION_CORRECTION: FixedTemplate(
            code=DECISION_CORRECTION,
            subject_template="Decision correction — Application {{application_id}}",
            decision_critical_template=(
                "This email corrects the outcome previously communicated for application "
                "{{application_id}}. The current decision is: {{decision_label}}."
            ),
            editable_template=DEFAULT_EDITABLE_TEMPLATE,
        ),
    }
)


STAGE_DECISION_TEMPLATE_POLICY: Mapping[tuple[str, str], str] = MappingProxyType(
    {
        ("CV_SCREENING", "PASS_CV"): INTERVIEW_INVITATION,
        ("CV_SCREENING", "REJECT_CV"): REJECTION_AFTER_CV,
        ("INTERVIEW", "PASS_INTERVIEW"): OFFER_EMAIL,
        ("INTERVIEW", "REJECT_INTERVIEW"): REJECTION_AFTER_INTERVIEW,
    }
)


DECISION_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "PASS_CV": "Passed CV screening",
        "REJECT_CV": "Not proceeding after CV screening",
        "PASS_INTERVIEW": "Offer approved after interview",
        "REJECT_INTERVIEW": "Not proceeding after interview",
    }
)
