# Database Traceability Matrix (traceability.md)

## 1. Requirement-to-Schema Traceability Table

| Product / BA Source | System Design Driver / ADR | Conceptual Entity / Invariant | Physical Table & Column | Constraints / Index / Txn | Verification Strategy | Backend Owner | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CAP-001 / FR-001` | `DRV-F-001 / ADR-001` | `ENT-001 (Candidate)` | `candidates.full_name, email, stage, status` | `CON-002, CON-003, IDX-001` | Unit test Excel import parsing & field persistence | Backend Core | READY_FOR_REVIEW |
| `CAP-002 / FR-002` | `DRV-F-003 / ADR-001` | `VAL-003, VAL-004` | `candidates.stage, status, communicated_decision` | `CON-004, CON-005, IDX-001` | Integration test SQL query for prior decision contradiction | Backend Core | READY_FOR_REVIEW |
| `CAP-003 / FR-003` | `DRV-F-001 / ADR-007` | `ENT-002 (Draft Revision)` | `draft_revisions.template_code, decision_critical_content, editable_content` | `CON-007` | Unit test decision-critical lock & editable content split | Backend Core | READY_FOR_REVIEW |
| `CAP-004 / FR-004` | `DRV-F-004 / ADR-003` | `ENT-002 (Draft Revision)` | `draft_revisions.revision_number, status` | `CON-006, CON-008, CON-016, IDX-002` | Integration test revision increment & status reset to PENDING | Backend Core | READY_FOR_REVIEW |
| `CAP-007 / FR-005` | `DRV-F-005 / ADR-003` | `ENT-003 (Send Operation)` | `logical_send_operations.id, draft_revision_id` | `CON-010, REL-003, TXN-001` | Concurrent DB insert test asserting single operation per revision | Backend Core | READY_FOR_REVIEW |
| `CAP-006 / FR-006` | `DRV-F-007 / ADR-002` | `ENT-003, ENT-004` | `logical_send_operations.operation_status, provider_attempts.attempt_status` | `CON-011, CON-014, REL-004, TXN-003` | Unit test mapping Resend 200 to PROVIDER_ACCEPTED in Phase C | Backend Core | READY_FOR_REVIEW |
| `CAP-007 / FR-007` | `DRV-F-008 / ADR-004` | `ENT-003, ENT-004` | `logical_send_operations.resolution_mode, provider_attempts.attempt_number` | `CON-013, CON-017, IDX-005, TXN-003` | Integration test retry incrementing attempt without duplicating operation | Backend Core | READY_FOR_REVIEW |
| `CAP-008 / FR-008` | `DRV-F-009 / ADR-001` | `ENT-002, ENT-003` | `draft_revisions.is_correction, correction_rationale, prior_operation_id` | `CON-009, REL-002, TXN-003` | Integration test correction draft creation and communicated update gate | Backend Core | READY_FOR_REVIEW |
| `CAP-009 / FR-009` | `DRV-F-010 / ADR-005` | `ENT-005 (Audit Log)` | `audit_logs.event_name, entity_id, application_id, payload_json` | `CON-015, IDX-006, TXN-003` | DB test Phase C atomic rollback on audit insert error | Backend Core | READY_FOR_REVIEW |
| `CAP-003 / FR-010` | `DRV-F-002 / ADR-001` | `ENT-002 (Draft Revision)` | `draft_revisions.subject, template_code` | `CON-004, CON-005, CON-007` | Unit test subject keyword alignment check against template config | Backend Core | READY_FOR_REVIEW |
| `CAP-004 / FR-011` | `DRV-F-004 / ADR-003` | `ENT-002 (Draft Revision)` | `draft_revisions.status, superseded_at, discarded_at` | `CON-008, IDX-002, IDX-003` | Integration test marking older revisions as SUPERSEDED or DISCARDED | Backend Core | READY_FOR_REVIEW |
| `CAP-001 / FR-012` | `DRV-F-001 / ADR-001` | `VAL-001 (Application ID)` | `candidates.application_id` | `CON-001` | DB constraint test rejecting duplicate application_id | Backend Core | READY_FOR_REVIEW |
| `GOAL-001 / NFR-001`| `DRV-F-002 / ADR-005` | `VAL-003, VAL-004` | `candidates.stage, status, draft_revisions.status` | `CON-004, CON-005, CON-008` | Integration test blocking Phase A operation when guard fails | Backend Core | READY_FOR_REVIEW |
| `GOAL-003 / NFR-002`| `DRV-F-010 / ADR-005` | `ENT-005 (Audit Log)` | `audit_logs.created_at, payload_json` | `CON-015, IDX-006` | DB permission test verifying UPDATE and DELETE are revoked | Backend Core | READY_FOR_REVIEW |
| `GOAL-004 / NFR-003`| `DRV-F-005 / ADR-003` | `ENT-003 (Send Operation)` | `logical_send_operations.draft_revision_id` | `CON-010` | Parallel transaction test verifying DB UNIQUE conflict handling | Backend Core | READY_FOR_REVIEW |
| `CAP-005 / NFR-004`| `DRV-F-007 / ADR-004` | `ENT-004 (Provider Attempt)`| `provider_attempts.error_code, error_message, logical_send_operations.failure_category` | `CON-012` | Integration test normalizing Resend errors into human-readable messages | Backend Core | READY_FOR_REVIEW |
| `ADI-001` | `DRV-F-007 / ADR-002` | `ENT-003, ENT-004` | `logical_send_operations.provider_name, provider_attempts.attempt_status` | `CON-011, CON-014, TXN-002` | Mock HTTP test asserting Phase B timeout does not hold DB locks | Backend Core | READY_FOR_REVIEW |

---

## 2. Traceability Metrics & Audit Statistics

- **Total Upstream Material Requirements**: 17
- **Covered Database Objects**: 17
- **Blocked Requirements**: 0
- **Stale Inputs**: 0
- **Orphan Requirements Count**: 0
- **Orphan Tables / Columns Count**: 0
- **Orphan Indexes Count**: 0
- **Missing Constraints Count**: 0
- **Missing Downstream Owners Count**: 0
- **Missing Verification Strategies Count**: 0
- **Overall Traceability Coverage**: 100%
