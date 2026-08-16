# Data Dictionary: Recruitment Mail Guard (Minimal Real-Email MVP)

## 1. Overview
This document provides the definitive field-level dictionary for all 5 physical tables and columns in the PostgreSQL 16 database.

---

## 2. Table & Column Definitions

### Table: `candidates`
- **Table ID**: `TBL-001`
- **Purpose**: Master table for candidate job application records imported from Excel. Each row represents a candidate application uniquely identified by `application_id`.
- **Owner Container**: Backend Monolith (`FastAPI`)
- **Source Requirements**: `CAP-001`, `FR-001`, `FR-012`, `BR-001`, `BR-002`
- **Lifecycle / Deletion**: `RET-001` (Permanent retention during active campaign, no hard delete)

| Column ID | Field Name | Physical Data Type | Nullable | Default | Classification | Constraints | Description & Business Meaning | Example Value | Source ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `COL-001` | `id` | `INTEGER` | NO | `IDENTITY` | Internal | `PK` | Surrogate primary key | `101` | `ENT-001` |
| `COL-002` | `application_id` | `VARCHAR(64)` | NO | None | Internal | `UQ, CK` | Mandatory globally unique candidate application ID from verified source. No fake backfills. | `'APP-2026-001'` | `VAL-001`, `FR-012` |
| `COL-003` | `full_name` | `VARCHAR(255)` | NO | None | PII | `CK` | Full legal name of candidate | `'Nguyen Van A'` | `ENT-001`, `FR-001` |
| `COL-004` | `email` | `VARCHAR(255)` | NO | None | PII | `CK` | Candidate recipient email address | `'candidate@example.com'` | `VAL-002`, `FR-001` |
| `COL-005` | `phone` | `VARCHAR(50)` | YES | None | PII | None | Optional contact phone number | `'+84901234567'` | `ENT-001` |
| `COL-006` | `position` | `VARCHAR(255)` | YES | None | Internal | None | Job title applied for (descriptive attribute) | `'Senior Backend Engineer'` | `ENT-001` |
| `COL-007` | `stage` | `VARCHAR(80)` | NO | `'CV_SCREENING'` | Internal | `CK` | Current hiring stage (`CV_SCREENING`, `INTERVIEW`) | `'INTERVIEW'` | `VAL-003`, `FR-001` |
| `COL-008` | `status` | `VARCHAR(80)` | NO | `'PENDING'` | Internal | `CK` | Current decision status (`PENDING`, `PASS_CV`, `REJECT_CV`, `PASS_INTERVIEW`, `REJECT_INTERVIEW`) | `'PASS_INTERVIEW'` | `VAL-004`, `FR-001` |
| `COL-009` | `communicated_decision` | `VARCHAR(80)` | YES | None | Internal | `CK` | Decision communicated via email (Updated ONLY on `PROVIDER_ACCEPTED`) | `'PASS_INTERVIEW'` | `VAL-004`, `BR-002` |
| `COL-010` | `communicated_stage` | `VARCHAR(80)` | YES | None | Internal | `CK` | Stage corresponding to communicated decision | `'INTERVIEW'` | `VAL-003`, `BR-002` |
| `COL-011` | `communicated_at` | `TIMESTAMPTZ` | YES | None | Internal | None | Timestamp when provider confirmed acceptance | `'2026-08-15T09:30:00Z'` | `BR-002` |
| `COL-012` | `status_updated_at` | `TIMESTAMPTZ` | YES | None | Internal | None | Timestamp of last status modification | `'2026-08-15T09:00:00Z'` | `ENT-001` |
| `COL-013` | `status_updated_by` | `VARCHAR(255)` | YES | None | Internal | None | Recruiter username who modified status | `'demo_hr'` | `ENT-001` |
| `COL-014` | `interview_time` | `TIMESTAMPTZ` | YES | None | Internal | None | Scheduled interview datetime | `'2026-08-20T14:00:00Z'` | `ENT-001` |
| `COL-015` | `interviewer` | `VARCHAR(255)` | YES | None | Internal | None | Assigned interviewer name | `'Tran Van B'` | `ENT-001` |
| `COL-016` | `note` | `TEXT` | YES | None | Internal | None | Internal recruitment notes | `'Strong technical background'` | `ENT-001` |
| `COL-017` | `created_at` | `TIMESTAMPTZ` | NO | `now()` | Internal | None | Record import timestamp in UTC | `'2026-08-15T08:00:00Z'` | `ENT-001` |
| `COL-018` | `updated_at` | `TIMESTAMPTZ` | NO | `now()` | Internal | None | Record update timestamp in UTC | `'2026-08-15T09:30:00Z'` | `ENT-001` |

