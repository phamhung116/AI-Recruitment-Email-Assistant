# Canonical Product Specification: Recruitment Mail Guard (Minimal Real-Email MVP)

- **Document Status**: APPROVED_BASELINE_FOR_BA
- **Version**: 1.0.1
- **Last Updated**: 2026-08-12

## 1. Document Status & Versioning
Official Baseline Specification for Team1 Recruitment Mail Guard. Version 1.0.1 approved by User on 2026-08-12 following non-material BA reconciliation normalization for handoff to Business Analysis (`team1-ba`).

## 2. Product Vision
Provide an unyielding deterministic safety guard for HR recruitment communications, ensuring zero brand-damaging contradictory decision emails per job application and stage.

## 3. Problem Statement
- `PROB-001`: Risk of sending embarrassing, brand-damaging contradictory decision emails (e.g. Rejection after Offer, or wrong candidate name) due to manual copy-paste errors across spreadsheets and email clients.

## 4. Users & Personas
- Primary User (`USR-001`): Recruitment Specialist / HR Recruiter who prepares and issues individual candidate outcome notifications.
- Secondary Users: HR Operations Manager (Auditor).

## 5. Core Job-to-be-Done
- `JOB-001`: Issue verified, accurate candidate outcome emails via a real email provider for a specific job application and stage, ensuring zero contradictory communications for defined deterministic business rules.

## 6. Product Goals
- `GOAL-001`: Prevent 100% of defined & tested deterministic contradiction rules within the same `Application ID` + `Stage/Milestone`.
- `GOAL-002`: Issue single-candidate outcome emails via a real email provider with manual HR inspection and one-click Send confirmation.
- `GOAL-003`: Provide a controlled, auditable Decision Correction Workflow when business decisions change post-send.
- `GOAL-004`: Prevent duplicate email send operations during network timeouts or double-clicks.

## 7. Non-Goals
- `NG-001`: Automatic or background batch email sending (No automated campaigns).
- `NG-002`: Automated candidate pass/fail hiring decisions by AI.
- `NG-003`: CV screening, candidate scoring, or resume parsing.
- `NG-004`: Full Template Management UI or custom template CRUD.
- `NG-005`: Guaranteeing 100% inbox delivery or bounce tracking in MVP (Success = Provider accepted request).

## 8. Success Metrics
- `OUT-001`: 100% of defined and tested deterministic contradiction rules are enforced prior to provider transmission, backed by immutable audit trail.

## 9. MVP Scope
Single candidate real-email sending via provider, mandatory Application ID, Stage/Milestone contradiction tracking, Decision Revision tracking, pre-send draft superseding, Minimal Decision Correction Workflow (DEC-003), Logical Send Operation with 3 outcomes (`PROVIDER_ACCEPTED`, `DEFINITIVE_FAILURE`, `DELIVERY_UNKNOWN`) (DEC-004), and Fixed Pre-seeded Templates with Decision-Critical vs Editable content separation (DEC-005).

## 10. Explicit Out of Scope
Batch sending, auto sending, bounce tracking, marketing campaigns, LLM blocking core flow, async queues as product capabilities, multi-level manager approval for corrections, automatic retries in UNKNOWN state, Template CRUD UI, custom placeholders, AI free-text semantic review.

## 11. Core Journey
1. Import candidate list from Excel with mandatory `Application ID`, `Stage`, and verified hiring outcome decision.
2. Render email draft from fixed pre-seeded template, separating Decision-Critical (read-only) vs Editable content.
3. Run Deterministic Safety Guard checking required fields, email format, placeholder resolution, candidate name alignment, and prior send history for `Application ID + Stage`.
4. HR inspects draft and edits allowed fields if needed (triggering a new Draft Revision and re-check).
5. HR clicks Send. System creates Logical Send Operation. Provider accepts or fails. System records Audit Log and updates communicated outcome.

## 12. Capability Requirements

- `CAP-001`: Candidate Excel Import & Data Normalization
  - Description: Import candidate list from Excel with mandatory Application ID, Stage, Candidate Name, Email, and verified Status.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Required to seed verified candidate application data into the pipeline.
  - Disposition: MVP
  - Acceptance Criteria: `AC-001`
  - Status: confirmed

- `CAP-002`: Strict Status-to-Email Mapping & Contradiction Blocker
  - Description: Block draft generation and send button if requested email type contradicts prior send history for Application ID + Stage.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Core safety guard preventing contradictory communications.
  - Disposition: MVP
  - Acceptance Criteria: `AC-001`
  - Status: confirmed

- `CAP-003`: Fixed Pre-seeded Template Rendering & Content Separation
  - Description: Render draft separating Decision-Critical (read-only) content from Editable content.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Prevents HR from accidentally editing outcome meaning while allowing tone edits.
  - Disposition: MVP
  - Acceptance Criteria: `AC-004`
  - Status: confirmed

- `CAP-004`: Deterministic Safety Guard Engine
  - Description: Run checks for candidate name alignment, email format, required placeholders, and decision revisions.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Deterministic rule verification prior to enabling send button.
  - Disposition: MVP
  - Acceptance Criteria: `AC-004`
  - Status: confirmed

- `CAP-005`: HR Review Queue & Ready-to-Send Gate
  - Description: Single candidate inspection queue presenting draft with explicit warnings and one-click Send button.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Human-in-the-loop inspection interface.
  - Disposition: MVP
  - Acceptance Criteria: `AC-001`
  - Status: confirmed

- `CAP-006`: Real Email Provider Integration
  - Description: Send individual outcome email via provider API; success defined as provider accepted request.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Core real-email delivery execution.
  - Disposition: MVP
  - Acceptance Criteria: `AC-003`
  - Status: confirmed

