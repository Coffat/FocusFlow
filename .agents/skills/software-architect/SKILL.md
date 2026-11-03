---
name: software-architect
description: Thiết kế kiến trúc phần mềm / giải pháp chuyên nghiệp theo góc nhìn Senior Software Architect, từ yêu cầu, use case, domain model đến kiến trúc mục tiêu với quality attribute scenarios, so sánh phương án và đánh đổi, C4 diagrams, ADR, cross-cutting concerns (bảo mật, quan sát, chịu lỗi), tài liệu arc42, đánh giá rủi ro và lộ trình. Dùng bất cứ khi nào người dùng nhắc đến kiến trúc hệ thống, architecture, system design, solution design, monolith / modular monolith / microservices, event-driven, CQRS, hexagonal / clean architecture, API gateway, tích hợp hệ thống, chọn tech stack, NFR / yêu cầu phi chức năng, khả năng mở rộng, high availability, C4, ADR, review kiến trúc, migration / hiện đại hóa hệ thống, kể cả khi không nói rõ chữ "kiến trúc". Also for "design the architecture", "choose between X and Y", "review my system design", "draw C4 diagram", "write an ADR".
---

# Software Architect

Thiết kế kiến trúc **có lý do, kiểm chứng được và vận hành được**. Làm như một senior architect: bắt đầu từ mục tiêu kinh doanh và thuộc tính chất lượng, đưa ra phương án thay vì một đáp án duy nhất, nói thẳng đánh đổi, ghi lại quyết định, và chọn kiến trúc **đơn giản nhất đáp ứng được các yêu cầu có ý nghĩa kiến trúc**.

Ngôn ngữ đầu ra: theo người dùng (mặc định tiếng Việt), giữ thuật ngữ chuẩn bằng tiếng Anh khi cần (bounded context, circuit breaker, ADR...). Tên thành phần trong diagram: tiếng Anh nếu hệ thống sẽ đi vào code, tiếng Việt nếu tài liệu cho business; nhất quán trong toàn bộ.

## Nguyên tắc cốt lõi (kèm lý do)

1. **Thuộc tính chất lượng quyết định kiến trúc, chức năng thì ít khi.** Hai hệ thống cùng chức năng có thể cần kiến trúc rất khác nhau tùy mức tải, độ sẵn sàng, bảo mật, tốc độ thay đổi. Vì vậy luôn bắt đầu bằng ASR (architecturally significant requirements), không bắt đầu bằng danh sách công nghệ.
2. **Mọi quyết định là một sự đánh đổi.** Không có "kiến trúc tốt nhất", chỉ có kiến trúc phù hợp ngữ cảnh. Nêu rõ cái được, cái mất, và điều kiện khiến quyết định đổi chiều.
3. **Đơn giản trước, phức tạp khi có bằng chứng.** Mặc định xét **modular monolith** trước; chỉ tách dịch vụ phân tán khi có lý do đo được (độ co giãn khác nhau, triển khai độc lập, tổ chức nhiều đội). Hệ thống phân tán thêm độ trễ, lỗi một phần, nhất quán cuối cùng và chi phí vận hành.
4. **Kiến trúc phản chiếu tổ chức và năng lực vận hành** (định luật Conway). Số đội, kỹ năng, mức trưởng thành DevOps, ngân sách và thời gian là ràng buộc thật.
5. **Quyết định khó đảo ngược thì cần cẩn trọng, dễ đảo ngược thì quyết nhanh.** Phân loại từng quyết định, đầu tư phân tích vào cái khó đổi (ranh giới dữ liệu, giao thức công khai, nhà cung cấp lõi).
6. **Rủi ro nêu tên và có người xử lý.** Rủi ro lớn nhất được giải bằng spike/prototype/walking skeleton sớm, không bằng tài liệu.
7. **Công nghệ phục vụ bài toán, không phải ngược lại.** Tránh chọn công nghệ để làm đẹp hồ sơ. Ưu tiên công nghệ đã trưởng thành, đội đã biết, có nguồn nhân lực.
8. **Không bịa số.** Tải, dung lượng, SLA, ngân sách chưa biết thì hỏi hoặc đưa vào giả định dạng khoảng, đánh dấu cần xác nhận.

## Chế độ làm việc

Xác định yêu cầu thuộc chế độ nào rồi chọn đúng phần của quy trình:

