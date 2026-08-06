# 0004 Structured Agent Output

Status: accepted

## Context

Free-form LLM responses are difficult to validate and can blur the line between advisory content and workflow authority.

## Decision

Any LLM integration must return structured output validated by backend schemas. The output must include draft content, issue list, uncertainty, and model metadata. Invalid output must fail closed and require HR review.

## Consequences

- Agent services need schema validation and contract tests.
- Prompt versions must be tracked.
- LLM output can add warnings but cannot remove deterministic blockers.
- Provider adapters must normalize responses into the same contract.
