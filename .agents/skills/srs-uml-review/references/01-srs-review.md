# 01 — Review SRS / BRD / FRD / PRD / User story / NFR

Mục lục: A. Cấu trúc tài liệu · B. Chất lượng từng requirement · C. Chất lượng cả tập requirement · D. Business rule · E. NFR · F. Dữ liệu · G. Tích hợp/API · H. Bảo mật & tuân thủ · I. User story/AC · J. Từ khóa cảnh báo

Cột *Sev* là mức mặc định; điều chỉnh theo ngữ cảnh (luồng cốt lõi tăng 1 bậc, phần phụ giảm 1 bậc).

## A. Cấu trúc & quản trị tài liệu

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| SRS-A01 | Có mục đích, phạm vi **in-scope / out-of-scope** rõ | Chỉ nêu "hệ thống quản lý X", không có out-of-scope | S2 |
| SRS-A02 | Mục tiêu nghiệp vụ đo được, requirement truy về mục tiêu | Mục tiêu kiểu "nâng cao trải nghiệm", FR không gắn mục tiêu | S2 |
| SRS-A03 | Stakeholder & actor/role được liệt kê, có owner cho từng nhóm requirement | Actor xuất hiện trong FR nhưng không có ở danh sách | S2 |
| SRS-A04 | Glossary cho thuật ngữ nghiệp vụ, từ viết tắt | Một thuật ngữ nhiều nghĩa ("khách hàng", "đơn", "tài khoản") | S2 |
| SRS-A05 | Giả định, ràng buộc, phụ thuộc, rủi ro được ghi | Không có mục nào; hoặc phụ thuộc hệ thống ngoài không nêu | S3 |
| SRS-A06 | Version, lịch sử thay đổi, người duyệt, trạng thái (draft/approved) | Không biết bản nào hiệu lực | S3 |
| SRS-A07 | Không còn TBD/TBC/"sẽ bổ sung"/"xem thêm" không dẫn link | Đếm TBD; TBD ở luồng cốt lõi | S2 (cốt lõi) / S3 |
| SRS-A08 | Requirement có ID duy nhất, ổn định, không tái sử dụng | Trùng ID, nhảy số do xóa không ghi nhận | S3 |
| SRS-A09 | Độ ưu tiên (MoSCoW/giá trị) và release/phase | Mọi thứ "Must" | S3 |
| SRS-A10 | Tài liệu tham chiếu (BRD, quy định, hợp đồng) có phiên bản | Link chết, "theo quy định hiện hành" không nêu quy định nào | S3 |

## B. Chất lượng từng requirement (ISO/IEC/IEEE 29148:2018)

Mỗi requirement cần: **necessary, appropriate (đúng mức trừu tượng), unambiguous, complete, singular, feasible, verifiable, correct, conforming**.

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| SRS-B01 | **Unambiguous**: một cách hiểu duy nhất | Từ mơ hồ (mục J), đại từ không rõ chỉ ai ("nó", "hệ thống đó") | S2 |
| SRS-B02 | **Singular**: một requirement = một hành vi | "Hệ thống phải A **và** B **và** C"; nhiều "phải" trong một câu | S3 |
| SRS-B03 | **Complete**: có chủ thể, hành vi, điều kiện, kết quả | Thiếu actor/trigger ("Dữ liệu sẽ được gửi đi") thể bị động | S2 |
| SRS-B04 | **Verifiable**: có tiêu chí chấp nhận quan sát/đo được | Không thể viết test pass/fail | S2 |
| SRS-B05 | **Appropriate**: đúng tầng — nói "cái gì" chứ không "như thế nào" | Chỉ định công nghệ/bảng/thuật toán trong FR mà không có ràng buộc thật | S3 |
| SRS-B06 | **Feasible**: khả thi về kỹ thuật/thời gian/chi phí | "100% uptime", "zero bug", "xử lý mọi ngôn ngữ" | S2 |
| SRS-B07 | **Correct/necessary**: không là yêu cầu thừa không truy được về nhu cầu | Gold-plating | S4 |
| SRS-B08 | Lượng từ tuyệt đối | "luôn", "không bao giờ", "tất cả", "mọi" không có ngoại lệ | S2 |
| SRS-B09 | Phủ định / điều kiện kép | "Không được không cho phép…", "trừ khi… ngoại trừ…" | S3 |
| SRS-B10 | Động từ khuyên nhủ vs ràng buộc: dùng nhất quán *phải / nên / có thể* (shall/should/may) | Trộn "cần", "nên", "sẽ", "phải" tùy hứng | S3 |
| SRS-B11 | Điều kiện tham chiếu rõ | "Nếu hợp lệ" mà không nói hợp lệ theo quy tắc nào | S2 |

