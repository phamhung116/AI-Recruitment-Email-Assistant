# API Contract

## Current API

The current backend exposes unversioned routes from FastAPI.

### Health

`GET /health`

Response:

```json
{ "status": "ok" }
```

### Dashboard

`GET /dashboard`

Response:

```json
{
  "total_candidates": 15,
  "pending_emails": 3,
  "sent_emails": 1,
  "failed_emails": 0
}
```

### Candidates

`POST /candidates/import`

Multipart form:

- `file`: `.xlsx`

Response:

```json
{
  "imported": 10,
  "skipped": 1,
  "errors": ["Row 2: duplicate email test@example.com"]
}
```

`GET /candidates`

Query params:

- `search`
- `position`
- `stage`
- `status`

`GET /candidates/{id}`

`PATCH /candidates/{id}`

Request body:

```json
{
  "full_name": "Nguyen Minh An",
  "email": "an.nguyen@example.com",
  "status": "PASS_CV"
}
```

### Email Templates

`GET /email-templates`

`POST /email-templates`

`PATCH /email-templates/{id}`

`DELETE /email-templates/{id}`

Template request:

```json
{
  "name": "Interview Invitation",
  "email_type": "INTERVIEW_INVITATION",
  "subject": "Interview invitation for {{position}}",
  "body": "Hi {{candidate_name}}, ...",
  "required_placeholders": ["candidate_name", "position"],
  "is_sensitive": false
}
```

### Drafts And Queue

`POST /email-drafts/generate`

Request:

```json
{
  "candidate_id": 1,
  "email_type": "INTERVIEW_INVITATION",
  "created_by": "demo_hr"
}
```

Response shape: `EmailQueueRead`.

`GET /email-queue`

Query params:

- `status`

`GET /email-queue/{id}`

`PATCH /email-queue/{id}`

Request:

```json
{
  "subject": "Updated subject",
  "body": "Updated body"
}
```

`POST /email-queue/{id}/approve`

`POST /email-queue/{id}/send`

Current behavior: send simulation only.

`POST /email-queue/{id}/cancel`

`POST /api/v1/agent/review-draft`

Request:

```json
{
  "queue_id": 1,
  "actor": "demo_hr"
}
```

The endpoint re-runs deterministic validation, performs the configured semantic review, stores the combined result on the queue item, and appends a sanitized audit event. Gemini suggestions are advisory and do not overwrite the draft.

### History And Audit

`GET /email-history`

Query params:

- `candidate_id`

`GET /audit-logs`

Returns the latest 100 audit records.

## Current Error Responses

FastAPI returns standard errors:

```json
{
  "detail": "Candidate not found"
}
```

Some validation errors return an object in `detail`, for example:

```json
{
  "detail": {
    "passed": false,
    "errors": ["Template must exist."],
    "checked_at": "2026-08-04T10:00:00+00:00"
  }
}
```

## Target MVP API Changes

Use versioned routes for new APIs:

```text
/api/v1/...
```

Proposed additions:

- `POST /api/v1/processing-runs`
- `GET /api/v1/processing-runs/{id}`
- `GET /api/v1/validation-issues`
- `POST /api/v1/email-drafts/{id}/review-decisions`
- `POST /api/v1/email-drafts/{id}/simulate-send`

Do not remove current routes until frontend migration is complete.

## Target Validation Issue Shape

```json
{
  "rule_id": "STATUS_EMAIL_MISMATCH",
  "severity": "blocker",
  "message": "Email type does not match candidate status.",
  "evidence": {
    "candidate_status": "REJECT_CV",
    "requested_email_type": "INTERVIEW_INVITATION",
    "expected_email_type": "REJECTION_AFTER_CV"
  },
  "is_blocking": true,
  "source": "deterministic"
}
```

## Idempotency

Current behavior: Not implemented.

Target:

- Accept `Idempotency-Key` header for import, processing run, draft generation, and simulation endpoints.
- Persist key on `ProcessingRun`.
- Return the existing result for duplicate keys with identical input hash.
- Return conflict for duplicate key with different input hash.

## Pagination

Current behavior: Not implemented for list APIs.

Target:

- Add `limit`, `offset`, and optional `sort` for candidates, queue, history, audit, and processing runs.
- Include total count where needed by frontend tables.

## API Versioning

Current APIs are unversioned.

Target:

- Keep current routes for compatibility.
- Add `/api/v1` for new contracts.
- Document breaking changes before frontend migration.
