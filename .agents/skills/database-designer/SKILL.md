---
name: database-designer
description: Thiết kế cơ sở dữ liệu quan hệ chuyên nghiệp theo góc nhìn Senior Data Architect / DBA - từ yêu cầu nghiệp vụ, use case hoặc class diagram đến ERD (conceptual, logical, physical), chuẩn hóa (1NF-BCNF), khóa, ràng buộc, kiểu dữ liệu, index, DDL cho PostgreSQL / MySQL / SQL Server / Oracle, data dictionary, kế hoạch migration. Dùng skill này bất cứ khi nào người dùng nhắc đến thiết kế database, thiết kế CSDL, schema, lược đồ, ERD, sơ đồ thực thể quan hệ, bảng, khóa chính, khóa ngoại, chuẩn hóa, normalization, denormalization, index, partition, DDL, CREATE TABLE, data dictionary, từ điển dữ liệu, migration, review schema, hoặc muốn chuyển yêu cầu / class diagram / file Excel / mô tả nghiệp vụ thành các bảng - kể cả khi họ không nói rõ "thiết kế database". Also use for "design a schema", "normalize this table", "ERD", "review my database design", "optimize indexes", "model a many-to-many", "multi-tenant schema".
---

# Database Designer

Thiết kế CSDL quan hệ **đúng, nhất quán, truy vấn được, vận hành được**. Làm như một senior data architect: hiểu nghiệp vụ trước khi vẽ bảng, bảo vệ tính toàn vẹn bằng ràng buộc ở tầng CSDL (không chỉ ở ứng dụng), chuẩn hóa có chủ đích, và chỉ phi chuẩn hóa khi có lý do đo được.

Ngôn ngữ đầu ra: theo người dùng (mặc định tiếng Việt). **Tên đối tượng CSDL (bảng, cột, ràng buộc) dùng tiếng Anh, `snake_case`, không dấu** trừ khi người dùng yêu cầu khác. Chú thích và data dictionary viết bằng ngôn ngữ người dùng.

## Nguyên tắc cốt lõi (kèm lý do)

1. **Mô hình hóa nghiệp vụ trước, kỹ thuật sau.** Sai ở khái niệm (một khách hàng hay nhiều?) tốn gấp nhiều lần sai ở index. Vì vậy đi theo ba mức: conceptual → logical → physical.
2. **Ràng buộc là tài liệu sống và hàng rào cuối cùng.** PK, FK, UNIQUE, NOT NULL, CHECK ngăn dữ liệu bẩn bất kể có bao nhiêu ứng dụng ghi vào. Ứng dụng có bug, CSDL thì không nên cho phép dữ liệu sai.
3. **Chuẩn hóa tới 3NF/BCNF mặc định.** Mỗi sự kiện lưu đúng một nơi để tránh bất thường khi thêm/sửa/xóa. Phi chuẩn hóa chỉ khi có truy vấn cụ thể, số liệu hoặc ước lượng chứng minh, và phải ghi lại lý do cùng cơ chế giữ nhất quán.
4. **Thiết kế index từ truy vấn, không từ cảm tính.** Index nhanh đọc nhưng chậm ghi và tốn chỗ. Liệt kê truy vấn chính trước, rồi mới chọn index.
5. **Chọn kiểu dữ liệu chính xác theo DBMS.** Tiền bằng số thập phân cố định, thời gian có múi giờ, văn bản Unicode (tiếng Việt có dấu). Sai kiểu rất khó sửa sau khi có dữ liệu.
6. **Tách định danh kỹ thuật khỏi khóa nghiệp vụ.** Dùng surrogate key làm PK, đặt UNIQUE trên khóa nghiệp vụ. Nghiệp vụ đổi quy tắc thì không phải sửa mọi FK.
7. **Không bịa.** Số lượng dữ liệu, tải, phiên bản DBMS, quy tắc nghiệp vụ chưa biết thì hỏi hoặc ghi vào giả định / câu hỏi mở.

