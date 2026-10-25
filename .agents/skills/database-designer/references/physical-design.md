# Thiết kế vật lý (Physical design)

## Mục lục
1. Khóa chính và sinh khóa
2. Kiểu dữ liệu theo DBMS
3. Ràng buộc
4. Index
5. Partition và dữ liệu lớn
6. Đặt tên
7. Bảo mật và dữ liệu cá nhân
8. Bối cảnh Việt Nam
9. Khác biệt cần nhớ giữa các DBMS

Các tính năng phụ thuộc phiên bản: **kiểm tra phiên bản người dùng đang dùng** trước khi đưa vào DDL; nếu không rõ, chọn cách chạy được trên phiên bản hỗ trợ phổ biến và ghi chú.

## 1. Khóa chính và sinh khóa

**Mặc định**: surrogate key + `UNIQUE` trên khóa nghiệp vụ. PK nhỏ, bất biến, không mang ý nghĩa nghiệp vụ.

| Lựa chọn | Ưu | Nhược | Dùng khi |
|---|---|---|---|
| **Số nguyên tự tăng** (`bigint` identity) | Nhỏ, tuần tự, index gọn, join nhanh | Lộ số lượng/thứ tự nếu để lộ ra ngoài; khó sinh ở nhiều nơi; có lỗ hổng (gap) | Mặc định cho OLTP một CSDL |
| **UUID ngẫu nhiên (v4)** | Sinh phân tán, khó đoán | Chèn ngẫu nhiên → phân mảnh index, hiệu năng ghi kém, khóa 16 byte | Cần ID sinh ngoài CSDL; **không** làm khóa cụm (clustered) trên SQL Server/InnoDB |
| **UUIDv7 / ID có thứ tự thời gian** | Sinh phân tán và vẫn gần tuần tự | 16 byte; lộ thời điểm tạo | Phân tán, hoặc cần ID công khai không đoán thứ tự dễ dàng |
| **Khóa nghiệp vụ tự nhiên** | Không cần cột phụ | Có thể đổi, dài, nhiều cột | Bảng tra cứu ổn định (mã quốc gia ISO, mã tiền tệ) |
| **PK tổ hợp** | Tự nhiên cho bảng nối, thực thể yếu | FK dài, join nhiều cột | Bảng nối N–N, dòng chi tiết (`order_id, line_no`) |

Cách sinh theo DBMS:
- **PostgreSQL**: `bigint GENERATED ALWAYS AS IDENTITY` (ưu tiên hơn `serial`). UUIDv7: hàm `uuidv7()` có sẵn từ **PostgreSQL 18**; các bản cũ sinh ở ứng dụng hoặc dùng extension. `gen_random_uuid()` cho v4.
- **MySQL (InnoDB)**: `BIGINT AUTO_INCREMENT`. Bảng InnoDB được tổ chức theo PK (clustered), nên PK ngẫu nhiên gây phân mảnh. Lưu UUID dạng `BINARY(16)` (dùng `UUID_TO_BIN(uuid, 1)` để sắp xếp theo thời gian với UUID v1), tránh `CHAR(36)`.
- **SQL Server**: `bigint IDENTITY(1,1)`; UUID dùng `uniqueidentifier` với `NEWSEQUENTIALID()` làm mặc định nếu là khóa cụm. Mặc định PK là clustered index; có thể đặt clustered ở cột khác.
- **Oracle**: `NUMBER(19) GENERATED ALWAYS AS IDENTITY` (12c trở lên) hoặc sequence + trigger ở bản cũ; `RAW(16)` cho UUID.

Nếu ID lộ ra ngoài (URL, API): cân nhắc **public_id** (UUID/ULID) tách khỏi PK nội bộ để không lộ thứ tự và tránh tấn công liệt kê.

## 2. Kiểu dữ liệu theo DBMS

| Nhu cầu | PostgreSQL | MySQL 8 | SQL Server | Oracle |
|---|---|---|---|---|
| ID số | `bigint` | `BIGINT` | `bigint` | `NUMBER(19)` |
| Tiền / số chính xác | `numeric(19,4)` | `DECIMAL(19,4)` | `decimal(19,4)` | `NUMBER(19,4)` |
| Chuỗi ngắn Unicode | `varchar(n)` hoặc `text` + CHECK | `VARCHAR(n)` + `utf8mb4` | `nvarchar(n)` (hoặc `varchar` với collation UTF-8 từ 2019) | `NVARCHAR2(n)` hoặc `VARCHAR2(n CHAR)` với `AL32UTF8` |
| Văn bản dài | `text` | `TEXT` / `MEDIUMTEXT` | `nvarchar(max)` | `CLOB` |
| Boolean | `boolean` | `BOOLEAN` (= `TINYINT(1)`) | `bit` | `BOOLEAN` (23ai) hoặc `NUMBER(1)` + CHECK |
| Ngày | `date` | `DATE` | `date` | `DATE` (có cả giờ) |
| Thời điểm | `timestamptz` | `DATETIME(6)` lưu UTC | `datetimeoffset` hoặc `datetime2` lưu UTC | `TIMESTAMP WITH TIME ZONE` |
| JSON | `jsonb` | `JSON` | `nvarchar(max)` + `CHECK (ISJSON(col)=1)`; bản mới có kiểu `json` gốc | `JSON` (21c+) hoặc `CLOB`/`VARCHAR2` + `IS JSON` |
| UUID | `uuid` | `BINARY(16)` | `uniqueidentifier` | `RAW(16)` |
| Nhị phân | `bytea` | `BLOB` | `varbinary(max)` | `BLOB` |