**EARS** (gợi ý sửa, dùng khi câu thiếu cấu trúc):
- Ubiquitous: `Hệ thống phải <hành vi>.`
- State-driven: `Khi <trạng thái>, hệ thống phải …` (While)
- Event-driven: `Khi <sự kiện>, hệ thống phải …` (When)
- Optional feature: `Với <tính năng được bật>, hệ thống phải …` (Where)
- Unwanted behaviour: `Nếu <điều kiện lỗi>, thì hệ thống phải …` (If … then)
- Complex: kết hợp các dạng trên.

## C. Chất lượng cả tập requirement

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| SRS-C01 | **Consistent**: không mâu thuẫn | Hai FR cho hai kết quả với cùng điều kiện; số liệu khác nhau giữa các mục | S1–S2 |
| SRS-C02 | **Complete**: phủ hết luồng chính, thay thế, ngoại lệ, vòng đời dữ liệu (tạo → đọc → sửa → hủy/lưu trữ) | Có "tạo" nhưng không có "hủy/khôi phục/xem lịch sử" | S2 |
| SRS-C03 | Không trùng lặp | Cùng quy tắc viết ở 3 nơi → rủi ro lệch | S3 |
| SRS-C04 | Phân vai–quyền: ai được làm gì | Không có ma trận actor × chức năng × quyền | S2 |
| SRS-C05 | Xử lý lỗi, trạng thái rỗng, hết hạn, đồng thời (concurrency), hủy giữa chừng, idempotency | Chỉ mô tả "happy path" | S2 |
| SRS-C06 | Thông báo/email/log: nội dung, kênh, điều kiện, người nhận | "Gửi thông báo" mà không nói gì | S3 |
| SRS-C07 | Báo cáo/xuất dữ liệu: cột, bộ lọc, quyền, định dạng, khối lượng | "Có báo cáo doanh thu" | S2 |
| SRS-C08 | Đa ngôn ngữ, múi giờ, tiền tệ, làm tròn, định dạng ngày | Không nêu khi hệ thống có người dùng/giao dịch xuyên múi giờ | S3 |
| SRS-C09 | Di trú dữ liệu / chuyển đổi / cutover / rollback | Hệ thống thay thế hệ cũ nhưng không nói dữ liệu cũ | S2 |
| SRS-C10 | Vận hành: backup/restore, RPO/RTO, giám sát, hỗ trợ | Thiếu ở hệ thống production | S3 |

## D. Business rule

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| SRS-D01 | Mỗi rule có ID, phát biểu độc lập, owner, nguồn | Rule chôn trong câu văn FR | S3 |
| SRS-D02 | Rule nhiều điều kiện → **decision table**; kiểm tra tổ hợp đủ & không trùng/không mâu thuẫn | Danh sách "nếu…nếu…" chồng chéo; tổ hợp bị thiếu | S2 |
| SRS-D03 | Công thức tính: đơn vị, làm tròn, thứ tự phép toán, ví dụ số | "Tính phí theo bậc" không có bảng bậc & ví dụ | S2 |
| SRS-D04 | Giá trị biên được định nghĩa bao gồm/không bao gồm | "Trên 18 tuổi" (>18 hay ≥18?) | S2 |
| SRS-D05 | Rule có hiệu lực theo thời gian (effective date), phiên bản | Đổi chính sách nhưng không nói áp dụng cho dữ liệu cũ hay mới | S2 |

