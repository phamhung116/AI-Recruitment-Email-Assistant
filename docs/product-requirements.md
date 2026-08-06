# Product Requirements

## Problem Statement

Recruitment teams send high-volume candidate emails that can contain sensitive decisions, schedule details, and personal data. Manual drafting is slow and error-prone; pure AI drafting is risky because the AI must not decide hiring outcomes or invent missing information.

`Recruitment Mail Guard` should help HR draft and validate recruitment emails while preserving human control, deterministic policy enforcement, and auditability.

## Target Users

- HR recruiters who prepare candidate communication.
- HR managers who review sensitive or high-risk drafts.
- Engineering/admin users who configure templates, rules, and integrations.

## User Stories

- As HR, I can import candidate data from an Excel file so that I do not enter records manually.
- As HR, I can view candidate status and email readiness before generating a draft.
- As HR, I can generate an email draft only when candidate status maps to an allowed email type.
- As HR, I can see blocking errors and warnings before reviewing a draft.
- As HR, I can edit, approve, reject, or cancel a draft before any delivery action.
- As HR manager, I can require approval for sensitive email types such as rejection and offer emails.
- As admin, I can manage approved templates and required placeholders.
- As auditor, I can review processing history and audit events.

## Functional Requirements

- Import `.xlsx` candidate files.
- Normalize candidate fields from known headers.
- Validate required candidate data before draft generation.
- Validate email format before draft generation. Not implemented.
- Detect duplicate candidates or recipients. Partially implemented for Excel import and sent email history.
- Map recruitment status to email type through explicit rules.
- Generate drafts from approved templates and candidate fields.
- Detect unresolved or unsupported template placeholders.
- Classify validation findings by severity. Not implemented.
- Present drafts and warnings in an HR review queue.
- Record audit events for generation, approval, cancellation, status update, and delivery simulation.
- Store processing history for traceability. Partially implemented through `EmailHistory` and `AuditLog`.
- Avoid real automatic email sending in MVP.

## Non-Functional Requirements

- Safety: AI cannot make hiring decisions or change status.
- Reliability: deterministic rules must run before LLM review.
- Traceability: processing runs and audit events must be queryable.
- Privacy: candidate PII must be minimized in logs, prompts, and provider calls.
- Maintainability: use existing FastAPI, SQLAlchemy, React, Vite, and TypeScript structure.
- Local development: support Docker PostgreSQL and separate backend/frontend dev servers.

## MVP Scope

In MVP:

- Candidate import and manual candidate update.
- Explicit status-to-email mapping.
- Deterministic validation rule engine.
- Template-based draft generation.
- Optional LLM semantic review behind a provider abstraction.
- HR review queue with approve/edit/reject/cancel decisions.
- Processing run records and audit events.
- Send simulation only.

Current implementation already has some of this scope but needs hardening and alignment with the target safety model.

## Explicitly Excluded Features

- Real email sending.
- Fully automated candidate pass/fail decisions.
- Automated recruitment status changes by AI.
- CV screening or candidate scoring.
- Multi-tenant enterprise RBAC.
- Production-grade compliance certification.
- Background campaign delivery.

## Success Criteria

- HR can process a sample candidate file end-to-end without real email delivery.
- Invalid or risky drafts show deterministic findings before review.
- Sensitive email types cannot bypass HR approval.
- Draft generation is traceable through processing run and audit records.
- LLM output, when added, is structured and cannot override deterministic rules.
- Automated tests cover key validation rules and API contracts.

## Unknowns And Needs Confirmation

- Authentication and real actor identity model: Not implemented.
- Retention period for candidate PII and audit logs: Needs confirmation.
- Final company-defined recruitment statuses and email type rules: Needs confirmation.
- Real email provider roadmap after MVP: Needs confirmation.
- Compliance requirements such as GDPR, SOC 2, or local labor-law constraints: Unknown.
