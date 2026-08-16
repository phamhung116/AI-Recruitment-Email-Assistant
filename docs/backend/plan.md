# Backend Implementation Plan

## Objective
Thiết lập kế hoạch triển khai Backend toàn diện cho hệ thống **Recruitment Mail Guard (Minimal Real-Email MVP)** dựa trên các đặc tả đã duyệt (Product Specification v1.0.1, Business Analysis v1.2.0-BA, System Design ADR-001..007, Database Specification v1.0.0-DB). Kế hoạch này được chuẩn bị ở chế độ `PLAN_ONLY` để cung cấp lộ trình thực thi theo Vertical Slices chi tiết, an toàn, có thể kiểm thử và truy vết cho Coding Agent tiếp theo.

## Status
COMPLETED

## Inputs
| Input Document | Canonical Path | Required / Optional | Approval State | Fingerprint (SHA-256) |
| :--- | :--- | :--- | :--- | :--- |
| Product Spec | `docs/product/product.md` | Required | APPROVED_FOR_DELIVERY | `667ee99f494a4cf55f18914b7d2e25dce818c2716a443b235346ede1e7cbf5e4` |
| Business Analysis | `docs/ba/business-analysis.md` | Required | APPROVED | `d425d5f0de918d0261974906122dada3834be70cf5ee14bf1041e833eeef97ab` |
| BA Traceability | `docs/ba/requirements-traceability.md` | Optional | APPROVED | `1926a124ca2918fc4754bc681237105c410773e7f793f9fd2f6d347636ce00b3` |
| System Design | `docs/system-design/system-design.md` | Required | APPROVED | `e684be53a735d86d7ded34368052abadea01990920b32d3331585072e3b6c1cc` |
| SD Traceability | `docs/system-design/traceability.md` | Optional | APPROVED | `3d74468b73135f5ea3f91771a599c18bc4074de43e5023b5b8c34afca4e16f62` |
| Database Spec | `docs/database/database.md` | Required | READY_FOR_REVIEW | `d29f5ee5fd86d7eebbca877be436961e8cb946c10d07e6184103d547f02ae744` |
| Data Dictionary | `docs/database/data-dictionary.md` | Optional | DRAFT_OR_UNAPPROVED | `cd2bc119e26c2e865f3553c6faee9f3b04fc0f98d03fd77f2ebfee6ce84a072e` |
| DB Traceability | `docs/database/traceability.md` | Optional | DRAFT_OR_UNAPPROVED | `532024f969bf2255f8fd3ffc41018b76696c5c40ddce218f245e9eca90f24ad1` |

## Input Fingerprints
- `docs/product/product.md`: `667ee99f494a4cf55f18914b7d2e25dce818c2716a443b235346ede1e7cbf5e4`
- `docs/ba/business-analysis.md`: `d425d5f0de918d0261974906122dada3834be70cf5ee14bf1041e833eeef97ab`
- `docs/ba/requirements-traceability.md`: `1926a124ca2918fc4754bc681237105c410773e7f793f9fd2f6d347636ce00b3`
- `docs/system-design/system-design.md`: `e684be53a735d86d7ded34368052abadea01990920b32d3331585072e3b6c1cc`
- `docs/system-design/traceability.md`: `3d74468b73135f5ea3f91771a599c18bc4074de43e5023b5b8c34afca4e16f62`
- `docs/database/database.md`: `d29f5ee5fd86d7eebbca877be436961e8cb946c10d07e6184103d547f02ae744`
- `docs/database/data-dictionary.md`: `cd2bc119e26c2e865f3553c6faee9f3b04fc0f98d03fd77f2ebfee6ce84a072e`
- `docs/database/traceability.md`: `532024f969bf2255f8fd3ffc41018b76696c5c40ddce218f245e9eca90f24ad1`

## Current-State Findings
Khảo sát hiện trạng codebase tại `backend/`:
1. **Tech Stack & Runtime**: Python 3.11+, FastAPI web framework, SQLAlchemy 2.0 ORM, PostgreSQL database (`recruitment_db`).
2. **Quản lý Package**: `backend/requirements.txt` (chứa các thư viện thừa: `celery`, `redis`, `google-generativeai`, `pika`).
3. **ORM Models Hiện tại (`backend/app/models/entities.py`)**:
   - `Candidate`: Thiếu `application_id` (bắt buộc), `communicated_decision`, `communicated_stage`, `communicated_at`.
   - `EmailTemplate`: Bảng database lưu mẫu email động (trái với System Design/Product quy định Fixed Template Catalog in-code).
   - `EmailQueue`: Bảng queue đơn giản lưu draft và simulation flag (trái với System Design/Database quy định `draft_revisions`).
   - `EmailHistory`: Bảng log phẳng không có liên kết attempts (trái với Database Spec quy định `logical_send_operations` + `provider_attempts`).
   - `OutboxEvent`: Bảng Transactional Outbox (trái với System Design ADR-002/ADR-003 quy định Synchronous REST call).
   - `AuditLog`: Schema cũ (`action`, `metadata_json`), thiếu `event_name`, `entity_type`, `entity_id`, `application_id`, `payload_json`.
4. **Services Hiện tại (`backend/app/services/`)**:
   - `email_workflow.py`: Monolithic 350+ dòng chứa lẫn lộn simulation, risk checks, outbox publish.
   - `agent_review.py`, `agent_worker.py`, `gemini_provider.py`, `skill_loader.py`, `review_progress.py`, `draft_review_queue.py`: Các module LLM semantic review không thuộc MVP core scope.
   - `outbox_dispatcher.py`: Worker background polling không thuộc target architecture.
5. **Database Migration State**: Hiện chưa có thư mục Alembic migrations; khởi tạo bảng bằng `Base.metadata.create_all` lúc startup.
6. **Docker Services (`docker-compose.yml`)**: Chạy service `postgres` 16 trên cổng 5432.
7. **Test Framework**: `pytest` đã có trong requirements; các test hiện tại (`backend/tests/`) tập trung vào async review pipeline cũ và simulation cũ.

## Reconciliation Findings
| Finding ID | Phân loại | Mô tả Chi tiết | Nguồn Đối chiếu | Thành phần Ảnh hưởng | Kế hoạch Xử lý |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `FND-001` | `IMPLEMENTATION_GAP` | Thiếu trường `application_id` bắt buộc trên `candidates` và thiếu 4 bảng mục tiêu (`draft_revisions`, `logical_send_operations`, `provider_attempts`, `audit_logs`). | `DB-TBL-001`..`005`, `ADR-003` | `app/models/entities.py`, Migration | Tạo 5 ORM models chuẩn và Alembic initial migration. |
| `FND-002` | `IMPLEMENTATION_GAP` | Chưa triển khai Resend Synchronous REST Adapter với Idempotency-Key và chuẩn hóa 3 trạng thái (`PROVIDER_ACCEPTED`, `DEFINITIVE_FAILURE`, `DELIVERY_UNKNOWN`). | `CAP-006`, `FR-006`, `ADR-002` | `app/adapters/resend_adapter.py` (NEW) | Xây dựng adapter với `httpx`, timeout 10s, SHA-256 payload digest. |
| `FND-003` | `IMPLEMENTATION_GAP` | Luồng gửi email hiện tại giữ DB transaction và giả lập send; chưa áp dụng mô hình 3 pha tách rời (Phase A -> Phase B -> Phase C). | `CAP-007`, `FR-005`, `ADR-005` | `app/services/send_orchestrator.py` (NEW) | Tách biệt hoàn toàn HTTP call ra ngoài DB transaction. |
| `FND-004` | `IMPLEMENTATION_GAP` | Chưa có Contradiction Guard theo cặp khóa `Application ID` + `Stage` và Decision Correction workflow (bắt buộc `correction_rationale`). | `CAP-005`, `FR-004`, `BR-001`, `BR-008` | `app/services/safety_guard.py` (NEW) | Hiện thực bộ kiểm tra deterministic và quản lý draft superseding. |
| `FND-005` | `LEGACY_DECOMMISSION` | Codebase chứa RabbitMQ, Redis, Celery tasks, Outbox dispatcher và Gemini LLM pipeline. | `ADR-006`, `ADR-007` | `app/messaging/`, `app/tasks/`, `app/services/gemini_*`, `outbox_*` | Cô lập, loại bỏ khỏi core runtime và cập nhật `requirements.txt`. |
| `FND-006` | `SAFE_DERIVATION` | Quản lý Fixed Template Catalog dưới dạng Python constants/dataclass thay vì đọc bảng DB `email_templates`. | `DEC-005`, `CAP-002` | `app/constants/templates.py` (NEW) | Khai báo đủ 5 template chuẩn (`INTERVIEW_INVITATION`, `REJECTION_AFTER_CV`, `OFFER_EMAIL`, `REJECTION_AFTER_INTERVIEW`, `DECISION_CORRECTION`) in-code. |
| `FND-007` | `SAFE_DERIVATION` | Đặt tên trường `full_name` trong database tương thích với cột `candidate name` / `name` khi import Excel. | `VAL-001`, `COL-003` | `app/services/excelImport.py` | Ánh xạ linh hoạt `candidate name` -> `full_name` khi đọc Excel. |
| `FND-008` | `ENVIRONMENT_DEPENDENCY` | Khởi chạy thực tế cần PostgreSQL 16 và API Key Resend hợp lệ (`RESEND_API_KEY`). | `ADR-002`, `CON-001` | `.env.example`, `app/core/config.py` | Khai báo trong `.env.example`, mock hoàn toàn trong test suite. |

