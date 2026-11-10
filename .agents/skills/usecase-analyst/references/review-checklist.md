# Checklist rà soát (tự chạy trước khi giao)

## Diagram
- [ ] Mọi actor nằm ngoài system boundary, tên là vai trò.
- [ ] Mọi use case có tên "động từ + đối tượng" và đạt mục tiêu quan sát được của actor.
- [ ] Không use case mồ côi; không actor mồ côi.
- [ ] include: gốc → được include; extend: mở rộng → gốc; generalization trỏ về cha.
- [ ] Không có association giữa actor với actor.
- [ ] Hệ thống ngoài có tương tác thật đều là actor phụ.
- [ ] ID trong diagram khớp danh sách và đặc tả.
- [ ] Mỗi hình ≤ ~12 use case hoặc đã chia gói.

## Đặc tả (cho từng use case)
- [ ] Có đủ: ID, tên, mô tả, actor chính/phụ, trigger, tiền/hậu điều kiện (thành công + thất bại).
- [ ] Tiền điều kiện kiểm tra được; hậu điều kiện mô tả trạng thái, không mô tả hành động.
- [ ] Luồng chính là kịch bản thành công, bước đánh số, một chủ ngữ một hành động, không mô tả UI.
- [ ] Mọi điểm rẽ nhánh có luồng thay thế/ngoại lệ; mỗi luồng nêu rõ quay lại bước nào hoặc kết thúc.
- [ ] Các lỗi điển hình được xét: dữ liệu không hợp lệ, không đủ quyền, hệ thống ngoài không phản hồi, xung đột đồng thời, hết phiên/timeout.
- [ ] Include/extend trong đặc tả khớp diagram, có extension point + điều kiện cho extend.
- [ ] Quy tắc nghiệp vụ được đánh mã và tham chiếu từ bước.
- [ ] Không có từ mơ hồ ("xử lý", "thích hợp", "nhanh", "v.v."). Con số chưa biết nằm ở Câu hỏi mở.
- [ ] Mọi giả định đã được ghi rõ.

## Bàn giao
- [ ] Tóm tắt ngắn: phạm vi, actor, số use case, giả định chính, câu hỏi mở cần người dùng xác nhận.
