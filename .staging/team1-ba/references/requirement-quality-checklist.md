# Requirement Quality Checklist

Bảng kiểm tra chất lượng yêu cầu nghiệp vụ (Business Requirements Quality Checklist) dùng để phát hiện lỗi trước khi handoff.

## 1. Các tiêu chí kiểm định (Quality Criteria)

- **Clear & Unambiguous**: Không chứa từ ngữ mơ hồ ("nhanh", "dễ dùng", "tùy chọn", "hợp lý", "sớm nhất có thể"). Mọi tiêu chí phải đo lường hoặc kiểm thử được.
- **Traceable Source**: Mỗi requirement có duy nhất nguồn hợp lệ (`SOURCE_BEFORE_REQUIREMENT`).
- **Testable Acceptance Criteria**: Mỗi Functional Requirement (`FR-###`) phải có ít nhất một Acceptance Criterion (`AC-###`) với cấu hình Given-When-Then hoặc quy tắc kiểm thử rõ ràng.
- **Explicit Failure & Exception Behavior**: Mọi luồng chính đều phải có mô tả hành vi xử lý khi lỗi xảy ra (ví dụ: mất kết nối, dữ liệu không hợp lệ, người dùng hủy thao tác).
- **Authorization & Data Ownership**: Xác định rõ Actor nào (`ACT-###`) có quyền thực hiện thao tác và ai sở hữu dữ liệu liên quan.
- **No Unassigned Requirements**: Mọi yêu cầu nghiệp vụ bắt buộc phải được gán ít nhất một downstream owner (`Architecture`, `Database`, `UI/UX`, `Backend`, `Frontend`, `QA`).

## 2. Danh sách Anti-patterns cần gắn cờ (Flags)

1. **Orphan Requirement**: Requirement không có Nguồn (`Source`) hoặc không có Downstream Owner.
2. **Scope Creep**: Yêu cầu tự thêm mới không nằm trong phạm vi MVP đã duyệt của `docs/product/product.md`.
3. **Unsupported Assumption**: Giả định quan trọng (Material Assumption) chưa được người dùng chấp nhận nhưng đã được coi là confirmed requirement.
4. **Contradiction**: Hai yêu cầu mâu thuẫn trực tiếp (ví dụ: FR-001 yêu cầu bắt buộc nhập số điện thoại, nhưng FR-005 cho phép bỏ qua bước nhập thông tin liên lạc).
