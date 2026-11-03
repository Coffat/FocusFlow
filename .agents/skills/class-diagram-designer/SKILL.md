---
name: class-diagram-designer
description: Thiết kế UML 2 class diagram (sơ đồ lớp) chuẩn xác theo góc nhìn Senior Business Analyst / Software Architect, và viết bảng mô tả lớp (class specification / data dictionary) đi kèm. Dùng skill này bất cứ khi nào người dùng nhắc đến class diagram, sơ đồ lớp, sơ đồ class, domain model, mô hình miền, mô hình lớp phân tích, thiết kế lớp, quan hệ giữa các lớp, kế thừa, association, aggregation, composition, multiplicity, bội số, interface, abstract class, association class, hoặc muốn chuyển yêu cầu / use case / đặc tả nghiệp vụ / SRS / schema thành các lớp và quan hệ — kể cả khi họ không nói rõ chữ "class diagram". Also use for "design classes", "model the domain", "draw UML class diagram", "PlantUML class", "Mermaid classDiagram", "reverse-engineer classes from code or database".
---

# Class Diagram Designer

Tạo **UML 2 class diagram** đúng ký hiệu và đúng ý nghĩa, kèm **bảng mô tả lớp** để dev, tester, DBA và khách hàng hiểu cùng một mô hình. Ký hiệu bám theo bài "The UML 2 class diagram" của IBM Developer (Donald Bell) và đối chiếu với UML 2.5. Bài IBM chỉ dạy **ký hiệu**, không dạy chọn lớp nào để mô hình hóa; phần phương pháp nằm trong `references/modeling-guide.md`.

Ngôn ngữ đầu ra: theo ngôn ngữ người dùng (mặc định tiếng Việt). Tên lớp, thuộc tính, thao tác trong diagram dùng tiếng Anh nếu đây là mô hình sẽ đi vào code; dùng tiếng Việt nếu là mô hình nghiệp vụ cho business đọc. Hỏi hoặc suy ra từ ngữ cảnh, và giữ nhất quán trong toàn bộ mô hình.

## Nền tảng khái niệm (phải đúng)

- Class diagram là **structure diagram**: thể hiện cấu trúc tĩnh, không phụ thuộc thời gian. Trình tự, luồng, trạng thái thuộc về sequence/activity/state diagram.
- Các phần tử được vẽ là **classifier**: class, interface, data type, component (và enumeration, một dạng data type). Mọi thứ dưới đây dùng "lớp" để chỉ classifier nói chung.
- Một lớp là hình chữ nhật 3 ngăn: **tên** (bắt buộc) / **thuộc tính** / **thao tác** (hai ngăn dưới tùy chọn, bỏ bớt khi diagram chỉ nhấn vào quan hệ).
- Cú pháp thuộc tính: `visibility name : Type [multiplicity] = default`
- Cú pháp thao tác: `visibility name(param : Type, ...) : ReturnType`
- Visibility: `+` public, `#` protected, `-` private, `~` package. UML bắt buộc **xác định** visibility cho từng thành viên nhưng cho phép **không hiển thị** trên diagram.

Bảng ký hiệu đầy đủ, kể cả các chỗ bài IBM viết lỏng hoặc có lỗi in: `references/notation.md`.

## Chọn góc nhìn trước khi vẽ

Cùng một ký hiệu nhưng mức chi tiết khác nhau tùy mục đích. Xác định rõ rồi giữ nhất quán, vì trộn lẫn các mức là lỗi phổ biến nhất khiến diagram vừa rối vừa sai:

| Góc nhìn | Dùng khi | Chi tiết |
|---|---|---|
| **Conceptual / Domain** | Phân tích nghiệp vụ, làm việc với business | Khái niệm nghiệp vụ, thuộc tính theo đơn vị nghiệp vụ (Dollars, Minutes), ít hoặc không có thao tác, không có getter/setter, không kiểu kỹ thuật |
| **Specification / Design** | Thiết kế phần mềm | Interface, thao tác, visibility, navigability rõ, kiểu dữ liệu chung |
| **Implementation** | Sinh code, tài liệu hóa code có sẵn | Kiểu đúng theo ngôn ngữ, đúng với code thật |

