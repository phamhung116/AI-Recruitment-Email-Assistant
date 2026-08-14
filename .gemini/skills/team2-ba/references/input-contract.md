# Input Contract — Team2 BA Skill

## 1. Phân Loại Đầu Vào (Input Classifications)

Mọi tài liệu hoặc thông tin đầu vào được đưa vào `team2-ba` phải được gắn một trong các nhãn trạng thái sau:

- `required`: Bắt buộc phải có để thực hiện phân tích (ví dụ: `<project-root>/docs/product/product.md`). Nếu thiếu, chuyển trạng thái hệ thống sang `BLOCKED`.
- `optional`: Đầu vào bổ trợ (ví dụ: tài liệu quy định nội bộ, OpenAPI spec, giao diện mẫu).
- `unavailable`: Tài liệu được nhắc tới nhưng chưa sẵn sàng hoặc không tìm thấy.
- `stale`: Tài liệu đã cũ hoặc có vân tay (fingerprint) không khớp với checkpoint gần nhất.
- `contradictory`: Tài liệu có xung đột trực tiếp với các tài liệu đầu vào khác.
- `not_applicable`: Tài liệu không liên quan tới phạm vi dự án hiện tại.

---

## 2. Danh Mục Đầu Vào Chi Tiết

| Loại tài liệu | Đường dẫn / Nguồn chuẩn | Trạng thái bắt buộc | Mục đích sử dụng |
|---|---|---|---|
| Product Specification | `<project-root>/docs/product/product.md` | `required` | Nguồn duy nhất cho Product Scope & Objectives |
| Architecture Specification | `<project-root>/docs/architecture/architecture.md` | `optional` (Gap/Impact mode) | Rà soát kiến trúc hạ tầng & constraints |
| Database Specification | `<project-root>/docs/database/database.md` | `optional` | Rà soát mô hình dữ liệu thực thể |
| UI/UX Specification | `<project-root>/docs/ui-ux/ui-to-frontend.md` | `optional` | Đối chiếu luồng giao diện người dùng |
| Backend Specification | `<project-root>/docs/backend/backend.md` | `optional` | Đối chiếu các API endpoint & business logic |
| Existing BA Artifacts | `<project-root>/docs/ba/*` | `optional` (Resume mode) | Tiếp tục phiên phân tích hoặc đánh giá lại |

---

## 3. Quy Tắc Xác Minh Approval State

1. Không công nhận một tài liệu là `approved` nếu không có bằng chứng phê duyệt rõ ràng từ người dùng hoặc dấu mốc `APPROVED` trong tài liệu đó.
2. Khi phát hiện mâu thuẫn giữa 2 tài liệu đầu vào, không tự ý chọn một bên. Phải ghi nhận thành `OQ-###` (Open Question) và hỏi người dùng theo nguyên tắc `ONE_QUESTION_PER_TURN`.
