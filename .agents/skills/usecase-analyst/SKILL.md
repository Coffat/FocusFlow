---
name: usecase-analyst
description: Viết đặc tả use case (use case specification) và thiết kế use case diagram chuẩn UML theo góc nhìn của Senior Business Analyst / System Analyst. Dùng skill này bất cứ khi nào người dùng nhắc đến use case, usecase, đặc tả use case, use case diagram, sơ đồ use case, actor, tác nhân, luồng chính / luồng thay thế / luồng ngoại lệ, main flow, alternative flow, include/extend, phân tích yêu cầu chức năng, hoặc đưa một mô tả nghiệp vụ / SRS / user story và muốn chuyển thành use case — kể cả khi họ không nói rõ chữ "use case". Also use for "write use case spec", "draw use case diagram", "identify actors", "functional requirements to use cases".
---

# Use Case Analyst

Biến mô tả nghiệp vụ / yêu cầu thành **use case diagram** và **đặc tả use case** đúng chuẩn UML, đủ chi tiết để dev, tester và khách hàng cùng hiểu một cách. Làm việc như một senior BA: hỏi đúng chỗ, mô hình hóa theo **mục tiêu của actor** chứ không theo chức năng kỹ thuật, và tự rà soát trước khi giao.

Ngôn ngữ đầu ra: theo ngôn ngữ người dùng đang viết (mặc định tiếng Việt; giữ thuật ngữ UML tiếng Anh như `<<include>>`, `<<extend>>`, Actor, Precondition trong ngoặc khi cần).

## Khái niệm nền (phải đúng)

Use case diagram mô tả các chức năng chính của hệ thống và tương tác giữa hệ thống với môi trường bên ngoài, đại diện bởi **actor**. Actor có thể là con người, tổ chức, máy móc hoặc hệ thống bên ngoài (theo tài liệu IBM Rational/DMA về use-case diagrams, phù hợp UML 2.x).

- **System boundary (subject)**: khung chữ nhật bao các use case. Actor luôn nằm **ngoài** khung.
- **Actor**: một *vai trò* tương tác với hệ thống, không phải một người cụ thể hay chức danh phòng ban. Một người có thể đóng nhiều vai trò, một vai trò có nhiều người.
  - *Primary actor*: bắt đầu use case để đạt mục tiêu của mình.
  - *Supporting/secondary actor*: cung cấp dịch vụ cho hệ thống (cổng thanh toán, SMS gateway, hệ thống ngân hàng).
  - *Time/Timer*: dùng khi hệ thống tự kích hoạt theo lịch; ưu tiên đặt tên actor "Bộ lập lịch" hoặc ghi rõ trigger thay vì tạo actor thừa.
- **Use case**: một chuỗi hành động hệ thống thực hiện để mang lại **kết quả có giá trị quan sát được** cho một actor. Tên = *động từ + đối tượng* ("Đặt hàng", "Duyệt đơn nghỉ phép").
- **Quan hệ**:
  - Association (đường liền, không mũi tên): actor ↔ use case.
  - `<<include>>`: use case gốc **luôn** gọi use case được include; mũi tên nét đứt **từ gốc → được include**. Dùng để tách hành vi dùng chung.
  - `<<extend>>`: hành vi **tùy chọn / có điều kiện**; mũi tên nét đứt **từ use case mở rộng → use case gốc**, kèm extension point và điều kiện.
  - Generalization: nét liền, đầu tam giác rỗng, trỏ về cha. Dùng cho actor (Quản trị viên là một Người dùng) hoặc use case chuyên biệt hóa.

Chi tiết ký hiệu, mẫu PlantUML và lỗi hay gặp: `references/diagram-guide.md`.

## Quy trình

Làm tuần tự; bỏ qua bước nào đã có thông tin sẵn.

### 1. Nắm bối cảnh (hỏi tối đa 3–5 câu, gộp một lần)
Chỉ hỏi những gì thật sự chặn việc mô hình hóa: phạm vi hệ thống (subject), ai dùng hệ thống, mục tiêu nghiệp vụ chính, hệ thống bên ngoài phải tích hợp, và quy tắc nghiệp vụ quan trọng. Nếu người dùng đã đưa tài liệu, **đọc hết rồi mới hỏi**. Nếu không thể hỏi, nêu rõ giả định ở cuối ("Assumptions") và tiếp tục.

### 2. Xác định actor
Với mỗi danh từ chỉ người/hệ thống trong tài liệu, tự hỏi: *Nó có ở ngoài hệ thống không? Nó có mục tiêu riêng hoặc cung cấp dịch vụ không?* Gộp các vai trò trùng nhau, tách khi quyền/mục tiêu khác nhau. Đặt tên theo vai trò (Khách hàng, Kế toán), không theo tên người hay "User" chung chung.

