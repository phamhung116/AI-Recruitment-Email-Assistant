# Downstream Ownership & Routing Rules

Quy tắc gán quyền sở hữu yêu cầu nghiệp vụ cho các skill downstream trong pipeline Team1.

## 1. Bản đồ định tuyến Owner (Owner Routing Map)

Mọi yêu cầu nghiệp vụ (`FR-###`, `NFR-###`) phải được phân công cho một hoặc nhiều Downstream Owners theo nguyên tắc sau:

- **Architecture (`team1-architecture`)**: Các NFR về hiệu năng, bảo mật, tính khả dụng, tích hợp hệ thống bên thứ ba, hoặc yêu cầu liên quan đến chiến lược hạ tầng/runtime.
- **Database (`team1-dbdesign`)**: Các yêu cầu về lưu trữ dữ liệu, quy tắc ràng buộc toàn vẹn dữ liệu (data constraints), thời gian lưu trữ (retention), audit log.
- **UI/UX (`team1-ui-ux`)**: Các yêu cầu về quy trình tương tác người dùng, form nhập liệu, validation trên UI, hiển thị trạng thái lỗi/rỗng/loading, trải nghiệm giao diện.
- **Backend (`team1-backend`)**: Các yêu cầu về xử lý nghiệp vụ phía máy chủ, tính toán, xử lý bất đồng bộ, API endpoints, mã lỗi nghiệp vụ.
- **Frontend (`team1-frontend`)**: Các yêu cầu về state management phía client, routing giao diện, gọi API và phản hồi thao tác người dùng.
- **QA (`team1-qa`)**: Tất cả các yêu cầu (`FR-###`, `NFR-###`) để phục vụ việc lập kịch bản test suite end-to-end và nghiệm thu.

## 2. Quy chuẩn Handoff

Khi hoàn tất tài liệu BA và đạt trạng thái `READY_FOR_HANDOFF`, skill `team1-ba` sẽ cung cấp thông tin đường dẫn canonical outputs (`docs/ba/business-analysis.md`, `docs/ba/requirements-traceability.md`) để bước tiếp theo trong pipeline (`team1-architecture`) có thể tiếp nhận và xử lý.
