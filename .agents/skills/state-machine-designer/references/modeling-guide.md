# Hướng dẫn mô hình hóa State Machine

## Mục lục
1. Khi nào một khái niệm là state machine
2. Tìm trạng thái
3. Tìm sự kiện, guard, effect
4. Cấu trúc hóa: phân cấp, vùng, history
5. Bảng chuyển trạng thái và kiểm tra đầy đủ
6. Kiểm chứng
7. Ánh xạ vào CSDL, API, mã nguồn
8. Kiểm thử
9. Lỗi hay gặp về phương pháp

## 1. Khi nào một khái niệm là state machine

Dấu hiệu tốt: thực thể có vòng đời; có quy tắc "chỉ được làm X khi ở trạng thái Y"; cùng một lệnh cho kết quả khác nhau theo trạng thái; có timer/hết hạn; nhiều hệ thống gửi sự kiện đến không đúng thứ tự. Nếu chỉ có một chuỗi bước tuyến tính do một tác nhân thực hiện, thường là activity diagram. Vòng đời nên mô hình riêng cho **từng thực thể có vòng đời độc lập** (đơn hàng, thanh toán, vé) thay vì một máy trạng thái "thần" cho cả hệ thống.

## 2. Tìm trạng thái

Với mỗi trạng thái ứng viên, kiểm tra:
1. **Hành vi khác**: nó chấp nhận hoặc từ chối sự kiện khác với các trạng thái khác không? Nếu không → có thể là thuộc tính.
2. **Bền**: tồn tại một khoảng thời gian đáng kể (chờ sự kiện bên ngoài), không phải một bước xử lý tức thời.
3. **Loại trừ lẫn nhau** trong cùng một region.
4. **Đặt tên là điều kiện**: "Chờ thanh toán", "Đã duyệt", "Hết hạn", không đặt tên là hành động ("Đang xử lý", "Tính toán"). Tên hành động thường là dấu hiệu của activity bị nhét vào state machine.
5. **Có lối ra** (trừ trạng thái cuối) và **có lối vào**.
6. Có **bất biến** (điều luôn đúng ở trạng thái này), ví dụ "Đã xác nhận ⇒ có mã thanh toán".

Nguồn tìm trạng thái: giá trị `status` hiện có, nhãn trên giao diện, các cụm "khi X xong thì ...", các thông báo lỗi "không thể ... khi đang ...", trạng thái ở object node của activity diagram, bảng tra cứu trạng thái trong CSDL.

Trạng thái thường bị bỏ sót: **Hết hạn/Timeout**, **Thất bại/Cần xử lý tay**, **Đang hoàn tiền/Hoàn tiền thất bại**, **Đã hủy** (khác **Hết hạn**), **Tạm dừng**, **Đã lưu trữ/Đóng**.

Tránh bùng nổ: nếu có `n` cờ boolean độc lập thì không tạo 2ⁿ trạng thái; dùng orthogonal region hoặc tách thành các state machine riêng.

## 3. Tìm sự kiện, guard, effect

**Event catalogue** cho từng sự kiện: tên, loại (call/signal/time/change), nguồn, dữ liệu, **idempotent không**, điều gì xảy ra nếu đến muộn hoặc trùng.

- Đặt tên sự kiện nhất quán: sự việc đã xảy ra (`paymentSucceeded`, `holdExpired`) hoặc lệnh (`cancel`, `checkIn`); chọn một kiểu cho cả mô hình.
- **Guard**: điều kiện kiểm tra được, không tác dụng phụ (`[trước hạn hủy]`, `[số lần thử < N]`). Giá trị N, ngưỡng lấy từ BR; chưa biết thì ghi câu hỏi mở.
- **Effect**: hành vi ngắn, có thể thực hiện trong một giao dịch; việc dài/ngoài hệ thống tách thành sự kiện tiếp theo (gửi yêu cầu → chờ sự kiện kết quả).
- **Sự kiện do chính máy sinh ra** (gửi signal tới chính mình) nên hạn chế.

## 4. Cấu trúc hóa: phân cấp, vùng, history

