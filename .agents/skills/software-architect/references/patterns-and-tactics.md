# Mẫu và chiến thuật kiến trúc

## Mục lục
1. Tích hợp và API
2. Chịu lỗi và co giãn
3. Dữ liệu và nhất quán
4. Bảo mật
5. Quan sát
6. Triển khai và vận hành
7. Đa tenant
8. Hiện đại hóa hệ thống cũ
9. Bối cảnh Việt Nam

## 1. Tích hợp và API

| Mẫu | Dùng khi | Lưu ý |
|---|---|---|
| **API Gateway** | Một điểm vào cho client: xác thực, giới hạn tốc độ, định tuyến, TLS | Đừng nhồi logic nghiệp vụ; tránh thành nút thắt/điểm lỗi duy nhất (chạy dự phòng) |
| **BFF (Backend for Frontend)** | Web/mobile cần dữ liệu và độ chi tiết khác nhau | Mỗi BFF một đội/client; tránh trùng logic nghiệp vụ |
| **REST** | Tài nguyên, cache HTTP, công khai rộng | Versioning (đường dẫn hoặc header), phân trang, lỗi theo chuẩn (vd. RFC 9457 Problem Details) |
| **gRPC** | Nội bộ, hiệu năng, hợp đồng chặt, streaming | Cần cổng chuyển đổi cho trình duyệt |
| **GraphQL** | Client cần tự chọn dữ liệu, nhiều nguồn | Kiểm soát độ sâu/độ phức tạp truy vấn, N+1, phân quyền theo trường |
| **Webhook** | Thông báo sự kiện ra bên ngoài | Ký chữ ký, retry, idempotency, xác minh nguồn |
| **Message queue / topic** | Bất đồng bộ, san tải | Idempotent consumer, DLQ, thứ tự theo khóa, giám sát độ trễ |
| **Anti-corruption layer** | Bảo vệ mô hình nội bộ khỏi hệ thống ngoài/legacy | Dịch mô hình ở biên |
| **Adapter theo cổng nhà cung cấp** | Nhiều cổng thanh toán/vận chuyển | Giao diện nội bộ ổn định, adapter thay thế được |
| **Transactional outbox** | Cần ghi dữ liệu **và** phát sự kiện nhất quán | Ghi sự kiện vào bảng outbox cùng giao dịch; tiến trình riêng đọc và phát (hoặc CDC); bên nhận idempotent |
| **Saga** | Giao dịch xuyên dịch vụ | **Orchestration** (bộ điều phối trung tâm, dễ theo dõi) hoặc **choreography** (sự kiện, ghép nối lỏng, khó nhìn tổng thể); mỗi bước có hành động bù |
| **Idempotency key** | API ghi có thể gọi lại (thanh toán, tạo đơn) | Lưu khóa + kết quả, trả lại kết quả cũ khi lặp |
| **Strangler fig** | Thay dần hệ cũ | Xem §8 |

Hợp đồng API: định nghĩa bằng đặc tả (OpenAPI, AsyncAPI, Protobuf), **contract test**, chính sách tương thích ngược, vòng đời phiên bản và ngày ngừng hỗ trợ.

## 2. Chịu lỗi và co giãn

- **Timeout** cho mọi lời gọi ra ngoài (không để mặc định vô hạn). Tổng timeout của chuỗi gọi phải nhỏ hơn timeout của người gọi ngoài cùng.
- **Retry** chỉ với thao tác idempotent, **backoff lũy thừa kèm jitter** (ngẫu nhiên), giới hạn số lần; tránh "retry storm" (lỗi khuếch đại khi mọi tầng cùng retry).
- **Circuit breaker**: ngắt khi lỗi vượt ngưỡng để bên phụ thuộc hồi phục, thử lại có kiểm soát (half-open).
- **Bulkhead**: cô lập tài nguyên (pool luồng/kết nối riêng cho từng phụ thuộc) để một phụ thuộc chậm không kéo sập toàn bộ.
- **Rate limiting / load shedding / backpressure**: giới hạn đầu vào, từ chối sớm yêu cầu ưu tiên thấp khi quá tải.
- **Graceful degradation**: tính năng không thiết yếu tắt có kiểm soát (ẩn gợi ý, dùng cache cũ) thay vì sập toàn bộ.
- **Queue-based load leveling**: hàng đợi làm đệm giữa bên sinh tải và bên xử lý; **waiting room** cho đợt mở bán đột biến.
- **Stateless service + scale ngang** sau bộ cân bằng tải; trạng thái phiên đưa ra kho dùng chung hoặc token; health check (liveness/readiness) đúng nghĩa.
- **Cache**: cache-aside là mặc định; xác định TTL, chiến lược vô hiệu hóa, chống cache stampede (khóa/ gộp yêu cầu, jitter TTL); không cache dữ liệu cần nhất quán mạnh khi chưa xét kỹ; ghi rõ độ cũ chấp nhận được.
- **Sao lưu và khôi phục**: 3-2-1, thử khôi phục định kỳ (sao lưu chưa từng khôi phục thì chưa phải sao lưu); diễn tập DR theo RTO/RPO.
- **Chaos / game day** (thử nghiệm lỗi có kiểm soát) khi hệ thống đã ổn định.

