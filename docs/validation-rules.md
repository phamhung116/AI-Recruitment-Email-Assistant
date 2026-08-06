# Validation Rules

Severity levels:

- `info`: informational, does not block.
- `warning`: HR review required, does not always block.
- `error`: blocks draft generation or queue action until fixed.
- `blocker`: blocks because action is unsafe or policy-disallowed.

## Rule Catalog

| Rule ID | Description | Required Evidence | Severity | Blocking | Classification | Suggested Remediation |
| --- | --- | --- | --- | --- | --- | --- |
| `CANDIDATE_REQUIRED_NAME` | Candidate must have a name. | `candidate.full_name` | error | Yes | Deterministic | Add verified candidate name. |
| `CANDIDATE_REQUIRED_EMAIL` | Draft recipient must exist. | `candidate.email` | error | Yes | Deterministic | Add verified email address. |
| `CANDIDATE_EMAIL_FORMAT` | Recipient email must be syntactically valid. | `candidate.email` | error | Yes | Deterministic | Correct email after HR verification. |
| `DUPLICATE_IMPORT_EMAIL` | Import row duplicates an existing or prior row email. | import row email, existing emails | warning/error | Usually yes for import row | Deterministic | Skip duplicate or merge manually. |
| `DUPLICATE_RECIPIENT_IN_CAMPAIGN` | Same recipient appears more than once in one campaign. | campaign recipients | error | Yes | Deterministic | Deduplicate campaign. |
| `STATUS_UNSUPPORTED` | Status is unknown or unsupported. | `candidate.status` | blocker | Yes | Deterministic or AI-assisted for label interpretation | Configure explicit mapping or update status. |
| `STATUS_PENDING` | Pending status cannot generate a draft. | `candidate.status` | blocker | Yes | Deterministic | HR updates status after decision. |
| `STATUS_EMAIL_MISMATCH` | Requested email type does not match mapped status. | status, requested type, expected type | blocker | Yes | Deterministic | Use mapped email type or change rule after approval. |
| `TEMPLATE_MISSING` | No template exists for selected email type. | `email_type`, template query | error | Yes | Deterministic | Create approved template. |
| `TEMPLATE_REQUIRED_VALUE_MISSING` | Required placeholder has no candidate value. | template required placeholders, candidate fields | error | Yes | Deterministic | Add verified candidate data or adjust template. |
| `TEMPLATE_UNSUPPORTED_PLACEHOLDER` | Template contains placeholder not supported by renderer. | subject/body placeholders | error | Yes | Deterministic | Replace or implement placeholder. |
| `TEMPLATE_UNRESOLVED_PLACEHOLDER` | Rendered draft still contains placeholder syntax. | rendered subject/body | error | Yes | Deterministic | Fix data or template. |
| `SENSITIVE_TEMPLATE_FLAG` | Sensitive email type must use sensitive template flag. | email type, template `is_sensitive` | error | Yes | Deterministic | Mark template sensitive. |
| `REQUIRES_HR_APPROVAL` | Sensitive or uncertain drafts need HR approval. | email type, issues | warning | Blocks send/simulation until approved | Deterministic | HR reviews and approves. |
| `DUPLICATE_SENT_HISTORY` | Candidate already has sent/simulated history for same email type. | `EmailHistory` | error | Yes | Deterministic | Confirm duplicate intent and create explicit override flow. |
| `DUPLICATE_PROCESSING_RUN` | Same idempotency key or input hash already processed. | processing run key/hash | error | Yes | Deterministic | Reuse prior result or start new campaign. |
| `AI_SEMANTIC_MISMATCH` | Draft language does not match intended email type. | draft text, email type | warning/error | Depends on severity | AI-assisted | HR edits draft or selects correct template. |
| `AI_CONTRADICTORY_LANGUAGE` | Draft contains conflicting dates, names, outcomes, or instructions. | draft text, candidate fields | warning/error | Usually yes | AI-assisted | HR resolves conflict. |
| `AI_UNSUPPORTED_INFERENCE` | Draft appears to infer missing policy/data. | draft text, missing fields | warning/error | Yes when material | AI-assisted | Remove inferred content. |

## Current Implementation Mapping

Implemented today:

- `STATUS_PENDING`
- `STATUS_EMAIL_MISMATCH`
- `TEMPLATE_MISSING`
- `TEMPLATE_REQUIRED_VALUE_MISSING`
- `TEMPLATE_UNSUPPORTED_PLACEHOLDER`
- `SENSITIVE_TEMPLATE_FLAG`
- `DUPLICATE_SENT_HISTORY`
- Partial duplicate email detection during import.

Not implemented:

- Email format validation in backend.
- Normalized `ValidationIssue` records.
- Severity taxonomy beyond a boolean `passed` and `errors`.
- Campaign duplicate processing.
- AI-assisted semantic review.
- Idempotency checks.

## Examples

### Missing Interview Time

Candidate status: `PASS_CV`

Mapped email type: `INTERVIEW_INVITATION`

Template requires: `candidate_name`, `position`, `interview_time`, `interviewer`

If `interview_time` is missing, return `TEMPLATE_REQUIRED_VALUE_MISSING` with severity `error` and block draft generation.

### Wrong Email Type

Candidate status: `REJECT_CV`

Requested email type: `INTERVIEW_INVITATION`

Expected email type: `REJECTION_AFTER_CV`

Return `STATUS_EMAIL_MISMATCH` with severity `blocker`.

### Ambiguous Draft Language

Email type: `INTERVIEW_REMINDER`

Draft body: "Congratulations on your offer."

Return `AI_SEMANTIC_MISMATCH` with severity `warning` or `error` and require HR review.