## Environment Gate
| Tên Biến Môi Trường | Mục Đích Sử Dụng | Yêu Cầu Bắt Buộc | Độ Nhạy Cảm | Trạng Thái Phân Loại |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL 16 connection string | YES | YES | Required for local runtime & implementation |
| `BACKEND_HOST` | Host binding cho FastAPI (Mặc định: `0.0.0.0`) | NO | NO | Has safe default (`0.0.0.0`) |
| `BACKEND_PORT` | Port binding cho FastAPI (Mặc định: `8000`) | NO | NO | Has safe default (`8000`) |
| `ENVIRONMENT` | Môi trường runtime (`development` / `test`) | NO | NO | Has safe default (`development`) |
| `LOG_LEVEL` | Cấp độ log (`INFO` / `DEBUG`) | NO | NO | Has safe default (`INFO`) |
| `CORS_ORIGINS` | Danh sách domain Frontend được gọi API | NO | NO | Has safe default (`http://localhost:5173`) |
| `RESEND_API_KEY` | API Key xác thực gửi email thật qua Resend REST API | YES | YES | BLOCKED: chưa có trong `backend/.env` hoặc process environment |
| `EMAIL_SENDER_ADDRESS` | Email người gửi mặc định (verified trên Resend) | YES (Cho Live Send) | NO | Có safe default cho Resend sandbox (`onboarding@resend.dev`) |
| `EMAIL_SENDER_NAME` | Tên hiển thị người gửi email | NO | NO | Has safe default (`Recruitment Team`) |

**Environment Gate Status**: `PASS` — đã xác minh `DATABASE_URL`, `RESEND_API_KEY` và `EMAIL_SENDER_ADDRESS` đều có giá trị mà không in hoặc lưu secret vào tài liệu.

## Approved Stack and Backend Root
- **Ngôn ngữ**: Python 3.11+
- **Web Framework**: FastAPI 0.110+ (Asgi / Starlette)
- **Database Engine**: PostgreSQL 16
- **ORM / Persistence**: SQLAlchemy 2.0 (Declarative Mapping)
- **Migration Tool**: Alembic
- **HTTP Client**: `httpx` / `requests` (Synchronous with timeout)
- **Test Runner**: `pytest`, `pytest-asyncio`, `httpx` (MockTransport)
- **Backend Root Directory**: `backend`

## Requirement Traceability
| Requirement ID | Architectural Source | Database Table | Vertical Slice ID | Target Module / Route |
| :--- | :--- | :--- | :--- | :--- |
| `CAP-001`, `FR-001`, `FR-012` | `ADR-001` | `candidates` | `SLICE-005`, `SLICE-017` | `app/services/excelImport.py`, `POST /candidates/import` |
| `CAP-002`, `FR-002`, `DEC-005` | `ADR-001` | In-Memory Catalog | `SLICE-006` | `app/constants/templates.py`, `app/services/template_service.py` |
| `CAP-003`, `FR-003`, `FR-010` | `ADR-001` | `draft_revisions` | `SLICE-006`, `SLICE-009` | `app/services/draft_service.py` |
| `CAP-004`, `FR-004`, `BR-004` | `ADR-001` | `draft_revisions` | `SLICE-007`, `SLICE-008`, `SLICE-009` | `app/services/safety_guard.py`, `POST /drafts/generate` |
| `CAP-008`, `FR-008`, `DEC-003` | `ADR-004` | `draft_revisions` | `SLICE-010` | `app/services/draft_service.py`, `POST /drafts/correct` |
| `CAP-006`, `FR-006`, `SPIKE-001` | `ADR-002` | `provider_attempts` | `SLICE-012` | `app/adapters/resend_adapter.py` |
| `CAP-007`, `FR-005`, `BR-013` | `ADR-003`, `ADR-005` | `logical_send_operations` | `SLICE-011`, `SLICE-013` | `app/services/send_orchestrator.py`, `POST /drafts/{id}/send` |
| `CAP-008`, `FR-007`, `AC-015` | `ADR-004` | `logical_send_operations` | `SLICE-014`, `SLICE-015` | `app/services/send_orchestrator.py`, `POST /operations/{id}/resolve` |
| `CAP-009`, `FR-009`, `NFR-002` | `ADR-005` | `audit_logs` | `SLICE-016`, `SLICE-017` | `app/services/audit_service.py`, `GET /audit-logs` |
| `NFR-001`..`NFR-004` | `ADR-001`..`007` | Toàn bộ 5 Tables | `SLICE-001`..`SLICE-020` | Toàn bộ Backend Architecture |

## Vertical Slices

### Slice SLICE-001: Backend Foundation & Dependency Cleanup
- **Requirement Sources**: `NFR-001`, `ADR-001`, `ADR-006`
- **Dependencies**: None
- **Status**: completed
- **Acceptance Criteria**:
  - Dọn dẹp `backend/requirements.txt`: Loại bỏ Celery, Redis, RabbitMQ (pika), Gemini SDK khỏi runtime dependencies bắt buộc.
  - Tổ chức lại cấu trúc thư mục backend chuẩn Modular Monolith (`app/adapters/`, `app/constants/`, `app/core/`, `app/db/`, `app/models/`, `app/schemas/`, `app/services/`, `app/api/`).
- **Expected Files**:
  - `backend/requirements.txt`
  - `backend/app/core/config.py`
  - `backend/app/constants/__init__.py`
- **Actual Changed Files**:
  - `backend/requirements.txt`
  - `backend/app/core/config.py`
  - `backend/app/adapters/__init__.py`
  - `backend/tests/test_config.py`
  - `backend/.env.example`
- **Validation Commands**:
  - `python -m pip check`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `45`, Failed: `0`, Skipped: `0`
  - Summary: `pytest -q` pass; config tests 3/3 pass; app import pass; `pip check` pass; dependency/structure scan pass. Còn 2 warning FastAPI startup deprecation thuộc slice bootstrap sau.
- **Decisions and Assumptions**: `DEC-001`
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-002` database engine and session factory configuration.

### Slice SLICE-002: Database Engine & Session Factory Configuration
- **Requirement Sources**: `ADR-001`, `TBL-001`..`TBL-005`
- **Dependencies**: `SLICE-001`
- **Status**: completed
- **Acceptance Criteria**:
  - Cấu hình SQLAlchemy 2.0 Engine và `sessionmaker` trong `app/db/database.py`.
  - Hỗ trợ context manager session an toàn cho các tác vụ độc lập.
- **Expected Files**:
  - `backend/app/db/database.py`
- **Actual Changed Files**:
  - `backend/app/db/database.py`
  - `backend/tests/db/__init__.py`
  - `backend/tests/db/test_connection.py`
- **Validation Commands**:
  - `pytest tests/db/test_connection.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `49`, Failed: `0`, Skipped: `0`
  - Summary: Focused DB lifecycle tests 4/4 pass; full regression 49/49 pass; app/session import check pass. Focused tests dùng SQLite in-memory, không kết nối PostgreSQL demo.
- **Decisions and Assumptions**: None
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-003` physical ORM entities after user review.

### Slice SLICE-003: Physical ORM Entities Implementation (5 Target Tables)
- **Requirement Sources**: `TBL-001`, `TBL-002`, `TBL-003`, `TBL-004`, `TBL-005`, `ADR-003`
- **Dependencies**: `SLICE-002`
- **Status**: completed
- **Acceptance Criteria**:
  - Định nghĩa 5 declarative ORM models trong `app/models/entities.py`: `Candidate`, `DraftRevision`, `LogicalSendOperation`, `ProviderAttempt`, `AuditLog`.
  - Khai báo đầy đủ kiểu dữ liệu, default values, nullability, unique keys, check constraints, foreign keys với `ON DELETE RESTRICT`.
- **Expected Files**:
  - `backend/app/models/entities.py`
- **Actual Changed Files**:
  - `backend/app/models/entities.py`
  - `backend/app/models/__init__.py`
  - `backend/app/services/audit.py`
  - `backend/app/db/seed.py`
  - `backend/tests/models/__init__.py`
  - `backend/tests/models/test_entities_schema.py`
  - Legacy test fixtures updated only with explicit test `application_id` values.
- **Validation Commands**:
  - `pytest tests/models/test_entities_schema.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `58`, Failed: `0`, Skipped: `0`
  - Summary: Focused ORM schema tests 9/9 pass; full backend regression 58/58 pass; PostgreSQL DDL compilation and app/target-model import pass. Không kết nối PostgreSQL demo.
