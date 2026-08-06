# Implementation Plan

This plan fits the current FastAPI + React/Vite repository. It does not replace the application with a greenfield architecture.

## Phases

1. Repository audit
2. Product and MVP clarification
3. Domain model design
4. Validation rule engine
5. Agent and LLM integration
6. API design
7. Database and audit-history design
8. Frontend workflow design
9. Testing and evaluation
10. Security and privacy checks
11. Docker and local development setup
12. MVP implementation order
13. Demo preparation
14. Future improvements outside MVP

## Milestones

- M1: Documentation and repository audit complete.
- M2: Deterministic validation engine and issue model designed.
- M3: API contracts and persistence model implemented.
- M4: HR review workflow aligned with no-real-send MVP.
- M5: Optional LLM semantic review integrated behind an abstraction.
- M6: Tests and demo scenario complete.

## Ordered Task Checklist

### Phase 1: Repository audit

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1-T1 | MVP | Keep audit docs current after each implementation slice. | `README.md`, `AGENTS.md`, `docs/*` | None | None | Docs reflect actual routes, models, commands, and gaps. | Manual doc review. | Docs can drift if skipped. |

### Phase 2: Product and MVP clarification

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P2-T1 | MVP | Confirm final recruitment statuses and email mappings. | `backend/app/services/rules.py`, `frontend/src/types/recruitment.ts`, `frontend/src/constants/emailTypes.ts` | None | Product owner decision | Mapping table is explicit and documented. Unknown statuses block safely. | Unit tests for each status. | Wrong mapping can create unsafe emails. |
| P2-T2 | MVP | Rename user-facing "send" language to clear simulation wording where needed. | `frontend/src/features/emailQueue/EmailQueuePage.tsx`, `frontend/src/features/dashboard/DashboardPage.tsx`, `backend/app/api/emailQueueRoutes.py` | None | P2-T1 | UI/API docs make clear no real email is sent. | Frontend smoke test. | Users may believe real email was delivered. |

### Phase 3: Domain model design

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P3-T1 | MVP | Add model design for `ProcessingRun` and `ValidationIssue`. | `backend/app/models/entities.py`, `backend/app/schemas/api.py` | Optional migration files later | P2-T1 | Models capture run type, status, issue severity, source, and blocking flag. | Model/schema unit tests. | Schema changes need migration strategy. |
| P3-T2 | MVP | Add review decision representation. | `backend/app/models/entities.py`, `backend/app/schemas/api.py`, `backend/app/services/email_workflow.py` | Optional migration files later | P3-T1 | Approve/edit/reject/cancel decisions are traceable separately from queue status. | Workflow integration tests. | Duplicates current queue status unless responsibilities are clear. |
| P3-T3 | Post-MVP | Add `Campaign` model. | `backend/app/models/entities.py`, `backend/app/schemas/api.py` | Optional migration files later | P3-T1 | Multiple candidates can be grouped into one campaign. | Campaign API tests. | May overcomplicate MVP. |

### Phase 4: Validation rule engine

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P4-T1 | MVP | Refactor current `build_risk_check` into a deterministic validation service returning structured issues. | `backend/app/services/email_workflow.py`, `backend/app/services/rules.py`, `backend/app/schemas/api.py` | `backend/app/services/validation.py` | P3-T1 | Each rule returns rule ID, severity, message, evidence, source, and blocking flag. | Unit tests for all rules. | Refactor can change existing draft behavior. |
| P4-T2 | MVP | Add backend email format validation. | `backend/app/services/validation.py`, `backend/app/services/excelImport.py` | None | P4-T1 | Invalid recipient emails block draft generation and are reported on import. | Unit and import tests. | Regex may reject valid addresses if too strict. |
| P4-T3 | MVP | Add duplicate recipient and duplicate processing checks. | `backend/app/services/validation.py`, `backend/app/models/entities.py` | None | P3-T1 | Repeated email type for same candidate or idempotency key is blocked or requires explicit override. | Integration tests. | Needs clear override policy. |

