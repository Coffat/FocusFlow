# 02 — Review Use Case Diagram & Use Case Specification

Chuẩn: UML 2.5.1 (use case), Cockburn "Writing Effective Use Cases" (goal level, extension).

Mục lục: A. Use case diagram · B. Use case spec · C. Độ phủ & chất lượng tập UC · D. Lỗi hay gặp

## A. Use case diagram

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| UC-A01 | **Actor là vai trò**, không phải cá nhân hoặc thành phần nội bộ | "Nguyễn Văn A", "Database", "Controller", "Module Thanh toán" là actor | S2 |
| UC-A02 | Phân biệt actor chính (khởi tạo) và phụ (hệ thống ngoài được gọi); đặt đúng bên | Cổng thanh toán đặt bên trái như người dùng | S3 |
| UC-A03 | Mỗi actor có ≥1 UC; mỗi UC có ≥1 actor (trừ UC chỉ được `include`) | Actor/UC mồ côi | S2 |
| UC-A04 | Tên UC: **động từ + đối tượng**, thể hiện mục tiêu của actor, không phải thao tác UI | "Nhấn nút lưu", "Màn hình đăng nhập" | S3 |
| UC-A05 | **Goal level hợp lý**: UC = một mục tiêu người dùng hoàn thành trong một phiên làm việc | Quá nhỏ (từng CRUD field), quá lớn ("Quản lý hệ thống") | S2 |
| UC-A06 | **`<<include>>`**: mũi tên đứt **từ UC gốc → UC được include**; hành vi bắt buộc, luôn thực hiện | Mũi tên ngược chiều; include cho hành vi tùy chọn | S2 |
| UC-A07 | **`<<extend>>`**: mũi tên đứt **từ UC mở rộng → UC gốc**; hành vi có điều kiện, có extension point & điều kiện | Extend không có điều kiện/extension point; UC gốc phụ thuộc UC extend | S2 |
| UC-A08 | Generalization actor/UC dùng khi thật sự "là một loại"; mũi tên rỗng tam giác về phía cha | Dùng generalization thay include; cây kế thừa sâu không cần | S3 |
| UC-A09 | System boundary rõ; actor nằm ngoài, UC nằm trong | Không có boundary; UC của hệ thống khác lẫn vào | S3 |
| UC-A10 | Không biểu diễn **thứ tự/luồng dữ liệu** (đó là activity/sequence) | Mũi tên giữa các UC thể hiện "sau đó" | S2 |
| UC-A11 | Không nhồi quá nhiều UC trong một sơ đồ (≳ 20–25) → tách theo gói/subsystem | Sơ đồ không đọc nổi | S3 |
| UC-A12 | Include/extend không lạm dụng: tách UC "Xác thực" dùng chung được; tách thành UC nhỏ nhặt chỉ để vẽ | | S3 |

## B. Use case specification