## 3. Dữ liệu và nhất quán

- **Sở hữu dữ liệu** một dịch vụ/module; nguồn sự thật duy nhất cho mỗi loại dữ liệu; chỗ khác là bản sao có nhãn.
- **Read replica** cho tải đọc (chấp nhận độ trễ sao chép); **sharding/partition** khi một nút không đủ (thiết kế khóa phân mảnh theo mẫu truy cập, tránh điểm nóng).
- **CDC** (change data capture) để đồng bộ dữ liệu sang kho khác một cách đáng tin cậy.
- **Tìm kiếm**: search engine (Elasticsearch/OpenSearch...) là bản sao đọc, không phải nguồn sự thật.
- **Quản lý schema/migration**: expand → migrate → contract; công cụ migration có phiên bản.
- **Vòng đời dữ liệu**: lưu giữ, lưu trữ lạnh, xóa/ẩn danh theo chính sách và pháp lý.
- Mô hình dữ liệu chi tiết: skill `database-designer`.

## 4. Bảo mật

- **Mô hình hóa mối đe dọa** (STRIDE: giả mạo, chỉnh sửa, chối bỏ, lộ thông tin, từ chối dịch vụ, nâng quyền) trên diagram luồng dữ liệu; phân loại tài sản, ranh giới tin cậy.
- **Defense in depth** và **ít đặc quyền nhất**; **zero trust**: không tin mạng nội bộ, xác thực/ủy quyền từng lời gọi.
- **Xác thực người dùng**: dùng giao thức chuẩn (OAuth 2.0 / OpenID Connect) với IdP thay vì tự viết; MFA; quản lý phiên/token (thời hạn ngắn, refresh, thu hồi).
- **Xác thực giữa dịch vụ**: mTLS hoặc token dịch vụ; định danh workload.
- **Phân quyền**: RBAC là điểm khởi đầu, ABAC/theo ngữ cảnh khi cần; kiểm tra ở **phía máy chủ** tại mọi điểm, kể cả kiểm tra quyền trên đối tượng (chống IDOR/BOLA).
- **Bảo vệ dữ liệu**: TLS mọi nơi; mã hóa lưu trữ; quản lý khóa (KMS/HSM); **bí mật** ở kho bí mật chuyên dụng, không trong mã nguồn/ảnh container; che dữ liệu nhạy cảm trong log.
- **Chuỗi cung ứng**: quét phụ thuộc, SBOM, ký artifact, ảnh nền tối thiểu.
- **Kiểm toán**: log bất biến cho hành động nhạy cảm; đồng hồ đồng bộ.
- Tham chiếu: OWASP Top 10, OWASP ASVS (mức xác minh), CIS benchmarks. Kiểm tra phiên bản hiện hành khi trích dẫn.

## 5. Quan sát (Observability)

- Ba trụ cột: **log có cấu trúc** (JSON, correlation/trace id), **metric** (RED cho dịch vụ: rate, errors, duration; USE cho tài nguyên: utilization, saturation, errors), **trace phân tán** (OpenTelemetry là chuẩn mở thường dùng).
- Mỗi yêu cầu mang **trace id** qua mọi thành phần và hàng đợi.
- Định nghĩa **SLI/SLO** và cảnh báo theo tốc độ đốt error budget thay vì ngưỡng tài nguyên thuần túy; cảnh báo phải **hành động được** (có runbook).
- Health endpoint, dashboard theo luồng nghiệp vụ (đơn/giờ, tỷ lệ thanh toán thành công) chứ không chỉ CPU.
- Không log dữ liệu cá nhân/bí mật; kiểm soát chi phí lưu log (lấy mẫu, lưu giữ theo mức độ).

## 6. Triển khai và vận hành

