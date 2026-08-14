# Business Analysis Specification: Recruitment Mail Guard (Minimal Real-Email MVP)

- **Status**: READY_FOR_HANDOFF
- **Version**: 1.2.0-BA
- **Last Updated**: 2026-08-12

## 1. Executive Summary
This document defines the formal business requirements, AS-IS and TO-BE process workflows, deterministic business rules, state transitions, use cases, and testable acceptance criteria for Team1 Recruitment Mail Guard based on the approved product baseline `docs/product/product.md` (APPROVED_BASELINE_FOR_BA v1.0.1).

## 2. Sources & Approval State
- **Primary Source of Truth**: `docs/product/product.md` (Status: `APPROVED_BASELINE_FOR_BA`, Version: 1.0.1, Fingerprint: `17b10266e440729d4c55a9e0b1a41ee5c6494700afab3878743df9cdbcff4a6b`, Approved on 2026-08-12).
- **Product Decisions**: `DEC-003` (Decision Correction Workflow), `DEC-004` (Logical Send Operation & Anti-Duplicate), `DEC-005` (Fixed Pre-seeded Templates & Content Separation). *(Note: Prior references to DEC-001/002 have been re-mapped to confirmed Product Capability/Goal/Rule IDs: GOAL-002 & CAP-006 for Real-Email MVP; GOAL-001, CAP-002, BR-001, BR-002 for Contradiction Scope Boundary).*
- **Product Problem & Goals**: `PROB-001`, `GOAL-001`, `GOAL-002`, `GOAL-003`, `GOAL-004`.
- **Product Capabilities**: `CAP-001` through `CAP-009`.
- **Product Business Rules**: `BR-001` through `BR-005`.
- **BA Approval State**: Approved by User / Product Owner on 2026-08-12 (`APPROVED`).

## 3. Business Objectives
- `OBJ-001`: Prevent 100% of defined & tested deterministic contradiction rules for candidate decision emails within the same `Application ID` + `Stage/Milestone`.
- `OBJ-002`: Eliminate manual copy-paste errors when preparing candidate notifications from Excel records.
- `OBJ-003`: Provide an immutable, auditable log of candidate outcome communications and post-send decision corrections.
- `OBJ-004`: Prevent creating duplicate Logical Send Operations and ensure retries reuse existing operation identity during network timeouts, double-clicks, or page reloads.

## 4. Scope & Out of Scope
### In Scope (MVP)
- Candidate Excel Import with mandatory globally unique `Application ID`, `Stage`, `Candidate Name`, `Email`, `Status`.
- Contradiction guard per `Application ID + Stage`.
- Fixed pre-seeded templates for core journey (`INTERVIEW_INVITATION`, `REJECTION_AFTER_CV`, `OFFER_EMAIL`, `REJECTION_AFTER_INTERVIEW`, `DECISION_CORRECTION`).
- Content separation into Decision-Critical (read-only) vs Editable fields.
- Deterministic Safety Guard check before Send button enablement.
- Single candidate real-email sending via provider API (success = provider accepted).
- Logical Send Operation with 3 outcomes (`PROVIDER_ACCEPTED`, `DEFINITIVE_FAILURE`, `DELIVERY_UNKNOWN`).
- Minimal Decision Correction Workflow for post-send decision changes (`DEC-003`).
- Immutable Audit Log and processing history.

### Out of Scope (LATER / REJECT)
- Batch sending, automated sending, marketing campaigns.
- Template CRUD UI, custom placeholders, multiple templates per type.
- LLM/Agent blocking core flow or automated hiring decisions.
- Multi-level manager approval workflows.
- Bounce tracking, delivery webhooks, campaign analytics.
- Async messaging infrastructure (RabbitMQ, Celery, Redis Lock, Outbox) as product requirements.

## 5. Stakeholders & Actors
- `ACT-001` **HR Recruiter / Specialist** (Primary Actor): Manages candidate records, inspects rendered drafts, edits allowed fields, issues outcome emails, and initiates decision corrections.
- `ACT-002` **Candidate** (Recipient / External Actor): Receives outcome communications sent by HR.
- `ACT-003` **Email Provider API** (External System Dependency): External service executing real email delivery upon receiving send requests.

## 6. AS-IS & TO-BE Workflows

### AS-IS Process Analysis (Manual Workflow)
1. HR receives candidate hiring decisions from hiring managers via chat, email, or meeting notes.
2. HR manually locates the candidate row in a master Excel spreadsheet and checks position and stage.
3. HR opens a Word/Docs template, manually copy-pastes candidate name, position, and interview details.
4. HR opens Gmail/Outlook, pastes recipient email and rendered body, and clicks send manually.
- **Risk Points**:
  - Wrong recipient email or miscopied candidate name.
  - Contradictory outcome sent (e.g. Rejection sent after an oral Offer).
  - Duplicate email sent due to confusion over whether prior email was sent.
  - Uncertainty whether email was delivered when network drops.

### Stage–Decision–Email Type Policy Table

| Stage / Milestone | Allowed Decision | Pre-seeded Template / Email Type | Guard Behavior on Unsupported Combination |
| :--- | :--- | :--- | :--- |
| `CV_SCREENING` | `PASS_CV` | `INTERVIEW_INVITATION` | Fail closed (`STATUS_EMAIL_MISMATCH`) |
| `CV_SCREENING` | `REJECT_CV` | `REJECTION_AFTER_CV` | Fail closed (`STATUS_EMAIL_MISMATCH`) |
| `INTERVIEW` | `PASS_INTERVIEW` | `OFFER_EMAIL` | Fail closed (`STATUS_EMAIL_MISMATCH`) |
| `INTERVIEW` | `REJECT_INTERVIEW` | `REJECTION_AFTER_INTERVIEW` | Fail closed (`STATUS_EMAIL_MISMATCH`) |
| `*` (Any unmapped stage, decision, or email type) | Unmapped | None | **Fail Closed** (`STATUS_UNSUPPORTED` / `STATUS_EMAIL_MISMATCH`) |

#### Policy Enforcement Rules
1. **Strict Stage-Decision Policy**: A draft or send operation can only be created if the `(Stage, Decision, Email Type)` triplet strictly matches an allowed entry in the policy table. Any unsupported stage, decision, or email type MUST fail closed with `STATUS_UNSUPPORTED` or `STATUS_EMAIL_MISMATCH`.
2. **Correction Workflow Policy**: `DECISION_CORRECTION` is a specialized communication workflow and email template, NOT a hiring decision. When HR uses the Decision Correction Workflow (`DEC-003`), the new decision being issued MUST STILL be a valid allowed hiring decision for that stage per the policy table (e.g. at `INTERVIEW`, changing from `REJECT_INTERVIEW` to `PASS_INTERVIEW`).

### TO-BE Workflows

#### `UC-001`: Candidate Excel Import & Application Identity Validation
- **Trigger**: HR uploads an Excel file or selects an application row.
- **Preconditions**: Excel file is accessible `.xlsx`.
- **Main Flow**:
  1. HR selects Excel file for import.
  2. System validates presence of mandatory header contract (`Application ID`, `Stage`, `Candidate Name`, `Email`, `Status`).
  3. System verifies `Application ID` global uniqueness.
  4. System displays imported Application record ready for draft generation.
