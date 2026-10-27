# 08 — Mở rộng cho hệ thống AI / LLM / Agent

Đọc khi SRS/UC/sơ đồ mô tả chatbot, RAG, agent, multi-agent, tính năng sinh nội dung, hoặc mô hình ML ra quyết định. Các rule này **bổ sung** cho 01–06, không thay thế.

Mục lục: A. Đặc tả hành vi phi tất định · B. Guardrail & an toàn · C. Human-in-the-loop · D. Tool & tích hợp · E. Dữ liệu & RAG · F. Đánh giá & chấp nhận · G. Vận hành · H. Pháp lý & quản trị · I. Ảnh hưởng lên UML

## A. Đặc tả hành vi phi tất định

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| AI-A01 | Phân định phần **tất định** (quy tắc, quyền, tính toán) và **xác suất** (sinh văn bản, phân loại). Yêu cầu tất định (số tiền, quyền, trạng thái) không được giao hoàn toàn cho LLM | "Agent tự quyết định hoàn tiền" không có quy tắc/ngưỡng | S1–S2 |
| AI-A02 | Phạm vi năng lực & ngoài phạm vi (out-of-scope intents), hành vi khi **không biết/không chắc** (từ chối, hỏi lại, chuyển người) | Không nói agent xử lý câu hỏi ngoài miền thế nào | S2 |
| AI-A03 | Tiêu chí chấp nhận là **ngưỡng thống kê trên bộ đánh giá** (accuracy/precision/recall/groundedness/refusal-rate) thay vì "trả lời đúng" | AC dạng "câu trả lời chính xác" | S2 |
| AI-A04 | Ngôn ngữ, giọng điệu, độ dài, định dạng đầu ra, persona; xử lý tiếng Việt có/không dấu, viết tắt, code-switching | Không nêu khi người dùng Việt | S3 |
| AI-A05 | Bối cảnh hội thoại: độ dài memory, tóm tắt, quên theo yêu cầu, ranh giới phiên | Không nói | S3 |

## B. Guardrail & an toàn

| ID | Kiểm tra | Sev |
|---|---|---|
| AI-B01 | Mối đe dọa được liệt kê theo **OWASP Top 10 for LLM Applications (2025)**: prompt injection (trực tiếp & gián tiếp qua tài liệu/web/email), lộ dữ liệu nhạy cảm, excessive agency, rò rỉ system prompt, vector/embedding weakness, misinformation, unbounded consumption | S1–S2 |
| AI-B02 | Nguyên tắc: **nội dung lấy từ bên ngoài là dữ liệu, không là lệnh**; tool có quyền tối thiểu; hành động ghi/xóa/chuyển tiền cần xác nhận | S1 |
| AI-B03 | Bộ lọc đầu vào/đầu ra: PII, nội dung độc hại, chủ đề cấm; hành vi khi chặn (thông báo gì, có log không) | S2 |
| AI-B04 | Ranh giới dữ liệu theo người dùng/tenant trong truy xuất (RAG) và bộ nhớ; không rò chéo | S1 |
| AI-B05 | Giới hạn tài nguyên: token, số bước agent, số tool call, thời gian, chi phí/người dùng; chống vòng lặp vô hạn | S2 |
| AI-B06 | Hành vi khi người dùng cố vượt rào (jailbreak) và leo thang | S3 |

## C. Human-in-the-loop (HITL)

| ID | Kiểm tra | Sev |
|---|---|---|
| AI-C01 | Danh mục hành động theo **mức rủi ro** → mức tự động hóa (tự động / đề xuất rồi người duyệt / chỉ người làm) | S1–S2 |
| AI-C02 | Điểm duyệt: ai duyệt, trong bao lâu, dữ liệu hiển thị để duyệt đủ để quyết định, timeout, người thay thế | S2 |
| AI-C03 | Chuyển giao sang người (handoff): điều kiện kích hoạt, ngữ cảnh chuyển kèm, hàng đợi, giờ làm việc | S2 |
| AI-C04 | Quyền ghi đè/hoàn tác của người; kết quả duyệt được lưu làm dữ liệu cải thiện (nếu có, có đồng ý) | S3 |
| AI-C05 | Tránh "rubber-stamping": thiết kế UI/khối lượng duyệt khả thi, lấy mẫu kiểm tra chất lượng | S3 |

