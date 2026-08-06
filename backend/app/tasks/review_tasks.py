from app.messaging.celery_app import REVIEW_TASK_NAME, celery_app
from app.services.agent_worker import process_review_job


@celery_app.task(
    bind=True,
    name=REVIEW_TASK_NAME,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def review_email_draft_task(
    self,
    *,
    queue_id: int,
    draft_version: int,
    content_hash: str,
) -> dict:
    return process_review_job(
        queue_id=queue_id,
        draft_version=draft_version,
        content_hash=content_hash,
        delivery_id=self.request.id or "unknown-delivery",
    )
