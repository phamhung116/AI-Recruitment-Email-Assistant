from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.constants.templates import (
    DECISION_CORRECTION,
    DECISION_CRITICAL_MARKER,
    FIXED_TEMPLATE_CATALOG,
    INTERVIEW_INVITATION,
    OFFER_EMAIL,
    REJECTION_AFTER_CV,
    REJECTION_AFTER_INTERVIEW,
)
from app.services.template_service import (
    TemplateRenderContext,
    TemplateServiceError,
    render_template,
    select_template,
    validate_decision_critical_content,
)


APPROVED_TEMPLATE_CODES = {
    INTERVIEW_INVITATION,
    REJECTION_AFTER_CV,
    OFFER_EMAIL,
    REJECTION_AFTER_INTERVIEW,
    DECISION_CORRECTION,
}


def context(
    *,
    stage: str = "CV_SCREENING",
    decision: str = "PASS_CV",
    email_type: str = INTERVIEW_INVITATION,
    is_correction: bool = False,
) -> TemplateRenderContext:
    return TemplateRenderContext(
        application_id="APP-2026-001",
        candidate_name="Nguyen Van A",
        recipient="Candidate@Example.COM",
        stage=stage,
        decision=decision,
        email_type=email_type,
        is_correction=is_correction,
    )


def assert_error_code(expected_code: str, action) -> None:
    with pytest.raises(TemplateServiceError) as caught:
        action()
    assert caught.value.error_code == expected_code


def test_catalog_contains_exactly_five_immutable_templates() -> None:
    assert set(FIXED_TEMPLATE_CATALOG) == APPROVED_TEMPLATE_CODES

    with pytest.raises(TypeError):
        FIXED_TEMPLATE_CATALOG["CUSTOM"] = FIXED_TEMPLATE_CATALOG[INTERVIEW_INVITATION]  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        FIXED_TEMPLATE_CATALOG[INTERVIEW_INVITATION].code = "CUSTOM"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("stage", "decision", "email_type"),
    [
        ("CV_SCREENING", "PASS_CV", INTERVIEW_INVITATION),
        ("CV_SCREENING", "REJECT_CV", REJECTION_AFTER_CV),
        ("INTERVIEW", "PASS_INTERVIEW", OFFER_EMAIL),
        ("INTERVIEW", "REJECT_INTERVIEW", REJECTION_AFTER_INTERVIEW),
    ],
)
def test_policy_selects_the_approved_standard_template(
    stage: str,
    decision: str,
    email_type: str,
) -> None:
    assert select_template(
        context(stage=stage, decision=decision, email_type=email_type)
    ).code == email_type


def test_pending_and_unsupported_stage_decisions_fail_closed() -> None:
    assert_error_code(
        "STATUS_PENDING",
        lambda: select_template(context(decision="PENDING")),
    )
    assert_error_code(
        "STATUS_UNSUPPORTED",
        lambda: select_template(
            context(stage="CV_SCREENING", decision="PASS_INTERVIEW", email_type=OFFER_EMAIL)
        ),
    )


def test_email_type_mismatch_fails_closed() -> None:
    assert_error_code(
        "STATUS_EMAIL_MISMATCH",
        lambda: select_template(context(email_type=REJECTION_AFTER_CV)),
    )


def test_render_separates_locked_outcome_from_editable_content() -> None:
    rendered = render_template(context())

    assert rendered.template_code == INTERVIEW_INVITATION
    assert rendered.subject == "Interview invitation — Application APP-2026-001"
    assert rendered.decision_critical_content in rendered.rendered_body
    assert DECISION_CRITICAL_MARKER in rendered.editable_content
    assert DECISION_CRITICAL_MARKER not in rendered.rendered_body
    assert rendered.locked_fields == {
        "application_id": "APP-2026-001",
        "stage": "CV_SCREENING",
        "decision": "PASS_CV",
        "recipient": "candidate@example.com",
        "email_type": INTERVIEW_INVITATION,
    }
    with pytest.raises(TypeError):
        rendered.locked_fields["decision"] = "REJECT_CV"  # type: ignore[index]


def test_editable_greeting_and_closing_can_change_without_changing_outcome() -> None:
    original = render_template(context())
    edited_layout = (
        "Hello Nguyen Van A,\n\n"
        f"{DECISION_CRITICAL_MARKER}\n\n"
        "Please reply if you need a different interview time.\n\nHilab Recruitment"
    )

    edited = render_template(context(), editable_content=edited_layout)

    assert edited.decision_critical_content == original.decision_critical_content
    assert edited.rendered_body.startswith("Hello Nguyen Van A")
    assert edited.rendered_body.endswith("Hilab Recruitment")
    assert edited.rendered_body.count(original.decision_critical_content) == 1


@pytest.mark.parametrize(
    "editable_content",
    [
        "Hello candidate. No protected insertion point.",
        f"{DECISION_CRITICAL_MARKER}\n{DECISION_CRITICAL_MARKER}",
        "",
    ],
)
def test_editable_content_cannot_remove_or_duplicate_protected_insertion_point(
    editable_content: str,
) -> None:
    assert_error_code(
        "DECISION_CRITICAL_CONTENT_MODIFIED",
        lambda: render_template(context(), editable_content=editable_content),
    )


def test_submitted_decision_critical_content_must_match_exactly() -> None:
    rendered = render_template(context())
    validate_decision_critical_content(context(), rendered.decision_critical_content)

    assert_error_code(
        "DECISION_CRITICAL_CONTENT_MODIFIED",
        lambda: validate_decision_critical_content(
            context(),
            "We will not move forward with your application.",
        ),
    )


def test_correction_template_still_requires_a_valid_stage_decision() -> None:
    correction_context = context(
        stage="INTERVIEW",
        decision="PASS_INTERVIEW",
        email_type=DECISION_CORRECTION,
        is_correction=True,
    )

    rendered = render_template(correction_context)

    assert rendered.template_code == DECISION_CORRECTION
    assert "corrects the outcome previously communicated" in rendered.rendered_body
    assert "Offer approved after interview" in rendered.decision_critical_content

    assert_error_code(
        "STATUS_UNSUPPORTED",
        lambda: render_template(
            context(
                stage="CV_SCREENING",
                decision="PASS_INTERVIEW",
                email_type=DECISION_CORRECTION,
                is_correction=True,
            )
        ),
    )


def test_unknown_editable_placeholder_is_rejected() -> None:
    assert_error_code(
        "TEMPLATE_PLACEHOLDER_MISSING",
        lambda: render_template(
            context(),
            editable_content=(
                "Dear {{candidate_name}},\n\n"
                f"{DECISION_CRITICAL_MARKER}\n\n"
                "{{unknown_value}}"
            ),
        ),
    )
