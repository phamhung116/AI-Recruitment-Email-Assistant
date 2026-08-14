# AGENTS.md

Guidance for any agent, human or AI, working in this repository.

This project builds an AI-assisted safety review layer for the recruitment email pipeline: deterministic validation first, LLM semantic review second as advisory output only, and HR approval before anything is marked as sent. No real email is ever sent in the MVP.

## Repository Layout

- `backend/`: FastAPI application with SQLAlchemy models, Pydantic schemas, route modules, and services.
- `frontend/`: React + Vite + TypeScript application with route-level feature pages and Axios API client.
- `sampleData/`: sample Excel input for local testing and import.
- `docker-compose.yml`: PostgreSQL 16 service.

Backend landmarks:

- `backend/app/main.py`: app factory, CORS, router registration, startup table creation.
- `backend/app/api/`: route modules for candidates, templates, queue, history, audit, dashboard, and health.
- `backend/app/models/entities.py`: `Candidate`, `EmailTemplate`, `EmailQueue`, `EmailHistory`, `AuditLog`.
- `backend/app/schemas/api.py`: request and response schemas.
- `backend/app/services/rules.py`: status-to-email mapping, sensitive-type list, transitions.
- `backend/app/services/email_workflow.py`: draft generation, risk checks, approve/cancel/send simulation.
- `backend/app/services/ai_email.py`: LLM/agent service boundary; placeholder-fill today, semantic review target.
- `backend/app/services/excelImport.py`: `.xlsx` import.
- `backend/app/services/audit.py`: audit log insertion.

Frontend landmarks:

- `frontend/src/app/router.tsx`: dashboard, candidates, detail, templates, queue, history, audit routes.
- `frontend/src/services/recruitmentApi.ts`: API client.
- `frontend/src/types/recruitment.ts`: frontend API types, expected to mirror backend schemas.
- `frontend/src/features/*`: product screens.
- `frontend/src/components/*`: shared layout, table, dialog, state, and UI components.

Extend this architecture; do not replace it. New functionality should go into a new module or service rather than growing an existing file past a few hundred lines. In particular, do not keep piling logic into `email_workflow.py`. Split by responsibility:

- Rules service: deterministic validation and policy mapping.
- Draft service: template rendering and draft assembly.
- Agent service: LLM review only.
- Audit service: append-only events.

## First Files To Inspect

- `README.md`
- `docs/implementation-plan.md`
- `docs/system-architecture.md`
- `docs/domain-model.md`
- `docs/validation-rules.md`
- `backend/app/models/entities.py`
- `backend/app/schemas/api.py`
- `backend/app/services/email_workflow.py`
- `backend/app/services/rules.py`
- `frontend/src/services/recruitmentApi.ts`
- `frontend/src/types/recruitment.ts`

## Current Commands

Backend:

```bash
cd backend
pip install -r requirements.txt
python -m app.db.seed
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run build
```

Docker:

```bash
docker compose up -d postgres
```

Tests, formatting, and linting are not configured yet. Do not claim they exist until the repository contains the corresponding config and scripts.

## Backend Conventions

- Routes handle request parsing, dependency injection, response models, and HTTP error mapping. Do not put business logic in `backend/app/api/*`.
- Every request and response shape gets an explicit Pydantic schema in `backend/app/schemas/`. Do not pass raw ORM objects or ad hoc dicts across the API boundary.
- Deterministic checks live in the rules/service layer, never only in the LLM path. This includes required fields, email format, duplicate detection, status-to-email mapping, template placeholder resolution, and prior-send history.
- The LLM must not be the only thing standing between bad data and a queued draft.
- New Python dependencies must be recorded in `backend/requirements.txt` or a future `pyproject.toml`; do not vendor or duplicate packages.
- Prefer integration-style tests that exercise a full route -> service -> DB round trip for workflow behavior.
- Use focused unit tests for pure functions, such as rule predicates in `rules.py`.

## Frontend Conventions

- `frontend/src/types/recruitment.ts` must stay in lockstep with `backend/app/schemas/api.py`.
- Any backend schema change is a breaking-change candidate and needs a matching frontend type update in the same change.
- API calls go through `frontend/src/services/recruitmentApi.ts`; feature components do not call `axios` or `fetch` directly.
- Keep feature pages in `frontend/src/features/*` thin.
- Shared table, dialog, layout, and state logic belongs in `frontend/src/components/*`.
- Use the existing frontend stack: React, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS, local UI components, and Lucide icons.

## LLM And Agent Boundary Rules

These rules are non-negotiable because they define the safety boundary of the project.

- Advisory only: the LLM reviews semantic consistency, flags contradictions or ambiguity, and explains warnings in HR-readable language.
- The LLM never decides hiring outcomes, never mutates candidate status, never invents data, and never overrides a deterministic blocker.
- Bounded input: everything sent to the model must be a structured, size-capped fragment such as candidate fields, template, and draft body. Never send a raw or unbounded dump of database or request state.
- Graceful degradation: if the LLM call fails or times out, fall back to deterministic-only review and explicitly mark the queue item as `semantic review unavailable`. Do not silently skip review or block indefinitely.
- Uncertainty is a signal, not noise. Low-confidence or ambiguous LLM output should raise severity for HR review instead of being discarded.
- No live send path: nothing in the agent service, or anywhere else, should be able to reach a real email provider in the MVP.
- In this MVP, "send" in API/UI means "mark simulated" unless a provider integration has been explicitly designed and approved post-MVP through a separate safety review.

