# Domain Model

## Current Persisted Models

### Candidate

File: `backend/app/models/entities.py`

Fields:

- `id`
- `full_name`
- `email`
- `phone`
- `position`
- `stage`
- `status`
- `interview_time`
- `interviewer`
- `note`
- `created_at`
- `updated_at`

Relationships:

- One candidate has many `EmailQueue` rows.
- One candidate has many `EmailHistory` rows.

### RecruitmentStatus

Current enum name: `CandidateStatus`

Values:

- `PENDING`
- `PASS_CV`
- `REJECT_CV`
- `INTERVIEW_CONFIRMED`
- `PASS_INTERVIEW`
- `REJECT_INTERVIEW`
- `OFFER_ACCEPTED`

Final company status taxonomy: Needs confirmation.

### EmailType

Current values:

- `APPLICATION_RECEIVED`
- `INTERVIEW_INVITATION`
- `INTERVIEW_REMINDER`
- `REJECTION_AFTER_CV`
- `REJECTION_AFTER_INTERVIEW`
- `OFFER_EMAIL`
- `ONBOARDING_EMAIL`
- `RESCHEDULE_RESPONSE`
- `NEXT_ROUND_EMAIL`

Only some values are mapped from status rules today.

### EmailTemplate

Fields:

- `id`
- `name`
- `email_type`
- `subject`
- `body`
- `required_placeholders`
- `is_sensitive`
- `created_at`
- `updated_at`

Current approved-template workflow: Not implemented.

### EmailDraft

Current implementation uses `EmailQueue` as the draft/queue entity.

Fields:

- `id`
- `candidate_id`
- `email_type`
- `to_email`
- `subject`
- `body`
- `status`
- `requires_hr_approval`
- `risk_check_result`
- `created_by`
- `approved_by`
- `sent_at`
- `created_at`
- `updated_at`

### AuditEvent

Current enum-like action constants:

- `ai_generate_email`
- `approve_email`
- `send_email`
- `cancel_email`
- `update_candidate_status`

Fields:

- `id`
- `action`
- `entity_type`
- `entity_id`
- `actor`
- `metadata_json`
- `created_at`

## Target MVP Models

### Campaign

Purpose: group candidate processing into an import or email-preparation batch.

Status: Not implemented.

Suggested fields:

- `id`
- `name`
- `source`
- `status`
- `created_by`
- `created_at`
- `updated_at`

### ValidationIssue

Purpose: persist deterministic and AI-assisted findings.

Status: Not implemented. Current issues are JSON in `EmailQueue.risk_check_result`.

Suggested fields:

- `id`
- `processing_run_id`
- `email_queue_id`
- `candidate_id`
- `rule_id`
- `severity`
- `message`
- `evidence_json`
- `is_blocking`
- `source`
- `created_at`

### ReviewDecision

Purpose: record HR approve/edit/reject/cancel decisions.

Status: Not implemented as a distinct entity.

Suggested fields:

- `id`
- `email_queue_id`
- `decision`
- `reviewed_by`
- `notes`
- `created_at`

Allowed decisions:

- `APPROVE`
- `EDIT`
- `REJECT`
- `CANCEL`

### ProcessingRun

Purpose: represent each import, draft generation, validation, or review run.

Status: Not implemented.

Suggested fields:

- `id`
- `campaign_id`
- `candidate_id`
- `email_queue_id`
- `run_type`
- `status`
- `input_hash`
- `idempotency_key`
- `started_at`
- `completed_at`
- `metadata_json`

### AuditEvent

Current `AuditLog` can be extended or kept as the MVP audit event table.

Target additions:

- Store request correlation ID where available.
- Store actor identity from auth when implemented.
- Avoid storing large PII payloads.

## Relationships

Target:

- Campaign has many ProcessingRuns.
- Candidate has many ProcessingRuns.
- Candidate has many EmailDrafts.
- EmailDraft has many ValidationIssues.
- EmailDraft has many ReviewDecisions.
- ProcessingRun has many ValidationIssues.
- AuditEvent references entity type and entity ID.

## State Transitions

Current `QueueStatus`:

```text
DRAFT -> APPROVED -> SENT
DRAFT -> CANCELLED
PENDING_APPROVAL -> APPROVED -> SENT
PENDING_APPROVAL -> CANCELLED
APPROVED -> CANCELLED
```

Current send simulation blocks:

- Cannot send sensitive draft unless approved.
- Cannot send sent/cancelled/failed drafts.
- Cannot edit sent drafts.

Target MVP should rename or clearly label `SENT` as simulated unless real delivery is explicitly added post-MVP.

Candidate status transitions:

- Current code may update candidate status during send simulation for some email types.
- Target MVP should require explicit HR-controlled status changes and must not let AI change status.