## E. Yêu cầu phi chức năng (ISO/IEC 25010:2023)

Nhóm đặc tính: Functional suitability · Performance efficiency · Compatibility · **Interaction capability** (thay Usability) · Reliability · Security · Maintainability · **Flexibility** · **Safety**.

| ID | Kiểm tra | Dấu hiệu lỗi | Sev |
|---|---|---|---|
| SRS-E01 | NFR theo mẫu **Planguage**: Metric – Scale – Meter (cách đo) – Điều kiện (tải, môi trường) – Must/Plan/Wish | "Nhanh", "ổn định", "bảo mật cao" | S2 |
| SRS-E02 | Hiệu năng: percentile (p95/p99), tải đồng thời, kích thước dữ liệu, điều kiện đo | "Phản hồi < 2s" không nói với bao nhiêu user/dữ liệu | S2 |
| SRS-E03 | Khả dụng/độ tin cậy: SLA/SLO, RPO/RTO, cửa sổ bảo trì, hành vi khi suy giảm | "24/7" không nói thế nào là sự cố | S2 |
| SRS-E04 | Khả năng mở rộng: tăng trưởng dự kiến 1–3 năm | Không có số | S3 |
| SRS-E05 | Truy cập (WCAG 2.2 AA nếu là sản phẩm công/khách hàng), thiết bị/trình duyệt/phiên bản hỗ trợ | "Thân thiện người dùng" | S2–S3 |
| SRS-E06 | Khả năng quan sát: log, metric, trace, audit; thời gian lưu | Không có audit trail ở nghiệp vụ nhạy cảm | S2 |
| SRS-E07 | Bảo trì/triển khai: môi trường, CI/CD, feature flag, tương thích ngược | Hiếm khi cần ở SRS nghiệp vụ; chỉ flag khi là yêu cầu của khách | S4 |
| SRS-E08 | Xung đột NFR chưa được cân nhắc | Latency cực thấp + mã hóa toàn bộ + audit đồng bộ không nêu trade-off | S3 |
| SRS-E09 | Safety (nếu hệ thống có thể gây hại vật lý/tài chính/y tế) | Thiếu hazard analysis, fail-safe | S1–S2 |

## F. Dữ liệu

| ID | Kiểm tra | Sev |
|---|---|---|
| SRS-F01 | Mỗi trường dữ liệu nhập: kiểu, độ dài, bắt buộc, định dạng, miền giá trị, mặc định, quy tắc validate, thông báo lỗi | S2 |
| SRS-F02 | Dữ liệu tham chiếu/danh mục: nguồn, ai quản trị, cách cập nhật | S3 |
| SRS-F03 | Phân loại dữ liệu (công khai/nội bộ/nhạy cảm/cá nhân), chủ sở hữu, thời gian lưu, quy tắc xóa/ẩn danh | S2 |
| SRS-F04 | Tính duy nhất & khóa nghiệp vụ (mã, email, số điện thoại) và hành vi khi trùng | S2 |
| SRS-F05 | Kích thước/giới hạn file upload, định dạng cho phép, quét mã độc | S3 |

## G. Tích hợp & API

| ID | Kiểm tra | Sev |
|---|---|---|
| SRS-G01 | Mỗi giao diện ngoài: hệ thống nào, hướng, giao thức, đồng bộ/bất đồng bộ, tần suất, khối lượng, owner | S2 |
| SRS-G02 | Hợp đồng dữ liệu: schema (OpenAPI/AsyncAPI hoặc bảng trường), mã lỗi, versioning | S2 |
| SRS-G03 | Timeout, retry, backoff, idempotency key, xử lý trùng, thứ tự thông điệp, dead-letter | S2 |
| SRS-G04 | Hành vi khi hệ thống ngoài lỗi/chậm; đối soát dữ liệu (reconciliation) | S2 |
| SRS-G05 | Xác thực giữa các hệ thống (OAuth2/mTLS/API key), quản lý bí mật, rate limit | S2 |

