# System Architecture Traceability Matrix

- **Project**: Recruitment Mail Guard (Minimal Real-Email MVP)
- **Document Status**: APPROVED_FOR_HANDOFF
- **Last Verified**: 2026-08-12T16:05:00+07:00

## 1. Requirement-to-Architecture Traceability Matrix

| Product/BA Source ID | Architectural Driver ID | ADR ID | Target Component | Verification Approach | Downstream Owner | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FR-001` | `DRV-F-001` | `ADR-001`, `ADR-007` | Backend / `excelImport.py` | Integration test Excel upload header contract & uniqueness check | Backend, Frontend, QA | confirmed |
| `FR-002` | `DRV-F-003` | `ADR-001`, `ADR-005` | Backend / `rules.py` | Unit test prior history contradiction check for App ID + Stage | Backend, Frontend, QA | confirmed |
| `FR-003` | `DRV-F-001` | `ADR-001`, `ADR-007` | Backend & Frontend / `draft_service.py` | Unit test decision-critical lock & editable content separation | UI/UX, Backend, Frontend, QA | confirmed |
| `FR-004` | `DRV-F-004` | `ADR-003`, `ADR-007` | Backend / `draft_service.py` | Integration test edit revision increment & status reset to PENDING | Backend, Frontend, QA | confirmed |
| `FR-005` | `DRV-F-005` | `ADR-003`, `ADR-005` | Backend / `send_service.py` | Integration test Phase A single operation creation & draft freeze | Backend, Architecture, QA | confirmed |
| `FR-006` | `DRV-F-007` | `ADR-002`, `ADR-003` | Backend / `provider_adapter.py` | Unit/Mock test Phase B HTTP response mapping (ACCEPTED, FAILURE, UNKNOWN) | Architecture, Backend, QA | confirmed |
| `FR-007` | `DRV-F-008` | `ADR-004` | Backend & Frontend / `send_service.py` | Integration test DELIVERY_UNKNOWN reconciliation & manual override | Backend, Frontend, QA | confirmed |
| `FR-008` | `DRV-F-009` | `ADR-001`, `ADR-005` | Backend & Frontend / `correction_service.py` | Integration test correction workflow with rationale & confirmation modal | UI/UX, Backend, Frontend, QA | confirmed |
| `FR-009` | `DRV-F-010` | `ADR-005` | Backend / `audit.py` | Integration test Phase C atomic DB transaction audit log persistence | Backend, Database, QA | confirmed |
| `FR-010` | `DRV-F-002` | `ADR-001` | Backend / `rules.py` | Unit test subject line keyword alignment check against decision | Backend, QA | confirmed |
| `FR-011` | `DRV-F-004` | `ADR-003` | Backend / `draft_service.py` | Integration test pre-send revision superseding logic | Backend, Database, QA | confirmed |
| `FR-012` | `DRV-F-001` | `ADR-001`, `ADR-005` | Backend / `excelImport.py` | Integration test Application ID DB unique constraint | Backend, Database, QA | confirmed |
| `NFR-001` | `DRV-F-002` | `ADR-001`, `ADR-005` | Backend / `rules.py` | Integration test blocking provider attempt when guard fails | Backend, Architecture, QA | confirmed |
| `NFR-002` | `DRV-F-010` | `ADR-005` | PostgreSQL / `audit_logs` DB Table | DB test table permission restriction preventing UPDATE/DELETE | Backend, Database, QA | confirmed |
| `NFR-003` | `DRV-F-005`, `DRV-Q-002` | `ADR-003` | Backend / `LogicalSendOperation` Model | Concurrent HTTP request test verifying single Phase A operation creation | Backend, Architecture, QA | confirmed |
| `NFR-004` | `DRV-F-007` | `ADR-002`, `ADR-004` | Frontend / Exception Dialog Components | Component test human-readable failure guidance rendering | UI/UX, Frontend, QA | confirmed |
| `ADI-001` | `DRV-F-007` | `ADR-002` | Backend / `provider_adapter.py` | Provider HTTP integration test with timeout & header assertions | Architecture | confirmed |

## 2. Traceability Statistics & Quality Check

- **Total Material Requirements**: 17
- **Covered Requirements**: 17
- **Blocked Requirements**: 0
- **Orphan Requirements**: 0
- **Orphan Components**: 0
- **Missing Verification**: 0
- **Missing Owner**: 0
- **Overall Traceability Coverage**: 100%