## D. Tool & tích hợp

| ID | Kiểm tra | Sev |
|---|---|---|
| AI-D01 | Mỗi tool có **hợp đồng**: mô tả, tham số (kiểu, ràng buộc), kết quả, lỗi, side-effect, **idempotency**, quyền yêu cầu, timeout, retry | S2 |
| AI-D02 | Tool xác thực thay mặt người dùng (delegated, scope tối thiểu), không dùng khóa dịch vụ rộng quyền | S1–S2 |
| AI-D03 | Xử lý lỗi tool: tool lỗi/chậm/trả dữ liệu sai → agent làm gì; không bịa kết quả | S2 |
| AI-D04 | Thứ tự & song song gọi tool; transaction/bù trừ (saga) khi nhiều bước ghi | S2 |
| AI-D05 | Multi-agent: vai trò, giao thức trao đổi, ai giữ trạng thái chung, xử lý bất đồng giữa agent, quyền từng agent | S2 |
| AI-D06 | Phiên bản & thay đổi schema tool/mô hình ảnh hưởng thế nào đến hành vi | S3 |

## E. Dữ liệu & RAG

| ID | Kiểm tra | Sev |
|---|---|---|
| AI-E01 | Nguồn tri thức: danh mục, chủ sở hữu, độ tươi, tần suất cập nhật, quyền truy cập theo tài liệu | S2 |
| AI-E02 | Trích dẫn nguồn trong câu trả lời, hành vi khi không tìm thấy (không bịa), xung đột giữa nguồn | S2 |
| AI-E03 | Chiến lược chia đoạn, embedding, lọc metadata, re-rank được nêu ở mức yêu cầu (không bắt chọn công nghệ) | S4 |
| AI-E04 | Dữ liệu cá nhân trong prompt/log/trace/huấn luyện: có gửi cho nhà cung cấp mô hình bên thứ ba không; vùng lưu trữ; thời gian giữ; có dùng để huấn luyện không | S1–S2 |
| AI-E05 | Chất lượng & kiểm duyệt dữ liệu nạp; quy trình xóa tài liệu → xóa khỏi chỉ mục | S2 |

## F. Đánh giá & chấp nhận

| ID | Kiểm tra | Sev |
|---|---|---|
| AI-F01 | Bộ **golden set / eval set** có kích thước, phân bố (bình thường, biên, đối kháng, tiếng Việt), chủ sở hữu, quy trình cập nhật | S2 |
| AI-F02 | Chỉ số & ngưỡng go/no-go theo từng loại tác vụ; phân tách lỗi nghiêm trọng (hallucination ở tình huống nhạy cảm) với lỗi nhẹ | S2 |
| AI-F03 | Đánh giá hồi quy khi đổi mô hình/prompt/tool/dữ liệu; A/B, canary, rollback | S2 |
| AI-F04 | Red-teaming trước phát hành; phạm vi và tần suất | S3 |
| AI-F05 | Phương pháp chấm (người/LLM-as-judge) và kiểm định độ tin cậy của người chấm | S3 |

## G. Vận hành

| ID | Kiểm tra | Sev |
|---|---|---|
| AI-G01 | Quan sát: trace từng bước (prompt, tool call, kết quả), dấu vết tách khỏi PII hoặc che dấu; thời gian lưu | S2 |
| AI-G02 | SLO riêng: latency (TTFT, tổng), độ khả dụng, chi phí/lượt, tỷ lệ lỗi/từ chối/handoff | S2 |
| AI-G03 | Dự phòng khi nhà cung cấp mô hình lỗi/hết hạn mức: fallback model, hàng đợi, thông báo | S2 |
| AI-G04 | Quản lý phiên bản mô hình/prompt/cấu hình; ghi lại phiên bản cho mỗi phản hồi (audit) | S2 |
| AI-G05 | Kênh phản hồi người dùng (👍/👎, báo lỗi) và vòng cải tiến | S3 |
| AI-G06 | Minh bạch với người dùng: cho biết đang tương tác với AI, giới hạn, cách xin gặp người | S2 |

