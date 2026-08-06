# 0003 No Real Email Sending In MVP

Status: accepted

## Context

Real email sending introduces operational, privacy, reputational, and compliance risk. The existing repository has a `/send` action, but it currently simulates delivery by writing queue/history records.

## Decision

The MVP must not send real emails. Any delivery action in the MVP must be clearly labeled as simulation in product copy, documentation, and audit metadata.

## Consequences

- Gmail, Outlook, SendGrid, SMTP, and similar integrations are post-MVP.
- UI copy should avoid implying real delivery.
- Email history in MVP represents simulated send history.
- A future real provider requires a separate ADR and safety review.