- **Alternate Flow**: If optional attributes (e.g. `position`, `interview_time`, `note`) are present, system imports them for display and placeholder resolution. Position is treated as a descriptive attribute, not part of identity uniqueness.
- **Exception Flow 1**: If mandatory headers or candidate values (`Application ID`, `Stage`, `Candidate Name`, `Email`, `Status`) are missing or invalid, system rejects the row with `CANDIDATE_HEADER_INVALID` or `CANDIDATE_REQUIRED_VALUE_MISSING`.
- **Exception Flow 2**: If `Application ID` already exists in system, system rejects the row with `DUPLICATE_APPLICATION_ID`.
- **Postconditions**: Validated Application record is stored and ready for template rendering.
- **Data Involved**: `Application ID`, `Stage`, `Candidate Name`, `Email`, `Status`, `Position`, `Interview Time`.

#### `UC-002`: Template Rendering & Draft Content Separation
- **Trigger**: HR selects a validated Application to generate an outcome draft.
- **Preconditions**: Candidate stage and decision map to an allowed pre-seeded template per Policy Table.
- **Main Flow**:
  1. System selects pre-seeded template matching Stage and Decision.
  2. System renders subject and body.
  3. System locks **Decision-Critical content** (`Application ID`, `Stage`, `Decision`, `Recipient`, `Email Type`, core outcome sentence) as Read-Only.
  4. System opens **Editable content** (greeting, closing, non-outcome notes) for HR inspection.
- **Exception Flow**: If candidate status is `PENDING` or unmapped, system blocks generation with `STATUS_PENDING`.
- **Postconditions**: Draft Revision 1 generated in `DRAFT_PENDING_CHECK` state.

#### `UC-003`: Editable Content Revision & Safety Guard Invalidation
- **Trigger**: HR edits allowed phrasing in the Editable content area.
- **Preconditions**: Draft is in `READY_TO_SEND` or `DRAFT_PENDING_CHECK` state.
- **Main Flow**:
  1. HR modifies greeting or closing notes.
  2. System increments Draft Revision ID (`REV-002`).
  3. System invalidates prior `READY_TO_SEND` status and sets status to `DRAFT_PENDING_CHECK`.
  4. System re-executes Deterministic Safety Guard checks.
  5. If checks pass, status transitions to `READY_TO_SEND` and Send button enables.
- **Exception Flow**: If HR attempts to edit Decision-Critical content, system rejects the edit action.
- **Postconditions**: Active Draft Revision updated; Send button enabled only after passing re-check.

#### `UC-004`: Contradiction Detection & Send Hard Block
- **Trigger**: HR attempts to generate or send an outcome email.
- **Preconditions**: Prior sent email exists for the same `Application ID + Stage`.
- **Main Flow**:
  1. System queries communication history for `Application ID` and `Stage`.
  2. If prior sent email has an opposing decision (e.g. `REJECT` sent, now requesting `OFFER`), system triggers `HARD_BLOCK`.
  3. System locks normal Send button and displays link: `Create decision correction`.
- **Alternate Flow**: If prior sent email is for a different stage (e.g. `PASS_CV` at `CV_SCREENING`, now `REJECT_INTERVIEW` at `INTERVIEW`), system allows normal draft generation (`AC-013`).
- **Postconditions**: Opposing outcome email blocked on normal Send flow.

#### `UC-005`: Logical Send Operation Execution & Outcome Handling
- **Trigger**: HR clicks Send on a `READY_TO_SEND` draft.
- **Preconditions**: All deterministic rules passed; active Draft Revision frozen.
- **Main Flow**:
  1. HR clicks Send button.
  2. System creates a unique `Logical Send Operation` bound to active Draft Revision ID and sets status to `SENDING_UNCONFIRMED`.
  3. System initiates provider transmission attempt.
  4. Provider confirms request acceptance (`PROVIDER_ACCEPTED`).
  5. System transitions status to `PROVIDER_ACCEPTED`, records Audit Log, and updates current communicated outcome.
- **Alternate Flow 1 (Definitive Failure)**: Provider rejects request (e.g. invalid recipient syntax). System transitions to `DEFINITIVE_FAILURE`, displays readable error, and enables Retry or Draft Edit.
- **Alternate Flow 2 (Delivery Unknown)**: Provider transmission times out or connection drops. System transitions to `DELIVERY_UNKNOWN`, blocks normal Send, displays warning "Unconfirmed whether provider received email", and enables Retry (reusing same Logical Send Operation).
- **Postconditions**: Outcome recorded in Audit Trail.

#### `UC-006`: Status Reconciliation & Anti-Duplicate Retry
- **Trigger**: HR clicks `Retry Send` on a `DELIVERY_UNKNOWN` or `DEFINITIVE_FAILURE` draft.
- **Preconditions**: Draft is in `DELIVERY_UNKNOWN` or `DEFINITIVE_FAILURE` state.
- **Main Flow (Delivery Unknown Recovery)**:
  1. For `DELIVERY_UNKNOWN`, system MUST perform status reconciliation before retry to verify if provider received the email.
  2. If provider verification confirms receipt, system transitions status to `PROVIDER_ACCEPTED` and stops retry.
  3. If provider verification confirms email was not received, system re-issues send request using the SAME `Logical Send Operation` (same operation ID and idempotency identity).
- **Alternate Flow 1 (Retryable Definitive Failure)**: If draft is in `DEFINITIVE_FAILURE` due to a transient/retryable error (e.g. 5xx or connection drop post-connect), status reconciliation is not required. HR clicks `Retry Send`, and system re-issues send request directly on the SAME `Logical Send Operation`, creating a new Provider Attempt.
- **Alternate Flow 2 (Content/Address Validation Failure)**: If `DEFINITIVE_FAILURE` is caused by content or address validation error, system transitions operation to `FAILED_TERMINAL`. Retrying old content is blocked. HR must edit editable fields or email address, creating a NEW `Draft Revision`.
- **Alternate Flow 3 (Manual HR Override)**: HR manually verifies in email client, selects "Provider Accepted" or "Provider Not Received" with mandatory warning acknowledgment. System logs Audit Event.
- **Exception Flow**: If HR double-clicks Send or reloads browser during in-flight send, system rejects creation of a second Logical Send Operation (`AC-007`).
- **Postconditions**: At most one Logical Send Operation may ever be created for each Draft Revision; retries reuse existing operation identity.

#### `UC-007`: Decision Correction Workflow (`DEC-003`)
- **Trigger**: HR clicks `Create decision correction` on a HARD_BLOCKED opposing outcome.
- **Preconditions**: Prior email accepted by provider for same `Application ID + Stage`.
- **Main Flow**:
  1. HR enters new valid hiring decision for current stage and mandatory change rationale (`Rationale`).
  2. System renders `DECISION_CORRECTION` template explicitly stating this updates a prior decision.
  3. System displays confirmation modal showing side-by-side comparison (prior decision, timestamp, recipient vs new decision) and high-visibility warning.
  4. HR checks final manual confirmation and clicks Send Correction.
  5. System executes Logical Send Operation. Communicated decision is updated to the new decision ONLY AFTER provider returns `PROVIDER_ACCEPTED`.
