# System Architecture Execution Plan & Checkpoint

- **Project Name**: Recruitment Mail Guard (Minimal Real-Email MVP)
- **Execution Mode**: existing-system
- **Execution Profile**: standard (<=45 minutes)
- **Started At**: 2026-08-12T16:05:00+07:00
- **Deadline At**: 2026-08-12T23:59:50+07:00
- **Current Status**: APPROVED_FOR_HANDOFF

## 1. Input Inventory & Fingerprints

| Input Path | Required / Optional | Available Status | Approval State | SHA-256 Fingerprint | Last Checked | Relevance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `docs/product/product.md` | Required | Available | APPROVED_BASELINE_FOR_BA (v1.0.1) | `17b10266e440729d4c55a9e0b1a41ee5c6494700afab3878743df9cdbcff4a6b` | 2026-08-12T16:05:00+07:00 | High (Primary Product Baseline) |
| `docs/ba/business-analysis.md` | Required | Available | READY_FOR_HANDOFF (v1.2.0-BA) | `378e9140fa9bd773d1aa17f3eb3ea52b415a7703ca6384f880ef201d4a9ec802` | 2026-08-12T16:05:00+07:00 | High (Primary BA Requirements) |
| `docs/ba/requirements-traceability.md` | Required | Available | READY_FOR_HANDOFF | `77fec358309df53d0abacdfae379a2ba9ab5a420b98fbc1859cbf1ecce58bc5c` | 2026-08-12T16:05:00+07:00 | High (BA RTM) |
| `docs/ba/plan.md` | Required | Available | READY_FOR_HANDOFF | `5979adcefa84f7b60ea47f52caee9a72c1c69c6cfefea34d28edca82ae2ee235` | 2026-08-12T16:05:00+07:00 | High (BA Plan Baseline) |
| `docs/product/ba-reconciliation.md` | Required | Available | COMPLETED | `8a2e1d7465fc9f9570183b07dfabfecae4ff80b43501a39f6007eec5d36e84bb` | 2026-08-12T16:05:00+07:00 | Medium (Reconciliation Log) |

## 2. Input Fingerprint Drift & Affected-Area Audit

- **Product Spec Baseline Fingerprint**: `17b10266e440729d4c55a9e0b1a41ee5c6494700afab3878743df9cdbcff4a6b` (Matched exact).
- **BA Spec Input Fingerprint**: `378e9140fa9bd773d1aa17f3eb3ea52b415a7703ca6384f880ef201d4a9ec802` (Matched exact).
- **Drift Audit Classification**: Zero unhandled input change or material fingerprint MISMATCH detected. No STALE decision gates present.

## 3. In-Scope & Out-of-Scope Architecture Work

