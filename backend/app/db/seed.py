"""Seed candidate applications after Alembic has created the target schema."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.database import SessionLocal
from app.models import Candidate


def seed() -> None:
    with SessionLocal() as db:
        seed_candidates(db)
        db.commit()


def seed_candidates(db) -> None:
    existing_application_ids = {
        application_id
        for (application_id,) in db.query(Candidate.application_id).all()
    }
    candidates = sample_candidates()
    db.add_all(
        candidate
        for candidate in candidates
        if candidate.application_id not in existing_application_ids
    )


def sample_candidates() -> list[Candidate]:
    now = datetime.now(timezone.utc)
    return [
        Candidate(application_id="DEMO-2026-001", full_name="Nguyen Minh An", email="an.nguyen@example.com", phone="0901000001", position="Frontend Developer", stage="CV_SCREENING", status="PASS_CV", interview_time=now + timedelta(days=2), interviewer="Linh Tran", note="Strong React profile"),
        Candidate(application_id="DEMO-2026-002", full_name="Tran Bao Chau", email="chau.tran@example.com", phone="0901000002", position="Backend Developer", stage="CV_SCREENING", status="REJECT_CV", note="Not enough Python experience"),
        Candidate(application_id="DEMO-2026-003", full_name="Le Hoang Nam", email="nam.le@example.com", phone="0901000003", position="Data Analyst", stage="INTERVIEW", status="REJECT_INTERVIEW", interview_time=now - timedelta(days=1), interviewer="Quang Pham"),
        Candidate(application_id="DEMO-2026-004", full_name="Pham Thu Ha", email="ha.pham@example.com", phone="0901000004", position="HR Specialist", stage="INTERVIEW", status="PASS_INTERVIEW"),
        Candidate(application_id="DEMO-2026-005", full_name="Do Gia Bao", email="gia.bao@example.com", phone="0901000005", position="QA Engineer", stage="CV_SCREENING", status="PENDING"),
        Candidate(application_id="DEMO-2026-006", full_name="Hoang Kim Ngan", email="ngan.hoang@example.com", phone="0901000006", position="Product Designer", stage="INTERVIEW", status="PASS_INTERVIEW"),
        Candidate(application_id="DEMO-2026-007", full_name="Vo Thanh Dat", email="dat.vo@example.com", phone="0901000007", position="DevOps Engineer", stage="CV_SCREENING", status="PASS_CV"),
        Candidate(application_id="DEMO-2026-008", full_name="Bui Anh Thu", email="thu.bui@example.com", phone="0901000008", position="Business Analyst", stage="INTERVIEW", status="REJECT_INTERVIEW"),
        Candidate(application_id="DEMO-2026-009", full_name="Dang Quoc Huy", email="huy.dang@example.com", phone="0901000009", position="AI Engineer", stage="CV_SCREENING", status="PENDING"),
        Candidate(application_id="DEMO-2026-010", full_name="Mai Phuong Linh", email="linh.mai@example.com", phone="0901000010", position="Backend Developer", stage="INTERVIEW", status="PASS_INTERVIEW"),
        Candidate(application_id="DEMO-2026-011", full_name="Nguyen Khanh Vy", email="vy.nguyen@example.com", phone="0901000011", position="Recruitment Specialist", stage="CV_SCREENING", status="PASS_CV"),
        Candidate(application_id="DEMO-2026-012", full_name="Tran Duc Minh", email="minh.tran@example.com", phone="0901000012", position="Full-stack Developer", stage="INTERVIEW", status="REJECT_INTERVIEW"),
        Candidate(application_id="DEMO-2026-013", full_name="Le My Duyen", email="duyen.le@example.com", phone="0901000013", position="QA Engineer", stage="CV_SCREENING", status="REJECT_CV"),
        Candidate(application_id="DEMO-2026-014", full_name="Pham Gia Huy", email="giahuy.pham@example.com", phone="0901000014", position="AI Engineer", stage="INTERVIEW", status="PASS_INTERVIEW"),
        Candidate(application_id="DEMO-2026-015", full_name="Do Thien An", email="thienan.do@example.com", phone="0901000015", position="Project Manager", stage="CV_SCREENING", status="PENDING"),
    ]


if __name__ == "__main__":
    seed()
    print("Candidate seed data created.")