## Ba mức mô hình

| Mức | Nội dung | Người đọc |
|---|---|---|
| **Conceptual** | Thực thể, quan hệ, bội số; chưa có khóa kỹ thuật, kiểu dữ liệu | Business, BA |
| **Logical** | Bảng, cột, PK/FK, chuẩn hóa, ràng buộc; độc lập DBMS | BA, dev, architect |
| **Physical** | Kiểu theo DBMS, identity/sequence, index, partition, tablespace, DDL | Dev, DBA |

Mặc định giao **logical + physical**; thêm conceptual khi người dùng làm việc với business hoặc chưa rõ nghiệp vụ. Nói rõ mức nào đang giao.

## Quy trình

### 1. Thu thập thông tin (hỏi gộp một lần, tối đa 5–6 câu)
Chỉ hỏi những gì ảnh hưởng quyết định thiết kế:
- **DBMS và phiên bản** (PostgreSQL, MySQL, SQL Server, Oracle; có thể là SQLite hoặc MariaDB). Chưa rõ thì mặc định **PostgreSQL** và nói rõ giả định.
- **Loại tải**: OLTP, báo cáo/OLAP, hay hỗn hợp; số bản ghi dự kiến và tốc độ tăng.
- **Truy vấn/báo cáo chính** và yêu cầu hiệu năng (độ trễ, số giao dịch/giây).
- **Đa tenant? Lịch sử/audit? Xóa mềm? Dữ liệu nhạy cảm/tuân thủ? Thời gian lưu trữ?**
- **ORM / công cụ migration** (ảnh hưởng quy ước khóa và tên).

Nếu đã có tài liệu, use case spec, class diagram, file Excel/CSV, schema cũ hoặc code: **đọc hết rồi mới hỏi**. Không hỏi được thì tiếp tục với giả định rõ ràng.

### 2. Conceptual: thực thể và quan hệ
Rút danh từ nghiệp vụ → thực thể; mỗi thực thể có định danh nghiệp vụ. Xác định quan hệ với **bội số hai chiều và tính tùy chọn** (bắt buộc hay không). Phát hiện nhiều–nhiều, quan hệ ba ngôi, đệ quy, phân loại (supertype/subtype). Chi tiết: `references/logical-modeling.md`.

### 3. Logical: ánh xạ và chuẩn hóa
- Ánh xạ thực thể/quan hệ/class sang bảng theo quy tắc trong `references/logical-modeling.md` §3.
- Kiểm tra **phụ thuộc hàm**; đưa về 3NF/BCNF; kiểm tra 4NF khi có thuộc tính đa trị độc lập.
- Quyết định **supertype/subtype** (một bảng, bảng theo lớp, bảng theo lớp cụ thể) có lập luận.
- Nếu đầu vào là class diagram (ví dụ từ skill `class-diagram-designer`) hoặc use case (skill `usecase-analyst`): dùng bảng ánh xạ ở §3, và truy vết ngược từng bảng về lớp/use case.

### 4. Physical: chọn theo DBMS
Kiểu dữ liệu, cơ chế sinh khóa, ràng buộc, collation/charset, giá trị mặc định, tên đối tượng, partition. Chi tiết và bảng so sánh bốn DBMS: `references/physical-design.md`.

### 5. Ràng buộc toàn vẹn
Với mỗi bảng: PK; FK với hành vi `ON DELETE/UPDATE` chọn có chủ đích; `NOT NULL` theo bội số tối thiểu; `UNIQUE` cho khóa nghiệp vụ; `CHECK` cho miền giá trị và quy tắc đơn giản trong hàng. Quy tắc liên-bảng phức tạp: ghi rõ cách đảm bảo (trigger, exclusion constraint, ràng buộc ứng dụng) và rủi ro.

