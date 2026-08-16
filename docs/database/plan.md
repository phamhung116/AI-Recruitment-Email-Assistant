# Database Design Plan & Tracking (plan.md)

## 1. Session Metadata
- **Project Name**: Recruitment Mail Guard (Minimal Real-Email MVP)
- **Project Root**: `D:\hilab\Project_W1\AI-Recruitment-Email-Assistant`
- **Mode**: `existing-schema`
- **Profile**: `standard`
- **Started At**: 2026-08-15T15:23:45+07:00
- **Current Status**: READY_FOR_REVIEW
- **Approval State**: PENDING_USER_APPROVAL

## 2. Input Inventory & Fingerprints

| Input Path | Category | Status | Approval State | SHA-256 Fingerprint | Last Checked | Relevance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `docs/product/product.md` | required | available | APPROVED_BASELINE_FOR_BA (v1.0.1) | `316e189df41671e629c9c370a03f39b2068b422dc8d6682a5e3ae0c1707246c7` | 2026-08-15T15:40:00+07:00 | High (Primary Product Baseline) |
| `docs/ba/business-analysis.md` | required | available | READY_FOR_HANDOFF (v1.2.0-BA) | `d425d5f0de918d0261974906122dada3834be70cf5ee14bf1041e833eeef97ab` | 2026-08-15T15:40:00+07:00 | High (Primary BA Requirements) |
| `docs/ba/requirements-traceability.md` | required | available | READY_FOR_HANDOFF | `1926a124ca2918fc4754bc681237105c410773e7f793f9fd2f6d347636ce00b3` | 2026-08-15T15:40:00+07:00 | High (BA RTM) |
| `docs/system-design/system-design.md` | required | available | APPROVED_FOR_HANDOFF | `e684be53a735d86d7ded34368052abadea01990920b32d3331585072e3b6c1cc` | 2026-08-15T15:40:00+07:00 | High (System Architecture Spec) |
| `docs/system-design/traceability.md` | required | available | APPROVED_FOR_HANDOFF | `3d74468b73135f5ea3f91771a599c18bc4074de43e5023b5b8c34afca4e16f62` | 2026-08-15T15:40:00+07:00 | High (Architecture Traceability) |

## 3. Approved Database Engine & Architecture Decisions
- Engine: PostgreSQL 16 (`postgres:16-alpine` per `docker-compose.yml`)
- **Target Version**: PostgreSQL 16.x
- **Architecture Style**: Modular Monolith with Decoupled 3-Phase Execution Model (`ADR-001`, `ADR-005`)
- **External Provider Adapter**: Resend REST API with native `Idempotency-Key` and 24h retention window (`ADR-002`, `SPIKE-001`)
- **Target Schema Scope**: Exactly 5 core tables (`candidates`, `draft_revisions`, `logical_send_operations`, `provider_attempts`, `audit_logs`).
- **Template Architecture**: Pre-seeded email templates are managed as immutable application constants/configuration in code per `DEC-005`, eliminating the `email_templates` CRUD table from the target schema.
- **Data Ownership Boundaries**: Single PostgreSQL instance owning candidate application state, draft revisions, send attempts, and immutable audit trail (`ADR-005`). RabbitMQ, Redis, Celery, Outbox events decommissioned from core path (`ADR-006`).

## 4. Work Items & Progress
- [x] Task 1: Inspect & fingerprint canonical inputs (Product v1.0.1, BA v1.2.0-BA, System Design APPROVED)
- [x] Task 2: Existing Schema Assessment (`existing-schema` mode, retiring legacy tables from writes)
- [x] Task 3: Conceptual Data Model (`ENT-001` .. `ENT-005`, `VAL-001` .. `VAL-004`)
- [x] Task 4: Logical Data Model & Mermaid ERD (5-Table Target Architecture)
- [x] Task 5: Physical Schema Specification (PostgreSQL 16 DDL rules, strict constraints, ON DELETE/UPDATE RESTRICT)
- [x] Task 6: Workload-driven Index Design (`QRY-001` .. `QRY-006`, partial index on active drafts)
- [x] Task 7: Transactions & Concurrency Rules (Phase A / Phase B / Phase C boundaries)
- [x] Task 8: Security, PII & Lifecycle Rules (`SEC-001` .. `SEC-003`, `RET-001` .. `RET-003`)
- [x] Task 9: Compatibility & Migration Design (`DBCR-001` non-destructive transition, strict source ID verification)
- [x] Task 10: Traceability Matrix & Quality Gate Validation (100% Coverage, Exit Code 0)

## 5. Key Decisions & Rationales (`DEC-###`)
- `DEC-001`: **Entity Hierarchy for Anti-Duplicate Guarantees** — Enforce `Draft Revision 1 : 1 Logical Send Operation 1 : N Provider Attempts`. Database `UNIQUE` constraint on `logical_send_operations(draft_revision_id)` guarantees zero duplicate operations on double-click or network retry (`ADR-003`).
- `DEC-002`: **Decoupled 3-Phase Transaction Boundaries** — Phase A prepares and commits DB state (`SENDING_UNCONFIRMED`, `ProviderAttempt #1` in `PREPARED`), Phase B executes external Resend HTTP POST outside DB transaction, Phase C finalizes DB state and inserts atomic audit log entry in single transaction block (`ADR-005`).
- `DEC-003`: **Globally Unique Application ID & Strict Data Hygiene** — Enforce `UNIQUE NOT NULL` constraint on `candidates(application_id)` for all participating records. No synthetic/fake ID backfill (`APP-<id>`) is permitted. Unverified legacy rows missing an ID are quarantined until HR provides verified source values (`FR-012`).
- `DEC-004`: **Template Configuration in Code** — The 5 fixed templates are application code constants separating locked decision-critical content from editable greetings/notes, avoiding unnecessary database CRUD tables (`DEC-005`).
- `DEC-005`: **Immutable Append-Only Audit Trail** — Restrict SQL permissions on `audit_logs` to `INSERT` and `SELECT` only. Every state transition in Phase C is atomic with its audit log row (`NFR-002`, `ADR-005`).

## 6. Assumptions (`ASM-###`)
- `ASM-001`: Candidate Excel import provides verified `application_id`, `full_name`, `email`, `stage`, and `status`. Recruiter is responsible for hiring decisions accuracy (`ASM-001`).
- `ASM-002`: Resend API supports `Idempotency-Key` (24h retention window) for provider-backed idempotent replay during `DELIVERY_UNKNOWN` reconciliation (`ADR-002`, `SPIKE-001`).

## 7. Checkpoint & Exact Next Action
- **Current Checkpoint**: Database Semantic Repair completed. All artifacts updated to `READY_FOR_REVIEW`. Approval State is `PENDING_USER_APPROVAL`.
- **Exact Next Action**: Present the repaired specification to the User for review and explicit approval. Do NOT proceed to Backend implementation until User grants approval.
