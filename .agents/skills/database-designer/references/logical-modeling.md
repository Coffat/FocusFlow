# Mô hình hóa logic: ERD, ánh xạ, chuẩn hóa

## Mục lục
1. Thực thể, thuộc tính, quan hệ
2. Bội số (cardinality) và tính tùy chọn (optionality)
3. Quy tắc ánh xạ sang bảng (gồm từ class diagram)
4. Supertype / subtype
5. Chuẩn hóa
6. Phi chuẩn hóa có chủ đích
7. Lỗi hay gặp

## 1. Thực thể, thuộc tính, quan hệ

- **Thực thể**: thứ nghiệp vụ cần ghi nhận và phân biệt được từng cá thể (Customer, Order). Tên là danh từ số ít.
- **Thực thể yếu**: không tự định danh được, phụ thuộc thực thể cha (OrderItem phụ thuộc Order). PK gồm khóa cha + số thứ tự/khóa riêng.
- **Thuộc tính**: dữ kiện đơn trị về thực thể. Thuộc tính đa trị → bảng riêng (hoặc kiểu mảng/JSON nếu không cần ràng buộc, xem `patterns.md`). Thuộc tính suy diễn được (tuổi từ ngày sinh) thường **không lưu**.
- **Quan hệ**: mối liên kết giữa thực thể, có tên động từ ("Customer đặt Order").
- Ký hiệu ERD thông dụng: Chen, **Crow's foot** (khuyến nghị cho trao đổi với dev/DBA), IDEF1X. Mặc định dùng crow's foot (Mermaid `erDiagram` dùng ký hiệu này).

## 2. Bội số và tính tùy chọn

Hỏi **hai chiều**, mỗi chiều hai câu: tối thiểu bao nhiêu (0 hay 1) và tối đa bao nhiêu (1 hay nhiều).

| Crow's foot (Mermaid) | Nghĩa |
|---|---|
| `\|\|` | đúng một |
| `\|o` | không hoặc một |
| `}o` | không hoặc nhiều |
| `}\|` | một hoặc nhiều |

Cận **tối thiểu = 1** ở phía FK nghĩa là cột FK `NOT NULL`. Cận **tối đa = 1** ở phía "một" của 1–1 nghĩa là FK có `UNIQUE`.

Quan hệ **định danh** (identifying: khóa cha nằm trong PK con, Mermaid `--`) và **không định danh** (non-identifying, `..`).

## 3. Quy tắc ánh xạ sang bảng

| Mô hình | Ánh xạ quan hệ |
|---|---|
| Thực thể / class | 1 bảng; thuộc tính → cột |
| **1–N** | FK ở bảng phía "N" trỏ tới PK phía "1"; `NOT NULL` nếu tối thiểu là 1 |
| **1–1** | FK + `UNIQUE` ở bảng phụ thuộc/tùy chọn; hoặc **dùng chung PK** (PK của bảng con cũng là FK tới cha) khi con luôn gắn với cha. Nếu cả hai bắt buộc và luôn cùng vòng đời, cân nhắc gộp bảng |
| **N–N** | **Bảng nối (junction)** với FK tới hai bảng; PK tổ hợp `(a_id, b_id)` nếu mỗi cặp chỉ một lần, hoặc surrogate PK + `UNIQUE (a_id, b_id)` |
| **Association class** (UML) / thuộc tính của quan hệ | Chính là bảng nối, thêm các cột của association class |
| **Cặp có thể lặp** (cùng A–B nhiều bản ghi: nhiều giao dịch) | Bảng thường có surrogate PK, hai FK `1–N`; không dùng PK tổ hợp `(a_id, b_id)` |
| **Ba ngôi** (A–B–C cùng tham gia) | Một bảng nối ba FK; kiểm tra phụ thuộc hàm để biết khóa là tổ hợp nào, và xem có tách được thành các nhị ngôi không (4NF/5NF) |
| **Đệ quy** (nhân viên–quản lý, danh mục cha–con) | FK tự tham chiếu `parent_id` (nullable cho gốc); N–N đệ quy dùng bảng nối |
| **Composition** (UML thoi đặc) | FK `NOT NULL` + `ON DELETE CASCADE`; thường PK tổ hợp hoặc surrogate |
| **Aggregation** (thoi rỗng) / association | FK, `ON DELETE RESTRICT` hoặc `SET NULL` tùy bội số |
| **Enumeration** | Bảng tra cứu (lookup) khi giá trị thay đổi/có thuộc tính/cần đa ngôn ngữ; hoặc `CHECK (col IN (...))` / kiểu `ENUM` khi tập nhỏ, ổn định (xem `patterns.md`) |
| **Data type có cấu trúc** (Money, Address) | Nhiều cột có tiền tố, hoặc bảng riêng nếu có vòng đời riêng |
| **Thuộc tính đa trị** | Bảng con (1–N) |
| **Derived attribute** | Không lưu; dùng view hoặc generated column |

