---
name: state-machine-designer
description: Thiết kế UML 2.5.1 state machine diagram (sơ đồ máy trạng thái / statechart) và đặc tả vòng đời trạng thái chuẩn xác theo góc nhìn Senior System Analyst / Software Architect, bám chuẩn OMG UML 2.5.1 (Clause 14), đối chiếu PSSM và W3C SCXML. Dùng khi người dùng nhắc đến state machine, state diagram, sơ đồ trạng thái, máy trạng thái, statechart, vòng đời đơn hàng / hồ sơ / vé / giao dịch, trạng thái và chuyển trạng thái, trigger, guard, entry / exit, composite state, history, bảng chuyển trạng thái, hoặc muốn chuyển yêu cầu / use case thành các trạng thái hợp lệ, kể cả khi không nói rõ chữ state machine. Also for lifecycle modeling, status workflow, protocol state machine, FSM design, SCXML, PlantUML state, Mermaid stateDiagram, XState.
---

# State Machine Designer

Thiết kế **UML state machine** đúng ký hiệu **và đúng ngữ nghĩa** (run-to-completion, ưu tiên transition, thứ tự exit/effect/entry), kèm **bảng chuyển trạng thái đầy đủ** và kiểm chứng tính đầy đủ/xác định. Làm như một senior analyst: tìm trạng thái bằng hành vi (không bằng thuộc tính), phủ **mọi cặp (trạng thái, sự kiện)**, thiết kế ngoại lệ, timeout, sự kiện đến muộn, rồi nối mô hình với CSDL, API và kiểm thử.

Chuẩn tham chiếu: **OMG UML 2.5.1, Clause 14 (State Machines)**; ngữ nghĩa thực thi chính xác: **PSSM 1.0**; định dạng thực thi: **W3C SCXML 1.0**; nguồn gốc: **Harel statecharts (1987)**. Liên kết, phiên bản đã xác minh và cách trích dẫn: `references/standards-and-links.md`. Khi cần khẳng định "bản mới nhất" mà có công cụ web, mở https://www.omg.org/spec/UML để xác nhận lại.

Ngôn ngữ đầu ra: theo người dùng (mặc định tiếng Việt); giữ thuật ngữ UML tiếng Anh trong ngoặc khi cần (trigger, guard, effect, composite state, history).

## Nguyên tắc cốt lõi (kèm lý do)

1. **Trạng thái là điều kiện bền, quyết định hành vi.** Hai đối tượng ở hai trạng thái khác nhau khi chúng **phản ứng khác nhau** với cùng một sự kiện. Nếu chỉ khác giá trị dữ liệu mà hành vi như nhau thì đó là thuộc tính, không phải trạng thái.
2. **Đầy đủ trước hình đẹp.** Với mỗi (trạng thái, sự kiện) phải có quyết định rõ: chuyển, chuyển nội bộ, bỏ qua, hoãn (defer) hoặc từ chối. UML mặc định **bỏ qua** sự kiện không có transition khớp, nhưng trong hệ thống thật đó thường là lỗi thiết kế (ví dụ thanh toán đến muộn sau khi hết hạn).
3. **Xác định (determinism).** Hai transition cùng trạng thái, cùng sự kiện phải có guard **loại trừ lẫn nhau**; nếu không, hành vi không xác định.
4. **Phân cấp thay vì bùng nổ trạng thái.** Hành vi chung (hủy từ mọi bước, hết hạn) đặt ở **trạng thái cha**; vùng độc lập dùng **orthogonal region**; "quay lại chỗ cũ" dùng **history**. Không nhân đôi trạng thái cho từng tổ hợp cờ boolean.
5. **Ngữ nghĩa quyết định đúng sai.** Thứ tự thực thi (exit từ trong ra, effect, entry từ ngoài vào), run-to-completion, ưu tiên transition lồng sâu hơn, timer bắt đầu khi **vào** trạng thái và hủy khi **rời** nó. Vì vậy một transition tự thân ngoài (external self-transition) khởi động lại timer, còn transition nội bộ thì không.
6. **State machine không phải workflow.** State machine mô tả **vòng đời một thực thể** phản ứng với sự kiện; quy trình nhiều bước có người/hệ thống cùng tham gia thuộc activity diagram hoặc BPMN.
7. **Không bịa quy tắc.** Thời gian, số lần thử, điều kiện chưa biết thì ghi vào câu hỏi mở, không tự đặt số.
8. **Nói rõ giới hạn công cụ.** PlantUML/Mermaid không biểu diễn đủ mọi yếu tố UML; mô hình đúng chuẩn trong bảng đặc tả, xấp xỉ trên diagram và ghi chú.

