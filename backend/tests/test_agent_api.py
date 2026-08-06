import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.database import Base, get_db
from app.main import create_app
from app.models import Candidate, CandidateStatus, EmailQueue, EmailTemplate, EmailType
from app.services.email_workflow import generate_email_draft


class AgentReviewApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {"GEMINI_AGENT_ENABLED": "false"})
        self.environment.start()
        get_settings.cache_clear()

        with self.engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())

        app = create_app()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.environment.stop()
        get_settings.cache_clear()

    def test_review_endpoint_persists_result_on_queue_item(self) -> None:
        db = self.SessionLocal()
        try:
            candidate = Candidate(
                full_name="API Demo",
                email="api-demo@example.com",
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
            draft = generate_email_draft(db, candidate.id, None, "creator")
            queue_id = draft.id
        finally:
            db.close()

        response = self.client.post(
            "/api/v1/agent/review-draft",
            json={"queue_id": queue_id, "actor": "api_reviewer"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "disabled")

        verification_db = self.SessionLocal()
        try:
            queue_item = verification_db.get(EmailQueue, queue_id)
            self.assertEqual(
                queue_item.risk_check_result["agent_review"]["status"],
                "disabled",
            )
        finally:
            verification_db.close()

    def test_review_endpoint_rejects_unknown_fields(self) -> None:
        response = self.client.post(
            "/api/v1/agent/review-draft",
            json={"queue_id": 1, "status": "APPROVED"},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
