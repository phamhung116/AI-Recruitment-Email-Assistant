# Ownership Routing — Team2 BA Skill

## 1. Bảng Định Tuyền Trách Nhiệm Downstream (Downstream Routing Rules)

Mỗi yêu cầu nghiệp vụ sau khi được chuẩn hóa phải được gán trách nhiệm rõ ràng cho các nhóm/skill hạ nguồn:

| Nhóm Downstream | Ký hiệu Owner | Loại Yêu Cầu Phù Hợp | Tài liệu Handoff Tương Ứng |
|---|---|---|---|
| Architecture | `Architecture` | NFR về Performance, Security, Availability, Integration | `<project-root>/docs/architecture/architecture.md` |
| Database | `Database` | Data Ownership, Entity Rules, Retention Policy | `<project-root>/docs/database/database.md` |
| UI / UX | `UI-UX` | User Flow, User Interaction, Screen Layout Expectation | `<project-root>/docs/ui-ux/ui-to-frontend.md` |
| Backend | `Backend` | Business Rules, API Logic, Calculations, Integrations | `<project-root>/docs/backend/backend.md` |
| Frontend | `Frontend` | Form Validation, Client-side States, UI Events | `<project-root>/docs/frontend/frontend.md` |
| QA / Testing | `QA` | Acceptance Criteria, Edge Cases, Exception Scenarios | Test Cases & Automation Test Scripts |

Không để trống mục Downstream Owner cho bất kỳ yêu cầu nào.
