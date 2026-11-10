# Mẫu thiết kế và bẫy thường gặp

## Mục lục
1. Trạng thái và danh mục (lookup vs ENUM vs CHECK)
2. Xóa mềm
3. Audit và phiên bản bản ghi
4. Lịch sử và hiệu lực theo thời gian
5. Cây / phân cấp
6. Đa tenant
7. Dữ liệu linh hoạt: JSON, EAV
8. Polymorphic association
9. Đánh số chứng từ không đứt quãng
10. Tiền và số lượng
11. Địa chỉ, liên hệ, danh tính
12. Đồng thời và tính nhất quán
13. Tính toán sẵn, báo cáo

## 1. Trạng thái và danh mục

| Cách | Khi dùng | Lưu ý |
|---|---|---|
| `CHECK (status IN ('DRAFT','PAID',...))` trên cột chuỗi | Tập nhỏ, ổn định, không có thuộc tính đi kèm | Thêm giá trị = sửa ràng buộc (DDL) |
| **Bảng tra cứu** (`order_statuses(code PK, name, sort_order, is_active)`) + FK | Giá trị thay đổi, cần nhãn/đa ngôn ngữ/thuộc tính, cần quản trị từ giao diện | Thêm một join; dùng khóa tự nhiên `code` ngắn để dễ đọc |
| Kiểu `ENUM` (PostgreSQL/MySQL) | Tập rất ổn định | Khó đổi/xóa giá trị; MySQL ENUM sắp xếp theo thứ tự khai báo |
| Số nguyên mã hóa | **Tránh**: không tự giải thích | |

Trạng thái có **quy tắc chuyển** (DRAFT → PAID → SHIPPED) → ghi lại bảng chuyển hợp lệ trong tài liệu và/hoặc bảng `status_transitions`; lịch sử chuyển trạng thái → bảng `order_status_history(order_id, from, to, changed_at, changed_by)`.

## 2. Xóa mềm

Cột `deleted_at timestamptz NULL` (hoặc `is_deleted`). Chỉ dùng khi **nghiệp vụ cần khôi phục hoặc lưu vết**. Cái giá:
- Mọi truy vấn phải lọc `deleted_at IS NULL` (dễ sót) → dùng view hoặc row-level security cho dữ liệu "đang hoạt động".
- `UNIQUE` xung đột với bản ghi đã xóa → dùng unique index có điều kiện: PostgreSQL `CREATE UNIQUE INDEX uq_users_email_active ON users (lower(email)) WHERE deleted_at IS NULL;`, SQL Server filtered index `WHERE deleted_at IS NULL`. MySQL không có index có điều kiện: dùng cột sinh ra hoặc đưa cột trạng thái vào khóa.
- FK vẫn trỏ tới bản ghi đã xóa mềm: định nghĩa rõ nghiệp vụ.
Thay thế: **bảng lưu trữ** (`*_archive`) hoặc bảng lịch sử, giữ bảng chính sạch.

## 3. Audit và phiên bản bản ghi

Cột chuẩn cho bảng nghiệp vụ: `created_at`, `created_by`, `updated_at`, `updated_by`. Tự cập nhật `updated_at` bằng trigger hoặc ở ứng dụng (thống nhất một cách).

**Optimistic locking**: cột `version integer NOT NULL DEFAULT 0` (hoặc `rowversion` trên SQL Server); cập nhật kèm `WHERE id = ? AND version = ?` và tăng `version`; 0 hàng bị ảnh hưởng nghĩa là xung đột.

**Audit chi tiết**: bảng `*_audit` ghi (đối tượng, hành động, giá trị cũ/mới dạng JSON hoặc theo cột, người dùng, thời điểm, correlation id), nạp bằng trigger hoặc CDC. Audit là **append-only**, cấp quyền chỉ INSERT.

## 4. Lịch sử và hiệu lực theo thời gian

Phân biệt hai trục thời gian:
- **Valid time**: dữ kiện đúng ngoài đời trong khoảng nào (giá niêm yết từ ngày A đến B).
- **Transaction time**: CSDL biết dữ kiện đó khi nào (để hỏi "tháng trước hệ thống tưởng giá là bao nhiêu").