- **Hành vi chung → trạng thái cha**: "Hủy được ở mọi bước trước khi xác nhận" đặt một transition ở cha thay vì lặp ở mọi state con.
- **Timer nghiệp vụ → trạng thái cha**: thời gian giữ ghế 10 phút đặt `after 10 phút` ở cha *Hoạt động* để chuyển giữa các con không làm timer khởi động lại.
- **Orthogonal region** khi có hai khía cạnh thực sự độc lập (trạng thái thanh toán và trạng thái giao hàng); nếu chúng phụ thuộc nhau chặt thì dùng một region với trạng thái tổ hợp có tên rõ.
- **History** khi cần "tiếp tục từ chỗ dừng" (tạm dừng/tiếp tục). Chọn shallow hay deep có chủ đích.
- **Submachine** khi một vòng đời con tái sử dụng ở nhiều nơi (quy trình thanh toán).
- **Entry/exit** cho hành vi luôn xảy ra khi vào/ra trạng thái (khởi động/hủy timer, giữ/nhả tài nguyên) để không phải lặp trên mọi transition.

## 5. Bảng chuyển trạng thái và kiểm tra đầy đủ

Bảng ma trận trạng thái × sự kiện (mỗi ô một quyết định):

| Ký hiệu ô | Ý nghĩa |
|---|---|
| `→ S [guard] / effect` | Chuyển sang S |
| `∘ [guard] / effect` | Chuyển nội bộ (không rời trạng thái) |
| `—` (có lý do) | **Bỏ qua có chủ ý** (an toàn khi sự kiện trùng/muộn vô hại) |
| `⧖` | **Hoãn** (defer) |
| `✗` | **Từ chối/lỗi** (trả mã lỗi, ghi log, không đổi trạng thái) |

Quy tắc kiểm tra:
- **Không ô trống.** Mỗi ô một ký hiệu; ô `—` phải ghi lý do.
- Các transition cùng ô có guard **loại trừ** và phủ kín (hoặc có `[else]`).
- Mỗi sự kiện của event catalogue xuất hiện ở ít nhất một trạng thái; mỗi trạng thái nhận ít nhất một sự kiện (trừ final).
- Hàng của trạng thái cuối: mọi sự kiện muộn đều có quyết định (thường `✗` hoặc `—`, đôi khi bồi hoàn).
- Hàng của trạng thái **hết hạn/hủy**: xét **sự kiện đến muộn** từ hệ thống ngoài (thanh toán thành công, webhook).

Phân loại ô trống thường gặp để hỏi người dùng: "nếu A xảy ra khi đang ở B thì sao?" Câu trả lời là quy tắc nghiệp vụ hoặc một transition mới.

## 6. Kiểm chứng

- [ ] **Reachability**: mọi state tới được từ initial (duyệt đồ thị).
- [ ] **Không trạng thái chết/bẫy**: mọi state không-final có ít nhất một transition ra hoạt động được; không có tập state kín không thoát trừ khi có chủ ý.
- [ ] **Xác định**: không cặp (state, event) nào có hai transition guard chồng lấn.
- [ ] **Đầy đủ**: bảng không ô trống.
- [ ] **Timer**: mỗi time event gắn đúng state; hành vi khi rời state (hủy timer) đúng; không bị reset ngoài ý muốn.
- [ ] **Completion/livelock**: không có chuỗi completion transition quay vòng vô hạn.
- [ ] **Bất biến**: mỗi state có bất biến, mỗi transition giữ/thiết lập đúng bất biến.
- [ ] **Đồng thời**: hai sự kiện đến gần nhau (thanh toán thành công và hết hạn cùng lúc) cho kết quả xác định; có cơ chế tuần tự hóa (khóa, version) hoặc quy tắc ưu tiên rõ ràng.
- [ ] **Idempotent**: sự kiện lặp (webhook gửi lại) cho cùng kết quả.
- [ ] **Hoàn tác**: mọi hành vi có tác dụng ngoài (giữ tiền, giữ ghế) có transition bồi hoàn khi đường đi thất bại.

Với máy trạng thái quan trọng, có thể kiểm chứng tự động bằng model checker (liệt kê cặp đến trạng thái, kiểm tra thuộc tính an toàn như "không tới Đã dùng nếu chưa Đã thanh toán"); nêu rõ nếu chưa làm.

## 7. Ánh xạ vào CSDL, API, mã nguồn

