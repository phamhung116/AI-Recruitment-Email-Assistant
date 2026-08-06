import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.database import SessionLocal
from app.messaging.celery_app import REVIEW_TASK_NAME, REVIEW_TASK_QUEUE, celery_app
from app.models import OutboxEvent, OutboxStatus
from app.services.draft_review_queue import DRAFT_REVIEW_EVENT


OutboxPublisher = Callable[[OutboxEvent], None]


@dataclass(frozen=True)
class DispatchSummary:
    published: int = 0
    failed: int = 0


def publish_review_event(event: OutboxEvent) -> None:
    if event.event_type != DRAFT_REVIEW_EVENT:
        raise ValueError(f"Unsupported outbox event type: {event.event_type}")

    celery_app.send_task(
        REVIEW_TASK_NAME,
        kwargs={
            "queue_id": event.payload_json["queue_id"],
            "draft_version": event.payload_json["draft_version"],
            "content_hash": event.payload_json["content_hash"],
        },
        queue=REVIEW_TASK_QUEUE,
        task_id=f"outbox-{event.id}",
        retry=True,
        retry_policy={"max_retries": 3, "interval_start": 0, "interval_step": 1, "interval_max": 3},
    )


def dispatch_pending_events(
    *,
    session_factory: sessionmaker = SessionLocal,
    publisher: OutboxPublisher = publish_review_event,
    batch_size: int | None = None,
) -> DispatchSummary:
    settings = get_settings()
    db: Session = session_factory()
    published = 0
    failed = 0
    try:
        events = (
            db.query(OutboxEvent)
            .filter(OutboxEvent.status == OutboxStatus.PENDING.value)
            .order_by(OutboxEvent.id)
            .limit(batch_size or settings.outbox_batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        for event in events:
            event.attempt_count += 1
            try:
                publisher(event)
            except Exception as error:
                event.last_error = type(error).__name__[:500]
                failed += 1
            else:
                event.status = OutboxStatus.PUBLISHED.value
                event.published_at = datetime.now(timezone.utc)
                event.last_error = None
                published += 1
        db.commit()
        return DispatchSummary(published=published, failed=failed)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_dispatcher_forever(
    *,
    session_factory: sessionmaker = SessionLocal,
    publisher: OutboxPublisher = publish_review_event,
    settings: Settings | None = None,
) -> None:
    dispatcher_settings = settings or get_settings()
    while True:
        dispatch_pending_events(
            session_factory=session_factory,
            publisher=publisher,
            batch_size=dispatcher_settings.outbox_batch_size,
        )
        time.sleep(dispatcher_settings.outbox_poll_interval_seconds)
