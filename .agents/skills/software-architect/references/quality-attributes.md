# Thuộc tính chất lượng (Quality Attributes)

## Mục lục
1. Mô hình ISO/IEC 25010:2023
2. Quality attribute scenario (QAS)
3. Utility tree và ưu tiên
4. Chiến thuật (tactics) theo thuộc tính
5. Số liệu hay dùng: khả dụng, SLO, RTO/RPO
6. Câu hỏi khai thác NFR

## 1. Mô hình ISO/IEC 25010:2023 (chất lượng sản phẩm)

Phiên bản 2023 có **chín** đặc tính. So với bản 2011: *Usability* đổi thành **Interaction capability**, *Portability* đổi thành **Flexibility**, thêm **Safety**, và *Security* có thêm tiểu đặc tính *Resistance*. Tên tiểu đặc tính dưới đây là bản tóm tắt để định hướng; dùng văn bản chuẩn khi cần trích dẫn chính thức.

| Đặc tính | Ý chính | Tiểu đặc tính (tóm tắt) |
|---|---|---|
| Functional suitability | Chức năng đáp ứng nhu cầu | completeness, correctness, appropriateness |
| Performance efficiency | Hiệu năng so với tài nguyên | time behaviour, resource utilization, capacity |
| Compatibility | Cùng tồn tại và trao đổi với hệ khác | co-existence, interoperability |
| Interaction capability | Người dùng đạt mục tiêu hiệu quả (trước đây Usability) | learnability, operability, user error protection, inclusivity, ... |
| Reliability | Chạy đúng theo thời gian | faultlessness, availability, fault tolerance, recoverability |
| Security | Bảo vệ thông tin và hệ thống | confidentiality, integrity, non-repudiation, accountability, authenticity, resistance |
| Maintainability | Dễ sửa đổi | modularity, reusability, analysability, modifiability, testability |
| Flexibility | Thích nghi môi trường mới (trước đây Portability) | adaptability, scalability, installability, replaceability |
| Safety | Tránh gây hại cho người, tài sản, môi trường | operational constraint, risk identification, fail safe, hazard warning, safe integration |

Ghi chú thực hành: các thuộc tính vận hành **observability, deployability, operability, cost-efficiency** không phải đặc tính riêng của ISO 25010 nhưng thường quan trọng với kiến trúc; đưa vào như thuộc tính bổ sung (map về Maintainability/Flexibility/Performance khi cần đối chiếu chuẩn). Các khung cloud (AWS Well-Architected, Azure Well-Architected) dùng trụ cột vận hành, bảo mật, độ tin cậy, hiệu năng, tối ưu chi phí (AWS thêm bền vững); dùng làm danh sách kiểm tra bổ sung, kiểm tra phiên bản hiện hành khi trích dẫn.

## 2. Quality attribute scenario (QAS)

Mỗi yêu cầu chất lượng viết thành 6 thành phần (Bass, Clements, Kazman):

| Thành phần | Câu hỏi |
|---|---|
| **Source** | Ai/cái gì tạo kích thích (người dùng, hệ thống ngoài, kẻ tấn công, lỗi phần cứng)? |
| **Stimulus** | Sự kiện gì xảy ra? |
| **Artifact** | Phần nào của hệ thống bị tác động? |
| **Environment** | Trong điều kiện nào (bình thường, quá tải, giờ cao điểm, sự cố)? |
| **Response** | Hệ thống phải làm gì? |
| **Response measure** | Đo bằng gì, ngưỡng bao nhiêu? |

Ví dụ (số liệu chỉ minh họa, phải thay bằng số của dự án):

