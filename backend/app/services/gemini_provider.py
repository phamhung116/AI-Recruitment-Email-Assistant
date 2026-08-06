from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel

from app.core.config import Settings, get_settings


SUPPORTED_GEMINI_JSON_SCHEMA_KEYS = {
    "$anchor",
    "$defs",
    "$id",
    "$ref",
    "additionalProperties",
    "anyOf",
    "description",
    "enum",
    "format",
    "items",
    "maximum",
    "maxItems",
    "minimum",
    "minItems",
    "oneOf",
    "prefixItems",
    "properties",
    "propertyOrdering",
    "required",
    "title",
    "type",
}


class GeminiConfigurationError(RuntimeError):
    """Raised when Gemini is requested without a complete server-side configuration."""


class GeminiProviderError(RuntimeError):
    """Raised when Gemini cannot produce a usable response."""

    def __init__(self, message: str, category: str = "provider_error") -> None:
        super().__init__(message)
        self.category = category


class GeminiAgentProvider:
    provider_name = "gemini"

    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[[str, float], Any] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client_factory = client_factory or _create_google_genai_client

    @property
    def model(self) -> str:
        return self.settings.gemini_model

    @property
    def is_configured(self) -> bool:
        return self.settings.gemini_is_configured

    def configuration_summary(self) -> dict[str, str | bool | int | float]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "enabled": self.settings.gemini_agent_enabled,
            "configured": self.is_configured,
            "timeout_seconds": self.settings.gemini_timeout_seconds,
            "max_retries": self.settings.gemini_max_retries,
            "max_agent_steps": self.settings.gemini_agent_max_steps,
        }

    @contextmanager
    def client(self) -> Iterator[Any]:
        api_key = self.settings.gemini_api_key_value
        if not self.settings.gemini_agent_enabled:
            raise GeminiConfigurationError("Gemini agent is disabled by configuration.")
        if api_key is None:
            raise GeminiConfigurationError("GEMINI_API_KEY is required when the Gemini agent is enabled.")

        client = self._client_factory(api_key, self.settings.gemini_timeout_seconds)
        try:
            yield client
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()


    def generate_structured(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> str:
        last_error: Exception | None = None
        total_attempts = self.settings.gemini_max_retries + 1

        for _ in range(total_attempts):
            try:
                with self.client() as client:
                    response = client.models.generate_content(
                        model=self.model,
                        contents=user_prompt,
                        config=_generate_content_config(system_instruction, response_schema),
                    )
                response_text = getattr(response, "text", None)
                if isinstance(response_text, str) and response_text.strip():
                    return response_text

                parsed = getattr(response, "parsed", None)
                if isinstance(parsed, BaseModel):
                    return parsed.model_dump_json()
                if isinstance(parsed, dict):
                    return response_schema.model_validate(parsed).model_dump_json()
                raise GeminiProviderError("Gemini returned an empty structured response.")
            except GeminiConfigurationError:
                raise
            except Exception as error:
                last_error = error

        raise GeminiProviderError(
            f"Gemini request failed after {total_attempts} attempt(s).",
            category=_classify_provider_error(last_error),
        ) from last_error


def _generate_content_config(
    system_instruction: str,
    response_schema: type[BaseModel],
) -> Any:
    from google.genai import types

    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_json_schema=_sanitize_json_schema(response_schema.model_json_schema()),
        temperature=0.1,
    )


def _create_google_genai_client(api_key: str, timeout_seconds: float) -> Any:
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(timeout_seconds * 1_000)),
    )


def _classify_provider_error(error: Exception | None) -> str:
    if error is None:
        return "provider_error"

    code = getattr(error, "code", None)
    status = str(getattr(error, "status", "")).upper()
    error_name = type(error).__name__.lower()

    if code in {401, 403} or "AUTH" in status or "PERMISSION" in status:
        return "authentication"
    if code == 404 or "NOT_FOUND" in status:
        return "model_not_found"
    if code == 429 or "RESOURCE_EXHAUSTED" in status or "QUOTA" in status:
        return "quota"
    if code == 400 or "INVALID_ARGUMENT" in status:
        return "invalid_request"
    if code in {408, 504} or "TIMEOUT" in status or "timeout" in error_name:
        return "timeout"
    if isinstance(error, GeminiProviderError):
        return error.category
    return "provider_error"


def _sanitize_json_schema(value: Any, *, container_key: str | None = None) -> Any:
    """Keep the JSON Schema subset accepted by Gemini structured output."""
    if isinstance(value, list):
        return [_sanitize_json_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    if container_key in {"$defs", "properties"}:
        return {
            key: _sanitize_json_schema(item)
            for key, item in value.items()
        }

    return {
        key: _sanitize_json_schema(item, container_key=key)
        for key, item in value.items()
        if key in SUPPORTED_GEMINI_JSON_SCHEMA_KEYS
    }
