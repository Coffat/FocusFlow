# Ký hiệu và ngữ nghĩa State Machine (UML 2.5.1, Clause 14)

## Mục lục
1. Loại state machine
2. State và nội dung của state
3. Transition
4. Pseudostate và final state
5. Composite state, region, submachine
6. Ngữ nghĩa thực thi
7. Protocol state machine
8. Ánh xạ sang SCXML và PSSM
9. Lỗi hay gặp về ngữ nghĩa

Nội dung được diễn đạt lại bằng lời của người viết skill. Cần câu chữ chính xác thì mở PDF UML 2.5.1, Clause 14 (xem `standards-and-links.md`). UML nêu rằng dạng state machine của nó dựa trên biến thể hướng đối tượng của statecharts của Harel, có một số khác biệt ngữ nghĩa nhỏ.

## 1. Loại state machine

- **Behavior state machine**: mô tả hành vi của các thể hiện của một classifier (hoặc của một behavior) theo sự kiện.
- **Protocol state machine**: mô tả **trình tự hợp lệ** của các lời gọi/sự kiện (giao thức sử dụng), không có hành vi bên trong; xem §7.

Một state machine thuộc một **context** (class, component...). Gọi một operation hoặc gửi signal tới thể hiện tạo ra event occurrence mà state machine xử lý.

## 2. State và nội dung của state

Ký hiệu: hình chữ nhật bo góc, có tên và (tùy chọn) ngăn nội dung.

| Phần | Cú pháp | Ý nghĩa |
|---|---|---|
| **Entry behavior** | `entry / hành vi` | Chạy mỗi khi **vào** state |
| **Exit behavior** | `exit / hành vi` | Chạy mỗi khi **rời** state |
| **Do activity** | `do / hành vi` | Chạy **trong khi** ở state; bị hủy khi rời state; nếu xong trước sẽ phát completion event |
| **Internal transition** | `sự kiện [guard] / effect` | Phản ứng với sự kiện **mà không rời state** nên **không** chạy exit/entry |
| **Deferred event** | `sự kiện / defer` | Giữ sự kiện lại để xử lý ở state khác |

Phân loại state:
- **Simple state**: không có cấu trúc con.
- **Composite state**: chứa ≥ 1 region (xem §5).
- **Submachine state**: tham chiếu một state machine khác (như chèn vĩ mô); tương đương composite.
- **Final state**: xem §4.

## 3. Transition

Cú pháp nhãn: `trigger [guard] / effect`

| Phần | Ý nghĩa |
|---|---|
| **Trigger** | Sự kiện kích hoạt; có thể nhiều trigger ngăn cách bằng dấu phẩy |
| **Guard** | Biểu thức boolean trong `[ ]`, đánh giá khi sự kiện được xử lý; **không nên có tác dụng phụ** |
| **Effect** | Hành vi chạy khi transition được thực thi |

Loại trigger (event):
- **Call event**: gọi operation.
- **Signal event**: nhận signal.
- **Time event**: `after 10 phút` (quan hệ, đếm từ lúc **vào** state nguồn) hoặc `at (thời điểm)` (tuyệt đối).
- **Change event**: `when (biểu thức)` (khi điều kiện chuyển sang đúng).
- **Any receive**: bất kỳ sự kiện.
- **Không có trigger** (completion transition): kích hoạt khi state nguồn **hoàn thành** (do activity xong, hoặc mọi region của composite đã tới final).

Loại transition (kind):
- **External**: rời state nguồn rồi vào state đích; self-transition ngoài vẫn **exit rồi entry** state đó (kích hoạt lại entry, timer).
- **Internal**: không rời state; không exit/entry.
- **Local**: giữa composite state và state con của nó, **không** rời composite state cha.

## 4. Pseudostate và final state

| Phần tử | Ký hiệu | Ý nghĩa |
|---|---|---|
| **Initial** | Chấm đặc | Điểm bắt đầu của region; một transition ra, không trigger, có thể có effect |
| **Final state** | Vòng tròn chứa chấm đặc | Region **hoàn thành**; không phải pseudostate. Khi mọi region của composite tới final thì composite hoàn thành |
| **Terminate** | Dấu X | Hủy đối tượng sở hữu máy trạng thái; không chạy exit behavior |
| **Choice** | Hình thoi | Rẽ nhánh **động**: guard đánh giá **tại lúc tới choice**, sau khi các effect của đoạn trước đã chạy. Nên có `[else]` |
| **Junction** | Chấm tròn đặc nhỏ (merge/split của transition) | Rẽ nhánh **tĩnh**: toàn bộ guard dọc các đoạn được đánh giá **trước** khi transition xảy ra |
| **Fork** | Thanh dày, một vào nhiều ra | Chia vào nhiều region đồng thời |
| **Join** | Thanh dày, nhiều vào một ra | Hợp từ nhiều region; chỉ đi khi mọi nguồn đã sẵn sàng |
| **Shallow history (H)** | H trong vòng tròn | Nhớ **state con trực tiếp** hoạt động gần nhất của region; vào lại thì phục hồi mức đó (mức sâu hơn vào theo initial) |
| **Deep history (H*)** | H* trong vòng tròn | Nhớ **toàn bộ cấu hình** lồng nhau gần nhất |
| **Entry point / Exit point** | Vòng tròn nhỏ trên viền | Cổng vào/ra có đóng gói của composite state hoặc submachine |

History có thể có **default history transition** dùng khi region chưa từng được vào.

## 5. Composite state, region, submachine