Quy tắc chung:
- **Không dùng `float`/`double`/`real` cho tiền** hoặc số cần chính xác. Dùng decimal cố định.
- Tiền luôn đi kèm `currency_code char(3)` (ISO 4217). Làm tròn theo số chữ số thập phân của từng tiền tệ (VND không có phần thập phân theo ISO 4217) ở tầng ứng dụng, nhưng cột lưu đủ scale cho tính toán trung gian (thường 4).
- **Thời gian lưu UTC** và có múi giờ khi DBMS hỗ trợ. MySQL `TIMESTAMP` bị giới hạn đến năm 2038, nên dùng `DATETIME`. Ngày thuần (ngày sinh, ngày hiệu lực) dùng `date`, không dùng timestamp.
- **Độ dài chuỗi theo nghiệp vụ**, không lạm dụng `max`/`TEXT`: email 254, mã quốc gia 2–3, mã tiền tệ 3. `TEXT` không có giới hạn tốt cho PG; cột cần giới hạn thì thêm `CHECK (char_length(col) <= n)`.
- **Unicode đầy đủ**: MySQL dùng `utf8mb4` (không dùng `utf8` cũ là 3 byte); SQL Server dùng `nvarchar` cho tiếng Việt khi không dùng collation UTF-8; Oracle dùng `AL32UTF8`.
- Số điện thoại, mã số thuế, số căn cước, mã bưu chính, số tài khoản là **chuỗi**, không phải số (giữ số 0 đầu, không tính toán).
- Trạng thái và mã: chuỗi ngắn có `CHECK` hoặc FK tới bảng tra cứu; tránh số "ma thuật" (1,2,3) không có chú giải.

## 3. Ràng buộc

| Ràng buộc | Nguyên tắc |
|---|---|
| `PRIMARY KEY` | Mọi bảng đều có |
| `FOREIGN KEY` | Mọi quan hệ đều có FK thật. Đặt tên rõ. Chọn `ON DELETE`: **RESTRICT/NO ACTION** (mặc định an toàn), **CASCADE** (chỉ cho composition: con không tồn tại không có cha), **SET NULL** (quan hệ tùy chọn), tránh chuỗi CASCADE xuyên nhiều aggregate. `ON UPDATE` thường không cần khi khóa bất biến |
| `NOT NULL` | Mặc định `NOT NULL`; cho phép `NULL` chỉ khi "không có giá trị" là trạng thái hợp lệ có ý nghĩa nghiệp vụ |
| `UNIQUE` | Cho khóa nghiệp vụ, cặp không trùng. Cần chuẩn hóa trước (ví dụ `lower(email)`) |
| `CHECK` | Miền giá trị (`quantity > 0`), quan hệ giữa các cột trong cùng hàng (`valid_to > valid_from`), tập hữu hạn. MySQL ép CHECK từ 8.0.16 (các bản trước bỏ qua) |
| `DEFAULT` | Cho giá trị khởi tạo hợp lý (`now()`, `0`, `'DRAFT'`) |
| Exclusion (PG) | Chống chồng lấn khoảng thời gian/phạm vi với `EXCLUDE USING gist` |
| Trigger | Dùng hạn chế cho quy tắc liên-bảng không biểu diễn được bằng khai báo; ghi tài liệu; có test |

Hành vi **NULL trong UNIQUE khác nhau** giữa DBMS (PostgreSQL, MySQL, Oracle cho phép nhiều giá trị NULL trong cột unique; SQL Server coi NULL bằng nhau nên chỉ cho một NULL, và dùng unique index có điều kiện `WHERE col IS NOT NULL` để cho phép nhiều NULL). PostgreSQL 15+ có `UNIQUE NULLS NOT DISTINCT`. Luôn ghi chú khi thiết kế phụ thuộc hành vi này.

Oracle coi chuỗi rỗng `''` là `NULL`; nhớ khi thiết kế `NOT NULL` và so sánh.

## 4. Index

