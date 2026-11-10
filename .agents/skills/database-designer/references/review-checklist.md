# Checklist rà soát thiết kế CSDL (tự chạy trước khi giao)

## Mô hình và chuẩn hóa
- [ ] Mỗi bảng có mục đích rõ, truy vết về thực thể/lớp/use case.
- [ ] Đã liệt kê phụ thuộc hàm; mỗi bảng đạt ít nhất 3NF/BCNF hoặc có ghi chú phi chuẩn hóa (lý do, truy vấn hưởng lợi, cơ chế đồng bộ).
- [ ] Không có cột chứa danh sách/nhiều giá trị (CSV, `phone1..phone3`) khi cần truy vấn theo phần tử.
- [ ] Quan hệ N–N có bảng nối; thuộc tính của quan hệ nằm ở bảng nối.
- [ ] Cặp có thể lặp không dùng PK tổ hợp `(a_id, b_id)`.
- [ ] Kế thừa đã chọn chiến lược có lập luận; không dùng kế thừa cho vai trò đổi theo thời gian.
- [ ] Snapshot lịch sử (giá, tên, địa chỉ trong chứng từ) được dùng đúng chỗ và ghi chú.

## Khóa và ràng buộc
- [ ] Mọi bảng có PK; PK nhỏ, bất biến, không mang nghĩa nghiệp vụ (trừ bảng tra cứu ổn định).
- [ ] Khóa nghiệp vụ có `UNIQUE`; hành vi NULL trong UNIQUE phù hợp DBMS.
- [ ] Mọi quan hệ có FK thật; `ON DELETE` chọn có chủ đích (CASCADE chỉ cho composition).
- [ ] `NOT NULL` khớp bội số tối thiểu; `NULL` chỉ khi có ý nghĩa nghiệp vụ rõ.
- [ ] `CHECK` cho miền giá trị, trạng thái, quan hệ giữa các cột (`valid_to > valid_from`).
- [ ] Quy tắc liên-bảng không khai báo được đã ghi rõ cơ chế (trigger/ứng dụng/exclusion) và rủi ro.
- [ ] Không có FK đa hình không ép được toàn vẹn (hoặc đã dùng mẫu thay thế).

## Kiểu dữ liệu
- [ ] Tiền dùng decimal cố định + `currency_code`; không `float`.
- [ ] Thời điểm lưu UTC/có múi giờ; ngày thuần dùng `date`; MySQL không dùng `TIMESTAMP` cho ngày xa.
- [ ] Chuỗi Unicode đúng (utf8mb4 / nvarchar / AL32UTF8); độ dài theo nghiệp vụ.
- [ ] Số điện thoại, mã số thuế, số căn cước, mã bưu chính là chuỗi.
- [ ] Trạng thái/mã dùng chuỗi có nghĩa + CHECK/lookup, không số ma thuật.
- [ ] Kiểu và cú pháp khớp **DBMS và phiên bản** đã chọn.

## Index và hiệu năng
- [ ] Có bảng truy vấn → index; không index thừa; thứ tự cột index tổ hợp đúng (bằng trước, khoảng/sắp xếp sau).
- [ ] Mọi FK dùng để join/xóa cha đều có index (PostgreSQL, SQL Server, Oracle không tự tạo).
- [ ] Không index riêng trên cột ít giá trị mà không có điều kiện bổ trợ.
- [ ] Partition chỉ khi có lý do (kích thước, vòng đời dữ liệu) và truy vấn lọc theo khóa partition.
- [ ] Khối lượng dữ liệu và tăng trưởng đã được ước lượng hoặc ghi vào câu hỏi mở.

## Vận hành, bảo mật, tuân thủ
- [ ] Cột audit (`created_at/by`, `updated_at/by`) và chiến lược xóa (cứng/mềm/lưu trữ) đã quyết định.
- [ ] Optimistic locking hoặc chiến lược đồng thời cho bảng có tranh chấp.
- [ ] Dữ liệu cá nhân/nhạy cảm đã phân loại; có chính sách mã hóa, che, lưu giữ.
- [ ] Mật khẩu chỉ lưu băm; không lưu bí mật dạng rõ.
- [ ] Quyền ứng dụng ít đặc quyền; tách quyền migration và runtime.
- [ ] Đa tenant (nếu có): `tenant_id` mọi bảng, FK/UNIQUE theo tenant, RLS hoặc cơ chế tương đương.
- [ ] Có kế hoạch migration (expand/contract, backfill, hoàn tác) cho thay đổi trên dữ liệu thật.

## Đặt tên và tài liệu
- [ ] `snake_case` nhất quán, số ít/số nhiều nhất quán, không từ khóa dành riêng, không vượt giới hạn độ dài.
- [ ] Ràng buộc/index có tên theo quy ước (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`).
- [ ] ERD, DDL, data dictionary khớp nhau từng bảng, cột, quan hệ.
- [ ] DDL theo thứ tự phụ thuộc, có thể chạy từ đầu; nêu rõ chưa/đã chạy thử.

## Bàn giao
- [ ] Tóm tắt: DBMS giả định, quyết định đáng chú ý (đặc biệt phi chuẩn hóa), rủi ro, câu hỏi mở cần xác nhận.