- **Exception Flow 1**: If HR attempts to create a 2nd correction draft while one is active/pending, system rejects the action (`AC-018`).
- **Exception Flow 2**: If correction provider response is `DEFINITIVE_FAILURE` or `DELIVERY_UNKNOWN`, system applies standard exception handling (`AC-019`, `AC-020`); communicated decision remains unchanged until `PROVIDER_ACCEPTED`.
- **Postconditions**: Original email and Correction email both preserved in immutable Audit Trail.

## 7. State Transition Specifications

### 1. Application Decision State Transitions
- **`DRAFT_DECISION` -> `COMMUNICATED`**:
  - Trigger: Email Provider accepts send request for active Draft Revision.
  - Actor: `ACT-001` (HR Recruiter) via `ACT-003` (Email Provider).
  - Guard: Deterministic checks passed, Logical Send Operation in `PROVIDER_ACCEPTED`.
  - Result State: `COMMUNICATED`.
  - Rejected Behavior: Decision remains uncommunicated; status set to `DEFINITIVE_FAILURE` or `DELIVERY_UNKNOWN`.
  - Required Audit Event: `APPLICATION_DECISION_COMMUNICATED`.
- **`COMMUNICATED` -> `CORRECTED`**:
  - Trigger: Decision Correction email accepted by Provider (`DEC-003`).
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: `Create decision correction` executed with mandatory rationale and explicit user confirmation; provider returns `PROVIDER_ACCEPTED`.
  - Result State: `CORRECTED`.
  - Rejected Behavior: Status remains `COMMUNICATED`; original outcome stays active until provider acceptance.
  - Required Audit Event: `APPLICATION_DECISION_CORRECTED`.

### 2. Draft Revision State Transitions
- **`UNINITIALIZED` -> `DRAFT_PENDING_CHECK`**:
  - Trigger: HR selects Application to generate draft.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Application status maps to allowed template per Policy Table.
  - Result State: `DRAFT_PENDING_CHECK` (Revision ID `REV-001`).
  - Rejected Behavior: Generation blocked with error (`STATUS_PENDING` / `STATUS_UNSUPPORTED`).
  - Required Audit Event: `DRAFT_REVISION_CREATED`.
- **`DRAFT_PENDING_CHECK` -> `READY_TO_SEND`**:
  - Trigger: Deterministic Safety Guard validation completes.
  - Actor: System.
  - Guard: 100% of required fields, format checks, name alignment, and prior history rules pass.
  - Result State: `READY_TO_SEND`.
  - Rejected Behavior: Status set to `BLOCKED_DETERMINISTIC`; Send button disabled.
  - Required Audit Event: `SAFETY_GUARD_PASSED`.
- **`READY_TO_SEND` -> `DRAFT_PENDING_CHECK` (Re-edit)**:
  - Trigger: HR edits Editable content area.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Edit restricted to Editable content area only.
  - Result State: `DRAFT_PENDING_CHECK` (Revision ID incremented to `REV-002`).
  - Rejected Behavior: Edit rejected if attempting to modify Decision-Critical content.
  - Required Audit Event: `DRAFT_REVISION_UPDATED`.
- **`DRAFT_PENDING_CHECK` / `READY_TO_SEND` -> `SUPERSEEDED`**:
  - Trigger: New Draft Revision created for same Application ID + Stage before send.
  - Actor: System.
  - Guard: Newer revision ID exists for unsent draft.
  - Result State: `SUPERSEEDED`.
  - Rejected Behavior: Unsent revision remains active.
  - Required Audit Event: `DRAFT_REVISION_SUPERSEEDED`.

### 3. Logical Send Operation State Transitions
- **`UNINITIALIZED` -> `SENDING_UNCONFIRMED`**:
  - Trigger: HR clicks Send on `READY_TO_SEND` draft.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Active Draft Revision passes 100% deterministic checks; draft content frozen.
  - Result State: `SENDING_UNCONFIRMED`.
  - Rejected Behavior: Send request blocked; UI displays validation errors.
  - Required Audit Event: `LOGICAL_SEND_OPERATION_CREATED`.
- **`SENDING_UNCONFIRMED` -> `PROVIDER_ACCEPTED`**:
  - Trigger: Provider API responds with request acceptance confirmation.
  - Actor: `ACT-003` (Email Provider API).
  - Guard: Provider response code indicates accepted request.
  - Result State: `PROVIDER_ACCEPTED`.
  - Rejected Behavior: Transition to `DEFINITIVE_FAILURE` or `DELIVERY_UNKNOWN`.
  - Required Audit Event: `EMAIL_PROVIDER_ACCEPTED`.
- **`SENDING_UNCONFIRMED` -> `DEFINITIVE_FAILURE`**:
  - Trigger: Provider API returns definitive rejection error.
  - Actor: `ACT-003` (Email Provider API).
  - Guard: Provider error code indicates unaccepted request.
  - Result State: `DEFINITIVE_FAILURE`.
  - Behavioral Classification:
    - **Transient / Retryable Failure** (e.g. provider server 5xx or connection drop post-connect): HR clicks `Retry Send`. System reuses the SAME Logical Send Operation ID (incrementing Provider Attempt counter). Status transitions to `SENDING_UNCONFIRMED`.
    - **Content / Address Validation Failure** (e.g. malformed recipient email or payload syntax error): Operation transitions to `FAILED_TERMINAL` and is retired; old operation MUST NOT be reused to send modified content. HR must edit recipient email or editable content, creating a NEW `Draft Revision` (`REV-002`).
  - Required Audit Event: `EMAIL_PROVIDER_FAILED`.
- **`DEFINITIVE_FAILURE` -> `SENDING_UNCONFIRMED` (Retryable Failure Retry)**:
  - Trigger: HR clicks Retry Send on a draft in `DEFINITIVE_FAILURE` state caused by a transient/retryable provider error.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Failure is retryable; keeps original Logical Send Operation ID, idempotency identity, and frozen draft; creates a new Provider Attempt.
  - Result State: `SENDING_UNCONFIRMED`.
  - Rejected Behavior: Direct retry blocked if failure was due to content/address validation error.
  - Required Audit Event: `LOGICAL_SEND_OPERATION_RETRIED`.
- **`DEFINITIVE_FAILURE` -> `FAILED_TERMINAL` (Content/Address Validation Terminal Failure)**:
  - Trigger: Provider returns definitive failure caused by content or address validation error.
  - Actor: System.
  - Guard: Error classification indicates un-retryable payload/address error.
  - Result State: `FAILED_TERMINAL` (operation closed permanently and retired).
  - Consequence: HR must edit editable draft content or candidate email address, creating a new `Draft Revision` (`REV-002`). The retired Logical Send Operation is NEVER reused to send modified content; a new operation is created when the new Draft Revision is sent.
  - Required Audit Event: `LOGICAL_SEND_OPERATION_TERMINATED`.
- **`SENDING_UNCONFIRMED` -> `DELIVERY_UNKNOWN`**:
  - Trigger: Network connection timeout or unconfirmed provider response.
  - Actor: System.
  - Guard: No definitive provider response received within timeout window.
  - Result State: `DELIVERY_UNKNOWN`.
  - Rejected Behavior: N/A.
  - Required Audit Event: `EMAIL_DELIVERY_UNCONFIRMED`.
