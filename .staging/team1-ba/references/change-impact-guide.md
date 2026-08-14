# Change Impact Analysis Guide

Hướng dẫn đánh giá tác động khi có yêu cầu thay đổi nghiệp vụ (Change Request).

## 1. Quy trình xử lý Change Impact Mode

Khi người dùng yêu cầu thay đổi nghiệp vụ:
1. Tạo tệp Change Request mới tại `<project-root>/docs/ba/changes/CR-###.md`.
2. Trích xuất yêu cầu thay đổi, người yêu cầu và lý do thay đổi.
3. Rà soát danh mục yêu cầu hiện tại trong `docs/ba/business-analysis.md` để xác định danh sách `FR-###` và `NFR-###` bị ảnh hưởng.
4. Đánh giá tác động theo các chiều:
   - **Product Scope**: Có vi phạm MVP non-goals hoặc mở rộng tính năng ngoài ý định ban đầu không?
   - **Architecture**: Có làm thay đổi luồng xử lý hệ thống hoặc tích hợp không?
   - **Database**: Có yêu cầu thay đổi cấu trúc bảng, trường thông tin hoặc quan hệ không?
   - **UI/UX**: Có thay đổi layout, luồng màn hình hoặc trạng thái UI không?
   - **Backend / Frontend**: Có làm hỏng các API hoặc logic hiện tại không?
   - **QA**: Cần bổ sung hoặc sửa đổi những kịch bản kiểm thử nào?

## 2. Thước đo mức độ tác động (Impact Severity Levels)

- `none`: Không ảnh hưởng đến các tài liệu hoặc code hiện có.
- `low`: Ảnh hưởng nhỏ đến mô tả tiêu chuẩn, không thay đổi logic downstream.
- `medium`: Yêu cầu điều chỉnh nhẹ ở 1-2 downstream specs (UI hoặc Backend).
- `high`: Làm thay đổi đáng kể luồng nghiệp vụ, giao diện và cấu trúc dữ liệu.
- `blocker`: Mâu thuẫn trực tiếp với định hướng kiến trúc hoặc scope sản phẩm cốt lõi đã duyệt.

*Lưu ý bất biến*: Không tự ý sửa các tài liệu downstream đã được duyệt. Phải ghi nhận kết quả phân tích tác động và chuyển giao (handoff) cho artifact owner tương ứng thực hiện review.
