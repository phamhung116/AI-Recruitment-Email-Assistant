import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.constants.auditActions import AGENT_REVIEW_EMAIL, AUTO_CANCEL_EMAIL, SEND_EMAIL
from app.core.config import get_settings
from app.models import AuditLog, Candidate, CandidateStatus, EmailHistory, EmailQueue, EmailTemplate, EmailType, OutboxEvent, OutboxStatus, QueueStatus
from app.schemas.agent import (
    AgentModelMetadata,
    AgentReviewResult,
    AgentReviewStatus,
    AgentSemanticIssue,
    AgentUncertainty,
)
from app.schemas.api import EmailQueueUpdate
from app.schemas.validation import IssueSeverity
from app.services.agent_review import review_queue_draft
from app.services.email_workflow import (
    approve_email,
    cancel_email,
    generate_email_draft,
    send_email,
    update_email_draft,
)


class StaticReviewAgent:
    def __init__(self, result: AgentReviewResult) -> None:
        self.result = result

    def review(self, request) -> AgentReviewResult:
        return self.result


class QueueStateMachineTest(unittest.TestCase):
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
        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        try:
            self.db.rollback()
            self.db.close()
            with self.engine.begin() as connection:
                for table in reversed(Base.metadata.sorted_tables):
                    connection.execute(table.delete())
        finally:
            self.environment.stop()
            get_settings.cache_clear()

    def test_api_schema_forbids_direct_status_update(self) -> None:
        with self.assertRaises(ValidationError):
            EmailQueueUpdate.model_validate({"status": QueueStatus.APPROVED.value})

    def test_editing_approved_sensitive_draft_resets_approval(self) -> None:
        candidate, _ = self._create_rejection_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")
        self.assertEqual(draft.status, QueueStatus.PENDING_APPROVAL.value)

        self._mark_review_completed(draft)
        approved = approve_email(self.db, draft.id, "reviewer")
        self.assertEqual(approved.status, QueueStatus.APPROVED.value)
        self.assertEqual(approved.approved_by, "reviewer")

        edited = update_email_draft(self.db, draft.id, body=f"{draft.body}\nReviewed wording.")

        self.assertEqual(edited.status, QueueStatus.PENDING_APPROVAL.value)
        self.assertIsNone(edited.approved_by)
        self.assertTrue(edited.risk_check_result["passed"])

    def test_sensitive_draft_cannot_send_without_approval(self) -> None:
        candidate, _ = self._create_rejection_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")

        with self.assertRaisesRegex(HTTPException, "approval"):
            send_email(self.db, draft.id)

        self.assertEqual(draft.status, QueueStatus.PENDING_APPROVAL.value)
        self.assertEqual(self.db.query(EmailHistory).count(), 0)

    def test_approval_preserves_current_async_review_version(self) -> None:
        candidate, _ = self._create_rejection_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")
        risk = dict(draft.risk_check_result)
        metadata = dict(risk["async_review"])
        metadata.update({"status": "COMPLETED", "review_version": risk["draft_version"]})
        risk["async_review"] = metadata
        draft.risk_check_result = risk
        self.db.commit()

        approved = approve_email(self.db, draft.id, "reviewer")

        self.assertEqual(approved.risk_check_result["draft_version"], 1)
        self.assertEqual(approved.risk_check_result["content_hash"], risk["content_hash"])
        self.assertEqual(approved.risk_check_result["async_review"]["status"], "COMPLETED")
        self.assertEqual(approved.risk_check_result["async_review"]["review_version"], 1)

    def test_send_records_history_without_changing_candidate_workflow(self) -> None:
        candidate, _ = self._create_rejection_fixture()
        original_stage = candidate.stage
        original_status = candidate.status
        draft = generate_email_draft(self.db, candidate.id, None, "creator")
        self._mark_review_completed(draft)
        approve_email(self.db, draft.id, "reviewer")

        sent = send_email(self.db, draft.id, "sender")

        self.db.refresh(candidate)
        self.assertEqual(sent.status, QueueStatus.SENT.value)
        self.assertIsNotNone(sent.sent_at)
        self.assertEqual(self.db.query(EmailHistory).count(), 1)
        self.assertEqual(candidate.stage, original_stage)
        self.assertEqual(candidate.status, original_status)

    def test_terminal_sent_state_rejects_all_queue_actions(self) -> None:
        candidate, _ = self._create_interview_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")
        self._mark_review_completed(draft)
        send_email(self.db, draft.id)

        actions = (
            lambda: update_email_draft(self.db, draft.id, subject="Changed"),
            lambda: approve_email(self.db, draft.id),
            lambda: cancel_email(self.db, draft.id),
            lambda: send_email(self.db, draft.id),
        )
        for action in actions:
            with self.subTest(action=action):
                with self.assertRaises(HTTPException) as error:
                    action()
                self.assertEqual(error.exception.status_code, 400)

    def test_send_auto_cancels_older_drafts_of_same_candidate_and_email_type(self) -> None:
        candidate, _ = self._create_interview_fixture()
        old_draft = generate_email_draft(self.db, candidate.id, None, "creator")
        old_approved = generate_email_draft(self.db, candidate.id, None, "creator")
        self._mark_review_completed(old_approved)
        approve_email(self.db, old_approved.id, "reviewer")
        draft_to_send = generate_email_draft(self.db, candidate.id, None, "creator")
        self._mark_review_completed(draft_to_send)

        unrelated_type = EmailQueue(
            candidate_id=candidate.id,
            email_type=EmailType.OFFER_EMAIL.value,
            to_email=candidate.email,
            subject="Offer",
            body="Offer body",
            status=QueueStatus.DRAFT.value,
            requires_hr_approval=False,
            risk_check_result={"passed": True},
        )
        self.db.add(unrelated_type)
        self.db.commit()

        sent = send_email(self.db, draft_to_send.id, "sender")

        self.db.refresh(old_draft)
        self.db.refresh(old_approved)
        self.db.refresh(unrelated_type)
        self.assertEqual(sent.status, QueueStatus.SENT.value)
        self.assertEqual(old_draft.status, QueueStatus.CANCELLED.value)
        self.assertEqual(old_approved.status, QueueStatus.CANCELLED.value)
        self.assertEqual(unrelated_type.status, QueueStatus.DRAFT.value)

        cancellation_audits = (
            self.db.query(AuditLog)
            .filter(AuditLog.action == AUTO_CANCEL_EMAIL)
            .order_by(AuditLog.entity_id)
            .all()
        )
        self.assertEqual(len(cancellation_audits), 2)
        self.assertEqual(
            {audit.metadata_json["previous_status"] for audit in cancellation_audits},
            {QueueStatus.DRAFT.value, QueueStatus.APPROVED.value},
        )
        self.assertTrue(all(
            audit.metadata_json["sent_queue_id"] == sent.id
            for audit in cancellation_audits
        ))
        send_audit = (
            self.db.query(AuditLog)
            .filter(AuditLog.action == SEND_EMAIL, AuditLog.entity_id == sent.id)
            .one()
        )
        self.assertEqual(send_audit.metadata_json["auto_cancelled_count"], 2)

    def test_invalid_edit_keeps_previous_content_and_approval(self) -> None:
        candidate, _ = self._create_rejection_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")
        self._mark_review_completed(draft)
        approve_email(self.db, draft.id, "reviewer")
        original_subject = draft.subject
        original_body = draft.body

        with self.assertRaises(HTTPException) as error:
            update_email_draft(self.db, draft.id, body="Hello {{unresolved_name}}")

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(draft.subject, original_subject)
        self.assertEqual(draft.body, original_body)
        self.assertEqual(draft.status, QueueStatus.APPROVED.value)
        self.assertEqual(draft.approved_by, "reviewer")

    def test_non_sensitive_draft_can_be_simulated_directly(self) -> None:
        candidate, _ = self._create_interview_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")

        self.assertEqual(draft.status, QueueStatus.DRAFT.value)
        self._mark_review_completed(draft)
        sent = send_email(self.db, draft.id)
        self.assertEqual(sent.status, QueueStatus.SENT.value)

    def test_generation_persists_queued_async_review_and_outbox(self) -> None:
        candidate, _ = self._create_interview_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")

        review = draft.risk_check_result["async_review"]
        self.assertEqual(review["status"], "QUEUED")
        self.assertEqual(review["draft_version"], 1)
        self.assertEqual(draft.risk_check_result["draft_version"], 1)
        self.assertEqual(len(draft.risk_check_result["content_hash"]), 64)
        self.assertEqual(draft.status, QueueStatus.DRAFT.value)
        event = self.db.query(OutboxEvent).one()
        self.assertEqual(event.status, OutboxStatus.PENDING.value)
        self.assertEqual(event.aggregate_id, draft.id)
        self.assertEqual(event.payload_json["draft_version"], 1)
        self.assertEqual(event.payload_json["content_hash"], draft.risk_check_result["content_hash"])

    def test_saving_draft_increments_version_and_creates_matching_outbox_event(self) -> None:
        candidate, _ = self._create_interview_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")
        original_hash = draft.risk_check_result["content_hash"]

        updated = update_email_draft(
            self.db,
            draft.id,
            subject="Updated interview subject for Backend Engineer",
        )

        self.assertEqual(updated.risk_check_result["draft_version"], 2)
        self.assertNotEqual(updated.risk_check_result["content_hash"], original_hash)
        events = self.db.query(OutboxEvent).order_by(OutboxEvent.id).all()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1].payload_json, {
            "queue_id": draft.id,
            "draft_version": 2,
            "content_hash": updated.risk_check_result["content_hash"],
        })

    def test_save_and_outbox_are_rolled_back_together(self) -> None:
        candidate, _ = self._create_interview_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")
        original_subject = draft.subject
        original_risk = dict(draft.risk_check_result)

        with patch(
            "app.services.email_workflow.create_review_outbox_event",
            side_effect=RuntimeError("outbox insert failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "outbox insert failed"):
                update_email_draft(
                    self.db,
                    draft.id,
                    subject="Must roll back for Backend Engineer",
                )

        self.db.refresh(draft)
        self.assertEqual(draft.subject, original_subject)
        self.assertEqual(draft.risk_check_result, original_risk)
        self.assertEqual(self.db.query(OutboxEvent).count(), 1)

    def test_explicit_agent_warning_is_advisory_and_resets_queue_for_hr_review(self) -> None:
        candidate, _ = self._create_interview_fixture()
        draft = generate_email_draft(self.db, candidate.id, None, "creator")
        original_subject = draft.subject
        original_body = draft.body
        fake_agent = StaticReviewAgent(
            AgentReviewResult(
                status=AgentReviewStatus.COMPLETED,
                draft_subject="Suggested safer subject",
                draft_body="Suggested safer body",
                issues=[
                    AgentSemanticIssue(
                        rule_id="AI_SEMANTIC_MISMATCH",
                        severity=IssueSeverity.WARNING,
                        message="The call to action is ambiguous.",
                        evidence="The draft does not state how to confirm attendance.",
                        requires_human_review=True,
                    )
                ],
                uncertainty=AgentUncertainty(has_uncertainty=False),
                review_summary="HR should review the call to action.",
                requires_human_review=True,
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
        )

        result = review_queue_draft(
            self.db,
            draft.id,
            actor="reviewer",
            agent=fake_agent,
        )

        self.db.refresh(draft)
        self.assertEqual(result.status, AgentReviewStatus.COMPLETED)
        self.assertEqual(draft.subject, original_subject)
        self.assertEqual(draft.body, original_body)
        self.assertEqual(draft.status, QueueStatus.PENDING_APPROVAL.value)
        self.assertTrue(draft.requires_hr_approval)
        self.assertEqual(
            draft.risk_check_result["agent_review"]["issues"][0]["rule_id"],
            "AI_SEMANTIC_MISMATCH",
        )

        audit = (
            self.db.query(AuditLog)
            .filter(AuditLog.action == AGENT_REVIEW_EMAIL, AuditLog.actor == "reviewer")
            .one()
        )
        self.assertEqual(audit.metadata_json["issue_count"], 1)
        self.assertNotIn(candidate.email, str(audit.metadata_json))
        self.assertNotIn(original_body, str(audit.metadata_json))

    def _create_rejection_fixture(self) -> tuple[Candidate, EmailTemplate]:
        return self._create_fixture(
            candidate_status=CandidateStatus.REJECT_CV.value,
            candidate_stage="CV_SCREENING",
            email_type=EmailType.REJECTION_AFTER_CV.value,
            is_sensitive=True,
            subject="Application update for {{position}}",
            body="Hello {{candidate_name}}, your application for {{position}} will not proceed.",
            required_placeholders=["candidate_name", "position"],
        )

    def _create_interview_fixture(self) -> tuple[Candidate, EmailTemplate]:
        return self._create_fixture(
            candidate_status=CandidateStatus.PASS_CV.value,
            candidate_stage="CV_SCREENING",
            email_type=EmailType.INTERVIEW_INVITATION.value,
            is_sensitive=False,
            subject="Interview for {{position}}",
            body="Hello {{candidate_name}}, meet {{interviewer}} at {{interview_time}}.",
            required_placeholders=["candidate_name", "position", "interviewer", "interview_time"],
        )

    def _mark_review_completed(self, draft: EmailQueue) -> None:
        risk = dict(draft.risk_check_result)
        metadata = dict(risk["async_review"])
        metadata.update(
            {
                "status": "COMPLETED",
                "review_version": risk["draft_version"],
            }
        )
        risk["async_review"] = metadata
        draft.risk_check_result = risk
        self.db.commit()

    def _create_fixture(
        self,
        *,
        candidate_status: str,
        candidate_stage: str,
        email_type: str,
        is_sensitive: bool,
        subject: str,
        body: str,
        required_placeholders: list[str],
    ) -> tuple[Candidate, EmailTemplate]:
        candidate = Candidate(
            application_id=f"TEST-{uuid4()}",
            full_name="Nguyen Demo",
            email="demo@example.com",
            position="Backend Engineer",
            stage=candidate_stage,
            status=candidate_status,
            interview_time=datetime(2026, 8, 7, 9, 0, tzinfo=timezone.utc),
            interviewer="HR Demo",
        )
        template = EmailTemplate(
            name=f"Template {email_type}",
            email_type=email_type,
            subject=subject,
            body=body,
            required_placeholders=required_placeholders,
            is_sensitive=is_sensitive,
        )
        self.db.add_all([candidate, template])
        self.db.commit()
        self.db.refresh(candidate)
        self.db.refresh(template)
        return candidate, template


if __name__ == "__main__":
    unittest.main()