- **`DELIVERY_UNKNOWN` -> `PROVIDER_ACCEPTED` (Reconciliation / Manual Override)**:
  - Trigger: Provider status verification or HR manual override confirms receipt.
  - Actor: System / `ACT-001` (HR Recruiter).
  - Guard: Provider verification positive OR HR manual override with warning acknowledgment.
  - Result State: `PROVIDER_ACCEPTED`.
  - Rejected Behavior: Status remains `DELIVERY_UNKNOWN`.
  - Required Audit Event: `DELIVERY_UNKNOWN_RESOLVED_ACCEPTED`.
- **`DELIVERY_UNKNOWN` -> `SENDING_UNCONFIRMED` (Retry)**:
  - Trigger: HR clicks Retry Send after status verification confirms email not received.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Status verification confirms provider did not receive email; reuses SAME Logical Send Operation ID.
  - Result State: `SENDING_UNCONFIRMED`.
  - Rejected Behavior: Retry blocked if verification confirms email was already accepted.
  - Required Audit Event: `LOGICAL_SEND_OPERATION_RETRIED`.

*Invariant*: At most one Logical Send Operation may ever be created for each Draft Revision. A Logical Send Operation may contain multiple Provider Attempts.

### 4. Decision Correction State Transitions
- **`UNINITIALIZED` -> `CORRECTION_DRAFT`**:
  - Trigger: HR clicks `Create decision correction` on HARD_BLOCKED opposing outcome.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Prior email accepted by provider for same Application ID + Stage; no existing active correction draft (`AC-018`).
  - Result State: `CORRECTION_DRAFT`.
  - Rejected Behavior: Action blocked if another correction draft is currently pending.
  - Required Audit Event: `DECISION_CORRECTION_INITIATED`.
- **`CORRECTION_DRAFT` -> `DISCARDED` (Cancellation)**:
  - Trigger: HR cancels correction draft before confirming send.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Correction draft in `CORRECTION_DRAFT` state.
  - Result State: `DISCARDED` (Original communicated outcome remains active unchanged).
  - Rejected Behavior: Cannot cancel after transmission initiated.
  - Required Audit Event: `DECISION_CORRECTION_CANCELLED`.
- **`CORRECTION_DRAFT` -> `SENDING_UNCONFIRMED`**:
  - Trigger: HR confirms side-by-side comparison modal with mandatory rationale.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Rationale text non-empty, manual confirmation checked, deterministic rules pass, new decision valid for stage.
  - Result State: `SENDING_UNCONFIRMED`.
  - Rejected Behavior: Confirmation blocked if rationale is missing or empty.
  - Required Audit Event: `DECISION_CORRECTION_SUBMITTED`.
- **`SENDING_UNCONFIRMED` -> `PROVIDER_ACCEPTED` (Correction Success)**:
  - Trigger: Provider API responds with request acceptance confirmation for correction.
  - Actor: `ACT-003` (Email Provider API).
  - Guard: Provider response code indicates accepted request.
  - Result State: `PROVIDER_ACCEPTED`.
  - Resulting Outcome Update: **Communicated decision is updated to the corrected decision ONLY AFTER provider returns `PROVIDER_ACCEPTED`.** Prior decision set to `CORRECTED`.
  - Required Audit Event: `DECISION_CORRECTION_ACCEPTED`.
- **`SENDING_UNCONFIRMED` -> `DEFINITIVE_FAILURE` (Correction Failure)**:
  - Trigger: Provider API returns definitive error for correction transmission.
  - Actor: `ACT-003` (Email Provider API).
  - Guard: Provider error code indicates rejected request.
  - Result State: `DEFINITIVE_FAILURE`.
  - Resulting Outcome Update: **Communicated decision remains unchanged (prior outcome stays active)**; displays human-readable error (`AC-019`).
  - Required Audit Event: `DECISION_CORRECTION_FAILED`.
- **`DEFINITIVE_FAILURE` -> `SENDING_UNCONFIRMED` (Correction Retryable Failure Retry)**:
  - Trigger: HR clicks Retry Send on a correction draft in `DEFINITIVE_FAILURE` state caused by a transient/retryable provider error.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Failure is retryable; keeps original Logical Send Operation ID, idempotency identity, and frozen correction draft; creates a new Provider Attempt.
  - Result State: `SENDING_UNCONFIRMED`.
  - Resulting Outcome Update: **Prior communicated decision MUST remain unchanged until the correction receives `PROVIDER_ACCEPTED`.**
  - Required Audit Event: `DECISION_CORRECTION_RETRIED`.
- **`DEFINITIVE_FAILURE` -> `FAILED_TERMINAL` (Correction Terminal Failure)**:
  - Trigger: Correction send fails due to content or address validation error.
  - Actor: System.
  - Guard: Error classification indicates un-retryable payload/address error.
  - Result State: `FAILED_TERMINAL` (correction operation closed permanently).
  - Consequence: Modifying correction draft details requires creating a new Draft Revision. The retired operation is NEVER reused to send modified content.
  - Resulting Outcome Update: **Prior communicated decision MUST remain unchanged until a correction receives `PROVIDER_ACCEPTED`.**
  - Required Audit Event: `DECISION_CORRECTION_TERMINATED`.
- **`SENDING_UNCONFIRMED` -> `DELIVERY_UNKNOWN` (Correction Unconfirmed)**:
  - Trigger: Network connection timeout or unconfirmed provider response during correction.
  - Actor: System.
  - Guard: Response missing within timeout window.
  - Result State: `DELIVERY_UNKNOWN`.
  - Resulting Outcome Update: **Communicated decision remains unchanged (prior outcome stays active)**; displays human-readable unconfirmed warning (`AC-020`).
  - Required Audit Event: `DECISION_CORRECTION_UNCONFIRMED`.
- **`DELIVERY_UNKNOWN` -> `PROVIDER_ACCEPTED` (Correction Reconciliation)**:
  - Trigger: Status reconciliation or manual override confirms correction email receipt.
  - Actor: System / `ACT-001` (HR Recruiter).
  - Guard: Provider receipt confirmed.
  - Result State: `PROVIDER_ACCEPTED`.
  - Resulting Outcome Update: Communicated decision updated to corrected decision.
  - Required Audit Event: `DECISION_CORRECTION_RECONCILED_ACCEPTED`.
- **`DELIVERY_UNKNOWN` -> `SENDING_UNCONFIRMED` (Correction Retry)**:
  - Trigger: HR clicks Retry Send after verification confirms correction email was not received.
  - Actor: `ACT-001` (HR Recruiter).
  - Guard: Non-receipt confirmed; reuses SAME Logical Send Operation ID.
  - Result State: `SENDING_UNCONFIRMED`.
  - Resulting Outcome Update: Communicated decision remains unchanged until provider accepts.
  - Required Audit Event: `DECISION_CORRECTION_RETRIED`.

## 8. Functional Requirements


