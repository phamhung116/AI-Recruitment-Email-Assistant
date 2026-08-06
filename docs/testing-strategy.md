# Testing Strategy

## Current State

Backend `unittest` coverage is implemented for the queue state machine, transactional outbox, dispatcher failure, duplicate worker delivery, stale-result protection, Gemini provider boundary, SENT immutability, and auto-cancel. Frontend Vitest and Testing Library cover Quick Actions, async review polling, version checks, and disabled actions. Playwright covers the synthetic full-stack workflow with isolated SQLite and Gemini disabled while still using RabbitMQ, Redis, dispatcher, and worker. Pytest, Ruff, Black, and mypy are not configured.

## Unit Tests

Backend unit tests should cover:

- Status-to-email mapping.
- Sensitive email type detection.
- Placeholder extraction and unsupported placeholder detection.
- Required placeholder value checks.
- Email format validation when implemented.
- Duplicate detection.
- Severity classification.
- Idempotency behavior when implemented.

Frontend unit tests should cover:

- API type mapping helpers.
- Filter behavior for tables.
- Form validation schemas.
- Status badge rendering.

## Integration Tests

Backend integration tests should use a test database and cover:

- Candidate import.
- Draft generation success.
- Draft generation blockers.
- Queue approval.
- Send simulation.
- Audit event creation.
- Email history creation.

## API Tests

API tests should verify:

- Response schemas.
- 404 errors for missing entities.
- 400 errors for invalid workflow actions.
- Validation issue payload shape.
- Pagination once implemented.
- Idempotency once implemented.

## Frontend Tests

Implemented:

- Structured deterministic blockers and remediation display.
- Gemini completed, unavailable, uncertainty, and suggested-wording states.
- Stale review behavior after an HR edit.
- Status-to-email policy mapping, including blocked `PENDING` status.
- Queue approval lock while content is unsaved.
- Sensitive draft action availability.
- Save-before-action workflow.
- Explicit send-simulation confirmation.
- Automatic Queued/Reviewing polling and terminal-state rendering.
- Approval/send locks until review and draft versions match.
- SENT read-only rendering and technical version details.

Still recommended:

- Component tests for candidate detail, template editor, and queue review drawer.
- Mock API tests for success/error/loading/empty states.
- Accessibility checks for dialogs and forms.
- A separate upload E2E case for Excel import validation.

## Agent Contract Tests

Once an LLM provider abstraction exists:

- Validate structured output parsing.
- Reject missing required fields.
- Reject unexpected severity values.
- Ensure deterministic blockers cannot be downgraded by AI output.
- Ensure refusal behavior for pass/fail or status-change requests.

## Prompt Regression Tests

Maintain a fixed prompt evaluation set:

- Correct interview invitation.
- Rejection email with wrong candidate name.
- Offer email with missing salary or policy data.
- Interview reminder with contradictory date.
- Unsupported status label.
- Draft that claims email was sent.

Each prompt version should be compared against expected issue IDs and severity bands.

## Evaluation Dataset

Start with small JSON fixtures:

- Valid candidate rows.
- Missing email.
- Invalid email.
- Duplicate email.
- Missing interview time.
- Unsupported status.
- Wrong email type.
- Unsupported placeholder.
- Sensitive template not flagged.

Use synthetic data only. Do not commit real candidate records.

## Adversarial And Failure Cases

- Prompt injection inside candidate notes.
- Candidate name attempting to change instructions.
- Template text that tells the agent to ignore rules.
- Missing template.
- LLM timeout.
- Malformed LLM JSON.
- Duplicate idempotency key with different input.
- Large Excel file.
- Corrupt Excel file.

## Manual Acceptance Tests

1. Seed database.
2. Open frontend dashboard.
3. Import sample candidate file.
4. Open a `PASS_CV` candidate with interview data.
5. Generate `INTERVIEW_INVITATION`.
6. Confirm queue row has passing risk result.
7. Open a `PENDING` candidate and confirm draft generation is blocked.
8. Create template with unsupported placeholder and confirm generation is blocked.
9. Approve a sensitive draft.
10. Run send simulation and confirm history/audit entries are created.

## Current Backend Test Command

Backend:

```bash
cd backend
python -m unittest discover -s tests -v
```

## Current Frontend Test Commands

Frontend:

```bash
cd frontend
npm test
npm run test:coverage
```

`npm run test:watch` is available for local development. A lint command is not configured yet.

## Current Browser E2E Command

```bash
cd frontend
npm run test:e2e
```

The runner starts isolated servers on ports `18000` and `14173`, recreates `backend/.e2e/recruitment-e2e.sqlite3`, disables Gemini, starts a Celery worker and Outbox Dispatcher, then removes the SQLite file after the test. RabbitMQ and Redis must already be healthy. Install the browser once with `npx playwright install chromium`.