---

### Table: `draft_revisions`
- **Table ID**: `TBL-002`
- **Purpose**: Email draft revisions, change tracking, superseding, discard tracking, and Decision Correction support.
- **Owner Container**: Backend Monolith (`FastAPI`)
- **Source Requirements**: `CAP-003`, `CAP-004`, `FR-003`, `FR-004`, `FR-011`, `BR-004`, `BR-007`
- **Lifecycle / Deletion**: `RET-002` (Older drafts marked `SUPERSEDED`, discarded marked `DISCARDED`, retained for audit)

| Column ID | Field Name | Physical Data Type | Nullable | Default | Classification | Constraints | Description & Business Meaning | Example Value | Source ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `COL-019` | `id` | `UUID` | NO | `gen_random_uuid()` | Internal | `PK` | Unique revision UUID | `'550e8400-e29b-41d4-a716-446655440000'` | `ENT-002` |
| `COL-020` | `candidate_id` | `INTEGER` | NO | None | Internal | `FK` | Foreign key to `candidates.id` (`ON DELETE RESTRICT ON UPDATE RESTRICT`) | `101` | `ENT-001`, `FR-004` |
| `COL-021` | `revision_number` | `INTEGER` | NO | `1` | Internal | `CK` | Incremental revision number per candidate | `1` | `FR-004`, `BR-004` |
| `COL-022` | `template_code` | `VARCHAR(80)` | NO | None | Internal | `CK` | Pre-seeded template code from application config | `'OFFER_EMAIL'` | `ENT-002`, `DEC-005` |
| `COL-023` | `stage` | `VARCHAR(80)` | NO | None | Internal | `CK` | Candidate stage at time of draft (`CV_SCREENING`, `INTERVIEW`) | `'INTERVIEW'` | `VAL-003`, `FR-002` |
| `COL-024` | `decision` | `VARCHAR(80)` | NO | None | Internal | `CK` | Hiring decision reflected in draft | `'PASS_INTERVIEW'` | `VAL-004`, `FR-002` |
| `COL-025` | `to_email` | `VARCHAR(255)` | NO | None | PII | `CK` | Locked recipient email address | `'candidate@example.com'` | `VAL-002`, `FR-001` |
| `COL-026` | `subject` | `VARCHAR(500)` | NO | None | Internal | None | Rendered subject line | `'Job Offer: Senior Backend Engineer'` | `FR-010` |
| `COL-027` | `decision_critical_content` | `TEXT` | NO | None | Internal | None | Read-only locked outcome body fragment | `'We are pleased to offer you...'` | `CAP-003`, `DEC-005` |
| `COL-028` | `editable_content` | `TEXT` | NO | None | Internal | None | Recruiter edited text fragment | `'Dear Nguyen Van A, ...'` | `CAP-003`, `DEC-005` |
| `COL-029` | `rendered_body` | `TEXT` | NO | None | Internal | None | Complete assembled email body | `'Dear Nguyen Van A, ...'` | `CAP-003`, `FR-003` |
| `COL-030` | `status` | `VARCHAR(50)` | NO | `'DRAFT_PENDING_CHECK'` | Internal | `CK` | Status (`DRAFT_PENDING_CHECK`, `READY_TO_SEND`, `BLOCKED_DETERMINISTIC`, `FROZEN_IN_FLIGHT`, `SUPERSEDED`, `CORRECTION_DRAFT`, `DISCARDED`, `FINALIZED`) | `'READY_TO_SEND'` | `ENT-002`, `FR-004` |
| `COL-031` | `is_correction` | `BOOLEAN` | NO | `false` | Internal | None | Decision correction indicator flag | `false` | `CAP-008`, `DEC-003` |
| `COL-032` | `correction_rationale` | `TEXT` | YES | None | Internal | `CK` | Mandatory rationale if `is_correction=true` (min 5 chars) | `'Interview feedback revised'` | `CAP-008`, `BR-005` |
| `COL-033` | `prior_operation_id` | `UUID` | YES | None | Internal | `FK` | References `logical_send_operations.id` (`ON DELETE RESTRICT ON UPDATE RESTRICT`) | `'660e8400-e29b-41d4-a716-446655440000'` | `CAP-008` |
| `COL-034` | `risk_check_result` | `JSONB` | NO | `'{}'::jsonb` | Internal | None | JSON evaluation of deterministic checks | `'{"name_aligned": true}'` | `CAP-004`, `FR-004` |
| `COL-035` | `created_by` | `VARCHAR(255)` | NO | `'demo_hr'` | Internal | None | Recruiter who authored revision | `'demo_hr'` | `ENT-002` |
| `COL-036` | `superseded_at` | `TIMESTAMPTZ` | YES | None | Internal | None | Timestamp when superseded | `'2026-08-15T09:10:00Z'` | `FR-011` |
| `COL-037` | `discarded_at` | `TIMESTAMPTZ` | YES | None | Internal | None | Timestamp when discarded | `'2026-08-15T09:12:00Z'` | `BR-007` |
| `COL-038` | `created_at` | `TIMESTAMPTZ` | NO | `now()` | Internal | None | Revision creation timestamp in UTC | `'2026-08-15T09:00:00Z'` | `ENT-002` |
| `COL-039` | `updated_at` | `TIMESTAMPTZ` | NO | `now()` | Internal | None | Revision update timestamp in UTC | `'2026-08-15T09:05:00Z'` | `ENT-002` |

