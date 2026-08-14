# Business Analysis Plan & Checkpoint

- **Mode**: gap-analysis
- **Execution Profile**: standard
- **Started At**: 2026-08-12T10:57:00+07:00
- **Deadline At**: 2026-08-12T11:42:00+07:00
- **Status**: READY_FOR_HANDOFF

## 1. Scope & Constraints

- **In Scope**: Final semantic correction and gap remediation for Team1 Recruitment Mail Guard based on approved product spec `docs/product/product.md` (APPROVED_BASELINE_FOR_BA v1.0.1). Covers 4 State Transition Specs (including full Decision Correction & Logical Send Operation failure handling), NFR-001 to NFR-004 normalization, source ID integrity (mapping non-existent DEC-001/002 to valid GOAL/CAP/BR IDs), Stage-Decision Policy Table correction (removing DECISION_CORRECTION as hiring decision), controlled anti-duplicate delivery guarantees, standardized assumptions (ASM-001, ADI-001), 22 Given-When-Then ACs, and 100% Traceability. Upstream Drift Classification: `NON_MATERIAL_UPSTREAM_NORMALIZATION`.
- **Out of Scope**: Batch sending, auto sending, template CRUD, LLM in core flow, manager approval, provider selection, architecture, database schema, UI design, API design, tech stack. (RabbitMQ, Redis, Celery, Outbox are legacy implementation context only).
- **Stop Condition**: Resolution of all BA gaps, validator passing, manual checks verification, and User review without self-approval or handoff to Architecture.

## 2. Input Inventory & Fingerprints

| Input Path | Availability | Approval State | Fingerprint (SHA-256) | Status |
| :--- | :--- | :--- | :--- | :--- |
| `docs/product/product.md` | `required` | APPROVED_BASELINE_FOR_BA (v1.0.1) | `17b10266e440729d4c55a9e0b1a41ee5c6494700afab3878743df9cdbcff4a6b` | Valid Primary Source of Truth |
| `docs/product-requirements.md` | `optional` | Legacy Proposal | `5717643ce4bb33cfc2394ae1b997c6ce2ea87bfbd6c694fca2fa0c1efecac5bc` | Supporting Context |
| `README.md` | `optional` | Legacy Spec | `f6a422119ef5f60bdf739ecaaef2c6e6df6ceebdbdfbc44b80b7e4113e61ff1b` | Legacy Implementation Context |

## 3. Work Items & Status

- [x] Step 1: Perform gap analysis on BA artifacts against product source `docs/product/product.md`
- [x] Step 2: Complete 4 formal State Transition Specifications (Application Decision, Draft Revision, Logical Send Operation, Decision Correction)
- [x] Step 3: Normalize NFR-001 to NFR-004 with full FR quality contract and RTM integration
- [x] Step 4: Remove invalid source references (DEC-001, DEC-002, SPEC-001) and replace with verified product IDs (`GOAL-001`, `GOAL-002`, `CAP-001`..`CAP-009`, `BR-001`..`BR-005`, `DEC-003`..`DEC-005`)
- [x] Step 5: Fix Stage-Decision Policy Table (remove DECISION_CORRECTION as hiring decision; require valid stage decision during correction) with Fail-Closed behavior
- [x] Step 6: Clarify Application Identity (Globally Unique Application ID, Position as attribute) and rename FR-012
- [x] Step 7: Complete Decision Correction & Logical Send Operation failure state transitions (retryable vs content/address validation FAILED_TERMINAL)
- [x] Step 8: Standardize anti-duplicate guarantees to controlled operation identity reuse; document provider physical duplicate risk
- [x] Step 9: Reclassify assumptions (ASM-001 header contract as validation rule, ASM-002 sync response as ADI-001, standardize remaining ASM-001)
- [x] Step 10: Expand to 22 Given-When-Then Acceptance Criteria covering 3 correction outcomes, deterministic blockers, and human-readable messages
- [x] Step 11: Synchronize RTM (`docs/ba/requirements-traceability.md`), perform Upstream Drift Check against Product v1.0.1 (`NON_MATERIAL_UPSTREAM_NORMALIZATION`), run `validate_ba_state.py`, and close Approval Gate (`APPROVED`).

## 4. Key Decisions & Open Questions

- **Product Source Mapping Alignment**: `DEC-001` and `DEC-002` were non-existent IDs in `product.md`. BA requirements previously referencing them have been re-mapped to confirmed Product Capability/Goal/Rule IDs (`GOAL-002`, `CAP-006` for Real-Email MVP; `GOAL-001`, `CAP-002`, `BR-001`, `BR-002` for Contradiction Scope Boundary). `DEC-003`, `DEC-004`, and `DEC-005` are confirmed Product Spec Section 9 decisions.
- **DEC-003**: Minimal Decision Correction Workflow for MVP. Normal Send remains HARD_BLOCKED after prior send. HR explicitly triggers `Create decision correction` with mandatory rationale, explicit correction email body, side-by-side prior vs new comparison with high-visibility warning, and explicit final confirmation. History preserved. Retry allowed on unaccepted correction without creating duplicate drafts. Communicated outcome is updated ONLY after provider returns `PROVIDER_ACCEPTED`. Manager approvals moved to LATER. Pure deterministic control, no LLM intervention.
- **DEC-004**: Logical Send Operation frozen upon Send. 3 explicit outcomes: `PROVIDER_ACCEPTED` (updates communicated decision, no inbox guarantee, no resend), `DEFINITIVE_FAILURE` (retryable failure transitions to `SENDING_UNCONFIRMED` on same operation; content/address validation failure transitions to `FAILED_TERMINAL` requiring edit & new revision), `DELIVERY_UNKNOWN` (timeout/network loss, status reconciliation required before retry, normal send blocked, unconfirmed warning displayed). Verification required before retry. HR manual status override permitted with Audit Log warning. Architecture handoff for idempotency headers/reconciliation. Invariant: At most one Logical Send Operation may ever be created for each Draft Revision. A Logical Send Operation may contain multiple Provider Attempts.
- **DEC-005**: Fixed Pre-seeded Templates for Core Journey (`INTERVIEW_INVITATION`, `REJECTION_AFTER_CV`, `OFFER_EMAIL`, `REJECTION_AFTER_INTERVIEW`, `DECISION_CORRECTION`). No Template CRUD UI/API in MVP. Content divided into Decision-Critical (read-only, rendered from verified data) vs Editable (greetings, closing, notes). Edits create new Draft Revision, invalidate Ready-to-Send state, re-run deterministic checks. Subject validated against decision. Pure deterministic enforcement, LLM semantic review in LATER.
- **OQ-001**: None currently blocking BA normalization.

## 5. Checkpoint & Exact Next Action

- **Current Checkpoint**: Approval Gate officially closed. All BA artifacts approved by User / Product Owner on 2026-08-12 based on Product Baseline v1.0.1 (Fingerprint: `17b10266e440729d4c55a9e0b1a41ee5c6494700afab3878743df9cdbcff4a6b`). Status updated to `READY_FOR_HANDOFF`.
- **Exact Next Action**: BA artifacts are ready for Architecture handoff. Await User command to initiate Architecture phase.