## Product Safety Rules

- HR remains the final decision-maker.
- Do not let AI decide whether a candidate passes or fails.
- Do not let AI change recruitment status.
- Do not invent missing candidate information.
- Do not infer company policy without explicit rules.
- Do not silently correct important candidate data.
- Do not claim a real email was sent without evidence.
- Do not add real email sending to the MVP unless a later requirement explicitly changes scope.
- Do not bypass HR review for sensitive or uncertain drafts.
- Do not expose candidate PII unnecessarily in logs, prompts, errors, or telemetry.

## Trust Boundaries

Treat these as untrusted:

- Browser and user input.
- Uploaded Excel files.
- LLM output.

Treat existing database rows as possibly stale or conflicting because candidates may have been edited concurrently.

A real email provider, if ever added, is a high-risk boundary and explicitly out of scope for the MVP. Do not wire one up without a separate design and review pass.

## API Design Conventions

- Use resource-oriented routes with plural resources in the path, such as `/candidates` and `/email-drafts`.
- Request and response Pydantic models should be named `*Request` and `*Response`.
- Keep API schemas explicit even when they seem to match ORM models.
- List endpoints should support pagination using cursor/limit or page/page_size. Pagination is currently missing project-wide; add it when touching a list endpoint rather than deferring further.
- Mutating endpoints that can be safely retried, such as draft generation and send simulation, should be idempotent where feasible.
- Idempotency keys are currently missing; flag this instead of silently reintroducing duplicate-send risk.
- Invalid input should return structured 4xx responses.
- Deterministic blockers must prevent draft creation or queue advancement instead of surfacing as a 500 or silent no-op.

## Breaking-Change Checklist

Before merging, check whether the change touches any of these files or concerns:

- `backend/app/schemas/api.py`: update `frontend/src/types/recruitment.ts` in the same change.
- `backend/app/models/entities.py`: needs a migration. There are currently no migrations in this repo, so call this out explicitly in the PR rather than hand-editing the database.
- Route paths or methods in `backend/app/api/*`: update `frontend/src/services/recruitmentApi.ts` and relevant docs.
- Status-to-email mapping or transition rules in `backend/app/services/rules.py`: these are safety-critical deterministic rules and need tests, not just a manual check.

## Testing

- Backend: use pytest when test infrastructure is added. Favor one integration test per workflow path, such as import -> draft -> approve/cancel -> send simulation, over many isolated unit tests.
- Backend: assert whole response/object equality where practical instead of excessive field-by-field checks.
- Frontend: add component/integration tests for feature pages that touch the review queue and approval flow.
- Frontend: do not chase 100% coverage on presentational components.
- There are currently no automated tests in this repo.
- Treat "add a test for the path you touched" as a standing expectation for any change to `rules.py`, `email_workflow.py`, or the agent service, even before a full suite exists.

## Change Size Guidance

Keep changes reviewable:

- Aim under about 500 lines for logic changes in rules, workflow, or agent boundaries.
- Aim under about 800 lines for mechanical changes such as schema/type plumbing or refactors.
- If a change is larger, split it into staged PRs. For example, add the processing-run model separately from wiring it into the queue endpoint.

## Known Gaps

Do not silently fix these without flagging the scope and tradeoff in the PR:

- Validation issues are stored as JSON on `EmailQueue`, not normalized records.
- No processing-run or campaign model.
- No idempotency keys.
- No pagination.
- No automated test suite yet.
- No auth/RBAC.
- No DB migrations; schema is created at startup.
- Audit logging failure policy is undefined and currently coupled to the main DB transaction.

These are acceptable for the MVP scope. Any change that makes one of them worse, such as adding another unmigrated model field or another unpaginated list endpoint, should say so explicitly in the PR description.

## Change Discipline

- Do not invent APIs, dependencies, tables, or product behavior.
- Do not install dependencies unless the task explicitly requires it.
- Do not create migrations unless the task explicitly requires database implementation.
- Do not rename or delete existing files unless explicitly requested.
- Do not assume an empty directory is unused.
- Update docs when behavior, API contracts, setup, or safety policy changes.
- Add or update tests with implementation changes once test infrastructure exists.
- When a fact cannot be verified, document it as `Unknown`, `Not implemented`, or `Needs confirmation`.

## Skill Triggering Rules

- **Slash Invocation for Skills (`/skill-name`):** Whenever the user starts a prompt with a slash followed by a skill name (e.g. `/team2-ba`, `/team1-qa-qc`, `/team1-product`, `/team1-architecture`, `/recruitment-email-review`), the AI agent MUST automatically recognize it as an explicit command to load, trigger, and execute that specific skill. Strip the leading `/` and match against the skill `name` in frontmatter.

