# Ký hiệu và ngữ nghĩa Activity Diagram (UML 2.5.1, Clause 15)

## Mục lục
1. Khung và thành phần chính
2. Action
3. Control node và ngữ nghĩa token
4. Cạnh (edge)
5. Object node, pin, parameter
6. Partition (swimlane)
7. Sự kiện và tín hiệu
8. Vùng (region), ngoại lệ, mở rộng
9. Điều kiện trước/sau, weight, guard
10. Đối chiếu với BPMN 2.0.2
11. Lỗi hay gặp về ngữ nghĩa

Điều khoản được diễn đạt lại bằng lời của người viết skill; khi cần câu chữ chính xác hãy mở PDF UML 2.5.1 (xem `standards-and-links.md`).

## 1. Khung và thành phần chính

- **Activity** là một *behavior* mô tả luồng thực thi bằng các node và edge. Vẽ trong khung có nhãn `act` (hoặc `activity`) và tên; parameter node nằm trên đường viền khung.
- **ActivityNode** gồm 3 họ: **ExecutableNode** (action), **ControlNode**, **ObjectNode**.
- **ActivityEdge** gồm **control flow** (chuyển điều khiển) và **object flow** (chuyển dữ liệu/đối tượng).
- **Ngữ nghĩa**: dựa trên **token** chạy dọc cạnh, tương tự Petri net. Control token mang quyền điều khiển, object token mang dữ liệu. Một node nhận token từ cạnh vào, thực thi, rồi cấp token ra cạnh ra.

## 2. Action

| Loại | Ký hiệu | Ghi chú |
|---|---|---|
| Action (opaque/thông thường) | Hình chữ nhật bo góc, tên bên trong | Đơn vị cơ bản; chạy khi **mọi cạnh vào** (và pin bắt buộc) đều có token |
| **Call Behavior Action** | Action có biểu tượng "rake" (ba nhánh) | Gọi một Activity/Behavior khác; dùng để phân rã |
| Call Operation Action | Action tên theo `Lớp::thaoTác` | Gọi một operation |
| **Send Signal Action** | Ngũ giác lồi (mũi nhọn ra) | Gửi tín hiệu, không chờ |
| **Accept Event Action** | Ngũ giác lõm | Chờ một sự kiện/tín hiệu |
| **Accept Time Event** | Đồng hồ cát | Chờ thời điểm hoặc khoảng thời gian |

Quy tắc ngữ nghĩa của action:
- Có **nhiều cạnh vào** thì action chỉ bắt đầu khi **tất cả** cạnh vào đều có token (ngầm là join kiểu AND). Muốn "một trong các đường dẫn tới" phải đặt **Merge** trước action.
- Sau khi xong, action cấp token cho **tất cả** cạnh ra (ngầm là fork). Muốn chọn một đường thì đặt **Decision** sau action.

## 3. Control node và ngữ nghĩa token

| Node | Ký hiệu | Ngữ nghĩa |
|---|---|---|
| **Initial Node** | Chấm tròn đặc | Điểm bắt đầu. Một activity có thể có **nhiều** initial node; khi đó gọi activity khởi động **nhiều luồng đồng thời**, mỗi initial một luồng |
| **Activity Final** | Vòng tròn chứa chấm đặc (bullseye) | Khi nhận token: **kết thúc toàn bộ activity**, mọi luồng còn lại bị dừng |
| **Flow Final** | Vòng tròn có dấu X | Chỉ **hủy token của nhánh đó**, các nhánh khác tiếp tục |
| **Decision** | Hình thoi, một cạnh vào, nhiều cạnh ra có guard | Token chỉ đi vào **một** cạnh ra có guard thỏa. Guard nên **loại trừ lẫn nhau**; chồng lấn thì kết quả không xác định. Nên có `[else]` |
| **Merge** | Hình thoi, nhiều cạnh vào, một cạnh ra | Chuyển **từng token** đến cạnh ra, **không đồng bộ** |
| **Fork** | Thanh dày, một cạnh vào, nhiều cạnh ra | **Nhân token** thành các luồng đồng thời |
| **Join** | Thanh dày, nhiều cạnh vào, một cạnh ra | **Đồng bộ**: chỉ phát token ra khi **mọi cạnh vào** đều có token (mặc định). Có thể gắn **join spec** (biểu thức điều kiện) để nới quy tắc |