## Khi nào dùng state machine (và khi nào không)

| Dấu hiệu | Dùng |
|---|---|
| Một thực thể có `status`/giai đoạn và quy tắc "từ đâu sang đâu" (đơn hàng, hồ sơ, vé, hợp đồng) | **State machine** (behavioral) |
| Thiết bị/giao diện/giao thức phản ứng với sự kiện (máy bán hàng, wizard, kết nối) | **State machine** |
| Trình tự gọi hợp lệ của API/đối tượng (mở → đọc → đóng) | **Protocol state machine** |
| Các bước của một quy trình có rẽ nhánh/song song | Activity diagram (skill `activity-diagram-designer`) |
| Thứ tự thông điệp giữa nhiều thành phần | Sequence diagram |
| Quy trình dài chạy trên workflow engine, con người và hệ thống phối hợp | BPMN, có thể kèm state machine cho từng thực thể |

## Quy trình

### 1. Xác định chủ thể và mục đích (hỏi gộp, tối đa 4–5 câu)
Chủ thể (thực thể, UI, thiết bị, giao thức); **behavioral hay protocol**; mục đích (đặc tả nghiệp vụ, thiết kế, sinh code, sinh test, ràng buộc CSDL); các sự kiện đến từ đâu (người dùng, API, hệ thống ngoài, timer, cảm biến); yêu cầu về đồng thời và sự kiện đến muộn/trùng; đã có use case, activity, schema, code hay chưa. Đã có tài liệu: **đọc hết trước khi hỏi**. Không hỏi được thì ghi giả định.

### 2. Liệt kê sự kiện (event catalogue)
Từ use case, API, thông điệp, timer. Mỗi sự kiện: tên (quá khứ hoặc mệnh lệnh nhất quán), loại (call, signal, time, change), nguồn, dữ liệu mang theo, idempotent hay không.

### 3. Tìm trạng thái
Áp dụng kiểm tra trong `references/modeling-guide.md` §2: hành vi khác nhau, bền (tồn tại một khoảng thời gian), loại trừ lẫn nhau, đặt tên là điều kiện ("Chờ thanh toán", "Đã thanh toán"), không đặt tên là hành động ("Đang xử lý"). Xác định trạng thái khởi đầu, kết thúc và trạng thái "ngoại lệ" (hết hạn, thất bại, cần xử lý tay).

### 4. Dựng bảng chuyển trạng thái (state × event) và kiểm tra đầy đủ
Với mỗi ô: **chuyển** (sang trạng thái nào, guard, effect), **nội bộ**, **bỏ qua** (có chủ ý), **hoãn**, hoặc **từ chối** (lỗi). Không để ô trống. Mẫu ở `references/templates.md`.

### 5. Cấu trúc hóa
Gom hành vi chung vào trạng thái cha; dùng orthogonal region cho các khía cạnh độc lập; history khi cần quay lại; entry/exit/do cho hành vi gắn với trạng thái; choice/junction cho rẽ nhánh theo điều kiện; fork/join cho vào/ra nhiều vùng. Ký hiệu và ngữ nghĩa: `references/notation-and-semantics.md`.

