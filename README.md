# Recruitment Mail Guard

Demo ứng dụng hỗ trợ HR tạo và kiểm tra email tuyển dụng với FastAPI, React,
PostgreSQL, RabbitMQ, Redis và Gemini. Hệ thống chỉ mô phỏng gửi email; không có
SMTP hoặc email provider thật.

## Kiến trúc demo

```text
React frontend
    │ Save Draft (phản hồi ngay)
    ▼
FastAPI ── một PostgreSQL transaction ──► EmailQueue + OutboxEvent(PENDING)
                                              │
                                      Outbox Dispatcher
                                              │ publish
                                              ▼
                                          RabbitMQ
                                              │
                                        Celery Worker
                                      ┌───────┴────────┐
                                      ▼                ▼
                              Redis lock/progress   Gemini review
                                      │                │
                                      └───────┬────────┘
                                              ▼
                                  PostgreSQL review result
                                              │ polling
                                              ▼
                                       React frontend
```

- PostgreSQL là nguồn dữ liệu chính và lưu draft, Outbox Event, review, history,
  audit log.
- RabbitMQ là broker duy nhất của review job.
- Redis chỉ giữ lock chống xử lý trùng và progress có TTL; Redis không thay thế
  PostgreSQL.
- Worker kiểm tra lại `draft_version` và `content_hash` trước khi ghi kết quả.
  Kết quả của draft cũ không thể ghi đè draft mới.
- Nếu RabbitMQ, Redis hoặc Gemini không sẵn sàng, draft vẫn được lưu; UI hiển thị
  trạng thái queued/unavailable và khóa Approve/Simulate Send.

## Chức năng đã hoàn thành

- Save Draft nhanh, không gọi Gemini trong HTTP request.
- Transactional Outbox trong cùng transaction với draft.
- RabbitMQ dispatcher, Celery Agent Worker và Redis deduplication/progress.
- Polling trạng thái Queued, Reviewing, Completed, Unavailable, Failed, Stale.
- Update Status và Schedule Interview từ Candidate Quick Actions.
- Chuẩn hóa datetime rỗng thành `null` và hiển thị FastAPI validation errors.
- SENT read-only; tự cancel draft cũ cùng candidate và email type khi một item SENT.
- Send simulation ghi EmailHistory và AuditLog nhưng không gửi email thật.
- Automated backend, frontend và browser E2E tests.

## Yêu cầu

- Python 3.11+
- Node.js 20+ và npm
- Docker Desktop với Docker Compose

## Cấu hình

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Các biến backend chính:

```text
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/ai_recruitment_email_assistant
RABBITMQ_URL=amqp://guest:guest@localhost:5672//
REDIS_URL=redis://localhost:6379/0
GEMINI_AGENT_ENABLED=false
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
```

Chỉ đặt `GEMINI_AGENT_ENABLED=true` khi `GEMINI_API_KEY` đã được cấu hình ở
backend. Không đưa key vào frontend hoặc commit `.env`.

## Chạy local

Khởi động hạ tầng:

```powershell
docker compose up -d postgres rabbitmq redis
docker compose ps
```

Chuẩn bị backend và seed dữ liệu demo:

```powershell
Set-Location backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.db.seed
```

Mở bốn terminal từ thư mục `backend`:

```powershell
# Terminal 1: API
.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Terminal 2: Outbox Dispatcher
.venv\Scripts\python.exe -m scripts.run_outbox_dispatcher

# Terminal 3: Agent Worker (Windows/demo)
.venv\Scripts\python.exe -m celery -A app.messaging.celery_app:celery_app worker --pool=solo --loglevel=INFO --queues=email_review
```

Mở frontend:

```powershell
Set-Location frontend
npm install
npm run dev
```

- Frontend: `http://localhost:5173`
- FastAPI docs: `http://localhost:8000/docs`
- RabbitMQ management: `http://localhost:15672` (`guest` / `guest`, local demo only)

## Kiểm thử

```powershell
# Backend
Set-Location backend
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m scripts.smoke_test_async_pipeline

# Manual Gemini thật — chỉ dùng synthetic data
.venv\Scripts\python.exe -m scripts.smoke_test_gemini_pipeline

# Frontend
Set-Location ..\frontend
npm test
npm run build
npm run test:e2e
```

`npm run test:e2e` dùng SQLite trong `backend/.e2e`, tắt Gemini, nhưng vẫn chạy
dispatcher/worker thật qua RabbitMQ và Redis. PostgreSQL demo không bị sửa.

## API chính

- `POST /email-drafts/generate`
- `GET /email-queue`
- `GET /email-queue/{id}`
- `PATCH /email-queue/{id}`
- `POST /email-queue/{id}/approve`
- `POST /email-queue/{id}/send`
- `POST /email-queue/{id}/cancel`
- `POST /api/v1/agent/review-draft` — endpoint review thủ công/diagnostic
- `GET /email-history`
- `GET /audit-logs`

## Giới hạn hiện tại

- Schema dùng `Base.metadata.create_all()`; chưa có Alembic migration.
- Chưa có authentication/RBAC hoặc tenant isolation.
- Chưa có resend workflow hoàn chỉnh.
- Chưa có dead-letter dashboard, cluster hoặc production monitoring.
- Validation/review metadata vẫn nằm trong JSON thay vì bảng chuẩn hóa riêng.
- Không gửi email thật.

Xem [docs/demo-runbook.md](docs/demo-runbook.md) để chạy và thuyết trình demo.
