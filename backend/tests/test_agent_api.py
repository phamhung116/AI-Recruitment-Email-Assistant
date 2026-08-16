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
from app.models import Candidate, CandidateStatus, EmailQueue, EmailTemplate, EmailType, OutboxEvent
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
                application_id="TEST-API-001",
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

    def test_saving_draft_rechecks_required_candidate_content(self) -> None:
        db = self.SessionLocal()
        try:
            candidate = Candidate(
                application_id="TEST-API-002",
                full_name="Tran Bao Chau",
                email="chau@example.com",
                position="Backend Developer",
                stage="CV_SCREENING",
                status=CandidateStatus.REJECT_CV.value,
            )
            template = EmailTemplate(
                name="CV rejection",
                email_type=EmailType.REJECTION_AFTER_CV.value,
                subject="Update on your application for {{position}}",
                body="Hi {{candidate_name}}, thank you for your interest in {{position}}.",
                required_placeholders=["candidate_name", "position"],
                is_sensitive=True,
            )
            db.add_all([candidate, template])
            db.commit()
            queue_id = generate_email_draft(db, candidate.id, None, "creator").id
        finally:
            db.close()

        response = self.client.patch(
            f"/email-queue/{queue_id}",
            json={
                "subject": "Update on your application for Backend Developer",
                "body": "Hi\n\nThank you for your interest in Backend Developer.",
            },
        )

        self.assertEqual(response.status_code, 400, response.text)
        result = response.json()["detail"]
        self.assertFalse(result["passed"])
        self.assertIn(
            "REQUIRED_CONTENT_MISSING",
            [issue["rule_id"] for issue in result["issues"]],
        )

    def test_saving_draft_reports_candidate_name_mismatch_with_context(self) -> None:
        db = self.SessionLocal()
        try:
            candidate = Candidate(
                application_id="TEST-API-003",
                full_name="Tran Bao Chau",
                email="chau@example.com",
                position="Backend Developer",
                stage="CV_SCREENING",
                status=CandidateStatus.REJECT_CV.value,
            )
            template = EmailTemplate(
                name="CV rejection",
                email_type=EmailType.REJECTION_AFTER_CV.value,
                subject="Update on your application for {{position}}",
                body="Hi {{candidate_name}}, thank you for your interest in {{position}}.",
                required_placeholders=["candidate_name", "position"],
                is_sensitive=True,
            )
            db.add_all([candidate, template])
            db.commit()
            queue_id = generate_email_draft(db, candidate.id, None, "creator").id
        finally:
            db.close()

        response = self.client.patch(
            f"/email-queue/{queue_id}",
            json={
                "subject": "Update on your application for Backend Developer",
                "body": "Hi Ha Bao Chau,\n\nThank you for your interest in Backend Developer.",
            },
        )

        self.assertEqual(response.status_code, 400, response.text)
        result = response.json()["detail"]
        issues = result["issues"]
        mismatch = next(issue for issue in issues if issue["rule_id"] == "CANDIDATE_NAME_MISMATCH")
        self.assertEqual(mismatch["evidence"]["expected_candidate_name"], "Tran Bao Chau")
        self.assertEqual(mismatch["evidence"]["detected_candidate_name"], "Ha Bao Chau")
        self.assertIn("Expected 'Tran Bao Chau'", mismatch["message"])
        self.assertNotIn("candidate_name", [
            placeholder
            for issue in issues
            if issue["rule_id"] == "REQUIRED_CONTENT_MISSING"
            for placeholder in issue["evidence"]["missing_placeholders"]
        ])

    def test_semantically_changed_draft_requires_fresh_agent_review_before_approval(self) -> None:
        db = self.SessionLocal()
        try:
            candidate = Candidate(
                application_id="TEST-API-004",
                full_name="Tran Bao Chau",
                email="chau@example.com",
                position="Backend Developer",
                stage="CV_SCREENING",
                status=CandidateStatus.REJECT_CV.value,
            )
            template = EmailTemplate(
                name="CV rejection",
                email_type=EmailType.REJECTION_AFTER_CV.value,
                subject="Update on your application for {{position}}",
                body="Hi {{candidate_name}}, thank you for your interest in {{position}}.",
                required_placeholders=["candidate_name", "position"],
                is_sensitive=True,
            )
            db.add_all([candidate, template])
            db.commit()
            queue_id = generate_email_draft(db, candidate.id, None, "creator").id
        finally:
            db.close()

        save_response = self.client.patch(
            f"/email-queue/{queue_id}",
            json={
                "subject": "Update on your application for Backend Developer",
                "body": (
                    "Hi Tran Bao Chau,\n\n"
                    "Thank you for applying for Backend Developer. "
                    "We are pleased to invite you to the next interview. "
                    "Unfortunately, we will not move forward with your application."
                ),
            },
        )
        self.assertEqual(save_response.status_code, 200, save_response.text)
        self.assertTrue(save_response.json()["risk_check_result"]["passed"])
        self.assertEqual(
            save_response.json()["risk_check_result"]["async_review"]["status"],
            "QUEUED",
        )
        self.assertNotIn("agent_review", save_response.json()["risk_check_result"])

        premature_approval = self.client.post(f"/email-queue/{queue_id}/approve")
        self.assertEqual(premature_approval.status_code, 400)
        self.assertIn("Wait for AI review", premature_approval.json()["detail"])

    def test_pass_cv_contradiction_is_saved_as_a_new_version_for_agent_review(self) -> None:
        db = self.SessionLocal()
        try:
            candidate = Candidate(
                application_id="TEST-API-005",
                full_name="Nguyen Minh An",
                email="an@example.com",
                position="Backend Developer",
                stage="CV_SCREENING",
                status=CandidateStatus.PASS_CV.value,
            )
            template = EmailTemplate(
                name="Interview invitation",
                email_type=EmailType.INTERVIEW_INVITATION.value,
                subject="Interview for {{position}}",
                body="Hi {{candidate_name}}, we would like to invite you to interview for {{position}}.",
                required_placeholders=["candidate_name", "position"],
                is_sensitive=False,
            )
            db.add_all([candidate, template])
            db.commit()
            draft = generate_email_draft(db, candidate.id, None, "creator")
            risk_result = dict(draft.risk_check_result)
            async_review = dict(risk_result["async_review"])
            async_review.update({
                "status": "COMPLETED",
                "review_version": risk_result["draft_version"],
            })
            risk_result["async_review"] = async_review
            draft.risk_check_result = risk_result
            db.commit()
            queue_id = draft.id
        finally:
            db.close()

        response = self.client.patch(
            f"/email-queue/{queue_id}",
            json={
                "subject": "Interview for Backend Developer",
                "body": (
                    "Hi Nguyen Minh An,\n\n"
                    "Thank you for applying for Backend Developer. "
                    "We will not move forward with your application now, but perhaps next time."
                ),
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        saved_risk = response.json()["risk_check_result"]
        self.assertEqual(saved_risk["draft_version"], 2)
        self.assertEqual(saved_risk["async_review"]["status"], "QUEUED")
        self.assertNotIn("agent_review", saved_risk)

        db = self.SessionLocal()
        try:
            events = (
                db.query(OutboxEvent)
                .filter(OutboxEvent.aggregate_id == queue_id)
                .order_by(OutboxEvent.id)
                .all()
            )
            self.assertEqual(len(events), 2)
            self.assertEqual(events[-1].payload_json["draft_version"], 2)
            self.assertEqual(events[-1].status, "PENDING")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