- **Decisions and Assumptions**: `DEC-002`
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-004` Alembic migration after user review.

### Slice SLICE-004: Alembic Migration Foundation & Initial Core Migration
- **Requirement Sources**: `TBL-001`..`TBL-005`, `RET-001`..`RET-003`, `DBCR-001`
- **Dependencies**: `SLICE-003`
- **Status**: completed
- **Acceptance Criteria**:
  - Khởi tạo môi trường Alembic trong `backend/alembic/` và file `alembic.ini`.
  - Tạo migration script `001_initial_core_schema.py` tạo chính xác 5 bảng, constraints và indexes.
  - Hỗ trợ nâng cấp (`upgrade head`) và hạ cấp (`downgrade base`) thành công trên clean database.
- **Expected Files**:
  - `backend/alembic.ini` (NEW)
  - `backend/alembic/env.py` (NEW)
  - `backend/alembic/versions/001_initial_core_schema.py` (NEW)
- **Actual Changed Files**:
  - `backend/alembic.ini`
  - `backend/alembic/env.py`
  - `backend/alembic/script.py.mako`
  - `backend/alembic/versions/__init__.py`
  - `backend/alembic/versions/001_initial_core_schema.py`
  - `backend/tests/db/test_migration_contract.py`
  - `backend/scripts/validate_migration_roundtrip.py`
- **Validation Commands**:
  - `python -m alembic -c alembic.ini upgrade head --sql`
  - `python -m pytest -q tests/db/test_migration_contract.py tests/models/test_entities_schema.py`
  - `python scripts/validate_migration_roundtrip.py`
  - `python -m pytest -q`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `62`, Failed: `0`, Skipped: `0`
  - Summary: Offline PostgreSQL SQL generation passed; migration contract/schema tests 13/13 passed; isolated PostgreSQL `upgrade -> downgrade -> upgrade` passed with exactly 5 target tables; full backend regression 62/62 passed.
- **Decisions and Assumptions**: Clean-schema baseline only. The existing demo database and legacy data were not migrated because verified `application_id` backfill values are unavailable.
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-005` candidate import and application identity validation after user review.

### Slice SLICE-005: Candidate Excel/CSV Import & Identity Validation
- **Requirement Sources**: `CAP-001`, `FR-001`, `FR-012`, `VAL-001`, `VAL-002`, `BR-001`
- **Dependencies**: `SLICE-004`
- **Status**: completed
- **Acceptance Criteria**:
  - Cập nhật `app/services/excelImport.py` bắt buộc 5 trường: `application_id`, `stage`, `candidate name` (hoặc `name`), `email`, `status`.
  - Cho phép rỗng các trường optional: `position`, `phone`, `interview_time`, `interviewer`, `note`.
  - Từ chối import và báo lỗi chi tiết nếu thiếu `application_id` hoặc phát hiện trùng lặp `application_id`.
- **Expected Files**:
  - `backend/app/services/excelImport.py`
- **Actual Changed Files**:
  - `backend/app/services/excelImport.py`
  - `backend/tests/services/__init__.py`
  - `backend/tests/services/test_excel_import.py`
  - `docs/backend/plan.md`
- **Validation Commands**:
  - `python -m pytest -q tests/services/test_excel_import.py`
  - `python -m compileall -q app`
  - `python -m pytest -q`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `73`, Failed: `0`, Skipped: `0`
  - Summary: Focused Excel import tests 11/11 passed; Python compilation passed; full backend regression 73/73 passed. All tests used disposable SQLite and in-memory Excel files; the demo database was not accessed.
- **Decisions and Assumptions**: Candidate name header aliases `Candidate Name`, `Name`, and legacy `Full Name` map to `full_name`. Duplicate identity is based only on trimmed `application_id`; email may repeat across distinct applications. Import remains `.xlsx` per approved BA workflow.
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-006` fixed template catalog and content protection after user review.

### Slice SLICE-006: Fixed Template Catalog & Content Protection Service
- **Requirement Sources**: `CAP-002`, `CAP-003`, `FR-002`, `FR-010`, `DEC-005`, `BR-003`
- **Dependencies**: `SLICE-001`
- **Status**: completed
- **Acceptance Criteria**:
  - Định nghĩa đủ Fixed Template Catalog in-code trong `app/constants/templates.py` (`INTERVIEW_INVITATION`, `REJECTION_AFTER_CV`, `OFFER_EMAIL`, `REJECTION_AFTER_INTERVIEW`, `DECISION_CORRECTION`).
  - Xây dựng `app/services/template_service.py` render nội dung với vùng `decision_critical_content` bất biến và vùng `editable_content` cho phép HR tùy chỉnh.
- **Expected Files**:
  - `backend/app/constants/templates.py` (NEW)
  - `backend/app/services/template_service.py` (NEW)
- **Actual Changed Files**:
  - `backend/app/constants/templates.py`
  - `backend/app/services/template_service.py`
  - `backend/tests/services/test_template_service.py`
  - `docs/backend/plan.md`
- **Validation Commands**:
  - `python -m pytest -q tests/services/test_template_service.py`
  - `python -m compileall -q app`
  - `python -m pytest -q`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `88`, Failed: `0`, Skipped: `0`
  - Summary: Fixed catalog/content-protection tests 15/15 passed; Python compilation passed; full backend regression 88/88 passed. Tests cover exact catalog membership, policy selection, fail-closed errors, correction policy, editable content, protected marker integrity and immutable locked fields.
- **Decisions and Assumptions**: `DEC-003`. Editable content retains one internal `{{decision_critical_content}}` insertion marker; the backend replaces it with catalog-rendered read-only content. Exact English copy remains an internal reversible detail because upstream defines meaning and template types, not final wording.
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-007` deterministic safety guard engine after user review.

### Slice SLICE-007: Deterministic Safety Guard Engine
- **Requirement Sources**: `CAP-004`, `FR-003`, `FR-010`, `NFR-001`, `BR-008`, `BR-010`, `VAL-002`..`VAL-004`
- **Dependencies**: `SLICE-006`
- **Status**: completed
- **Acceptance Criteria**:
  - Xây dựng `app/services/safety_guard.py` thực thi kiểm tra deterministic độc lập: Email format, nullability, template type khớp status, required fields.
  - Trả về danh sách chi tiết các vi phạm (`issues`) nếu không hợp lệ.
- **Expected Files**:
  - `backend/app/services/safety_guard.py` (NEW)
- **Actual Changed Files**:
  - `backend/app/services/safety_guard.py`
  - `backend/tests/services/test_safety_guard.py`
  - `docs/backend/plan.md`
- **Validation Commands**:
  - `python -m pytest -q tests/services/test_safety_guard.py`
  - `python -m compileall -q app`
  - `python -m pytest -q`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `108`, Failed: `0`, Skipped: `0`
  - Summary: Focused deterministic safety tests 20/20 passed; Python compilation passed; full backend regression 108/108 passed. Validation includes null/missing values, email syntax, locked-field drift, policy mismatch, protected content, body assembly, candidate name, unresolved placeholders, subject contradiction and PII-safe evidence.
- **Decisions and Assumptions**: Pure snapshot validation only. Contradiction history belongs to SLICE-008 and revision superseding belongs to SLICE-009. Traceability was corrected from BR-005..BR-007 to the applicable BR-008/BR-010 rules.
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-008` Application ID + Stage contradiction guard after user review.

### Slice SLICE-008: Contradiction Guard (Application ID + Stage Key)
- **Requirement Sources**: `CAP-002`, `FR-002`, `BR-003`, `BR-004`, `BR-005`, `BR-006`, `AC-002`, `AC-013`, `AC-021`
- **Dependencies**: `SLICE-007`
- **Status**: completed
- **Acceptance Criteria**:
  - Triển khai kiểm tra Contradiction Guard theo cặp khóa `Application ID` + `Stage`.
  - Ngăn chặn tạo draft hoặc gửi email nếu phát hiện xung đột giữa trạng thái hiện tại và lịch sử truyền thông trong cùng Stage.
- **Expected Files**:
  - `backend/app/services/safety_guard.py`
- **Actual Changed Files**:
  - `backend/app/services/safety_guard.py`
  - `backend/tests/services/test_contradiction_guard.py`
  - `docs/backend/plan.md`
- **Validation Commands**:
  - `pytest tests/services/test_contradiction_guard.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `123`, Failed: `0`, Skipped: `0`
  - Summary: Focused contradiction tests 15/15 passed; Python compilation passed; full backend regression 123/123 passed.
- **Decisions and Assumptions**: Normal flow blocks only an opposing decision for the same Application ID + Stage. Same-decision checks and valid cross-stage progression pass; correction is the only explicit bypass. Candidate communicated fields remain the approved MVP source of the current communicated outcome.
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-009` draft revision lifecycle after user review.

### Slice SLICE-009: Draft Revision Lifecycle & Superseding Engine
- **Requirement Sources**: `CAP-004`, `FR-004`, `FR-011`, `BR-007`, `BR-009`, `AC-004`, `AC-011`, `ENT-002`
- **Dependencies**: `SLICE-007`, `SLICE-008`
- **Status**: completed
- **Acceptance Criteria**:
  - Xây dựng `app/services/draft_service.py` quản lý vòng đời `DraftRevision`.
  - Tự động tăng `revision_number` và đánh dấu bản nháp cũ là `SUPERSEDED` khi tạo bản nháp mới cho cùng candidate.
- **Expected Files**:
  - `backend/app/services/draft_service.py` (NEW)
- **Actual Changed Files**:
  - `backend/app/services/draft_service.py`
  - `backend/tests/services/test_draft_lifecycle.py`
  - `docs/backend/plan.md`
- **Validation Commands**:
  - `pytest tests/services/test_draft_lifecycle.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `140`, Failed: `0`, Skipped: `0`
  - Summary: Focused draft lifecycle tests 17/17 passed; Python compilation passed; full backend regression 140/140 passed.
