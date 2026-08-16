"""Select and render fixed templates while preserving protected outcome text."""

from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Mapping

from app.constants.templates import (
    DECISION_CORRECTION,
    DECISION_CRITICAL_MARKER,
    DECISION_LABELS,
    FIXED_TEMPLATE_CATALOG,
    STAGE_DECISION_TEMPLATE_POLICY,
    FixedTemplate,
)


PLACEHOLDER_PATTERN = re.compile(r"{{([a-zA-Z0-9_]+)}}")


class TemplateServiceError(ValueError):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(f"{error_code}: {message}")


@dataclass(frozen=True, slots=True)
class TemplateRenderContext:
    application_id: str
    candidate_name: str
    recipient: str
    stage: str
    decision: str
    email_type: str
    is_correction: bool = False


@dataclass(frozen=True, slots=True)
class RenderedTemplate:
    template_code: str
    subject: str
    decision_critical_content: str
    editable_content: str
    rendered_body: str
    locked_fields: Mapping[str, str]


def get_fixed_template(template_code: str) -> FixedTemplate:
    template = FIXED_TEMPLATE_CATALOG.get(template_code)
    if template is None:
        raise TemplateServiceError(
            "STATUS_UNSUPPORTED",
            f"Unsupported email type: {template_code or '<empty>'}",
        )
    return template


def select_template(context: TemplateRenderContext) -> FixedTemplate:
    if context.decision == "PENDING":
        raise TemplateServiceError(
            "STATUS_PENDING",
            "A pending application does not have an outcome email template.",
        )

    policy_template_code = STAGE_DECISION_TEMPLATE_POLICY.get(
        (context.stage, context.decision)
    )
    if policy_template_code is None:
        raise TemplateServiceError(
            "STATUS_UNSUPPORTED",
            f"Unsupported stage and decision combination: {context.stage}/{context.decision}",
        )

    expected_email_type = (
        DECISION_CORRECTION if context.is_correction else policy_template_code
    )
    if context.email_type != expected_email_type:
        raise TemplateServiceError(
            "STATUS_EMAIL_MISMATCH",
            f"Expected {expected_email_type} for {context.stage}/{context.decision}, "
            f"received {context.email_type or '<empty>'}.",
        )

    return get_fixed_template(expected_email_type)


def render_template(
    context: TemplateRenderContext,
    editable_content: str | None = None,
) -> RenderedTemplate:
    template = select_template(context)
    values = _render_values(context)
    subject = _render_placeholders(template.subject_template, values)
    critical_content = _render_placeholders(
        template.decision_critical_template,
        values,
    )
    editable_source = (
        template.editable_template if editable_content is None else editable_content
    )
    rendered_editable = _render_placeholders(
        editable_source,
        values,
        preserved_placeholders={"decision_critical_content"},
    )
    rendered_body = assemble_rendered_body(critical_content, rendered_editable)
    locked_fields = MappingProxyType(
        {
            "application_id": values["application_id"],
            "stage": values["stage"],
            "decision": values["decision"],
            "recipient": values["recipient"],
            "email_type": values["email_type"],
        }
    )

    return RenderedTemplate(
        template_code=template.code,
        subject=subject,
        decision_critical_content=critical_content,
        editable_content=rendered_editable,
        rendered_body=rendered_body,
        locked_fields=locked_fields,
    )


def assemble_rendered_body(
    decision_critical_content: str,
    editable_content: str,
) -> str:
    marker_count = editable_content.count(DECISION_CRITICAL_MARKER)
    if marker_count != 1:
        raise TemplateServiceError(
            "DECISION_CRITICAL_CONTENT_MODIFIED",
            "Editable content must retain exactly one protected content insertion point.",
        )
    return editable_content.replace(
        DECISION_CRITICAL_MARKER,
        decision_critical_content,
        1,
    )


def validate_decision_critical_content(
    context: TemplateRenderContext,
    submitted_content: str,
) -> None:
    expected_content = render_template(context).decision_critical_content
    if submitted_content != expected_content:
        raise TemplateServiceError(
            "DECISION_CRITICAL_CONTENT_MODIFIED",
            "Decision-critical content is read-only and must match the fixed template.",
        )


def _render_values(context: TemplateRenderContext) -> dict[str, str]:
    required_values = {
        "application_id": context.application_id.strip(),
        "candidate_name": context.candidate_name.strip(),
        "recipient": context.recipient.strip().lower(),
        "stage": context.stage.strip(),
        "decision": context.decision.strip(),
        "email_type": context.email_type.strip(),
        "decision_label": DECISION_LABELS.get(context.decision, ""),
    }
    missing_values = [name for name, value in required_values.items() if not value]
    if missing_values:
        raise TemplateServiceError(
            "TEMPLATE_PLACEHOLDER_MISSING",
            f"Missing template value(s): {', '.join(sorted(missing_values))}",
        )
    return required_values


def _render_placeholders(
    source: str,
    values: Mapping[str, str],
    preserved_placeholders: set[str] | None = None,
) -> str:
    preserved = preserved_placeholders or set()

    def replace(match: re.Match[str]) -> str:
        placeholder = match.group(1)
        if placeholder in preserved:
            return match.group(0)
        if placeholder not in values:
            raise TemplateServiceError(
                "TEMPLATE_PLACEHOLDER_MISSING",
                f"Unknown or unavailable template placeholder: {placeholder}",
            )
        return values[placeholder]

    rendered = PLACEHOLDER_PATTERN.sub(replace, source)
    unresolved = {
        placeholder
        for placeholder in PLACEHOLDER_PATTERN.findall(rendered)
        if placeholder not in preserved
    }
    if unresolved:
        raise TemplateServiceError(
            "TEMPLATE_PLACEHOLDER_MISSING",
            f"Unresolved template placeholder(s): {', '.join(sorted(unresolved))}",
        )
    return rendered
