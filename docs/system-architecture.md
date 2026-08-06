# System Architecture

## Current Architecture

The repository is a two-app system with asynchronous review infrastructure:

- `backend/`: FastAPI application with SQLAlchemy models, Pydantic schemas, domain route modules, and service modules.
- `frontend/`: React/Vite TypeScript application with route-level feature pages and an Axios API client.
- `sampleData/`: sample Excel input file.
- `docker-compose.yml`: PostgreSQL 16, RabbitMQ management, and Redis services.

Current backend modules:

- `app/main.py`: app factory, CORS, router registration, startup table creation.
- `app/api/`: route modules for candidates, templates, queue, history, audit logs, dashboard, health.
- `app/models/entities.py`: `Candidate`, `EmailTemplate`, `EmailQueue`, `EmailHistory`, `AuditLog`, and `OutboxEvent`.
- `app/schemas/api.py`: request/response schemas.
- `app/services/rules.py`: status-to-email mapping, sensitive email type list, send simulation transitions.
- `app/services/email_workflow.py`: draft generation, transactional outbox creation, approve/cancel/send simulation.
- `app/services/outbox_dispatcher.py`: publishes pending PostgreSQL outbox events to RabbitMQ.
- `app/services/agent_worker.py`: version-safe Gemini review persistence.
- `app/services/review_progress.py`: Redis lock and expiring progress records.
- `app/services/ai_email.py`: mock AI service that fills placeholders.
- `app/services/excelImport.py`: `.xlsx` import.
- `app/services/audit.py`: audit log insertion.

Current frontend modules:

- `src/app/router.tsx`: dashboard, candidates, detail, templates, queue, history, audit routes.
- `src/services/recruitmentApi.ts`: API client.
- `src/types/recruitment.ts`: frontend API types.
- `src/features/*`: product screens.
- `src/components/*`: shared layout, table, dialog, state, and UI components.
- `src/components/shared/EmailReviewPanel.tsx`: HR-readable deterministic and Gemini review presentation shared by queue and draft preview.

## Target MVP Architecture

```text
Candidate input
    -> parser/normalizer
    -> schema validation
    -> validation rule engine
    -> status-email policy mapping
    -> template renderer / draft generator
    -> deterministic safety review
    -> optional LLM semantic review
    -> severity classifier
    -> HR review queue
    -> approve / edit / reject / cancel
    -> processing run + audit events
```

The target MVP should extend the current architecture instead of replacing it.

## Module Responsibilities

- API routes: request parsing, dependency injection, response models, HTTP errors.
- Schemas: explicit request and response contracts.
- Models: persisted entities and relationships.
- Rules service: deterministic validations and policy mapping.
- Draft service: template rendering and draft assembly.
- Agent service: LLM semantic review and natural-language explanations only.
- Audit service: append-only workflow events.
- Frontend API client: typed calls mirroring backend contract.
- Frontend feature pages: HR workflows and review surfaces.

## Request And Data Flow

Current flow:

1. Frontend uploads Excel through `POST /candidates/import`.
2. Backend parses rows with openpyxl and inserts `Candidate` records.
3. Frontend opens candidate detail and calls `POST /email-drafts/generate`.
4. Backend maps candidate status to email type.
5. Backend validates template presence, placeholder data, duplicate sent history, and sensitive-template flag.
6. `MockAIEmailService` renders subject/body by replacing placeholders.
7. Backend creates `EmailQueue` and `OutboxEvent` in one PostgreSQL transaction and returns immediately.
8. Dispatcher publishes the event to RabbitMQ; a Celery worker acquires a Redis lock.
9. Worker reviews the exact draft version and persists only a matching result.
10. Frontend polls the queue item and unlocks workflow actions only for a current completed review.
11. HR can approve, cancel, or simulate send.
12. Send simulation writes `EmailHistory`, marks the item SENT, auto-cancels superseded drafts, and logs audit events.

Target flow changes:

- Add processing-run and validation-issue records.
- Add richer deterministic validation before draft creation.
- Add optional LLM semantic review after deterministic checks.
- Replace "send" wording in MVP UI/API with "mark simulated" or keep clearly labeled simulation.
- Prevent automatic real email delivery.

## Deterministic Validation Responsibilities

- Required fields.
- Email format.
- Duplicate candidate and duplicate recipient checks.
- Status-to-email mapping.
- Campaign eligibility.
- Template placeholder support and resolution.
- Prior sent history and duplicate processing checks.
- Severity assignment for explicit rules.

## LLM Responsibilities

- Review semantic consistency between email body and intended email type.
- Detect contradictory or ambiguous language.
- Explain warnings in HR-readable language.
- Draft wording from approved templates when a provider is implemented.
- Flag uncertainty for HR review.

The LLM must not decide hiring outcomes, mutate candidate status, invent data, or override deterministic blockers.

## External Integrations

Current:

- PostgreSQL as source of truth.
- RabbitMQ as the only review-job broker.
- Redis for locks and temporary progress.
- Gemini behind a bounded provider abstraction with structured output and safe fallback.
- Browser frontend with polling.
- No real email provider.

Post-MVP:

- Real email provider only after explicit approval and separate safety design.
- Auth/RBAC provider. Not implemented.

## Trust Boundaries

- Browser/user input is untrusted.
- Uploaded Excel files are untrusted.
- Database records may contain stale or conflicting candidate data.
- LLM output is untrusted and advisory.
- Email provider, if later added, is a high-risk boundary and outside MVP.

## Failure Handling

- Invalid input should return structured 4xx errors.
- Deterministic blockers should prevent draft creation or queue advancement.
- Non-blocking warnings should be attached to review output.
- LLM failures should degrade to deterministic review and mark semantic review as unavailable.
- Audit logging failures need an explicit policy. Current behavior is coupled to the main DB transaction.
- Database connection failures return server errors. Retry behavior is not implemented.

## Known Gaps

- Validation issues are stored as JSON on `EmailQueue`, not normalized records.
- No campaign or processing-run model.
- No idempotency keys.
- No pagination.
- No dead-letter dashboard or production-grade monitoring.
- No auth/RBAC.
- No migrations.
