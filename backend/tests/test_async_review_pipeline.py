import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.database import Base
from app.messaging.celery_app import celery_app
from app.models import Candidate, CandidateStatus, EmailQueue, EmailTemplate, EmailType, OutboxEvent, OutboxStatus
from app.schemas.agent import AgentModelMetadata, AgentReviewResult, AgentReviewStatus, AgentUncertainty
from app.services.agent_worker import WORKER_COMPLETED, WORKER_DUPLICATE, WORKER_STALE, process_review_job
from app.services.email_workflow import generate_email_draft, update_email_draft
from app.services.outbox_dispatcher import dispatch_pending_events
from app.services.review_progress import review_progress_key


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set(self, name, value, ex=None, nx=False):
        if nx and name in self.values:
            return False
        self.values[name] = value
        return True

    def eval(self, script, number_of_keys, key, token):
        if self.values.get(key) != token:
            return 0
        del self.values[key]
        return 1


class CountingReviewAgent:
    def __init__(self, before_result=None) -> None:
        self.calls = 0
        self.before_result = before_result

    def review(self, request) -> AgentReviewResult:
        self.calls += 1
        if self.before_result:
            self.before_result()
        return AgentReviewResult(
            status=AgentReviewStatus.COMPLETED,
            draft_subject=request.draft.subject,
            draft_body=request.draft.body,
            issues=[],
            uncertainty=AgentUncertainty(has_uncertainty=False),
            review_summary="The draft matches the supplied facts.",
            requires_human_review=False,
            semantic_review_available=True,
            model_metadata=AgentModelMetadata(
                provider="fake-gemini",
                model="fake-model",
                prompt_version="semantic_review.v1",
                skill_name="recruitment-email-review",
                skill_version="1.0.0",
                attempts=1,
            ),
            trace=[],
        )


class AsyncReviewPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(cls.temp_directory.name) / "async-review.sqlite3"
        cls.engine = create_engine(
            f"sqlite+pysqlite:///{database_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()
        cls.temp_directory.cleanup()

    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {"GEMINI_AGENT_ENABLED": "false"})
        self.environment.start()
        get_settings.cache_clear()
        with self.engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())

    def tearDown(self) -> None:
        self.environment.stop()
        get_settings.cache_clear()

    def test_celery_uses_rabbitmq_without_a_result_backend(self) -> None:
        self.assertTrue(celery_app.conf.broker_url.startswith("amqp://"))
        self.assertIsNone(celery_app.conf.result_backend)

    def test_dispatcher_publishes_pending_event_and_marks_it_published(self) -> None:
        draft = self._create_draft()
        published_payloads: list[dict] = []

        summary = dispatch_pending_events(
            session_factory=self.SessionLocal,
            publisher=lambda event: published_payloads.append(dict(event.payload_json)),
        )

        self.assertEqual(summary.published, 1)
        self.assertEqual(summary.failed, 0)
        self.assertEqual(published_payloads[0]["queue_id"], draft.id)
        db = self.SessionLocal()
        try:
            event = db.query(OutboxEvent).one()
            self.assertEqual(event.status, OutboxStatus.PUBLISHED.value)
            self.assertEqual(event.attempt_count, 1)
            self.assertIsNotNone(event.published_at)
        finally:
            db.close()

    def test_dispatcher_keeps_event_pending_when_rabbitmq_publish_fails(self) -> None:
        self._create_draft()

        def fail_publish(event):
            raise ConnectionError("private broker detail")

        summary = dispatch_pending_events(
            session_factory=self.SessionLocal,
            publisher=fail_publish,
        )

        self.assertEqual(summary.published, 0)
        self.assertEqual(summary.failed, 1)
        db = self.SessionLocal()
        try:
            event = db.query(OutboxEvent).one()
            self.assertEqual(event.status, OutboxStatus.PENDING.value)
            self.assertEqual(event.last_error, "ConnectionError")
            self.assertNotIn("private broker detail", event.last_error)
        finally:
            db.close()

    def test_duplicate_worker_delivery_calls_agent_once(self) -> None:
        draft = self._create_draft()
        version = draft.risk_check_result["draft_version"]
        content_hash = draft.risk_check_result["content_hash"]
        redis_client = FakeRedis()
        agent = CountingReviewAgent()

        first = process_review_job(
            queue_id=draft.id,
            draft_version=version,
            content_hash=content_hash,
            delivery_id="delivery-1",
            session_factory=self.SessionLocal,
            redis_client=redis_client,
            agent=agent,
        )
        duplicate = process_review_job(
            queue_id=draft.id,
            draft_version=version,
            content_hash=content_hash,
            delivery_id="delivery-2",
            session_factory=self.SessionLocal,
            redis_client=redis_client,
            agent=agent,
        )

        self.assertEqual(first["status"], WORKER_COMPLETED)
        self.assertEqual(duplicate["status"], WORKER_DUPLICATE)
        self.assertEqual(agent.calls, 1)
        self.assertIn(review_progress_key(draft.id, version), redis_client.values)

    def test_result_becomes_stale_when_draft_changes_during_agent_call(self) -> None:
        draft = self._create_draft()
        version = draft.risk_check_result["draft_version"]
        content_hash = draft.risk_check_result["content_hash"]

        def save_new_version() -> None:
            db = self.SessionLocal()
            try:
                update_email_draft(db, draft.id, subject="Newer subject wins")
            finally:
                db.close()

        agent = CountingReviewAgent(before_result=save_new_version)
        result = process_review_job(
            queue_id=draft.id,
            draft_version=version,
            content_hash=content_hash,
            delivery_id="stale-delivery",
            session_factory=self.SessionLocal,
            redis_client=FakeRedis(),
            agent=agent,
        )

        self.assertEqual(result["status"], WORKER_STALE)
        db = self.SessionLocal()
        try:
            current = db.get(EmailQueue, draft.id)
            self.assertEqual(current.subject, "Newer subject wins")
            self.assertEqual(current.risk_check_result["draft_version"], 2)
            self.assertEqual(current.risk_check_result["async_review"]["status"], "QUEUED")
            self.assertNotIn("agent_review", current.risk_check_result)
        finally:
            db.close()

    def _create_draft(self) -> EmailQueue:
        db = self.SessionLocal()
        try:
            candidate = Candidate(
                full_name="Async Demo",
                email="async-demo@example.com",
                position="Backend Engineer",
                stage="CV_SCREENING",
                status=CandidateStatus.PASS_CV.value,
                interview_time=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
                interviewer="HR Demo",
            )
            template = EmailTemplate(
                name="Interview template",
                email_type=EmailType.INTERVIEW_INVITATION.value,
                subject="Interview for {{position}}",
                body="Hello {{candidate_name}}, meet {{interviewer}} at {{interview_time}}.",
                required_placeholders=["candidate_name", "position", "interviewer", "interview_time"],
                is_sensitive=False,
            )
            db.add_all([candidate, template])
            db.commit()
            return generate_email_draft(db, candidate.id, None, "creator")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