Truy vết: mỗi bảng ghi nguồn (lớp/entity/use case) để review được.

## 4. Supertype / subtype (kế thừa)

Ba chiến lược; chọn dựa trên truy vấn và ràng buộc:

| Chiến lược | Cấu trúc | Ưu | Nhược | Dùng khi |
|---|---|---|---|---|
| **Một bảng (single table)** | Mọi lớp con trong 1 bảng + cột `type` | Truy vấn đa hình đơn giản, không join | Nhiều cột NULL; khó ép `NOT NULL`; phải dùng `CHECK` theo `type` | Ít lớp con, ít thuộc tính riêng |
| **Bảng theo lớp (class table / joined)** | Bảng cha + bảng con (PK con = FK cha) | Chuẩn hóa, ràng buộc chính xác, FK trỏ tới cha được | Cần join; ghi nhiều bảng | Lớp con có thuộc tính riêng đáng kể (mặc định tốt) |
| **Bảng theo lớp cụ thể (concrete table)** | Mỗi lớp cụ thể một bảng chứa cả thuộc tính cha | Truy vấn một lớp không join | Truy vấn đa hình cần `UNION`; **không có FK chung tới "cha"**; trùng cấu trúc | Lớp con tách biệt, ít truy vấn đa hình |

Với single table, thêm CHECK để thuộc tính riêng của loại nào chỉ có giá trị khi đúng loại. Nếu thuộc "vai trò thay đổi theo thời gian" (một người vừa là khách vừa là nhân viên), **không dùng kế thừa**; dùng bảng vai trò liên kết tới `party`/`person`.

## 5. Chuẩn hóa

Phụ thuộc hàm `X → Y`: biết X xác định duy nhất Y. Bắt đầu bằng việc **liệt kê các phụ thuộc hàm** từ nghiệp vụ, không đoán từ dữ liệu mẫu.

| Dạng | Điều kiện | Vi phạm điển hình → cách sửa |
|---|---|---|
| **1NF** | Giá trị nguyên tử; không nhóm lặp; có khóa; thứ tự hàng/cột không mang nghĩa | `phones = "090.., 091.."` hoặc `phone1, phone2, phone3` → bảng con `customer_phones` |
| **2NF** | 1NF + mọi thuộc tính không-khóa phụ thuộc vào **toàn bộ** khóa ứng viên (không phụ thuộc một phần khóa tổ hợp) | `order_items(order_id, product_id, product_name)`: `product_name` chỉ phụ thuộc `product_id` → chuyển sang `products` |
| **3NF** | 2NF + thuộc tính không-khóa không phụ thuộc **bắc cầu** vào khóa (không-khóa → không-khóa) | `orders(order_id, customer_id, customer_city)`: `customer_id → customer_city` → chuyển `customer_city` sang `customers` |
| **BCNF** | Mọi **định thức** (vế trái của phụ thuộc hàm không tầm thường) là khóa ứng viên | `enrollment(student, course, teacher)` với `teacher → course` → tách `teacher_course(teacher, course)` và `enrollment(student, teacher)` |
| **4NF** | BCNF + không có phụ thuộc đa trị không tầm thường ngoài siêu khóa | `person_skill_language(person, skill, language)` với kỹ năng và ngôn ngữ độc lập → tách `person_skill`, `person_language` |
| **5NF** | Mọi phụ thuộc nối (join dependency) được suy ra từ khóa ứng viên | Hiếm; gặp ở quan hệ ba ngôi thật sự có thể tách thành ba nhị ngôi mà không mất thông tin |

