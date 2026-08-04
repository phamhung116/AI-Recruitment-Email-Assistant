from abc import ABC, abstractmethod
from datetime import datetime

from app.models import Candidate, EmailTemplate


class AIEmailService(ABC):
    @abstractmethod
    def generate(self, candidate: Candidate, template: EmailTemplate, email_type: str) -> tuple[str, str]:
        raise NotImplementedError


class MockAIEmailService(AIEmailService):
    def generate(self, candidate: Candidate, template: EmailTemplate, email_type: str) -> tuple[str, str]:
        values = {
            "full_name": candidate.full_name or "",
            "candidate_name": candidate.full_name or "",
            "email": candidate.email or "",
            "phone": candidate.phone or "",
            "position": candidate.position or "",
            "stage": candidate.stage or "",
            "status": candidate.status or "",
            "interview_time": self._format_dt(candidate.interview_time),
            "interviewer": candidate.interviewer or "",
            "note": candidate.note or "",
            "email_type": email_type,
        }
        return self._fill(template.subject, values), self._fill(template.body, values)

    @staticmethod
    def _format_dt(value: datetime | None) -> str:
        return value.strftime("%Y-%m-%d %H:%M") if value else ""

    @staticmethod
    def _fill(text: str, values: dict[str, str]) -> str:
        rendered = text
        for key, value in values.items():
            rendered = rendered.replace("{{" + key + "}}", value)
        return rendered


def get_ai_email_service() -> AIEmailService:
    return MockAIEmailService()