---

### Table: `logical_send_operations`
- **Table ID**: `TBL-003`
- **Purpose**: Single logical send operation unit bound 1:1 to Draft Revision with anti-duplicate guarantee. No redundant candidate identifier stored.
- **Owner Container**: Backend Monolith (`FastAPI`)
- **Source Requirements**: `CAP-007`, `DEC-004`, `FR-005`, `FR-007`, `NFR-003`, `BR-013`
- **Lifecycle / Deletion**: Permanent transaction history

| Column ID | Field Name | Physical Data Type | Nullable | Default | Classification | Constraints | Description & Business Meaning | Example Value | Source ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `COL-040` | `id` | `UUID` | NO | `gen_random_uuid()` | Internal | `PK` | Unique operation UUID (used directly as `Idempotency-Key` for Resend) | `'770e8400-e29b-41d4-a716-446655440000'` | `ENT-003`, `DEC-004` |
| `COL-041` | `draft_revision_id` | `UUID` | NO | None | Internal | `UQ, FK` | Foreign key to `draft_revisions.id` (`ON DELETE RESTRICT ON UPDATE RESTRICT`, Strict 1:1 Invariant) | `'550e8400-e29b-41d4-a716-446655440000'` | `CAP-007`, `NFR-003` |
| `COL-042` | `operation_status` | `VARCHAR(50)` | NO | `'SENDING_UNCONFIRMED'` | Internal | `CK` | Current status of send operation (`SENDING_UNCONFIRMED`, `PROVIDER_ACCEPTED`, `DEFINITIVE_FAILURE`, `DELIVERY_UNKNOWN`, `FAILED_TERMINAL`) | `'PROVIDER_ACCEPTED'` | `ENT-003`, `DEC-004` |
| `COL-043` | `provider_name` | `VARCHAR(50)` | NO | `'RESEND'` | Internal | None | External provider adapter | `'RESEND'` | `CAP-006`, `ADR-002` |
| `COL-044` | `provider_message_id` | `VARCHAR(255)` | YES | None | Internal | None | Resend message UUID from 200 response | `'49bf7438-e70d-4208-88d4-6d97c555f8b1'` | `FR-006`, `SPIKE-001` |
| `COL-045` | `final_outcome` | `VARCHAR(50)` | YES | None | Internal | `CK` | Normalized outcome | `'PROVIDER_ACCEPTED'` | `DEC-004`, `FR-006` |
| `COL-046` | `failure_category` | `VARCHAR(50)` | YES | None | Internal | `CK` | Failure classification (`TRANSIENT_RETRYABLE`, `VALIDATION_TERMINAL`, `QUOTA_EXCEEDED`) | `'TRANSIENT_RETRYABLE'` | `DEC-004`, `FR-007` |
| `COL-047` | `resolution_mode` | `VARCHAR(50)` | YES | None | Internal | `CK` | Resolution method (`AUTOMATIC_SYNC`, `PROVIDER_IDEMPOTENT_REPLAY`, `HR_MANUAL_OVERRIDE`) | `'AUTOMATIC_SYNC'` | `ADR-004`, `FR-007` |
| `COL-048` | `resolution_rationale` | `TEXT` | YES | None | Internal | None | Recruiter resolution rationale | `'Verified in email logs'` | `ADR-004`, `AC-015` |
| `COL-049` | `resolved_by` | `VARCHAR(255)` | YES | None | Internal | None | Username who resolved status | `'demo_hr'` | `ADR-004` |
| `COL-050` | `resolved_at` | `TIMESTAMPTZ` | YES | None | Internal | None | Resolution timestamp | `'2026-08-15T09:35:00Z'` | `ADR-004` |
| `COL-051` | `created_by` | `VARCHAR(255)` | NO | `'demo_hr'` | Internal | None | User who clicked Send | `'demo_hr'` | `ENT-003` |
| `COL-052` | `created_at` | `TIMESTAMPTZ` | NO | `now()` | Internal | None | Phase A creation timestamp in UTC | `'2026-08-15T09:30:00Z'` | `ENT-003` |
| `COL-053` | `updated_at` | `TIMESTAMPTZ` | NO | `now()` | Internal | None | Phase C finalization timestamp in UTC | `'2026-08-15T09:30:02Z'` | `ENT-003` |