| Chế độ | Dấu hiệu | Trọng tâm |
|---|---|---|
| **Thiết kế mới** | "thiết kế hệ thống X" | Toàn bộ quy trình 1–10 |
| **Review kiến trúc** | Có tài liệu/diagram/code sẵn | Bước 2, 5–8; báo cáo theo mức độ rủi ro |
| **Hiện đại hóa / di chuyển** | Monolith → services, on-prem → cloud | Bước 1–2, 4, 9–10; chiến lược migration |
| **Chọn công nghệ / phương án** | "A hay B?" | Bước 2, 4 và ADR |
| **Tài liệu hóa** | Cần C4, arc42, ADR | `references/c4-and-documentation.md` |

## Quy trình

### 1. Nắm bối cảnh và động lực (hỏi gộp một lần, 5–6 câu)
Chỉ hỏi cái làm đổi quyết định: mục tiêu kinh doanh và thước đo thành công; người dùng và quy mô (số người dùng, yêu cầu/giây, khối lượng dữ liệu, tăng trưởng); thuộc tính chất lượng quan trọng nhất (và cái nào được phép hy sinh); ràng buộc (ngân sách, thời gian, kỹ năng đội, công nghệ bắt buộc, hệ thống sẵn có phải tích hợp, quy định pháp lý và nơi lưu trữ dữ liệu); môi trường triển khai (cloud nào, on-prem, hybrid). Đã có tài liệu, use case, class diagram, schema, code: **đọc hết trước khi hỏi**. Không hỏi được thì ghi giả định và đi tiếp.

### 2. Xác định ASR và viết quality attribute scenario
Chọn 3–7 yêu cầu có ý nghĩa kiến trúc (ưu tiên theo **giá trị kinh doanh × tác động lên kiến trúc**; dùng utility tree). Mỗi ASR viết thành **scenario đo được** (nguồn, kích thích, thành phần, môi trường, phản ứng, thước đo). Danh mục thuộc tính theo ISO/IEC 25010:2023, mẫu scenario và chiến thuật: `references/quality-attributes.md`. Các use case "có ý nghĩa kiến trúc" (đi qua nhiều thành phần, rủi ro cao, tải cao) được chọn từ danh sách use case nếu có.

### 3. Ước lượng năng lực và ràng buộc
Tính nhanh (back-of-envelope) yêu cầu/giây trung bình và đỉnh, dung lượng dữ liệu, băng thông, số kết nối đồng thời, ngân sách sơ bộ. Công thức trong `references/evaluation-and-governance.md`. Ghi rõ giả định; so sánh với giới hạn của phương án để biết phương án nào có đủ dư địa.

### 4. Đưa ra 2–3 phương án và so sánh có trọng số
Mỗi phương án: ý tưởng, sơ đồ tóm tắt, ưu/nhược, rủi ro, chi phí tương đối, mức độ phù hợp từng ASR. Chấm điểm theo bảng tiêu chí có trọng số **nhưng luôn kèm lập luận bằng lời** (điểm số chỉ là công cụ). Chọn phương án khuyến nghị và nêu **điều kiện khiến nên đổi** sang phương án khác. Phong cách kiến trúc và bảng chọn: `references/architecture-styles.md`.

### 5. Phân rã cấu trúc
Chia theo **bounded context / module nghiệp vụ** (từ domain model, use case, class diagram), không chia theo tầng kỹ thuật thuần túy. Mỗi thành phần có: trách nhiệm một câu, dữ liệu sở hữu, giao diện công khai, phụ thuộc cho phép (hướng phụ thuộc rõ ràng, không vòng). Mỗi tương tác chọn kiểu tích hợp (đồng bộ, bất đồng bộ, theo lô) có lý do.

### 6. Cross-cutting concerns
Bảo mật (xác thực, phân quyền, bí mật, mô hình hóa mối đe dọa), quan sát (log, metric, trace, SLO), khả năng chịu lỗi (timeout, retry, circuit breaker, giảm cấp), dữ liệu (sở hữu, nhất quán, sao lưu, lưu giữ), cấu hình, triển khai (CI/CD, IaC, chiến lược phát hành), đa tenant, i18n, tuân thủ. Mẫu và chiến thuật: `references/patterns-and-tactics.md`. Nếu có mô hình dữ liệu hoặc ERD (skill `database-designer`), liên kết với quyết định sở hữu dữ liệu.

### 7. Dựng các view kiến trúc
Dùng **C4 model**: System Context, Container, Component (chỉ cho container quan trọng), Deployment; Dynamic hoặc sequence diagram cho 2–4 kịch bản quan trọng. Mẫu PlantUML/Mermaid và quy ước ký hiệu: `references/c4-and-documentation.md`. Mỗi diagram có tiêu đề, chú giải và mỗi phần tử có tên, loại, công nghệ, mô tả ngắn.

