# Checklist rà soát Activity Diagram (tự chạy trước khi giao)

## Chọn loại và phạm vi
- [ ] Activity diagram là loại sơ đồ phù hợp (không phải sequence, state machine hay BPMN); đã nêu lý do.
- [ ] Phạm vi, sự kiện bắt đầu, kết quả, các bên tham gia và mức trừu tượng được nêu.
- [ ] Giả định và câu hỏi mở được ghi, không bịa quy tắc/số liệu.

## Ký hiệu
- [ ] Initial, action, decision, merge, fork, join, final dùng đúng ký hiệu và đúng vai trò.
- [ ] Activity Final và Flow Final dùng đúng (kết thúc toàn bộ vs một nhánh).
- [ ] Guard trong `[ ]`, có `[else]`, loại trừ lẫn nhau.
- [ ] Action đặt tên động từ + đối tượng; không mô tả UI vụn.
- [ ] Mỗi action thuộc đúng một swimlane theo chủ thể thực hiện.
- [ ] Object node có kiểu và trạng thái khi cần; control flow và object flow không lẫn.

## Ngữ nghĩa (token)
- [ ] Không có decision → join; không có fork → merge ngoài ý muốn.
- [ ] Cạnh vào nhiều của action đã được hiểu là AND; đặt Merge nếu muốn OR.
- [ ] Mọi vòng lặp có lối thoát; mọi hành động chờ ngoài có timeout hoặc ngoại lệ.
- [ ] Mọi đường đi đều kết thúc đúng; không node treo hoặc action không thể tới.
- [ ] Đã mô phỏng token cho ≥ 2–4 kịch bản (thành công, rẽ nhánh, ngoại lệ, song song) và ghi kết quả.
- [ ] Hủy/ngắt nhiều bước dùng interruptible region (hoặc ghi chú tương đương), không nhân bản decision.

## Mô hình hóa
- [ ] 5–15 action mỗi sơ đồ; hơn thế đã phân rã bằng call behavior action.
- [ ] Truy vết về use case và quy tắc nghiệp vụ (BR-xx).
- [ ] Trạng thái đối tượng ở object node khớp state machine liên quan.
- [ ] Các giới hạn công cụ (pin, region, exception handler không vẽ được) đã nêu và có ghi chú.

## Đầu ra và nguồn
- [ ] Mã PlantUML dùng cú pháp mới; `if/endif`, `fork/end fork`, `;` đủ; đã render thử hoặc ghi rõ chưa kiểm tra.
- [ ] Bảng đặc tả khớp từng nút trong sơ đồ (ID, tên, làn).
- [ ] Tham chiếu chuẩn nêu đúng bản (UML 2.5.1, Clause 15) và không chép dài nguyên văn.
- [ ] Nếu khẳng định "bản mới nhất", đã kiểm tra lại hoặc ghi rõ ngày/nguồn xác minh.
