# Input Contract & Classification Rules

Tài liệu này định nghĩa quy định tiếp nhận và phân loại tất cả các đầu vào mà skill `team1-ba` xử lý.

## 1. Phân loại đầu vào (Input Classification)

Mọi đầu vào được phân loại vào đúng 1 trong 6 trạng thái:

- `required`: Đầu vào bắt buộc phải có để bắt đầu phân tích. Trong full mode, `<project-root>/docs/product/product.md` là bắt buộc.
- `optional`: Đầu vào bổ trợ như tài liệu đề xuất của stakeholder, quy định nghiệp vụ công ty, OpenAPI contract hiện có.
- `unavailable`: Tài liệu được nhắc tới nhưng không tìm thấy file hoặc không có nội dung khả dụng.
- `stale`: Đầu vào có mốc thời gian/fingerprint cũ hơn so với phiên bản cập nhật gần nhất của tài liệu upstream.
- `contradictory`: Hai hoặc nhiều đầu vào chứa thông tin nghiệp vụ mâu thuẫn trực tiếp với nhau.
- `not applicable`: Đầu vào không liên quan tới phạm vi dự án hiện tại.

## 2. Quy định về minh chứng phê duyệt (Approval Evidence)

- Không coi tài liệu là `approved` nếu không có minh chứng phê duyệt rõ ràng (trạng thái `APPROVED` ghi trong file spec hoặc câu xác nhận trực tiếp của người dùng).
- Trường hợp tài liệu upstream ở trạng thái `DRAFT` hoặc `NEEDS_CLARIFICATION`, skill phải dừng ở trạng thái `BLOCKED` hoặc hỏi người dùng làm rõ trước khi tiếp tục.

## 3. Fingerprinting & Integrity

Trước khi phân tích, phải gọi script `python scripts/fingerprint_inputs.py` để tính SHA-256 cho toàn bộ file đầu vào khả dụng và lưu vết vào `docs/ba/plan.md`. Khi ở `resume` mode, nếu SHA-256 của file nguồn thay đổi, kết quả phân tích liên quan phải được đánh giá lại.