Quy tắc kết hợp cần nhớ:
- **Fork → ... → Join**: cấu trúc đúng cho song song rồi đồng bộ.
- **Decision → ... → Merge**: cấu trúc đúng cho rẽ nhánh rồi hợp lại.
- **Decision → Join**: sai, chỉ một nhánh có token nên Join chờ mãi (**deadlock**).
- **Fork → Merge**: sai khi ý định là đồng bộ; phần sau Merge sẽ chạy **nhiều lần** (token nhân đôi).
- Decision và Merge có thể ghép trong một thoi, nhưng nên tách để dễ đọc.

## 4. Cạnh (edge)

- Mũi tên liền. **Guard** đặt trong ngoặc vuông `[điều kiện]` trên cạnh ra của decision (hoặc bất kỳ cạnh nào).
- **Weight** `{weight = n}`: số token tối thiểu phải có để cạnh "chuyển" (mặc định 1).
- **Connector** (vòng tròn nhỏ có nhãn) để tránh cắt đường; dùng tiết kiệm.
- Cạnh không có guard coi như guard luôn đúng.
- Object flow nối **output pin/object node → input pin/object node**.

## 5. Object node, pin, parameter

| Phần tử | Ký hiệu | Ghi chú |
|---|---|---|
| **Object node** | Hình chữ nhật, `Tên : Kiểu [trạng thái]` | Giữ token dữ liệu giữa các action; trạng thái trong `[ ]` (vd. `Đơn : Order [đã thanh toán]`) |
| **Pin** (input/output) | Ô vuông nhỏ gắn viền action | Đầu vào/ra của action; thay cho object node khi dữ liệu thuộc riêng action |
| **Central Buffer** | Object node có `<<centralBuffer>>` | Hàng đợi trung gian nhiều nguồn/nhiều đích |
| **Data Store** | `<<datastore>>` | Lưu trữ **không bị tiêu thụ** khi đọc (lưu trữ bền) |
| **Activity Parameter Node** | Object node nằm trên viền khung | Tham số vào/ra của cả activity |
| **Value pin** | Pin cho giá trị hằng | Dùng khi đầu vào cố định |

Dùng object node khi **kiểu dữ liệu và trạng thái** của nó quan trọng cho luồng (đơn "đã duyệt" mới được giao). Không vẽ object node cho mọi dữ liệu.

## 6. Partition (swimlane)

- **ActivityPartition**: nhóm các node theo **ai/cái gì chịu trách nhiệm** (người, bộ phận, hệ thống, hệ thống ngoài). Ký hiệu là các làn kẻ ngang hoặc dọc kèm tên; có thể phân cấp và nhiều chiều.
- Mỗi action **thuộc một làn** theo **chủ thể thực hiện**, không theo "chủ thể được hưởng lợi".
- Cạnh qua làn biểu diễn bàn giao trách nhiệm. Nên giữ số làn ≤ 5–6 để dễ đọc.

## 7. Sự kiện và tín hiệu

- **Accept Event Action** không có cạnh vào: được **bật khi activity (hoặc structured node chứa nó) bắt đầu** và còn hiệu lực đến khi activity chứa nó kết thúc (UML 2.5.1). Dùng để mô hình hóa "luôn lắng nghe" (vd. người dùng hủy bất kỳ lúc nào).
- Accept Event Action có cạnh vào: chỉ chờ sau khi token tới.
- **Time Event**: `sau 10 phút` (quan hệ) hoặc `lúc 08:00` (tuyệt đối); chu kỳ biểu diễn bằng time event lặp trong vòng lặp hoặc accept time event không cạnh vào cùng cạnh phản hồi.
- **Send Signal** là hành động bất đồng bộ, không chờ phản hồi; cần một Accept Event đối ứng nếu cần phản hồi.

## 8. Vùng, ngoại lệ, mở rộng