- **Hiệu năng**: Khi 3.000 người dùng đồng thời tìm suất chiếu vào giờ mở bán (môi trường: tải đỉnh), hệ thống trả kết quả tìm kiếm với p95 ≤ 500 ms và tỷ lệ lỗi < 0,1%.
- **Nhất quán/độ đúng**: Khi hai khách đặt cùng một ghế trong cùng khoảnh khắc, đúng một giao dịch thành công, giao dịch còn lại nhận thông báo "ghế không còn"; không bao giờ bán trùng (0 sự cố/tháng).
- **Khả dụng**: Khi một node ứng dụng chết giữa giờ làm việc, lưu lượng tự chuyển sang node khác trong ≤ 30 giây, không mất giao dịch đã xác nhận.
- **Khôi phục**: Khi mất cả vùng chính, hệ thống khôi phục với RPO ≤ 5 phút và RTO ≤ 1 giờ.
- **Bảo mật**: Khi người dùng thường cố truy cập hồ sơ của người khác qua API, hệ thống từ chối với 403, ghi log kiểm toán, và cảnh báo nếu lặp lại > 10 lần/phút.
- **Khả năng sửa đổi**: Khi cần thêm một cổng thanh toán mới, chỉ phải viết một adapter mới và cấu hình; ≤ 5 ngày người, không sửa module Booking.
- **Khả năng triển khai**: Khi có commit vào nhánh chính, pipeline build, kiểm thử và triển khai lên staging trong ≤ 20 phút; triển khai production không gián đoạn.
- **Quan sát**: Khi tỷ lệ lỗi dịch vụ vượt 2% trong 5 phút, đội trực nhận cảnh báo trong ≤ 2 phút kèm trace id để truy vết.

Scenario thiếu thước đo ("hệ thống phải nhanh", "dễ mở rộng") là **chưa dùng được**; hỏi lại hoặc đề xuất giá trị kèm đánh dấu cần xác nhận.

## 3. Utility tree và ưu tiên

Gốc "Utility" → nhánh là thuộc tính → nhánh con là mối quan tâm → lá là scenario. Mỗi lá chấm hai trục **(giá trị kinh doanh: H/M/L, độ khó/tác động kiến trúc: H/M/L)**. Cặp (H,H) là ASR chính; thiết kế và đánh giá tập trung vào chúng. Số ASR chính nên ≤ 5–7; nhiều hơn thì tiêu chí chưa được ưu tiên.

Khi các thuộc tính xung đột (hiệu năng vs bảo mật, linh hoạt vs đơn giản, nhất quán vs khả dụng): ghi thành **điểm đánh đổi** và để chủ sản phẩm/nhà tài trợ chọn.

## 4. Chiến thuật theo thuộc tính

| Thuộc tính | Chiến thuật |
|---|---|
| **Khả dụng** | Phát hiện lỗi (health check, heartbeat, monitor). Phục hồi: dự phòng chủ động/bị động, retry, rollback, failover. Phòng ngừa: loại bỏ khỏi phục vụ, giao dịch, kiểm tra tiền điều kiện. Giảm cấp có kiểm soát (graceful degradation) |
| **Hiệu năng** | Giảm nhu cầu: giới hạn tốc độ, ưu tiên hóa yêu cầu, giảm độ chi tiết. Quản lý tài nguyên: song song, cache, nhân bản, hàng đợi san tải, tăng hiệu quả thuật toán, tối ưu truy vấn/index |
| **Co giãn** | Ứng dụng không giữ trạng thái; trạng thái đẩy ra kho dữ liệu/cache; scale ngang; tách đọc/ghi; sharding/partition; xử lý bất đồng bộ qua hàng đợi |
| **Bảo mật** | Phát hiện (giám sát, audit, IDS). Chống chịu (xác thực, phân quyền, mã hóa, giảm bề mặt tấn công, phân đoạn mạng, ít đặc quyền nhất). Phản ứng (cách ly, thu hồi). Khôi phục (sao lưu, phục hồi) |
| **Khả năng sửa đổi** | Giảm ghép nối (giao diện ổn định, trung gian, event), tăng gắn kết (một trách nhiệm/module), trì hoãn ràng buộc (cấu hình, plugin, dependency injection) |
| **Khả năng kiểm thử** | Điểm quan sát/điều khiển, cô lập phụ thuộc, hợp đồng (contract test), dữ liệu kiểm thử tái lập |
| **Khả năng triển khai** | CI/CD, hạ tầng dạng mã, phát hành không downtime (blue-green, canary), feature flag, cấu hình ngoài mã |
| **Quan sát** | Log có cấu trúc + correlation id, metric (RED/USE), distributed tracing, dashboard theo SLO |
| **Tương thích** | Chuẩn mở, versioning API, tương thích ngược/xuôi, lớp chống hỏng hóc (anti-corruption layer) |
| **Chi phí** | Right-sizing, autoscaling, tầng lưu trữ theo độ nóng, reserved/spot, dừng môi trường không dùng, theo dõi chi phí theo tính năng/tenant |

