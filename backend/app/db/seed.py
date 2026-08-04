from datetime import datetime, timedelta, timezone

from app.db.database import Base, SessionLocal, engine
from app.models import Candidate, EmailQueue, EmailTemplate, EmailType, QueueStatus


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_candidates(db)

        existing_types = {row.email_type for row in db.query(EmailTemplate).all()}
        templates = [
            EmailTemplate(
                name="Interview Invitation",
                email_type=EmailType.INTERVIEW_INVITATION.value,
                subject="Interview invitation for {{position}} at HiLab",
                body="Hi {{candidate_name}},\n\nThank you for applying for {{position}}. We would like to invite you to an interview at {{interview_time}} with {{interviewer}}.\n\nBest regards,\nHiLab HR",
                required_placeholders=["candidate_name", "position", "interview_time", "interviewer"],
                is_sensitive=False,
            ),
            EmailTemplate(
                name="Rejection After CV",
                email_type=EmailType.REJECTION_AFTER_CV.value,
                subject="Update on your application for {{position}}",
                body="Hi {{candidate_name}},\n\nThank you for your interest in {{position}}. After reviewing your CV, we will not move forward at this time. We appreciate your time and wish you the best.\n\nHiLab HR",
                required_placeholders=["candidate_name", "position"],
                is_sensitive=True,
            ),
            EmailTemplate(
                name="Interview Reminder",
                email_type=EmailType.INTERVIEW_REMINDER.value,
                subject="Reminder: interview for {{position}}",
                body="Hi {{candidate_name}},\n\nThis is a reminder for your interview for {{position}} at {{interview_time}} with {{interviewer}}.\n\nSee you soon,\nHiLab HR",
                required_placeholders=["candidate_name", "position", "interview_time", "interviewer"],
                is_sensitive=False,
            ),
            EmailTemplate(
                name="Offer Email",
                email_type=EmailType.OFFER_EMAIL.value,
                subject="Offer for {{position}}",
                body="Hi {{candidate_name}},\n\nCongratulations. We are excited to offer you the {{position}} role. Our HR team will contact you with the next details.\n\nHiLab HR",
                required_placeholders=["candidate_name", "position"],
                is_sensitive=True,
            ),
            EmailTemplate(
                name="Onboarding Email",
                email_type=EmailType.ONBOARDING_EMAIL.value,
                subject="Welcome to HiLab",
                body="Hi {{candidate_name}},\n\nWelcome aboard. We will share onboarding information for your {{position}} role shortly.\n\nHiLab HR",
                required_placeholders=["candidate_name", "position"],
                is_sensitive=False,
            ),
        ]
        db.add_all([template for template in templates if template.email_type not in existing_types])

        if db.query(EmailQueue).count() == 0:
            candidate_by_email = {
                candidate.email: candidate
                for candidate in db.query(Candidate).all()
                if candidate.email
            }
            minh_an = candidate_by_email.get("an.nguyen@example.com")
            bao_chau = candidate_by_email.get("chau.tran@example.com")
            hoang_ngan = candidate_by_email.get("ngan.hoang@example.com")

            queue_items = []
            if minh_an:
                queue_items.append(
                    EmailQueue(
                        candidate_id=minh_an.id,
                        email_type=EmailType.INTERVIEW_INVITATION.value,
                        to_email=minh_an.email,
                        subject="Interview invitation for Frontend Developer at HiLab",
                        body="Hi Nguyen Minh An,\n\nWe would like to invite you to an interview for Frontend Developer.\n\nHiLab HR",
                        status=QueueStatus.DRAFT.value,
                        requires_hr_approval=False,
                        risk_check_result={"passed": True, "errors": [], "source": "seed"},
                        created_by="seed_hr",
                    )
                )
            if bao_chau:
                queue_items.append(
                    EmailQueue(
                        candidate_id=bao_chau.id,
                        email_type=EmailType.REJECTION_AFTER_CV.value,
                        to_email=bao_chau.email,
                        subject="Update on your application for Backend Developer",
                        body="Hi Tran Bao Chau,\n\nThank you for your interest. We will not move forward at this time.\n\nHiLab HR",
                        status=QueueStatus.PENDING_APPROVAL.value,
                        requires_hr_approval=True,
                        risk_check_result={"passed": True, "errors": [], "source": "seed"},
                        created_by="seed_hr",
                    )
                )
            if hoang_ngan:
                queue_items.append(
                    EmailQueue(
                        candidate_id=hoang_ngan.id,
                        email_type=EmailType.OFFER_EMAIL.value,
                        to_email=hoang_ngan.email,
                        subject="Offer for Product Designer",
                        body="Hi Hoang Kim Ngan,\n\nCongratulations. We are excited to offer you the Product Designer role.\n\nHiLab HR",
                        status=QueueStatus.APPROVED.value,
                        requires_hr_approval=True,
                        risk_check_result={"passed": True, "errors": [], "source": "seed"},
                        created_by="seed_hr",
                        approved_by="demo_hr",
                    )
                )

            db.add_all(queue_items)

        db.commit()
    finally:
        db.close()