### Phase 5: Agent and LLM integration

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P5-T1 | MVP | Define provider abstraction without adding a real provider by default. | `backend/app/services/ai_email.py`, `backend/app/core/config.py`, `backend/app/schemas/api.py` | `backend/app/services/agent_review.py` | P4-T1 | Mock provider and interface return structured output. | Contract tests. | Premature provider-specific design. |
| P5-T2 | MVP | Add semantic review hook after deterministic validation. | `backend/app/services/email_workflow.py`, `backend/app/services/agent_review.py` | None | P5-T1 | LLM failure does not bypass deterministic rules; result is marked unavailable. | Integration tests with mock provider failures. | AI output may be trusted too much. |
| P5-T3 | Post-MVP | Add real model provider. | `backend/app/core/config.py`, `backend/requirements.txt` | Provider adapter file | P5-T2, explicit dependency approval | Provider is configurable and secrets stay server-side. | Contract and prompt regression tests. | Privacy and cost exposure. |

### Phase 6: API design

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P6-T1 | MVP | Add versioned API schemas for validation issues, processing runs, and review decisions. | `backend/app/schemas/api.py` | None | P3-T1 | New schemas are explicit and frontend-consumable. | Schema tests. | Current unversioned APIs may diverge. |
| P6-T2 | MVP | Add endpoints for processing-run detail and review decisions. | `backend/app/api/emailQueueRoutes.py`, `backend/app/main.py` | `backend/app/api/processingRunRoutes.py` | P6-T1 | Frontend can fetch run issues and submit review decisions. | API tests. | Route naming churn. |
| P6-T3 | Post-MVP | Add pagination to list endpoints. | Candidate, queue, history, audit route modules; frontend API client | None | P6-T1 | Lists accept `limit` and `offset`; responses include total count where needed. | API and frontend tests. | Frontend tables must migrate carefully. |

### Phase 7: Database and audit-history design

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P7-T1 | MVP | Decide migration approach and stop relying on startup `create_all` for production path. | `backend/app/main.py`, `backend/app/db/database.py`, `README.md` | Alembic files only if implementation begins | P3-T1 | Local demo still works; production path has migration plan. | Startup smoke test. | Migration setup adds dependency and workflow changes. |
| P7-T2 | MVP | Expand audit events for validation and review actions. | `backend/app/constants/auditActions.py`, `backend/app/services/audit.py`, workflow services | None | P3-T2 | Draft generation, validation, review, and simulation have audit trail. | Integration tests. | Audit metadata may include PII if not masked. |

### Phase 8: Frontend workflow design

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P8-T1 | MVP | Show structured validation issues in candidate detail and queue preview. | `frontend/src/features/candidates/CandidateDetailPage.tsx`, `frontend/src/features/emailQueue/EmailQueuePage.tsx`, `frontend/src/types/recruitment.ts` | Optional shared issue component | P4-T1, P6-T1 | HR sees severity, message, blocking status, and remediation. | Component tests and manual workflow test. | Dense warnings can overwhelm HR. |
| P8-T2 | MVP | Add explicit approve/edit/reject review controls. | `frontend/src/features/emailQueue/EmailQueuePage.tsx`, `frontend/src/services/recruitmentApi.ts` | None | P6-T2 | Decisions are persisted and reflected in queue status. | Frontend integration test with mocked API. | Current approve/cancel controls may conflict. |
| P8-T3 | Post-MVP | Add campaign processing screens. | `frontend/src/app/router.tsx`, `frontend/src/constants/navigation.ts` | `frontend/src/features/campaigns/*` | P3-T3 | HR can review campaign-level progress. | E2E tests. | Not needed for single-candidate MVP. |