- **Decisions and Assumptions**: Revision numbers are candidate-wide per the approved unique constraint, while superseding is scoped to candidate + stage. Only unsent normal statuses are superseded; frozen, finalized, discarded and correction drafts remain immutable in this workflow. Audit event persistence remains assigned to SLICE-016.
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-010` Decision Correction workflow after user review.

### Slice SLICE-010: Decision Correction Workflow & Prior Operation Linkage
- **Requirement Sources**: `CAP-008`, `FR-008`, `DEC-003`, `BR-011`, `AC-008`, `AC-018`, `ADR-004`, `REL-002`, `CON-009`
- **Dependencies**: `SLICE-009`
- **Status**: completed
- **Acceptance Criteria**:
  - Triển khai workflow Decision Correction: Yêu cầu bắt buộc nhập `correction_rationale` và liên kết `prior_operation_id`.
  - Thiết lập trạng thái draft là `CORRECTION_DRAFT`.
- **Expected Files**:
  - `backend/app/services/draft_service.py`
- **Actual Changed Files**:
  - `backend/app/services/draft_service.py`
  - `backend/tests/services/test_decision_correction.py`
  - `docs/backend/plan.md`
- **Validation Commands**:
  - `pytest tests/services/test_decision_correction.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `160`, Failed: `0`, Skipped: `0`
  - Summary: Focused Decision Correction tests 20/20 passed; Python compilation passed; full backend regression 160/160 passed.
- **Decisions and Assumptions**: Correction initiation updates the internal candidate decision while preserving communicated decision/stage/time until provider acceptance. The latest matching provider-accepted operation is linked for side-by-side comparison. Explicit human confirmation is enforced later at the send/API boundary; audit persistence remains SLICE-016.
- **Blocker**: None
- **Exact Next Action**: Proceed to `SLICE-011` Logical Send Operation and concurrency guard after user review.

### Slice SLICE-011: Logical Send Operation & Concurrency Guard
- **Requirement Sources**: `CAP-007`, `FR-005`, `NFR-003`, `BR-013`, `ADR-003`, `DEC-004`
- **Dependencies**: `SLICE-009`
- **Status**: completed
- **Acceptance Criteria**:
  - Khởi tạo bản ghi `LogicalSendOperation` ràng buộc 1:1 với `draft_revisions.id`.
  - Sử dụng database unique constraint và row-level lock để ngăn chặn double-click gửi trùng.
- **Expected Files**:
  - `backend/app/services/send_orchestrator.py` (NEW)
- **Actual Changed Files**:
  - `backend/app/services/send_orchestrator.py`
  - `backend/tests/services/test_logical_send_concurrency.py`
- **Validation Commands**:
  - `pytest tests/services/test_logical_send_concurrency.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `10`, Failed: `0`, Skipped: `0`
  - Summary: Focused SLICE-011 tests passed; related draft/correction regression passed 47/47; backend regression excluding the separately tracked migration-contract environment issue passed 166/166.
- **Decisions and Assumptions**: `DEC-004`; PostgreSQL row lock serializes competing prepare requests and the approved unique constraint remains the final 1:1 invariant. Provider attempts remain owned by SLICE-013.
- **Blocker**: None
- **Exact Next Action**: Completed; proceed to SLICE-012 Resend adapter.

### Slice SLICE-012: Resend Synchronous REST Adapter & Payload Digest
- **Requirement Sources**: `CAP-006`, `FR-006`, `NFR-004`, `ADR-002`, `SPIKE-001`
- **Dependencies**: `SLICE-001`
- **Status**: completed
- **Acceptance Criteria**:
  - Xây dựng `app/adapters/resend_adapter.py` gửi synchronous HTTP POST tới Resend API (`https://api.resend.com/emails`).
  - Gửi header `Idempotency-Key: <operation_id>` và tính toán SHA-256 digest của payload gửi đi.
  - Cấu hình timeout an toàn (connect 5s, read 10s).
- **Expected Files**:
  - `backend/app/adapters/resend_adapter.py` (NEW)
- **Actual Changed Files**:
  - `backend/app/adapters/resend_adapter.py`
  - `backend/app/core/config.py`
  - `backend/.env.example`
  - `backend/tests/adapters/__init__.py`
  - `backend/tests/adapters/test_resend_adapter_mock.py`
  - `backend/tests/test_config.py`
- **Validation Commands**:
  - `pytest tests/adapters/test_resend_adapter_mock.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `12`, Failed: `0`, Skipped: `0`
  - Summary: MockTransport adapter/config tests passed 12/12; backend regression excluding the separately tracked migration-contract environment issue passed 175/175.
- **Decisions and Assumptions**: Direct `httpx` REST adapter follows ADR-002, sends a UUID idempotency key, canonical payload digest, mandatory User-Agent, bounded timeouts, and sanitized provider errors. Automated tests never call Resend.
- **Blocker**: None
- **Exact Next Action**: Completed; proceed to SLICE-013 three-phase orchestration.

### Slice SLICE-013: Decoupled 3-Phase Send Transaction Execution (Phase A / B / C)
- **Requirement Sources**: `CAP-007`, `FR-005`, `FR-006`, `ADR-005`, `BR-013`
- **Dependencies**: `SLICE-011`, `SLICE-012`
- **Status**: completed
- **Acceptance Criteria**:
  - Hiện thực quy trình gửi 3 pha trong `app/services/send_orchestrator.py`:
    - **Pha A**: Mở DB Tx 1 -> Tạo Send Operation / Provider Attempt -> Commit & đóng DB connection.
    - **Pha B**: Gọi Resend REST API (hoàn toàn ngoài DB transaction).
    - **Pha C**: Mở DB Tx 2 -> Cập nhật trạng thái kết quả, cập nhật `communicated_decision` nếu `PROVIDER_ACCEPTED` -> Commit DB.
- **Expected Files**:
  - `backend/app/services/send_orchestrator.py`
- **Actual Changed Files**:
  - `backend/app/services/send_orchestrator.py`
  - `backend/tests/services/test_three_phase_send_pipeline.py`
- **Validation Commands**:
  - `pytest tests/services/test_three_phase_send_pipeline.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `7`, Failed: `0`, Skipped: `0`
  - Summary: Three-phase pipeline tests passed; combined send-focused tests passed 26/26; backend regression passed 182/182 excluding the separately tracked migration-contract environment issue.
- **Decisions and Assumptions**: Provider HTTP executes only after Phase A session is committed and closed. Phase C updates communicated outcome only for `PROVIDER_ACCEPTED`. Immutable audit events remain owned by SLICE-016.
- **Blocker**: None
- **Exact Next Action**: Completed; proceed to SLICE-014.

### Slice SLICE-014: Definitive Failure & Transient Retry Classification
- **Requirement Sources**: `CAP-007`, `FR-006`, `FR-007`, `NFR-004`, `ADR-002`, `BR-014`
- **Dependencies**: `SLICE-013`
- **Status**: completed
- **Acceptance Criteria**:
  - Phân loại response từ Resend: HTTP 4xx -> `DEFINITIVE_FAILURE` (không retry); HTTP 5xx / Network Timeout -> `TRANSIENT_RETRYABLE` hoặc `DELIVERY_UNKNOWN`.
  - Tạo bản ghi `ProviderAttempt` mới khi thực hiện retry dưới cùng một `LogicalSendOperation`.
- **Expected Files**:
  - `backend/app/services/send_orchestrator.py`
- **Actual Changed Files**:
  - `backend/app/services/send_orchestrator.py`
  - `backend/tests/services/test_failure_classification.py`
- **Validation Commands**:
  - `pytest tests/services/test_failure_classification.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `5`, Failed: `0`, Skipped: `0`
  - Summary: Failure classification and retry sequence tests passed; combined SLICE-013/014 tests passed 12/12.
- **Decisions and Assumptions**: Only `TRANSIENT_RETRYABLE` and `QUOTA_EXCEEDED` definitive failures can create a new attempt. Validation-terminal and delivery-unknown states require different workflows.
- **Blocker**: None
- **Exact Next Action**: Completed; proceed to SLICE-015 reconciliation.

### Slice SLICE-015: `DELIVERY_UNKNOWN` Reconciliation & Manual Resolution Workflow
- **Requirement Sources**: `CAP-008`, `FR-007`, `ADR-004`, `BR-015`, `AC-015`, `AC-016`
- **Dependencies**: `SLICE-014`
- **Status**: completed
- **Acceptance Criteria**:
  - Khi Phase B bị socket timeout sau khi request đã gửi, đánh dấu `DELIVERY_UNKNOWN`.
  - Khóa không cho phép tự động retry gửi mới; cung cấp endpoint đối soát thủ công yêu cầu nhập `resolution_rationale` và `resolved_by`.
- **Expected Files**:
  - `backend/app/services/send_orchestrator.py`
- **Actual Changed Files**:
  - `backend/app/services/send_orchestrator.py`
  - `backend/tests/services/test_delivery_unknown_reconciliation.py`
- **Validation Commands**:
  - `pytest tests/services/test_delivery_unknown_reconciliation.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `7`, Failed: `0`, Skipped: `0`
  - Summary: Provider replay and governed manual resolution tests passed; combined reconciliation/failure tests passed 12/12.
