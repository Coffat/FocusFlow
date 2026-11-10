# 04 — Review DB Diagram / ERD / DDL

Áp dụng cho ERD (Chen, Crow's foot, IDEF1X, UML), DBML, SQL DDL, dbdiagram, ảnh. Quy tắc chung theo mô hình quan hệ; chi tiết **phụ thuộc DBMS** (PostgreSQL, MySQL, SQL Server, Oracle...) → khi tài liệu chưa nêu DBMS, ghi "tùy DBMS" và hỏi, không áp quy tắc riêng.

Mục lục: A. Mức mô hình · B. Bảng & khóa · C. Cột & kiểu · D. Quan hệ & toàn vẹn · E. Chuẩn hóa · F. Index & hiệu năng · G. Dữ liệu nhạy cảm & vòng đời · H. Anti-pattern · I. Đối chiếu

## A. Mức mô hình

Xác định: **conceptual** (entity, quan hệ), **logical** (thuộc tính, khóa, chuẩn hóa), **physical** (kiểu, index, partition theo DBMS). Chấm đúng mức; không đòi index trong conceptual.

## B. Bảng & khóa

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| DB-B01 | **Mọi bảng có PK** | Bảng không PK | S1 |
| DB-B02 | PK ổn định, duy nhất, không null, không mang ý nghĩa dễ đổi (email, số điện thoại làm PK) | PK = email | S2 |
| DB-B03 | Khóa tự nhiên quan trọng có **UNIQUE** (mã đơn, mã SKU, email nếu duy nhất) kể cả khi dùng surrogate key | Chỉ có `id`, mã nghiệp vụ trùng được | S2 |
| DB-B04 | Khóa tổng hợp trong bảng nối hợp lý (hoặc surrogate + unique cặp) | Bảng nối không chặn trùng cặp | S2 |
| DB-B05 | Kiểu khóa & chiến lược sinh nhất quán (BIGINT identity / UUID; cân nhắc UUIDv7 để index thân thiện thứ tự) | Trộn kiểu ngẫu nhiên; UUIDv4 làm clustered PK ở bảng ghi nhiều | S3 |
| DB-B06 | ID lộ ra API không cho phép đoán (IDOR/BOLA): dùng UUID/opaque hoặc kiểm quyền | ID tuần tự lộ + không nói kiểm quyền | S2 |
| DB-B07 | Tên bảng/cột theo quy ước nhất quán (snake_case, số ít/nhiều thống nhất), không từ khóa dự trữ | `Order` (từ khóa), trộn `UserID`/`user_id` | S3 |

## C. Cột & kiểu dữ liệu

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| DB-C01 | Mỗi cột có kiểu, độ dài/precision-scale phù hợp | Không kiểu; VARCHAR không giới hạn tùy tiện | S2 |
| DB-C02 | **Tiền**: DECIMAL/NUMERIC(p,s) (thường `(19,4)` hoặc theo tiền tệ), có cột currency; không FLOAT/DOUBLE | `price FLOAT` | S1–S2 |
| DB-C03 | **Thời gian**: kiểu có múi giờ hoặc chuẩn UTC thống nhất; phân biệt date/datetime; không lưu ngày bằng chuỗi | `created VARCHAR` | S2 |
| DB-C04 | **NOT NULL** theo nghiệp vụ; NULL có nghĩa rõ, tránh NULL làm ba trạng thái | Cột bắt buộc theo SRS lại nullable | S2 |
| DB-C05 | **DEFAULT** hợp lý cho status, flag, timestamp | Không default dẫn tới NULL ngoài ý muốn | S3 |
| DB-C06 | **CHECK/ENUM/bảng tham chiếu** cho miền giá trị (status, loại) | Status là VARCHAR tự do | S2 |
| DB-C07 | Boolean/flag không dùng 0/1/Y/N lẫn lộn | | S3 |
| DB-C08 | Cột JSON/JSONB dùng có chủ đích (dữ liệu bán cấu trúc), không chứa dữ liệu cần ràng buộc/join thường xuyên | JSON nhét quan hệ | S2 |
| DB-C09 | Dữ liệu văn bản đa ngôn ngữ: collation/encoding (UTF-8), độ dài đủ cho tiếng Việt có dấu, so khớp không phân biệt dấu nếu cần | | S3 |
| DB-C10 | Cột dẫn xuất không lưu trùng trừ khi có lý do hiệu năng được ghi rõ (denormalization) | `total_amount` lưu mà không có cơ chế giữ đồng bộ | S3 |
| DB-C11 | Số điện thoại, mã bưu chính, số định danh: lưu dạng chuỗi, có chuẩn hóa (E.164) | Điện thoại là INT (mất số 0) | S2 |

## D. Quan hệ & toàn vẹn

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| DB-D01 | Mỗi quan hệ có **FK khai báo** (hoặc ghi lý do không dùng FK, ví dụ sharding/microservice) | Quan hệ chỉ vẽ, không FK | S2 |
| DB-D02 | **ON DELETE / ON UPDATE** chọn có chủ đích (RESTRICT/NO ACTION, CASCADE chỉ cho thành phần composition, SET NULL khi cho phép) | CASCADE trên quan hệ có dữ liệu tài chính/lịch sử | S1–S2 |
| DB-D03 | Cardinality & optionality (bắt buộc/tùy chọn ở mỗi đầu) khớp SRS; FK NOT NULL ⇔ bắt buộc | 1–n vẽ nhưng FK nullable trong khi bắt buộc | S2 |
| DB-D04 | Quan hệ n–n có **bảng nối**, có chặn trùng cặp, có cột riêng của quan hệ (số lượng, ngày) | n–n vẽ trực tiếp ở mức physical | S1–S2 |
| DB-D05 | Quan hệ 1–1: có lý do tách bảng; FK unique | 1–1 mà không UNIQUE | S3 |
| DB-D06 | Không vòng tham chiếu FK gây khó insert/delete (hoặc có deferrable) | Cycle | S3 |
| DB-D07 | Quan hệ đệ quy (cây/phân cấp): chiến lược (adjacency, path, closure), chống chu trình | `parent_id` không kiểm chu trình | S3 |
| DB-D08 | Ràng buộc nghiệp vụ biểu diễn được ở DB: unique có điều kiện (partial index), exclusion (không chồng khoảng thời gian), check liên cột | Chỉ dựa vào code | S3 |
| DB-D09 | Giao dịch & tính nhất quán: ranh giới transaction, khóa lạc quan (cột `version`/`row_version`) cho thực thể bị sửa đồng thời | Không cơ chế chống ghi đè mất | S2 |

## E. Chuẩn hóa

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| DB-E01 | **1NF**: giá trị nguyên tử; không danh sách phân cách dấu phẩy; không nhóm cột lặp | `phone1, phone2, phone3`; `tags = "a,b,c"` | S2 |
| DB-E02 | **2NF**: không phụ thuộc một phần vào khóa tổng hợp | Trong bảng `order_item(order_id, product_id, product_name)`, `product_name` phụ thuộc `product_id` | S2 |
| DB-E03 | **3NF/BCNF**: không phụ thuộc bắc cầu | `employee(dept_id, dept_name)` | S2 |
| DB-E04 | **Denormalization có chủ đích** phải được ghi lý do & cơ chế đồng bộ; đặc biệt snapshot tại thời điểm giao dịch (giá, tên, địa chỉ lúc đặt) là **đúng**, không phải lỗi | Cắt nhầm snapshot thành tham chiếu → đổi giá làm đổi lịch sử đơn | S1–S2 |

Phân biệt rất rõ: lặp dữ liệu **vô tình** (lỗi) và **snapshot/denormalize có chủ đích** (tốt). Hỏi trước khi kết luận.

## F. Index & hiệu năng (mức physical)

| ID | Kiểm tra | Sev |
|---|---|---|
| DB-F01 | Index cho FK dùng join/lọc (nhiều DBMS không tự tạo) | S2 |
| DB-F02 | Index theo truy vấn thực tế (từ SRS: tìm kiếm, báo cáo); thứ tự cột trong composite index; không index thừa | S3 |
| DB-F03 | Ước lượng khối lượng & tăng trưởng; chiến lược partition/archiving cho bảng log/giao dịch lớn | S3 |
| DB-F04 | Tìm kiếm văn bản/đa điều kiện cần giải pháp riêng (full-text, search engine) thay vì `LIKE '%x%'` | S3 |
| DB-F05 | Idempotency: bảng/khóa để chống xử lý trùng thông điệp/giao dịch; outbox cho phát sự kiện đáng tin | S3 |

## G. Dữ liệu nhạy cảm & vòng đời

| ID | Kiểm tra | Sev |
|---|---|---|
| DB-G01 | Phân loại cột PII/nhạy cảm; mã hóa/hashing/tokenization; không lưu mật khẩu rõ (dùng thuật toán băm chuyên dụng có salt: Argon2id/bcrypt/scrypt) | S1 |
| DB-G02 | Retention, ẩn danh, xóa theo yêu cầu chủ thể dữ liệu; xung đột với audit/soft delete được giải quyết | S2 |
| DB-G03 | **Soft delete**: cột `deleted_at`; unique phải dùng partial/filtered để cho phép tạo lại; truy vấn mặc định lọc | S2 |
| DB-G04 | Audit: `created_at/by`, `updated_at/by`; bảng lịch sử/CDC cho dữ liệu quan trọng | S2 |
| DB-G05 | Đa tenant: `tenant_id` ở mọi bảng liên quan, nằm trong unique & index, chiến lược cô lập (schema/row-level security) | S1–S2 |
| DB-G06 | Dữ liệu theo hiệu lực (effective dating): `valid_from/valid_to`, chống chồng lấn | S2 |
| DB-G07 | Sao lưu, phục hồi, di trú schema (migration có đảo ngược/zero-downtime) được nêu khi là yêu cầu | S3 |

## H. Anti-pattern cần nhận diện

- **EAV** (entity–attribute–value) cho dữ liệu thông thường.
- **Polymorphic association** (`target_type`, `target_id` không FK).
- **Bảng "god"** > ~50 cột hỗn hợp nhiều khái niệm.
- **Cột "status" kiêm nhiều ý** (vừa trạng thái xử lý vừa kết quả).
- **Lưu file nhị phân lớn** trong bảng giao dịch không có lý do.
- **Magic number** trong status (1,2,3) không có bảng/ghi chú.
- **Dùng NULL thay cho "không áp dụng"** trong nhiều ngữ nghĩa.
- **Khóa ngoại thiếu/đa hình** làm mất toàn vẹn.
- **Tên bảng/cột gây lẫn** (`type`, `data`, `value`, `info`).

## I. Đối chiếu

- Mỗi class lưu trữ ↔ bảng; mỗi thuộc tính ↔ cột; multiplicity ↔ FK nullability & unique.
- Mỗi trạng thái trong state diagram ↔ giá trị hợp lệ của cột status (CHECK/enum); có cột lưu thời điểm/lý do chuyển trạng thái nếu SRS cần.
- Mỗi trường nhập trong SRS (độ dài, kiểu, bắt buộc) ↔ cột (kiểu, độ dài, NOT NULL).
- Mỗi báo cáo/tìm kiếm trong SRS ↔ truy vấn khả thi với index.
- Chi tiết: `06-cross-consistency.md`.

## Gợi ý khi đã có DDL

Nếu có công cụ chạy code: parse DDL (ví dụ `sqlglot` hoặc chạy trên SQLite/PostgreSQL tạm) để liệt kê bảng thiếu PK, FK không index, cột nullable ở khóa, kiểu FLOAT cho tiền. Kết quả máy chỉ là dữ liệu đầu vào; vẫn phải xét ngữ cảnh trước khi gán severity.
