---
name: team2-ba
description: "Phân tích yêu cầu nghiệp vụ, workflow, business rule, use case, acceptance criteria, traceability và change impact sau khi docs/product/product.md đã được duyệt. Dùng khi cần tạo mới, review, gap analysis, thay đổi hoặc tiếp tục một phiên BA bị gián đoạn. Không dùng cho product discovery, product prioritization, architecture design, UI design hoặc implementation."
---

# Team2 Business Analysis

Chuyển đổi product specification đã được duyệt thành bộ yêu cầu nghiệp vụ chuẩn hóa, có nguồn gốc, có khả năng kiểm thử và truy vết đầy đủ cho các kỹ sư triển khai tiếp theo.

## Các Nguyên Tắc Bất Biến (Invariants)

1. `SOURCE_BEFORE_REQUIREMENT`: Mọi requirement phải có nguồn hợp lệ (Product ID, tài liệu nguồn, User Decision, Policy, hoặc Assumption được dán nhãn ASM-###). Requirement không có nguồn không được công nhận là `confirmed`.
2. `TRACEABILITY_BEFORE_HANDOFF`: Không kết luận `READY_FOR_HANDOFF` nếu requirement bắt buộc chưa được truy vết trọn vẹn: Source → Requirement → AC → Downstream Owner.
3. `NO_SILENT_ASSUMPTIONS`: Mọi giả định phải có ID (ASM-###), lý do, tác động, người sở hữu và trạng thái.
4. `ONE_QUESTION_PER_TURN`: Khi hỏi người dùng để làm rõ, chỉ hỏi **1 câu mỗi lượt** với 2–3 lựa chọn loại trừ nhau, trade-off ngắn, 1 lựa chọn khuyến nghị và tùy chọn "Bỏ qua / Giả định mặc định".
5. `NO_FAKE_APPROVAL`: Không tự đặt trạng thái approved hoặc ready nếu người dùng chưa phê duyệt các quyết định material.
6. `NO_IMPLEMENTATION`: Không viết hoặc sửa bất kỳ mã nguồn ứng dụng hay code triển khai nào.
7. `DURABLE_STATE`: Luôn lưu trữ checkpoint tại `<project-root>/docs/ba/plan.md` để có thể khôi phục phiên bị gián đoạn.
8. `TIMEBOX_AWARE`: Chọn profile (`quick`, `standard`, `extended`), ghi nhận mốc thời gian và điểm dừng. Không báo hoàn thành giả khi hết thời gian.

## Quy Trình Thực Thi

### Bước 1: Kiểm Tra Đầu Vào & Chọn Mode
- Đọc [Input Contract](references/input-contract.md). Kiểm tra sự tồn tại của `<project-root>/docs/product/product.md`.
- Chọn đúng 1 Execution Mode:
  - `full`: Tạo mới BA specification từ product doc đã approved.
  - `gap-analysis`: Tìm điểm thiếu, mâu thuẫn hoặc đứt gãy truy vết.
  - `change-impact`: Đánh giá ảnh hưởng khi có yêu cầu thay đổi (CR-###).
  - `resume`: Đã có `docs/ba/plan.md` chưa hoàn thành.
- Chọn Execution Profile: `quick` (≤15m), `standard` (≤45m), `extended` (>45m).

### Bước 2: Inventory & Fingerprint Input
- Chạy `python .gemini/skills/team2-ba/scripts/fingerprint_inputs.py` để tính SHA-256 cho các tài liệu đầu vào.
- Phân loại tài liệu: `required`, `optional`, `unavailable`, `stale`, `contradictory`, `not_applicable`.

### Bước 3: Phân Tích Scope & Actors
- Trích xuất Business Objectives (OBJ-###), Stakeholders (ACT-###), In-scope / Out-of-scope capabilities, Constraints (CON-###) và Dependencies (DEP-###).
- Tuân thủ nghiêm ngặt phạm vi MVP trong `product.md`. Không tự ý mở rộng scope.

### Bước 4: Mô Hình Hóa Quy Trình AS-IS & TO-BE
- Đọc [Business Process Modeling](references/business-process-modeling.md).
- Mô tả chi tiết Workflow: Trigger, Preconditions, Main flow, Alternate flow, Exception flow, Postconditions, Data involved. Sử dụng sơ đồ Mermaid khi cần.

### Bước 5: Chuẩn Hóa Yêu Cầu & Acceptance Criteria
- Sử dụng bảng mã ID chuẩn: `OBJ`, `ACT`, `FR`, `NFR`, `BR`, `UC`, `AC`, `ASM`, `CON`, `DEP`, `OQ`, `DEC`, `CR`.
- Mỗi requirement bắt buộc có: ID, Title, Rationale, Source, Priority, Expected Outcome, Acceptance Criteria (AC-###), Downstream Owners, Status (`proposed`, `confirmed`, `assumed`, `blocked`, `changed`, `deprecated`).
- Đọc [Requirement Quality Checklist](references/requirement-quality-checklist.md) để kiểm tra chất lượng yêu cầu.

### Bước 6: Xây Dựng Requirements Traceability Matrix (RTM)
- Đọc [Traceability Rules](references/traceability-rules.md) và [Ownership Routing](references/ownership-routing.md).
- Đảm bảo mọi dòng liên kết trọn vẹn: Product Source → BA Requirement → AC → Workflow/UC → Downstream Owner.

### Bước 7: Xử Lý Thay Đổi (Change Impact Mode)
- Khi có thay đổi, đọc [Change Impact Guide](references/change-impact-guide.md). Sinh file `docs/ba/changes/CR-###.md`, phân tích mức độ tác động và đề xuất review cho chủ sở hữu tài liệu downstream.

### Bước 8: Validation & Handoff
- Ghi các tài liệu canonical:
  - `<project-root>/docs/ba/plan.md` (từ `assets/ba-plan.template.md`)
  - `<project-root>/docs/ba/business-analysis.md` (từ `assets/business-analysis.template.md`)
  - `<project-root>/docs/ba/requirements-traceability.md` (từ `assets/traceability-matrix.template.md`)
- Chạy `python .gemini/skills/team2-ba/scripts/validate_ba_state.py` để kiểm tra toàn bộ quy tắc trước khi tuyên bố trạng thái `READY_FOR_HANDOFF`.