---

### Table: `provider_attempts`
- **Table ID**: `TBL-004`
- **Purpose**: Physical outbound HTTP transmission attempts to Resend API. Stores only sanitized telemetry (payload digest, status, provider error code/message, latency). No redundant URLs, raw headers, or raw payloads.
- **Owner Container**: Backend Monolith (`FastAPI`)
- **Source Requirements**: `CAP-006`, `CAP-007`, `FR-006`, `FR-007`, `BR-013`, `BR-015`
- **Lifecycle / Deletion**: Permanent attempt history for observability

| Column ID | Field Name | Physical Data Type | Nullable | Default | Classification | Constraints | Description & Business Meaning | Example Value | Source ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `COL-054` | `id` | `UUID` | NO | `gen_random_uuid()` | Internal | `PK` | Unique attempt UUID | `'880e8400-e29b-41d4-a716-446655440000'` | `ENT-004` |
| `COL-055` | `operation_id` | `UUID` | NO | None | Internal | `FK` | Foreign key to `logical_send_operations.id` (`ON DELETE RESTRICT ON UPDATE RESTRICT`) | `'770e8400-e29b-41d4-a716-446655440000'` | `ENT-003`, `ADR-003` |
| `COL-056` | `attempt_number` | `INTEGER` | NO | `1` | Internal | `CK` | Physical attempt sequence number | `1` | `ADR-003`, `FR-007` |
| `COL-057` | `request_payload_digest` | `VARCHAR(64)` | NO | None | Internal | None | SHA-256 hash of JSON request body | `'e3b0c44298fc1c149afbf4c8996fb924...'` | `NFR-002` |
| `COL-058` | `attempt_status` | `VARCHAR(50)` | NO | `'PREPARED'` | Internal | `CK` | Attempt state (`PREPARED`, `IN_FLIGHT`, `ACCEPTED`, `DEFINITIVE_FAILURE`, `UNCONFIRMED_TIMEOUT`, `ABORTED`) | `'ACCEPTED'` | `ENT-004`, `ADR-005` |
| `COL-059` | `http_status_code` | `INTEGER` | YES | None | Internal | None | HTTP status code received | `200` | `FR-006`, `ADR-002` |
| `COL-060` | `provider_message_id` | `VARCHAR(255)` | YES | None | Internal | None | Message UUID extracted from provider response | `'49bf7438-e70d-4208-88d4-6d97c555f8b1'` | `FR-006` |
| `COL-061` | `error_code` | `VARCHAR(100)` | YES | None | Internal | None | Normalized provider error code | `'rate_limit_exceeded'` | `NFR-004` |
| `COL-062` | `error_message` | `TEXT` | YES | None | Internal | None | Sanitized human-readable error description | `'Connection timeout after 10.0s'` | `NFR-004` |
| `COL-063` | `latency_ms` | `INTEGER` | YES | None | Internal | None | Outbound network duration in milliseconds | `245` | `DRV-Q-004` |
| `COL-064` | `initiated_at` | `TIMESTAMPTZ` | NO | `now()` | Internal | None | Phase A attempt start timestamp in UTC | `'2026-08-15T09:30:00Z'` | `ADR-005` |
| `COL-065` | `completed_at` | `TIMESTAMPTZ` | YES | None | Internal | None | Phase C attempt finish timestamp in UTC | `'2026-08-15T09:30:01Z'` | `ADR-005` |