- `FR-001`: Candidate Excel Import & Field Validation
  - Description: The system shall import candidate application records from Excel files, requiring globally unique `Application ID`, `Stage`, `Candidate Name`, `Email`, and verified `Status`.
  - Rationale: Establishes verified application input data.
  - Source: CAP-001, BR-001
  - Priority: High
  - Preconditions: Uploaded file is readable `.xlsx`.
  - Expected Outcome: Validated application records stored in system.
  - Acceptance Criteria: `AC-001`, `AC-012`
  - Edge/Exception Cases: Missing/invalid header contract raises `CANDIDATE_HEADER_INVALID`. Missing required candidate fields raises `CANDIDATE_REQUIRED_VALUE_MISSING`. Duplicate `Application ID` raises `DUPLICATE_APPLICATION_ID`.
  - Dependencies: None
  - Downstream Owners: Backend, Frontend, QA
  - Status: confirmed

- `FR-002`: Contradiction Detection for Application ID + Stage
  - Description: The system shall evaluate prior sent communication history per `Application ID` and `Stage/Milestone`. If an opposing decision email was previously accepted by provider for the same `Application ID + Stage`, the system shall HARD_BLOCK normal draft sending.
  - Rationale: Core safety guard preventing contradictory communications.
  - Source: CAP-002, BR-001, BR-003, DEC-003
  - Priority: High
  - Preconditions: Communication history queried for Application ID and Stage.
  - Expected Outcome: Send button disabled for opposing outcomes on normal flow.
  - Acceptance Criteria: `AC-002`, `AC-013`, `AC-021`
  - Edge/Exception Cases: Cross-stage progression (e.g. `PASS_CV` at `CV_SCREENING` then `REJECT_INTERVIEW` at `INTERVIEW`) is permitted.
  - Dependencies: `FR-001`
  - Downstream Owners: Backend, Frontend, QA
  - Status: confirmed

- `FR-003`: Fixed Pre-seeded Template Rendering & Content Protection
  - Description: The system shall render drafts using fixed pre-seeded templates per Policy Table (`INTERVIEW_INVITATION`, `REJECTION_AFTER_CV`, `OFFER_EMAIL`, `REJECTION_AFTER_INTERVIEW`, `DECISION_CORRECTION`), locking Decision-Critical content as read-only and allowing edits only to Editable content.
  - Rationale: Prevents accidental modification of core hiring decisions while allowing tone adjustments.
  - Source: CAP-003, DEC-005
  - Priority: High
  - Preconditions: Candidate stage and status map to pre-seeded template.
  - Expected Outcome: Rendered draft with protected decision-critical fields.
  - Acceptance Criteria: `AC-003`
  - Edge/Exception Cases: Attempt to edit decision-critical text is rejected by UI/API.
  - Dependencies: `FR-001`
  - Downstream Owners: UI/UX, Backend, Frontend, QA
  - Status: confirmed

- `FR-004`: Draft Revisioning & Safety Guard Invalidation
  - Description: Any modification to Editable content shall create a new `Draft Revision`, invalidate prior `READY_TO_SEND` state, re-run deterministic checks, and lock Send until re-validation passes.
  - Rationale: Ensures edited text undergoes full safety re-checking before release.
  - Source: CAP-004, DEC-005
  - Priority: High
  - Preconditions: Active draft edited by HR.
  - Expected Outcome: New revision created; status reset to `DRAFT_PENDING_CHECK`.
  - Acceptance Criteria: `AC-004`
  - Edge/Exception Cases: Unedited drafts retain current revision status. Attempt to send superseded revision rejected (`AC-011`).
  - Dependencies: `FR-003`
  - Downstream Owners: Backend, Frontend, QA
  - Status: confirmed

- `FR-005`: Logical Send Operation Creation & Draft Freezing
  - Description: When HR clicks Send, the system shall create a single `Logical Send Operation` bound to the active `Draft Revision ID` and freeze all draft fields during transmission.
  - Rationale: Prevents concurrent edits or duplicate send requests during in-flight transmission.
  - Source: CAP-007, DEC-004
  - Priority: High
  - Preconditions: Draft status is `READY_TO_SEND`.
  - Expected Outcome: Draft frozen in `SENDING_UNCONFIRMED` state with active operation ID.
  - Acceptance Criteria: `AC-005`, `AC-007`
  - Edge/Exception Cases: Double-click or page reload reuses existing Logical Send Operation without creating a second operation.
  - Dependencies: `FR-004`
  - Downstream Owners: Backend, Architecture, QA
  - Status: confirmed

- `FR-006`: Real Email Provider Integration & Result Mapping
  - Description: The system shall transmit single-candidate send requests to the Email Provider API and map the response into `PROVIDER_ACCEPTED`, `DEFINITIVE_FAILURE`, or `DELIVERY_UNKNOWN`.
  - Rationale: Executes real email delivery and records definitive outcome status.
  - Source: CAP-006, GOAL-002, DEC-004
  - Priority: High
  - Preconditions: Logical Send Operation created.
  - Expected Outcome: Provider response recorded in draft state and audit log.
  - Acceptance Criteria: `AC-006`, `AC-014`, `AC-022`
  - Edge/Exception Cases: Timeout or connection drop sets state to `DELIVERY_UNKNOWN`.
  - Dependencies: `FR-005`
  - Downstream Owners: Architecture, Backend, QA
  - Status: confirmed

- `FR-007`: Delivery Unknown Handling & Provider Status Verification
  - Description: In `DELIVERY_UNKNOWN` state, the system shall block normal Send, disable creation of new send operations, require provider status verification before retry, and permit manual HR override only with explicit warning and Audit Log entry.
  - Rationale: Prevents accidental duplicate email delivery following network timeouts.
  - Source: CAP-007, DEC-004
  - Priority: High
  - Preconditions: Draft state is `DELIVERY_UNKNOWN`.
  - Expected Outcome: Retry reuses same Logical Send Operation after verification.
  - Acceptance Criteria: `AC-007`, `AC-015`, `AC-016`, `AC-022`
  - Edge/Exception Cases: Manual override logged with actor timestamp, rationale, and choice.
  - Dependencies: `FR-006`
  - Downstream Owners: Backend, Frontend, QA
  - Status: confirmed

- `FR-008`: Decision Correction Workflow Initiation
  - Description: The system shall provide a dedicated `Create decision correction` workflow when HR needs to change a communicated decision post-send, requiring mandatory rationale, side-by-side warning display, and explicit confirmation.
  - Rationale: Controlled process for legitimate post-send business decision changes.
  - Source: CAP-008, DEC-003
  - Priority: High
  - Preconditions: Prior email accepted by provider for same Application ID + Stage.
  - Expected Outcome: Correction draft generated with mandatory rationale prompt.
  - Acceptance Criteria: `AC-008`, `AC-017`, `AC-018`, `AC-019`, `AC-020`
  - Edge/Exception Cases: Attempt to create 2nd correction while 1 is active rejected (`AC-018`).
  - Dependencies: `FR-002`
  - Downstream Owners: UI/UX, Backend, Frontend, QA
  - Status: confirmed

