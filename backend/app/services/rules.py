from app.models import CandidateStatus, EmailType


STATUS_EMAIL_RULES: dict[str, str | None] = {
    CandidateStatus.PASS_CV.value: EmailType.INTERVIEW_INVITATION.value,
    CandidateStatus.REJECT_CV.value: EmailType.REJECTION_AFTER_CV.value,
    CandidateStatus.INTERVIEW_CONFIRMED.value: EmailType.INTERVIEW_REMINDER.value,
    CandidateStatus.PASS_INTERVIEW.value: EmailType.OFFER_EMAIL.value,
    CandidateStatus.REJECT_INTERVIEW.value: EmailType.REJECTION_AFTER_INTERVIEW.value,
    CandidateStatus.OFFER_ACCEPTED.value: EmailType.ONBOARDING_EMAIL.value,
    CandidateStatus.PENDING.value: None,
}

SENSITIVE_EMAIL_TYPES = {
    EmailType.REJECTION_AFTER_CV.value,
    EmailType.REJECTION_AFTER_INTERVIEW.value,
    EmailType.OFFER_EMAIL.value,
}

SEND_STATUS_TRANSITIONS: dict[str, dict[str, str]] = {
    EmailType.INTERVIEW_INVITATION.value: {"stage": "INTERVIEW", "status": CandidateStatus.INTERVIEW_CONFIRMED.value},
    EmailType.OFFER_EMAIL.value: {"stage": "OFFER", "status": CandidateStatus.PASS_INTERVIEW.value},
    EmailType.ONBOARDING_EMAIL.value: {"stage": "ONBOARDING", "status": CandidateStatus.OFFER_ACCEPTED.value},
}


def email_type_for_status(status: str) -> str | None:
    return STATUS_EMAIL_RULES.get(status)