Nguyên tắc:
1. **Bắt đầu từ truy vấn**: lọc (WHERE), nối (JOIN), sắp xếp (ORDER BY), nhóm (GROUP BY).
2. **Index cho mọi FK** dùng để join hoặc để xóa/cập nhật cha nhanh. PostgreSQL, SQL Server, Oracle không tự tạo index cho FK; MySQL InnoDB tự tạo nếu chưa có index phù hợp.
3. **Index tổ hợp**: đặt cột so sánh **bằng** trước, cột khoảng/sắp xếp sau; chỉ dùng được theo **tiền tố trái** (leftmost prefix). `(customer_id, placed_at)` phục vụ lọc theo `customer_id` và theo `customer_id + placed_at`, không phục vụ lọc chỉ `placed_at`.
4. **Độ chọn lọc**: index riêng trên cột ít giá trị (boolean, status) thường vô ích; hiệu quả khi là một phần index tổ hợp hoặc là **index có điều kiện** (partial/filtered).
5. **Covering index**: thêm cột vào index để truy vấn không phải đọc bảng (`INCLUDE` trong PostgreSQL 11+ và SQL Server; MySQL không có `INCLUDE`, thêm cột vào cuối khóa).
6. **Index theo biểu thức/hàm**: `lower(email)`. PostgreSQL, Oracle, MySQL 8.0.13+ hỗ trợ trực tiếp; SQL Server qua cột tính toán (computed column).
7. **Index có điều kiện**: PostgreSQL partial index, SQL Server filtered index; MySQL chưa có (dùng cột sinh ra).
8. Mỗi index tăng chi phí ghi và dung lượng; xóa index không dùng. Kiểm chứng bằng `EXPLAIN (ANALYZE)` và thống kê sử dụng index.
9. Loại index đặc thù: PostgreSQL **GIN** (jsonb, mảng, full-text), **GiST** (phạm vi, hình học), **BRIN** (bảng rất lớn sắp xếp theo thời gian); **Full-text** theo từng DBMS. Tìm kiếm tiếng Việt không dấu: cần chuẩn hóa/`unaccent` hoặc cột tìm kiếm riêng.
10. `LIKE '%abc'` (wildcard đầu) không dùng được B-tree thường; cần trigram (PG `pg_trgm`) hoặc full-text.

## 5. Partition và dữ liệu lớn

- Chỉ partition khi bảng đủ lớn (hàng trăm triệu hàng hoặc yêu cầu lưu trữ/xóa theo kỳ) và truy vấn **lọc theo khóa partition**. Partition **không** tự làm truy vấn nhanh hơn nếu không có partition pruning.
- Khóa phổ biến: thời gian (range theo tháng/quý) cho log, giao dịch; `tenant_id` (hash/list) cho đa tenant.
- Lợi ích chính: xóa/lưu trữ nhanh theo kỳ (`DROP/DETACH PARTITION`), bảo trì cục bộ.
- Ràng buộc: PostgreSQL yêu cầu khóa partition nằm trong mọi PK/UNIQUE; MySQL cũng yêu cầu khóa partition nằm trong mọi unique key. Nên cân nhắc khi chọn PK.
- Dữ liệu cũ: chiến lược lưu trữ (archive), bảng lịch sử, tiêu chí giữ lại.

## 6. Đặt tên

- `snake_case`, chữ thường, không dấu, không khoảng trắng; nhất quán (chọn **số nhiều** hay **số ít** một lần và giữ nguyên; mặc định số nhiều: `customers`, `orders`).
- Tránh từ khóa dành riêng (`order`, `user`, `group`, `table`, `desc`): dùng `orders`, `app_users`.
- Cột PK: `id` hoặc `<bảng_số_ít>_id`; FK: `<bảng_số_ít_được_tham_chiếu>_id`. Giữ một kiểu thống nhất toàn schema.
- Ràng buộc/index đặt tên rõ: `pk_<bảng>`, `fk_<bảng>_<bảng_cha>`, `uq_<bảng>_<cột>`, `ck_<bảng>_<ý>`, `ix_<bảng>_<cột>`.
- Cột thời gian: `created_at`, `updated_at`, `deleted_at`, `valid_from/valid_to`; boolean `is_`/`has_`.
- Giới hạn độ dài định danh: PostgreSQL 63 byte, MySQL 64 ký tự, SQL Server 128, Oracle 128 byte (12.2+; bản cũ 30).
- Không dùng tiền tố `tbl_`, không dùng tên chung chung (`data`, `info`, `value`).

## 7. Bảo mật và dữ liệu cá nhân

