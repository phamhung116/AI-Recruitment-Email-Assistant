# Traceability Rules — Team2 BA Skill

## 1. Nguyên Tắc Ma Trận Truy Vết (Requirements Traceability Matrix - RTM)

1. **Chuỗi Truy Vết Bắt Buộc (Mandatory Traceability Chain):**
   ```text
   Product Source (PRD ID)
   └── BA Requirement (FR-### / NFR-### / BR-###)
       └── Acceptance Criteria (AC-###)
           └── Workflow / Use Case (UC-###)
               └── Downstream Owner (Architecture / Database / UI-UX / Backend / Frontend / QA)
                   └── Current Status
   ```

2. **Chấm Dứt Trạng Thái Mồ Côi (No Orphan Requirement):**
   - Bất kỳ requirement nào không có **Product Source** hợp lệ được coi là *Orphan Requirement*.
   - Bất kỳ requirement nào không có **Downstream Owner** hoặc **Acceptance Criteria** sẽ làm vô hiệu hóa trạng thái `READY_FOR_HANDOFF`.

3. **Cập Nhật Tự Động Thống Kê RTM:**
   Trong file `<project-root>/docs/ba/requirements-traceability.md`, luôn có phần tổng hợp con số thống kê:
   - Total Requirements
   - Total Confirmed
   - Total Assumed
   - Total Blocked
   - Total Orphaned
   - Total Missing Acceptance Criteria
   - Total Missing Downstream Owner