### 3. Xác định use case ở mức mục tiêu người dùng
Hỏi mỗi actor: *"Bạn dùng hệ thống để đạt được điều gì?"* Mỗi câu trả lời là một ứng viên. Kiểm tra bằng **kiểm tra mức độ (size test)**: use case hoàn thành trong một lần tương tác liên tục, đem lại giá trị trọn vẹn, và actor có thể "xong việc" sau đó. Không tạo use case cho thao tác UI ("Bấm nút Lưu"), bước nội bộ ("Ghi log"), hay CRUD rời rạc khi nghiệp vụ thực chất là một mục tiêu ("Quản lý sản phẩm" có thể là một use case gộp, trừ khi từng thao tác có luồng/quy tắc khác biệt đáng kể).

### 4. Dựng quan hệ và vẽ diagram
Ưu tiên association. Chỉ dùng include/extend khi có lý do rõ (tái sử dụng thật hoặc hành vi tùy chọn thật) vì lạm dụng làm diagram thành sơ đồ phân rã chức năng. Xuất **PlantUML** (xem `references/diagram-guide.md`), kèm bảng tóm tắt actor và danh sách use case có ID. Nếu môi trường hỗ trợ render (artifact/visualize), render thêm bản trực quan; nếu không, cung cấp mã PlantUML để dán vào plantuml.com hoặc draw.io.

Giữ diagram ≤ ~12 use case mỗi hình; hệ thống lớn thì chia theo module/gói (package) và một diagram tổng quan.

### 5. Viết đặc tả cho từng use case
Dùng mẫu trong `references/spec-template.md` (có ví dụ hoàn chỉnh). Nguyên tắc cốt lõi:

- **Luồng chính (basic flow)** là kịch bản thành công thường gặp nhất, viết thành các bước đánh số, mỗi bước một câu chủ động, chủ ngữ rõ ràng ("Hệ thống…", "Khách hàng…"). Không mô tả giao diện (nút, ô nhập) trừ khi là ràng buộc; mô tả **ý định và dữ liệu trao đổi**.
- **Luồng thay thế (alternative flow)** là cách khác vẫn đạt mục tiêu; **luồng ngoại lệ (exception flow)** là lỗi/thất bại. Đánh số tham chiếu bước gốc (`3a`, `3b`) và nói rõ quay lại bước nào hoặc kết thúc ra sao.
- **Tiền điều kiện** là thứ phải đúng *trước* khi bắt đầu; **hậu điều kiện** chia thành thành công (success guarantee) và thất bại (minimal guarantee).
- **Quy tắc nghiệp vụ** đánh mã (BR-01…) và tham chiếu từ bước tương ứng thay vì nhét vào câu chữ.
- Mỗi use case gắn actor chính, actor phụ, trigger, và liệt kê include/extend khớp với diagram.
- Điều gì chưa biết thì ghi vào **Câu hỏi mở**, không tự bịa số liệu hay quy tắc.

### 6. Tự rà soát trước khi giao
Chạy `references/review-checklist.md`. Sửa lỗi trước, rồi mới trình bày. Báo cáo ngắn gọn cho người dùng: đã giả định gì, còn câu hỏi mở nào.

## Định dạng đầu ra mặc định

1. **Tóm tắt phạm vi & giả định** (3–6 dòng)
2. **Bảng actor** (Tên | Loại primary/secondary | Mô tả)
3. **Danh sách use case** (ID | Tên | Actor chính | Mục tiêu)
4. **Use case diagram** (PlantUML + hình nếu render được)
5. **Đặc tả từng use case** theo mẫu
6. **Câu hỏi mở / rủi ro**

Nếu người dùng chỉ yêu cầu một phần (chỉ diagram hoặc chỉ một spec), chỉ giao phần đó. Nếu cần file Word/Excel, dùng skill docx/xlsx để xuất; giữ nội dung đúng cấu trúc trên.

## Ví dụ ngắn

Input: "Khách hàng đặt vé xem phim online, thanh toán qua VNPay, nhân viên rạp có thể hủy suất chiếu và hệ thống hoàn tiền."

Cách nghĩ: Actor chính = Khách hàng, Nhân viên rạp; actor phụ = Cổng VNPay. Use case mục tiêu = Đặt vé, Hủy suất chiếu. "Thanh toán" là hành vi dùng chung → `Đặt vé <<include>> Thanh toán trực tuyến`; "Hoàn tiền" xảy ra khi hủy suất chiếu và có vé đã bán → `Hoàn tiền <<extend>> Hủy suất chiếu` (điều kiện: tồn tại vé đã thanh toán). Không tạo use case "Chọn ghế" hay "Nhập thẻ" riêng: đó là bước trong luồng chính.


## Vị trí lưu trữ trong dự án FocusFlow

Khi phân tích ca sử dụng hoặc cập nhật sơ đồ trong dự án FocusFlow, tuân thủ các đường dẫn sau:
- **Tài liệu yêu cầu tham chiếu**: [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
- **Tài liệu đặc tả ca sử dụng**: [`docs/uml/use-case-specifications.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md)
- **Thư mục sơ đồ PlantUML**: [`docs/uml/use-cases/`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/) (lưu các tệp `.puml`, có thể tham chiếu cấu trúc và palette tại [`docs/uml/use-cases/use-case-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml))
- **Sơ đồ Draw.io**: [`docs/uml/UC_Dia.drawio`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/UC_Dia.drawio)