Quy tắc nhớ cho 3NF: mọi thuộc tính không-khóa "phụ thuộc vào khóa, toàn bộ khóa, và không gì ngoài khóa". 3NF luôn đạt được mà **không mất thông tin và bảo toàn phụ thuộc**; BCNF luôn đạt được không mất thông tin nhưng đôi khi **không bảo toàn được mọi phụ thuộc hàm** bằng khóa. Khi đó chọn 3NF và ép phần còn lại bằng ràng buộc bổ sung, rồi ghi chú.

Quy trình thực hành: (1) liệt kê thuộc tính và phụ thuộc hàm; (2) tìm khóa ứng viên; (3) kiểm từng dạng theo thứ tự; (4) tách bằng phép chiếu **không mất thông tin** (nối lại cho ra đúng bảng gốc); (5) kiểm tra bảo toàn phụ thuộc.

## 6. Phi chuẩn hóa có chủ đích

Chỉ khi có bằng chứng (truy vấn nóng, số đo, khối lượng) và đã thử cách rẻ hơn trước: index phù hợp, view, materialized view, bảng tóm tắt, cache. Các dạng hợp lệ:

- **Snapshot lịch sử**: `order_items.unit_price`, `invoices.customer_name_at_issue`, địa chỉ giao hàng sao chép vào đơn. Đây là *dữ kiện tại thời điểm giao dịch*, không phải trùng lặp.
- **Cột tính sẵn** (tổng đơn, số lượng tồn): giữ nhất quán bằng generated column (khi cùng hàng), trigger, hoặc cập nhật trong cùng transaction; ghi rõ cơ chế và cách đối soát.
- **Bảng tóm tắt/báo cáo** làm mới theo lịch hoặc theo sự kiện.
- **Kho dữ liệu phân tích**: lược đồ sao (star), snowflake; fact và dimension; khóa thay thế và slowly changing dimension. Đây là thiết kế OLAP khác với OLTP, nói rõ khi chuyển.

Mỗi phi chuẩn hóa phải ghi: **lý do, truy vấn hưởng lợi, cơ chế đồng bộ, rủi ro lệch dữ liệu**.

## 7. Lỗi hay gặp

1. Bảng "thần": một bảng chứa nhiều khái niệm (`master_data` với cột `type`).
2. Lưu danh sách trong một cột (CSV trong chuỗi) khi cần truy vấn/ràng buộc theo phần tử.
3. Thiếu bảng nối cho N–N, hoặc nhét khóa ngoại vào cả hai bảng.
4. PK tổ hợp `(a_id, b_id)` cho cặp có thể lặp.
5. Dùng khóa nghiệp vụ dễ đổi (email, số điện thoại, mã số thuế) làm PK/FK.
6. Lưu thuộc tính suy diễn mà không có cơ chế đồng bộ.
7. Một FK trỏ tới nhiều bảng (polymorphic) mà không có cách ép toàn vẹn.
8. Dùng NULL để mã hóa nhiều ý nghĩa ("chưa biết", "không áp dụng", "rỗng").
9. Kế thừa cho vai trò thay đổi.
10. Phi chuẩn hóa sớm, không có số liệu.
