---
name: team1-ba
description: "Dùng sau khi docs/product/product.md đã được duyệt để phân tích yêu cầu nghiệp vụ, quy trình workflow AS-IS/TO-BE, business rules, use cases, acceptance criteria, traceability matrix và change impact cho pipeline Team1. Dùng khi cần tạo mới, review, gap analysis, thay đổi hoặc tiếp tục phiên BA bị gián đoạn. Không dùng cho product discovery, product prioritization, architecture design, UI design hoặc code implementation."
---

# Team1 Business Analysis (team1-ba)

Chuyển đổi MVP product specification đã được duyệt thành bộ yêu cầu nghiệp vụ đủ rõ, có nguồn, có khả năng kiểm thử và truy vết được cho các skill downstream (Architecture, Database, UI/UX, Backend, Frontend, QA).

## Các nguyên tắc bất biến

- `SOURCE_BEFORE_REQUIREMENT`: Mỗi requirement phải có nguồn cụ thể (Product spec ID, tài liệu nguồn, quyết định của người dùng, business rule). Requirement không có nguồn không được coi là confirmed.
- `TRACEABILITY_BEFORE_HANDOFF`: Không handoff nếu requirement bắt buộc chưa truy vết được: Source -> Requirement -> Acceptance Criteria -> Downstream Owner.
- `NO_SILENT_ASSUMPTIONS`: Mọi giả định phải có ID (`ASM-###`), lý do, tác động, owner và trạng thái. Không biến suy đoán thành confirmed requirement.
- `ONE_QUESTION_PER_TURN`: Khi cần làm rõ quyết định material, chỉ hỏi một câu mỗi lượt. Đưa 2-3 lựa chọn loại trừ nhau, trade-off ngắn, recommendation và tùy chọn bỏ qua/dùng giả định mặc định.
- `NO_FAKE_APPROVAL`: Không đặt trạng thái approved/ready nếu chưa có sự phê duyệt rõ ràng từ người dùng.
- `NO_IMPLEMENTATION`: Không chọn tech stack, không thiết kế database schema, không vẽ giao diện chi tiết, không viết code hoặc migration.
- `DURABLE_STATE`: Lưu trạng thái vào `docs/ba/plan.md` để có thể tiếp tục (resume) chính xác khi bị ngắt phiên.
- `TIMEBOX_AWARE`: Chọn execution profile trước khi làm (`quick`: <=15m, `standard`: <=45m mặc định, `extended`: >45m). Hết timebox phải lưu checkpoint và exact next action.

## Bước 1: Inspect và chọn execution mode

Đọc [input contract](references/input-contract.md). Chọn đúng 1 mode:
1. `full`: Tạo BA spec mới từ `docs/product/product.md` đã được duyệt.
2. `gap-analysis`: Tìm điểm thiếu, mâu thuẫn hoặc không truy vết được trong tài liệu BA/downstream hiện có.
3. `change-impact`: Đánh giá tác động khi có yêu cầu thay đổi (tạo `CR-###.md`).
4. `resume`: Tiếp tục phiên làm việc từ `docs/ba/plan.md` dở dang.

Lập inventory và tính fingerprint đầu vào bằng `python scripts/fingerprint_inputs.py`.

## Bước 2: Phân tích phạm vi và Stakeholders

Xác định Business Objectives (`OBJ-###`), In-scope, Out-of-scope capabilities kế thừa từ Product Spec, Stakeholders/Actors (`ACT-###`), constraints (`CON-###`) và dependencies (`DEP-###`). Không mở rộng phạm vi MVP ngoài scope đã duyệt.

## Bước 3: Phân tích Quy trình AS-IS và TO-BE

Đọc [quy tắc mô hình hóa quy trình](references/business-process-modeling.md). Với mỗi workflow quan trọng:
- Trigger, Preconditions, Main Flow, Alternate Flow, Exception Flow, Postconditions, Data involved, Business Owner, Success Outcome.
- Sử dụng sơ đồ Mermaid (flowchart/sequence) khi cần làm rõ luồng phức tạp.

## Bước 4: Chuẩn hóa Yêu cầu nghiệp vụ (Requirements)

Đọc [chỉ dẫn gán owner](references/ownership-routing.md). Chuẩn hóa hệ thống ID ổn định:
- `OBJ-###` (Objective), `ACT-###` (Actor), `FR-###` (Functional Requirement), `NFR-###` (Non-Functional Requirement), `BR-###` (Business Rule), `UC-###` (Use Case), `AC-###` (Acceptance Criterion), `ASM-###` (Assumption), `CON-###` (Constraint), `DEP-###` (Dependency), `OQ-###` (Open Question), `DEC-###` (Decision), `CR-###` (Change Request).

Mỗi requirement phải bao gồm: ID, Title, Description, Rationale, Source, Priority, Preconditions, Expected outcome, Acceptance criteria, Edge/exception cases, Dependencies, Downstream owners, Status (`proposed`, `confirmed`, `assumed`, `blocked`, `changed`, `deprecated`).

## Bước 5: Kiểm tra chất lượng và xử lý sai lệch

Đọc [quality checklist](references/requirement-quality-checklist.md). Phát hiện yêu cầu mơ hồ, mâu thuẫn, thiếu tiêu chí kiểm thử hoặc thiếu owner. Không tự giải quyết mâu thuẫn material; hỏi người dùng từng câu một theo `ONE_QUESTION_PER_TURN`.

## Bước 6: Xây dựng Ma trận Truy vết (Traceability Matrix)

Đọc [quy tắc truy vết](references/traceability-rules.md). Đánh giá ma trận liên kết từ Product Source -> BA Requirement -> Acceptance Criteria -> Workflow/Use Case -> Downstream Owner -> Current Status.

## Bước 7: Quản lý Yêu cầu Thay đổi (Change Impact)

Đọc [chỉ dẫn change impact](references/change-impact-guide.md). Trong mode `change-impact`:
- Tạo `docs/ba/changes/CR-###.md` từ [template change request](assets/change-request.template.md).
- Phân tích ảnh hưởng đến Product, Architecture, Database, UI/UX, Backend, Frontend, QA.
- Phân loại mức độ tác động (`none`, `low`, `medium`, `high`, `blocker`). Không tự sửa tài liệu approved của skill khác.

## Bước 8: Approval Gate và Handoff

Dùng các template tại `assets/` để ghi kết quả:
- `<project-root>/docs/ba/plan.md` từ [ba-plan.template.md](assets/ba-plan.template.md).
- `<project-root>/docs/ba/business-analysis.md` từ [business-analysis.template.md](assets/business-analysis.template.md).
- `<project-root>/docs/ba/requirements-traceability.md` từ [traceability-matrix.template.md](assets/traceability-matrix.template.md).

Chạy công cụ kiểm tra định ước: `python scripts/validate_ba_state.py`.
Chỉ tuyên bố `READY_FOR_HANDOFF` khi validator vượt qua và không còn blocker.

Các trạng thái hoàn thành hợp lệ: `DRAFT`, `NEEDS_CLARIFICATION`, `BLOCKED`, `READY_WITH_ACCEPTED_ASSUMPTIONS`, `READY_FOR_HANDOFF`.
