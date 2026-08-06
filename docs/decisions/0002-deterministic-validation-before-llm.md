# 0002 Deterministic Validation Before LLM

Status: accepted

## Context

Many safety checks are explicit and reliable in code: required fields, email format, duplicate detection, status-to-email mapping, placeholder resolution, and prior sent history.

## Decision

The system will run deterministic validation before any LLM-assisted review or drafting. Deterministic blockers cannot be downgraded or overridden by LLM output.

## Consequences

- Rule IDs and severity must be stable.
- LLM usage is limited to semantic review, explanation, and draft wording.
- The backend remains the source of truth for workflow eligibility.
- Tests must cover deterministic rules independently from agent tests.
