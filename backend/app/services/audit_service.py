"""Append-only audit events for recruitment workflow state transitions."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.models import ActionOutcome, AuditLog


class AuditEvent(str, Enum):
    CANDIDATE_IMPORTED = "CANDIDATE_IMPORTED"
    DRAFT_GENERATED = "DRAFT_GENERATED"
    SEND_PREPARED = "SEND_PREPARED"
    SEND_OUTCOME_FINALIZED = "SEND_OUTCOME_FINALIZED"
    DECISION_CORRECTED = "DECISION_CORRECTED"
    DELIVERY_UNKNOWN_RESOLVED = "DELIVERY_UNKNOWN_RESOLVED"


SENSITIVE_PAYLOAD_KEYS = frozenset(
    {
        "body",
        "email",
        "full_name",
        "phone",
        "rendered_body",
        "subject",
        "to_email",
    }
)


def append_audit_event(
    db: Session,
    *,
    event: AuditEvent,
    entity_type: str,
    entity_id: str | int,
    actor: str,
    application_id: str | None = None,
    outcome: ActionOutcome = ActionOutcome.SUCCESS,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    """Stage a sanitized event in the caller-owned transaction."""

    normalized_actor = actor.strip()
    if not normalized_actor:
        raise ValueError("Audit actor is required.")

    sanitized_payload = payload or {}
    prohibited = SENSITIVE_PAYLOAD_KEYS.intersection(sanitized_payload)
    if prohibited:
        names = ", ".join(sorted(prohibited))
        raise ValueError(f"Audit payload contains prohibited PII/content keys: {names}")

    audit = AuditLog(
        event_name=event.value,
        entity_type=entity_type,
        entity_id=str(entity_id),
        application_id=application_id,
        actor=normalized_actor,
        action_outcome=outcome.value,
        payload_json=sanitized_payload,
    )
    db.add(audit)
    return audit
