"""Run the real Gemini integration through draft generation using synthetic in-memory data."""

import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.constants.auditActions import AGENT_REVIEW_EMAIL
from app.core.config import get_settings
from app.db.database import Base
from app.models import AuditLog, Candidate, CandidateStatus, EmailTemplate, EmailType
from app.services.email_workflow import generate_email_draft


def main() -> None:
    settings = get_settings()
    if not settings.gemini_is_configured:
        raise SystemExit(
            "Gemini is not ready. Set GEMINI_AGENT_ENABLED=true and configure GEMINI_API_KEY."
        )

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()
    try:
        candidate = Candidate(
            full_name="Workflow Demo",
            email="workflow-demo@example.com",
            position="Backend Engineer",
            stage="CV_SCREENING",
            status=CandidateStatus.PASS_CV.value,
            interview_time=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
            interviewer="HR Demo",
        )
        template = EmailTemplate(
            name="Synthetic interview invitation",
            email_type=EmailType.INTERVIEW_INVITATION.value,
            subject="Interview invitation for {{position}}",
            body="Hello {{candidate_name}}, please meet {{interviewer}} at {{interview_time}}.",
            required_placeholders=["candidate_name", "position", "interviewer", "interview_time"],
            is_sensitive=False,
        )
        db.add_all([candidate, template])
        db.commit()

        draft = generate_email_draft(db, candidate.id, None, "smoke_test")
        agent_review = draft.risk_check_result["agent_review"]
        audit_count = (
            db.query(AuditLog)
            .filter(AuditLog.action == AGENT_REVIEW_EMAIL)
            .count()
        )
        print(
            json.dumps(
                {
                    "queue_status": draft.status,
                    "deterministic_passed": draft.risk_check_result["passed"],
                    "agent_status": agent_review["status"],
                    "semantic_review_available": agent_review["semantic_review_available"],
                    "requires_hr_approval": draft.requires_hr_approval,
                    "agent_audit_count": audit_count,
                },
                indent=2,
            )
        )
        if agent_review["status"] != "completed" or audit_count != 1:
            raise SystemExit(1)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


if __name__ == "__main__":
    main()