- **In-Scope**:
  - Evaluation of current repository source code (`backend`, `frontend`, `docker-compose.yml`, dependencies).
  - Component classification (KEEP, SIMPLIFY, REMOVE_FROM_CORE_FLOW, LATER, UNKNOWN).
  - Canonical definition of Architectural Drivers (`DRV-F-001` .. `DRV-F-010`, `DRV-Q-001` .. `DRV-Q-004`, `CON-001` .. `CON-003`, `ASM-001` .. `ASM-002`, `RSK-001` .. `RSK-003`).
  - Architecture options analysis comparing Modular Monolith vs Minimal Background Worker vs Retaining Event-Driven Queue (RabbitMQ/Redis/Celery/Outbox).
  - Target architecture design based on Modular Monolith with decoupled 3-Phase Transaction Boundary (Phase A DB Commit / Phase B Outbound HTTP / Phase C DB Finalize) and Resend Email Provider Adapter.
  - Completion of technical spike `SPIKE-001` with official provider comparative research (Resend vs SendGrid vs Postmark) and Resend 24-hour idempotent replay mechanics ([SPIKE-001](file:///d:/hilab/Project_W1/AI-Recruitment-Email-Assistant/docs/system-design/spikes/SPIKE-001-provider-capability.md)).
  - Creation and formal User approval of mandatory ADRs (`ADR-001` through `ADR-007`, status `accepted`).
  - Mermaid diagrams: C4 Level 1 Context, C4 Level 2 Container, Deployment Topology, Sequence Diagrams (3-Phase Send, Retry/Reconciliation, Decision Correction), Security/Trust Boundary, Data Flow.
  - Failure-first design for 10 critical operational scenarios.
  - Security, privacy (PII), secret management, trust boundaries, audit immutability, and observability architecture.
  - Full Requirement-to-Architecture Traceability Matrix (`docs/system-design/traceability.md`).
- **Out-of-Scope**:
  - Implementation of application source code, ORM schema models, or DB migrations.
  - Modification of Docker Compose or environment configuration files.
  - Microservices, Kubernetes, or complex distributed queue infrastructure for MVP.
  - Holding DB transactions open across external HTTP network calls.

## 4. Accepted Decisions & Completed Technical Spikes

- **Accepted Decisions (Accepted ADRs)**:
  - `ADR-001`: Target Architecture Style selected as Modular Monolith (FastAPI + React + PostgreSQL + Resend Email Provider Adapter) (`accepted`).
  - `ADR-002`: Synchronous REST Email Provider Integration (Resend) with Decoupled 3-Phase Execution and Normalized Outcome Mapping (`PROVIDER_ACCEPTED`, `DEFINITIVE_FAILURE`, `DELIVERY_UNKNOWN`) (`accepted`).
  - `ADR-003`: Single Logical Send Operation per Draft Revision with Retry Identity Reuse and Provider Attempt tracking (`accepted`).
  - `ADR-004`: Provider-backed Idempotent Status Reconciliation & Manual HR Resolution for `DELIVERY_UNKNOWN` state (`accepted`).
  - `ADR-005`: Decoupled Transaction Boundary (Phase A DB Commit / Phase B Outbound HTTP / Phase C DB Finalize) with Append-Only Immutable Audit Log (`accepted`).
  - `ADR-006`: Legacy Component Disposition — Decommissioning RabbitMQ, Redis, Celery Workers, Outbox Dispatcher, and LLM from core path (`accepted`).
  - `ADR-007`: Strangler-Fig Migration Strategy from Legacy Simulation Monolith to Minimal Real-Email MVP (`accepted`).
- **Completed Technical Spikes**:
  - `SPIKE-001`: Provider capability investigation completed; Resend selected for native `Idempotency-Key` (24h retention window) and provider-backed idempotent replay ([SPIKE-001](file:///d:/hilab/Project_W1/AI-Recruitment-Email-Assistant/docs/system-design/spikes/SPIKE-001-provider-capability.md)) (`COMPLETED`).
- **Blockers & Architectural Risks**:
  - `RSK-001`: Provider API Timeout / Drop resulting in `DELIVERY_UNKNOWN` state requiring provider-backed idempotent replay or manual resolution.
  - `RSK-002`: Provider physical duplicate delivery residual risk across network retry boundaries.
  - `RSK-003`: Database transaction failure during audit logging requiring atomic rollback in Phase C.

## 5. Checkpoint & Exact Next Action

- **Completed Steps**:
  - [x] Step 1: Inspect and Inventory Inputs & Approval Gate (Product v1.0.1 APPROVED, BA v1.2.0-BA READY_FOR_HANDOFF)
  - [x] Step 2: Current-State Assessment & Component Classification Inventory
  - [x] Step 3: Extract Architectural Drivers (`DRV-F-001`..`010`, `DRV-Q-001`..`004`, `CON-001`..`003`, `ASM-001`..`002`, `RSK-001`..`003`)
  - [x] Step 4: Feasibility Critique & Architecture Options Analysis (Options A, B, C)
  - [x] Step 5: Write Mandatory ADRs (`ADR-001` through `ADR-007`) & obtain formal User Approval (`accepted`)
  - [x] Step 6: Complete SPIKE-001 comparative provider research (Resend selected) & document 24h idempotent replay mechanics
  - [x] Step 7: System Boundaries & C4 Modeling (Context, Container, Deployment, 3-Phase Sequences, Security Boundary, Data Flow)
  - [x] Step 8: Cross-Cutting Concerns Design (Decoupled 3-Phase Security, Resilience, Capacity, Observability)
  - [x] Step 9: Architecture Traceability Matrix (`traceability.md`) & Downstream Handoff Contracts
  - [x] Step 10: Validator Script Update & Quality Check (`APPROVED_FOR_HANDOFF`, Exit Code 0)
- **Exact Next Action**: Hand off approved System Architecture Specification (`docs/system-design/system-design.md`) and accepted ADRs to downstream Database Design phase (`team1-dbdesign`).
