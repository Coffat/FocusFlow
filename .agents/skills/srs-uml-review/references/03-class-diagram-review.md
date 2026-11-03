# 03 — Review Class Diagram / Domain Model

Chuẩn: UML 2.5.1 (Classifier, Association, Generalization, Dependency, Realization), OCL cho invariant.

Mục lục: A. Xác định mức mô hình · B. Class & thành viên · C. Quan hệ · D. Kế thừa & interface · E. Thiết kế & chất lượng · F. Đối chiếu · G. Ký pháp

## A. Xác định mức mô hình trước khi chấm

Phân loại sơ đồ: **conceptual/domain** (nghiệp vụ, không phương thức kỹ thuật), **specification/design** (có kiểu dữ liệu, thao tác, visibility), **implementation** (sát code). Trộn lẫn các mức trong một sơ đồ là finding (CLS-A01, S3). Chỉ yêu cầu chi tiết phù hợp mức đã chọn; không bắt domain model phải có getter/setter.

## B. Class & thành viên

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| CLS-B01 | Tên class: danh từ số ít, PascalCase, có nghĩa nghiệp vụ, khớp glossary | "Data", "Manager", "Helper", "Info", "Process" | S3 |
| CLS-B02 | Thuộc tính có **kiểu**; kiểu phù hợp (tiền: Decimal/Money, không Float; thời điểm: Instant/ZonedDateTime; ID có kiểu rõ) | Thuộc tính không kiểu; `double price` | S2 |
| CLS-B03 | **Multiplicity/nullability** thuộc tính (`[0..1]`, `[1..*]`) khi cần | Không rõ bắt buộc/tùy chọn | S3 |
| CLS-B04 | Visibility (+ − # ~) hợp lý; thuộc tính thường private ở mức design | Mọi thứ public | S3 |
| CLS-B05 | **Thuộc tính dẫn xuất** ký hiệu `/` thay vì lưu trùng (tổng tiền, tuổi) | Lưu `age` cùng `dateOfBirth` | S3 |
| CLS-B06 | Static (gạch chân), abstract (in nghiêng/`{abstract}`), enumeration `<<enumeration>>` đúng ký pháp | Trạng thái là String tự do thay vì enum | S3 |
| CLS-B07 | Thao tác có tham số/kiểu trả về (mức design); tên là động từ | `process()`, `doIt()` | S3 |
| CLS-B08 | Tránh **thuộc tính khóa ngoại** trong domain model (dùng association thay vì `customerId`) | Class có `customerId` và đồng thời có association tới Customer (dư/lặp) | S3 |
| CLS-B09 | Constraint/invariant quan trọng được ghi (`{unique}`, OCL, ghi chú): `endDate ≥ startDate`, tổng dòng = tổng đơn | Quy tắc toàn vẹn chỉ nằm trong đầu | S3 |
| CLS-B10 | Class có thuộc tính/thao tác thuộc trách nhiệm khác (low cohesion), class "God" (> ~15 thuộc tính + nhiều trách nhiệm) | | S3 |
| CLS-B11 | Class rỗng, không dùng, không thuộc tập nghiệp vụ nào | | S3 |

## C. Quan hệ

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| CLS-C01 | **Multiplicity cả hai đầu** mọi association | Thiếu một hoặc cả hai đầu | S2 |
| CLS-C02 | Multiplicity đúng nghiệp vụ & khớp SRS | "1 đơn có đúng 1 sản phẩm" trong khi SRS cho nhiều dòng | S2 |
| CLS-C03 | **Navigability** (mũi tên mở) có chủ đích; hai chiều chỉ khi thật cần | Mọi quan hệ hai chiều → coupling cao | S3 |
| CLS-C04 | **Role name** khi có nhiều quan hệ giữa cùng cặp class hoặc quan hệ tự thân | `Employee` – `Employee` không nói manager/subordinate | S3 |
| CLS-C05 | **Composition** (hình thoi đặc): phần **không tồn tại độc lập**, chết theo tổng thể, mỗi phần thuộc đúng một tổng thể (multiplicity phía tổng thể = 1 hoặc 0..1) | Dùng composition cho quan hệ mà phần dùng chung/tồn tại độc lập | S2 |
| CLS-C06 | **Aggregation** (hình thoi rỗng) rất ít khi có giá trị ngữ nghĩa trong UML 2.5.1 → ưu tiên association; nếu dùng cần lý do | Aggregation mọi nơi như "has-a" | S4 |
| CLS-C07 | **Association class** cho thuộc tính thuộc về *quan hệ* (n–n có dữ liệu riêng: số lượng, ngày tham gia) | n–n không có nơi chứa thuộc tính quan hệ | S2 |
| CLS-C08 | Không có quan hệ n–n chưa giải quyết ở mức design | Chỉ vẽ n–n không rõ ánh xạ | S3 |
| CLS-C09 | **Dependency** (đứt, mũi tên mở) cho phụ thuộc tạm thời/tham số; không lạm dụng association | | S3 |
| CLS-C10 | Phụ thuộc vòng giữa package/class không cần thiết | Cycle | S3 |
| CLS-C11 | Quan hệ có tên động từ nếu giúp hiểu (`đặt`, `chứa`) và hướng đọc | | S4 |
| CLS-C12 | Thứ tự/tập hợp: `{ordered}`, `{unique}`, `{set}` khi cần | Danh sách dòng đơn cần thứ tự nhưng không ghi | S3 |

## D. Kế thừa & interface

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| CLS-D01 | Generalization thỏa **"is-a" và Liskov**: con dùng thay cha được, không từ chối/ghi đè bỏ hành vi cha | `Square extends Rectangle`; `Penguin.fly()` ném lỗi | S2 |
| CLS-D02 | Kế thừa để **tái sử dụng code** thay vì ngữ nghĩa → ưu tiên composition | | S3 |
| CLS-D03 | Độ sâu kế thừa ≤ ~3; không tạo lớp con chỉ khác một thuộc tính (dùng thuộc tính `type`/enum) | | S3 |
| CLS-D04 | Ràng buộc generalization set: `{disjoint}`/`{overlapping}`, `{complete}`/`{incomplete}` khi quan trọng; discriminator | | S3 |
| CLS-D05 | Interface `<<interface>>` + **realization** (mũi tên đứt, đầu rỗng) đúng ký pháp; không thuộc tính trong interface (trừ constant) | Dùng mũi tên kế thừa liền cho implements | S3 |
| CLS-D06 | Đa kế thừa lớp tránh nếu ngôn ngữ đích không hỗ trợ | | S3 |
| CLS-D07 | Role vs type: người thay đổi vai trò theo thời gian (khách→nhân viên) không mô hình bằng kế thừa tĩnh | `Customer` và `Employee` kế thừa `Person` nhưng một người là cả hai | S2 |

## E. Thiết kế & chất lượng

| ID | Kiểm tra | Sev |
|---|---|---|
| CLS-E01 | Aggregate/boundary rõ (nếu theo DDD): aggregate root, truy cập con qua root; không tham chiếu thẳng vào ruột aggregate khác bằng đối tượng (dùng ID) | S3 |
| CLS-E02 | Value object (Money, Address, DateRange) không bị phân mảnh thành chuỗi thuộc tính rải rác | S3 |
| CLS-E03 | Lịch sử/phiên bản/hiệu lực theo thời gian (effective dating, snapshot giá, địa chỉ giao hàng tại thời điểm đặt) được mô hình khi SRS yêu cầu | S2 |
| CLS-E04 | Soft delete, audit field (createdBy, createdAt, version) có chỗ đứng nhất quán | S3 |
| CLS-E05 | Entity vs DTO/ViewModel không lẫn một sơ đồ (nếu là design) | S3 |
| CLS-E06 | Đa tenant, đa tiền tệ, đa ngôn ngữ (i18n bảng dịch) nếu SRS yêu cầu | S2 |
| CLS-E07 | Phân quyền & dữ liệu nhạy cảm được thể hiện ở mức cần (stereotype `<<PII>>` hoặc chú thích) | S3 |
| CLS-E08 | Mẫu thiết kế dùng đúng mục đích, không "pattern cho có" | S4 |

## F. Đối chiếu bắt buộc khi có artifact khác

- Mọi danh từ nghiệp vụ chính trong SRS/UC → có class hoặc được giải thích (thuộc tính của class khác?).
- Mọi class lưu trữ → có bảng trong DB (hoặc lý do không lưu).
- Mọi `<<enumeration>>` trạng thái → trùng tập trạng thái của state diagram.
- Thao tác chính trong UC → có chủ sở hữu trách nhiệm (class/service).
- Chi tiết: `06-cross-consistency.md`.

## G. Ký pháp UML cần nhớ khi chấm (tránh chấm sai)

| Quan hệ | Đường | Đầu mũi |
|---|---|---|
| Association | liền | không/mũi mở (navigability) |
| Aggregation | liền | hình thoi **rỗng** ở phía tổng thể |
| Composition | liền | hình thoi **đặc** ở phía tổng thể |
| Generalization | liền | tam giác **rỗng** về phía cha |
| Realization | **đứt** | tam giác **rỗng** về phía interface |
| Dependency | **đứt** | mũi mở về phía được phụ thuộc |

Nếu sơ đồ dùng ký pháp khác (Crow's foot trong class diagram, Mermaid `||--o{`), hiểu theo cú pháp công cụ và chỉ flag khi **ngữ nghĩa** sai, không flag vì khác ký pháp. Khi trả về đề xuất cho Mermaid/PlantUML, dùng cú pháp của chính công cụ đó.
