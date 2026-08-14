# Change Impact Guide — Team2 BA Skill

## 1. Quy Trình Quản Lý Thay Đổi (Change Impact Management)

Khi kích hoạt `change-impact` mode, không được phép âm thầm thay đổi hoặc ghi đè trực tiếp các yêu cầu đã phê duyệt. Bắt buộc thực hiện theo các bước:

1. **Khởi tạo Change Request:** Tạo file `<project-root>/docs/ba/changes/CR-###.md` dựa trên template `assets/change-request.template.md`.
2. **Liệt Kê Yêu Cầu Bị Ảnh Hưởng:** Xác định chính xác các mã `FR-###`, `NFR-###`, `BR-###`, `UC-###` bị ảnh hưởng trực tiếp hoặc gián tiếp.
3. **Đánh Giá Tác Động Downstream (Impact Rating):**
   - `none`: Không ảnh hưởng.
   - `low`: Ảnh hưởng nhỏ tới giao diện hoặc tài liệu.
   - `medium`: Cần sửa đổi API hoặc logic nghiệp vụ phụ.
   - `high`: Ảnh hưởng tới cơ sở dữ liệu hoặc luồng xử lý chính.
   - `blocker`: Thay đổi lớn làm hỏng kiến trúc hoặc phạm vi MVP.
4. **Xác Định Artifact Owner Cần Review:** Đánh dấu rõ các vai trò cần rà soát lại (`Architecture`, `Database`, `UI/UX`, `Backend`, `Frontend`, `QA`).
5. **Giữ Nguyên Approved Document:** Không thay đổi trạng thái sang `confirmed` hay `accepted` nếu chưa có quyết định phê duyệt (DEC-###) từ người dùng.
