# 05 — Review State Machine Diagram

Chuẩn: UML 2.5.1 State Machine (state, pseudostate, transition, region, composite state, submachine).

Mục lục: A. Cú pháp & cấu trúc · B. Trạng thái · C. Transition · D. Tính đầy đủ & xác định (completeness/determinism) · E. Cấu trúc nâng cao · F. Nghiệp vụ & đối chiếu · G. Kỹ thuật transition matrix

## A. Cú pháp & cấu trúc

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| ST-A01 | Đối tượng/vòng đời được mô hình xác định rõ (state của **cái gì**: Đơn hàng, Hồ sơ, Phiên) — một sơ đồ một thực thể | Trộn trạng thái đơn hàng và thanh toán trong một sơ đồ phẳng | S2 |
| ST-A02 | Có **đúng một initial pseudostate** (chấm đen) trong mỗi region, transition ra từ nó **không có trigger** | Nhiều initial; initial có guard/trigger | S2 |
| ST-A03 | Có final state (đích kết thúc) nếu vòng đời kết thúc; nếu không bao giờ kết thúc, ghi rõ | Vòng đời kết thúc nhưng không có final; trạng thái cuối không rõ | S3 |
| ST-A04 | Không transition **đi ra** từ final state; không transition **đi vào** initial | | S2 |
| ST-A05 | Ký pháp transition: `trigger [guard] / effect` đúng thứ tự | `[guard] trigger / effect` sai thứ tự hoặc lẫn | S3 |
| ST-A06 | Pseudostate dùng đúng: **choice** (guard đánh giá lúc rẽ), **junction** (gộp/tách tĩnh), fork/join (song song), history (H, H*), entry/exit point | Dùng diamond không nói loại | S3 |

## B. Trạng thái

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| ST-B01 | Tên state mô tả **tình trạng kéo dài** (tính từ/quá khứ phân từ/"Đang…"): "Chờ duyệt", "Đã thanh toán", "Đang giao" — không phải hành động tức thời | "Duyệt", "Thanh toán", "Gửi" | S3 |
| ST-B02 | Tên state duy nhất, nhất quán với glossary/enum/DB | "Hủy" ở sơ đồ, "Cancelled" ở DB, "Void" ở API | S2 |
| ST-B03 | Mỗi state là **bất biến có nghĩa** (điều gì luôn đúng trong state): phân biệt được hành vi/quyền/dữ liệu so với state khác | Hai state không khác gì về hành vi → gộp | S3 |
| ST-B04 | Không "bùng nổ trạng thái" do trộn các chiều độc lập (trạng thái xử lý × trạng thái thanh toán × trạng thái giao) | `Đã duyệt_Chưa TT_Chưa giao`… | S2 |
| ST-B05 | Hoạt động `entry/`, `exit/`, `do/` đặt đúng chỗ khi hành vi gắn với trạng thái | Side-effect rải ở mọi transition đi vào | S4 |
| ST-B06 | Trạng thái lỗi/treo/đang xử lý bất đồng bộ (pending, failed, timed-out, retrying) có mặt khi có tích hợp bên ngoài | Chỉ có thành công/thất bại tức thời | S2 |

## C. Transition

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| ST-C01 | Mỗi transition có **trigger** (sự kiện, hành động của actor, timeout `after(…)`, điều kiện `when(…)`), trừ completion transition | Mũi tên trần không giải thích | S2 |
| ST-C02 | Trigger là **sự kiện**, nêu ai kích hoạt (actor/quyền) hoặc hệ thống/timer | "Chuyển sang đã duyệt" không nêu ai duyệt | S2 |
| ST-C03 | **Guard** tường minh, kiểm chứng được, tham chiếu business rule | `[hợp lệ]` | S2 |
| ST-C04 | **Effect** (hành động khi chuyển): ghi log, gửi thông báo, phát sự kiện, cập nhật dữ liệu — nêu rõ nếu SRS yêu cầu | Không nói side-effect | S3 |
| ST-C05 | Transition tự thân (self-transition) phân biệt **external** (chạy exit/entry) và **internal** (không chạy) | | S4 |
| ST-C06 | Transition hủy/hoàn tác/mở lại có đủ ràng buộc; không cho "quay lại" bừa bãi trạng thái đã có hệ quả (đã thanh toán → nháp) | `Đã thanh toán → Nháp` | S2 |
| ST-C07 | Timeout có giá trị, đơn vị, điểm bắt đầu tính, ai/cái gì xử lý | "Tự động hủy nếu quá hạn" | S2 |