- **CI/CD** tự động: build, kiểm thử (đơn vị, tích hợp, hợp đồng), quét bảo mật, triển khai.
- **Hạ tầng dạng mã** (Terraform/Pulumi/CloudFormation/Bicep), môi trường tái lập; cấu hình ngoài mã (12-factor); phân biệt cấu hình và bí mật.
- **Chiến lược phát hành**: rolling, blue-green, canary; **feature flag** tách triển khai khỏi phát hành; có đường quay lui (rollback) đã thử.
- **Container/orchestration** (Kubernetes) chỉ khi có đủ năng lực vận hành; thay thế đơn giản hơn: PaaS, dịch vụ container được quản lý, serverless.
- **Môi trường**: dev/staging/prod; staging đủ giống prod; dữ liệu kiểm thử đã che.
- **Vận hành**: runbook, on-call, postmortem không đổ lỗi, quản lý sự cố; theo dõi chỉ số phân phối (DORA: tần suất triển khai, thời gian dẫn thay đổi, tỷ lệ thay đổi thất bại, thời gian khôi phục).
- **Chi phí**: gắn thẻ tài nguyên, ngân sách và cảnh báo, rà soát định kỳ (FinOps).

## 7. Đa tenant

Mô hình dữ liệu: schema chung + `tenant_id`, schema riêng, DB riêng (xem `database-designer/patterns.md` nếu có). Ở mức kiến trúc cần quyết định thêm: cô lập tài nguyên và "hàng xóm ồn ào" (hạn mức, giới hạn tốc độ theo tenant), cấu hình/tính năng theo tenant, định tuyến và nhận diện tenant (subdomain, token), sao lưu/khôi phục theo tenant, mô hình tính phí và đo lường sử dụng, di chuyển tenant giữa các cụm, tuân thủ nơi lưu dữ liệu theo tenant.

## 8. Hiện đại hóa hệ thống cũ

| Chiến lược | Ý tưởng | Dùng khi |
|---|---|---|
| **Strangler fig** | Đặt lớp chặn (proxy/gateway) trước hệ cũ, thay dần từng chức năng bằng hệ mới, chuyển lưu lượng từng phần | Mặc định cho thay thế dần, giảm rủi ro |
| **Branch by abstraction** | Tạo abstraction trong code, cài đặt mới song song, chuyển dần | Thay thành phần bên trong cùng cơ sở mã |
| **Chạy song song / shadow** | Hệ mới nhận bản sao lưu lượng, so sánh kết quả với hệ cũ | Cần chứng minh tương đương (tài chính, tính toán) |
| **Anti-corruption layer** | Dịch mô hình giữa cũ và mới | Hệ cũ có mô hình khó coi |
| **Expand → migrate → contract** | Thay đổi dữ liệu tương thích ngược | Chuyển schema không gián đoạn |
| **Big-bang** | Chuyển toàn bộ một lần | Chỉ khi hệ nhỏ/chuyển đổi dữ liệu đơn giản và chấp nhận rủi ro cao |

Trình tự: hiểu hệ cũ (khám phá phụ thuộc, dữ liệu, luồng), chọn "đường cắt" theo ranh giới nghiệp vụ có giá trị cao/rủi ro thấp, dựng pipeline và quan sát trước, chuyển từng lát, đo và đối soát, tắt phần cũ. Tránh "viết lại từ đầu" không có chiến lược chuyển tiếp.

## 9. Bối cảnh Việt Nam

- **Dữ liệu và pháp lý**: kiểm tra quy định hiện hành về bảo vệ dữ liệu cá nhân, an ninh mạng, **lưu trữ dữ liệu trong nước** và an toàn thông tin theo cấp độ (đặc biệt với hệ thống nhà nước, tài chính, y tế). Các quy định thay đổi: **tra văn bản hiện hành** trước khi khẳng định yêu cầu cụ thể, và ghi vào ràng buộc kiến trúc (vị trí vùng cloud, sao lưu, kênh truyền).
- **Tích hợp phổ biến**: cổng thanh toán và ví điện tử nội địa, hóa đơn điện tử, định danh điện tử, SMS brand name, vận chuyển. Dùng adapter + idempotency + đối soát định kỳ; luôn xét độ tin cậy và SLA của bên thứ ba.
- **Hạ tầng**: cloud quốc tế có vùng gần (Singapore...) hoặc nhà cung cấp trong nước; cân nhắc độ trễ, chi phí, yêu cầu lưu trữ trong nước, hỗ trợ kỹ thuật.
- **Nhân lực**: ưu tiên công nghệ có nguồn nhân lực sẵn trong đội/thị trường; chi phí tuyển dụng là một phần của TCO.
- **Địa chỉ hành chính** đã đổi sang hai cấp từ 07/2025: kiến trúc dữ liệu tham chiếu cần cập nhật được và có ánh xạ lịch sử (xem skill `database-designer`).