- **Region**: vùng chứa đỉnh (vertex) và transition. Composite state có một region (**sequential/hierarchical**) hoặc nhiều region (**orthogonal**, chạy đồng thời, kẻ bằng đường nét đứt).
- Ở composite state, **một** trạng thái con hoạt động mỗi region; cấu hình hoạt động là cây các state.
- Transition khai báo ở composite state áp dụng cho **mọi** state con (hành vi chung: hủy, hết hạn).
- **Submachine state** cho phép tái sử dụng một state machine; dùng entry/exit point để nối.
- **Cẩn thận**: transition vào composite state không ghi rõ trạng thái con thì đi theo **initial** của region.

## 6. Ngữ nghĩa thực thi

1. **Event pool và run-to-completion (RTC)**: sự kiện được xếp hàng; mỗi lần xử lý **một** sự kiện đến khi **hoàn tất mọi hệ quả** (kể cả completion event nội bộ) rồi mới sang sự kiện kế. Vì vậy không có can thiệp giữa chừng trong một bước.
2. **Chọn transition**: xét các transition **có thể** (trigger khớp, guard đúng) xuất phát từ các state hoạt động. Nếu xung đột, transition của **state lồng sâu hơn** được ưu tiên (state con ghi đè state cha). Nếu nhiều transition cùng cấp mà guard chồng lấn thì **không xác định**: tránh.
3. **Không có transition nào khớp**: sự kiện bị **bỏ** (trừ khi bị defer). Đây là mặc định của UML, không phải quyết định nghiệp vụ.
4. **Thứ tự thực thi một transition external**: exit các state từ **trong ra ngoài** (tới phần chung), chạy **effect**, entry các state từ **ngoài vào trong** (tới đích, rồi theo initial/history nếu đích là composite).
5. **Time event**: bộ đếm bắt đầu khi **vào** state chứa transition và bị hủy khi rời. Self-transition ngoài đặt lại bộ đếm; transition nội bộ không.
6. **Completion event**: phát khi state hoàn thành; completion transition (không trigger) được ưu tiên xử lý trước các sự kiện khác trong pool.
7. **Orthogonal region**: một sự kiện được gửi tới **mọi** region; mỗi region có thể thực thi một transition; thứ tự giữa các region không được quy định.
8. **Defer**: sự kiện bị giữ trong pool qua các state mà nó được khai báo defer, và được xét lại khi tới state không defer nó.
9. PSSM 1.0 quy định chính xác ngữ nghĩa thực thi cho một tập con lớn của state machine UML (dùng khi cần mô phỏng/sinh code có thể kiểm chứng).

## 7. Protocol state machine

- Chỉ mô tả **thứ tự hợp lệ** của lời gọi/sự kiện; không có entry/exit/do hay effect.
- Transition dạng `[điều kiện trước] sự kiện / [điều kiện sau]`.
- State thường biểu thị trạng thái "được phép làm gì" (đã mở, đã đóng).
- Dùng để đặc tả hợp đồng sử dụng API hay đối tượng và để sinh test trình tự gọi; không mô tả cách đối tượng làm.

## 8. Ánh xạ sang SCXML và PSSM

| UML | SCXML 1.0 | Ghi chú |
|---|---|---|
| State, composite | `<state>` (có `<state>` con) | `initial` thuộc tính hoặc phần tử |
| Orthogonal regions | `<parallel>` | |
| Final | `<final>` | |
| Shallow/Deep history | `<history type="shallow\|deep">` | |
| Transition | `<transition event cond target type>` | `type="internal"` ứng với local/internal |
| Entry/Exit | `<onentry>`, `<onexit>` | |
| Time event | `<send event="..." delay="..."/>` đặt trong `onentry`, hủy bằng `<cancel>` trong `onexit` | SCXML không có `after` dựng sẵn |
| Choice/Junction | Nhiều transition có `cond`, theo thứ tự tài liệu | Transition khớp **đầu tiên theo thứ tự tài liệu** thắng |
| Dữ liệu | `<datamodel>`, `<data>`, `<assign>` | |

Hai điểm khác biệt cần nhớ: SCXML ưu tiên theo **thứ tự tài liệu** và state con trước state cha; UML mô tả xung đột bằng độ sâu lồng. Khi chuyển đổi, kiểm tra lại các transition xung đột.

## 9. Lỗi hay gặp về ngữ nghĩa

1. Dùng **self-transition ngoài** khi chỉ muốn phản ứng (nên dùng transition nội bộ), làm timer và entry bị chạy lại.
2. Đặt timer ở state con rồi chuyển qua lại giữa các state con khiến timer **khởi động lại** ngoài ý muốn; timer nghiệp vụ nên ở **state cha**.
3. Hai transition cùng sự kiện, guard chồng lấn.
4. Nhầm **choice** và **junction**: guard phụ thuộc kết quả effect của đoạn trước thì phải dùng choice.
5. Quên **initial** của composite state hoặc region.
6. Trạng thái cuối không có `[*]` hoặc tạo trạng thái không có lối ra mà không phải final (trạng thái bẫy).
7. Quên rằng sự kiện không khớp **bị bỏ**: lỗi nghiệp vụ bị nuốt im lặng.
8. Dùng history khi trạng thái nên được khởi tạo lại sạch (hoặc ngược lại).
9. Đặt hành vi dài hoặc chặn trong entry/effect làm phá vỡ run-to-completion.
10. Nhầm "completion transition" (không trigger) với "luôn chuyển ngay": nó chỉ đi khi state nguồn **hoàn thành**.
