# Team1 Frontend Handoff

## Status

status: READY_FOR_QA  
updated_at: 2026-08-17

## Implemented Scope

| Slice | Routes | Components | Source Requirements | Status |
| --- | --- | --- | --- | --- |
| FE-001 | all | typed v1 API client, error handling | OpenAPI, backend handoff | completed |
| FE-002 | `/candidates` | import review, filters, sorting, pagination, table states | CAP-001 | completed |
| FE-003 | `/candidates/:candidateId` | candidate context, draft revisions, protected content, explicit send confirmation | CAP-002..008 | completed |
| FE-004 | `/email-operations` | operation filters, attempt details, retry, reconcile, manual resolution | CAP-006..008 | completed |
| FE-005 | `/`, `/audit-logs` | dashboard metrics, activity and audit views | CAP-009 | completed |
| FE-006 | all | responsive shell, navigation cleanup, loading/empty/error states | UI specification | completed |

## API Integration

| Screen/Component | Endpoint | Method | Request | Response | Error States |
| --- | --- | --- | --- | --- | --- |
| Candidates | `/api/v1/candidates` | GET | pagination/filter/sort query | candidate page | inline error state |
| Import review | `/api/v1/candidates/import/preview`, `/import` | POST | multipart `.xlsx` | row review/import result | row reasons and toast |
| Candidate detail | `/api/v1/candidates/{id}` | GET | path ID | candidate | not found/error state |
| Draft workflow | `/api/v1/drafts`, `/drafts/{id}` | POST/PATCH | typed draft input | immutable revision | deterministic blocker detail |
| Real send | `/api/v1/drafts/{id}/send` | POST | actor and explicit confirmation | send operation | conflict/blocker feedback |
| Operations | `/api/v1/send-operations` | GET | pagination/filter query | operation page | loading/empty/error state |
| Recovery actions | `/api/v1/send-operations/{id}/*` | POST | governed action payload | updated operation | warning/error toast |
| Audit | `/api/v1/audit-logs` | GET | pagination query | audit page | loading/empty/error state |

## UI States

| Route/Component | Loading | Empty | Error | Permission/Auth | Notes |
| --- | --- | --- | --- | --- | --- |
| `/` | skeleton | zero metrics | friendly retry state | internal only | client-side MVP aggregation |
| `/candidates` | table skeleton | import CTA | inline retry state | internal only | horizontal overflow on small screens |
| `/candidates/:candidateId` | detail skeleton | no revisions | not found/API error | explicit send confirmation | protected outcome is read-only |
| `/email-operations` | table skeleton | no operations | inline retry state | governed actions | unknown delivery exposes reconciliation |
| `/audit-logs` | table skeleton | no events | inline retry state | internal only | details avoid email body/PII |

## Configuration

| Variable | Required | Purpose | Notes |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | No | Backend origin | defaults to `http://localhost:8000` |
| `PLAYWRIGHT_CHANNEL` | No | Use a system browser for E2E | set to `chrome` when Playwright Chromium is unavailable |

## Verification

| Command | CWD | Timestamp | Exit Code | Summary |
| --- | --- | --- | --- | --- |
| `npm test` | `frontend` | 2026-08-17 | 0 | 30 tests passed |
| `npm run build` | `frontend` | 2026-08-17 | 0 | TypeScript and Vite production build passed |
| `$env:PLAYWRIGHT_CHANNEL='chrome'; npm run test:e2e` | `frontend` | 2026-08-17 | 0 | 2 desktop/mobile E2E projects passed without a provider call |

## Known Limitations

- Authentication and RBAC are not implemented; `demo_hr` is a temporary actor identity.
- There is no bulk or automatic sending. Every real send requires explicit confirmation.
- Resend provider acceptance does not guarantee inbox delivery.
- Live provider verification is pending local credentials and a verified sender.
- Legacy template/history source modules may remain dormant, but they are not routed or part of the v1 runtime.