---

### Table: `audit_logs`
- **Table ID**: `TBL-005`
- **Purpose**: Append-only immutable audit trail for candidate import, safety checks, sends, discards, and decision corrections.
- **Owner Container**: Backend Monolith (`FastAPI`)
- **Source Requirements**: `CAP-009`, `GOAL-003`, `FR-009`, `NFR-002`, `BR-012`, `ADR-005`
- **Lifecycle / Deletion**: Permanent compliance ledger (`UPDATE`/`DELETE` prohibited)

| Column ID | Field Name | Physical Data Type | Nullable | Default | Classification | Constraints | Description & Business Meaning | Example Value | Source ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `COL-066` | `id` | `BIGINT` | NO | `IDENTITY` | Internal | `PK` | Monotonically increasing audit log sequence | `1001` | `ENT-005` |
| `COL-067` | `event_name` | `VARCHAR(100)` | NO | None | Internal | `CK` | Event classification (`CANDIDATE_IMPORTED`, `DRAFT_GENERATED`, `SEND_OUTCOME_FINALIZED`, etc.) | `'SEND_OUTCOME_FINALIZED'` | `CAP-009`, `FR-009` |
| `COL-068` | `entity_type` | `VARCHAR(80)` | NO | None | Internal | None | Target entity name (`CANDIDATE`, `DRAFT_REVISION`, `LOGICAL_SEND_OPERATION`) | `'LOGICAL_SEND_OPERATION'` | `CAP-009` |
| `COL-069` | `entity_id` | `VARCHAR(128)` | NO | None | Internal | None | Stringified entity identifier | `'770e8400-e29b-41d4-a716-446655440000'` | `CAP-009` |
| `COL-070` | `application_id` | `VARCHAR(64)` | YES | None | Internal | None | Denormalized application ID for fast filtering | `'APP-2026-001'` | `VAL-001`, `FR-009` |
| `COL-071` | `actor` | `VARCHAR(255)` | NO | `'demo_hr'` | Internal | None | User or system actor who triggered event | `'demo_hr'` | `CAP-009` |
| `COL-072` | `action_outcome` | `VARCHAR(50)` | NO | None | Internal | None | Event outcome (`SUCCESS`, `BLOCKED`, `FAILURE`, `UNCONFIRMED`) | `'SUCCESS'` | `CAP-009` |
| `COL-073` | `payload_json` | `JSONB` | NO | `'{}'::jsonb` | Internal | None | Sanitized event metadata and state transition diff | `'{"provider_status": 200}'` | `NFR-002` |
| `COL-074` | `created_at` | `TIMESTAMPTZ` | NO | `now()` | Internal | None | Event timestamp in UTC | `'2026-08-15T09:30:02Z'` | `NFR-002`, `ADR-005` |
