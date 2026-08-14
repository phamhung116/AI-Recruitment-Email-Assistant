# Requirement Quality Checklist — Team2 BA Skill

## 1. Tiêu Chí Kiểm Tra Chất Lượng Yêu Cầu (Quality Criteria)

Mỗi yêu cầu nghiệp vụ (FR / NFR / BR) khi được tạo ra phải vượt qua 12 tiêu chí kiểm tra chất lượng sau:

1. **Clear Wording (Từ ngữ rõ ràng):** Không dùng các từ mơ hồ như *"nhanh", "dễ dùng", "tối ưu", "mạnh mẽ", "khi cần"*.
2. **Testability (Khả năng kiểm thử):** Phải kèm theo ít nhất 1 Acceptance Criterion (`AC-###`) có thể xác minh bằng Test Case cụ thể.
3. **Actor Association (Xác định Actor):** Mọi hành vi phải chỉ rõ Primary Actor (`ACT-###`) thực hiện.
4. **Failure & Exception Behavior (Xử lý lỗi):** Phải định nghĩa luồng xử lý ngoại lệ, thông báo lỗi và trạng thái hệ thống khi thất bại.
5. **Authorization & Security (Phân quyền):** Rõ ràng ai có quyền thực hiện, điều kiện phân quyền và bảo mật dữ liệu liên quan.
6. **Data Ownership & Persistence (Chủ sở hữu dữ liệu):** Xác định dữ liệu tạo ra thuộc thực thể nào, lưu trữ ở đâu và quy định lưu vết.
7. **No Contradiction (Không mâu thuẫn):** Không mâu thuẫn với bất kỳ yêu cầu nào khác trong cùng phiên hoặc tài liệu nguồn.
8. **No Orphan Requirements (Không mồ côi):** Mọi yêu cầu phải truy vết ngược về Product Requirement hoặc Business Objective hợp lệ.
9. **No Scope Creep (Không phình phạm vi):** Không bổ sung tính năng mới ngoài MVP scope đã được phê duyệt trong `product.md`.
10. **Supported Assumptions (Giả định được công nhận):** Mọi giả định liên quan phải có mã `ASM-###` và được chấp nhận hoặc ghi nhận rủi ro.
11. **Downstream Ownership (Chủ sở hữu downstream):** Mọi yêu cầu phải gán trách nhiệm cho ít nhất 1 team triển khai (`Architecture`, `Database`, `UI/UX`, `Backend`, `Frontend`, `QA`).
12. **Stable ID (Định danh ổn định):** Tất cả các mục phải sử dụng mã ID chuẩn hóa duy nhất và không bị thay đổi ngẫu nhiên.

---

## 2. Bảng Mã Định Danh Chuẩn (Standard ID Schema)

- `OBJ-###`: Business Objective
- `ACT-###`: Actor / Stakeholder
- `FR-###`: Functional Requirement
- `NFR-###`: Non-Functional Requirement
- `BR-###`: Business Rule
- `UC-###`: Use Case
- `AC-###`: Acceptance Criterion
- `ASM-###`: Assumption
- `CON-###`: Constraint
- `DEP-###`: Dependency
- `OQ-###`: Open Question
- `DEC-###`: Decision
- `CR-###`: Change Request
