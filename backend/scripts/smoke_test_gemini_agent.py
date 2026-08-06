"""Run one synthetic Gemini review without touching the database or email workflow."""

from app.agents import RecruitmentEmailAgent
from app.core.config import get_settings
from app.schemas.agent import (
    AgentCandidateFacts,
    AgentDraftInput,
    AgentReviewRequest,
    AgentReviewStatus,
    AgentTemplateInput,
)
from app.schemas.validation import ValidationResult


def main() -> None:
    settings = get_settings()
    if not settings.gemini_is_configured:
        raise SystemExit(
            "Gemini is not ready. Set GEMINI_AGENT_ENABLED=true and configure GEMINI_API_KEY."
        )

    request = AgentReviewRequest(
        candidate=AgentCandidateFacts(
            full_name="Nguyen Demo",
            position="Backend Engineer",
            status="PASS_CV",
            interview_time="2026-08-10T09:00:00+07:00",
            interviewer="HR Demo",
        ),
        email_type="INTERVIEW_INVITATION",
        template=AgentTemplateInput(
            name="Synthetic interview invitation",
            email_type="INTERVIEW_INVITATION",
            subject="Interview invitation for Backend Engineer",
            body="Hello Nguyen Demo, please meet HR Demo on 2026-08-10 at 09:00.",
            is_sensitive=False,
        ),
        draft=AgentDraftInput(
            subject="Interview invitation for Backend Engineer",
            body="Hello Nguyen Demo, please meet HR Demo on 2026-08-10 at 09:00.",
        ),
        deterministic_validation=ValidationResult.from_issues([]),
        company_policy=["HR remains the final decision-maker."],
    )
    result = RecruitmentEmailAgent(settings=settings).review(request)
    print(result.model_dump_json(indent=2))
    if result.status != AgentReviewStatus.COMPLETED:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
