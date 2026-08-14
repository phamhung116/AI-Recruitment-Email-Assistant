# Requirements Traceability Matrix (RTM)

- **Document Status**: READY_FOR_HANDOFF
- **Product Source**: `docs/product/product.md` (APPROVED_BASELINE_FOR_BA v1.0.1)
- **BA Source**: `docs/ba/business-analysis.md`
- **Last Updated**: 2026-08-12

## 1. Traceability Matrix Table

| Product Source | BA Requirement ID | Requirement Title | Acceptance Criteria | Use Case | Downstream Owners | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CAP-001`, `BR-001` | `FR-001` | Candidate Excel Import & Field Validation | `AC-001`, `AC-012` | `UC-001` | Backend, Frontend, QA | confirmed |
| `CAP-002`, `BR-001`, `BR-003`, `DEC-003` | `FR-002` | Contradiction Detection for Application ID + Stage | `AC-002`, `AC-013`, `AC-021` | `UC-004` | Backend, Frontend, QA | confirmed |
| `CAP-003`, `DEC-005` | `FR-003` | Fixed Pre-seeded Template Rendering & Content Protection | `AC-003` | `UC-002` | UI/UX, Backend, Frontend, QA | confirmed |
| `CAP-004`, `DEC-005` | `FR-004` | Draft Revisioning & Safety Guard Invalidation | `AC-004`, `AC-011` | `UC-003` | Backend, Frontend, QA | confirmed |
| `CAP-007`, `DEC-004` | `FR-005` | Logical Send Operation Creation & Draft Freezing | `AC-005`, `AC-007` | `UC-005` | Backend, Architecture, QA | confirmed |
| `CAP-006`, `GOAL-002`, `DEC-004` | `FR-006` | Real Email Provider Integration & Result Mapping | `AC-006`, `AC-014`, `AC-022` | `UC-005` | Architecture, Backend, QA | confirmed |
| `CAP-007`, `DEC-004` | `FR-007` | Delivery Unknown Handling & Provider Status Verification | `AC-007`, `AC-015`, `AC-016`, `AC-022` | `UC-006` | Backend, Frontend, QA | confirmed |
| `CAP-008`, `DEC-003` | `FR-008` | Decision Correction Workflow Initiation | `AC-008`, `AC-017`, `AC-018`, `AC-019`, `AC-020` | `UC-007` | UI/UX, Backend, Frontend, QA | confirmed |
| `CAP-009`, `DEC-003`, `DEC-004` | `FR-009` | Immutable Audit Trail Logging | `AC-009` | `UC-005` | Backend, Database, QA | confirmed |
| `CAP-003`, `DEC-005` | `FR-010` | Subject Line Validation Against Decision | `AC-010`, `AC-021` | `UC-002` | Backend, QA | confirmed |
| `CAP-004`, `BR-005` | `FR-011` | Pre-Send Draft Superseding | `AC-011` | `UC-003` | Backend, Database, QA | confirmed |
| `CAP-001`, `BR-001` | `FR-012` | Globally Unique Application ID Enforcement | `AC-012` | `UC-001` | Backend, Database, QA | confirmed |
| `GOAL-001`, `CAP-004` | `NFR-001` | Safety & Determinism Quality Gate | `AC-004`, `AC-010`, `AC-021` | `UC-003` | Backend, Architecture, QA | confirmed |
| `GOAL-003`, `DEC-003` | `NFR-002` | Audit Trail Immutability | `AC-009` | `UC-005` | Backend, Database, QA | confirmed |
| `GOAL-004`, `DEC-004` | `NFR-003` | Logical Send Operation Uniqueness & Retry Controls | `AC-005`, `AC-007` | `UC-006` | Backend, Architecture, QA | confirmed |
| `CAP-005`, `DEC-004` | `NFR-004` | Human-Readable Exception Messaging | `AC-006`, `AC-007`, `AC-014`, `AC-022` | `UC-005`, `UC-006` | UI/UX, Frontend, QA | confirmed |

## 2. Coverage Summary
- Total BA Requirements with Valid Product Source: 100% (All 12 FRs and 4 NFRs trace to confirmed Product capabilities CAP-001..CAP-009, Goals GOAL-001..GOAL-004, Product Rules BR-001..BR-005, or Product Decisions DEC-003..DEC-005).
- Product Capabilities & Goals Coverage: 100% (CAP-001..CAP-009, GOAL-001..GOAL-004, DEC-003..DEC-005 mapped in RTM).
- Total Functional Requirements: 12 (`FR-001` to `FR-012`).
- Total Non-Functional Requirements: 4 (`NFR-001` to `NFR-004`).
- Total Acceptance Criteria: 22 (`AC-001` to `AC-022`).
- Total Use Cases: 7 (`UC-001` to `UC-007`).
- Total Downstream Owners Assigned: 100% (Architecture, Database, UI/UX, Backend, Frontend, QA).
- Orphan Requirements: 0.
- Broken Links: 0.

