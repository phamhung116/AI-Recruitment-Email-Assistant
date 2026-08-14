# Business Process Modeling Guide

Hướng dẫn mô hình hóa quy trình nghiệp vụ AS-IS và TO-BE cho `team1-ba`.

## 1. Cấu trúc mô tả luồng quy trình (Flow Specification)

Mỗi quy trình nghiệp vụ chính phải được trình bày theo cấu trúc chuẩn:
- **Process Name / ID**: Tên và mã định danh quy trình (`UC-###`).
- **Trigger**: Sự kiện kích hoạt quy trình.
- **Preconditions**: Điều kiện tiên quyết để quy trình bắt đầu.
- **Main Flow (Happy Path)**: Trình tự các bước thực hiện thành công từ 1 đến N.
- **Alternate Flows**: Các luồng rẽ nhánh hợp lệ.
- **Exception / Failure Flows**: Trình tự xử lý sự cố hoặc khi dữ liệu không thỏa mãn business rules.
- **Postconditions**: Trạng thái hệ thống sau khi hoàn tất quy trình.
- **Data Involved**: Các đối tượng dữ liệu được tạo mới, đọc, cập nhật hoặc xóa (CRUD).
- **Business Owner**: Người sở hữu nghiệp vụ chịu trách nhiệm về quy trình này.

## 2. Quy chuẩn sơ đồ Mermaid

Sử dụng sơ đồ Mermaid để minh họa các luồng phức tạp:
- **Flowchart (`graph TD` / `graph LR`)**: Dùng cho mô hình luồng quyết định (decision flow) và luồng xử lý tổng thể.
- **Sequence Diagram (`sequenceDiagram`)**: Dùng cho luồng giao tiếp giữa User/Actor và các thành phần hệ thống.

*Lưu ý syntax*: Tránh đặt ký tự đặc biệt trong label sơ đồ Mermaid để tránh lỗi render.
