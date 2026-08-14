# Product Plan & Checkpoint

- **Mode**: discovery
- **Execution Profile**: standard
- **Started At**: 2026-08-12T10:26:00+07:00
- **Deadline At**: 2026-08-12T11:15:00+07:00
- **Status**: APPROVED_BASELINE_FOR_BA

## 1. Scope & Boundaries

- **In Scope**: Minimal Real-Email MVP. Single candidate email sending via provider, mandatory Application ID, Stage/Milestone contradiction tracking, Decision Revision tracking, pre-send draft superseding, Minimal Decision Correction Workflow (DEC-003), Logical Send Operation with 3 outcomes (`PROVIDER_ACCEPTED`, `DEFINITIVE_FAILURE`, `DELIVERY_UNKNOWN`) (DEC-004), and Fixed Pre-seeded Templates with Decision-Critical vs Editable content separation (DEC-005).
- **Out of Scope**: Batch sending, auto sending, bounce tracking, marketing campaigns, LLM blocking core flow, async queues as product capabilities, multi-level manager approval for corrections, automatic retries in UNKNOWN state, Template CRUD UI, custom placeholders, AI free-text semantic review.
- **Stop Condition**: Approved Baseline Handoff to Business Analysis (`team1-ba`).

## 2. Input Inventory & Fingerprints

| Input Source | Type | Approval State | Status |
| :--- | :--- | :--- | :--- |
| `docs/product-requirements.md` | Stakeholder Input | APPROVED_BASELINE_FOR_BA | Primary Proposal Input |
| `README.md` | Existing Spec | Legacy Reference | Legacy Implementation Reference |

## 3. Work Items & Progress

- [x] Step 1: Inspect inputs and select discovery mode
- [x] Step 2: Establish problem statement, primary user, core job, and outcome
- [x] Step 3.1: Material Decision 1 - Product Scope Strategy (Option B Minimal Real-Email MVP selected - DEC-001)
- [x] Step 3.2: Material Decision 2 - Contradiction Scope (Option A Application ID + Stage/Milestone selected - DEC-002)
- [x] Step 3.3: Material Decision 3 - Post-Send Correction Workflow Scope (Option B Minimal Correction Workflow selected - DEC-003)
- [x] Step 3.4: Material Decision 4 - Provider Timeout/Failure, Logical Send Operation, and Anti-Duplicate (Option A refined - DEC-004)
- [x] Step 3.5: Material Decision 5 - Template Management Scope (Fixed Pre-seeded Templates - DEC-005)
- [x] Step 4: Finalize updated MVP / LATER / REJECT baseline (READY_FOR_BASELINE_REVIEW)
- [x] Step 5: State validation & User Approval Gate (APPROVED_BASELINE_FOR_BA on 2026-08-12)

## 4. Key Decisions

- **DEC-001**: Minimal Real-Email MVP scope. Single candidate email sending via provider, no batch, no auto-sending. Deterministic Safety Guard runs before send. LLM semantic review moved to LATER.
- **DEC-002**: Contradiction boundary is `Application ID` + `Stage/Milestone`. Decision Revision tracks edits per stage. Before send: latest revision active, older drafts superseded. After send: opposing results for same Application + Stage blocked even if revision increases. `PASS_CV` -> `REJECT_INTERVIEW` is valid. `Application ID` is mandatory for MVP.
- **DEC-003**: Minimal Decision Correction Workflow for MVP. Normal Send remains HARD_BLOCKED after prior send. HR explicitly triggers `Create decision correction` with mandatory rationale, explicit correction email body, side-by-side prior vs new comparison with high-visibility warning, and explicit final confirmation. History preserved. Retry allowed on unaccepted correction without creating duplicate drafts. Provider acceptance updates current communicated outcome. Manager approvals moved to LATER. Pure deterministic control, no LLM intervention.
- **DEC-004**: Logical Send Operation frozen upon Send. 3 explicit outcomes: `PROVIDER_ACCEPTED` (no inbox guarantee, no resend), `DEFINITIVE_FAILURE` (human-readable error, retry/edit enabled), `DELIVERY_UNKNOWN` (timeout/network loss, no auto-retry, normal send blocked, unconfirmed warning displayed). Retry reuses same Logical Send Operation. Verification required before retry. HR manual status override permitted with Audit Log warning. Architecture handoff for idempotency headers/reconciliation. Acceptance criterion: retry/double-click/reload must not proactively create a 2nd Logical Send Operation for the same Draft Revision.
- **DEC-005**: Fixed Pre-seeded Templates for Core Journey (`INTERVIEW_INVITATION`, `REJECTION_AFTER_CV`, `OFFER_EMAIL`, `REJECTION_AFTER_INTERVIEW`, `DECISION_CORRECTION`). No Template CRUD UI/API in MVP. Content divided into Decision-Critical (read-only, rendered from verified data) vs Editable (greetings, closing, notes). Edits create new Draft Revision, invalidate Ready-to-Send state, re-run deterministic checks. Subject validated against decision. Pure deterministic enforcement, LLM semantic review in LATER.

## 5. Checkpoint & Exact Next Action

- **Current Checkpoint**: Minimal Product Baseline officially approved by User on 2026-08-12. Status updated to `APPROVED_BASELINE_FOR_BA`. Validation script passed.
- **Exact Next Action**: Stop execution and report canonical spec path to User. Await further instructions.