**CSDL** (xem `database-designer`):
- Cột `status` kiểu chuỗi ngắn có nghĩa kèm `CHECK (status IN (...))` hoặc FK tới bảng trạng thái; tên và tập giá trị khớp state machine.
- Bảng lịch sử `<thực_thể>_status_history(thực_thể_id, from_status, to_status, event, changed_at, changed_by, reason)` append-only khi cần kiểm toán.
- Bảng `allowed_transitions(from_status, event, to_status)` khi muốn cấu hình hóa; hoặc giữ bảng chuyển trong mã (đơn giản hơn) và kiểm thử.
- **Optimistic locking** (`version`) để hai sự kiện đồng thời không cùng chuyển; chuyển trạng thái bằng `UPDATE ... SET status = :to WHERE id = :id AND status = :from` (cập nhật có điều kiện) và kiểm tra số hàng bị ảnh hưởng.
- Cột thời gian tương ứng với timer (`hold_expires_at`) và job quét/lập lịch; không dựa vào bộ nhớ.

**API**:
- Mỗi sự kiện/lệnh là một endpoint hoặc một giá trị hành động; chuyển không hợp lệ trả **409 Conflict** (kèm trạng thái hiện tại) hoặc 422 tùy quy ước; không trả 200 im lặng.
- Hành động có thể gọi lại cần **idempotency key**.
- Phản hồi nêu trạng thái mới và các hành động hợp lệ tiếp theo.

**Mã nguồn**:
- Cách đơn giản: `enum` trạng thái + bảng chuyển (map `(state, event) → handler`) + hàm guard; một nơi duy nhất thay đổi trạng thái.
- Mẫu State (GoF) khi mỗi trạng thái có hành vi riêng phức tạp.
- Thư viện statechart (ví dụ XState, thư viện SCXML) khi cần phân cấp, vùng song song, history; xuất cấu hình từ mô hình.
- Mọi thay đổi trạng thái và sự kiện phát ra (event) trong **một giao dịch**; dùng **transactional outbox** cho sự kiện gửi ra ngoài (xem `software-architect`).
- Không để ứng dụng khác ghi trực tiếp vào cột `status`.

## 8. Kiểm thử

- **State coverage**: mỗi state được tới ít nhất một lần.
- **Transition coverage** (tối thiểu): mỗi transition chạy ít nhất một lần, kể cả các nhánh guard.
- **Negative coverage**: mỗi ô `✗` có test xác nhận bị từ chối và **không đổi** trạng thái.
- **Sự kiện đến muộn/trùng/ngược thứ tự**: test riêng cho từng trạng thái cuối và trạng thái hết hạn.
- **Time**: dùng đồng hồ giả để test `after`/`at`; test rằng timer **bị hủy** khi rời state.
- **Chuỗi (N-switch)**: với đường nguy hiểm (hủy sau thanh toán, hoàn tiền thất bại rồi thử lại) kiểm tra chuỗi hai–ba chuyển liên tiếp.
- **Thuộc tính/bất biến**: sinh ngẫu nhiên chuỗi sự kiện hợp lệ và kiểm tra bất biến sau mỗi bước.
- Sinh test từ bảng chuyển trạng thái để bảng và mã không lệch nhau.

## 9. Lỗi hay gặp về phương pháp

1. **Chỉ vẽ happy path**; bỏ hết hết hạn, thất bại, sự kiện muộn.
2. **Biến state machine thành workflow**: trạng thái tên là động từ/bước ("Gửi email", "Tính tiền").
3. **God state machine** cho cả hệ thống; thiếu tách theo thực thể.
4. **Cờ boolean song song** thay vì region hoặc trạng thái rõ ràng.
5. **Trạng thái trùng ý** ("Hủy", "Đã hủy", "Cancelled") không thống nhất giữa diagram, DB và API.
6. **Transition không có sự kiện** (completion) dùng bừa để "chạy tiếp" dẫn tới vòng lặp ẩn.
7. **Guard có tác dụng phụ** hoặc phụ thuộc dữ liệu ngoài không ổn định.
8. **Effect chứa việc dài/ngoài hệ thống** làm giao dịch kéo dài.
9. **Không có trạng thái cuối** hoặc nhiều "trạng thái cuối" tương đương không phân biệt (thành công/thất bại).
10. **Timer đặt sai phạm vi** (state con thay vì state cha), hoặc không có cơ chế thực thi timer thực tế (job/scheduler).
11. Không đồng bộ giữa state machine và **activity diagram / use case / DB**.