- **Decisions and Assumptions**: Exact-payload replay is allowed only inside Resend's 24-hour idempotency window. After that window, HR must verify provider state and explicitly acknowledge a manual resolution. `PROVIDER_NOT_RECEIVED` unlocks the controlled retry path on the same logical operation.
- **Blocker**: None
- **Exact Next Action**: Completed; proceed to SLICE-016 audit trail.

### Slice SLICE-016: Immutable Append-Only Audit Trail Service
- **Requirement Sources**: `CAP-009`, `FR-009`, `NFR-002`, `BR-012`, `ADR-005`
- **Dependencies**: `SLICE-003`
- **Status**: completed
- **Acceptance Criteria**:
  - Xây dựng `app/services/audit_service.py` ghi nhận các sự kiện bất biến (`CANDIDATE_IMPORTED`, `DRAFT_GENERATED`, `SEND_PREPARED`, `SEND_OUTCOME_FINALIZED`, `DECISION_CORRECTED`, `DELIVERY_UNKNOWN_RESOLVED`).
  - Đảm bảo audit log được ghi nhận nguyên tử (atomic) cùng transaction của state transition.
- **Expected Files**:
  - `backend/app/services/audit_service.py` (NEW)
- **Actual Changed Files**:
  - `backend/app/services/audit_service.py`
  - `backend/app/services/draft_service.py`
  - `backend/app/services/excelImport.py`
  - `backend/app/services/send_orchestrator.py`
  - `backend/tests/services/test_audit_trail.py`
- **Validation Commands**:
  - `pytest tests/services/test_audit_trail.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `4`, Failed: `0`, Skipped: `0`
  - Summary: Structured append-only events, PII key rejection, transaction rollback, and Phase C atomic rollback tests passed; combined send/audit regression passed 18/18.
- **Decisions and Assumptions**: Audit writes use the caller-owned transaction and never commit independently. Structured payloads omit candidate email, name, message subject, and body. Existing database migration privileges remain the enforcement boundary against UPDATE/DELETE.
- **Blocker**: None
- **Exact Next Action**: Completed; define the missing canonical API contract before SLICE-017 implementation.

### Slice SLICE-017: API Routers, Pydantic v2 Schemas & Standard Error Model
- **Requirement Sources**: `CAP-001`..`CAP-009`, `FR-001`..`FR-011`, `NFR-004`
- **Dependencies**: `SLICE-005`, `SLICE-010`, `SLICE-013`, `SLICE-015`, `SLICE-016`
- **Status**: completed
- **Acceptance Criteria**:
  - Xây dựng các router chuẩn trong `app/api/`: `candidates.py`, `drafts.py`, `send_operations.py`, `audit.py`.
  - Khai báo Pydantic schemas trong `app/schemas/api.py` với type annotations đầy đủ.
  - Chuẩn hóa mô hình lỗi JSON (`error_code`, `message`, `details`, `timestamp`).
- **Expected Files**:
  - `backend/app/schemas/api.py`
  - `backend/app/api/candidateRoutes.py`
  - `backend/app/api/draftRoutes.py` (NEW)
  - `backend/app/api/sendRoutes.py` (NEW)
  - `backend/app/api/auditRoutes.py`
  - `backend/app/main.py`
- **Actual Changed Files**:
  - `docs/api-contract.md`
  - `backend/app/schemas/api.py`
  - `backend/app/api/v1/candidates.py`
  - `backend/app/api/v1/drafts.py`
  - `backend/app/api/v1/send_operations.py`
  - `backend/app/api/v1/audit.py`
  - `backend/app/api/v1/dependencies.py`
  - `backend/app/api/v1/errors.py`
  - `backend/app/api/v1/router.py`
  - `backend/app/main.py`
  - `backend/tests/api/test_v1_api_routes.py`
- **Validation Commands**:
  - `pytest tests/api/test_api_routes.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `2`, Failed: `0`, Skipped: `0`
  - Summary: API integration tests passed for import, draft generation, explicit send confirmation, provider acceptance, repeated-call idempotency, audit visibility, pagination validation, and standard errors.
- **Decisions and Assumptions**: `/api/v1` is the canonical REST boundary. Authentication and rate limiting remain outside MVP, so deployment is restricted to trusted local/internal evaluation. The temporary actor field is replaced by authenticated identity later.
- **Blocker**: None
- **Exact Next Action**: Completed; proceed to SLICE-018 OpenAPI export.

### Slice SLICE-018: OpenAPI Contract Generation & Schema Synchronization
- **Requirement Sources**: `FR-011`, `NFR-004`, `frontend-handoff-contract.md`
- **Dependencies**: `SLICE-017`
- **Status**: completed
- **Acceptance Criteria**:
  - Tạo script xuất OpenAPI static JSON spec từ FastAPI application: `docs/backend/openapi.json`.
  - Xác thực không có schema drift giữa runtime API và tài liệu.
- **Expected Files**:
  - `backend/scripts/export_openapi.py` (NEW)
  - `docs/backend/openapi.json` (NEW)
- **Actual Changed Files**:
  - `backend/scripts/export_openapi.py`
  - `backend/tests/api/test_openapi_contract.py`
  - `docs/backend/openapi.json`
- **Validation Commands**:
  - `python backend/scripts/export_openapi.py`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `2`, Failed: `0`, Skipped: `0`
  - Summary: Static OpenAPI export completed; `python scripts/export_openapi.py --check` passed and route/schema contract tests passed.
- **Decisions and Assumptions**: Runtime FastAPI OpenAPI is canonical; the committed static artifact is generated and checked for exact drift.
- **Blocker**: None
- **Exact Next Action**: Completed; proceed to SLICE-019 legacy runtime decommissioning.

### Slice SLICE-019: Legacy Infrastructure Decommissioning
- **Requirement Sources**: `ADR-006`, `ADR-007`
- **Dependencies**: `SLICE-017`
- **Status**: completed
- **Acceptance Criteria**:
  - Xóa bỏ hoặc ngừng kích hoạt các file cũ không thuộc MVP: `celery_app.py`, `outbox_dispatcher.py`, `gemini_provider.py`, `agent_worker.py`, `agent_review.py`, `email_workflow.py`.
  - Cập nhật `docker-compose.yml` chỉ giữ service PostgreSQL 16.
- **Expected Files**:
  - `docker-compose.yml`
- **Actual Changed Files**:
  - `backend/app/main.py`
  - `docker-compose.yml`
  - `backend/tests/test_agent_api.py` (REMOVED: decommissioned endpoint contract)
  - `backend/tests/test_review_progress_api.py` (REMOVED: decommissioned Redis polling contract)
  - `backend/tests/test_async_review_pipeline.py` (REMOVED: decommissioned Celery contract)
  - `backend/tests/test_queue_state_machine.py` (REMOVED: decommissioned legacy queue contract)
  - `backend/tests/test_recruitment_email_agent.py` (REMOVED: decommissioned Gemini agent contract)
- **Validation Commands**:
  - `pytest tests/`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `164`, Failed: `0`, Skipped: `0`
  - Summary: Clean virtualenv regression passed; runtime exposes only health and canonical `/api/v1` routes. Docker Compose contains PostgreSQL only.
- **Decisions and Assumptions**: Dormant compatibility source may remain temporarily, but it is not imported or mounted by the runtime and is not extended.
- **Blocker**: None
- **Exact Next Action**: Completed; proceed to SLICE-020 handoff.

### Slice SLICE-020: Comprehensive Automated Test Suite & Backend Handoff Document
- **Requirement Sources**: `NFR-001`..`NFR-004`, `backend-template.md`
- **Dependencies**: `SLICE-001`..`SLICE-019`
- **Status**: completed
- **Acceptance Criteria**:
  - Toàn bộ test suite chạy pass 100%: Unit tests cho safety guard và rules, DB integration tests cho 5 tables, Mock tests cho Resend adapter, Concurrency tests.
  - Soạn thảo tài liệu bàn giao `docs/backend/backend.md` đầy đủ thông tin cho Frontend và QA.
- **Expected Files**:
  - `backend/tests/test_end_to_end_journey.py` (NEW)
  - `docs/backend/backend.md` (NEW)
- **Actual Changed Files**:
  - `backend/tests/adapters/test_resend_adapter.py`
  - `backend/tests/api/`
  - `backend/tests/services/test_audit_trail.py`
  - `backend/tests/services/test_delivery_unknown_reconciliation.py`
  - `backend/tests/services/test_failure_classification.py`
  - `backend/tests/services/test_logical_send_concurrency.py`
  - `backend/tests/services/test_three_phase_send_pipeline.py`
  - `docs/backend/backend.md`
