"""Run a synthetic end-to-end review through real Gemini, RabbitMQ, and Redis."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SMOKE_ROOT = BACKEND_ROOT / ".e2e"
SMOKE_DATABASE = SMOKE_ROOT / "gemini-pipeline-smoke.sqlite3"


def main() -> None:
    SMOKE_ROOT.mkdir(exist_ok=True)
    if SMOKE_DATABASE.exists():
        SMOKE_DATABASE.unlink()
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{SMOKE_DATABASE.as_posix()}"

    from redis import Redis

    from app.core.config import get_settings
    from app.db.database import Base, SessionLocal, engine
    from app.models import Candidate, CandidateStatus, EmailQueue, EmailTemplate, EmailType, OutboxEvent
    from app.services.email_workflow import generate_email_draft
    from app.services.outbox_dispatcher import dispatch_pending_events
    from app.services.review_progress import review_lock_key, review_progress_key

    settings = get_settings()
    if not settings.gemini_is_configured:
        raise RuntimeError("Gemini smoke requires GEMINI_AGENT_ENABLED=true and a server-side GEMINI_API_KEY.")

    run_id = uuid4().hex[:8]
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    worker = None
    redis_client = None
    queue_id = draft_version = content_hash = None
    try:
        candidate = Candidate(
            full_name=f"Gemini Smoke {run_id}",
            email=f"gemini-{run_id}@example.com",
            position="Backend Engineer",
            stage="CV_SCREENING",
            status=CandidateStatus.PASS_CV.value,
            interview_time=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
            interviewer="HR Demo",
            note="Synthetic smoke-test record only.",
        )
        template = EmailTemplate(
            name="Gemini smoke interview template",
            email_type=EmailType.INTERVIEW_INVITATION.value,
            subject="Interview for {{position}}",
            body="Hello {{candidate_name}}, meet {{interviewer}} at {{interview_time}}.",
            required_placeholders=["candidate_name", "position", "interviewer", "interview_time"],
            is_sensitive=False,
        )
        db.add_all([candidate, template])
        db.commit()
        draft = generate_email_draft(db, candidate.id, None, "gemini_smoke")
        queue_id = draft.id
        draft_version = draft.risk_check_result["draft_version"]
        content_hash = draft.risk_check_result["content_hash"]

        worker_environment = os.environ.copy()
        worker_environment["PYTHONUNBUFFERED"] = "1"
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        worker = subprocess.Popen(
            [
                sys.executable, "-m", "celery", "-A", "app.messaging.celery_app:celery_app",
                "worker", "--pool=solo", "--loglevel=WARNING", "--queues=email_review",
                f"--hostname=gemini-smoke-{run_id}@%h",
            ],
            cwd=BACKEND_ROOT,
            env=worker_environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        time.sleep(3)
        summary = dispatch_pending_events()
        if summary.published != 1:
            raise RuntimeError(f"Expected one published event, got {summary.published}.")

        deadline = time.monotonic() + 120
        final_status = None
        while time.monotonic() < deadline:
            db.expire_all()
            current = db.get(EmailQueue, queue_id)
            final_status = current.risk_check_result["async_review"]["status"]
            if final_status in {"COMPLETED", "UNAVAILABLE", "FAILED", "STALE"}:
                break
            time.sleep(0.5)
        if final_status != "COMPLETED":
            raise RuntimeError(f"Expected real Gemini review COMPLETED, got {final_status}.")

        current = db.get(EmailQueue, queue_id)
        review = current.risk_check_result["agent_review"]
        event = db.query(OutboxEvent).one()
        print(json.dumps({
            "outbox_status": event.status,
            "queue_id": queue_id,
            "draft_version": draft_version,
            "review_status": final_status,
            "provider": review["model_metadata"]["provider"],
            "model": review["model_metadata"]["model"],
            "attempts": review["model_metadata"]["attempts"],
            "loop_steps": review["model_metadata"]["loop_steps"],
            "tool_calls": review["model_metadata"]["tool_calls"],
            "trace_steps": [step["step"] for step in review["trace"]],
            "issue_count": len(review["issues"]),
        }, indent=2))
    finally:
        db.close()
        if worker is not None:
            worker.terminate()
            try:
                worker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)
        if queue_id is not None and draft_version is not None:
            redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
            redis_client.delete(review_progress_key(queue_id, draft_version))
            if content_hash is not None:
                redis_client.delete(review_lock_key(queue_id, draft_version, content_hash))
            redis_client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if SMOKE_DATABASE.exists():
            SMOKE_DATABASE.unlink()


if __name__ == "__main__":
    main()