## 5. Số liệu hay dùng

Khả dụng và thời gian ngừng cho phép (làm tròn):

| Khả dụng | Ngừng/năm | Ngừng/tháng (30 ngày ≈ 43.200 phút) |
|---|---|---|
| 99% | 3,65 ngày | 7,2 giờ |
| 99,9% | 8,76 giờ | 43,2 phút |
| 99,95% | 4,38 giờ | 21,6 phút |
| 99,99% | 52,6 phút | 4,32 phút |
| 99,999% | 5,26 phút | 26 giây |

- **Nối tiếp**: hệ thống cần cả A và B hoạt động → khả dụng = a × b (0,999 × 0,999 ≈ 0,998). Nhiều phụ thuộc đồng bộ **làm giảm** khả dụng tổng.
- **Song song (dự phòng độc lập)**: 1 − (1 − a)ⁿ. Giả định độc lập hiếm khi đúng hoàn toàn (cùng vùng, cùng bản phát hành lỗi).
- **SLI** = chỉ số đo (tỉ lệ yêu cầu thành công, độ trễ p95); **SLO** = mục tiêu nội bộ cho SLI; **SLA** = cam kết với khách, thường lỏng hơn SLO và có chế tài. **Error budget** = 1 − SLO, dùng cân bằng giữa phát hành tính năng và độ ổn định.
- **RTO** = thời gian tối đa chấp nhận được để khôi phục dịch vụ; **RPO** = lượng dữ liệu tối đa chấp nhận được mất (tính theo thời gian). RPO ≈ 0 cần sao chép đồng bộ; RTO nhỏ cần hạ tầng dự phòng sẵn (chi phí tăng mạnh).
- Hiệu năng: dùng **phân vị** (p50/p95/p99), không dùng trung bình; đo cả độ trễ đuôi.

## 6. Câu hỏi khai thác NFR

- Bao nhiêu người dùng (tổng, đồng thời, đỉnh)? Đỉnh khi nào, kéo dài bao lâu? Tăng trưởng 1–3 năm?
- Độ trễ chấp nhận được cho thao tác quan trọng nhất? Có thao tác nào có thể bất đồng bộ?
- Gián đoạn tối đa chấp nhận được? Giờ vận hành (24/7 hay giờ hành chính)? Cửa sổ bảo trì?
- Mất dữ liệu chấp nhận được không (RPO)? Khôi phục sau thảm họa bao lâu (RTO)?
- Dữ liệu nhạy cảm nào? Quy định áp dụng (dữ liệu cá nhân, tài chính, ngành)? Dữ liệu có bắt buộc lưu trong nước không?
- Cần kiểm toán, truy vết ai làm gì? Lưu bao lâu?
- Tích hợp với hệ thống nào, giao thức nào, ai sở hữu, SLA của họ ra sao?
- Tần suất thay đổi nghiệp vụ? Phần nào hay đổi nhất?
- Đội bao nhiêu người, kỹ năng gì, đã vận hành hệ thống phân tán chưa?
- Ngân sách hạ tầng và nhân sự? Thời hạn bắt buộc?