- **Validation Commands**:
  - `pytest backend/tests -v`
  - `python C:\Users\quang\.gemini\skills\team1-backend\scripts\validate_delivery_state.py --project-root . --final`
- **Latest Output / Exit Code / Failure Count**:
  - Exit Code: `0`
  - Passed: `164`, Failed: `0`, Skipped: `0`
  - Summary: Full clean-environment suite passed in 4.64 seconds; OpenAPI drift check passed.
- **Decisions and Assumptions**: Provider tests use deterministic fake transports; automated tests never send real email.
- **Blocker**: None
- **Exact Next Action**: Completed; backend handoff is ready. Live provider smoke remains an environment-controlled release check.

## Decisions
- `DEC-001`: Triển khai kiến trúc Modular Monolith trên FastAPI, loại bỏ hoàn toàn RabbitMQ, Celery, Redis, và Transactional Outbox khỏi runtime core MVP (theo `ADR-001`, `ADR-006`).
- `DEC-002`: Thiết kế cơ sở dữ liệu PostgreSQL 16 với đúng 5 bảng mục tiêu (`candidates`, `draft_revisions`, `logical_send_operations`, `provider_attempts`, `audit_logs`) theo Database Specification v1.0.0-DB.
- `DEC-003`: Sử dụng Fixed Template Catalog in-code gồm `INTERVIEW_INVITATION`, `REJECTION_AFTER_CV`, `OFFER_EMAIL`, `REJECTION_AFTER_INTERVIEW`, `DECISION_CORRECTION`, với vùng nội dung kết quả bất biến (`decision_critical_content`), loại bỏ bảng `email_templates` khỏi target schema.
- `DEC-004`: Áp dụng mô hình Logical Send Operation (ràng buộc 1:1 với Draft Revision) kết hợp Header `Idempotency-Key` khi gọi Resend REST API để kiểm soát duplicate send ở ranh giới ứng dụng. Duplicate delivery trong hạ tầng provider vẫn là residual risk theo `RSK-002`.
- `DEC-005`: Tách rời giao tác cơ sở dữ liệu theo mô hình 3 pha (Phase A prepare -> Phase B external HTTP ngoài DB -> Phase C finalize + audit log atomic commit) theo `ADR-005`.
- `DEC-006`: Phân loại AI Semantic Review / Gemini / LLM Advisory vào phạm vi LATER, không triển khai trong MVP hiện tại.

## Assumptions
- `ASM-001`: Môi trường kiểm thử cục bộ có PostgreSQL 16 khả dụng qua Docker Compose trên cổng 5432 (`localhost:5432`).
- `ASM-002`: Các bài kiểm thử tự động sử dụng Mock Transport / Fake Provider, không yêu cầu kết nối mạng Internet ra Resend thật.

## Blockers
- None. `BLK-ENV-001` đã được giải quyết ngày 2026-08-15; secret chỉ được xác minh presence/non-empty và không được in ra.

## Verification Evidence
Chưa có bằng chứng kiểm thử mới trong giai đoạn lập kế hoạch (PLAN_ONLY). Toàn bộ 20 Vertical Slices đang ở trạng thái pending chờ Coding Agent thực thi.

## Validation Strategy
Kế hoạch kiểm thử tự động toàn diện được thiết lập cho Coding Agent:
1. **Kiểm tra Mã nguồn & Định dạng**:
   - Linter / Code Style: `flake8 backend/app`
   - Type Checking: `mypy backend/app`
2. **Kiểm thử Đơn vị (Unit Tests)**:
   - `pytest backend/tests/services/test_safety_guard.py`: Kiểm thử các quy tắc deterministic và contradiction guard.
   - `pytest backend/tests/services/test_template_service.py`: Kiểm thử render template và bảo vệ nội dung bất biến.
3. **Kiểm thử Tích hợp Cơ sở Dữ liệu (DB Integration Tests)**:
   - `pytest backend/tests/models/test_entities_schema.py`: Kiểm thử 5 bảng, unique constraints, FK onDelete restrict.
   - `alembic upgrade head && alembic downgrade base`: Kiểm thử tính toàn vẹn 2 chiều của migration script.
4. **Kiểm thử Ranh giới & Concurrency (Boundary & Concurrency Tests)**:
   - `pytest backend/tests/services/test_logical_send_concurrency.py`: Giả lập 2 request song song cùng gửi 1 draft revision.
   - `pytest backend/tests/services/test_three_phase_send_pipeline.py`: Xác nhận DB connection đã được giải phóng trong Phase B.
5. **Kiểm thử External Adapter (Mock Contract Tests)**:
   - `pytest backend/tests/adapters/test_resend_adapter_mock.py`: Giả lập các phản hồi 200, 4xx (Definitive Failure), 5xx/Timeout (`DELIVERY_UNKNOWN`).
6. **Kiểm thử Toàn trình API (End-to-End API Tests)**:
   - `pytest backend/tests/api/test_api_routes.py`: Kiểm thử luồng import -> create draft -> deterministic check -> send email -> audit log.
7. **Kiểm tra Bảo mật & Rò rỉ Thông tin**:
   - Quét secret trong codebase và logs để đảm bảo không ghi `RESEND_API_KEY` hay PII ứng viên.
8. **Kiểm định Trạng thái Bàn giao Bền vững (Delivery-State Validator)**:
   - `python C:\Users\quang\.gemini\skills\team1-backend\scripts\validate_delivery_state.py --project-root .`

## Remaining Work
Toàn bộ 20 Vertical Slices giữ trạng thái `pending`; implementation chưa bắt đầu vì `BLK-ENV-001`.

## Exact Next Action
Người dùng thêm `RESEND_API_KEY=<secret>` vào `backend/.env` (không gửi secret trong chat). Sau khi xác minh biến đã được đặt mà không in giá trị, Coding Agent chuyển `BE-001` sang `in_progress` và bắt đầu **`SLICE-001` (Backend Foundation & Dependency Cleanup)**.

## Delivery identity

- Goal: Triển khai backend Minimal Real-Email MVP theo 20 vertical slices phía trên.
- Backend root: `backend`
- Current phase: implementation
- Next task: SLICE-011
- Last updated: 2026-08-16 by Codex

## Approved stack and constraints

- Runtime/framework: Python 3.11+, FastAPI, SQLAlchemy 2.0.
- Database engine: PostgreSQL 16.
- Provider: Resend REST API qua decoupled 3-phase execution.
- Existing conventions to preserve: routes mỏng, service tách trách nhiệm, schema Pydantic tường minh, không log secret/PII.

## Decisions and assumptions

| ID | Type | Decision or assumption | Source/rationale | Impact | Status |
|---|---|---|---|---|---|
| BE-DEC-001 | decision | Dùng 5 bảng target và fixed catalog gồm 5 template | Approved BA, System Design, Database | SLICE-003, SLICE-006 | accepted |
| BE-DEC-002 | decision | Không cam kết chống duplicate vật lý tuyệt đối ở provider | Product RSK-002, ADR-002 | SLICE-011..015 | accepted |

## Tasks

### BE-001 — Environment hard gate

- Requirement sources: CAP-006, FR-006, ADR-002
- Dependencies: none
- Status: completed
- Acceptance criteria:
  - `DATABASE_URL` và `RESEND_API_KEY` khả dụng mà không ghi/echo secret.
  - `EMAIL_SENDER_ADDRESS` dùng giá trị đã xác minh hoặc safe Resend sandbox default.
- Files expected/changed:
  - `docs/backend/plan.md`
  - `backend/.env.example`
- Validation:
  - Command/procedure: kiểm tra presence/non-empty của biến, không in giá trị.
  - Pass criteria: tất cả biến required có trạng thái SET hoặc có approved safe default.
- Latest validation result:
  - Run context: local workspace, 2026-08-15
  - Exit/result: pass
  - Summary: `DATABASE_URL`, `RESEND_API_KEY`, `EMAIL_SENDER_ADDRESS` đều SET; không in giá trị.
- Decisions/assumptions:
  - Automated tests dùng MockTransport nhưng final provider capability vẫn cần credential thật.
- Blocker:
  - None
- Next action:
  - Completed; tiếp tục BE-002 / SLICE-001.

### BE-002 — Backend foundation and dependency cleanup

- Requirement sources: NFR-001, ADR-001, ADR-006
- Dependencies: BE-001
- Status: completed
- Acceptance criteria:
  - Core runtime requirements không còn Celery, Redis hoặc Gemini SDK.
  - Cấu hình Modular Monolith khai báo các biến runtime/provider an toàn và không làm lộ secret.
  - Cấu trúc `app/adapters`, `app/constants`, `app/core`, `app/db`, `app/models`, `app/schemas`, `app/services`, `app/api` tồn tại.
- Files expected/changed:
  - `backend/requirements.txt`
  - `backend/app/core/config.py`
  - `backend/app/adapters/__init__.py`
  - `backend/tests/test_config.py`
- Validation:
  - Command/procedure: config tests, import/start check, dependency declaration scan, `pip check`.
  - Pass criteria: mọi command exit 0; không còn dependency legacy trong requirements.
- Latest validation result:
  - Run context: backend virtual environment after final SLICE-001 changes, 2026-08-15
  - Exit/result: 0
  - Summary: `pytest -q` passed 45 tests; config tests passed 3/3; app import and `pip check` passed; dependency/structure scan passed.
