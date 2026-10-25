# Đánh giá, ước lượng, chọn công nghệ và quản trị kiến trúc

## Mục lục
1. Ước lượng năng lực (back-of-envelope)
2. So sánh phương án có trọng số
3. Đánh giá kiến trúc kiểu ATAM rút gọn
4. Fitness function
5. Chọn công nghệ và build vs buy
6. Chi phí
7. Nợ kỹ thuật và rủi ro
8. Quản trị nhẹ
9. Phản mẫu (anti-pattern)

## 1. Ước lượng năng lực

Mục đích: biết **bậc độ lớn** để loại phương án không đủ sức hoặc quá đắt, không phải con số chính xác. Ghi rõ giả định, dùng khoảng, đánh dấu cần xác nhận.

Công thức:
- **Yêu cầu/giây trung bình** = (số người dùng hoạt động/ngày × số yêu cầu mỗi người/ngày) ÷ 86.400.
- **Đỉnh** = trung bình × hệ số đỉnh (thường 3–10×; sự kiện mở bán/khuyến mãi có thể cao hơn nhiều).
- **Số yêu cầu đồng thời** (Little's law) = yêu cầu/giây × thời gian xử lý trung bình (giây).
- **Dung lượng lưu trữ** = số bản ghi mới/ngày × kích thước bản ghi × số ngày lưu giữ × hệ số (index, bản sao, sao lưu; thường ×2–×3).
- **Băng thông** = yêu cầu/giây × kích thước phản hồi trung bình.
- **Số instance ứng dụng** ≈ đỉnh yêu cầu/giây ÷ (khả năng xử lý một instance × mức dùng mục tiêu ~50–70%) + dự phòng N+1.

Ví dụ: 1 triệu người dùng/ngày × 20 yêu cầu = 20 triệu/ngày ≈ 231 yêu cầu/giây trung bình; hệ số đỉnh 5–10 ≈ 1.200–2.300 yêu cầu/giây. Với độ trễ trung bình 200 ms, số yêu cầu đồng thời ≈ 230–460.

Sau ước lượng, hỏi: một CSDL giao dịch đơn có chịu nổi không? Cần cache/replica? Có điểm nghẽn đơn (một hàng đợi, một khóa nóng)? Dữ liệu 3 năm vào bao nhiêu TB?

## 2. So sánh phương án có trọng số

| Tiêu chí (từ ASR) | Trọng số | Phương án A | Phương án B | Phương án C |
|---|---|---|---|---|
| Nhất quán ghế (không bán trùng) | 5 | 5 | 3 | 4 |
| Chịu đỉnh tải | 4 | 3 | 5 | 4 |
| Thời gian ra thị trường | 4 | 5 | 2 | 3 |
| Chi phí vận hành | 3 | 5 | 2 | 3 |
| Khả năng thay đổi | 3 | 3 | 4 | 4 |
| **Tổng có trọng số** | | ... | ... | ... |

Quy tắc dùng:
- Tiêu chí lấy **từ ASR**, trọng số do bên liên quan xác nhận; cho điểm 1–5 kèm **một dòng lý do** mỗi ô.
- Kiểm tra độ nhạy: đổi trọng số ±1 xem xếp hạng có đảo không; nếu đảo, quyết định phụ thuộc vào ưu tiên, hãy nói rõ.
- Điểm số không thay lập luận: trình bày phương án thắng, vì sao, và **điều kiện đổi**.
- Loại sớm phương án vi phạm ràng buộc cứng (pháp lý, ngân sách, công nghệ bắt buộc).

## 3. Đánh giá kiến trúc kiểu ATAM rút gọn

1. Trình bày kiến trúc đề xuất (C4 + ADR).
2. Liệt kê ASR (scenario) theo ưu tiên.
3. Với mỗi scenario: kiến trúc đáp ứng bằng cơ chế nào (chiến thuật, thành phần), có chứng cứ gì (ước lượng, prototype, kinh nghiệm)?
4. Ghi nhận:
   - **Rủi ro**: quyết định có thể gây hậu quả xấu cho một ASR.
   - **Điểm nhạy cảm**: một tham số/quyết định ảnh hưởng mạnh tới một thuộc tính (kích thước pool, TTL cache).
   - **Điểm đánh đổi**: một quyết định tác động trái chiều lên ≥ 2 thuộc tính (cache tăng hiệu năng nhưng giảm nhất quán).
   - **Điểm không rủi ro**: quyết định ổn đã được phân tích.
5. Từ rủi ro → **chủ đề rủi ro** và hành động giảm thiểu (spike, thử tải, thay đổi thiết kế), có chủ sở hữu và hạn.
6. Phân biệt rõ phần đã **chứng minh** (thử nghiệm) với phần **giả định**.

## 4. Fitness function

Kiểm thử tự động bảo vệ thuộc tính kiến trúc để kiến trúc không thoái hóa:
- **Phụ thuộc**: kiểm thử kiến trúc (ArchUnit, NetArchTest, dependency-cruiser) ép "module A không gọi nội bộ module B", "không vòng phụ thuộc", "lớp miền không import framework".
- **Hiệu năng**: thử tải trong pipeline; ngưỡng p95 theo scenario; so sánh với baseline.
- **Bảo mật**: quét phụ thuộc/bí mật/SAST/DAST trong CI; kiểm thử phân quyền theo vai trò.
- **Khả năng triển khai**: thời gian pipeline, tỉ lệ thay đổi thất bại.
- **Dữ liệu**: kiểm thử migration trên bản sao, kiểm thử hợp đồng API/sự kiện.
- **Chi phí**: cảnh báo ngân sách, chi phí theo yêu cầu/tenant.

Mỗi ASR chính nên có ít nhất một fitness function hoặc cách đo trong vận hành.

## 5. Chọn công nghệ và build vs buy

Tiêu chí (cho điểm theo ASR và ràng buộc): phù hợp bài toán, độ trưởng thành và tính ổn định, cộng đồng và hỗ trợ, năng lực/đường cong học của đội, **nguồn nhân lực thị trường**, giấy phép, **tổng chi phí sở hữu** (license, hạ tầng, vận hành, đào tạo), rủi ro khóa nhà cung cấp và **chi phí thoát**, bảo mật và tuân thủ, khả năng tích hợp, lộ trình sản phẩm.

- Ưu tiên công nghệ "nhàm chán", đã chứng minh; mỗi công nghệ mới tiêu tốn "ngân sách đổi mới" của đội.
- **Build** khi là lợi thế cạnh tranh cốt lõi; **buy/dùng dịch vụ** cho phần đại trà (xác thực, thanh toán, email, tìm kiếm, giám sát) trừ khi ràng buộc đặc thù.
- Với dịch vụ quản lý (managed): cân nhắc SLA, giới hạn, chi phí khi lớn, khả năng xuất dữ liệu.
- **Proof of concept** cho lựa chọn rủi ro cao, có tiêu chí thành công đo được và hạn chót.
- Ghi quyết định vào ADR cùng phương án bị loại.
- Kiểm tra phiên bản và tính năng hiện hành của công nghệ trước khi dựa vào; đừng cho rằng tính năng tồn tại từ trí nhớ.

## 6. Chi phí

- Mô hình chi phí theo thành phần: tính toán, lưu trữ, mạng/egress, dịch vụ quản lý, giám sát/log, license, nhân sự vận hành.
- So sánh phương án theo **chi phí ở ba mức tải** (hiện tại, ×3, ×10), không chỉ hiện tại.
- Chi phí vận hành nhân sự của kiến trúc phức tạp thường lớn hơn chi phí hạ tầng.
- Cơ chế kiểm soát: gắn thẻ, ngân sách/cảnh báo, right-sizing, autoscaling có chặn trên, tắt môi trường không dùng, đo chi phí theo tính năng/tenant.

## 7. Nợ kỹ thuật và rủi ro

- **Sổ rủi ro**: mô tả, xác suất, tác động, chủ sở hữu, kế hoạch giảm thiểu/chấp nhận, ngày xem lại.
- **Nợ kỹ thuật** có chủ đích (đánh đổi tốc độ, ghi nhận, có kế hoạch trả) khác với nợ vô ý. Ghi vào arc42 mục 11: mô tả, lý do, hậu quả nếu không trả, ước lượng công sức, điều kiện kích hoạt trả nợ.
- Ưu tiên giải rủi ro lớn nhất sớm (spike, walking skeleton, thử tải).

## 8. Quản trị nhẹ

- Quyết định có ý nghĩa qua **ADR** và đánh giá đồng cấp; không cần hội đồng nặng nề.
- **Nguyên tắc kiến trúc** ngắn (5–10 điều) và có hệ quả, để đội tự quyết trong khuôn khổ.
- **Đường lát vàng (paved road)**: bộ công nghệ và mẫu được hỗ trợ; đi lệch phải có lý do.
- Rà soát kiến trúc định kỳ và khi có thay đổi lớn về tải, tổ chức, ràng buộc.
- Đo sức khỏe kỹ thuật bằng chỉ số phân phối (DORA) và tín hiệu vận hành (sự cố, thời gian khôi phục, độ phủ kiểm thử hợp đồng).

## 9. Phản mẫu thường gặp

1. **Distributed monolith**: chia dịch vụ nhưng ghép chặt, chung CSDL, triển khai cùng lúc.
2. **Tách microservices quá sớm** khi miền chưa rõ và đội nhỏ.
3. **Resume-driven / golden hammer**: chọn công nghệ vì thịnh hành hoặc vì quen một công cụ.
4. **Big ball of mud**: không ranh giới, ai gọi cũng được.
5. **Shared database** giữa nhiều dịch vụ/đội.
6. **Chatty services**: gọi chéo quá nhiều, độ trễ và lỗi nhân lên.
7. **Thiếu quan sát và thiếu timeout/retry hợp lý** (lỗi dây chuyền).
8. **Ivory tower**: kiến trúc sư không tham gia thực thi, tài liệu không khớp thực tế.
9. **Over-engineering**: lớp trừu tượng, tính linh hoạt không ai yêu cầu.
10. **Không có phương án thoát** với dịch vụ/nhà cung cấp lõi.
11. **Bỏ qua vận hành**: không runbook, không kế hoạch sao lưu/khôi phục, không SLO.
12. **Bảo mật thêm sau**: thiết kế xong mới nghĩ tới xác thực, phân quyền, mã hóa.