## H. Pháp lý & quản trị (luôn xác minh hiệu lực hiện hành)

Các văn bản cần cân nhắc tùy thị trường và rủi ro: Luật Trí tuệ nhân tạo của Việt Nam, Luật Bảo vệ dữ liệu cá nhân và Luật Dữ liệu của Việt Nam, GDPR, **EU AI Act** (phân loại rủi ro; nghĩa vụ cho hệ thống rủi ro cao và minh bạch; thời điểm áp dụng từng nhóm nghĩa vụ đang được điều chỉnh), ISO/IEC 42001 (hệ thống quản lý AI), NIST AI RMF.

| ID | Kiểm tra | Sev |
|---|---|---|
| AI-H01 | Đã **phân loại mức rủi ro** của hệ thống AI theo khung pháp lý áp dụng, hoặc nêu rõ chưa phân loại | S2 |
| AI-H02 | Quyết định tự động ảnh hưởng đáng kể tới cá nhân (tín dụng, tuyển dụng, bảo hiểm, y tế, giáo dục): quyền giải thích, phản đối, can thiệp của con người | S1–S2 |
| AI-H03 | Bản quyền/nguồn dữ liệu huấn luyện & nội dung sinh ra; gắn nhãn nội dung do AI tạo nếu bắt buộc | S2 |
| AI-H04 | Trách nhiệm & chủ sở hữu (RACI) cho giám sát mô hình, xử lý sự cố, báo cáo sự cố | S3 |

Khi nêu điều khoản cụ thể: dùng công cụ tìm kiếm để xác minh; không có công cụ thì ghi `[CẦN XÁC MINH]` và chỉ nêu tên văn bản, không nêu số điều/ngày hiệu lực từ trí nhớ.

## I. Ảnh hưởng lên các sơ đồ UML

- **Use case diagram**: actor gồm cả *Người duyệt (HITL)*, *Quản trị nội dung/tri thức*, *Hệ thống LLM/nhà cung cấp mô hình* (actor phụ), *Quản trị đánh giá*. Thiếu các actor này là GAP phổ biến.
- **Use case spec**: thêm luồng ngoại lệ đặc thù AI — tool lỗi, độ tin cậy thấp, vi phạm guardrail, hết hạn mức token, người dùng từ chối đề xuất, handoff.
- **Class**: có `Conversation`, `Message`, `ToolCall`, `Approval`, `KnowledgeDocument/Chunk`, `EvaluationRun`, `PromptVersion`; kiểm tra quan hệ & vòng đời, trường PII.
- **DB**: lưu trace, phiên bản prompt/mô hình, kết quả duyệt, nhật ký guardrail; chỉ mục theo hội thoại/người dùng; chính sách xóa PII trong trace.
- **State**: vòng đời tác vụ agent (`Received → Planning → Awaiting_Tool → Awaiting_Approval → Executing → Completed/Failed/Escalated/Cancelled`), có timeout cho `Awaiting_*`, idempotency khi duyệt/tool trả trùng, cấm transition ghi khi chưa duyệt.

## Ví dụ finding mẫu

- **AI-B02 (S1, HIGH)**: Agent đọc email khách và có tool `refund_order` nhưng SRS không yêu cầu tách nội dung email khỏi chỉ thị hệ thống hay duyệt trước khi hoàn tiền.
  *Bằng chứng*: UC-07 bước 3 "Agent đọc nội dung email và thực hiện yêu cầu của khách"; bước 5 "gọi refund_order".
  *Hậu quả*: email chứa chỉ thị ẩn (prompt injection gián tiếp) có thể kích hoạt hoàn tiền trái phép.
  *Đề xuất (ĐỀ XUẤT)*: coi email là dữ liệu không tin cậy; hoàn tiền vượt ngưỡng X hoặc mọi hoàn tiền do agent đề xuất phải qua duyệt người; tool dùng quyền tối thiểu theo người dùng và có giới hạn số tiền/lần.