- Decisions/assumptions:
  - Legacy modules còn tồn tại tạm thời nhưng sẽ bị ngắt khỏi runtime và loại bỏ theo SLICE-019; không mở rộng chúng.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-002 after user review.

### BE-003 — Database engine and session lifecycle

- Requirement sources: ADR-001, TBL-001..TBL-005, TXN-001..TXN-003
- Dependencies: BE-002
- Status: completed
- Acceptance criteria:
  - SQLAlchemy 2.0 engine and typed session factory preserve PostgreSQL configuration and SQLite test compatibility.
  - Request-scoped sessions always close and roll back uncommitted work on errors.
  - Independent unit-of-work context manager commits success, rolls back failure and always closes its session.
- Files expected/changed:
  - `backend/app/db/database.py`
  - `backend/tests/db/test_connection.py`
- Validation:
  - Command/procedure: `pytest -q tests/db/test_connection.py`; full `pytest -q`; app import check.
  - Pass criteria: all commands exit 0 with no test failures and no connection to demo PostgreSQL during focused tests.
- Latest validation result:
  - Run context: backend virtual environment with disposable in-memory SQLite, 2026-08-15
  - Exit/result: 0
  - Summary: focused tests 4 passed; full suite 49 passed; app/session import check passed; 0 failures. No demo PostgreSQL access.
- Decisions/assumptions:
  - Focused database tests use disposable in-memory SQLite; no migration or demo PostgreSQL mutation belongs to this slice.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-003 after user review.

### BE-004 — Five approved ORM entities

- Requirement sources: TBL-001..TBL-005, REL-001..REL-004, CON-001..CON-017, IDX-001..IDX-006
- Dependencies: BE-003
- Status: completed
- Acceptance criteria:
  - Candidate, DraftRevision, LogicalSendOperation, ProviderAttempt and AuditLog map every approved target column with required types/nullability/defaults.
  - Approved unique, check and RESTRICT foreign-key constraints are represented in SQLAlchemy metadata.
  - Approved workload indexes are represented; target relationships expose the 1:N and strict 1:1 boundaries.
  - Legacy models remain compatibility-only until SLICE-019 and do not alter the five-table target contract.
- Files expected/changed:
  - `backend/app/models/entities.py`
  - `backend/app/models/__init__.py`
  - `backend/tests/models/test_entities_schema.py`
  - Legacy test fixtures only where mandatory `application_id` is now required.
- Validation:
  - Command/procedure: focused metadata/constraint tests on disposable SQLite; full `pytest -q`; app import check.
  - Pass criteria: all commands exit 0, zero failures, no demo PostgreSQL access.
- Latest validation result:
  - Run context: disposable SQLite metadata/constraint tests plus offline PostgreSQL DDL compilation, 2026-08-15
  - Exit/result: 0
  - Summary: focused schema tests 9 passed; full suite 58 passed; PostgreSQL DDL compile passed; app/target-model import passed; 0 failures.
- Decisions/assumptions:
  - JSONB uses a PostgreSQL dialect variant; UUID values use application-side `uuid4` in ORM so SQLite tests stay disposable, while `gen_random_uuid()` database defaults are enforced by the SLICE-004 PostgreSQL migration.
  - Legacy tables are retained in ORM metadata only for temporary compatibility and are excluded from the target migration contract.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-004 after user review.

### BE-005 — Alembic clean-schema migration

- Requirement sources: TBL-001..TBL-005, REL-001..REL-004, CON-001..CON-017, IDX-001..IDX-006, DBCR-001
- Dependencies: BE-004
- Status: completed
- Acceptance criteria:
  - Alembic environment reads `DATABASE_URL` without embedding credentials and filters autogeneration to the five target tables.
  - Initial migration creates exactly five target tables with approved PostgreSQL types, defaults, constraints and indexes on a clean database.
  - `upgrade head -> downgrade base -> upgrade head` succeeds on a dedicated local PostgreSQL test database.
  - Migration is not executed against the existing demo database; legacy tables/data remain untouched.
- Files expected/changed:
  - `backend/alembic.ini`
  - `backend/alembic/env.py`
  - `backend/alembic/script.py.mako`
  - `backend/alembic/versions/001_initial_core_schema.py`
  - `backend/tests/db/test_migration_contract.py`
  - `backend/scripts/validate_migration_roundtrip.py`
- Validation:
  - Command/procedure: offline migration contract tests; full backend suite; Alembic round-trip against dedicated local PostgreSQL test database.
  - Pass criteria: all commands exit 0; five target tables/constraints/indexes observed after upgrade; zero target tables after downgrade; demo database untouched.
- Latest validation result:
  - Run context: offline DDL generation, migration contract tests, disposable local PostgreSQL round-trip and full regression suite, 2026-08-15
  - Exit/result: 0
  - Summary: exactly five target tables created; downgrade left only Alembic bookkeeping; re-upgrade recreated all five tables; focused tests 13 passed and full backend suite 62 passed with 0 failures.
- Decisions/assumptions:
  - This revision is a clean-schema baseline. Existing demo rows cannot be safely converted because verified `application_id` values are not available; no synthetic backfill or automatic demo migration is permitted.
  - The dedicated local validation database was removed after the successful round-trip; it contained no user or demo data and is intentionally disposable.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-005 after user review.

### BE-006 — Candidate Excel import and identity validation

- Requirement sources: CAP-001, FR-001, FR-012, VAL-001..VAL-004, BR-001, AC-001, AC-012
- Dependencies: BE-005
- Status: completed
- Acceptance criteria:
  - Excel header contract requires Application ID, Stage, Candidate Name/Name, Email and Status while accepting approved optional columns.
  - Every row validates required values, normalized lowercase email syntax, supported stage/status values and parseable optional interview time.
  - Duplicate Application IDs in the database or within one file are rejected with `DUPLICATE_APPLICATION_ID`; repeated candidate email across different applications is allowed.
  - Preview never writes data; confirmed import persists only valid rows without modifying the demo database during automated verification.
- Files expected/changed:
  - `backend/app/services/excelImport.py`
  - `backend/tests/services/test_excel_import.py`
  - `docs/backend/plan.md`
- Validation:
  - Command/procedure: focused import tests on disposable SQLite; full backend regression suite; delivery-state validator.
  - Pass criteria: all commands exit 0; required header/value and duplicate identity negative paths pass; full suite has zero failures.
- Latest validation result:
  - Run context: disposable SQLite service tests, in-memory `.xlsx` files, Python compilation and full backend regression, 2026-08-15
  - Exit/result: 0
  - Summary: focused import tests 11 passed; full backend suite 73 passed; 0 failures. Header contract, required values, supported stage/status, email/date formats, field length, duplicate Application IDs, repeated email allowance, preview read-only behavior and valid-row persistence were verified.
- Decisions/assumptions:
  - Header aliases `candidate_name`, `name`, and legacy `full_name` all map to canonical `full_name`; all other required headers use their canonical normalized names.
  - Import remains `.xlsx` only because CSV support is not present in the approved BA workflow despite the legacy slice title.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-006 after user review.

### BE-007 — Fixed template catalog and protected content rendering

- Requirement sources: CAP-002, CAP-003, FR-002, FR-003, FR-010, DEC-005, AC-003
- Dependencies: BE-006
- Status: completed
- Acceptance criteria:
  - Immutable in-code catalog contains exactly the five approved template codes and no database-backed CRUD dependency.
  - Standard draft selection fails closed unless Stage, Decision and Email Type match the approved policy table; PENDING is rejected explicitly.
  - Rendering returns locked identity/outcome metadata, a fixed decision-critical block, editable surrounding content and a deterministic assembled body.
  - Editing cannot omit, duplicate or replace the decision-critical insertion point; submitted decision-critical content must exactly match the catalog-rendered value.
- Files expected/changed:
  - `backend/app/constants/templates.py`
  - `backend/app/services/template_service.py`
  - `backend/tests/services/test_template_service.py`
  - `docs/backend/plan.md`
- Validation:
  - Command/procedure: focused pure service tests; Python compilation; full backend regression; delivery-state validator.
  - Pass criteria: exact catalog/policy and negative content-protection paths pass; all commands exit 0 with zero failures.
- Latest validation result:
  - Run context: pure service tests, Python compilation and full backend regression, 2026-08-15
  - Exit/result: 0
  - Summary: focused template tests 15 passed; full backend suite 88 passed; 0 failures. Exact five-template catalog, four standard policy mappings, correction selection, immutable metadata/outcome, editable greeting/closing and all fail-closed negative paths were verified without database or external-service access.
- Decisions/assumptions:
  - Editable content uses one internal `{{decision_critical_content}}` insertion marker so greeting and closing remain editable while the protected block is always inserted by the backend.
  - Exact English copy is an internal reversible implementation detail because approved documents define template types and protected meaning but not final wording.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-007 after user review.

### BE-008 — Deterministic safety guard engine