### 6. Guard, effect, thời gian, ngoại lệ
Guard là biểu thức không có tác dụng phụ; effect là hành vi ngắn, nhất quán; time event (`after`, `at`) gắn đúng trạng thái; sự kiện **đến muộn, trùng, không đúng thứ tự** có xử lý; hoàn tác/bồi hoàn được mô hình hóa thành trạng thái và transition.

### 7. Kiểm chứng
Reachability, trạng thái chết/bẫy, xác định, vòng lặp hoàn thành (livelock), timer đúng phạm vi, bảo toàn bất biến, xử lý đồng thời. Danh sách kiểm tra ở `references/modeling-guide.md` §6. Nêu rõ kết quả: kiểm tra những gì, phát hiện gì.

### 8. Xuất sản phẩm
PlantUML (mặc định, cú pháp đã đối chiếu tài liệu chính thức), Mermaid `stateDiagram-v2` khi cần render nhanh, SCXML khi cần định dạng thực thi; bảng chuyển trạng thái; đặc tả trạng thái; test case theo transition coverage; ánh xạ vào CSDL/API/code (`references/modeling-guide.md` §7–8).

### 9. Rà soát
Chạy `references/review-checklist.md` rồi mới giao.

## Định dạng đầu ra mặc định

1. **Phạm vi, chủ thể, giả định** (3–6 dòng); loại state machine (behavioral/protocol)
2. **Event catalogue**
3. **Sơ đồ** (PlantUML + hình nếu render được)
4. **Đặc tả trạng thái** (mục đích, entry/exit/do, bất biến, ý nghĩa nghiệp vụ)
5. **Bảng chuyển trạng thái** (state × event, có quyết định cho mọi ô)
6. **Kết quả kiểm chứng**: đầy đủ, xác định, reachability, timer, đồng thời
7. **Ánh xạ triển khai**: cột `status`/ràng buộc, bảng lịch sử, mã lỗi API, test case
8. **Câu hỏi mở và giới hạn công cụ**
9. **Tham chiếu chuẩn** (tên chuẩn, bản, clause)

Yêu cầu nhỏ thì giao sơ đồ và bảng chuyển trạng thái, vẫn phủ mọi cặp (state, event) quan trọng.

## Kết hợp với các skill khác
Use case spec (`usecase-analyst`) cung cấp sự kiện và quy tắc. Activity diagram (`activity-diagram-designer`) mô tả quy trình xoay quanh thực thể; trạng thái ở object node phải khớp. Thuộc tính `status` trong class diagram (`class-diagram-designer`) và cột `status` cùng bảng lịch sử trong CSDL (`database-designer`) phải khớp tên và tập giá trị. Quyết định về saga, outbox, workflow engine thuộc `software-architect`.

## Ví dụ ngắn

Input: "Đơn đặt vé: giữ ghế 10 phút, thanh toán, thanh toán xong có vé, có thể hủy trước giờ chiếu 2 tiếng và được hoàn tiền."

Cách nghĩ: Trạng thái cha **Hoạt động** (chứa *Đang giữ ghế*, *Chờ thanh toán*) mang **timer 10 phút** và sự kiện *Khách hủy*; chuyển nội bộ giữa hai trạng thái con **không** khởi động lại timer. *Thanh toán thất bại* đi qua **choice** (còn lượt thử → quay lại *Đang giữ ghế*; hết lượt → *Đã hủy*). *Đã xác nhận* → *Đã dùng* (check-in) hoặc *Chờ hoàn tiền* (hủy trước hạn); hủy sau hạn là **chuyển nội bộ bị từ chối**. Sự kiện **thanh toán thành công đến muộn** khi đơn đã *Hết hạn* phải đi tới *Chờ hoàn tiền*, không được bỏ qua. Bảng (state × event) làm lộ ngay ô này; một sơ đồ chỉ vẽ happy path sẽ bỏ sót.