Mặc định: nếu người dùng đưa yêu cầu nghiệp vụ → **Conceptual/Domain**; nếu đưa code hoặc nói "thiết kế" → **Specification/Design**. Nói rõ lựa chọn này trong phần giả định.

## Quy trình

### 1. Nắm bối cảnh (hỏi tối đa 3–5 câu, gộp một lần)
Phạm vi hệ thống, góc nhìn cần (domain hay design), công nghệ đích nếu là design (ngôn ngữ, ORM), các thực thể chính đã biết, quy tắc nghiệp vụ ảnh hưởng đến quan hệ (xóa cascade, một-nhiều, lịch sử). Nếu đã có tài liệu, use case spec (ví dụ từ skill `usecase-analyst`), schema hay code → **đọc hết rồi mới hỏi**. Không hỏi được thì ghi giả định và tiếp tục.

### 2. Tìm lớp ứng viên rồi lọc
Trích danh từ từ yêu cầu, luồng use case, thuật ngữ nghiệp vụ (glossary). Lọc theo các câu hỏi trong `references/modeling-guide.md` §2: có định danh/vòng đời riêng không, có thuộc tính hoặc hành vi riêng không, là actor ngoài hệ thống không, chỉ là thuộc tính của lớp khác không, có phải đồng nghĩa không.

### 3. Xác định thuộc tính và thao tác
Chỉ đưa những gì phục vụ mục đích diagram. Khóa ngoại (`customerId`) **không** là thuộc tính của lớp domain: dùng association. Không vẽ cùng một quan hệ vừa là thuộc tính vừa là association. Thao tác lấy từ trách nhiệm của lớp, bước trong use case, quy tắc nghiệp vụ; không liệt kê getter/setter.

### 4. Chọn đúng loại quan hệ
Dùng cây quyết định trong `references/modeling-guide.md` §4. Tóm tắt:

| Quan hệ | Ký hiệu | Dùng khi |
|---|---|---|
| Generalization (kế thừa) | Nét liền, tam giác rỗng trỏ về lớp cha | "A là một loại B" và A dùng được ở mọi nơi dùng B |
| Realization (hiện thực) | Nét đứt, tam giác rỗng trỏ về interface | Lớp cài đặt một interface |
| Association | Nét liền, có role + multiplicity | Các đối tượng biết nhau lâu dài |
| Uni-directional association | Nét liền + mũi tên mở trỏ về lớp được biết | Chỉ một phía cần biết phía kia |
| Aggregation | Nét liền + hình thoi **rỗng** ở phía "toàn thể" | Toàn thể – bộ phận, vòng đời bộ phận độc lập (dùng tiết kiệm) |
| Composition | Nét liền + hình thoi **đặc** ở phía "toàn thể" | Bộ phận chỉ thuộc đúng một toàn thể và bị hủy theo |
| Association class | Lớp nối bằng nét đứt vào giữa đường association | Thông tin thuộc về *mối quan hệ*, không thuộc phía nào |
| Dependency | Nét đứt + mũi tên mở, từ phụ thuộc → được phụ thuộc | Quan hệ tạm thời (tham số, biến cục bộ), không giữ tham chiếu lâu dài |

### 5. Multiplicity và role
Mọi association (trừ generalization/realization/dependency) phải có **multiplicity ở cả hai đầu**; thêm role name ở đầu có ý nghĩa. Dạng hợp lệ: `1`, `0..1`, `*` (= `0..*`), `1..*`, `3`, `0..5`, `5..15`. Hỏi theo từng chiều: "Một A có tối thiểu và tối đa bao nhiêu B?" rồi "Một B có tối thiểu và tối đa bao nhiêu A?". Không điền cho có: số nào chưa biết thì ghi vào Câu hỏi mở.

