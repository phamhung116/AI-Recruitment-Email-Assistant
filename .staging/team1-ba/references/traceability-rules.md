# Requirements Traceability Rules

Tài liệu hướng dẫn thiết lập và duy trì ma trận truy vết (Requirements Traceability Matrix - RTM).

## 1. Cấu trúc chuỗi truy vết (Traceability Chain)

Mọi yêu cầu nghiệp vụ phải tuân thủ đúng chuỗi liên kết 6 mắt xích:
```text
Product Source (SPEC-### / Item)
  └── BA Requirement (FR-### / NFR-###)
        ├── Acceptance Criteria (AC-###)
        ├── Business Workflow / Use Case (UC-###)
        ├── Downstream Owner / Artifact (Architecture / DB / UI / Backend / Frontend / QA)
        └── Current Status (proposed / confirmed / assumed / blocked / changed / deprecated)
```

## 2. Quy tắc Validator kiểm tra Traceability

- **Rule 1 (No Broken Links)**: Mọi tham chiếu ID (ví dụ: `Source: SPEC-001`, `AC: AC-001`) phải tồn tại trong danh mục nguồn hoặc danh mục AC.
- **Rule 2 (No Orphan Requirements)**: Nếu một `FR-###` không có `Source` hoặc không có `Downstream Owner`, validator sẽ báo lỗi `ORPHAN_REQUIREMENT`.
- **Rule 3 (Mandatory AC Coverage)**: Mọi `FR-###` ở trạng thái `confirmed` hoặc `proposed` bắt buộc phải có ít nhất một `AC-###`.
- **Rule 4 (Strict Status Consistency)**: Nếu một requirement ở trạng thái `blocked`, tất cả các `UC-###` và `AC-###` phụ thuộc cũng không được phép đánh dấu `READY_FOR_HANDOFF`.
