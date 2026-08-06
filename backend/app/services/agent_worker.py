from datetime import datetime, timezone

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.agents import RecruitmentEmailAgent
from app.constants.auditActions import AGENT_REVIEW_EMAIL
from app.core.config import Settings, get_settings
from app.db.database import SessionLocal
from app.models import EmailQueue, EmailTemplate, QueueStatus
from app.schemas.agent import AgentReviewResult, AgentReviewStatus
from app.services.agent_review import (
    agent_review_audit_metadata,
    merge_review_result,
    review_email_content,
)
from app.services.audit import log_action
from app.services.draft_review_queue import REVIEW_METADATA_KEY
from app.services.review_progress import (
    acquire_review_lock,
    get_redis_client,
    release_review_lock,
    write_review_progress,
)
from app.services.rules import SENSITIVE_EMAIL_TYPES
from app.services.validation import validate_email_draft


WORKER_COMPLETED = "COMPLETED"
WORKER_DUPLICATE = "DUPLICATE"
WORKER_FAILED = "FAILED"
WORKER_STALE = "STALE"
WORKER_UNAVAILABLE = "UNAVAILABLE"


def process_review_job(
    *,
    queue_id: int,
    draft_version: int,
    content_hash: str,
    delivery_id: str,
    session_factory: sessionmaker = SessionLocal,
    redis_client: Redis | None = None,
    agent: RecruitmentEmailAgent | None = None,
    settings: Settings | None = None,
) -> dict:
    worker_settings = settings or get_settings()
    progress_client = redis_client or get_redis_client(worker_settings)
    try:
        lock_token = acquire_review_lock(
            progress_client,
            queue_id=queue_id,
            draft_version=draft_version,
            content_hash=content_hash,
            ttl_seconds=worker_settings.review_lock_ttl_seconds,
        )
    except RedisError:
        _mark_review_status_if_current(
            session_factory,
            queue_id=queue_id,
            draft_version=draft_version,
            content_hash=content_hash,
            status=WORKER_UNAVAILABLE,
            failure_reason="redis_unavailable",
        )
        return _result(queue_id, draft_version, WORKER_UNAVAILABLE)

    if lock_token is None:
        return _result(queue_id, draft_version, WORKER_DUPLICATE)

    _write_progress_safely(
        progress_client,
        queue_id=queue_id,
        draft_version=draft_version,
        status="REVIEWING",
        ttl_seconds=worker_settings.review_progress_ttl_seconds,
    )
    try:
        status = _review_and_persist(
            session_factory,
            queue_id=queue_id,
            draft_version=draft_version,
            content_hash=content_hash,
            agent=agent,
            delivery_id=delivery_id,
        )
    except HTTPException:
        _mark_review_status_if_current(
            session_factory,
            queue_id=queue_id,
            draft_version=draft_version,
            content_hash=content_hash,
            status=WORKER_FAILED,
            failure_reason="deterministic_validation_failed",
        )
        _write_progress_safely(
            progress_client,
            queue_id=queue_id,
            draft_version=draft_version,
            status=WORKER_FAILED,
            ttl_seconds=worker_settings.review_progress_ttl_seconds,
        )
        return _result(queue_id, draft_version, WORKER_FAILED)
    except Exception as error:
        _mark_review_status_if_current(
            session_factory,
            queue_id=queue_id,
            draft_version=draft_version,
            content_hash=content_hash,
            status=WORKER_FAILED,
            failure_reason=type(error).__name__,
        )
        _write_progress_safely(
            progress_client,
            queue_id=queue_id,
            draft_version=draft_version,
            status=WORKER_FAILED,
            ttl_seconds=worker_settings.review_progress_ttl_seconds,
        )
        _release_lock_safely(
            progress_client,
            queue_id=queue_id,
            draft_version=draft_version,
            content_hash=content_hash,
            token=lock_token,
        )
        raise

    _write_progress_safely(
        progress_client,
        queue_id=queue_id,
        draft_version=draft_version,
        status=status,
        ttl_seconds=worker_settings.review_progress_ttl_seconds,
    )
    return _result(queue_id, draft_version, status)


