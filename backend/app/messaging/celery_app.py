from celery import Celery

from app.core.config import get_settings


REVIEW_TASK_NAME = "email_review.review_draft"
REVIEW_TASK_QUEUE = "email_review"

settings = get_settings()
celery_app = Celery(
    "recruitment_mail_guard",
    broker=settings.rabbitmq_url,
    include=["app.tasks.review_tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_backend=None,
    task_acks_late=True,
    task_default_queue=REVIEW_TASK_QUEUE,
    task_ignore_result=True,
    task_reject_on_worker_lost=True,
    task_routes={REVIEW_TASK_NAME: {"queue": REVIEW_TASK_QUEUE}},
    task_serializer="json",
    timezone="UTC",
    worker_prefetch_multiplier=1,
)