- `FR-009`: Immutable Audit Trail Logging
  - Description: The system shall record immutable Audit Log entries for Application import, draft generation, revision updates, deterministic check results, send operations, provider responses, and correction rationales. An action requiring audit is considered complete only when its corresponding audit record is preserved.
  - Rationale: Provides full operational compliance and traceability.
  - Source: CAP-009, DEC-003, DEC-004
  - Priority: High
  - Preconditions: System action triggered.
  - Expected Outcome: Audit log record written with timestamp, actor, entity ID, and event details.
  - Acceptance Criteria: `AC-009`
  - Edge/Exception Cases: Audit log persistence failure prevents action completion.
  - Dependencies: None
  - Downstream Owners: Backend, Database, QA
  - Status: confirmed

- `FR-010`: Subject Line Validation Against Decision
  - Description: The system shall validate email subject lines against candidate status and decision, blocking send if the subject contains outcome terms conflicting with the current decision.
  - Rationale: Ensures email subject lines do not convey contradictory signals.
  - Source: CAP-003, DEC-005
  - Priority: High
  - Preconditions: Draft subject rendered or edited.
  - Expected Outcome: Mismatched subject flagged with `STATUS_EMAIL_MISMATCH`.
  - Acceptance Criteria: `AC-010`, `AC-021`
  - Edge/Exception Cases: Valid subjects matching decision pass check.
  - Dependencies: `FR-003`
  - Downstream Owners: Backend, QA
  - Status: confirmed

- `FR-011`: Pre-Send Draft Superseding
  - Description: When a new decision revision is created for an unsent draft, the system shall mark older draft revisions for that Application ID + Stage as `SUPERSEEDED`.
  - Rationale: Prevents sending outdated pre-send revisions.
  - Source: CAP-004, BR-005
  - Priority: High
  - Preconditions: New revision created before send.
  - Expected Outcome: Older unsent revisions set to `SUPERSEEDED`.
  - Acceptance Criteria: `AC-011`
  - Edge/Exception Cases: Sent revisions are never cancelled or modified.
  - Dependencies: `FR-004`
  - Downstream Owners: Backend, Database, QA
  - Status: confirmed

- `FR-012`: Globally Unique Application ID Enforcement
  - Description: The system shall enforce that every Application record possesses a globally unique `Application ID` across all candidates, positions, and hiring campaigns. Position is treated as a descriptive attribute, not part of the identity uniqueness key.
  - Rationale: Correctly bounds contradiction checks per job application without identity ambiguity.
  - Source: CAP-001, BR-001
  - Priority: High
  - Preconditions: Candidate application imported or created.
  - Expected Outcome: Globally unique Application IDs maintained across system.
  - Acceptance Criteria: `AC-012`
  - Edge/Exception Cases: Duplicate Application ID in import file rejected with `DUPLICATE_APPLICATION_ID`.
  - Dependencies: `FR-001`
  - Downstream Owners: Backend, Database, QA
  - Status: confirmed

## 9. Non-Functional Requirements

- `NFR-001`: Safety & Determinism Quality Gate
  - Description: Deterministic safety rules must execute and pass 100% before any external provider send operation is initiated.
  - Rationale: Ensures unsafe or unvalidated drafts never reach external delivery services.
  - Source: GOAL-001, CAP-004
  - Priority: High
  - Preconditions: Draft in `READY_TO_SEND` state.
  - Expected Outcome: Unvalidated drafts blocked from send transmission.
  - Acceptance Criteria: `AC-004`, `AC-010`, `AC-021`
  - Dependencies: `FR-004`, `FR-010`
  - Downstream Owners: Backend, Architecture, QA
  - Status: confirmed

- `NFR-002`: Audit Trail Immutability
  - Description: Audit Log records must be append-only and immutable. An action requiring audit is considered complete only when its corresponding audit record is preserved.
  - Rationale: Guarantees compliance traceability for recruitment communications.
  - Source: GOAL-003, DEC-003
  - Priority: High
  - Preconditions: Action execution logged.
  - Expected Outcome: Immutable audit record preserved.
  - Acceptance Criteria: `AC-009`
  - Dependencies: `FR-009`
  - Downstream Owners: Backend, Database, QA
  - Status: confirmed

- `NFR-003`: Logical Send Operation Uniqueness & Retry Controls
  - Description: Send operations must enforce single-operation execution per Draft Revision ID during network retries, browser reloads, or client double-clicks. A Logical Send Operation may contain multiple Provider Attempts during retries, but no second Logical Send Operation shall be created. Physical duplicate delivery on the email provider network is a residual risk passed to Architecture for evaluation.
  - Rationale: Prevents creating duplicate send operations in system state while acknowledging provider network boundary.
  - Source: GOAL-004, DEC-004
  - Priority: High
  - Preconditions: Logical Send Operation created.
  - Expected Outcome: Single Logical Send Operation maintained across retries and reloads.
  - Acceptance Criteria: `AC-005`, `AC-007`
  - Dependencies: `FR-005`, `FR-007`
  - Downstream Owners: Backend, Architecture, QA
  - Status: confirmed

- `NFR-004`: Human-Readable Exception Messaging
  - Description: Error states (`DEFINITIVE_FAILURE`, `DELIVERY_UNKNOWN`) must display clear, non-technical remediation guidance to HR recruiters.
  - Rationale: Enables HR recruiters to take correct manual or retry actions without technical confusion.
  - Source: CAP-005, DEC-004
  - Priority: High
  - Preconditions: Provider error or timeout occurs.
  - Expected Outcome: Human-readable error message displayed on UI.
  - Acceptance Criteria: `AC-006`, `AC-007`, `AC-014`, `AC-022`
  - Dependencies: `FR-006`, `FR-007`
  - Downstream Owners: UI/UX, Frontend, QA
  - Status: confirmed

## 10. Business Rules Summary (`BR-###`)
- `BR-001`: Application Identity — `Application ID` is globally unique across all candidates, positions, and campaigns in MVP.
- `BR-002`: Position Attribute — Position is a descriptive attribute of an Application, not part of the identity uniqueness key.
- `BR-003`: Contradiction Scope — Contradictions are evaluated strictly per `Application ID` + `Stage/Milestone`.
- `BR-004`: Valid Stage Progression — Outcomes across different stages (e.g. `PASS_CV` at `CV_SCREENING` then `REJECT_INTERVIEW` at `INTERVIEW`) are valid.
- `BR-005`: Post-Send Hard Block — After an outcome email is accepted by provider for an Application ID + Stage, normal Send for opposing outcomes is HARD_BLOCKED.
- `BR-006`: Revision Control — Revisions track pre-send edits. Creating a new revision does NOT bypass post-send contradiction blocks.
- `BR-007`: Unsent Revision Superseding — Before send, creating a new revision marks older unsent drafts for that stage as `SUPERSEEDED`.
- `BR-008`: Content Protection — Decision-critical draft fields are read-only and rendered from verified data.
- `BR-009`: Invalidation on Edit — Any edit to Editable content creates a new Draft Revision and resets status to `DRAFT_PENDING_CHECK`.
- `BR-010`: Subject Line Alignment — Email subject lines must not contradict the current hiring decision.
- `BR-011`: Correction Prerequisite — Decision Correction Workflow requires mandatory change rationale (`Rationale`) and explicit side-by-side confirmation.
- `BR-012`: History Immutability — Sent email history and audit logs cannot be edited or deleted.
- `BR-013`: Logical Send Operation Uniqueness — At most one Logical Send Operation may ever be created for each Draft Revision. A Logical Send Operation may contain multiple Provider Attempts. Physical duplicate delivery at the provider level is a residual risk passed to Architecture.
- `BR-014`: Provider Outcome Mapping — Provider response maps to `PROVIDER_ACCEPTED`, `DEFINITIVE_FAILURE`, or `DELIVERY_UNKNOWN`. A `DEFINITIVE_FAILURE` caused by content/address validation errors requires editing draft content and creating a new Draft Revision, retiring the old operation.
- `BR-015`: Retry Rules — Retry in `DELIVERY_UNKNOWN` must reuse the existing Logical Send Operation after status verification.
- `BR-016`: Manual Override Governance — HR manual override of `DELIVERY_UNKNOWN` requires explicit warning acknowledgment and Audit Log entry.
- `BR-017`: Provider Accepted Meaning — `PROVIDER_ACCEPTED` means provider accepted the send request; it does not guarantee inbox delivery. Communicated decision is updated ONLY after `PROVIDER_ACCEPTED`.

