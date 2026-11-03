# 06 — Nhất quán chéo & Truy vết (Traceability)

Chạy khi có ≥2 artifact. Lỗi lệch giữa artifact thường nặng nhất: dev chọn một nguồn, QA test theo nguồn khác.

Mục lục: A. Chuỗi truy vết · B. Quy tắc XC · C. Cách thực hiện · D. Ma trận mẫu · E. Mẫu finding

## A. Chuỗi truy vết chuẩn

```
Mục tiêu nghiệp vụ → FR/NFR/BR → Use case (+ bước) → Class/thao tác → Bảng/cột DB → State/transition → API/Màn hình → Test condition
```

Mỗi liên kết phải **hai chiều**: tiến (requirement được hiện thực ở đâu?) và lùi (artifact này phục vụ requirement nào?). Thành phần không truy ngược được = scope creep hoặc requirement ẩn. Requirement không truy tiến được = thiếu thiết kế.

## B. Quy tắc nhất quán chéo

| ID | Kiểm tra | Sev |
|---|---|---|
| XC-01 | **Thuật ngữ**: cùng khái niệm cùng tên ở SRS, UC, class, bảng, enum, API; không một tên hai nghĩa, không hai tên một nghĩa. Lập bảng đồng nghĩa (Khách hàng/Customer/Client/Account) | S2 |
| XC-02 | **Actor ↔ Role ↔ Quyền**: mọi actor ở UC có role trong SRS và quyền trong ma trận; mọi role có ≥1 UC | S2 |
| XC-03 | **FR → UC**: mỗi FR ánh xạ ≥1 UC/story; mỗi UC truy về FR | S2 |
| XC-04 | **UC → Class**: mỗi danh từ nghiệp vụ trong UC có class/thuộc tính; mỗi thao tác chính có chủ sở hữu | S3 |
| XC-05 | **Class → DB**: class lưu trữ ↔ bảng; thuộc tính ↔ cột (tên, kiểu, nullability); quan hệ & multiplicity ↔ FK, unique, nullability; kế thừa ↔ chiến lược ánh xạ (single table/table per class/joined) được nêu | S2 |
| XC-06 | **State ↔ Enum ↔ Cột status ↔ API**: cùng một tập giá trị, cùng chính tả; trạng thái nào là cuối; ánh xạ nhãn hiển thị | S1–S2 |
| XC-07 | **Transition ↔ UC/API**: mỗi chuyển trạng thái do UC/API cụ thể kích hoạt, có quyền, có điều kiện; UC thay đổi trạng thái đều có trong state diagram | S2 |
| XC-08 | **Quy tắc & số liệu**: giới hạn, thời gian, ngưỡng, công thức giống nhau ở mọi nơi nhắc đến (SRS, UC, guard, CHECK) | S1–S2 |
| XC-09 | **Trường dữ liệu**: SRS (kiểu, độ dài, bắt buộc, miền giá trị) ↔ cột DB ↔ thuộc tính class ↔ API schema ↔ UI | S2 |
| XC-10 | **Include/extend** giữa UC diagram và spec khớp; tên UC giống nhau ở diagram, spec, SRS | S3 |
| XC-11 | **NFR → thiết kế**: hiệu năng/khối lượng có hệ quả lên index, partition, bất đồng bộ; bảo mật có hệ quả lên cột mã hóa, audit table, quyền | S3 |
| XC-12 | **Phiên bản**: các artifact cùng baseline (cùng version/ngày); sơ đồ không cũ hơn text | S2 |
| XC-13 | **Phạm vi**: thứ có trong sơ đồ nhưng out-of-scope trong SRS (và ngược lại) | S2 |
| XC-14 | **Dữ liệu cá nhân/nhạy cảm**: SRS nói nhạy cảm ↔ DB có xử lý (mã hóa/ẩn) ↔ UC có kiểm quyền/audit | S1–S2 |
| XC-15 | **Báo cáo/tìm kiếm**: SRS nêu trường lọc/cột báo cáo ↔ DB có dữ liệu & index để lấy được | S3 |
| XC-16 | **Thông báo/sự kiện**: SRS nêu ↔ state effect/UC bước ↔ DB lưu log/outbox | S3 |

## C. Cách thực hiện

1. **Lập danh mục có ID** cho từng loại phần tử (FR-01…, UC-01…, E-01 entity, T-01 table, S-01 state). Nếu tài liệu không có ID, tạo ID tạm trong báo cáo và nói rõ là ID của reviewer.
2. **Dựng ma trận** (mục D). Dùng công cụ chạy code nếu có (đếm, đối chiếu tập, tìm phần tử không liên kết).
3. **Đối chiếu tập**: `A \ B` (có ở A nhưng thiếu ở B) và `B \ A`. Hai chiều.
4. **Với mỗi lệch**, hỏi: lỗi artifact nào? Không biết thì tạo `CONFLICT` nêu cả hai vị trí, **không tự chọn bên đúng** (trừ khi một bên là nguồn có thẩm quyền, ví dụ SRS đã duyệt so với sơ đồ nháp — khi đó ghi giả định đó).
5. **Gộp** nhiều lệch cùng gốc thành một finding (ví dụ đổi tên "Hủy" → "Cancelled" ở 5 nơi).

## D. Ma trận mẫu (rút gọn cho báo cáo)

| FR | UC | Class/Entity | Bảng | State/transition | Test condition | Trạng thái |
|---|---|---|---|---|---|---|
| FR-012 Tạo đơn | UC-03 | Order, OrderLine | orders, order_items | Nháp→Chờ TT | TC: tồn kho 0, 1, max | ✓ |
| FR-015 Hủy đơn | — | Order | orders.status | Chờ TT→Hủy | — | ✗ thiếu UC, thiếu test |
| — | UC-09 Xuất báo cáo | — | — | — | — | ✗ không truy được FR |

Chỉ đưa vào báo cáo các dòng **có vấn đề** và thống kê tổng (ví dụ "42/50 FR có UC; 8 thiếu"). Ma trận đầy đủ đặt ở phụ lục khi DEEP.

## E. Mẫu finding chéo

- **XC-06 (S1, HIGH)**: Hai nguồn về trạng thái cuối đơn hàng khác nhau.
  *State diagram*: `Đã giao → Hoàn tất`. *DDL*: `CHECK (status IN ('NEW','PAID','SHIPPED','DELIVERED','CANCELLED'))` — không có `COMPLETED`.
  *Hậu quả*: transition cuối không lưu được; test E2E luồng chính fail.
  *Đề xuất*: thống nhất tập trạng thái (hỏi PO có cần `COMPLETED` tách `DELIVERED` không), cập nhật CHECK/enum/API.

- **XC-08 (S2, HIGH)**: Thời gian giữ tồn kho: SRS §3.2 = 15 phút; UC-03 bước 6 = 30 phút; guard `after(20m)` trong state diagram.
  *Đề xuất*: một nguồn duy nhất (cấu hình `reservation_ttl`), các nơi khác tham chiếu BR-013.