Mẫu **hiệu lực** (valid time): `valid_from`, `valid_to` (hoặc kiểu khoảng). Quy ước **nửa mở** `[valid_from, valid_to)`, `valid_to` NULL hoặc vô cực = đang hiệu lực. Chặn chồng lấn:
```sql
-- PostgreSQL
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TABLE product_prices (
  product_id   bigint        NOT NULL REFERENCES products (product_id),
  valid_during tstzrange     NOT NULL,
  price        numeric(19,4) NOT NULL CHECK (price >= 0),
  CONSTRAINT ex_product_prices_no_overlap
    EXCLUDE USING gist (product_id WITH =, valid_during WITH &&)
);
```
Các DBMS khác: ràng buộc không chồng lấn dùng trigger/ứng dụng, ghi rõ. SQL Server có **temporal tables** (system-versioned, transaction time); Oracle có Flashback Data Archive; PostgreSQL dùng trigger/extension. **SCD loại 2** trong kho dữ liệu: dòng mới cho mỗi thay đổi, có `valid_from/valid_to/is_current`.

**Snapshot trong chứng từ**: đơn hàng, hóa đơn lưu bản sao giá, tên, địa chỉ tại thời điểm giao dịch thay vì chỉ tham chiếu bản ghi hiện tại.

## 5. Cây / phân cấp

| Mô hình | Cấu trúc | Ưu | Nhược |
|---|---|---|---|
| **Adjacency list** | `parent_id` | Đơn giản, ràng buộc FK, dễ cập nhật; dùng CTE đệ quy (`WITH RECURSIVE`/`WITH` tùy DBMS) để duyệt | Truy vấn cây con nhiều tầng cần đệ quy |
| **Materialized path** | `path = '/1/4/9/'` | Tìm cây con bằng `LIKE 'path%'` | Cập nhật khi di chuyển nhánh; không có FK cho path |
| **Closure table** | Bảng `(ancestor_id, descendant_id, depth)` | Truy vấn tổ tiên/hậu duệ nhanh, FK đầy đủ | Tốn chỗ, cập nhật phức tạp hơn |
| **Nested set** | `lft, rgt` | Đọc cây con rất nhanh | Ghi/chèn rất tốn; ít dùng hiện nay |
| **PostgreSQL `ltree`** | Kiểu đường dẫn có index | Gọn, nhiều toán tử | Chỉ PostgreSQL |

Mặc định: **adjacency list** cho cây nhỏ/vừa, cập nhật thường xuyên; **closure table** khi cần truy vấn hậu duệ/tổ tiên nhiều và cây ít đổi. Thêm `CHECK (id <> parent_id)`; chống chu trình bằng ứng dụng/trigger.

## 6. Đa tenant

| Mô hình | Cách | Phù hợp |
|---|---|---|
| **Schema chung + `tenant_id`** | Mọi bảng có `tenant_id`; ràng buộc/FK kèm `tenant_id` | Nhiều tenant nhỏ; chi phí thấp nhất |
| **Schema riêng cho mỗi tenant** | Mỗi tenant một schema | Số tenant vừa; cô lập khá, migration phức tạp |
| **Database riêng cho mỗi tenant** | Mỗi tenant một DB | Tenant lớn, yêu cầu cô lập/tuân thủ cao; chi phí vận hành cao |

Với schema chung: `tenant_id NOT NULL` mọi bảng; **FK tổ hợp** `(tenant_id, parent_id)` để không tham chiếu chéo tenant; UNIQUE tính theo `tenant_id`; index bắt đầu bằng `tenant_id`; bật **row-level security** (PostgreSQL RLS, SQL Server RLS, Oracle VPD) làm hàng rào ngoài ứng dụng.

## 7. Dữ liệu linh hoạt: JSON và EAV

- **JSON/JSONB** phù hợp cho thuộc tính thưa, cấu hình, payload bên ngoài không cần ràng buộc chặt. Không thay thế mô hình quan hệ cho dữ liệu cốt lõi cần FK, ràng buộc, báo cáo. PostgreSQL: index GIN, `CHECK` kiểm tra khóa bắt buộc. Cột dùng để lọc/join thường xuyên phải là **cột thật**.
- **EAV** (`entity_id, attribute, value` chuỗi): **tránh** vì mất kiểu dữ liệu, ràng buộc, truy vấn phức tạp và chậm. Thay bằng JSONB có CHECK, bảng thuộc tính theo nhóm, hoặc bảng riêng cho từng loại.