def _review_and_persist(
    session_factory: sessionmaker,
    *,
    queue_id: int,
    draft_version: int,
    content_hash: str,
    agent: RecruitmentEmailAgent | None,
    delivery_id: str,
) -> str:
    read_db: Session = session_factory()
    try:
        item = (
            read_db.query(EmailQueue)
            .options(joinedload(EmailQueue.candidate))
            .filter(EmailQueue.id == queue_id)
            .first()
        )
        if item is None:
            return WORKER_STALE
        if not _matches_review_job(item, draft_version, content_hash):
            return WORKER_STALE

        template = (
            read_db.query(EmailTemplate)
            .filter(EmailTemplate.email_type == item.email_type)
            .first()
        )
        deterministic = validate_email_draft(
            db=read_db,
            candidate=item.candidate,
            template=template,
            email_type=item.email_type,
            rendered_subject=item.subject,
            rendered_body=item.body,
        )
        if not deterministic.passed:
            raise HTTPException(status_code=400, detail=deterministic.model_dump(mode="json"))
        if template is None:
            raise HTTPException(status_code=400, detail="Email template not found.")
        candidate = item.candidate
        email_type = item.email_type
        subject = item.subject
        body = item.body
    finally:
        read_db.close()

    review = review_email_content(
        candidate=candidate,
        template=template,
        email_type=email_type,
        subject=subject,
        body=body,
        deterministic_validation=deterministic,
        agent=agent,
    )

    db: Session = session_factory()
    try:
        locked_item = (
            db.query(EmailQueue)
            .populate_existing()
            .filter(EmailQueue.id == queue_id)
            .with_for_update()
            .first()
        )
        if locked_item is None or not _matches_review_job(locked_item, draft_version, content_hash):
            db.rollback()
            return WORKER_STALE

        worker_status = _worker_status(review)
        locked_item.risk_check_result = _completed_risk_result(
            locked_item,
            deterministic.model_dump(mode="json"),
            review,
            worker_status=worker_status,
            draft_version=draft_version,
            content_hash=content_hash,
        )
        _apply_review_requirement(locked_item, template, review, worker_status)
        log_action(
            db,
            AGENT_REVIEW_EMAIL,
            "email_queue",
            locked_item.id,
            "agent_worker",
            {
                **agent_review_audit_metadata(review),
                "delivery_id": delivery_id,
                "draft_version": draft_version,
            },
        )
        db.commit()
        return worker_status
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _completed_risk_result(
    item: EmailQueue,
    deterministic_result: dict,
    review: AgentReviewResult,
    *,
    worker_status: str,
    draft_version: int,
    content_hash: str,
) -> dict:
    result = merge_review_result(deterministic_result, review)
    previous_metadata = (item.risk_check_result or {}).get(REVIEW_METADATA_KEY)
    previous_metadata = previous_metadata if isinstance(previous_metadata, dict) else {}
    result.update(
        {
            "draft_version": draft_version,
            "content_hash": content_hash,
            REVIEW_METADATA_KEY: {
                **previous_metadata,
                "status": worker_status,
                "draft_version": draft_version,
                "review_version": draft_version,
                "content_hash": content_hash,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    )
    return result


def _apply_review_requirement(
    item: EmailQueue,
    template: EmailTemplate | None,
    review: AgentReviewResult,
    worker_status: str,
) -> None:
    requires_approval = (
        item.email_type in SENSITIVE_EMAIL_TYPES
        or bool(template and template.is_sensitive)
        or review.requires_human_review
        or worker_status != WORKER_COMPLETED
    )
    item.requires_hr_approval = requires_approval
    if item.status == QueueStatus.APPROVED.value:
        item.approved_by = None
    if item.status in {
        QueueStatus.DRAFT.value,
        QueueStatus.PENDING_APPROVAL.value,
        QueueStatus.APPROVED.value,
    }:
        item.status = (
            QueueStatus.PENDING_APPROVAL.value
            if requires_approval
            else QueueStatus.DRAFT.value
        )


def _mark_review_status_if_current(
    session_factory: sessionmaker,
    *,
    queue_id: int,
    draft_version: int,
    content_hash: str,
    status: str,
    failure_reason: str,
) -> bool:
    db: Session = session_factory()
    try:
        item = (
            db.query(EmailQueue)
            .filter(EmailQueue.id == queue_id)
            .with_for_update()
            .first()
        )
        if item is None or not _matches_review_job(item, draft_version, content_hash):
            db.rollback()
            return False
        risk_result = dict(item.risk_check_result or {})
        metadata = risk_result.get(REVIEW_METADATA_KEY)
        metadata = dict(metadata) if isinstance(metadata, dict) else {}
        metadata.update(
            {
                "status": status,
                "draft_version": draft_version,
                "content_hash": content_hash,
                "failure_reason": failure_reason,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        risk_result[REVIEW_METADATA_KEY] = metadata
        item.risk_check_result = risk_result
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _matches_review_job(item: EmailQueue, draft_version: int, content_hash: str) -> bool:
    risk_result = item.risk_check_result or {}
    return (
        risk_result.get("draft_version") == draft_version
        and risk_result.get("content_hash") == content_hash
    )


def _worker_status(review: AgentReviewResult) -> str:
    if review.status == AgentReviewStatus.COMPLETED:
        return WORKER_COMPLETED
    if review.status in {AgentReviewStatus.DISABLED, AgentReviewStatus.UNAVAILABLE}:
        return WORKER_UNAVAILABLE
    return WORKER_FAILED


def _write_progress_safely(
    redis_client: Redis,
    *,
    queue_id: int,
    draft_version: int,
    status: str,
    ttl_seconds: int,
) -> None:
    try:
        write_review_progress(
            redis_client,
            queue_id=queue_id,
            draft_version=draft_version,
            status=status,
            ttl_seconds=ttl_seconds,
        )
    except RedisError:
        pass


def _release_lock_safely(
    redis_client: Redis,
    *,
    queue_id: int,
    draft_version: int,
    content_hash: str,
    token: str,
) -> None:
    try:
        release_review_lock(
            redis_client,
            queue_id=queue_id,
            draft_version=draft_version,
            content_hash=content_hash,
            token=token,
        )
    except RedisError:
        pass


def _result(queue_id: int, draft_version: int, status: str) -> dict:
    return {
        "queue_id": queue_id,
        "draft_version": draft_version,
        "status": status,
    }