## D. Tính đầy đủ & xác định

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| ST-D01 | **Không trạng thái không đến được (unreachable)** từ initial | State mồ côi | S2 |
| ST-D02 | **Không trạng thái chết (dead end)**: mọi state không-final phải có ≥1 transition ra (hoặc được ghi là "treo chờ can thiệp thủ công" kèm cách xử lý) | State kẹt vĩnh viễn | S1–S2 |
| ST-D03 | Từ mỗi state không-final tồn tại đường tới final (không "live-lock"/vòng vô tận không thoát) | Vòng Retry vô hạn không giới hạn | S2 |
| ST-D04 | **Xác định (determinism)**: cùng state + cùng trigger, các guard **loại trừ lẫn nhau** | Hai transition cùng trigger, guard chồng lấn hoặc đều không guard | S1–S2 |
| ST-D05 | **Đầy đủ guard**: tập guard của cùng trigger **phủ mọi trường hợp** (hoặc có else) | `[amount ≤ 100]` và `[amount > 200]` → thiếu (100,200] | S2 |
| ST-D06 | **Sự kiện không hợp lệ ở mỗi state** được quy định: bỏ qua, từ chối với mã lỗi, hay xếp hàng (defer) | Chỉ vẽ transition hợp lệ, không nói phản ứng với phần còn lại | S2 |
| ST-D07 | Idempotency: lặp lại cùng sự kiện (webhook trùng, bấm đúp) không gây chuyển trạng thái/side-effect kép | Không nói | S2 |
| ST-D08 | Đồng thời: hai sự kiện đến cùng lúc (hủy vs thanh toán) → luật ưu tiên/khóa | Race condition không xét | S2 |

## E. Cấu trúc nâng cao

| ID | Kiểm tra | Sev |
|---|---|---|
| ST-E01 | **Composite state**: transition vào/ra đúng viền; transition của composite áp dụng cho mọi substate (ví dụ `Hủy` từ bất kỳ substate) thay vì vẽ lặp | S3 |
| ST-E02 | **Orthogonal regions** cho các chiều độc lập thật sự; đồng bộ qua fork/join/sự kiện | S3 |
| ST-E03 | **History state** (H/H*) khi cần "tiếp tục nơi dừng" (tạm dừng/tiếp tục) | S3 |
| ST-E04 | **Submachine** tái sử dụng được tham chiếu đúng | S4 |
| ST-E05 | Sơ đồ không quá lớn (> ~12–15 state phẳng) → phân cấp | S3 |

## F. Nghiệp vụ & đối chiếu

| ID | Kiểm tra | Sev |
|---|---|---|
| ST-F01 | Tập trạng thái = tập giá trị hợp lệ của cột status/enum (DB, class, API); không thừa/thiếu | S1–S2 |
| ST-F02 | Mỗi transition ↔ một UC/FR/API (ai kích hoạt, quyền); mỗi UC thay đổi trạng thái xuất hiện trong sơ đồ | S2 |
| ST-F03 | Quyền theo trạng thái: **trong trạng thái nào được sửa/xóa/xem gì** (ví dụ chỉ sửa khi Nháp) | S2 |
| ST-F04 | Trạng thái kết thúc không cho thay đổi dữ liệu (immutable) hoặc có quy trình đính chính | S2 |
| ST-F05 | Lịch sử chuyển trạng thái được lưu (ai, khi nào, từ→đến, lý do) nếu cần audit | S2 |
| ST-F06 | Thông báo/SLA gắn với thời gian ở state (quá hạn duyệt → nhắc/leo thang) khớp SRS | S3 |
| ST-F07 | Hoàn tiền/bồi hoàn/đảo bút toán: có state hoặc transition tương ứng khi nghiệp vụ tài chính | S2 |

## G. Kỹ thuật bắt buộc: dựng transition matrix

Cho DEEP/STANDARD, dựng bảng **State × Event** từ sơ đồ:

| State \ Event | submit | approve | reject | cancel | timeout | ... |
|---|---|---|---|---|---|---|
| Nháp | → Chờ duyệt | ✗ | ✗ | → Hủy | – | |
| Chờ duyệt | ✗ | [đủ quyền] → Đã duyệt | → Nháp | → Hủy | → Hết hạn | |

Ký hiệu: `→ X` chuyển tới X; `✗` bị cấm (phải rõ phản ứng); `–` bỏ qua; ô trống = **không xác định → finding ST-D06**.

Từ matrix, tính tự động:
1. State không đến được: BFS từ initial.
2. Dead end: state không-final mà hàng toàn `✗/–`.
3. Chồng guard: cùng ô có ≥2 transition.
4. Ô trống.
5. Test condition: mỗi transition hợp lệ ≥1 test; mỗi transition bị cấm (`✗`) ≥1 test âm; guard dùng BVA.

Chấm độ phủ kiểm thử gợi ý: *all states → all transitions → all transition pairs (0-switch → 1-switch)* theo rủi ro.

## Ví dụ finding mẫu

- **ST-D05 (S2, HIGH)**: Từ "Chờ duyệt", sự kiện `approve` có hai transition: `[tổng ≤ 10 triệu] → Đã duyệt` và `[tổng > 10 triệu] → Chờ giám đốc`. Giá trị đúng 10 triệu thuộc nhánh 1 (≤). Nếu SRS §4.2 nói "từ 10 triệu trở lên cần giám đốc" thì mâu thuẫn tại biên.
  *Bằng chứng*: guard trong sơ đồ; SRS BR-021. *Đề xuất*: thống nhất `[tổng < 10tr]` và `[tổng ≥ 10tr]`.