## 11. Use Cases Summary (`UC-###`)
- `UC-001`: Candidate Excel Import & Application Identity Validation
- `UC-002`: Template Rendering & Draft Content Separation
- `UC-003`: Editable Content Revision & Safety Guard Invalidation
- `UC-004`: Contradiction Detection & Send Hard Block
- `UC-005`: Logical Send Operation Execution & Outcome Handling
- `UC-006`: Status Reconciliation & Anti-Duplicate Retry
- `UC-007`: Decision Correction Workflow (`DEC-003`)

## 12. Acceptance Criteria Summary (`AC-###`)

- `AC-001` (Validation Failure Requires Edit): Given an Excel import file with missing `Candidate Name`, `Email`, `Stage`, or `Status`, When HR uploads the file, Then the system MUST reject the row, display `CANDIDATE_REQUIRED_VALUE_MISSING`, and require data correction before draft generation.
- `AC-002` (Contradiction Hard Block): Given a sent email for `Application ID: APP-101` at `Stage: INTERVIEW` with outcome `REJECT`, When HR attempts to generate/send an `OFFER` email for `APP-101` at `INTERVIEW`, Then the system MUST disable normal Send and display `Create decision correction`.
- `AC-003` (Protected Decision Content): Given a rendered draft, When HR attempts to edit the Decision-Critical outcome sentence, Then the system MUST prevent the edit and maintain read-only state.
- `AC-004` (Revision Invalidation on Edit): Given a draft in `READY_TO_SEND` status, When HR edits the greeting text, Then the system MUST assign a new Draft Revision ID (`REV-002`), reset status to `DRAFT_PENDING_CHECK`, and re-run safety guard checks before Send is re-enabled.
- `AC-005` (Logical Send Operation Binding & Freeze): Given a draft in `READY_TO_SEND` status, When HR clicks Send, Then the system MUST create a single Logical Send Operation bound to Draft Revision ID `REV-001` and freeze all draft fields.
- `AC-006` (Provider Accepted State): Given a send request accepted by the provider, When the response returns, Then the system MUST set status to `PROVIDER_ACCEPTED`, record Audit Log, and disable further send requests on this operation.
- `AC-007` (Delivery Unknown & Double-Click Anti-Duplicate): Given a send operation in `DELIVERY_UNKNOWN` state, When HR clicks Retry Send, double-clicks Send, or reloads the browser, Then the system MUST NOT create a second Logical Send Operation and MUST reuse the original operation ID.
- `AC-008` (Correction Workflow Confirmation & Submission): Given an opposing decision post-send, When HR completes the Decision Correction Workflow with rationale and side-by-side confirmation, Then the system MUST create and submit a Logical Send Operation for the decision correction draft, retain both emails in history, and ONLY update the current communicated outcome IF AND WHEN the provider returns `PROVIDER_ACCEPTED`.
- `AC-009` (Audit Log Completeness): Given any draft generation, edit, send, failure, or correction, When the action completes, Then an immutable Audit Log entry MUST be written with timestamp, actor, entity ID, and event details. An action is considered complete only when its audit record is preserved.
- `AC-010` (Subject Line Validation): Given a draft for decision `REJECT`, When the subject line contains `Offer` or `Congratulations`, Then the system MUST flag `STATUS_EMAIL_MISMATCH` and lock Send.
- `AC-011` (Attempt Send Superseded Revision): Given an unsent Draft Revision `REV-001` superseded by `REV-002`, When an attempt is made to send `REV-001`, Then the system MUST reject the send request.
- `AC-012` (Globally Unique Application ID): Given an existing `Application ID: APP-101`, When an import file contains a duplicate `APP-101` for any candidate or position, Then the system MUST reject the row and flag `DUPLICATE_APPLICATION_ID`.
- `AC-013` (Valid Cross-Stage Progression): Given a sent email for `APP-101` at `Stage: CV_SCREENING` with outcome `PASS_CV`, When HR creates an outcome email for `APP-101` at `Stage: INTERVIEW` with outcome `REJECT_INTERVIEW`, Then the system MUST allow draft generation and pass contradiction check.
- `AC-014` (Definitive Failure Allowing Retry or Edit): Given a provider response returning a definitive failure, When the response is processed, Then the system MUST set status to `DEFINITIVE_FAILURE`, display human-readable error, and enable Retry Send (for transient failure) or Draft Edit (for content/address validation failure).
- `AC-015` (Manual Resolution to Provider Accepted): Given a draft in `DELIVERY_UNKNOWN` state, When HR manually verifies receipt in email system and selects "Provider Accepted" with warning acknowledgment, Then the system MUST transition status to `PROVIDER_ACCEPTED` and record Audit Log.
- `AC-016` (Manual Resolution to Provider Not Received): Given a draft in `DELIVERY_UNKNOWN` state, When HR manually verifies non-receipt and selects "Provider Not Received" with warning acknowledgment, Then the system MUST unlock Retry Send using the SAME Logical Send Operation and record Audit Log.
- `AC-017` (Correction Outcome PROVIDER_ACCEPTED): Given a Decision Correction draft in `SENDING_UNCONFIRMED` state, When provider returns `PROVIDER_ACCEPTED`, Then the system MUST set status to `PROVIDER_ACCEPTED`, update current communicated decision to the corrected decision, mark prior decision `CORRECTED`, and write Audit Log.
- `AC-018` (Attempt 2nd Correction While 1 Active): Given an active or pending Decision Correction draft for `APP-101` at `Stage: INTERVIEW`, When HR attempts to trigger a second `Create decision correction`, Then the system MUST reject the action until the active correction reaches a final state.
- `AC-019` (Correction Outcome DEFINITIVE_FAILURE): Given a Decision Correction draft in `SENDING_UNCONFIRMED` state, When provider returns `DEFINITIVE_FAILURE`, Then the system MUST set status to `DEFINITIVE_FAILURE`, display human-readable error message, retain prior communicated decision unchanged, and enable retry or draft edit.
- `AC-020` (Correction Outcome DELIVERY_UNKNOWN): Given a Decision Correction draft in `SENDING_UNCONFIRMED` state, When provider transmission times out or connection drops, Then the system MUST set status to `DELIVERY_UNKNOWN`, display human-readable unconfirmed warning message, retain prior communicated decision unchanged, block normal send, and enable status reconciliation or retry on the same operation.
- `AC-021` (Deterministic Guard Blocker Prevents Provider Attempt): Given a draft with one or more deterministic blockers (`BLOCKED_DETERMINISTIC`, e.g. contradiction, status-email mismatch, missing candidate value, or subject mismatch), When HR clicks Send or invokes the send endpoint, Then the system MUST block operation creation and MUST NOT initiate any Provider Attempt.
- `AC-022` (Human-Readable Exception Guidance): Given a send operation resulting in `DEFINITIVE_FAILURE` or `DELIVERY_UNKNOWN`, When displayed in the HR UI, Then the system MUST present a clear, non-technical, human-readable error or warning message detailing the failure reason and exact recommended recruiter action.

