# AI Recruitment Email Assistant

Trợ lý AI hỗ trợ quy trình gửi email tuyển dụng. MVP này tập trung vào workflow quản lý ứng viên, template email, generate draft bằng mock AI, queue approval và send simulation.

## Scope hiện tại

- Không tích hợp Claude/OpenAI thật.
- Không gửi email thật qua Gmail/Outlook/SendGrid.
- Không build CV screening.
- AI provider hiện tại là `MockAIEmailService`.
- Email sending hiện tại là simulation trong backend.

## Tech stack

- Frontend: ReactJS + TypeScript + Vite
- Backend: Python FastAPI
- Database: PostgreSQL
- ORM: SQLAlchemy
- Excel import: openpyxl
- Email/AI provider: mock services

## Cấu trúc

```text
backend/
  app/
    api/
      candidateRoutes.py
      dashboardRoutes.py
      emailHistoryRoutes.py
      emailQueueRoutes.py
      emailTemplateRoutes.py
      routes.py
    constants/
    core/config.py
    db/database.py
    db/seed.py
    models/entities.py
    schemas/api.py
    services/ai_email.py
    services/email_workflow.py
    services/rules.py
frontend/
  src/
    app/
    components/
    constants/
    features/
      auditLogs/
      candidates/
      dashboard/
      emailHistory/
      emailQueue/
      emailTemplates/
    lib/
    services/recruitmentApi.ts
    stores/
    types/
    utils/
    main.tsx
    styles.css
```

## Coding standards đã áp dụng

- Frontend dùng React + TypeScript, React Router, TanStack Query, Axios, Zustand, TailwindCSS, shadcn/ui-style source components, React Hook Form, Zod, Recharts và Lucide Icons.
- Frontend không còn gộp nhiều page vào `main.tsx`; mỗi page/component/service/constant được tách file riêng theo feature.
- Route-level lazy loading được bật để giảm initial bundle.
- Design system dùng HiLab Technology official brand tokens: primary red `#fb2c36`, accent yellow `#fac800`, neutral gray palette, semantic status colors và dark-mode CSS variables.
- Naming trong source dùng tiếng Anh; React component dùng PascalCase; biến/hàm JS dùng camelCase; shared constants dùng UPPER_CASE.
- Backend được tách theo domain route và service để giảm method dài, giảm duplicate logic và tránh hard-code message/action.
- API URL lấy từ `.env` qua `VITE_API_BASE_URL`; backend config lấy từ `.env`.
- UI có loading/error/empty states cơ bản và button dùng `type="button"` để tránh submit ngoài ý muốn.
- Các tiêu chí review lệch tech stack gốc như NestJS/Prisma/Tailwind/shadcn/Zustand được xem là N/A cho MVP FastAPI + ReactJS này.

## Setup database

Tạo PostgreSQL database:

```bash
createdb ai_recruitment_email_assistant
```

Hoặc dùng connection string khác trong `backend/.env`.

Nếu muốn chạy nhanh bằng Docker:

```bash
docker compose up -d postgres
```

## Run backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app.db.seed
uvicorn app.main:app --reload
```

API chạy tại `http://localhost:8000`.

FastAPI docs: `http://localhost:8000/docs`.

Ghi chú: MVP đang dùng `Base.metadata.create_all()` khi startup để dễ demo local. Khi production hóa, nên thay bằng Alembic migration đầy đủ.

## Run frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend chạy tại `http://localhost:5173`.

Trên Windows PowerShell, nếu `npm` bị chặn bởi execution policy, dùng `npm.cmd install` và `npm.cmd run dev`.

Build production frontend:

```bash
npm run build
```

## Excel import

File `.xlsx` nên có header:

```text
full_name, email, phone, position, stage, status, interview_time, interviewer, note
```

`interview_time` có thể là datetime cell trong Excel hoặc ISO string.

File mẫu để test upload đã có tại:

```text
sampleData/candidates_import_sample.xlsx
```

Backend sẽ tự skip candidate có email trùng để tránh import lặp dữ liệu khi test nhiều lần.

## Workflow demo

1. Seed database bằng `python -m app.db.seed`.
2. Mở Candidates, chọn một candidate có status như `PASS_CV`, `REJECT_CV`, `INTERVIEW_CONFIRMED`.
3. Bấm Generate Draft.
4. Mở Email Queue để preview/edit.
5. Nếu email sensitive như rejection hoặc offer, approve trước.
6. Bấm Send để simulation tạo `email_history` và cập nhật queue status.

Nếu candidate status là `PENDING`, backend sẽ block generate email với message:

```text
Candidate status is pending. Please update status before generating email.
```

## REST API

- `POST /candidates/import`
- `GET /candidates`
- `GET /candidates/{id}`
- `PATCH /candidates/{id}`
- `GET /email-templates`
- `POST /email-templates`
- `PATCH /email-templates/{id}`
- `DELETE /email-templates/{id}`
- `POST /email-drafts/generate`
- `GET /email-queue`
- `GET /email-queue/{id}`
- `PATCH /email-queue/{id}`
- `POST /email-queue/{id}/approve`
- `POST /email-queue/{id}/send`
- `POST /email-queue/{id}/cancel`
- `GET /email-history`
- `GET /audit-logs`

## Future integration points

- Claude/OpenAI: implement class mới theo interface `AIEmailService` trong `backend/app/services/ai_email.py`.
- Gmail/Microsoft Graph/SendGrid: thay logic simulation trong `send_email()` bằng email provider service riêng.
- Alembic: thêm migration để quản lý schema thay cho `create_all`.
- Auth/RBAC: thay actor mặc định `demo_hr` bằng user thật từ auth context.