## 8. Polymorphic association

Cột `target_type` + `target_id` trỏ tới nhiều bảng: **không ép được FK**. Thay thế:
1. **Bảng cha chung** (supertype) mà các bảng đích kế thừa PK; FK trỏ tới bảng cha.
2. **Nhiều cột FK nullable** (`order_id`, `customer_id`) kèm `CHECK` đúng một cột có giá trị.
3. **Bảng nối riêng theo từng loại** (`order_comments`, `customer_comments`).

## 9. Đánh số chứng từ không đứt quãng

Identity/sequence **có thể có lỗ hổng** (rollback, lỗi, cache). Chứng từ cần số liên tục (hóa đơn, phiếu thu): dùng bảng bộ đếm theo chuỗi số:
```sql
CREATE TABLE document_counters (
  series_code  varchar(20) NOT NULL,
  fiscal_year  smallint    NOT NULL,
  last_number  integer     NOT NULL DEFAULT 0,
  CONSTRAINT pk_document_counters PRIMARY KEY (series_code, fiscal_year)
);
-- Trong cùng transaction với việc tạo chứng từ (PostgreSQL):
UPDATE document_counters
   SET last_number = last_number + 1
 WHERE series_code = 'INV' AND fiscal_year = 2026
RETURNING last_number;
```
`UPDATE` khóa hàng nên tuần tự hóa việc cấp số; đổi lại giảm đồng thời. Ghi chú quy định pháp lý về hóa đơn/chứng từ cần kiểm tra theo văn bản hiện hành. Thêm `UNIQUE (series_code, fiscal_year, number)` trên bảng chứng từ.

## 10. Tiền và số lượng

- `amount numeric(19,4)` + `currency_code char(3)`; không bao giờ `float`.
- Tỷ giá, đơn giá có thể cần scale lớn hơn (`numeric(19,8)`).
- Số lượng: `integer` hoặc `numeric` nếu có phần lẻ; thêm `unit_code` khi nhiều đơn vị; `CHECK (quantity > 0)`.
- Tổng (`total_amount`) là giá trị suy diễn: nếu lưu, ghi rõ cơ chế đồng bộ và có truy vấn đối soát.
- Sổ cái: ghi bút toán **append-only** (không sửa/xóa), số dư là kết quả tổng hợp hoặc bảng số dư được cập nhật cùng transaction.

## 11. Địa chỉ, liên hệ, danh tính

- Một khách hàng nhiều địa chỉ/điện thoại/email: bảng con (`customer_addresses`, `customer_contacts`) với `type`, `is_primary` và ràng buộc một bản ghi primary duy nhất (unique index có điều kiện).
- `email` UNIQUE trên `lower(email)`; kiểm tra định dạng cơ bản ở ứng dụng.
- **Party model** (Person/Organization dùng chung `party`) khi một thực thể có thể đóng nhiều vai trò (khách hàng, nhà cung cấp, nhân viên).
- Địa chỉ Việt Nam: xem `physical-design.md` §8.

## 12. Đồng thời và tính nhất quán

- Giao dịch ngắn, đúng ranh giới nghiệp vụ; khóa theo thứ tự nhất quán để tránh deadlock.
- **Idempotency**: bảng `idempotency_keys(key UNIQUE, request_hash, response, created_at)` cho API ghi có thể gọi lại.
- **Outbox pattern**: ghi sự kiện cần phát vào bảng `outbox` trong cùng transaction với dữ liệu nghiệp vụ, một tiến trình đọc và phát đi; tránh ghi kép CSDL + message broker.
- Chống tồn kho âm: `CHECK (quantity_on_hand >= 0)` và cập nhật nguyên tử `UPDATE ... SET q = q - ? WHERE id = ? AND q >= ?`.

## 13. Tính toán sẵn, báo cáo

- **Generated/computed column** cho giá trị suy diễn cùng hàng (PostgreSQL 12+ `GENERATED ALWAYS AS (...) STORED`, MySQL, SQL Server computed, Oracle virtual column).
- **View** để đóng gói truy vấn; **materialized view** (PostgreSQL, Oracle) cho báo cáo nặng, có lịch làm mới.
- Tách tải báo cáo khỏi OLTP (replica đọc, kho dữ liệu) khi báo cáo nặng ảnh hưởng giao dịch.
