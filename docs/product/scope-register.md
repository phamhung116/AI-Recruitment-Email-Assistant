# Product Scope Register

## 1. Summary Statistics

- Total Evaluated Capabilities: 12
- Accepted MVP: 9
- Accepted LATER: 1
- Rejected Scope Creep: 2

## 2. Capability Register

| ID | Capability | Source | Pain Linkage | Core Job Linkage | Recommendation | Disposition | Decision Date | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `SCR-001` | Candidate import and identity validation | `CAP-001` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Required input for the guarded communication workflow. |
| `SCR-002` | Status mapping and contradiction blocker | `CAP-002` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Core brand-safety control. |
| `SCR-003` | Fixed protected templates | `CAP-003` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Minimal controllable content source. |
| `SCR-004` | Deterministic safety guard | `CAP-004` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Mandatory pre-provider gate. |
| `SCR-005` | HR inspection and send confirmation | `CAP-005` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Keeps the recruiter responsible for the final action. |
| `SCR-006` | Single-candidate real-email provider | `CAP-006` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Explicitly reconfirmed by the user. |
| `SCR-007` | Logical send operation and duplicate guard | `CAP-007` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Required for safe provider execution. |
| `SCR-008` | Decision correction | `CAP-008` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Handles a material post-send business decision change. |
| `SCR-009` | Immutable audit trail | `CAP-009` | `PROB-001` | `JOB-001` | MVP | `ACCEPT_MVP` | 2026-08-17 | Required for accountable real-email operations. |
| `SCR-010` | Advisory LLM semantic review | Existing prototype | `PROB-001` | `JOB-001` | LATER | `ACCEPT_LATER` | 2026-08-17 | Useful but must not block or control the real-email core path. |
| `SCR-011` | Batch or automatic send | User scope boundary | None | None | REJECT | `REJECT_SCOPE_CREEP` | 2026-08-17 | Creates a second, higher-risk product track. |
| `SCR-012` | AI hiring decision or CV screening | User scope boundary | None | None | REJECT | `REJECT_SCOPE_CREEP` | 2026-08-17 | Outside the communication-safety core job. |