def seed_candidates(db) -> None:
    existing_emails = {
        candidate.email
        for candidate in db.query(Candidate).all()
        if candidate.email
    }
    sample_candidates = [
        Candidate(full_name="Nguyen Minh An", email="an.nguyen@example.com", phone="0901000001", position="Frontend Developer", stage="CV_SCREENING", status="PASS_CV", interview_time=datetime.now(timezone.utc) + timedelta(days=2), interviewer="Linh Tran", note="Strong React profile"),
        Candidate(full_name="Tran Bao Chau", email="chau.tran@example.com", phone="0901000002", position="Backend Developer", stage="CV_SCREENING", status="REJECT_CV", note="Not enough Python experience"),
        Candidate(full_name="Le Hoang Nam", email="nam.le@example.com", phone="0901000003", position="Data Analyst", stage="INTERVIEW", status="INTERVIEW_CONFIRMED", interview_time=datetime.now(timezone.utc) + timedelta(days=1), interviewer="Quang Pham"),
        Candidate(full_name="Pham Thu Ha", email="ha.pham@example.com", phone="0901000004", position="HR Intern", stage="OFFER", status="OFFER_ACCEPTED"),
        Candidate(full_name="Do Gia Bao", email=None, phone="0901000005", position="QA Engineer", stage="NEW", status="PENDING"),
        Candidate(full_name="Hoang Kim Ngan", email="ngan.hoang@example.com", phone="0901000006", position="Product Designer", stage="INTERVIEW", status="PASS_INTERVIEW", interview_time=datetime.now(timezone.utc) + timedelta(days=3), interviewer="Mai Nguyen", note="Portfolio is polished and enterprise focused"),
        Candidate(full_name="Vo Thanh Dat", email="dat.vo@example.com", phone="0901000007", position="DevOps Engineer", stage="CV_SCREENING", status="PASS_CV", interview_time=datetime.now(timezone.utc) + timedelta(days=4), interviewer="Khoa Le", note="Strong cloud and CI/CD background"),
        Candidate(full_name="Bui Anh Thu", email="thu.bui@example.com", phone="0901000008", position="Business Analyst", stage="INTERVIEW", status="REJECT_INTERVIEW", interview_time=datetime.now(timezone.utc) - timedelta(days=1), interviewer="Anh Pham", note="Communication is good but domain fit is limited"),
        Candidate(full_name="Dang Quoc Huy", email="huy.dang@example.com", phone="0901000009", position="AI Engineer", stage="NEW", status="PENDING", note="Needs initial screening"),
        Candidate(full_name="Mai Phuong Linh", email="linh.mai@example.com", phone="0901000010", position="Backend Developer", stage="OFFER", status="PASS_INTERVIEW", interviewer="Quang Pham", note="Ready for offer discussion"),
        Candidate(full_name="Nguyen Khanh Vy", email="vy.nguyen@example.com", phone="0901000011", position="Recruitment Specialist", stage="CV_SCREENING", status="PASS_CV", interview_time=datetime.now(timezone.utc) + timedelta(days=5), interviewer="Thu Nguyen", note="Good HR operations background"),
        Candidate(full_name="Tran Duc Minh", email="minh.tran@example.com", phone="0901000012", position="Full-stack Developer", stage="INTERVIEW", status="INTERVIEW_CONFIRMED", interview_time=datetime.now(timezone.utc) + timedelta(days=2, hours=3), interviewer="Khoa Le", note="Balanced React and FastAPI experience"),
        Candidate(full_name="Le My Duyen", email="duyen.le@example.com", phone="0901000013", position="QA Engineer", stage="CV_SCREENING", status="REJECT_CV", note="Automation experience does not match current role"),
        Candidate(full_name="Pham Gia Huy", email="giahuy.pham@example.com", phone="0901000014", position="AI Engineer", stage="INTERVIEW", status="PASS_INTERVIEW", interview_time=datetime.now(timezone.utc) - timedelta(days=2), interviewer="Long Vu", note="Strong LLM application experience"),
        Candidate(full_name="Do Thien An", email="thienan.do@example.com", phone="0901000015", position="Project Manager", stage="NEW", status="PENDING", note="Awaiting HR review"),
    ]
    missing_candidates = [
        candidate
        for candidate in sample_candidates
        if not candidate.email or candidate.email not in existing_emails
    ]

    if missing_candidates:
        db.add_all(missing_candidates)
        db.commit()


if __name__ == "__main__":
    seed()
    print("Seed data created.")