### 6. Chia gói và chia diagram
Dùng **package** để nhóm theo module hay bounded context. Mỗi diagram ≤ khoảng 15–20 lớp, mỗi diagram một chủ đề (bài IBM cũng khuyên dùng nhiều diagram theo chủ đề thay vì một diagram khổng lồ). Hệ thống lớn: một diagram tổng quan chỉ có tên lớp + quan hệ, và mỗi package một diagram chi tiết.

### 7. Xuất diagram
Mặc định **PlantUML** (mẫu và quy ước trong `references/plantuml-templates.md`). Dùng **Mermaid `classDiagram`** khi người dùng muốn render ngay trong chat hoặc Markdown, nhưng nói rõ giới hạn (không có association class chuẩn, không có internal structure). Nếu môi trường render được (artifact/visualize), render thêm bản trực quan; nếu không, cung cấp mã để dán vào plantuml.com hoặc draw.io.

### 8. Viết bảng mô tả lớp
Với mỗi lớp: mục đích, thuộc tính (tên, kiểu, bội số, mặc định, ràng buộc, ý nghĩa), thao tác (chữ ký, mô tả, tiền/hậu điều kiện nếu quan trọng), quy tắc nghiệp vụ liên quan, use case tham chiếu. Mẫu ở cuối `references/plantuml-templates.md`.

### 9. Tự rà soát rồi mới giao
Chạy `references/review-checklist.md`, sửa lỗi trước. Báo cáo ngắn: góc nhìn đã chọn, giả định, câu hỏi mở.

## Định dạng đầu ra mặc định

1. **Phạm vi, góc nhìn, giả định** (3–6 dòng)
2. **Danh sách lớp** (Lớp | Loại: class/interface/enum/abstract | Package | Mục đích)
3. **Class diagram** (mã PlantUML hoặc Mermaid + hình nếu render được)
4. **Mô tả quan hệ**: bảng các association với role và multiplicity, giải thích các quan hệ không hiển nhiên (vì sao composition, vì sao association class)
5. **Bảng mô tả lớp**
6. **Câu hỏi mở / rủi ro**

Người dùng chỉ cần diagram thì chỉ giao mục 1–3. Cần Word/Excel thì dùng skill docx/xlsx để xuất, giữ nguyên cấu trúc.

## Ví dụ ngắn

Input: "Hãng bay có chuyến bay, mỗi chuyến dùng một máy bay (có thể chưa gán). Khách hàng thân thiết tích lũy dặm theo từng chuyến bay họ đi."

Cách nghĩ: Lớp: Flight, Plane, FrequentFlyer. `Flight "0..*" -- "0..1" Plane` (role `assignedPlane`), vì một Plane có thể không có chuyến hoặc nhiều chuyến; Flight có thể chưa gán Plane. Số dặm không thuộc riêng Flight hay FrequentFlyer mà thuộc **cặp** (Flight, FrequentFlyer) → association class `MileageCredit` với thuộc tính `miles`. Không tạo `planeId` trong Flight: đó là khóa ngoại, mối quan hệ đã được biểu diễn bằng association.


## Vị trí lưu trữ trong dự án FocusFlow

Khi thiết kế và cập nhật biểu đồ lớp trong dự án FocusFlow, tuân thủ các đường dẫn sau:
- **Tài liệu thiết kế lớp**: [`docs/uml/class-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams.md)
- **Tệp sơ đồ PlantUML tập trung**: [`docs/uml/class-diagrams/class-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml)
- **Mã nguồn thực thể miền tham chiếu**: [`backend/src/domain/models/`](file:///Users/vuthang/Documents/FocusFlow/backend/src/domain/models/)
- **Tài liệu SRS tham chiếu**: [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