| Phần tử | Ký hiệu | Dùng khi |
|---|---|---|
| **Interruptible Activity Region** | Vùng nét đứt bo góc; **interrupting edge** (nét gấp khúc/tia chớp) đi ra khỏi vùng | "Hủy bất kỳ lúc nào": khi sự kiện ngắt xảy ra, mọi token trong vùng bị hủy và luồng đi theo cạnh ngắt |
| **Exception Handler** | Ô vuông nhỏ trên cạnh dạng tia chớp từ node được bảo vệ tới handler | Xử lý ngoại lệ có kiểu; handler thay thế phần còn lại của node bị bảo vệ |
| **Expansion Region** | Vùng nét đứt với các ô expansion node; kiểu `<<parallel>>`, `<<iterative>>`, `<<stream>>` | Áp dụng cùng một xử lý cho **từng phần tử** của một tập |
| **Structured nodes** (conditional, loop, sequence) | Khung nhãn | Cấu trúc if/vòng lặp có phạm vi; hữu ích khi mô hình hóa gần mã |

Interruptible region là cách đúng để biểu diễn **hủy/timeout phủ nhiều bước**; chỉ dùng decision lồng nhau thì dễ sót nhánh.

## 9. Điều kiện trước/sau, weight, guard

- **Precondition/Postcondition** của activity: ghi `<<precondition>>` và `<<postcondition>>` trong khung hoặc note; local pre/post cho từng action.
- Guard và ràng buộc viết bằng ngôn ngữ tự nhiên có cấu trúc hoặc OCL; ưu tiên ngắn gọn, kiểm tra được.
- **Decision input** (`<<decisionInput>>`): hành vi tính giá trị mà các guard dùng.

## 10. Đối chiếu với BPMN 2.0.2

| UML activity | BPMN 2.0.2 | Ghi chú |
|---|---|---|
| Action | Task (service, user, manual, script...) | BPMN phân loại task theo cách thực hiện |
| Call Behavior Action | Call Activity / Sub-Process | |
| Decision, Merge | Exclusive Gateway | Cặp rẽ nhánh – hợp |
| Fork, Join | Parallel Gateway | |
| (không có ký hiệu riêng) | Inclusive Gateway | UML mô phỏng bằng decision guard không loại trừ cộng join spec; kém trực quan |
| (không có) | Event-based Gateway | Rẽ nhánh theo sự kiện đến trước |
| Initial Node | Start Event (none, message, timer...) | |
| Activity Final | Terminate End Event | Kết thúc toàn bộ |
| Flow Final | None End Event (nhánh kết thúc không dừng cả quy trình) | |
| Accept Event / Time Event | Intermediate Catch Event / Timer | |
| Send Signal | Throw Event / Send Task | |
| Interruptible Region + interrupting edge | Boundary Event (interrupting) trên Sub-Process | |
| Partition | Pool và Lane; **message flow** giữa pool khác nhau | BPMN có mô hình thông điệp giữa các tổ chức |
| Object Node | Data Object / Data Store | |

Chọn BPMN khi cần: nhiều bên tham gia với message flow, boundary event, bồi hoàn (compensation), chạy trên workflow engine, nhóm business quen BPMN. Chọn UML activity khi: mô hình hành vi của phần mềm trong hệ UML sẵn có, gắn với use case/class, hoặc ở mức thuật toán.

## 11. Lỗi hay gặp về ngữ nghĩa

1. Hiểu lầm **nhiều cạnh vào một action = OR**; thực tế là AND.
2. **Decision → Join** (deadlock) và **Fork → Merge** (nhân token).
3. Decision thiếu `[else]` hoặc guard chồng lấn.
4. Dùng **Activity Final** trong nhánh song song khi chỉ muốn kết thúc nhánh đó (phải dùng **Flow Final**), hoặc ngược lại.
5. Vòng lặp không có điều kiện thoát hoặc không có lối timeout.
6. Hành động không thuộc swimlane nào hoặc thuộc sai chủ thể.
7. Dùng activity diagram để vẽ **tương tác theo thời gian** nhiều đối tượng (nên dùng sequence).
8. Quá nhiều mức chi tiết trong một sơ đồ; > 20 nút không phân rã.
9. Object node cho mọi dữ liệu nhỏ; hoặc quên object khi trạng thái dữ liệu là điều kiện của luồng.
10. Lẫn **control flow** và **object flow** (mũi tên nối pin với control).
