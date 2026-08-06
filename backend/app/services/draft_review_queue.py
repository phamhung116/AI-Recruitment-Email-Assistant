from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy.orm import Session

from app.models import EmailQueue, OutboxEvent, OutboxStatus


DRAFT_REVIEW_EVENT = "email.draft.review_requested"
REVIEW_METADATA_KEY = "async_review"
REVIEW_STATUS_QUEUED = "QUEUED"


def calculate_content_hash(subject: str, body: str) -> str:
    content = f"{subject}\n\0\n{body}".encode("utf-8")
    return sha256(content).hexdigest()


def prepare_queued_review(
    deterministic_result: dict,
    *,
    subject: str,
    body: str,
    previous_result: dict | None = None,
) -> dict:
    previous_result = previous_result or {}
    previous_metadata = previous_result.get(REVIEW_METADATA_KEY)
    previous_metadata = previous_metadata if isinstance(previous_metadata, dict) else {}
    draft_version = _positive_int(previous_result.get("draft_version")) + 1
    content_hash = calculate_content_hash(subject, body)
    queued_at = datetime.now(timezone.utc).isoformat()

    result = dict(deterministic_result)
    result.update(
        {
            "draft_version": draft_version,
            "content_hash": content_hash,
            REVIEW_METADATA_KEY: {
                "status": REVIEW_STATUS_QUEUED,
                "draft_version": draft_version,
                "review_version": _optional_positive_int(previous_metadata.get("review_version")),
                "content_hash": content_hash,
                "queued_at": queued_at,
                "started_at": None,
                "completed_at": None,
            },
        }
    )
    return result


def create_review_outbox_event(db: Session, queue_item: EmailQueue) -> OutboxEvent:
    metadata = review_metadata(queue_item)
    event = OutboxEvent(
        event_type=DRAFT_REVIEW_EVENT,
        aggregate_type="email_queue",
        aggregate_id=queue_item.id,
        payload_json={
            "queue_id": queue_item.id,
            "draft_version": metadata["draft_version"],
            "content_hash": metadata["content_hash"],
        },
        status=OutboxStatus.PENDING.value,
    )
    db.add(event)
    return event


def review_metadata(queue_item: EmailQueue) -> dict:
    risk_result = queue_item.risk_check_result or {}
    metadata = risk_result.get(REVIEW_METADATA_KEY)
    if not isinstance(metadata, dict):
        raise ValueError("Queue item does not contain asynchronous review metadata.")
    return metadata


def _positive_int(value: object) -> int:
    return value if isinstance(value, int) and value > 0 else 0


def _optional_positive_int(value: object) -> int | None:
    return value if isinstance(value, int) and value > 0 else None
