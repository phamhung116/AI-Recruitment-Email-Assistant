# 0001 Human-In-The-Loop Email Workflow

Status: accepted

## Context

Recruitment emails can communicate sensitive hiring outcomes and personal scheduling details. The product uses AI assistance, but AI must not make hiring decisions or send communication without HR oversight.

## Decision

The MVP workflow will keep HR as the final decision-maker. Drafts must be reviewed by HR before sensitive queue actions. AI may suggest wording or identify risks, but it cannot approve, reject, or change candidate status.

## Consequences

- Queue and review screens are core product surfaces.
- Sensitive or uncertain drafts require explicit HR review.
- Automated "set-and-forget" sending is outside MVP.
- Audit events must capture HR decisions.
