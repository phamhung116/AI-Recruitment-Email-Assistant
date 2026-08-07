from pathlib import Path


PROMPT_VERSION = "semantic_review.v2"
MAX_PROMPT_BYTES = 32 * 1024


class PromptLoadError(RuntimeError):
    """Raised when a versioned agent prompt cannot be loaded safely."""


def load_recruitment_email_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent / "prompts" / "recruitment_email_system.md"
    if not prompt_path.is_file():
        raise PromptLoadError("Recruitment email system prompt is missing.")
    if prompt_path.stat().st_size > MAX_PROMPT_BYTES:
        raise PromptLoadError("Recruitment email system prompt exceeds the size limit.")

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise PromptLoadError("Recruitment email system prompt is empty.")
    return prompt
