import json
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.emailQueueRoutes import get_review_redis
from app.db.database import Base, get_db
from app.main import create_app
from app.models import Candidate, CandidateStatus, EmailQueue, EmailType, QueueStatus
from app.services.review_progress import review_progress_key


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str):
        return self.values.get(key)


class ReviewProgressApiTest(unittest.TestCase):
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
        with self.engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())

        self.redis = FakeRedis()
        app = create_app()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_review_redis] = lambda: self.redis
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_queue_detail_merges_matching_live_redis_progress(self) -> None:
        db = self.SessionLocal()
        try:
            candidate = Candidate(
                application_id="TEST-POLLING-001",
                full_name="Polling Demo",
                email="polling@example.com",
                position="Backend Engineer",
                stage="CV_SCREENING",
                status=CandidateStatus.PASS_CV.value,
            )
            db.add(candidate)
            db.flush()
            queue_item = EmailQueue(
                candidate_id=candidate.id,
                email_type=EmailType.INTERVIEW_INVITATION.value,
                to_email=candidate.email,
                subject="Interview",
                body="Hello",
                status=QueueStatus.DRAFT.value,
                risk_check_result={
                    "passed": True,
                    "draft_version": 2,
                    "content_hash": "hash-v2",
                    "async_review": {
                        "status": "QUEUED",
                        "draft_version": 2,
                        "content_hash": "hash-v2",
                    },
                },
            )
            db.add(queue_item)
            db.commit()
            queue_id = queue_item.id
        finally:
            db.close()

        self.redis.values[review_progress_key(queue_id, 2)] = json.dumps(
            {
                "queue_id": queue_id,
                "draft_version": 2,
                "status": "REVIEWING",
                "updated_at": "2026-08-06T15:30:00+00:00",
            }
        )

        response = self.client.get(f"/email-queue/{queue_id}")

        self.assertEqual(response.status_code, 200, response.text)
        metadata = response.json()["risk_check_result"]["async_review"]
        self.assertEqual(metadata["status"], "REVIEWING")
        self.assertEqual(metadata["draft_version"], 2)
        self.assertEqual(metadata["content_hash"], "hash-v2")


if __name__ == "__main__":
    unittest.main()