- Requirement sources: CAP-004, FR-003, FR-010, NFR-001, BR-008, BR-010, VAL-002..VAL-004, AC-003, AC-010, AC-021
- Dependencies: BE-007
- Status: completed
- Acceptance criteria:
  - Pure deterministic engine validates required candidate/draft values, email syntax, recipient and locked identity alignment, approved Stage/Decision/Email Type policy and unresolved placeholders.
  - Engine verifies decision-critical content exactly matches the fixed catalog and that the assembled body contains the protected outcome exactly once.
  - Candidate-name alignment and contradictory subject terms produce explicit blocking issues, including `STATUS_EMAIL_MISMATCH` for AC-010.
  - Result contains all detected issues with stable rule IDs, human-readable remediation and no database, LLM or external-service dependency.
- Files expected/changed:
  - `backend/app/services/safety_guard.py`
  - `backend/tests/services/test_safety_guard.py`
  - `docs/backend/plan.md`
- Validation:
  - Command/procedure: focused pure rule tests including negative paths; Python compilation; full backend regression; delivery-state validator.
  - Pass criteria: every defined rule and fail-closed path passes; all commands exit 0 with zero failures.
- Latest validation result:
  - Run context: pure deterministic unit tests, Python compilation and full backend regression, 2026-08-15
  - Exit/result: 0
  - Summary: focused safety guard tests 20 passed; full backend suite 108 passed; 0 failures. All required rule categories and aggregated negative paths were verified without database, LLM or external-service access.
- Decisions/assumptions:
  - Contradiction queries and post-send history are excluded from this pure engine and implemented in SLICE-008.
  - Revision superseding is excluded and implemented in SLICE-009; this slice validates one candidate/draft snapshot only.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-008 after user review.

### BE-009 — Application ID + Stage contradiction guard

- Requirement sources: CAP-002, FR-002, BR-003..BR-006, AC-002, AC-013, AC-021
- Dependencies: BE-008
- Status: completed
- Acceptance criteria:
  - Normal workflow blocks an opposing communicated decision only when Application ID and Stage both match.
  - Valid cross-stage progression and an unchanged same-stage decision are not falsely classified as contradictions.
  - Decision correction can pass the contradiction boundary while unsupported Stage/Decision combinations still fail closed.
  - Database lookup uses the globally unique Application ID and can lock the candidate row without committing or rolling back the caller transaction.
  - Findings expose stable, human-readable rule IDs and remediation without candidate name or email PII.
- Files expected/changed:
  - `backend/app/services/safety_guard.py`
  - `backend/tests/services/test_contradiction_guard.py`
  - `docs/backend/plan.md`
- Validation:
  - Command/procedure: focused contradiction tests on disposable SQLite; Python compilation; full backend regression; delivery-state validator.
  - Pass criteria: all normal/correction, same-stage/cross-stage and fail-closed paths pass; all commands exit 0 with zero failures.
- Latest validation result:
  - Run context: disposable SQLite service tests, Python compilation and full backend regression, 2026-08-16
  - Exit/result: 0
  - Summary: focused contradiction tests 15 passed; full backend suite 123 passed; 0 failures. Same-stage opposing decisions, valid cross-stage progression, Application ID isolation, caller-owned transaction boundary, correction routing, corrupt prior state and unsupported workflow paths were verified.
- Decisions/assumptions:
  - Candidate communicated fields are the approved current communication record for the MVP; no legacy email-history query is introduced.
  - Same decision in the same stage is not an opposing-result contradiction. Duplicate operation prevention remains owned by the send-operation slices.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-009 after user review.

### BE-010 — Draft revision lifecycle and superseding

- Requirement sources: CAP-004, FR-004, FR-011, BR-007, BR-009, AC-004, AC-011, ENT-002
- Dependencies: BE-009
- Status: completed
- Acceptance criteria:
  - Generate a standard draft from the fixed template and verified candidate data, then persist deterministic guard evidence and READY/BLOCKED status.
  - Editing editable content or subject creates the next candidate-wide revision number and re-runs all deterministic checks.
  - Creating a newer normal revision supersedes only older unsent normal revisions for the same candidate and stage, with UTC superseded timestamps.
  - No-op edits return the current revision; stale, frozen, finalized, discarded or correction drafts cannot be edited through the normal workflow.
  - Candidate row locking serializes revision numbering; service never commits or rolls back the caller transaction.
- Files expected/changed:
  - `backend/app/services/draft_service.py`
  - `backend/tests/services/test_draft_lifecycle.py`
  - `docs/backend/plan.md`
- Validation:
  - Command/procedure: focused lifecycle tests on disposable SQLite; Python compilation; full backend regression; delivery-state validator.
  - Pass criteria: generation/edit/superseding and every negative state path pass; all commands exit 0 with zero failures.
- Latest validation result:
  - Run context: disposable SQLite lifecycle tests, Python compilation and full backend regression, 2026-08-16
  - Exit/result: 0
  - Summary: focused lifecycle tests 17 passed; full backend suite 140 passed; 0 failures. Generation, guard evidence, candidate-wide numbering, stage-scoped superseding, editable revisions, no-op behavior, immutable states, protected content and caller-owned transaction boundaries were verified.
- Decisions/assumptions:
  - Revision numbers are candidate-wide because the approved unique constraint is `(candidate_id, revision_number)`; superseding remains stage-scoped.
  - `FROZEN_IN_FLIGHT` is no longer an unsent editable draft and is never superseded by this service.
  - Decision correction remains owned by SLICE-010 and is not created or superseded here.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-010 after user review.

### BE-011 — Decision correction draft workflow

- Requirement sources: CAP-008, FR-008, DEC-003, BR-011, AC-008, AC-018, ADR-004, REL-002, CON-009
- Dependencies: BE-010
- Status: completed
- Acceptance criteria:
  - Create a correction only for an opposing, policy-valid decision in the same stage as an existing provider-accepted communicated outcome.
  - Require a trimmed rationale of at least five characters and link the correction draft to the exact prior accepted Logical Send Operation.
  - Render the dedicated DECISION_CORRECTION template, run deterministic checks in correction mode and persist status CORRECTION_DRAFT with candidate-wide revision numbering.
  - Reject a second correction while another correction draft or retryable/in-flight correction operation remains active.
  - Keep communicated decision/stage/time unchanged until a later provider-accepted finalization; cancellation discards only an unsent correction draft.
  - Candidate row locking serializes correction initiation; service does not commit or roll back the caller transaction.
- Files expected/changed:
  - `backend/app/services/draft_service.py`
  - `backend/tests/services/test_decision_correction.py`
  - `docs/backend/plan.md`
- Validation:
  - Command/procedure: focused correction workflow tests on disposable SQLite; Python compilation; full backend regression; delivery-state validator.
  - Pass criteria: prior-operation linkage, rationale, policy, duplicate-active, cancellation and transaction boundaries all pass; all commands exit 0 with zero failures.
- Latest validation result:
  - Run context: disposable SQLite correction workflow tests, Python compilation and full backend regression, 2026-08-16
  - Exit/result: 0
  - Summary: focused correction tests 20 passed; full backend suite 160 passed; 0 failures. Rationale, policy, accepted-operation linkage, latest-operation selection, duplicate-active prevention, cancellation, communicated-outcome preservation and transaction ownership were verified.
- Decisions/assumptions:
  - Candidate `status` records the new internal hiring decision when correction is drafted; communicated fields remain the old candidate-facing outcome until provider acceptance.
  - Explicit side-by-side confirmation is a send-boundary requirement for later send/API slices; this slice preserves the prior operation link needed to construct that comparison.
  - Audit event persistence remains assigned to SLICE-016.
- Blocker:
  - None
- Next action:
  - Completed; continue with SLICE-011 after user review.

## Final validation summary

| Check | Command/procedure | Result | Evidence summary |
|---|---|---|---|
| Build/start | `uvicorn app.main:app` | passed | Temporary SQLite smoke server started successfully for browser E2E |
| Lint/type-check | Python import/pytest collection | passed | Application and tests imported successfully in clean virtualenv |
| Unit tests | `.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider` | passed | Full backend regression: 164 passed, 0 failed |
| Integration tests | `python -m pytest -q tests/services/test_excel_import.py` | passed | 11 import service tests passed using disposable SQLite and in-memory Excel files |
| Migration validation | `python scripts/validate_migration_roundtrip.py` | passed | Disposable local PostgreSQL: upgrade/downgrade/upgrade passed with exactly five core tables; demo DB untouched |
| Core smoke test | real Resend sandbox send with explicit approval | blocked | Missing local Resend credential and verified sender |
| OpenAPI consistency | `.venv\\Scripts\\python.exe scripts\\export_openapi.py --check` | passed | Runtime and committed artifact synchronized |
| Secret scan | repository scan excluding local `.env` | pending | Final repository hygiene check remains |

## Delivery status

- State: complete_with_environment_blockers
- Completed capabilities: all SLICE-001..020 code, canonical REST API, real Resend boundary, idempotent send orchestration, retry/reconciliation, atomic audit, test suite and backend handoff
- Partial or blocked capabilities: live Resend smoke test and migration of the pre-existing legacy PostgreSQL database
- Accepted limitations: physical duplicate delivery in provider infrastructure remains residual risk
- First action on resume: obtain approved legacy Stage/Decision mappings and configure Resend credentials in local `.env`, then run controlled release checks