## H. Bảo mật & tuân thủ

| ID | Kiểm tra | Sev |
|---|---|---|
| SRS-H01 | Xác thực & phân quyền (RBAC/ABAC), nguyên tắc least privilege, phân tách nhiệm vụ (maker–checker nếu tài chính) | S1–S2 |
| SRS-H02 | Quản lý phiên, MFA, khóa tài khoản, chính sách mật khẩu (theo ASVS 5.0 ở mức độ nào: L1/L2/L3) | S2 |
| SRS-H03 | Mã hóa khi lưu/truyền; quản lý khóa; che dấu dữ liệu (masking) trên UI/log | S2 |
| SRS-H04 | Dữ liệu cá nhân: căn cứ pháp lý/đồng ý, mục đích, quyền chủ thể dữ liệu (truy cập, xóa, rút lại đồng ý), chuyển dữ liệu xuyên biên giới, thông báo vi phạm. **Xác minh luật hiện hành trước khi nêu điều khoản** | S1–S2 |
| SRS-H05 | Audit log bất biến cho hành động quan trọng: ai, khi nào, làm gì, giá trị trước/sau | S2 |
| SRS-H06 | Yêu cầu theo ngành (ngân hàng, y tế, bảo hiểm, chứng khoán, công): nêu quy định áp dụng | S2 |
| SRS-H07 | Chống lạm dụng: rate limit, CAPTCHA, kiểm soát IDOR/BOLA, upload an toàn | S2 |

## I. User story & acceptance criteria

| ID | Kiểm tra | Sev |
|---|---|---|
| SRS-I01 | Story theo INVEST (Independent, Negotiable, Valuable, Estimable, Small, Testable); có "vì sao" (giá trị) | S3 |
| SRS-I02 | AC dạng Given/When/Then hoặc danh sách điều kiện kiểm chứng được; phủ luồng chính + ≥1 lỗi/biên | S2 |
| SRS-I03 | AC không mô tả giải pháp UI chi tiết trừ khi là ràng buộc | S4 |
| SRS-I04 | Story không là "epic trá hình" (đa chức năng, > 1 sprint) | S3 |
| SRS-I05 | **Definition of Ready** đạt: giá trị rõ, AC có, phụ thuộc xác định, thiết kế UI/UX liên kết, NFR liên quan, dữ liệu mẫu | S2 |

## J. Danh sách từ/cụm cảnh báo mơ hồ (quét tự động)

Tiếng Việt: nhanh, chậm, kịp thời, sớm nhất, càng sớm càng tốt, thân thiện, dễ sử dụng, trực quan, linh hoạt, tối ưu, hiệu quả, phù hợp, thích hợp, hợp lý, đầy đủ, cần thiết, nếu cần, nếu có thể, khi cần thiết, khoảng, xấp xỉ, vv., v.v., ..., và/hoặc, tương tự, tùy trường hợp, theo quy định, theo chuẩn, hỗ trợ (động từ mơ hồ), xử lý (động từ mơ hồ), quản lý (động từ mơ hồ), một số, nhiều, ít, lớn, nhỏ, thường xuyên, định kỳ (không chu kỳ), an toàn, bảo mật cao, ổn định, TBD, TBC.

English: fast, quickly, user-friendly, intuitive, flexible, optimal, efficient, appropriate, adequate, as needed, if possible, where applicable, approximately, etc., and/or, support, handle, manage, process, some, several, various, minimal, maximum (without value), robust, seamless, state-of-the-art.

Cách dùng: quét → với mỗi lần xuất hiện, chỉ tạo finding nếu từ đó **nằm trong một requirement** và thay đổi hành vi cần kiểm chứng. Từ trong phần giới thiệu/mô tả bối cảnh thì bỏ qua. Gộp mọi lần xuất hiện cùng loại vào một finding, liệt kê ≤5 ví dụ.

Động từ mơ hồ ("quản lý", "xử lý", "hỗ trợ") → đề xuất thay bằng các hành động CRUD/trạng thái cụ thể và kết quả quan sát được.
