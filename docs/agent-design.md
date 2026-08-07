# Agent Design

## Agent Role

The agent is a safety reviewer and drafting assistant for recruitment emails. It helps HR understand risk and draft language, but it does not make hiring decisions, change candidate status, or send email.

## Input

Expected input to the agent service:

- Candidate fields needed for the draft.
- Recruitment status and mapped email type.
- Approved template metadata and rendered draft.
- Deterministic validation results.
- Company policy rules supplied by the backend.
- Prompt version and model configuration.

Do not include unnecessary PII. Minimum viable fields should be used for each review.

## Tools

Implemented:

- `GeminiAgentProvider` isolates the Google Gen AI SDK and server-side credentials.
- `AgentModelOutput` validates Gemini JSON before the application can use it.
- `semantic_review.v2` is loaded from a bounded, versioned system-prompt file.
- `RecruitmentEmailAgent` loads the domain skill, enforces the deterministic gate, and delegates to a bounded Level 3 agent loop.
- The model chooses between two allowlisted read-only tools: candidate-fact checking and email-policy checking.
- The backend executes each tool without model-provided arguments, returns a structured observation, and requires both observations before finalization.
- Provider failure, malformed output, or exhausted steps return `unavailable` and require human review.

Workflow integration:

- Draft generation and content edits run semantic review after deterministic validation.
- The original draft remains authoritative; Gemini wording is advisory and is not applied automatically.
- Combined deterministic and semantic results are stored in `EmailQueue.risk_check_result`.
- `POST /api/v1/agent/review-draft` supports an explicit re-review of an editable queue item.
- Audit records contain status/model/version/count metadata only, not recipient email or draft body.
- Normalized processing-run history remains a post-MVP improvement.

## Policies

- The agent may suggest wording.
- The agent may identify ambiguity or semantic mismatch.
- The agent may explain validation issues.
- The agent must classify uncertainty conservatively.
- The agent must never decide pass/fail.
- The agent must never change status.
- The agent must never invent missing data.
- The agent must never claim email delivery.
- The agent must never bypass HR review.

## Execution Loop

1. Receive normalized candidate, template, intended email type, and deterministic findings.
2. If deterministic blockers exist, skip semantic generation and return advisory explanation only.
3. Build a minimized prompt containing the current run state and trusted observations.
4. Ask the model to select exactly one next action from the allowlist.
5. Execute the selected read-only tool in the backend and append its structured observation.
6. Repeat decide -> act -> observe until both required tools have run.
7. Allow `finalize` only after the required observations exist and validate the final structured output.
8. Merge deterministic findings and semantic findings without letting the LLM override blockers.
9. Persist model/tool counts, prompt version, final output, and sanitized trace in the queue risk JSON and audit metadata.
10. Present the Agent Review Journey, findings, uncertainty, suggestions, and HR checkpoints through the shared frontend panel.

## Structured Output Contract

Target shape:

```json
{
  "status": "completed",
  "draft_subject": "string",
  "draft_body": "string",
  "issues": [
    {
      "rule_id": "AI_SEMANTIC_MISMATCH",
      "severity": "warning",
      "message": "string",
      "evidence": "string",
      "requires_human_review": true
    }
  ],
  "uncertainty": {
    "has_uncertainty": true,
    "reason": "string"
  },
  "model_metadata": {
    "provider": "string",
    "model": "string",
    "prompt_version": "string",
    "skill_name": "string",
    "skill_version": "string",
    "attempts": 3,
    "loop_steps": 3,
    "tool_calls": 2
  },
  "requires_human_review": true,
  "semantic_review_available": true
}
```

Allowed severities: `info`, `warning`, `error`, `blocker`.

## Refusal And Uncertainty Behavior

The agent should refuse or return a blocking issue when asked to:

- Decide whether the candidate passed or failed.
- Change a recruitment status.
- Invent missing interview time, location, salary, or company policy.
- Send or claim to send an email.
- Ignore deterministic blockers.

If status labels, policy, or template meaning are ambiguous, return `requires_human_review=true`.

## Human Review Checkpoints

- After import validation.
- Before sensitive drafts enter approved state.
- Before any simulated delivery action.
- Whenever deterministic validation returns `warning`, `error`, or `blocker`.
- Whenever the agent returns uncertainty.

## Prompt Versioning

Prompt templates should be versioned, for example:

- `draft_generation.v1`
- `semantic_review.v2`
- `warning_explanation.v1`

Each processing run should persist prompt version, model provider, model name, and structured output validation status.

## Model Provider Abstraction

Target interface:

```text
ModelProvider.review_draft(input) -> AgentReviewResult
ModelProvider.generate_draft(input) -> AgentDraftResult
```

Provider details should be isolated from route handlers and deterministic services.

## Allowed Behavior Examples

- "The draft says the interview is tomorrow, but the candidate interview_time is missing. Human review required."
- "This rejection email matches the mapped email type but is sensitive and requires HR approval."
- "The status label is unsupported. I cannot infer the correct email type."

## Disallowed Behavior Examples

- "The candidate should fail the interview."
- "I updated the candidate to REJECT_INTERVIEW."
- "I filled in the missing interview date as next Monday."
- "This email has been sent."
- "The policy is probably to send an offer, so I selected OFFER_EMAIL."