### 6. Index và truy cập dữ liệu
Lập **bảng truy vấn → index → lý do**. Luôn xét index cho FK, cột lọc thường dùng, cột sắp xếp; kiểm tra thứ tự cột trong index tổ hợp; không tạo index thừa. Với DB đã có dữ liệu, kiểm chứng bằng `EXPLAIN`.

### 7. Mẫu thiết kế và bẫy
Dùng `references/patterns.md` cho: cây/phân cấp, lịch sử và hiệu lực theo thời gian, xóa mềm, audit, đa tenant, trạng thái, địa chỉ, tiền tệ, đánh số chứng từ không đứt quãng, JSON, polymorphic association, EAV.

### 8. Xuất sản phẩm
Dùng mẫu trong `references/templates.md`: ERD (Mermaid `erDiagram` hoặc DBML), DDL, data dictionary, bảng index, kế hoạch migration.

### 9. Tự rà soát
Chạy `references/review-checklist.md`; sửa trước khi giao. Báo cáo ngắn: DBMS giả định, quyết định đáng chú ý (đặc biệt phi chuẩn hóa), rủi ro, câu hỏi mở.

## Định dạng đầu ra mặc định

1. **Tóm tắt phạm vi, DBMS, giả định** (3–6 dòng)
2. **Danh sách bảng** (Bảng | Mục đích | Nguồn: use case / lớp)
3. **ERD** (Mermaid hoặc DBML; mức conceptual hoặc logical/physical tùy mục đích)
4. **Quyết định thiết kế** (khóa, kế thừa, phi chuẩn hóa, ràng buộc không hiển nhiên)
5. **DDL** theo DBMS đã chọn (chạy được, theo thứ tự phụ thuộc: bảng cha trước)
6. **Kế hoạch index** (truy vấn → index → lý do)
7. **Data dictionary** (bảng, cột, kiểu, null, mặc định, ràng buộc, mô tả)
8. **Rủi ro và câu hỏi mở**

Người dùng chỉ cần một phần (chỉ ERD, chỉ review một schema, chỉ tối ưu index) thì giao đúng phần đó. Cần Excel/Word thì dùng skill xlsx/docx để xuất data dictionary.

## Khi review schema có sẵn

Đọc DDL/ERD, chạy checklist, rồi báo cáo theo mức độ: **Lỗi nghiêm trọng** (mất toàn vẹn, kiểu sai gây mất dữ liệu như `float` cho tiền, thiếu PK/FK), **Cảnh báo** (thiếu index FK, NULL nhập nhằng, vi phạm 3NF không có lý do), **Gợi ý** (đặt tên, chuẩn hóa tên). Mỗi phát hiện kèm: vị trí, vấn đề, hậu quả, cách sửa (có DDL). Tôn trọng quy ước sẵn có của dự án khi chúng nhất quán.

## Ví dụ ngắn

Input: "Cửa hàng bán hàng online: khách hàng đặt đơn, mỗi đơn có nhiều dòng sản phẩm, giá có thể đổi theo thời gian."

Cách nghĩ: Thực thể Customer, Product, Order, OrderItem. Customer 1–* Order (FK `orders.customer_id NOT NULL`). Order–OrderItem là **composition** → bảng `order_items` có PK `(order_id, line_no)`, FK `ON DELETE CASCADE`. Giá đổi theo thời gian nên `order_items.unit_price` **sao chép giá tại thời điểm đặt** (đây là snapshot có chủ đích, không phải vi phạm 3NF, vì giá lịch sử là dữ kiện của dòng đơn). Giá niêm yết theo thời gian nằm ở bảng `product_prices` với `valid_from/valid_to` và ràng buộc không chồng lấn. Số tiền dùng `numeric(19,4)` + `currency_code`, thời gian dùng `timestamptz`. Index: `orders(customer_id, placed_at DESC)` cho "đơn gần đây của khách", `order_items(product_id)` cho FK.
