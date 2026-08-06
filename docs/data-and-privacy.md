# Data And Privacy

## Candidate Data Classification

Candidate data is sensitive personal information.

Current fields:

- Name: PII.
- Email: PII.
- Phone: PII.
- Position: recruitment context.
- Stage/status: hiring process data.
- Interview time/interviewer: scheduling and employee context.
- Note: may contain sensitive free text.
- Email subject/body: may contain PII and hiring outcome information.

## Minimum Data Required

Draft generation should only use:

- Candidate name.
- Candidate email.
- Position.
- Recruitment status.
- Required template fields, such as interview time and interviewer when the template requires them.

Do not send notes or phone number to an LLM unless a specific prompt requires them and HR approves the exposure.

## Retention Assumptions

Current repository: Not implemented.

Needs confirmation:

- Candidate record retention period.
- Email draft retention period.
- Audit log retention period.
- Deletion/anonymization process after retention expires.

## Secrets Management

Current:

- Backend reads `.env` through Pydantic settings.
- Frontend reads `VITE_API_BASE_URL`.
- No real LLM or email provider secrets exist.

Target:

- Keep secrets out of Git.
- Use environment variables for provider keys.
- Never expose backend provider secrets to frontend.

## Logging Restrictions

- Do not log full candidate payloads.
- Do not log full email body by default.
- Do not log raw prompts containing PII.
- Do not include sensitive candidate notes in audit metadata.
- Use correlation IDs and entity references instead of raw PII.

Current audit metadata is limited but not governed by a formal masking policy.

## PII Masking

Target examples:

- Email: `a***@example.com`
- Phone: `******0001`
- Candidate name in logs: use candidate ID where possible.

PII masking utility: Not implemented.

## Audit Requirements

Audit events should record:

- Actor.
- Action.
- Entity type and ID.
- Timestamp.
- Decision result.
- Validation issue summary.
- Prompt/model version when an LLM is used.

Current `AuditLog` supports action, entity, actor, metadata JSON, and timestamp.

## Provider Data Exposure

Current: no external model provider.

Target:

- Minimize prompt data.
- Record provider, model, prompt version, and structured output validation status.
- Avoid sending candidate notes unless necessary.
- Include opt-out/provider exposure policy before production use.

## Deletion Strategy

Current: Not implemented.

Target:

- Soft delete or anonymize candidate data.
- Preserve audit integrity with entity IDs and masked summaries.
- Define deletion behavior for drafts, history, processing runs, and validation issues.

## Unresolved Compliance Questions

- Applicable jurisdictions and privacy laws: Unknown.
- Candidate consent basis for AI-assisted processing: Needs confirmation.
- Data processing agreement requirements for model providers: Needs confirmation.
- Right-to-delete and right-to-access workflows: Needs confirmation.
- Production security review owner: Needs confirmation.