- **Phân loại dữ liệu**: định danh trực tiếp (họ tên, số căn cước, số điện thoại, email), nhạy cảm (sức khỏe, tài chính). Ghi vào data dictionary.
- **Tối thiểu hóa**: chỉ lưu cái cần. Có chính sách lưu giữ (retention) và cơ chế xóa/ẩn danh.
- Không lưu mật khẩu rõ; lưu **băm có muối** bằng thuật toán chuyên dụng (argon2id, bcrypt, scrypt), tính ở ứng dụng. Không lưu bí mật/khóa API dạng rõ trong bảng thường.
- Mã hóa: mã hóa lưu trữ (TDE/ổ đĩa) cộng mã hóa cột cho dữ liệu cực nhạy cảm; che (masking) ở môi trường không phải production.
- Quyền: tài khoản ứng dụng ít đặc quyền nhất (không phải owner/superuser); tách quyền migration và quyền runtime; dùng view hoặc row-level security (PostgreSQL RLS, SQL Server RLS, Oracle VPD) cho phân quyền theo dòng.
- Audit: ai thay đổi gì, khi nào (xem `patterns.md`).
- Tuân thủ: áp dụng quy định bảo vệ dữ liệu cá nhân hiện hành của Việt Nam (và GDPR nếu có dữ liệu EU). Văn bản pháp luật thay đổi: **kiểm tra văn bản hiện hành** trước khi khẳng định yêu cầu cụ thể.

## 8. Bối cảnh Việt Nam

- **Tiếng Việt có dấu**: Unicode đầy đủ; tìm kiếm không dấu cần cột/chỉ mục chuẩn hóa (`unaccent` ở PostgreSQL, collation `Vietnamese_CI_AI` ở SQL Server, `utf8mb4_unicode_ci`/`utf8mb4_0900_ai_ci` ở MySQL). Kiểm tra hành vi sắp xếp theo dấu với collation chọn.
- **Họ tên**: không giả định tách họ/đệm/tên; lưu `full_name` và tách thêm khi nghiệp vụ cần sắp xếp theo tên.
- **Số định danh**: số căn cước công dân/CMND, mã số thuế, số điện thoại → chuỗi; mã số thuế doanh nghiệp 10 chữ số, đơn vị phụ thuộc 13 chữ số (10 + 3). Không dùng làm PK; đặt `UNIQUE` nếu nghiệp vụ yêu cầu, và kiểm tra định dạng bằng `CHECK` đơn giản.
- **Đơn vị hành chính** (đã thay đổi): từ **01/7/2025** Việt Nam vận hành chính quyền địa phương **hai cấp** (tỉnh/thành phố – xã/phường/đặc khu), cấp huyện kết thúc hoạt động; số đơn vị cấp tỉnh còn **34**. Thiết kế bảng địa chỉ nên: (1) lưu danh mục theo cấp có `valid_from/valid_to` và mã chính thức; (2) có bảng ánh xạ đơn vị cũ → mới cho dữ liệu lịch sử; (3) chứng từ pháp lý (hóa đơn, hợp đồng) lưu **bản sao địa chỉ dạng chuỗi tại thời điểm phát hành**; (4) không cứng hóa 3 cấp tỉnh–huyện–xã. Danh mục này còn có thể thay đổi: **tra cứu danh mục hiện hành** khi nạp dữ liệu.
- **Tiền tệ**: VND không có phần thập phân (ISO 4217); vẫn lưu `numeric(19,4)` + `currency_code` nếu hệ thống có thể đa tiền tệ.
- **Chứng từ có số liên tục** (hóa đơn, phiếu): xem mục đánh số không đứt quãng trong `patterns.md`; quy định pháp lý cụ thể cần kiểm tra theo văn bản hiện hành.

## 9. Khác biệt cần nhớ giữa các DBMS

| Chủ đề | PostgreSQL | MySQL (InnoDB) | SQL Server | Oracle |
|---|---|---|---|---|
| Khóa cụm | Không (heap; `CLUSTER` là thao tác một lần) | PK luôn là clustered | PK mặc định clustered | Heap mặc định; IOT tùy chọn |
| Upsert | `INSERT ... ON CONFLICT` | `INSERT ... ON DUPLICATE KEY UPDATE` | `MERGE` | `MERGE` |
| DDL trong transaction | Có (hầu hết) | Không (tự commit) | Có | Không (tự commit) |
| Index có điều kiện | Partial | Không | Filtered | Qua biểu thức |
| Phân trang | `LIMIT/OFFSET` | `LIMIT/OFFSET` | `OFFSET ... FETCH` | `OFFSET ... FETCH` (12c+) |
| Chuỗi rỗng = NULL | Không | Không | Không | **Có** |
| Giới hạn độ dài tên | 63 byte | 64 ký tự | 128 | 128 byte (12.2+) |
| Schema = | schema trong DB | database | schema trong DB | user/schema |

Khi người dùng chưa chọn DBMS, viết DDL cho PostgreSQL và liệt kê **điểm khác biệt chính** khi chuyển sang DBMS khác (kiểu dữ liệu, identity, boolean, thời gian, upsert).
