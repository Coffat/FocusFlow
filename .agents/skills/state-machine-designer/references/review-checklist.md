# Checklist rà soát State Machine (tự chạy trước khi giao)

## Phạm vi và chủ thể
- [ ] Chủ thể (thực thể/UI/thiết bị/giao thức) và loại (behavioral/protocol) được nêu; state machine là loại sơ đồ phù hợp (không phải activity/BPMN).
- [ ] Mỗi thực thể có vòng đời độc lập có state machine riêng; không "máy thần".
- [ ] Giả định và câu hỏi mở được ghi, không bịa số/quy tắc.

## Trạng thái
- [ ] Mỗi trạng thái có hành vi khác biệt, bền, loại trừ trong region; đặt tên là điều kiện.
- [ ] Có initial, và final phân biệt rõ kết quả (thành công, thất bại, hủy).
- [ ] Đã xét Hết hạn, Thất bại/Cần xử lý tay, Hoàn tác/Hoàn tiền, Đã hủy.
- [ ] Không bùng nổ do cờ boolean; dùng phân cấp, region, history đúng chỗ.
- [ ] Mỗi trạng thái có bất biến.

## Transition và ngữ nghĩa
- [ ] Nhãn `trigger [guard] / effect` đầy đủ; guard không tác dụng phụ.
- [ ] Guard của các transition cùng (state, event) loại trừ nhau và phủ kín (có `[else]`).
- [ ] Choice vs junction chọn đúng; mọi choice có `[else]`.
- [ ] Phân biệt transition ngoài, nội bộ, local; self-transition ngoài chỉ khi cần exit/entry.
- [ ] Timer đặt đúng phạm vi (state cha khi là timer nghiệp vụ), bị hủy khi rời state.
- [ ] Thứ tự exit, effect, entry hiểu đúng; effect ngắn, trong một giao dịch.
- [ ] Hành vi chung đặt ở state cha; transition từ state con ưu tiên đúng.

## Đầy đủ và kiểm chứng
- [ ] Ma trận state × event không ô trống; ô bỏ qua có lý do.
- [ ] Sự kiện đến muộn, trùng, ngược thứ tự có xử lý (đặc biệt ở trạng thái hết hạn/cuối).
- [ ] Reachability, không trạng thái chết/bẫy, không livelock completion.
- [ ] Đồng thời: có cơ chế tuần tự hóa (version/khóa/ưu tiên) cho sự kiện cùng lúc.
- [ ] Idempotent cho sự kiện có thể gọi lại; hành vi hoàn tác có transition.

## Ánh xạ triển khai
- [ ] Tên và tập giá trị trạng thái khớp diagram, bảng, DB (`status` + CHECK/lookup), API, activity diagram.
- [ ] Chuyển không hợp lệ trả lỗi rõ (409/422), không im lặng.
- [ ] Bảng lịch sử/audit khi cần; cập nhật trạng thái có điều kiện hoặc version.
- [ ] Test case phủ transition coverage, negative coverage, timer, sự kiện muộn.

## Đầu ra và nguồn
- [ ] Event catalogue, đặc tả trạng thái, bảng chuyển, ma trận, test case khớp với sơ đồ.
- [ ] Mã PlantUML/Mermaid/SCXML đã render thử hoặc ghi rõ chưa kiểm tra; giới hạn công cụ được nêu.
- [ ] Tham chiếu chuẩn nêu đúng bản (UML 2.5.1, Clause 14; PSSM 1.0; SCXML 1.0) và không chép dài nguyên văn.
- [ ] Nếu khẳng định "bản mới nhất", đã kiểm tra lại hoặc ghi rõ ngày/nguồn xác minh.