### Phase 9: Testing and evaluation

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P9-T1 | MVP | Add backend pytest setup and rule tests. | `backend/requirements.txt` | `backend/tests/*` | P4-T1 | Deterministic rules are covered. | `pytest`. | New dependency requires approval. |
| P9-T2 | MVP | Add frontend test setup for key review components. | `frontend/package.json` | `frontend/src/**/*.test.tsx` | P8-T1 | Issue display and queue actions are tested. | Frontend test command. | Dependency and config churn. |
| P9-T3 | MVP | Add prompt/agent regression fixtures for mock provider. | None | `backend/tests/fixtures/agent_cases.json` | P5-T1 | Agent contract cases are stable and synthetic. | Contract tests. | Fixtures can encode unrealistic behavior. |

### Phase 10: Security and privacy checks

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P10-T1 | MVP | Add PII masking utilities for logs and provider input summaries. | `backend/app/services/audit.py`, agent service files | `backend/app/services/privacy.py` | P5-T1 | Audit metadata avoids raw email/phone/body unless required. | Unit tests. | Masking can hide needed audit evidence. |
| P10-T2 | MVP | Add upload size/type guard documentation and implementation plan. | `backend/app/services/excelImport.py`, `README.md` | None | None | Corrupt or non-xlsx files fail safely; size limit is documented. | Import tests. | Large uploads can affect memory. |

### Phase 11: Docker and local development setup

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P11-T1 | MVP | Align database names across docker, config default, and env example. | `docker-compose.yml`, `backend/.env.example`, `backend/app/core/config.py`, `README.md` | None | Needs confirmation | One documented local DB name works out of the box. | Backend startup smoke test. | Changing defaults can break local setups. |
| P11-T2 | Post-MVP | Add backend/frontend services to compose for demo. | `docker-compose.yml`, `README.md` | Optional Dockerfiles | P11-T1 | One command can start demo stack. | Manual compose test. | Dockerfiles add maintenance overhead. |

### Phase 12: MVP implementation order

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P12-T1 | MVP | Implement in order: DB alignment, validation service, issue schemas, review UI, audit expansion, tests. | Cross-cutting | See prior tasks | P2-T1 | Each slice is shippable and verified before the next. | All available tests plus manual acceptance. | Large slices increase regression risk. |

### Phase 13: Demo preparation

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P13-T1 | MVP | Prepare deterministic demo cases with synthetic data. | `backend/app/db/seed.py`, `sampleData/*`, `README.md` | Optional fixture files | P9-T1 | Demo shows valid draft, missing data blocker, wrong email type blocker, sensitive approval. | Manual demo script. | Demo can imply unsupported production readiness. |

### Phase 14: Future improvements outside MVP

| ID | Scope | Objective | Affected Existing Files | New Files | Dependencies | Acceptance Criteria | Tests Required | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P14-T1 | Post-MVP | Add auth/RBAC and real actor identity. | Backend route deps, frontend auth shell, audit service | Auth integration files | Product/security decision | Actions use authenticated actor instead of `demo_hr`. | Auth integration tests. | Security-critical scope. |
| P14-T2 | Post-MVP | Add real email provider with explicit send approval design. | Workflow services, config, API, frontend queue | Provider adapter files | Separate safety review | Real sends require approval, audit, idempotency, provider delivery evidence. | Provider sandbox tests. | Highest operational risk. |
| P14-T3 | Post-MVP | Add production compliance workflows. | Privacy, audit, deletion services | Compliance docs and jobs | Legal/security input | Retention, deletion, access export, and provider DPAs are defined. | Compliance acceptance tests. | Cannot be guessed by engineering alone. |

## MVP Completion Definition

- No real email sending is possible from the MVP path.
- Deterministic blockers run before draft generation and queue advancement.
- Validation issues have stable rule IDs, severity, evidence, source, and blocking behavior.
- HR can review, edit, approve, reject, or cancel drafts.
- Sensitive and uncertain drafts cannot bypass review.
- Processing history and audit events are persisted.
- Mock or real LLM provider output is structured and cannot override deterministic rules.
- Automated backend tests cover core rules and workflow blockers.
- README and docs match the implemented behavior.
