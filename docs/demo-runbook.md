# Demo Runbook

Runbook này dùng dữ liệu synthetic cho một phần trình bày 7–10 phút. Hệ thống
chỉ mô phỏng gửi email, không chuyển email thật ra ngoài.

## 1. Preflight

Từ root repository:

```powershell
docker compose up -d postgres rabbitmq redis
docker compose ps
```

Ba container phải ở trạng thái `healthy`. RabbitMQ management có tại
`http://localhost:15672` với tài khoản local `guest/guest`.

Chuẩn bị backend:

```powershell
Set-Location backend
Copy-Item .env.example .env   # bỏ qua nếu .env đã được cấu hình
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.db.seed
```

Để demo Gemini thật, xác nhận trong `backend/.env`:

```text
GEMINI_AGENT_ENABLED=true
GEMINI_API_KEY=<server-side-key>
GEMINI_MODEL=gemini-2.5-flash
```

Không mở hoặc nhập lại API key trên màn hình trình chiếu.

## 2. Khởi động đủ sáu thành phần

### Terminal 1 — PostgreSQL, RabbitMQ, Redis

```powershell
docker compose up -d postgres rabbitmq redis
```

### Terminal 2 — FastAPI

```powershell
Set-Location backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### Terminal 3 — Outbox Dispatcher

```powershell
Set-Location backend
.venv\Scripts\python.exe -m scripts.run_outbox_dispatcher
```

### Terminal 4 — Agent Worker

```powershell
Set-Location backend
.venv\Scripts\python.exe -m celery -A app.messaging.celery_app:celery_app worker --pool=solo --loglevel=INFO --queues=email_review
```

### Terminal 5 — Frontend

```powershell
Set-Location frontend
npm run dev
```

Mở `http://localhost:5173`. Giữ `http://localhost:8000/docs` và
`http://localhost:15672` làm màn hình kỹ thuật dự phòng.

## 3. Kiểm tra trước khi trình bày

```powershell
# backend/
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m scripts.smoke_test_async_pipeline

# Chỉ chạy khi đã cấu hình Gemini thật
.venv\Scripts\python.exe -m scripts.smoke_test_gemini_pipeline

# frontend/
npm test
npm run build
npm run test:e2e
```

Smoke/E2E dùng SQLite riêng trong `backend/.e2e` và dữ liệu synthetic. E2E tắt
Gemini nhưng vẫn dùng RabbitMQ và Redis thật. Các script tự dọn database và Redis
key test sau khi chạy.

## 4. Kịch bản trình bày

### A. Policy trước AI

1. Mở Candidates và chọn `Do Gia Bao`.
2. Chọn Generate Email Draft.
3. Chỉ ra `PENDING → No email allowed` và nút Continue bị khóa.
4. Giải thích: backend policy quyết định loại email; Gemini không được thay đổi
   quyết định tuyển dụng.

### B. Transactional Outbox và async review

1. Chọn `Nguyen Minh An`, Generate Email Draft.
2. Trình bày `PASS_CV → INTERVIEW_INVITATION` và verified template.
3. Sau Save, chỉ ra “Draft saved – review queued”: HTTP request đã kết thúc mà
   không chờ Gemini.
4. Mở Email Queue và quan sát `Queued → Reviewing → Completed`.
5. Mở Agent Review Journey để chỉ rõ vòng lặp: model chọn tool, backend chạy tool, model quan sát kết quả rồi mới finalize.
6. Mở Technical Review Details, chỉ Queue ID, Draft Version, Review Version, Loop Steps và Tools.
7. Giải thích transaction: draft và Outbox Event được lưu cùng nhau trong
   PostgreSQL; dispatcher publish event sang RabbitMQ.
8. Mở RabbitMQ management nếu cần chứng minh queue `email_review`.

### C. Redis dedupe và stale protection

1. Giải thích worker lấy Redis `SET NX` lock theo queue/version/hash.
2. Sửa subject/body rồi Save lại để tạo draft version mới.
3. Chỉ ra Approve và Simulate Send bị khóa trong lúc review.
4. Khi review mới hoàn tất, Review Version phải khớp Draft Version mới mở action.
5. Kết quả Gemini của version cũ được đánh dấu Stale và không thể ghi đè.

### D. Human in the loop và lifecycle

1. Với draft nhạy cảm của `Tran Bao Chau`, chỉ ra HR approval bắt buộc.
2. Approve sau khi kiểm tra nội dung.
3. Chọn Simulate Send và đọc thông báo “No real email will be delivered”.
4. Sau SENT, item read-only; draft/approved cũ cùng candidate + email type tự
   chuyển CANCELLED và có audit log.
5. Mở Email History và Audit Logs để kết thúc câu chuyện.

## 5. Fallback an toàn

Nếu Gemini, RabbitMQ hoặc Redis không ổn định:

1. Không quay lại gọi Gemini đồng bộ.
2. Draft vẫn được lưu trong PostgreSQL cùng Outbox Event.
3. UI hiển thị Queued hoặc Unavailable; Approve/Simulate Send vẫn bị khóa.
4. Dùng kết quả `smoke_test_async_pipeline` để chứng minh fallback.
5. Không tuyên bố review Completed nếu provider đang unavailable.

Nếu dispatcher/worker dừng giữa demo, khởi động lại hai process; event PENDING vẫn
nằm trong PostgreSQL để dispatcher retry.

## 6. Giới hạn và bước tiếp theo

- Chưa có Alembic; demo tạo bảng bằng `create_all()`.
- Chưa có resend workflow hoàn chỉnh.
- Chưa có DLQ dashboard, RabbitMQ/Redis cluster hoặc production monitoring.
- Chưa có authentication/RBAC.
- Chưa gửi email thật.
- JSON review metadata chưa được chuẩn hóa thành các bảng domain riêng.

Thông điệp chốt: PostgreSQL giữ sự thật, RabbitMQ vận chuyển job, Redis hỗ trợ
idempotency/progress, Gemini chỉ tư vấn, và HR giữ quyền quyết định cuối cùng.
