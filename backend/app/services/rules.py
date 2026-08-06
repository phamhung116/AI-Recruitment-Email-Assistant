from enum import Enum

from app.models import CandidateStatus, EmailType, QueueStatus


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

class QueueAction(str, Enum):
    EDIT = "edit"
    REVIEW = "review"
    APPROVE = "approve"
    CANCEL = "cancel"
    SIMULATE_SEND = "simulate_send"


QUEUE_ACTION_ALLOWED_STATUSES: dict[QueueAction, set[str]] = {
    QueueAction.EDIT: {
        QueueStatus.DRAFT.value,
        QueueStatus.PENDING_APPROVAL.value,
        QueueStatus.APPROVED.value,
    },
    QueueAction.REVIEW: {
        QueueStatus.DRAFT.value,
        QueueStatus.PENDING_APPROVAL.value,
        QueueStatus.APPROVED.value,
    },
    QueueAction.APPROVE: {
        QueueStatus.DRAFT.value,
        QueueStatus.PENDING_APPROVAL.value,
    },
    QueueAction.CANCEL: {
        QueueStatus.DRAFT.value,
        QueueStatus.PENDING_APPROVAL.value,
        QueueStatus.APPROVED.value,
        QueueStatus.FAILED.value,
    },
    QueueAction.SIMULATE_SEND: {
        QueueStatus.DRAFT.value,
        QueueStatus.APPROVED.value,
    },
}


def email_type_for_status(status: str) -> str | None:
    return STATUS_EMAIL_RULES.get(status)


def is_queue_action_allowed(status: str, action: QueueAction) -> bool:
    return status in QUEUE_ACTION_ALLOWED_STATUSES[action]
