# Hướng dẫn mô hình hóa Activity Diagram

## Mục lục
1. Từ use case spec sang activity diagram
2. Mức trừu tượng và đặt tên
3. Mẫu luồng thường gặp
4. Song song, đồng bộ và hủy
5. Kiểm chứng ngữ nghĩa (token game và kiểm tra tĩnh)
6. Lỗi hay gặp về phương pháp
7. Liên kết với các mô hình khác

## 1. Từ use case spec sang activity diagram

| Thành phần use case spec | Phần tử activity diagram |
|---|---|
| Trigger | Initial Node (hoặc Accept Event đầu luồng) |
| Tiền điều kiện | Precondition của activity; hoặc decision đầu luồng nếu hệ thống phải kiểm tra |
| Bước trong luồng chính | Action nối tiếp trục chính |
| Bước "Hệ thống/Khách hàng ..." | Partition (làn) theo chủ ngữ |
| Luồng thay thế (vẫn đạt mục tiêu) | Nhánh của Decision rồi Merge về luồng chính |
| Luồng ngoại lệ (không đạt mục tiêu) | Nhánh kết thúc bằng Activity/Flow Final hoặc quay về bước sửa lỗi |
| Include (UC bao hàm) | Call Behavior Action |
| Extend (UC mở rộng) | Decision tại extension point, nhánh gọi Call Behavior Action |
| Hậu điều kiện thành công / thất bại | Postcondition; hoặc object node có trạng thái ở cuối luồng |
| Quy tắc nghiệp vụ BR-xx | Guard trên cạnh hoặc ghi chú gắn action, kèm mã BR |
| Dữ liệu vào/ra | Object node hoặc pin |

## 2. Mức trừu tượng và đặt tên

- **Một mức một sơ đồ**: mức nghiệp vụ ("Duyệt đơn nghỉ phép"), mức hệ thống ("Hệ thống kiểm tra số dư"), hoặc mức thuật toán. Không trộn.
- Kích thước: 5–15 action trên một sơ đồ; > 20 nút thì phân rã bằng Call Behavior Action và vẽ sơ đồ con.
- **Tên action**: động từ + đối tượng ("Kiểm tra tồn kho"), không dùng danh từ ("Tồn kho"), không mô tả UI ("Bấm nút Lưu") trừ khi UI là yêu cầu.
- **Tên guard**: mệnh đề đúng/sai ngắn (`[ghế còn]`, `[tổng > hạn mức]`); nhánh còn lại `[else]`.
- **Tên làn**: vai trò hoặc hệ thống, ổn định giữa các sơ đồ ("Khách hàng", "Hệ thống đặt vé", "Cổng thanh toán").
- Hướng đọc: trên xuống hoặc trái sang phải, nhất quán.

## 3. Mẫu luồng thường gặp

**Rẽ nhánh rồi hợp**: Decision → các nhánh → Merge. Mọi nhánh phải hợp về cùng một Merge hoặc kết thúc.

**Vòng lặp kiểm tra/sửa**: Action → Decision `[hợp lệ]` / `[không hợp lệ]` → "Yêu cầu sửa" → quay về Merge đặt trước action. Phải có lối thoát (số lần thử tối đa, người dùng hủy).

**Thử lại có giới hạn**: Decision `[lần thử < N]` → thử lại; `[else]` → ngoại lệ/ trạng thái thất bại. Ghi N ở BR, không tự đặt.

**Song song rồi tổng hợp**: Fork → các nhánh → Join → tiếp tục. Dùng khi cần **tất cả** nhánh xong.

**Song song, một trong các nhánh thắng** (race, vd. thanh toán hay timeout): hai nhánh chờ (Accept Event và Time Event) cùng đi về **Merge**, kèm cách hủy nhánh còn lại (Interruptible Region hoặc luồng hủy). Không dùng Join vì chỉ một nhánh có token.

**Duyệt nhiều cấp**: chuỗi Action + Decision `[duyệt]`/`[từ chối]`; từ chối → kết thúc hoặc quay về người nộp. Duyệt song song nhiều người: Fork → Join với join spec nếu quy tắc "đủ n trên m" (ghi rõ spec).

**Xử lý từng phần tử** của một tập (từng dòng đơn hàng): Expansion Region `<<iterative>>` hoặc `<<parallel>>`; hoặc vòng lặp với Decision `[còn phần tử]` nếu cần gần mã.

**Hủy bất kỳ lúc nào**: Interruptible Activity Region bao các bước hủy được, cạnh ngắt tới nhánh "Hủy". Hoặc Accept Event không cạnh vào ở cấp activity.

**Timeout/Escalation**: Accept Time Event song song với bước chờ người dùng; hết giờ → leo thang hoặc tự động từ chối.

**Bồi hoàn (compensation)**: ở UML ghi bằng nhánh ngoại lệ gọi Call Behavior Action "Hoàn tác..."; với quy trình dài, mô hình hóa bồi hoàn chuẩn hơn bằng BPMN.

