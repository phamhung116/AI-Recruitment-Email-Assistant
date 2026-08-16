# System Architecture Execution Plan & Checkpoint

- **Project Name**: Recruitment Mail Guard (Minimal Real-Email MVP)
- **Execution Mode**: existing-system
- **Execution Profile**: standard (<=45 minutes)
- **Started At**: 2026-08-12T16:05:00+07:00
- **Current Status**: APPROVED_FOR_HANDOFF
- **User Approval Decision**: APPROVED
- **User Approval Date**: 2026-08-12

## 1. Input Inventory & Fingerprints

| Input Path | Required / Optional | Available Status | Approval State | SHA-256 Fingerprint | Last Checked | Relevance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `docs/product/product.md` | Required | Available | APPROVED_BASELINE_FOR_BA (v1.0.1) | `316e189df41671e629c9c370a03f39b2068b422dc8d6682a5e3ae0c1707246c7` | 2026-08-12T16:05:00+07:00 | High (Primary Product Baseline) |
| `docs/ba/business-analysis.md` | Required | Available | READY_FOR_HANDOFF (v1.2.0-BA) | `d425d5f0de918d0261974906122dada3834be70cf5ee14bf1041e833eeef97ab` | 2026-08-12T16:05:00+07:00 | High (Primary BA Requirements) |
| `docs/ba/requirements-traceability.md` | Required | Available | READY_FOR_HANDOFF | `1926a124ca2918fc4754bc681237105c410773e7f793f9fd2f6d347636ce00b3` | 2026-08-12T16:05:00+07:00 | High (BA RTM) |
| `docs/ba/plan.md` | Required | Available | READY_FOR_HANDOFF | `bdcd9c64a951af9cabbe8f58fe52b02ae26048ca4ed9c455ceb90ae2e8608ec6` | 2026-08-12T16:05:00+07:00 | High (BA Plan Baseline) |
| `docs/product/ba-reconciliation.md` | Required | Available | COMPLETED | `d3481bd7f14753e36346334757d2f53d6b00a8ad14eec52da4cec46863ba736e` | 2026-08-12T16:05:00+07:00 | Medium (Reconciliation Log) |

## 2. Input Fingerprint Drift & Affected-Area Audit

- **Product Spec Baseline Fingerprint**: `316e189df41671e629c9c370a03f39b2068b422dc8d6682a5e3ae0c1707246c7` (Matched exact).
- **BA Spec Input Fingerprint**: `d425d5f0de918d0261974906122dada3834be70cf5ee14bf1041e833eeef97ab` (Matched exact).
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
