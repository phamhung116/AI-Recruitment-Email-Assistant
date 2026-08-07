from app.agents.prompt_registry import PROMPT_VERSION, load_recruitment_email_system_prompt
from app.agents.review_loop import (
    AgentLoopError,
    StructuredReviewProvider,
    run_agent_loop,
)
from app.core.config import Settings, get_settings
from app.schemas.agent import (
    AgentModelMetadata,
    AgentModelOutput,
    AgentReviewRequest,
    AgentReviewResult,
    AgentReviewStatus,
    AgentTraceStep,
    AgentUncertainty,
)
from app.schemas.validation import IssueSeverity
from app.services.gemini_provider import GeminiAgentProvider
from app.services.rules import SENSITIVE_EMAIL_TYPES
from app.services.skill_loader import SkillBundle, SkillLoader


SKILL_NAME = "recruitment-email-review"
MAX_INPUT_BYTES = 32 * 1024


class RecruitmentEmailAgent:
    def __init__(
        self,
        provider: StructuredReviewProvider | None = None,
        settings: Settings | None = None,
        skill_loader: SkillLoader | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider = provider or GeminiAgentProvider(self.settings)
        self.skill_loader = skill_loader or SkillLoader()

    def review(self, request: AgentReviewRequest) -> AgentReviewResult:
        trace: list[AgentTraceStep] = []
        try:
            system_prompt = load_recruitment_email_system_prompt()
            skill = self.skill_loader.load(SKILL_NAME)
        except Exception as error:
            return self._unavailable(
                request=request,
                skill=None,
                attempts=0,
                trace=trace,
                reason=f"Agent instructions unavailable ({type(error).__name__}).",
            )

        trace.append(AgentTraceStep(step="load_instructions", status="completed", detail="Prompt and domain skill loaded."))

        if any(issue.is_blocking for issue in request.deterministic_validation.issues):
            trace.append(
                AgentTraceStep(
                    step="deterministic_gate",
                    status="blocked",
                    detail="Semantic model call skipped because deterministic blockers are final.",
                )
            )
            return AgentReviewResult(
                status=AgentReviewStatus.DETERMINISTIC_BLOCKED,
                draft_subject=request.draft.subject,
                draft_body=request.draft.body,
                issues=[],
                uncertainty=AgentUncertainty(has_uncertainty=False),
                review_summary="Resolve deterministic blockers before semantic review.",
                requires_human_review=True,
                semantic_review_available=False,
                model_metadata=self._metadata(skill, attempts=0),
                trace=trace,
            )

        trace.append(AgentTraceStep(step="deterministic_gate", status="completed", detail="No deterministic blocker found."))

        if not self.settings.gemini_agent_enabled:
            trace.append(
                AgentTraceStep(
                    step="model_review",
                    status="disabled",
                    detail="Gemini semantic review is disabled by configuration.",
                )
            )
            deterministic_review_needed = any(
                issue.severity != IssueSeverity.INFO
                for issue in request.deterministic_validation.issues
            )
            requires_human_review = (
                deterministic_review_needed
                or request.template.is_sensitive
                or request.email_type in SENSITIVE_EMAIL_TYPES
            )
            return AgentReviewResult(
                status=AgentReviewStatus.DISABLED,
                draft_subject=request.draft.subject,
                draft_body=request.draft.body,
                issues=[],
                uncertainty=AgentUncertainty(has_uncertainty=False),
                review_summary="Gemini semantic review is disabled by configuration.",
                requires_human_review=requires_human_review,
                semantic_review_available=False,
                model_metadata=self._metadata(skill, attempts=0),
                trace=trace,
            )

        request_json = request.model_dump_json(indent=2)
        if len(request_json.encode("utf-8")) > MAX_INPUT_BYTES:
            return self._unavailable(
                request=request,
                skill=skill,
                attempts=0,
                trace=trace,
                reason="Bounded agent input exceeds the configured size limit.",
            )

        system_instruction = f"{system_prompt}\n\n{skill.as_context()}"
        try:
            loop_result = run_agent_loop(
                provider=self.provider,
                request=request,
                system_instruction=system_instruction,
                max_steps=self.settings.gemini_effective_agent_steps,
            )
        except AgentLoopError as error:
            trace.extend(error.trace)
            return self._unavailable(
                request=request,
                skill=skill,
                attempts=error.model_calls,
                loop_steps=error.loop_steps,
                tool_calls=error.tool_calls,
                trace=trace,
                reason=error.reason,
            )

        trace.extend(loop_result.trace)
        return self._completed(
            request,
            loop_result.output,
            skill,
            loop_result.model_calls,
            trace,
            loop_steps=loop_result.loop_steps,
            tool_calls=loop_result.tool_calls,
            tool_requires_human_review=loop_result.tool_requires_human_review,
        )

    def _completed(
        self,
        request: AgentReviewRequest,
        output: AgentModelOutput,
        skill: SkillBundle,
        attempts: int,
        trace: list[AgentTraceStep],
        *,
        loop_steps: int,
        tool_calls: int,
        tool_requires_human_review: bool,
    ) -> AgentReviewResult:
        deterministic_review_needed = any(
            issue.severity != IssueSeverity.INFO
            for issue in request.deterministic_validation.issues
        )
        requires_human_review = (
            deterministic_review_needed
            or request.template.is_sensitive
            or request.email_type in SENSITIVE_EMAIL_TYPES
            or output.uncertainty.has_uncertainty
            or any(issue.requires_human_review for issue in output.issues)
            or tool_requires_human_review
        )
        return AgentReviewResult(
            status=AgentReviewStatus.COMPLETED,
            draft_subject=output.draft_subject,
            draft_body=output.draft_body,
            issues=output.issues,
            uncertainty=output.uncertainty,
            review_summary=output.review_summary,
            requires_human_review=requires_human_review,
            semantic_review_available=True,
            model_metadata=self._metadata(skill, attempts, loop_steps, tool_calls),
            trace=trace,
        )

    def _unavailable(
        self,
        *,
        request: AgentReviewRequest,
        skill: SkillBundle | None,
        attempts: int,
        trace: list[AgentTraceStep],
        reason: str,
        loop_steps: int = 0,
        tool_calls: int = 0,
    ) -> AgentReviewResult:
        trace.append(AgentTraceStep(step="fallback", status="completed", detail=reason))
        return AgentReviewResult(
            status=AgentReviewStatus.UNAVAILABLE,
            draft_subject=request.draft.subject,
            draft_body=request.draft.body,
            issues=[],
            uncertainty=AgentUncertainty(has_uncertainty=True, reason=reason),
            review_summary=reason,
            requires_human_review=True,
            semantic_review_available=False,
            model_metadata=self._metadata(skill, attempts, loop_steps, tool_calls),
            trace=trace,
        )

    def _metadata(
        self,
        skill: SkillBundle | None,
        attempts: int,
        loop_steps: int = 0,
        tool_calls: int = 0,
    ) -> AgentModelMetadata:
        return AgentModelMetadata(
            provider=getattr(self.provider, "provider_name", "unknown"),
            model=getattr(self.provider, "model", "unknown"),
            prompt_version=PROMPT_VERSION,
            skill_name=skill.name if skill else SKILL_NAME,
            skill_version=skill.version if skill else "unavailable",
            attempts=attempts,
            loop_steps=loop_steps,
            tool_calls=tool_calls,
        )
