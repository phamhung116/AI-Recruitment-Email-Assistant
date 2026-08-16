# Demo Runbook

This runbook demonstrates the current Recruitment Mail Guard workflow. The application uses PostgreSQL, FastAPI, React and the Resend HTTP API. Gemini, RabbitMQ, Redis, Celery and simulated sending are not part of the active runtime.

## 1. Preflight

From the repository root:

```powershell
docker compose up -d postgres
docker compose ps
```

Prepare the backend with a fresh database:

```powershell
Set-Location backend
Copy-Item .env.example .env
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.db.seed
```

Configure these values in `backend/.env` for a controlled real-email demonstration:

```text
RESEND_API_KEY=<server-side-key>
EMAIL_SENDER_ADDRESS=recruitment@your-verified-domain.example
EMAIL_SENDER_NAME=HiLab Recruitment Team
```

Never display, commit or place the Resend API key in frontend configuration. Use a test candidate email address controlled by the presenter.

The initial Alembic migration targets a fresh database. Do not apply it blindly to the legacy prototype database; first back up the database and approve mappings for legacy stage/status values.

## 2. Start The Application

Backend terminal:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API documentation is available at `http://localhost:8000/docs`.

## 3. Verification Before The Demo

```powershell
# backend/
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe scripts\export_openapi.py --check

# frontend/
npm test
npm run build
```

Browser E2E intentionally stops at the real-send confirmation dialog and does not call Resend:

```powershell
$env:PLAYWRIGHT_CHANNEL = "chrome"
npm run test:e2e
```

## 4. Demo Journey

1. Open Candidates and import or select a synthetic candidate.
2. Review the candidate Application ID, Stage and Decision.
3. Generate a fixed-catalog email draft.
4. Show the protected decision-critical content and deterministic safety findings.
5. Edit the allowed subject or content area to create a new immutable revision.
6. Select Send and show that no provider request occurs before explicit HR confirmation.
7. Confirm only when the recipient is a controlled test mailbox.
8. Open Email Operations and show the logical operation, provider attempt and provider message ID.
9. Open Audit Logs and show the draft/send events without exposing the email body or recipient PII.

## 5. Failure And Recovery Cases

- Missing API key or sender configuration blocks the provider call.
- A definitive provider rejection records the failure and does not mark the candidate outcome as communicated.
- A timeout or lost response becomes `DELIVERY_UNKNOWN`; do not create a new send blindly.
- Reconciliation within the provider idempotency window replays the same logical operation and idempotency key.
- Manual resolution requires acknowledgement, actor and rationale and is always audited.

## 6. Current Limitations

- No authentication, RBAC or rate limiting; use only on a trusted local/internal network.
- Resend acceptance means the provider accepted the request, not guaranteed inbox delivery.
- Delivery and bounce webhooks are not implemented yet.
- No bulk or automatic sending.
- No LLM semantic review in the current MVP.