Một spec đủ gồm: ID, tên, mục tiêu, tóm tắt, actor chính/phụ, mức (goal level), **precondition**, **trigger**, **luồng chính (main success scenario)**, **luồng thay thế/ngoại lệ (extensions)**, **postcondition** (thành công + tối thiểu khi thất bại), **business rule**, **NFR liên quan**, **tần suất/khối lượng**, giao diện/UI tham chiếu, câu hỏi mở.

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| UC-B01 | Precondition là trạng thái **kiểm chứng được** của hệ thống/dữ liệu, không phải hành động của actor | "Người dùng muốn thanh toán" | S2 |
| UC-B02 | Trigger xác định, một sự kiện bắt đầu | Không rõ UC bắt đầu khi nào | S3 |
| UC-B03 | Luồng chính: bước đánh số, **mỗi bước một hành động**, chủ ngữ rõ (Actor/Hệ thống), kết thúc ở thành công của mục tiêu | Bước gộp nhiều hành động; thiếu chủ ngữ; luồng chính chứa rẽ nhánh | S2 |
| UC-B04 | Luồng thay thế **tham chiếu số bước** và nêu **điểm quay lại** (resume ở bước nào / kết thúc UC) | "Nếu lỗi thì báo lỗi" không nói tiếp thế nào | S2 |
| UC-B05 | Phủ ngoại lệ hệ thống: validate sai, không có quyền, dữ liệu không tồn tại/đã bị đổi (concurrency), hết phiên, timeout, hệ thống ngoài lỗi, trùng lặp, hủy giữa chừng | Chỉ có 1–2 lỗi chung | S2 |
| UC-B06 | Mỗi lỗi có **kết quả quan sát được**: thông báo/mã lỗi, trạng thái dữ liệu sau lỗi (rollback/giữ nguyên) | "Hiển thị lỗi" | S2 |
| UC-B07 | Postcondition thành công: nêu thay đổi dữ liệu/trạng thái/sự kiện phát ra; **minimal guarantee** khi thất bại | Chỉ nói "thành công" | S2 |
| UC-B08 | Business rule được tham chiếu bằng ID, không chép lại khác nhau | Rule lặp với số khác | S2 |
| UC-B09 | Quyền: ai được kích hoạt, dữ liệu nào được thấy | Không đề cập quyền | S2 |
| UC-B10 | Không lộ chi tiết UI/công nghệ ("bấm nút xanh", "gọi stored procedure") trừ ràng buộc | | S3 |
| UC-B11 | Thuật ngữ khớp glossary & tên entity trong class/DB | | S3 |
| UC-B12 | Include/extend trong spec khớp với diagram (UC được include có tên, step gọi) | | S2 |
| UC-B13 | Có luồng **hủy/quay lại** khi UC nhiều bước | | S3 |
| UC-B14 | Có audit/thông báo/sự kiện phát ra khi nghiệp vụ yêu cầu | | S3 |
| UC-B15 | Luồng chính ≤ ~9–10 bước; nhiều hơn → gợi ý tách | | S4 |

## C. Độ phủ & chất lượng tập UC

| ID | Kiểm tra | Sev |
|---|---|---|
| UC-C01 | Mỗi FR trong SRS ánh xạ ≥1 UC (hoặc được giải thích vì sao không) | S2 |
| UC-C02 | Mỗi UC truy về ≥1 FR/mục tiêu nghiệp vụ (không có UC "mồ côi" yêu cầu) | S3 |
| UC-C03 | Vòng đời đối tượng chính có UC: tạo, xem, sửa, hủy/đóng, khôi phục, lưu trữ (nếu có) | S2 |
| UC-C04 | Vai trò quản trị/vận hành có UC (cấu hình, phân quyền, đối soát, báo cáo) — hay bị quên | S2 |
| UC-C05 | UC tích hợp/batch/job nền (actor là "Scheduler"/hệ thống ngoài) được mô hình | S3 |
| UC-C06 | Không trùng UC thực chất cùng một mục tiêu | S3 |

## D. Lỗi hay gặp (để đối chiếu nhanh)

- Dùng **extend** để biểu diễn "luồng lỗi" của luồng chính → lỗi thuộc extensions của spec, không phải extend diagram.
- Dùng **include** như gọi hàm tùy ý → chỉ include khi dùng lại thật.
- UC kiểu "CRUD tách rời" cho mọi bảng thay vì mục tiêu nghiệp vụ.
- Spec có luồng chính chạy đến "xong" nhưng postcondition không nói dữ liệu nào đổi.
- "Hệ thống" làm mọi thứ ở một bước ("Hệ thống kiểm tra, lưu, gửi mail, ghi log") → tách bước.
- Actor "Admin" quyền quá rộng, không phân biệt các vai trò admin khác nhau.

## Cách đề xuất sửa (minh họa ngắn)

Trước: `2. Hệ thống xử lý đơn hàng.`
Sau (ĐỀ XUẤT): `2. Hệ thống kiểm tra tồn kho cho từng dòng hàng (BR-012).` / `3. Hệ thống tạo đơn với trạng thái "Chờ thanh toán" và giữ tồn kho trong 15 phút (BR-013).`
Kèm hỏi: thời gian giữ tồn kho là cấu hình hay cố định?
