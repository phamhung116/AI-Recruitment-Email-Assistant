# Recruitment Mail Guard API Contract

Status: APPROVED_FOR_IMPLEMENTATION
Version: 1.0.0
Updated: 2026-08-17

## Decisions

- Style: REST + OpenAPI, consumed by the React/TypeScript SPA.
- Base path: `/api/v1` for the real-email workflow. Existing unversioned routes remain temporary compatibility endpoints until frontend migration completes.
- Success responses return the resource directly. List responses use `{items,total,page,page_size,pages}`.
- All timestamps are UTC ISO 8601. Candidate IDs are integers; draft, operation, and attempt IDs are UUID strings.
- Authentication and rate limiting are not implemented in this MVP. The API is suitable only for trusted local/internal evaluation and must not be exposed publicly.
- `actor` is an explicit temporary field until authentication supplies the recruiter identity.

## Standard Error

All target routes return:

```json
{
  "error_code": "DRAFT_NOT_READY_TO_SEND",
  "message": "The selected draft is not ready to send.",
  "details": {},
  "timestamp": "2026-08-17T09:30:00Z",
  "request_id": "c18d3b70-60d4-4f53-b808-d76c93b2bd9e"
}
```

Use `404` for missing resources, `409` for conflicting state/duplicates, and `422` for deterministic blockers or semantically invalid input. Provider outcomes are valid operation resources returned with `200`, including `DEFINITIVE_FAILURE` and `DELIVERY_UNKNOWN`.

## Candidates

- `POST /api/v1/candidates/import/preview`: multipart `.xlsx`; validates every non-empty row without persistence.
- `POST /api/v1/candidates/import`: multipart `.xlsx`; imports valid rows and returns row errors for rejected rows.
- `GET /api/v1/candidates?page=1&page_size=20&search=&stage=&status=&sort=created_at&direction=desc`
- `GET /api/v1/candidates/{candidate_id}`

Candidate list sorting is allow-listed to `full_name`, `created_at`, `updated_at`, and `status_updated_at`. Maximum `page_size` is 100.

## Draft Revisions

- `POST /api/v1/drafts` with `{application_id, actor}` creates a validated immutable draft revision.
- `PATCH /api/v1/drafts/{draft_revision_id}` with `{subject?, editable_content?, actor}` creates a new revision when content changes.
- `POST /api/v1/candidates/{candidate_id}/correction-drafts` with `{new_decision, rationale, actor}` creates a controlled correction draft.
- `GET /api/v1/drafts/{draft_revision_id}` returns draft, deterministic risk result, and send operation when present.
- `GET /api/v1/candidates/{candidate_id}/drafts?page=1&page_size=20` returns newest revisions first so candidate detail can recover state after refresh.

Decision-critical content is read-only. `PATCH` accepts only subject and editable content.

## Real Email Send

- `POST /api/v1/drafts/{draft_revision_id}/send` with `{actor, confirmation_acknowledged}`.

The endpoint runs the three-phase workflow and returns one logical operation. `confirmation_acknowledged=false` is blocked with `422`. Repeated calls for the same revision return the existing operation and never create a second provider attempt after an outcome is finalized.

- `POST /api/v1/send-operations/{operation_id}/retry` with `{actor, confirmation_acknowledged}` retries only retryable definitive failures on the same operation.
- `POST /api/v1/send-operations/{operation_id}/reconcile` with `{actor, confirmation_acknowledged}` replays the exact payload with the same provider idempotency key only within 24 hours.
- `POST /api/v1/send-operations/{operation_id}/resolve` with `{resolution, rationale, actor, warning_acknowledged}`.

Resolution is `PROVIDER_ACCEPTED` or `PROVIDER_NOT_RECEIVED`. The latter unlocks controlled retry on the same operation.

- `GET /api/v1/send-operations?page=1&page_size=20&status=&application_id=`
- `GET /api/v1/send-operations/{operation_id}`

Operation responses expose provider status and sanitized failure guidance, but never API keys or raw provider payloads.

## Audit

- `GET /api/v1/audit-logs?page=1&page_size=50&application_id=&event_name=`

Audit responses expose structured sanitized metadata. Candidate email, phone, full name, and email message content are not included.

## Compatibility And Migration

The frontend migrates to `/api/v1` in the same delivery before legacy routes are disconnected. Removing or changing a target field requires a versioned breaking-change decision and regenerated OpenAPI artifact. Static OpenAPI is exported to `docs/backend/openapi.json` and compared with runtime schema during verification.
