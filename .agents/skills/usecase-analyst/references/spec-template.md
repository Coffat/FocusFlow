# Mẫu đặc tả Use Case

Dùng đúng thứ tự mục dưới đây. Mục không áp dụng thì ghi "Không có", đừng xóa, để người đọc biết đã cân nhắc.

## Mẫu

```markdown
### UC-<nn>: <Động từ + đối tượng>

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-<nn> |
| **Tên** | |
| **Mô tả ngắn** | 1–2 câu: actor làm gì để đạt mục tiêu gì |
| **Actor chính** | |
| **Actor phụ** | |
| **Mức độ** | Mục tiêu người dùng / Tóm tắt / Chức năng con |
| **Trigger** | Sự kiện khởi động use case |
| **Tiền điều kiện** | Điều kiện phải đúng trước khi bắt đầu |
| **Hậu điều kiện – thành công** | Trạng thái hệ thống/dữ liệu sau khi thành công |
| **Hậu điều kiện – thất bại** | Bảo đảm tối thiểu khi thất bại (vd: không trừ tiền, không đổi dữ liệu) |
| **Include / Extend** | UC được include; UC mở rộng + extension point + điều kiện |
| **Tần suất / Độ ưu tiên** | (nếu biết) |

**Luồng chính (Basic Flow)**
1. ...
2. ...

**Luồng thay thế (Alternative Flows)**
- **2a. <Điều kiện>**
  1. ...
  2. Quay lại bước 3 của luồng chính.

**Luồng ngoại lệ (Exception Flows)**
- **3e. <Lỗi>**
  1. Hệ thống ... 
  2. Use case kết thúc (thất bại).

**Quy tắc nghiệp vụ**
- BR-01: ...

**Yêu cầu phi chức năng liên quan** (chỉ nếu gắn riêng với UC này)
- ...

**Dữ liệu vào / ra chính**
- Vào: ...
- Ra: ...

**Giả định & Câu hỏi mở**
- ...
```

## Quy ước viết

- Mỗi bước: một hành động, một chủ ngữ. "Khách hàng chọn suất chiếu." / "Hệ thống hiển thị sơ đồ ghế còn trống."
- Bước gọi use case khác ghi rõ: "Thực hiện UC-05 Thanh toán trực tuyến (include)."
- Tránh từ mơ hồ: "xử lý", "quản lý", "thích hợp", "nhanh". Nêu rõ xử lý gì, ngưỡng bao nhiêu hoặc đưa vào Câu hỏi mở.
- Không mô tả UI (nút, màu, vị trí). Mô tả thông tin trao đổi và quyết định.
- Luồng thay thế/ngoại lệ phải nói rõ **điểm quay lại** hoặc **kết thúc**.
- Mỗi điều kiện rẽ nhánh trong luồng chính phải có luồng thay thế/ngoại lệ tương ứng.
- Alternative flow = vẫn đạt mục tiêu. Exception flow = không đạt mục tiêu / lỗi.

## Ví dụ hoàn chỉnh

### UC-03: Đặt vé xem phim

| Thuộc tính | Nội dung |
|---|---|
| **ID** | UC-03 |
| **Tên** | Đặt vé xem phim |
| **Mô tả ngắn** | Khách hàng chọn suất chiếu, ghế và thanh toán để nhận vé điện tử. |
| **Actor chính** | Khách hàng |
| **Actor phụ** | Cổng thanh toán VNPay |
| **Mức độ** | Mục tiêu người dùng |
| **Trigger** | Khách hàng chọn "Đặt vé" cho một suất chiếu. |
| **Tiền điều kiện** | Khách hàng đã đăng nhập (UC-01). Suất chiếu còn ghế trống. |
| **Hậu điều kiện – thành công** | Vé được tạo trạng thái "Đã thanh toán", ghế bị khóa, vé điện tử gửi qua email. |
| **Hậu điều kiện – thất bại** | Ghế được nhả, không phát sinh giao dịch trừ tiền, không tạo vé. |
| **Include / Extend** | Include: UC-05 Thanh toán trực tuyến. Extend (bởi): UC-07 Áp dụng mã giảm giá tại extension point "Trước thanh toán", điều kiện: khách hàng nhập mã. |
| **Tần suất / Độ ưu tiên** | Rất cao / Must have |

**Luồng chính**
1. Khách hàng chọn phim và suất chiếu.
2. Hệ thống hiển thị sơ đồ ghế với trạng thái trống/đã đặt.
3. Khách hàng chọn một hoặc nhiều ghế (tối đa 8 ghế, BR-01).
4. Hệ thống giữ ghế tạm thời trong 10 phút (BR-02) và hiển thị tổng tiền.
5. Khách hàng xác nhận đặt vé.
6. Hệ thống thực hiện UC-05 Thanh toán trực tuyến (include).
7. Hệ thống tạo vé, đổi trạng thái ghế sang "Đã bán" và gửi vé điện tử qua email.
8. Hệ thống hiển thị mã đặt vé. Use case kết thúc thành công.

**Luồng thay thế**
- **4a. Khách hàng có mã giảm giá** (extension point "Trước thanh toán")
  1. Khách hàng nhập mã; hệ thống thực hiện UC-07 Áp dụng mã giảm giá.
  2. Quay lại bước 5 với tổng tiền đã cập nhật.
- **3a. Khách hàng đổi suất chiếu**
  1. Hệ thống nhả ghế đã chọn và quay lại bước 1.

**Luồng ngoại lệ**
- **3e. Ghế vừa bị người khác đặt**
  1. Hệ thống thông báo ghế không còn khả dụng và làm mới sơ đồ ghế.
  2. Quay lại bước 3.
- **4e. Hết thời gian giữ ghế**
  1. Hệ thống nhả ghế và thông báo phiên đặt vé hết hạn.
  2. Use case kết thúc (thất bại).
- **6e. Thanh toán thất bại hoặc bị hủy**
  1. Hệ thống nhả ghế, ghi nhận giao dịch thất bại, thông báo cho khách hàng.
  2. Use case kết thúc (thất bại).

**Quy tắc nghiệp vụ**
- BR-01: Mỗi giao dịch đặt tối đa 8 ghế.
- BR-02: Thời gian giữ ghế tạm là 10 phút kể từ lúc chọn ghế.

**Dữ liệu vào / ra chính**
- Vào: suất chiếu, danh sách ghế, thông tin thanh toán.
- Ra: mã đặt vé, vé điện tử, biên lai.

**Giả định & Câu hỏi mở**
- Giả định: một khách hàng chỉ giữ ghế ở một suất chiếu tại một thời điểm.
- Câu hỏi mở: Có cho phép đặt hộ người khác (tên khác trên vé) không?