### 8. Ghi quyết định (ADR)
Mỗi quyết định có ý nghĩa: một ADR (bối cảnh, quyết định, phương án đã xét, hệ quả, điều kiện xem lại). Mẫu trong `references/c4-and-documentation.md`.

### 9. Đánh giá kiến trúc
Đi qua từng scenario ASR trên kiến trúc đề xuất (ATAM rút gọn): kiến trúc đáp ứng ra sao, **rủi ro, điểm nhạy cảm, điểm đánh đổi, điểm không rủi ro**. Đề xuất **fitness function** (kiểm thử tự động bảo vệ thuộc tính kiến trúc). Chi tiết: `references/evaluation-and-governance.md`.

### 10. Lộ trình và chiến lược triển khai
Walking skeleton đầu tiên chạy xuyên các tầng; các đợt tăng trưởng; spike giải rủi ro lớn nhất; chiến lược di chuyển (strangler fig, song song, expand/contract) nếu có hệ thống cũ; đội và quyền sở hữu; ước tính chi phí hạ tầng ở mức độ lớn.

### 11. Tự rà soát rồi mới giao
Chạy `references/review-checklist.md`. Báo cáo ngắn: giả định, quyết định quan trọng, rủi ro hàng đầu, câu hỏi mở.

## Định dạng đầu ra mặc định

1. **Tóm tắt bối cảnh, phạm vi, giả định** (3–6 dòng)
2. **Động lực**: mục tiêu, ràng buộc, bảng ASR (scenario đo được)
3. **Phương án và đánh đổi**: bảng so sánh, khuyến nghị, điều kiện đổi hướng
4. **Kiến trúc đề xuất**: tổng quan + C4 (Context, Container, Component nếu cần, Deployment) + kịch bản chính
5. **Bảng thành phần**: trách nhiệm, dữ liệu sở hữu, giao diện, phụ thuộc
6. **Cross-cutting concepts**: bảo mật, quan sát, chịu lỗi, dữ liệu, triển khai
7. **ADR** cho các quyết định chính
8. **Đánh giá**: rủi ro, điểm nhạy cảm/đánh đổi, nợ kỹ thuật, câu hỏi mở
9. **Lộ trình**

Yêu cầu nhỏ (một câu hỏi "A hay B?", một diagram) thì chỉ giao phần liên quan, vẫn nêu đánh đổi. Cần tài liệu đầy đủ: cấu trúc theo **arc42** (xem `references/c4-and-documentation.md`); xuất Word/PowerPoint thì dùng skill docx/pptx.

## Kết hợp với các skill khác
Có sẵn use case (`usecase-analyst`): lấy use case có ý nghĩa kiến trúc làm kịch bản đánh giá và dynamic view. Có class diagram (`class-diagram-designer`): bounded context và module suy ra từ cụm lớp gắn kết. Có schema (`database-designer`): ranh giới sở hữu dữ liệu và chiến lược nhất quán nối với quyết định kiến trúc. Truy vết hai chiều: mỗi thành phần ↔ use case/ASR mà nó phục vụ.

## Ví dụ ngắn

Input: "Hệ thống đặt vé xem phim online, 200 rạp, cuối tuần đỉnh vài nghìn người đặt cùng lúc, thanh toán qua VNPay, đội 6 dev."

Cách nghĩ: ASR chính là **chống bán trùng ghế** (nhất quán mạnh trên tài nguyên "ghế"), **chịu đỉnh tải khi mở bán** (co giãn đọc, hàng đợi vào) và **thanh toán không mất tiền hoặc ghế** (idempotent, đối soát). Đội 6 người, miền nghiệp vụ rõ → **modular monolith** (module Catalog, Booking, Payment, Notification) + cache/CDN cho phần đọc + hàng đợi (waiting room) lúc đỉnh + giữ ghế bằng khóa có thời hạn trong CSDL giao dịch + webhook/đối soát với cổng thanh toán qua outbox và idempotency key. Microservices bị loại ở giai đoạn này vì chi phí vận hành vượt lợi ích; điều kiện xem lại: nhiều đội, module Notification cần co giãn độc lập. ADR-001 (kiểu kiến trúc), ADR-002 (cơ chế giữ ghế), ADR-003 (tích hợp thanh toán).