## 4. Song song, đồng bộ và hủy

| Muốn | Dùng | Không dùng |
|---|---|---|
| Các nhánh cùng chạy và chờ đủ | Fork rồi Join | Fork rồi Merge |
| Chọn một trong nhiều đường | Decision rồi Merge | Decision rồi Join |
| Chỉ kết thúc một nhánh | Flow Final | Activity Final |
| Kết thúc toàn bộ ngay | Activity Final | Flow Final |
| Hủy nhiều bước khi có sự kiện | Interruptible Region | Chuỗi decision lặp lại ở mỗi bước |
| "Ít nhất một trong các nhánh" | Join với join spec hoặc quy tắc nghiệp vụ ghi rõ | Join mặc định (AND) |

Cẩn thận với **race condition mô hình**: hai nhánh song song cùng sửa một object cần cơ chế tuần tự hóa (ghi chú hoặc lock ở mức thiết kế), nếu không sơ đồ ngầm cho phép kết quả khác nhau.

## 5. Kiểm chứng ngữ nghĩa

### 5.1 Token game (bắt buộc)
1. Đặt một token tại mỗi Initial Node.
2. Di chuyển token: action chỉ chạy khi **mọi cạnh vào** có token; Decision gửi token tới đúng một cạnh có guard thỏa; Fork nhân token; Join chờ đủ; Merge chuyển từng token; Flow Final hủy token; Activity Final dừng tất cả.
3. Chạy tối thiểu: (a) đường thành công, (b) mỗi nhánh Decision quan trọng, (c) một ngoại lệ/timeout, (d) một đường song song nếu có.
4. Ghi kết quả vào mục "Kết quả kiểm chứng token": kịch bản, chuỗi action, trạng thái cuối (số token còn lại, loại final).

### 5.2 Kiểm tra tĩnh
- [ ] Mọi action có ≥ 1 cạnh vào và ≥ 1 cạnh ra (trừ trước final).
- [ ] Mọi Decision có `[else]` hoặc guard phủ kín; guard loại trừ lẫn nhau.
- [ ] Mỗi Fork có Join tương ứng (hoặc các nhánh kết thúc bằng Flow Final có chủ ý).
- [ ] Không có Join mà nhánh vào đến từ Decision (deadlock).
- [ ] Không có Merge sau Fork nếu cần đồng bộ (nhân token).
- [ ] Mọi vòng lặp có điều kiện thoát và lối timeout hoặc hủy.
- [ ] Mọi đường dẫn đến đúng một loại final; không còn node "treo".
- [ ] Mọi hành động chờ ngoài có đường timeout hoặc ngoại lệ.
- [ ] Mỗi action thuộc đúng một làn.
- [ ] Object node có kiểu, trạng thái (nếu liên quan) và đầu nối đúng.
- [ ] Không có "dead action" (không thể tới) hoặc nhánh không thể thoát.

### 5.3 Các thuộc tính cần nêu trong báo cáo
**Không deadlock**, **kết thúc đúng**, **không nhân token ngoài ý muốn**, **mọi nhánh có điều kiện**. Nếu không chứng minh được một thuộc tính, nói thẳng.

## 6. Lỗi hay gặp về phương pháp

1. Vẽ **flowchart một làn** rồi gọi là activity diagram: bỏ qua trách nhiệm (làn) và song song.
2. Biến sơ đồ thành **tài liệu giao diện** (từng màn hình, từng nút).
3. **Quá chi tiết**: mỗi dòng code là một action.
4. **Thiếu nhánh lỗi/hủy/timeout**: chỉ vẽ happy path.
5. **Dùng một sơ đồ cho nhiều use case** không liên quan.
6. **Điều kiện mơ hồ** ("nếu hợp lệ") mà không định nghĩa hợp lệ ở đâu.
7. **Không truy vết** về use case/BR: không biết sơ đồ phục vụ yêu cầu nào.
8. **Dùng activity diagram thay state machine**: nếu mối quan tâm là vòng đời trạng thái của một thực thể, chuyển sang state machine.
9. **Dùng thuật ngữ UML sai**: gọi mọi hình thoi là "decision" kể cả khi là merge; gọi thanh dày là "đường" mà không rõ fork hay join.

## 7. Liên kết với các mô hình khác

- **Use case spec**: nguồn luồng; mỗi activity diagram ghi UC liên quan.
- **State machine**: vòng đời đối tượng xuất hiện ở object node `[trạng thái]` phải khớp trạng thái của state machine tương ứng.
- **Sequence diagram**: nếu quan tâm thứ tự thông điệp giữa thành phần ở một bước, tách ra sequence cho bước đó.
- **Class diagram**: kiểu của object node, thao tác của Call Operation Action khớp operation đã định nghĩa.
- **Kiến trúc**: các làn hệ thống ánh xạ vào container/module; bất đồng bộ (send signal, accept event) khớp tích hợp bằng message/queue.
