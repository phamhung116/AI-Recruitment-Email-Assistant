# AI Recruitment Email Assistant

Trợ lý nội bộ giúp HR import ứng viên, tạo email từ fixed template, chạy deterministic safety checks và gửi email thật theo từng ứng viên qua Resend. HR luôn là người xác nhận cuối cùng; hệ thống không dùng AI để quyết định tuyển dụng.

## Kiến trúc MVP

- Frontend: React, TypeScript, Vite, TanStack Query, Axios, Zustand, TailwindCSS, Radix/shadcn-style components, Lucide, Recharts.
- Backend: FastAPI, SQLAlchemy 2, Pydantic v2.
- Database: PostgreSQL 16, migration bằng Alembic.
- Email provider: Resend REST API, gửi thật từng ứng viên.
- Safety: fixed protected templates, deterministic checks, immutable revisions, explicit HR confirmation, one logical operation per draft, provider idempotency key, governed `DELIVERY_UNKNOWN` reconciliation.
- AI/LLM: không nằm trong MVP hiện tại. OpenAI/Claude semantic review là integration point về sau và chỉ mang tính advisory.

RabbitMQ, Redis, Celery, Gemini và send simulation đã bị ngắt khỏi runtime mới.

## Cấu hình

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Các biến backend quan trọng:

```dotenv
DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/<database>
RESEND_API_KEY=
EMAIL_SENDER_ADDRESS=onboarding@resend.dev
EMAIL_SENDER_NAME=Recruitment Team
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Không commit `.env` hoặc đưa `RESEND_API_KEY` vào frontend. `EMAIL_SENDER_ADDRESS` phải là sender/domain đã được Resend cho phép. Khi chưa có key, backend chủ động chặn real send.

Frontend dùng:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

## Chạy demo bằng Docker

```powershell
docker compose up --build --remove-orphans
```

- Frontend: `http://localhost:5173`
- FastAPI docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- PostgreSQL trong Docker expose ra host qua port `5433`, tránh đụng PostgreSQL local đang chạy ở port `5432`.

## Chạy local

Khởi động PostgreSQL:

```powershell
docker compose up -d postgres
docker compose ps
```

Backend:

```powershell
Set-Location backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.db.seed
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend, ở terminal khác:

```powershell
Set-Location frontend
npm install
npm run dev
```

- Frontend: `http://localhost:5173`
- FastAPI docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

`uvicorn` là ASGI server dùng để chạy FastAPI. `app.main:app` trỏ tới biến FastAPI `app` trong `backend/app/main.py`; `--reload` chỉ dùng cho development.

## Database hiện có

Migration `001_initial_core_schema` dành cho database mới. Nếu database đang chứa schema prototype cũ, không chạy migration mù: cần backup và xác nhận mapping các stage/status legacy trước. Không tự động đổi `NEW`, `OFFER`, `INTERVIEW_CONFIRMED` hoặc `OFFER_ACCEPTED`, vì đó có thể làm sai dữ liệu tuyển dụng.

Target schema gồm:

- `candidates`
- `draft_revisions`
- `logical_send_operations`
- `provider_attempts`
- `audit_logs`

## Kiểm thử

Backend:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe scripts\export_openapi.py --check
```

Frontend:

```powershell
Set-Location frontend
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

To use an existing Google Chrome installation instead of Playwright Chromium on Windows:

```powershell
$env:PLAYWRIGHT_CHANNEL = "chrome"
npm run test:e2e
```

Browser E2E dùng SQLite tạm, không gọi Resend và không sửa PostgreSQL local. Test chỉ đi tới confirmation dialog, không xác nhận gửi thật.

## API v1

Canonical contract: [docs/api-contract.md](docs/api-contract.md). Static OpenAPI: [docs/backend/openapi.json](docs/backend/openapi.json).

Các workflow chính:

- `POST /api/v1/candidates/import/preview`
- `POST /api/v1/candidates/import`
- `GET /api/v1/candidates`
- `POST /api/v1/drafts`
- `PATCH /api/v1/drafts/{draft_revision_id}`
- `POST /api/v1/drafts/{draft_revision_id}/send`
- `POST /api/v1/send-operations/{operation_id}/retry`
- `POST /api/v1/send-operations/{operation_id}/reconcile`
- `POST /api/v1/send-operations/{operation_id}/resolve`
- `GET /api/v1/audit-logs`

## Giới hạn an toàn

- Chưa có authentication, RBAC hoặc rate limiting. Chỉ chạy trong môi trường local/internal tin cậy, không public Internet.
- Chỉ gửi từng ứng viên; không batch send hoặc auto send.
- Resend trả `PROVIDER_ACCEPTED` nghĩa là provider đã nhận request, không bảo đảm email đã vào inbox.
- `DELIVERY_UNKNOWN` không được retry mù. Hệ thống yêu cầu replay cùng idempotency key trong 24 giờ hoặc HR xác minh và resolve thủ công có audit.
- Không có AI hiring decision, CV screening hoặc LLM semantic review trong MVP.
