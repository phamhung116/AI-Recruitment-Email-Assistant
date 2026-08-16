# Team1 Backend Handoff

## Status

status: READY_FOR_FRONTEND  
updated_at: 2026-08-17

## Implemented Scope

| Slice | Requirement Sources | Backend Areas | Status |
| --- | --- | --- | --- |
| SLICE-001..010 | CAP-001..005, CAP-008 | Database, import, fixed templates, safety guard, revisions, corrections | completed |
| SLICE-011..015 | CAP-006..008 | Resend adapter, logical operation, three-phase send, retry and reconciliation | completed |
| SLICE-016 | CAP-009 | Atomic append-only audit service | completed |
| SLICE-017..019 | FR-001..012 | REST v1, standard errors, OpenAPI, legacy runtime deactivation | completed |

## Environment And Setup

| Item | Value | Notes |
| --- | --- | --- |
| Backend base URL | `http://localhost:8000/api/v1` | Local default |
| API contract path | `docs/backend/openapi.json` | Generated from runtime |
| Backend root | `backend/` | Python 3.11+ |
| Start command | `uvicorn app.main:app --reload` | Run after `alembic upgrade head` |

## Frontend Environment Variables

| Variable | Required | Purpose | Notes |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | No | Backend origin | Defaults to `http://localhost:8000` |

## API Catalog

| Workflow | Method | Path | Request | Success Response | Error Cases |
| --- | --- | --- | --- | --- | --- |
| Import preview | POST | `/api/v1/candidates/import/preview` | multipart `.xlsx` | `ImportPreviewResult` | 400/422 |
| Import | POST | `/api/v1/candidates/import` | multipart `.xlsx` | `ImportResult` | 400/409/422 |
| Candidate list/detail | GET | `/api/v1/candidates`, `/api/v1/candidates/{id}` | query/path | paginated/detail | 404/422 |
| Generate/revise draft | POST/PATCH | `/api/v1/drafts`, `/api/v1/drafts/{id}` | typed JSON | `DraftRevisionRead` | 404/409/422 |
| Correction draft | POST | `/api/v1/candidates/{id}/correction-drafts` | decision/rationale/actor | `DraftRevisionRead` | 404/409/422 |
| Real send | POST | `/api/v1/drafts/{id}/send` | actor + confirmation | `SendOperationRead` | 404/409/422 |
| Retry/reconcile/resolve | POST | `/api/v1/send-operations/{id}/*` | governed action body | `SendOperationRead` | 404/409/422 |
| Operations/audit | GET | `/api/v1/send-operations`, `/api/v1/audit-logs` | pagination/filter | paginated list | 422 |

## Error Model

Target errors use `{error_code,message,details,timestamp,request_id}`. Deterministic blockers and missing confirmation return 422; state conflicts return 409; missing resources return 404. Provider terminal/unknown outcomes are successful operation resources with their explicit status, not transport errors.

## State And Enums

| Name | Values | Meaning | Frontend Notes |
| --- | --- | --- | --- |
| DraftStatus | DRAFT_PENDING_CHECK, READY_TO_SEND, BLOCKED_DETERMINISTIC, FROZEN_IN_FLIGHT, SUPERSEDED, CORRECTION_DRAFT, DISCARDED, FINALIZED | Immutable revision lifecycle | Send only READY_TO_SEND/CORRECTION_DRAFT |
| OperationStatus | SENDING_UNCONFIRMED, PROVIDER_ACCEPTED, DEFINITIVE_FAILURE, DELIVERY_UNKNOWN, FAILED_TERMINAL | Real provider lifecycle | DELIVERY_UNKNOWN requires reconcile/manual resolution |
| FailureCategory | TRANSIENT_RETRYABLE, VALIDATION_TERMINAL, QUOTA_EXCEEDED | Retry policy | Retry only transient/quota |

## Auth And Permissions

| Route/Action | Requirement | Notes |
| --- | --- | --- |
| All v1 routes | Trusted internal/local user | No auth/RBAC in MVP |
| Real send/retry/reconcile | Explicit confirmation | Actor body is temporary until auth exists |
| Manual resolution | Warning acknowledgement + rationale + actor | Always audited |

## External Dependencies

| Dependency | Purpose | Failure Behavior | Notes |
| --- | --- | --- | --- |
| PostgreSQL 16 | Durable state and audit | Request fails/rolls back | Alembic owns schema |
| Resend | Real single-candidate email | Definitive failure or DELIVERY_UNKNOWN | Same operation UUID is idempotency key |

## Verification Evidence

| Command | CWD | Timestamp | Exit Code | Summary |
| --- | --- | --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider` | `backend` | 2026-08-17 | 0 | 164 passed, including migration contract |
| `.venv\\Scripts\\python.exe scripts\\export_openapi.py --check` | `backend` | 2026-08-17 | 0 | Runtime and static OpenAPI synchronized |

## Known Limitations

- No authentication/RBAC or rate limiting; do not expose publicly.
- No batch/automatic send and no LLM semantic review in MVP.
- The existing local PostgreSQL database uses a legacy schema and hiring-state vocabulary. It has not been migrated because the mapping requires explicit HR approval; use a fresh database for the baseline migration.
- A live Resend smoke test remains blocked until `RESEND_API_KEY` and a verified `EMAIL_SENDER_ADDRESS` are configured locally.
- Resend acceptance means the provider accepted the request, not guaranteed inbox delivery.