- `CAP-007`: Logical Send Operation & Anti-Duplicate Safeguard
  - Description: Create Logical Send Operation freezing draft; enforce at most one Logical Send Operation per Draft Revision, allow multiple Provider Attempts during retries, and reuse operation identity. Physical duplicate delivery on provider network is a residual risk for Architecture evaluation.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Prevents double-sending emails on network failure or double-click.
  - Disposition: MVP
  - Acceptance Criteria: `AC-003`
  - Status: confirmed

- `CAP-008`: Decision Correction Workflow
  - Description: Explicit HR workflow requiring rationale and side-by-side warning to issue corrected decision post-send.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Handles business decision changes after initial email sent.
  - Disposition: MVP
  - Acceptance Criteria: `AC-001`
  - Status: confirmed

- `CAP-009`: Immutable Audit Trail
  - Description: Log all generation, approval, cancellation, send operations, and correction rationales.
  - Pain Linkage: `PROB-001`
  - Core Job Linkage: `JOB-001`
  - Rationale: Provides full traceability for HR operations.
  - Disposition: MVP
  - Acceptance Criteria: `AC-001`
  - Status: confirmed

## 13. Business Rules
- `BR-001`: Contradictions are evaluated strictly per Application ID + Stage/Milestone.
- `BR-002`: After an email is accepted by provider, opposing results for the same Application ID + Stage are HARD_BLOCKED on normal Send.
- `BR-003`: Post-send decision changes require the Decision Correction Workflow with mandatory rationale and explicit side-by-side confirmation.
- `BR-004`: Send confirmation creates a Logical Send Operation bound to Draft Revision ID, freezing draft content during flight.
- `BR-005`: Edits to editable content create a new Draft Revision, invalidate Ready-to-Send status, and re-run deterministic checks.

## 14. Relevant States & Edge Cases
- `DRAFT_PENDING_CHECK`: Draft generated, awaiting deterministic safety guard validation.
- `READY_TO_SEND`: All deterministic checks passed; Send button enabled.
- `BLOCKED_DETERMINISTIC`: One or more deterministic rules failed (e.g. contradiction, missing name, invalid email). Send disabled.
- `SENDING_UNCONFIRMED`: Logical Send Operation created, request in flight to Provider. Draft frozen.
- `PROVIDER_ACCEPTED`: Email request accepted by provider. Final state for this revision.
- `DEFINITIVE_FAILURE`: Provider returned definitive error. Transient failure enables retry on same operation ID; content/address validation failure transitions operation to FAILED_TERMINAL and requires editing draft content/email to create a new Draft Revision.
- `DELIVERY_UNKNOWN`: Timeout or network error. Normal Send blocked; Retry Send (same operation after status verification) or manual verification required.
- `CORRECTION_DRAFT`: Draft created via Decision Correction Workflow, awaiting rationale and final confirmation.

## 15. Testable Acceptance Criteria
- `AC-001`: Given a sent email for Application ID APP-101 at Stage INTERVIEW with outcome REJECT, When HR attempts to send an OFFER draft for APP-101 at INTERVIEW, Then the system MUST HARD_BLOCK the Send button and display a link to Create decision correction.
- `AC-002`: Given a sent email for APP-101 at Stage CV_SCREENING with outcome PASS_CV, When HR creates an outcome email for APP-101 at Stage INTERVIEW with outcome REJECT_INTERVIEW, Then the system MUST allow the draft generation and pass contradiction check.
- `AC-003`: Given a Logical Send Operation in progress or retry state for Revision REV-001, When HR double-clicks Send or reloads the browser, Then the system MUST NOT create a second Logical Send Operation for the same Draft Revision and MUST reuse the original operation identity.
- `AC-004`: Given a rendered draft, When HR edits the greeting text, Then a new Draft Revision is created and re-validated. When HR attempts to edit the Decision-Critical outcome sentence, Then the system MUST prevent the edit.

## 16. Business Assumptions
- `ASM-001`: HR recruiter is responsible for the accuracy of source candidate hiring decisions. The system validates Excel header contract, required values, and data format upon import.

## 17. Constraints & Dependencies
- `CON-001`: Real email provider API availability for sending.
- `CON-002`: All defined mandatory Deterministic Safety Guard checks must complete and pass before any Provider Attempt may be initiated.

## 18. Product Risks
- `RSK-001`: Provider network instability resulting in DELIVERY_UNKNOWN state requiring HR manual status verification.
- `RSK-002`: Provider physical duplicate delivery residual risk. Provider network may deliver email twice despite single request/operation identity.

## 19. Downstream Questions
1. How will the selected Email Provider API support idempotency keys or request deduplication headers to satisfy DEC-004?
2. What status reconciliation mechanism will be implemented to verify provider status during DELIVERY_UNKNOWN state recovery?
3. `ADI-001`: What Email Provider integration model (Synchronous HTTP vs Asynchronous Webhook/Polling) will be selected by Architecture to normalize transmission results into PROVIDER_ACCEPTED, DEFINITIVE_FAILURE, and DELIVERY_UNKNOWN? How will Architecture handle idempotency headers, provider deduplication, and status reconciliation?

## 20. Traceability & BA_BYPASS Log
- BA Reconciliation Log: `docs/product/ba-reconciliation.md`
- BA_BYPASS Status: N/A

## 21. Approval Record
- Confirmed by User on 2026-08-12 (v1.0.1 Non-Material Normalizations)
- Status: APPROVED_BASELINE_FOR_BA

