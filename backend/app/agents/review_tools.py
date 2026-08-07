import re
from collections.abc import Callable

from app.schemas.agent import (
    AgentReviewRequest,
    AgentToolFinding,
    AgentToolName,
    AgentToolObservation,
)
from app.schemas.validation import IssueSeverity


ReviewTool = Callable[[AgentReviewRequest], AgentToolObservation]

EXPECTED_INTENTS = {
    "APPLICATION_RECEIVED": "acknowledgement",
    "INTERVIEW_INVITATION": "interview invitation",
    "INTERVIEW_REMINDER": "interview reminder",
    "REJECTION_AFTER_CV": "rejection",
    "REJECTION_AFTER_INTERVIEW": "rejection",
    "OFFER_EMAIL": "job offer",
    "ONBOARDING_EMAIL": "onboarding",
    "RESCHEDULE_RESPONSE": "interview reschedule",
    "NEXT_ROUND_EMAIL": "next-round progression",
}

SENSITIVE_EMAIL_TYPES = {
    "REJECTION_AFTER_CV",
    "REJECTION_AFTER_INTERVIEW",
    "OFFER_EMAIL",
}

OUTCOME_CUES = {
    "rejection": ("not move forward", "will not proceed", "regret to inform", "unsuccessful"),
    "interview": ("invite you to interview", "interview invitation", "schedule an interview"),
    "offer": ("offer you", "job offer", "offer letter"),
    "onboarding": ("welcome aboard", "onboarding", "start date"),
    "progression": ("next round", "move forward with", "progress to"),
}


def execute_review_tool(tool: AgentToolName, request: AgentReviewRequest) -> AgentToolObservation:
    try:
        handler = REVIEW_TOOL_REGISTRY[tool]
    except KeyError as error:
        raise ValueError(f"Unsupported review tool: {tool}") from error
    return handler(request)


def check_candidate_facts(request: AgentReviewRequest) -> AgentToolObservation:
    content = _normalize(f"{request.draft.subject}\n{request.draft.body}")
    facts = {
        "candidate_name": request.candidate.full_name,
        "position": request.candidate.position,
    }
    if request.email_type in {"INTERVIEW_INVITATION", "INTERVIEW_REMINDER", "RESCHEDULE_RESPONSE"}:
        facts.update({
            "interview_time": request.candidate.interview_time,
            "interviewer": request.candidate.interviewer,
        })

    findings: list[AgentToolFinding] = []
    for field, value in facts.items():
        if not value:
            findings.append(AgentToolFinding(
                code=f"TOOL_{field.upper()}_UNAVAILABLE",
                severity=IssueSeverity.WARNING,
                message=f"Verified {field.replace('_', ' ')} is unavailable.",
                evidence={"field": field, "available": False},
            ))
            continue

        matched = _fact_matches_content(field, value, content)
        findings.append(AgentToolFinding(
            code=f"TOOL_{field.upper()}_{'MATCHED' if matched else 'NOT_FOUND'}",
            severity=IssueSeverity.INFO if matched else IssueSeverity.ERROR,
            message=(
                f"Verified {field.replace('_', ' ')} appears in the draft."
                if matched
                else f"Verified {field.replace('_', ' ')} was not found in the draft."
            ),
            evidence={"field": field, "matched": matched},
        ))

    missing_count = sum(finding.severity != IssueSeverity.INFO for finding in findings)
    return AgentToolObservation(
        tool=AgentToolName.CHECK_CANDIDATE_FACTS,
        summary=f"Checked {len(findings)} candidate facts; {missing_count} need semantic review.",
        findings=findings,
    )


def check_email_policy(request: AgentReviewRequest) -> AgentToolObservation:
    normalized_body = _normalize(request.draft.body)
    expected_intent = EXPECTED_INTENTS.get(request.email_type, "configured recruitment communication")
    detected_cues = [
        cue_name
        for cue_name, phrases in OUTCOME_CUES.items()
        if any(phrase in normalized_body for phrase in phrases)
    ]
    is_sensitive = request.template.is_sensitive or request.email_type in SENSITIVE_EMAIL_TYPES

    findings = [
        AgentToolFinding(
            code="TOOL_EXPECTED_EMAIL_INTENT",
            severity=IssueSeverity.INFO,
            message=f"The configured email intent is {expected_intent}.",
            evidence={"email_type": request.email_type, "expected_intent": expected_intent},
        ),
        AgentToolFinding(
            code="TOOL_DETECTED_OUTCOME_CUES",
            severity=IssueSeverity.INFO,
            message=(
                f"Detected outcome cues: {', '.join(detected_cues)}."
                if detected_cues
                else "No explicit outcome cue was detected; review the wording for ambiguity."
            ),
            evidence={"detected_cues": detected_cues},
        ),
        AgentToolFinding(
            code="TOOL_HR_APPROVAL_POLICY",
            severity=IssueSeverity.WARNING if is_sensitive else IssueSeverity.INFO,
            message=(
                "This email requires an explicit HR checkpoint."
                if is_sensitive
                else "This email type is not automatically classified as sensitive."
            ),
            evidence={"sensitive": is_sensitive},
        ),
    ]
    return AgentToolObservation(
        tool=AgentToolName.CHECK_EMAIL_POLICY,
        summary="Loaded the expected intent, detected wording cues, and evaluated HR policy.",
        findings=findings,
    )


def _fact_matches_content(field: str, value: str, normalized_content: str) -> bool:
    normalized_value = _normalize(value)
    if normalized_value in normalized_content:
        return True
    if field == "interview_time":
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        time_match = re.search(r"\d{2}:\d{2}", value)
        return bool(
            date_match
            and date_match.group(0) in normalized_content
            and (time_match is None or time_match.group(0) in normalized_content)
        )
    return False


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


REVIEW_TOOL_REGISTRY: dict[AgentToolName, ReviewTool] = {
    AgentToolName.CHECK_CANDIDATE_FACTS: check_candidate_facts,
    AgentToolName.CHECK_EMAIL_POLICY: check_email_policy,
}