## 13. Edge Cases & Exception Flows
- **Edge Case 1 (Missing Mandatory Fields)**: Handled by `FR-001` / `AC-001`. Import rejected.
- **Edge Case 2 (Duplicate Application ID)**: Handled by `FR-012` / `AC-012`. Import rejected with `DUPLICATE_APPLICATION_ID`.
- **Edge Case 3 (Candidate Applying to 2 Positions)**: Two distinct `Application ID`s created (`FR-012`). Contradiction checks execute independently per Application ID.
- **Edge Case 4 (Valid Stage Progression)**: `PASS_CV` at `CV_SCREENING` followed by `REJECT_INTERVIEW` at `INTERVIEW` passes validation (`FR-002` / `AC-013`).
- **Edge Case 5 (Opposing Outcomes Same Stage)**: Handled by `FR-002` / `AC-002`. Normal Send HARD_BLOCKED.
- **Edge Case 6 (Attempt Send Superseded Revision)**: Handled by `FR-011` / `AC-011`. System rejects send attempt on superseded revision.
- **Edge Case 7 (Double-Click / Page Reload During Send)**: System reuses existing `Logical Send Operation` without creating a second operation (`FR-005` / `AC-007`).
- **Edge Case 8 (Provider Response Lost / Timeout)**: System transitions to `DELIVERY_UNKNOWN` (`FR-006` / `AC-007`).
- **Edge Case 9 (Definitive Provider Failure)**: System transitions to `DEFINITIVE_FAILURE` (`FR-006` / `AC-014`). Enables Retry or Edit depending on error type.
- **Edge Case 10 (Unreconcilable UNKNOWN State)**: HR uses manual status override with mandatory warning and Audit Log entry (`FR-007` / `AC-015` / `AC-016`).
- **Edge Case 11 (False HR Override)**: Manual override logged in Audit Log for compliance review (`FR-007` / `AC-015` / `AC-016`).
- **Edge Case 12 (Edit Draft in READY_TO_SEND)**: Invalidate status to `DRAFT_PENDING_CHECK` and increment revision (`FR-004` / `AC-004`).
- **Edge Case 13 (Edit Decision-Critical Content)**: System prevents direct edit (`FR-003` / `AC-003`).
- **Edge Case 14 (Multiple Pending Corrections)**: System permits only one active correction draft per Application ID + Stage (`FR-008` / `AC-018`).
- **Edge Case 15 (Correction Delivery Outcomes)**: Correction follows `PROVIDER_ACCEPTED` (`AC-017`), `DEFINITIVE_FAILURE` (`AC-019`), or `DELIVERY_UNKNOWN` (`AC-020`) rules; communicated decision updated ONLY on `PROVIDER_ACCEPTED`.

## 14. Business Assumptions
- `ASM-001`: HR recruiters have access to external email provider logs or recipient inbox status to perform manual status verification during `DELIVERY_UNKNOWN` state recovery.
  - Owner: HR Recruiter / HR Operations
  - Impact: High (Required for manual status override in `UC-006` / `AC-015` / `AC-016`)
  - Validation Method: HR operational procedure review
  - Status: `accepted`

*(Note: Excel header schema validation is specified as a functional rule in FR-001 / AC-001; Provider response mechanism is specified as an Architecture Decision Input ADI-001).*

## 15. Constraints & Dependencies
- `CON-001`: External Real Email Provider API availability.
- `DEP-001`: Approved product baseline `docs/product/product.md`.

## 16. Open Questions
- None blocking BA specification. All material decision gates closed in product spec.

## 17. Risks & Impacts
- `RSK-001`: Temporary network loss causing `DELIVERY_UNKNOWN` state. Impact: Requires HR status verification or retry. Mitigation: Governed by `FR-007` / `AC-007`.
- `RSK-002`: Provider physical duplicate delivery residual risk. Impact: Provider may deliver email twice despite single request/idempotency key. Mitigation: Architecture evaluation of provider API deduplication capabilities.

## 18. Downstream Handoff

| BA Requirement ID | Downstream Owners | Target Artifact / Responsibility |
| :--- | :--- | :--- |
| `FR-001` | Backend, Frontend, QA | Excel Import parser & validation UI |
| `FR-002` | Backend, Frontend, QA | Contradiction Guard service & Send Hard Block UI |
| `FR-003` | UI/UX, Backend, Frontend, QA | Fixed Template Renderer & Read-Only Content Lock UI |
| `FR-004` | Backend, Frontend, QA | Revision Manager & Invalidation Logic |
| `FR-005` | Backend, Architecture, QA | Logical Send Operation service & In-Flight Freeze |
| `FR-006` | Architecture, Backend, QA | Email Provider Adapter & Response Mapping |
| `FR-007` | Backend, Frontend, QA | Delivery Unknown Handler & Manual Override Dialog |
| `FR-008` | UI/UX, Backend, Frontend, QA | Decision Correction Workflow UI & Side-by-Side Modal |
| `FR-009` | Backend, Database, QA | Immutable Audit Log Service & DB Schema |
| `FR-010` | Backend, QA | Subject Line Validation Rule |
| `FR-011` | Backend, Database, QA | Pre-Send Draft Superseding Logic |
| `FR-012` | Backend, Database, QA | Application ID Uniqueness Constraint |
| `NFR-001` | Backend, Architecture, QA | Deterministic Quality Gate Enforcement |
| `NFR-002` | Backend, Database, QA | Append-Only Audit Trail Integrity |
| `NFR-003` | Backend, Architecture, QA | Anti-Duplicate Send Operation Enforcement |
| `NFR-004` | UI/UX, Frontend, QA | Human-Readable Exception Messaging UI |
| `ADI-001` | Architecture | Email Provider Response Strategy (Sync HTTP vs Async Webhook/Polling normalization) |

## 19. Approval Record
- Stakeholder Approval: [APPROVED]
- Approved by: User / Product Owner
- Approval date: 2026-08-12
- Approved Product version: 1.0.1
- Approved Product fingerprint: 17b10266e440729d4c55a9e0b1a41ee5c6494700afab3878743df9cdbcff4a6b
- Confirmed by User on 2026-08-12

