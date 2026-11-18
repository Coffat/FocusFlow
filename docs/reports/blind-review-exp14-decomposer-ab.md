# Blind Pedagogical Review — Experiment 14: Decomposer Architecture A/B (`monolithic` vs `milestone_scoped`)

> **Phương pháp đánh giá mù (Blind Review Protocol):**
> - **Nguồn dữ liệu thực nghiệm:** `docs/experiments/exp_14_decomposer_architecture_ab.json` (chạy trực tiếp qua CofHub `http://127.0.0.1:8045`).
> - **Số cặp kịch bản đối chứng (Paired Scenarios):** **15 cặp** (30 mẫu độc lập `S-01` .. `S-30`), gồm toàn bộ 14 kịch bản cùng pass trên `golden_18_stage3_c3` và kịch bản phức tạp `H_E2E_05_FULLSTACK_NEXTJS_PG` trên `hard_6_full_e2e_c3`.
> - **Hạt giống xáo trộn cố định (Fixed RNG Seed):** `20261117`. Toàn bộ metadata về kiến trúc (`monolithic` / `milestone_scoped`), latency, số lượng token, số lần gọi hàm và điểm Judge đã được ẩn hoàn toàn khỏi phần nội dung mẫu khi chấm.
> - **File khóa giải mã (Unblinding Key):** `docs/experiments/blind_review_exp14_key.json`.

## 1. Rubric Chấm Điểm Sư Phạm 5 Tiêu Chí (Thang 1–5)

1. **C1 — Logical Progression & Prerequisites (1–5):** Trình tự nhiệm vụ trong từng milestone và giữa các milestone có tuân thủ chặt chẽ chuỗi tiên quyết (`THEORY` → `PRACTICE` → `REVIEW` / `PROJECT`), không nhảy cóc hoặc đảo ngược thứ tự nhận thức không?
2. **C2 — Theory-Practice-Review Balance (1–5):** Tỷ trọng giữa lý thuyết nền tảng (`THEORY`), thực hành tay (`PRACTICE`), ôn tập củng cố (`REVIEW`) và bài tập tích hợp (`PROJECT`) có cân bằng và phù hợp với trình độ người học không?
3. **C3 — Milestone & Outcome Coverage Fidelity (1–5):** Các nhiệm vụ có bao phủ đầy đủ 100% chuẩn đầu ra (`M*-O*`), khái niệm bắt buộc (`required_concepts`) và tiêu chí hoàn thành của từng cột mốc mà không trùng lặp hoặc lệch phạm vi không?
4. **C4 — Effort & Session Realism (1–5):** Thời lượng ước tính (`estimated_minutes` trong khoảng 30–120 phút) có khớp với ngân sách thời lượng của cột mốc (`0%` độ lệch tổng) và phân bổ hợp lý vào các khung giờ học (`schedule_blocks`) không?
5. **C5 — Actionability & Clarity (1–5):** Tên nhiệm vụ, `description`, `learning_objective` và `completion_criteria` có đủ cụ thể, rõ ràng và kiểm chứng/đo lường được ngay trong một phiên học không?

## 2. Bảng Đánh Giá Mù (Blind Evaluation Table — Trước Khi Giải Mã)

| Mẫu Blind | Kịch bản (`scenario_id`) | C1: Tiến trình & Tiên quyết | C2: Cân bằng T/P/R | C3: Bao phủ Outcome | C4: Khả thi Thời lượng | C5: Tính hành động & Rõ ràng | Tổng (/25) | Điểm TB (/5) | Nhận xét sư phạm (Blind) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **S-01** | `E02_BACKEND_INTERMEDIATE_TIGHT_B` | 5 | 4 | 5 | 5 | 5 | **24** | **4.80** | Tiến trình THEORY→PRACTICE rõ ràng cho từng milestone; mô tả và tiêu chí kiểm thử UoW/Idempotency rất chi tiết. |
| **S-02** | `E10_SYS_DESIGN_BEGINNER_TIGHT_A` | 5 | 4 | 5 | 5 | 5 | **24** | **4.80** | Bám sát Cache-Aside vs Write-Through và DLQ; tiêu chí hoàn thành có kịch bản test cụ thể. |
| **S-03** | `E03_BACKEND_ADVANCED_WIDE_A_INJ1` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Mỗi milestone đều có chu trình THEORY→PRACTICE→REVIEW cân bằng; chống prompt injection tuyệt đối. |
| **S-04** | `E09_FRONTEND_ADVANCED_WIDE_A_INJ3` | 5 | 5 | 5 | 5 | 4 | **24** | **4.80** | Cấu trúc THEORY→PRACTICE→PROJECT/REVIEW rất tốt, bám sát ngưỡng <200KB và Lighthouse >=95; mô tả ngắn gọn hơn. |
| **S-05** | `E11_SYS_DESIGN_INTERMEDIATE_WIDE_B` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Phân rã Redis Streams Consumer Group, DLQ và SSE Replay mạch lạc; tiêu chí kiểm thử failover và slow client rất sắc nét. |
| **S-06** | `E13_ML_BEGINNER_WIDE_A` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Chu trình THEORY→PRACTICE→REVIEW chuẩn mực cho chống Data Leakage và tối ưu ngưỡng F1/PR-AUC. |
| **S-07** | `E08_FRONTEND_INTERMEDIATE_TIGHT_B` | 5 | 4 | 5 | 5 | 4 | **23** | **4.60** | Bao phủ đúng Zoneless EventSource và Vitest/Playwright nhưng tiêu chí hoàn thành ngắn gọn hơn. |
| **S-08** | `E02_BACKEND_INTERMEDIATE_TIGHT_B` | 5 | 4 | 5 | 5 | 4 | **23** | **4.60** | Bao phủ đầy đủ AsyncEngine UoW và Outbox Consumer; mô tả ngắn hơn S-01. |
| **S-09** | `E08_FRONTEND_INTERMEDIATE_TIGHT_B` | 5 | 4 | 5 | 5 | 5 | **24** | **4.80** | Đặc tả rõ cơ chế Zoneless/OnPush, mock EventSource trong Vitest và kịch bản E2E Playwright. |
| **S-10** | `E12_SYS_DESIGN_ADVANCED_TIGHT_B` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Thiết kế Fencing Token chống Split-Brain và Saga Orchestrator sâu sắc, có bài tổng kết Staff Design. |
| **S-11** | `E05_DSA_INTERMEDIATE_WIDE_B` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Kết hợp THEORY→PRACTICE→REVIEW ở M1 và THEORY→PRACTICE→PROJECT ở M2 cho BFS/DFS, Kahn và Dijkstra. |
| **S-12** | `E11_SYS_DESIGN_INTERMEDIATE_WIDE_B` | 5 | 5 | 5 | 5 | 4 | **24** | **4.80** | Cấu trúc THEORY→PRACTICE→REVIEW/PROJECT tốt cho Redis Streams & SSE; tiêu chí hoàn thành ngắn gọn hơn S-05. |
| **S-13** | `E10_SYS_DESIGN_BEGINNER_TIGHT_A` | 5 | 4 | 5 | 5 | 4 | **23** | **4.60** | Đạt đầy đủ outcome về Caching và DLQ trong ngân sách 240 phút; tiêu chí ở mức vừa đủ. |
| **S-14** | `E18_DB_DEVOPS_ADVANCED_TIGHT_A` | 5 | 4 | 5 | 5 | 5 | **24** | **4.80** | Đặc tả rõ ArgoCD Sync Waves/Phases và kiểm thử kubectl drain node tôn trọng PDB. |
| **S-15** | `H_E2E_05_FULLSTACK_NEXTJS_PG` | 5 | 5 | 5 | 4 | 5 | **24** | **4.80** | Lộ trình 22 tasks bao phủ toàn diện 4 milestone Fullstack Next.js + PostgreSQL RLS; chia 3 mức thời lượng (60/90/120p). |
| **S-16** | `E13_ML_BEGINNER_WIDE_A` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Cấu trúc 6 tasks cân bằng THEORY→PRACTICE→REVIEW, nhấn mạnh kiểm chứng PR-AUC và threshold tuning. |
| **S-17** | `E12_SYS_DESIGN_ADVANCED_TIGHT_B` | 5 | 5 | 5 | 5 | 4 | **24** | **4.80** | Bao phủ tốt Raft Quorum/Fencing Token và Saga Pattern; mô tả ngắn gọn hơn S-10. |
| **S-18** | `H_E2E_05_FULLSTACK_NEXTJS_PG` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Lộ trình 20 tasks cực kỳ sắc nét (50% PRACTICE, 5 mức thời lượng 60–120p khớp độ khó, mô tả 210 ký tự/task và tiêu chí nghiệm thu định lượng). |
| **S-19** | `E01_BACKEND_BEGINNER_WIDE_A` | 4 | 4 | 5 | 5 | 5 | **23** | **4.60** | M1 có 2 task THEORY liên tiếp (tổng 3 THEORY, không có PROJECT), dù mô tả chi tiết. |
| **S-20** | `E09_FRONTEND_ADVANCED_WIDE_A_INJ3` | 5 | 5 | 5 | 5 | 4 | **24** | **4.80** | Đầy đủ THEORY→PRACTICE→REVIEW/PROJECT cho @defer và Lighthouse >=95; tiêu chí hoàn thành ngắn gọn. |
| **S-21** | `E07_FRONTEND_BEGINNER_WIDE_A` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Có mini-project giỏ hàng với Signals ở M1 và kiểm thử bàn phím/Screen Reader cho ARIA Form ở M2 rất thực tế. |
| **S-22** | `E17_DB_DEVOPS_INTERMEDIATE_WIDE_A` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Bao phủ sâu MVCC Row-level Locks, pgstattuple bloat và dự án pipeline Zero-Downtime Migration. |
| **S-23** | `E05_DSA_INTERMEDIATE_WIDE_B` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Mô tả giải thuật Iterative DFS/BFS và Kahn rất chi tiết (177 ký tự/task) kèm kiểm thử đồ thị có chu trình. |
| **S-24** | `E07_FRONTEND_BEGINNER_WIDE_A` | 5 | 5 | 5 | 5 | 4 | **24** | **4.80** | Cấu trúc THEORY→PRACTICE→REVIEW/PROJECT hợp lý cho Signals & ARIA Form; mô tả ngắn gọn hơn S-21. |
| **S-25** | `E17_DB_DEVOPS_INTERMEDIATE_WIDE_A` | 5 | 5 | 5 | 5 | 5 | **25** | **5.00** | Đặc tả sâu sắc kịch bản tái hiện deadlock, giám sát pg_locks và kiểm thử tải Expand-Contract 0% lỗi. |
| **S-26** | `E04_DSA_BEGINNER_TIGHT_A` | 5 | 4 | 5 | 5 | 4 | **23** | **4.60** | Bao phủ đúng Big-O, Two Pointers O(1) space và Sliding Window; mô tả ngắn gọn hơn S-27. |
| **S-27** | `E04_DSA_BEGINNER_TIGHT_A` | 5 | 4 | 5 | 5 | 5 | **24** | **4.80** | Mô tả rõ cấu trúc vòng lặp chuẩn của Sliding Window + HashMap và xử lý các ca biên. |
| **S-28** | `E01_BACKEND_BEGINNER_WIDE_A` | 5 | 5 | 5 | 5 | 4 | **24** | **4.80** | Cân bằng tốt THEORY→PRACTICE→REVIEW (M1) và THEORY→PRACTICE→PROJECT (M2) cho Python & FastAPI CRUD. |
| **S-29** | `E03_BACKEND_ADVANCED_WIDE_A_INJ1` | 5 | 5 | 5 | 5 | 4 | **24** | **4.80** | Cấu trúc THEORY→PRACTICE→REVIEW/PROJECT chuẩn cho Hexagonal & chống IDOR; văn phong cô đọng. |
| **S-30** | `E18_DB_DEVOPS_ADVANCED_TIGHT_A` | 5 | 4 | 5 | 5 | 5 | **24** | **4.80** | Đặc tả chi tiết annotation ArgoCD Sync Waves, hook rollback và diễn tập node drain duy trì 0% lỗi. |

---

## 3. Hồ Sơ Chi Tiết 30 Mẫu Đánh Giá Mù (`S-01` .. `S-30` — Đã Ẩn Metadata Kiến Trúc)

### S-01 — `E02_BACKEND_INTERMEDIATE_TIGHT_B` (Async SQLAlchemy 2.0 & Transactional Outbox cấp tốc)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Kiến trúc AsyncEngine và vòng đời AsyncSession trong SQLAlchemy 2.0 | Giải thích rõ ràng cơ chế commit/rollback/close và cách AsyncSession tương tác với async greenlet/asyncio loop. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành triển khai AsyncSession với async context manager an toàn | Hoàn thành đoạn mã Python chạy async engine với async with session, có test case chứng minh pool connection trả về trạng thái nhàn rỗi sau khi thực thi. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Lý thuyết kiến trúc Outbox Pattern và cơ chế Idempotency | Vẽ hoặc ghi chép được luồng ghi/đọc của Outbox pattern và liệt kê ít nhất 2 chiến lược đảm bảo Idempotent Consumer (ví dụ: unique constraint key, distributed lock). |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Thực hành triển khai Consumer Idempotent với SQLAlchemy 2.0 & FastAPI | Viết và chạy thành công test case giả lập gửi trùng một message 2 lần: DB chỉ lưu kết quả xử lý đúng 1 lần duy nhất mà không gây lỗi xung đột hoặc ghi đè sai. |

### S-02 — `E10_SYS_DESIGN_BEGINNER_TIGHT_A` (Nhập môn Thiết kế Hệ thống Web quy mô vừa)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết: Chiến lược Caching và Kiến trúc Cache-Aside vs Write-Through | Trình bày được bảng so sánh ưu/nhược điểm, use-case điển hình và rủi ro nhất quán dữ liệu giữa Cache-Aside và Write-Through. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành: Cài đặt và Phân biệt Cache-Aside và Write-Through qua Code | Mã nguồn chạy thành công các test case mô phỏng đọc ghi dữ liệu theo cả 2 mẫu thiết kế và giải quyết được vấn đề stale data cơ bản. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Lý thuyết Hàng đợi Bất đồng bộ và Chiến lược Dead-Letter Queue (DLQ) | Trình bày được sơ đồ luồng tin nhắn khi gặp sự cố xử lý và 3 kịch bản chuyển tin nhắn vào Dead-Letter Queue. |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Thực hành Xây dựng Dead-Letter Queue với FastAPI và Pydantic | Viết mã nguồn hoàn chỉnh có endpoint nhận task, xử lý lỗi sau số lần retry quy định và lưu tin nhắn hỏng vào DLQ thành công. |

### S-03 — `E03_BACKEND_ADVANCED_WIDE_A_INJ1` (Kiến trúc Modular Monolith & Multi-Tenant Backend)

- **Trình độ:** `ADVANCED` | **Khung ngày:** `2026-11-02` → `2026-12-28`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 2, `PROJECT`: 0) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết kiến trúc Hexagonal và Bounded Context trong Modular Monolith | Vẽ được sơ đồ phân tầng phân định rõ inbound/outbound ports và adapters của module. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành thiết kế Port và Adapter với FastAPI & Pydantic | Viết mã nguồn tách biệt hoàn toàn contract DTOs/ports khỏi logic cơ sở dữ liệu và triển khai thành công API route mẫu. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá và kiểm thử cách ly ranh giới Bounded Context | Bộ test suite kiểm thử domain service chạy độc lập với mock adapter và đạt 100% assertions thành công. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết kiến trúc Observability và cơ chế Rate Limiting chống lạm dụng API | Viết được tài liệu tóm tắt kiến trúc kiểm tra quyền truy cập tài nguyên (object-level authorization) và sơ đồ thuật toán Token Bucket. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành triển khai Middleware Rate Limiter và kiểm soát phân quyền tài nguyên | Mã nguồn middleware chạy thành công, trả về HTTP 403 Forbidden khi vi phạm IDOR và HTTP 429 Too Many Requests khi vượt ngưỡng gọi. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Kiểm thử bảo mật, đánh giá độ ổn định và đo lường Metrics API | Bộ test suite kiểm tra bảo mật vượt qua 100% kịch bản kiểm thử, log ghi nhận đầy đủ hành vi bị từ chối truy cập. |

### S-04 — `E09_FRONTEND_ADVANCED_WIDE_A_INJ3` (Micro-frontend Performance & Core Web Vitals)

- **Trình độ:** `ADVANCED` | **Khung ngày:** `2026-11-02` → `2026-12-20`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Nghiên cứu nguyên lý Deferrable Views và chiến lược Bundle Splitting | Trình bày được các điều kiện kích hoạt defer (on idle, on viewport, on interaction) và phân tích nguyên nhân gây vượt bundle budget. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Cấu hình Bundle Budget và áp dụng @defer vào các Micro-frontend Views | Triển khai được @defer trên ít nhất 2 thành phần view phụ, build thành công và bundle ban đầu đo lường được có xu hướng giảm rõ rệt. |
| **T3** | M1 | `PROJECT` | 60p | `M1-O1` | T2 | Đánh giá và tối ưu hóa đạt chuẩn Initial JS dưới 200KB | Báo cáo bundle analyzer và kết quả build xác nhận tổng dung lượng initial JS đạt dưới 200KB. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Nghiên cứu nguyên tắc Accessibility và Core Web Vitals Profiling | Tổng hợp danh sách kiểm tra các vi phạm Accessibility phổ biến và phương pháp đo CWV trên DevTools. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành audit và khắc phục lỗi Accessibility với Lighthouse | Khắc phục triệt để các cảnh báo trợ năng được chỉ ra trong báo cáo Lighthouse của ứng dụng. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Đánh giá nghiệm thu và xác nhận điểm Lighthouse Accessibility | Kết quả chạy kiểm thử Lighthouse đạt điểm Accessibility từ 95 trở lên. |

### S-05 — `E11_SYS_DESIGN_INTERMEDIATE_WIDE_B` (Hệ thống Realtime Notification & SSE Fan-out)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-12-18`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Kiến trúc Redis Streams Consumer Groups, cơ chế ACK và Pending Entries List (PEL) | Vẽ được sơ đồ luồng tin nhắn từ Stream chính sang Dead Letter Queue khi vượt quá số lần retry tối đa và giải thích cách giải quyết poison message. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Cài đặt Consumer Worker với Retry Policy và Dead Letter Queue (DLQ) | Mã nguồn xử lý thành công kịch bản worker gặp lỗi: tin nhắn được retry đúng số lần cấu hình trước khi bị đẩy sang stream 'notifications:dlq' kèm metadata lỗi. |
| **T3** | M1 | `PROJECT` | 60p | `M1-O1` | T2 | Tích hợp API giám sát và kiểm thử kịch bản Consumer Recovery & DLQ | Bộ test tự động chạy qua 100% kịch bản failover, tin nhắn lỗi được xác nhận vào DLQ và endpoint giám sát hiển thị chính xác độ dài PEL và số lượng tin nhắn trong DLQ. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết SSE Protocol và cơ chế Last-Event-ID | Trình bày được định dạng event stream chuẩn và mô tả luồng bắt/xử lý header Last-Event-ID khi client bị ngắt kết nối. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành SSE Replay Buffer từ Redis Streams | Viết mã nguồn xử lý SSE endpoint, kiểm thử giả lập ngắt kết nối và xác nhận các message từ sau Last-Event-ID được stream đầy đủ cho client. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Kiểm thử Backpressure và đánh giá độ tin cậy kết nối | Hoàn thành bài kiểm thử kịch bản slow client và network drop; xác nhận không có tràn bộ nhớ buffer và không trùng lặp/thất thoát message. |

### S-06 — `E13_ML_BEGINNER_WIDE_A` (Nhập môn Machine Learning với scikit-learn)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2027-01-01`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 2, `PROJECT`: 0) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết: Data Leakage và nguyên tắc chuẩn hóa dữ liệu | Giải thích rõ ràng vì sao không được fit scaler trên toàn bộ dữ liệu trước khi split và nêu được giải pháp khắc phục. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành: Triển khai Scikit-Learn Pipeline chống Data Leakage | Viết hoàn chỉnh đoạn mã tạo Pipeline với StandardScaler, kiểm tra không xuất hiện data leakage qua fit_transform sai vị trí. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá & Tổng hợp: Kiểm tra Feature Pipeline hoàn chỉnh | Hoàn thành báo cáo so sánh kết quả và hoàn thiện checklist kiểm tra data leakage trong feature engineering. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết đánh giá phân loại và xử lý mất cân bằng dữ liệu | Giải thích được sự khác biệt giữa ROC-AUC và PR-AUC trong bài toán imbalanced classification. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành tính toán và lựa chọn metric F1/PR-AUC với scikit-learn | Viết script Python chạy cross-validation và in ra báo cáo classification_report cùng PR-AUC score đạt chuẩn. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Đánh giá và tối ưu hóa ngưỡng phân loại (Threshold Tuning) | Xác định được ngưỡng quyết định tối ưu tối đa hóa F1-score trên tập validation. |

### S-07 — `E08_FRONTEND_INTERMEDIATE_TIGHT_B` (Angular Zoneless, SSE Streaming & Vitest trong 2 tuần)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Nghiên cứu cơ chế Zoneless và quản lý vòng đời EventSource | Tóm tắt và trình bày được quy trình dọn dẹp EventSource đảm bảo không rò rỉ bộ nhớ (memory leak). |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành triển khai EventSource Service và tự động hủy kết nối | Mã nguồn đóng kết nối EventSource đúng lúc khi component unmount mà không gây lỗi console. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Lập kế hoạch và thiết lập kiểm thử đơn vị với Vitest cho luồng SSE | Viết được bộ test case mẫu giả lập các sự kiện SSE onmessage, onerror và onclose. |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Kiểm thử End-to-End luồng SSE với Vitest và Playwright | Toàn bộ kịch bản E2E kiểm thử luồng SSE chạy pass trên Playwright và Vitest. |

### S-08 — `E02_BACKEND_INTERMEDIATE_TIGHT_B` (Async SQLAlchemy 2.0 & Transactional Outbox cấp tốc)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Nguyên lý AsyncEngine và Session Lifecycle trong SQLAlchemy 2.0 | Giải thích rõ ràng cơ chế tạo session, commit/rollback tự động qua async context manager và các nguyên nhân dẫn đến connection leak. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Cài đặt và kiểm thử Async Unit of Work không rò rỉ kết nối | Mã nguồn triển khai async context manager hoàn chỉnh, pass các ca kiểm thử giả lập lỗi và xác nhận pool connection không bị leak. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Thiết kế mẫu Transactional Outbox và Idempotency Consumer | Vẽ được luồng ghi DB + Outbox trong cùng một transaction và luồng xử lý idempotent với message ID / unique key. |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Lập trình Idempotent Outbox Consumer với FastAPI và SQLAlchemy | Tích hợp endpoint/worker kiểm tra idempotency key, commit trạng thái event thành công và test retry nhận kết quả nhất quán mà không duplicate dữ liệu. |

### S-09 — `E08_FRONTEND_INTERMEDIATE_TIGHT_B` (Angular Zoneless, SSE Streaming & Vitest trong 2 tuần)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Nghiên cứu cơ chế Zoneless, OnPush và quản lý vòng đời EventSource | Giải thích được cơ chế render của Zoneless/OnPush và viết được pseudo-code dọn dẹp EventSource sử dụng DestroyRef hoặc ngOnDestroy. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành triển khai Service EventSource và hủy kết nối an toàn với DestroyRef | Mã nguồn service và component hoàn chỉnh: kết nối SSE đóng ngay lập tức khi component unmount/destroy, không còn active connection ngầm trên DevTools Network tab. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Lý thuyết & Thiết lập kiểm thử Unit/Component với Vitest cho SSE Streaming | Tạo được test case cơ bản với Vitest mock EventSource phát sinh event và kiểm tra component cập nhật đúng tín hiệu/state mà không gặp lỗi change detection. |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Thực hành End-to-End Test luồng SSE Streaming bằng Playwright | Bộ test Playwright e2e chạy thành công tự động, kiểm chứng được chuỗi text stream hiển thị mượt mà trên UI và kết nối đóng đúng cách. |

### S-10 — `E12_SYS_DESIGN_ADVANCED_TIGHT_B` (Consensus Raft, Multi-Region Failover & Saga)

- **Trình độ:** `ADVANCED` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 2, `PROJECT`: 0) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết Leader Election, Quorum Reads và Nguy cơ Split-Brain | Trình bày được điều kiện tạo Quorum, giải thích được nguyên nhân gây split-brain và biện pháp phòng ngừa lý thuyết. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thiết kế & Thực hành Fencing Token để Ngăn Chặn Split-Brain | Viết được mã giả hoặc luồng xử lý xác thực fencing token ở tầng lưu trữ, xử lý thành công kịch bản stale leader bị từ chối ghi. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Tổng kết & Phân tích Đánh đổi Fencing Token trong Staff System Design | Hoàn thành bảng so sánh đánh đổi độ trễ/tính nhất quán và giải quyết trọn vẹn kịch bản network partition trong phỏng vấn thiết kế hệ thống. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết Orchestrated Saga và Chiến lược Bù trừ (Compensating Transactions) | Vẽ được sơ đồ State Machine mô tả luồng forward và backward compensation cho kịch bản thanh toán đơn hàng phân tán. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Hiện thực hóa Saga Orchestrator và Cơ chế Bù trừ Giao dịch | Viết bộ kiểm thử mô phỏng lỗi ở bước thanh toán hoặc trừ kho; hệ thống tự động kích hoạt API bù trừ và rollback trạng thái thành công. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Đánh giá Biên độ Lỗi, Edge Cases và Tối ưu Phỏng vấn Staff Design | Hoàn thành tài liệu tổng kết kiến trúc (Design Doc checklist) giải quyết trọn vẹn 3 ca lỗi biên nghiêm trọng trong giao dịch phân tán. |

### S-11 — `E05_DSA_INTERMEDIATE_WIDE_B` (Đồ thị, Cây nhị phân & Tìm kiếm nâng cao)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-12-17`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết & Cấu trúc dữ liệu: Biểu diễn Đồ thị và Cây nhị phân | Viết được mã giả minh họa BFS dùng Queue và DFS dùng Stack tường minh trên đồ thị/cây nhị phân. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành: Cài đặt BFS và DFS lặp (Iterative) | Vượt qua các ca kiểm thử chuẩn về duyệt cây/đồ thị không đệ quy với độ phức tạp thời gian O(V + E). |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Ôn tập & Tối ưu: Xử lý chu trình và đồ thị rời rạc | Tự xây dựng được checklist phát hiện lỗi lặp vô hạn và giải quyết trọn vẹn 2 bài toán tìm kiếm đường đi ngắn nhất không trọng số. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết: Đồ thị có hướng có trọng số & Thuật toán Kahn | Giải thích chi tiết được điều kiện nhận diện chu trình thông qua số lượng đỉnh được xử lý bởi hàng đợi in-degree. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành: Cài đặt Kahn phát hiện chu trình & Dijkstra | Code giải quyết chính xác bài toán Course Schedule (phát hiện chu trình) và bài toán tìm đường đi ngắn nhất trên đồ thị có trọng số. |
| **T6** | M2 | `PROJECT` | 60p | `M2-O1` | T5 | Dự án tổng hợp: Hệ thống phân tích phụ thuộc tác vụ và lộ trình tối ưu | Hoàn thiện mã nguồn mô-đun có unit tests kiểm tra trường hợp đồ thị hợp lệ lẫn trường hợp chứa chu trình. |

### S-12 — `E11_SYS_DESIGN_INTERMEDIATE_WIDE_B` (Hệ thống Realtime Notification & SSE Fan-out)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-12-18`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết kiến trúc Redis Streams Consumer Groups và Retry Mechanism | Vẽ được sơ đồ luồng message từ Stream sang Consumer, retry handler và DLQ. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành triển khai Consumer Worker với cơ chế Retry & DLQ | Consumer đọc được stream, giả lập fail 3 lần và chuyển thành công message vào DLQ stream. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá và tối ưu hóa xử lý lỗi Consumer Groups | Tài liệu hóa kịch bản xử lý crash recovery và checklist vận hành consumer group ổn định. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết Server-Sent Events (SSE), Backpressure và Last-Event-ID | Giải thích được cơ chế backpressure và luồng xử lý header Last-Event-ID trong SSE stream. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành xây dựng SSE Fan-out Service hỗ trợ Replay Message | Endpoint SSE trả về đúng luồng event, khi ngắt kết nối và gửi Last-Event-ID thì replay đầy đủ tin nhắn còn thiếu. |
| **T6** | M2 | `PROJECT` | 60p | `M2-O1` | T5 | Tích hợp và kiểm thử hệ thống SSE Replay dưới áp lực Backpressure | Chạy benchmark mô phỏng 50+ kết nối đồng thời với độ trễ mạng khác nhau mà không thất thoát message. |

### S-13 — `E10_SYS_DESIGN_BEGINNER_TIGHT_A` (Nhập môn Thiết kế Hệ thống Web quy mô vừa)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết Caching Strategies: Phân biệt Cache-Aside và Write-Through | Viết bảng so sánh chi tiết giữa Cache-Aside và Write-Through kèm sơ đồ luồng dữ liệu cho từng chiến lược. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành triển khai mô phỏng Cache-Aside và Write-Through | Chạy thành công kịch bản kiểm thử mô phỏng xử lý 100 truy vấn đọc/ghi và đo lường tỷ lệ cache hit cho cả hai phương pháp. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Lý thuyết Async Queue và Chiến lược Dead-Letter Queue (DLQ) | Liệt kê 4 tiêu chí xác định message lỗi cần chuyển vào DLQ và phác thảo quy trình xử lý tự động/thủ công cho DLQ. |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Thực hành thiết kế và xử lý Dead-Letter Queue an toàn | Kiểm thử thành công việc đẩy message hợp lệ qua luồng chính và chuyển hướng an toàn 100% message lỗi vào DLQ sau khi hết số lần retry. |

### S-14 — `E18_DB_DEVOPS_ADVANCED_TIGHT_A` (Kubernetes GitOps, Canary Rollout & Chaos Testing)

- **Trình độ:** `ADVANCED` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Kiến trúc GitOps với ArgoCD Sync Waves & Sync Phases | Trình bày được thứ tự thực thi của Sync Waves và cấu hình rollback policy trong ArgoCD Application manifest. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Cấu hình Helm/Kustomize & Triển khai Sync Waves với Rollback tự động | Manifest được đồng bộ tuần tự theo waves và ArgoCD tự động rollback về phiên bản ổn định khi ứng dụng phát sinh lỗi. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Nguyên lý SLO Alerting & Pod Disruption Budgets (PDB) | Giải thích được cơ chế hoạt động của minAvailable/maxUnavailable trong PDB và cấu trúc alerting rule cho SLO. |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Thiết lập PDB và Kiểm thử Drain Node Đảm bảo Availability | Lệnh kubectl drain node diễn ra an toàn, không có gián đoạn dịch vụ và Prometheus SLO alert không bị kích hoạt. |

### S-15 — `H_E2E_05_FULLSTACK_NEXTJS_PG` (Full-Stack Next.js App Router, React Server Components & PostgreSQL Indexing)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-11-30`
- **Cấu trúc đề xuất:** 4 milestones (1920 phút) | 22 tasks (1920 phút; `THEORY`: 5, `PRACTICE`: 9, `REVIEW`: 4, `PROJECT`: 4) | 23 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Nguyên lý Multi-Tenancy & Row-Level Security (RLS) trong PostgreSQL | Viết được tài liệu tóm tắt cơ chế RLS, so sánh ưu nhược điểm với mô hình Separate Database/Schema và giải thích luồng set_config('app.current_tenant_id'). |
| **T2** | M1 | `PRACTICE` | 120p | `M1-O1` | T1 | Cấu hình Lược đồ Multi-Tenant & Áp dụng RLS Policies | Script migration DDL chạy thành công; các truy vấn không có tenant context bị từ chối hoặc trả về 0 bản ghi. |
| **T3** | M1 | `THEORY` | 60p | `M1-O2` | T2 | Kỹ thuật Phân tích Truy vấn EXPLAIN ANALYZE & Thiết kế B-Tree / GIN Index | Chỉ ra được các điểm nghẽn Seq Scan và tính toán được cost/buffer cache hit ratio từ output của EXPLAIN ANALYZE. |
| **T4** | M1 | `PRACTICE` | 120p | `M1-O2` | T3, T2 | Đánh Index B-Tree / GIN & Đo lường Tối ưu Hóa Truy vấn | 100% câu truy vấn lọc theo tenant_id và tìm kiếm JSONB chuyển sang Index Scan/Bitmap Heap Scan, giảm I/O buffer reads ít nhất 70%. |
| **T5** | M1 | `PROJECT` | 120p | `M1-O1, M1-O3` | T4 | Kiểm thử Benchmark Hiệu năng p95 & Kiểm tra Rò rỉ Dữ liệu Cross-Tenant | Báo cáo benchmark ghi nhận p95 query latency đạt < 30ms trên 100k records; bài test truy vấn chéo giữa tenant A và tenant B trả về kết quả rỗng. |
| **T6** | M1 | `REVIEW` | 60p | `M1-O1, M1-O2, M1-O3` | T5 | Ôn tập & Đóng gói Module Database Multi-Tenant Migration | Tất cả file migration chạy clean up và migrate up/down trơn tru trên database mới mà không phát sinh lỗi. |
| **T7** | M2 | `THEORY` | 60p | `M2-O1` | T6 | Kiến trúc Next.js App Router & React Server Components Serialization | Phân tích được sơ đồ luồng dữ liệu RSC Payload từ server về client và phân biệt được trường hợp sử dụng Server vs Client Components. |
| **T8** | M2 | `PRACTICE` | 90p | `M2-O3` | T7 | Tổ chức Thư mục Dashboard: Route Groups, Nested Layouts & Parallel Routes | Cấu trúc thư mục được tổ chức chuẩn với nested layouts giữ nguyên state của sidebar/navbar khi chuyển trang con. |
| **T9** | M2 | `PRACTICE` | 120p | `M2-O2` | T8 | Khử Waterfall Fetching bằng Parallel Data Fetching & Suspense Streaming | Network tab thể hiện các truy vấn dữ liệu độc lập chạy song song; các thành phần dữ liệu chậm hiển thị skeleton fallback mượt mà. |
| **T10** | M2 | `PROJECT` | 90p | `M2-O1, M2-O2, M2-O3` | T9 | Tích hợp & Kiểm tra Hiệu năng TTFB/LCP với Lighthouse | Client bundle không chứa thư viện server-only; chỉ số Lighthouse Performance đạt > 85 điểm cho trang tổng quan dashboard. |
| **T11** | M2 | `REVIEW` | 60p | `M2-O1, M2-O2` | T10 | Review Kiến trúc App Router & RSC Best Practices | Không còn cảnh báo serializability warning trên console terminal; checklist RSC compliance hoàn thiện 100%. |
| **T12** | M3 | `THEORY` | 60p | `M3-O1, M3-O2` | T11 | Lý thuyết Session Cookie HttpOnly, CSRF & Phân quyền RBAC | Trình bày rõ ràng giải pháp phòng chống IDOR và phương pháp ký session an toàn không thể can thiệp ở client. |
| **T13** | M3 | `PRACTICE` | 120p | `M3-O1` | T12 | Xây dựng Hệ thống Xác thực Session Cookie & Phân quyền RBAC | Đăng nhập thành công tạo cookie HttpOnly bảo mật; người dùng không thể truy cập các route của tenant khác hoặc vượt quyền hạn được gán. |
| **T14** | M3 | `PRACTICE` | 120p | `M3-O2` | T13 | Bảo vệ Server Actions: Zod Validation & Phòng chống Lỗ hổng IDOR | Mọi action đều có schema validation bằng Zod; thử nghiệm can thiệp payload với ID của tenant khác đều bị chặn với mã lỗi 403 Forbidden. |
| **T15** | M3 | `PRACTICE` | 90p | `M3-O3` | T14 | Thiết lập Next.js Data Cache & Cập nhật Dữ liệu bằng Revalidation | Dữ liệu được phục vụ từ cache khi truy cập lặp lại; sau khi gọi Server Action update, cache tag tương ứng bị xóa và UI cập nhật ngay mà không tải lại trang. |
| **T16** | M3 | `REVIEW` | 60p | `M3-O1, M3-O2, M3-O3` | T15 | Đánh giá An ninh Server Actions & Kiểm tra Tính nhất quán Caching | Hoàn tất báo cáo security review; xác nhận không có bất kỳ dữ liệu nhạy cảm của tenant A xuất hiện trong cache của tenant B. |
| **T17** | M3 | `PROJECT` | 60p | `M3-O2, M3-O3` | T15, T16 | Tích hợp Luồng Mutation & Revalidation trong SaaS Workspace | Luồng CRUD dự án hoạt động trơn tru từ UI, cập nhật DB qua RLS, làm mới cache và đồng bộ state phía client. |
| **T18** | M4 | `THEORY` | 60p | `M4-O1` | T17 | Kiến trúc Playwright E2E cho Môi trường Multi-Tenant | Thiết lập tài liệu cấu hình fixtures cho Playwright với auth state độc lập giữa các roles. |
| **T19** | M4 | `PRACTICE` | 120p | `M4-O1` | T18 | Viết Playwright Test Suite: Auth, RBAC & Thao tác Multi-Tenant | Bộ test suite kiểm tra Auth và RBAC chạy pass 100% trong môi trường headless browser. |
| **T20** | M4 | `PRACTICE` | 90p | `M4-O2` | T19 | Tự động hóa Kịch bản Kiểm tra Cách ly Dữ liệu (Cross-Tenant Data Leak Test) | Kịch bản E2E xác nhận Tenant B không thể đọc, chỉnh sửa hoặc xóa bất kỳ tài nguyên nào thuộc sở hữu Tenant A. |
| **T21** | M4 | `PROJECT` | 120p | `M4-O3` | T20 | Audit Core Web Vitals với Lighthouse & Đo Kiểm Database Query Latency | Lighthouse Performance đạt trên 90 điểm; p95 latency của các truy vấn database chính đạt < 30ms. |
| **T22** | M4 | `REVIEW` | 60p | `M4-O1, M4-O2, M4-O3` | T21 | Tổng kết Dự án SaaS & Hoàn thiện Báo cáo Production Hardening | Toàn bộ bài test E2E pass; tài liệu kiến trúc và báo cáo latency hoàn chỉnh, đáp ứng 100% mục tiêu ban đầu. |

### S-16 — `E13_ML_BEGINNER_WIDE_A` (Nhập môn Machine Learning với scikit-learn)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2027-01-01`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 2, `PROJECT`: 0) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết Data Leakage và Feature Scaling trong scikit-learn | Giải thích rõ ràng tại sao không được fit scaler trên toàn bộ dataset trước khi train_test_split. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành xây dựng scikit-learn Pipeline chống Data Leakage | Chạy hoàn tất script tạo Pipeline tiền xử lý, kiểm tra kích thước và giá trị scaler chỉ được tính toán trên tập train. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá và kiểm thử quy trình tiền xử lý | Viết tài liệu ngắn checklist phòng tránh data leakage và hoàn thành bài tự đánh giá đạt 100%. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết Đánh giá mô hình trên dữ liệu mất cân bằng (Imbalanced Data) | Phân tích được trường hợp cụ thể mà Accuracy cao nhưng F1 và PR-AUC phản ánh mô hình kém hiệu quả. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành Cross-Validation và tính toán F1/PR-AUC | Chạy mô hình phân loại trên dataset mất cân bằng, xuất biểu đồ PR-AUC và bảng báo cáo classification report chi tiết. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Tổng kết và tối ưu ngưỡng quyết định (Threshold Tuning) | Xác định được ngưỡng threshold tối ưu hóa F1-score trên tập validation và kiểm tra lại trên tập test. |

### S-17 — `E12_SYS_DESIGN_ADVANCED_TIGHT_B` (Consensus Raft, Multi-Region Failover & Saga)

- **Trình độ:** `ADVANCED` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 2, `PROJECT`: 0) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết Raft Leader Election, Quorum Reads & Split-Brain | Viết tài liệu tóm tắt so sánh leader lease vs quorum read, và phân tích luồng ngăn chặn stale write bằng fencing token. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành mô phỏng Split-Brain và Fencing Token | Mã nguồn xử lý thành công việc reject request từ leader cũ khi thế hệ token (generation) nhỏ hơn token hiện hành. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Phân tích tình huống Multi-Region Failover & Consensus | Hoàn thành bài phân tích 3 kịch bản failover cross-region bảo đảm zero data loss và tính khả dụng cao. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết Orchestrated Saga & Transactional Outbox Pattern | Vẽ sơ đồ trạng thái (state machine) cho quy trình thanh toán - giữ hàng - vận chuyển khi xảy ra lỗi ở bước trung gian. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành thiết kế API Saga Orchestrator & Compensating Actions | Chạy bộ kiểm thử tự động mô phỏng lỗi dịch vụ thanh toán, xác nhận dịch vụ kho được kích hoạt hoàn trả tài nguyên thành công. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Tổng kết thiết kế hệ thống phân tán & Mock Interview Staff-level | Hoàn thành rubric đánh giá mock interview với đầy đủ giải pháp cho dual-write, network partition và partial failure. |

### S-18 — `H_E2E_05_FULLSTACK_NEXTJS_PG` (Full-Stack Next.js App Router, React Server Components & PostgreSQL Indexing)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-11-30`
- **Cấu trúc đề xuất:** 4 milestones (1920 phút) | 20 tasks (1920 phút; `THEORY`: 4, `PRACTICE`: 10, `REVIEW`: 3, `PROJECT`: 3) | 23 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Thiết kế Schema Multi-Tenant và Chuẩn hóa Dữ liệu Quan hệ 3NF | Vẽ và viết lược đồ DDL SQL cho 4 bảng chính có đầy đủ khóa ngoại, chỉ định ON DELETE cascade/restrict rõ ràng và kiểm tra cấu trúc đạt chuẩn 3NF. |
| **T2** | M1 | `PRACTICE` | 90p | `M1-O2` | T1 | Cấu hình Row-Level Security (RLS) với Session Variable trong PostgreSQL | Viết migration script áp dụng RLS hoàn chỉnh; mô phỏng phiên kết nối SET app.current_tenant_id và xác nhận dữ liệu của tenant khác không thể truy vấn hoặc can thiệp. |
| **T3** | M1 | `PRACTICE` | 90p | `M1-O3` | T1 | Thiết kế Chỉ mục B-Tree và GIN cho Truy vấn Phức hợp | Tạo composite index (tenant_id, created_at), B-Tree trên các trường truy vấn thường xuyên và GIN index trên trường JSONB attributes; biên tập file migration hoàn chỉnh. |
| **T4** | M1 | `REVIEW` | 120p | `M1-O3` | T2, T3 | Profiling Hiệu năng Truy vấn với EXPLAIN ANALYZE và Tối ưu p95 | Lập báo cáo đối sánh trước và sau khi đánh index; chứng minh thời gian thực thi của các câu truy vấn phức hợp đạt p95 < 30ms và loại bỏ hoàn toàn Seq Scan không cần thiết. |
| **T5** | M1 | `PROJECT` | 120p | `M1-O1, M1-O2` | T4 | Kiểm thử Toàn diện Cơ chế Cách ly Tenant và Tích hợp Cơ sở Dữ liệu | Bộ test suite kiểm thử RLS chạy thành công 100%, ghi nhận không có bất kỳ rò rỉ dữ liệu chéo nào khi chuyển đổi ngữ cảnh tenant_id. |
| **T6** | M2 | `THEORY` | 90p | `M2-O1, M2-O2` | T5 | Kiến trúc App Router, Layout lồng nhau và Ranh giới Serialization RSC | Vẽ được sơ đồ luồng dữ liệu RSC Payload, giải thích được lý do các kiểu dữ liệu không serialize được (như hàm, Symbol) không thể truyền trực tiếp từ Server sang Client qua props. |
| **T7** | M2 | `PRACTICE` | 105p | `M2-O1, M2-O2` | T6 | Thực hành Xây dựng Workspace Shell và Phân tách Server/Client Component Boundary | Mã nguồn cấu trúc App Router chạy không có lỗi hydration, client bundle chỉ đóng gói các UI tương tác (sidebar toggle, dropdown) trong khi dữ liệu nhạy cảm được xử lý trên Server. |
| **T8** | M2 | `PRACTICE` | 105p | `M2-O3` | T7 | Khử Request Waterfall với Parallel Data Fetching và React Suspense Streaming | Biểu đồ Network Waterfall trong DevTools chuyển từ dạng bậc thang tuần tự sang fetch đồng thời; TTFB giảm và nội dung quan trọng được stream độc lập không nghẽn trang. |
| **T9** | M2 | `REVIEW` | 120p | `M2-O1, M2-O2, M2-O3` | T8 | Đánh giá, Tối ưu Hóa Bundle và Khắc phục Lỗi Hydration Trang Workspace | Tạo báo cáo kiểm thử devtools xác nhận không còn client-side waterfall, không có hydration warning trên console, và client JS bundle của dashboard đạt dưới ngưỡng mục tiêu. |
| **T10** | M3 | `THEORY` | 75p | `M3-O1, M3-O2, M3-O3` | T9 | Kiến trúc Bảo mật Server Actions, Quản lý Phiên RBAC và Cơ chế Caching Next.js | Vẽ được sơ đồ luồng dữ liệu chứng minh cách Server Action nhận request, xác thực JWT/Session qua cookie, kiểm tra quyền RBAC và vị trí Data Cache can thiệp trong chu trình truy vấn. |
| **T11** | M3 | `PRACTICE` | 105p | `M3-O1` | T10 | Xây dựng Server Actions An toàn với Validation Zod và Chống IDOR/CSRF | Tạo được wrapper hành động an toàn (action client) tự động parse Zod schema, trích xuất tenant_id từ phiên làm việc và reject mã lỗi 403 khi input chứa ID thuộc tenant khác. |
| **T12** | M3 | `PRACTICE` | 105p | `M3-O2` | T10 | Thiết lập Xác thực Phiên HttpOnly Cookie và Phân quyền RBAC theo Tenant | Hệ thống phát hành session token vào HttpOnly cookie thành công; các route và Server Actions tự động chặn và trả lỗi Unauthorized/Forbidden khi tài khoản không có quyền tương ứng trong workspace. |
| **T13** | M3 | `PRACTICE` | 90p | `M3-O3` | T10 | Triển khai Chiến lược Caching Revalidation với revalidateTag và revalidatePath | Trang hiển thị dữ liệu từ cache với thời gian phản hồi nhanh; sau khi Server Action tạo/sửa dữ liệu thực thi `revalidateTag`, trang tự động hiển thị dữ liệu mới nhất mà không cần hard reload trình duyệt. |
| **T14** | M3 | `REVIEW` | 60p | `M3-O1, M3-O2, M3-O3` | T11, T12, T13 | Audit Bảo mật Session, RBAC và Kiểm thử Vòng đời Cache | Báo cáo checklist bảo mật đạt chuẩn: 100% request không có session hợp lệ bị từ chối, không thể thao tác IDOR sang workspace khác, và lệnh revalidateTag hoạt động chuẩn xác theo đúng phạm vi tag được gắn. |
| **T15** | M3 | `PROJECT` | 75p | `M3-O1, M3-O2, M3-O3` | T14 | Tổng hợp Tích hợp Module Quản trị SaaS Workspace Đa Tenant | Module Workspace Settings hoạt động trơn tru: người dùng thao tác form mượt mà, phân quyền theo role chính xác, Server Action từ chối mọi truy cập trái phép tenant, và dữ liệu workspace cập nhật tức thời qua revalidateTag. |
| **T16** | M4 | `THEORY` | 75p | `M4-O1, M4-O2` | T15 | Nghiên cứu nguyên lý Playwright E2E & Chiến lược kiểm thử cô lập Multi-Tenant | Viết được tài liệu tóm tắt kiến trúc kiểm thử Playwright, chiến lược dùng multi-context để mô phỏng 2 tenant đồng thời, và phân tích các trường hợp vi phạm IDOR cần kiểm thử. |
| **T17** | M4 | `PRACTICE` | 105p | `M4-O1` | T16 | Thiết lập môi trường Playwright & Viết kịch bản E2E Auth, RBAC và CRUD Workspace | Bộ test E2E thực thi tự động qua lệnh npx playwright test pass 100% các ca kiểm thử đăng nhập, xác thực phiên và tạo/sửa/xóa workspace. |
| **T18** | M4 | `PRACTICE` | 105p | `M4-O2` | T17 | Xây dựng kịch bản kiểm thử tự động chống rò rỉ dữ liệu chéo (Cross-Tenant Leak & IDOR) | Các ca kiểm thử tự động xác nhận Tenant B không thể đọc, sửa hoặc xóa dữ liệu của Tenant A qua cả direct URL navigation lẫn Server Action calls chạy pass hoàn toàn. |
| **T19** | M4 | `PRACTICE` | 105p | `M4-O3` | T17 | Đo kiểm và tinh chỉnh hiệu năng Web Vitals (LCP, CLS, INP) bằng Lighthouse CI | Báo cáo Lighthouse cho trang tổng quan (Dashboard) đạt điểm Performance >= 90, chỉ số LCP < 2.5s, CLS < 0.1 và ghi nhận bằng chứng kết quả kiểm toán. |
| **T20** | M4 | `PROJECT` | 120p | `M4-O1, M4-O2, M4-O3` | T18, T19 | Tích hợp toàn diện bộ kiểm thử CI/Staging & Đánh giá nghiệm thu Milestone | Toàn bộ test suite chạy headless thành công 100%, không flaky test; báo cáo nghiệm thu tổng hợp chứng minh p95 < 30ms và Performance > 90. |

### S-19 — `E01_BACKEND_BEGINNER_WIDE_A` (Nền tảng Python & FastAPI cho người mới bắt đầu)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2027-01-01`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 3, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 0) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết cú pháp Python, biến và kiểu dữ liệu cơ bản | Tóm tắt được các kiểu dữ liệu phổ biến và viết code mẫu sử dụng type annotations hợp lệ. |
| **T2** | M1 | `THEORY` | 60p | `M1-O1` | T1 | Cấu trúc điều khiển và xây dựng hàm với Type Hint | Định nghĩa được ít nhất 3 hàm xử lý logic kết hợp cấu trúc điều khiển và có đầy đủ type hints. |
| **T3** | M1 | `PRACTICE` | 60p | `M1-O1` | T2 | Thực hành viết bộ hàm chuẩn Type Hint và kiểm tra lỗi kiểu | Hoàn thành bài tập viết module gồm các hàm tính toán có type hints đạt chuẩn, chạy kiểm tra không có lỗi syntax hay typing. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết kiến trúc FastAPI, Routing & Pydantic v2 Schema | Giải thích được cơ chế hoạt động của path/query parameters, request body và phân biệt được schema Create/Read trong Pydantic v2. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành triển khai RESTful API CRUD và Request Validation | Tất cả các endpoint CRUD hoạt động chính xác qua Swagger UI (/docs), trả về HTTP 422 Unprocessable Entity khi dữ liệu đầu vào không hợp lệ. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Ôn tập và kiểm thử tích hợp các endpoint REST với Swagger UI & Pytest | Hoàn thành bảng checklist kiểm thử thủ công qua Docs và sửa toàn bộ lỗi logic validation phát sinh. |

### S-20 — `E09_FRONTEND_ADVANCED_WIDE_A_INJ3` (Micro-frontend Performance & Core Web Vitals)

- **Trình độ:** `ADVANCED` | **Khung ngày:** `2026-11-02` → `2026-12-20`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Nghiên cứu cơ chế @defer Views và chiến lược Bundle Budget | Tóm tắt được các điều kiện kích hoạt @defer và xác định ngân sách dung lượng tối đa cho bundle ban đầu. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Áp dụng Bundle Splitting và kiểm chuẩn dung lượng initial JS | Kích thước initial JS bundle sau khi build được nén và đo lường đạt dưới 200KB. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá và tối ưu hóa tải trang thực nghiệm | Báo cáo phân tích bundle xác nhận initial JS duy trì dưới 200KB và không có module trùng lặp. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Tìm hiểu tiêu chuẩn Core Web Vitals và Accessibility Audit | Xác định được danh sách kiểm tra (checklist) các lỗi trợ năng phổ biến cần khắc phục trên giao diện. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Khắc phục vi phạm trợ năng và đo đạc chỉ số với Lighthouse | Báo cáo Lighthouse kiểm tra cục bộ đạt điểm Accessibility từ 95 trở lên. |
| **T6** | M2 | `PROJECT` | 60p | `M2-O1` | T5 | Tích hợp và kiểm định tổng thể hiệu năng và trợ năng | Báo cáo tổng kết xác nhận ứng dụng đạt chuẩn Lighthouse Accessibility >= 95 và initial JS dưới 200KB. |

### S-21 — `E07_FRONTEND_BEGINNER_WIDE_A` (TypeScript & Angular Signals cơ bản)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2027-01-01`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết nền tảng về Angular Signals và Computed Signals | Giải thích được cơ chế lazy evaluation và dependency tracking của computed signal qua ví dụ minh họa. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành thao tác với Writable Signals và Computed | Viết được component quản lý danh sách sản phẩm mẫu sử dụng signal và computed để tính tổng giá trị mà không gây lỗi vòng lặp. |
| **T3** | M1 | `PROJECT` | 60p | `M1-O1` | T2 | Xây dựng ứng dụng quản lý trạng thái mini với Signals | Dự án giỏ hàng phản hồi chính xác khi thêm, xóa, cập nhật số lượng và tự động tính tổng tiền/chiết khấu qua computed signals. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết Standalone Components & Tiêu chuẩn A11y / ARIA | Giải thích được cơ chế imports trực tiếp của Standalone Component và liệt kê đúng ít nhất 3 thuộc tính ARIA cơ bản áp dụng cho form controls. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành xây dựng Reactive Form chuẩn ARIA | Form hoạt động đầy đủ tính năng validate, hiển thị thông báo lỗi có gắn thuộc tính aria-invalid và aria-describedby chính xác. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Đánh giá và kiểm thử A11y Form bằng bàn phím & Screen Reader | Vượt qua kiểm tra tab navigation không bị bẫy focus (keyboard trap) và các trường input phản hồi đúng trạng thái khi có lỗi. |

### S-22 — `E17_DB_DEVOPS_INTERMEDIATE_WIDE_A` (PostgreSQL Query Tuning, MVCC & Alembic Migration Zero-Downtime)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-12-17`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết MVCC, cơ chế Khóa hàng (Row-level Locks) và Giảm thiểu Deadlock | Trình bày được ma trận tương thích giữa các loại lock và 3 nguyên tắc phòng chống deadlock thường gặp. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành thiết lập Lock Timeout và Xử lý Deadlock mô phỏng | Viết kịch bản test tái hiện deadlock và cài đặt retry logic bắt exception SerializationFailure/DeadlockDetected thành công. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá và Tối ưu Vacuum, Table Bloat phòng ngừa suy hao hiệu năng | Đo đạc chỉ số bloat bằng pgstattuple/pg_stat_user_tables và xác định cấu hình autovacuum threshold tối ưu. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Chiến lược Zero-Downtime Migration với Expand and Contract Pattern | Vẽ sơ đồ quy trình 4 bước Expand and Contract cho kịch bản thay đổi schema trên bảng hàng triệu bản ghi. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành Alembic Migration an toàn trên bảng lớn | Chạy thành công migration script chia nhỏ batch update kết hợp CREATE INDEX CONCURRENTLY không gây lock timeout. |
| **T6** | M2 | `PROJECT` | 60p | `M2-O1` | T5 | Dự án Zero-Downtime Migration Pipeline hoàn chỉnh | Hoàn thiện pipeline kiểm tra migration phát hiện và chặn các câu lệnh DDL nguy hiểm (như ADD COLUMN DEFAULT không tương thích, non-concurrent index). |

### S-23 — `E05_DSA_INTERMEDIATE_WIDE_B` (Đồ thị, Cây nhị phân & Tìm kiếm nâng cao)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-12-17`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 2, `PROJECT`: 0) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết & Cơ chế Duyệt Cây và Đồ thị Không Đệ quy | Viết được giả mã mô phỏng duyệt cây tiền thứ tự (Pre-order), trung thứ tự (In-order) dùng Stack và BFS dùng Queue trên giấy/ghi chú. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành Cài đặt Iterative DFS và BFS cho Đồ thị | Vượt qua các ca kiểm thử mẫu về duyệt đồ thị liên thông và kiểm tra tính liên thông bằng DFS/BFS lặp trong Python. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Ôn tập & Đánh giá Tối ưu hóa Bộ nhớ Duyệt Đồ thị Lặp | Hoàn thành tài liệu tổng kết ngắn hoặc bảng so sánh độ phức tạp, xử lý ngoại lệ biên (đồ thị rỗng, đỉnh cô lập). |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết giải thuật Kahn và bậc vào (In-degree) trên Đồ thị có hướng | Viết được mã giả hoặc sơ đồ khối mô tả từng bước của giải thuật Kahn và giải thích được điều kiện dừng chứng minh đồ thị có chu trình. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Cài đặt thuật toán Kahn và phát hiện chu trình trên đồ thị có hướng | Chạy thành công chương trình và vượt qua bài test kiểm tra đồ thị có chu trình (trả về thông báo hoặc danh sách rỗng) và đồ thị DAG (trả về thứ tự tô-pô hợp lệ). |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Tối ưu hóa và kiểm thử thuật toán Kahn trên các ca biên phức tạp | Hoàn thiện bộ test case bao quát tối thiểu 5 ca kiểm thử biên và tối ưu hóa mã nguồn đạt chuẩn O(V + E). |

### S-24 — `E07_FRONTEND_BEGINNER_WIDE_A` (TypeScript & Angular Signals cơ bản)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2027-01-01`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết TypeScript Type System và Angular Signals cơ bản | Giải thích được sự khác nhau giữa signal(), computed() và cách cập nhật state với .set() / .update(). |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành quản lý State Component với Signals | Viết được component quản lý giỏ hàng/danh sách với signal và computed phản ánh dữ liệu tức thì. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá và tối ưu hóa Reactive State bằng Signals | Hoàn thành bài review code và khắc phục lỗi lặp vô hạn hoặc tính toán dư thừa trong computed. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết Standalone Components và Tiêu chuẩn ARIA trong Form | Liệt kê đúng các thuộc tính ARIA cần thiết cho input/error message và cấu trúc imports trong standalone component. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành xây dựng Reactive Form chuẩn ARIA | Form hoạt động đầy đủ chức năng validate dữ liệu và các thông báo lỗi hiển thị chuẩn accessibility. |
| **T6** | M2 | `PROJECT` | 60p | `M2-O1` | T5 | Dự án mini: Tích hợp Standalone Form với Signals State | Ứng dụng hoạt động trơn tru, form phản hồi theo signal state và vượt qua kiểm tra accessibility cơ bản. |

### S-25 — `E17_DB_DEVOPS_INTERMEDIATE_WIDE_A` (PostgreSQL Query Tuning, MVCC & Alembic Migration Zero-Downtime)

- **Trình độ:** `INTERMEDIATE` | **Khung ngày:** `2026-11-02` → `2026-12-17`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 2, `PROJECT`: 0) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết MVCC, Transaction Isolation và Cơ chế Row-Level Locking trong PostgreSQL | Giải thích được cơ chế phát hiện deadlock của PostgreSQL và phân biệt được 4 loại Row-Level Lock. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành tái hiện Deadlock và Kỹ thuật phòng tránh với Lock Ordering & NOWAIT | Viết script cập nhật đa luồng/đa transaction kiểm tra thành công: không phát sinh deadlock exception và xử lý lock contention an toàn. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá, Giám sát Lock Contention và Cơ chế Vacuum chống Bloat | Xây dựng được bộ câu truy vấn giám sát pg_locks & pg_stat_activity và checklist phòng tránh deadlock cho dự án thực tế. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết mẫu hình Expand-Contract & Khóa DDL trong PostgreSQL | Trình bày được 3 pha Expand, Dual-write/Sync, Contract và phân tích được lý do tại sao không đổi tên cột trực tiếp trong production. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành thiết kế Migration kịch bản Expand-Contract với Alembic | Bộ mã migration Alembic chạy thông suốt qua 2 bước Expand và Contract, có cấu hình timeout rõ ràng và dữ liệu đồng bộ nhất quán. |
| **T6** | M2 | `REVIEW` | 60p | `M2-O1` | T5 | Đánh giá và Kiểm thử tải quy trình Zero-Downtime Migration | Báo cáo kiểm thử đạt tỷ lệ lỗi 0% trên các truy vấn đồng thời trong suốt thời gian diễn ra migration. |

### S-26 — `E04_DSA_BEGINNER_TIGHT_A` (Mảng, Chuỗi & Độ phức tạp Big-O trong 14 ngày)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết Độ phức tạp Big-O và Kỹ thuật Two Pointers | Viết được phân tích độ phức tạp thời gian/bộ nhớ cho 2 đoạn mã mẫu và tóm tắt điều kiện áp dụng Two Pointers. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành Two Pointers tối ưu O(1) Không gian | Vượt qua toàn bộ test cases cho 2 bài toán thao tác mảng với Two Pointers đạt chuẩn O(1) space. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Lý thuyết Cấu trúc HashMap và Kỹ thuật Sliding Window | Vẽ được sơ đồ chuyển dịch hai biên của Sliding Window và giải thích cách cập nhật HashMap khi mở rộng/thu hẹp cửa sổ. |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Thực hành Giải bài toán Sliding Window kết hợp HashMap | Viết và kiểm thử thành công thuật toán giải bài toán Sliding Window với độ phức tạp tối ưu O(n). |

### S-27 — `E04_DSA_BEGINNER_TIGHT_A` (Mảng, Chuỗi & Độ phức tạp Big-O trong 14 ngày)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết phân tích Big-O và kỹ thuật Two Pointers | Giải thích được sự khác biệt giữa O(1) và O(n) space, đồng thời mô tả được cơ chế hoạt động của Hai con trỏ trên mảng đã sắp xếp. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành Two Pointers và tối ưu bộ nhớ O(1) | Viết và chạy thành công mã nguồn Python giải quyết bài toán Hai con trỏ đạt độ phức tạp O(n) time và O(1) space. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Lý thuyết & Kỹ thuật Sliding Window kết hợp HashMap | Trình bày được cấu trúc vòng lặp Sliding Window chuẩn và phân tích được độ phức tạp thời gian O(n) thay vì O(n^2). |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Thực hành giải bài toán Sliding Window kinh điển | Viết mã nguồn hoàn chỉnh, xử lý chính xác các trường hợp biên và vượt qua toàn bộ test cases kiểm thử. |

### S-28 — `E01_BACKEND_BEGINNER_WIDE_A` (Nền tảng Python & FastAPI cho người mới bắt đầu)

- **Trình độ:** `BEGINNER` | **Khung ngày:** `2026-11-02` → `2027-01-01`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết cú pháp Python, biến và hàm kèm Type Hints | Tóm tắt được các kiểu dữ liệu nguyên thủy, cú pháp hàm và viết được ví dụ minh họa có type hints. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành viết hàm xử lý dữ liệu với Type Hints | Hoàn thành bộ bài tập viết hàm Python có kiểm tra kiểu dữ liệu tĩnh không phát sinh lỗi. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Đánh giá và tối ưu mã nguồn Python cơ bản | Refactor mã nguồn đạt chuẩn PEP 8 và vượt qua các test cases kiểm thử logic cơ bản. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Tổng quan FastAPI Routing và Data Validation với Pydantic v2 | Giải thích được cơ chế serialize/deserialize và validation của Pydantic schema trên FastAPI endpoint. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Thực hành xây dựng các REST Endpoints CRUD cơ bản | Endpoints phản hồi đúng HTTP status codes và trả về lỗi 422 Unprocessable Entity khi dữ liệu sai schema. |
| **T6** | M2 | `PROJECT` | 60p | `M2-O1` | T5 | Tích hợp và hoàn thiện dự án FastAPI CRUD đầu tiên | Toàn bộ luồng CRUD chạy ổn định trên Swagger UI (/docs) với dữ liệu mẫu và vượt qua kịch bản kiểm thử. |

### S-29 — `E03_BACKEND_ADVANCED_WIDE_A_INJ1` (Kiến trúc Modular Monolith & Multi-Tenant Backend)

- **Trình độ:** `ADVANCED` | **Khung ngày:** `2026-11-02` → `2026-12-28`
- **Cấu trúc đề xuất:** 2 milestones (360 phút) | 6 tasks (360 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 1, `PROJECT`: 1) | 5 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Lý thuyết kiến trúc Hexagonal và Bounded Context trong Modular Monolith | Viết tài liệu tổng hợp và sơ đồ kiến trúc thể hiện luồng phụ thuộc Inversion of Control cho module mẫu. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Thực hành tách Port & Adapter cho dịch vụ Core Domain | Mã nguồn tách biệt hoàn toàn domain khỏi router, test suite pass kiểm tra boundary enforcement. |
| **T3** | M1 | `REVIEW` | 60p | `M1-O1` | T2 | Kiểm thử cô lập và đánh giá Contract Boundaries | Báo cáo code review và bộ test unit/integration đạt 100% ranh giới module. |
| **T4** | M2 | `THEORY` | 60p | `M2-O1` | T3 | Lý thuyết kiểm soát truy cập Multi-Tenant và phòng chống IDOR | Hoàn thành tài liệu phân tích rủi ro IDOR và đặc tả logic chặn truy cập chéo tenant. |
| **T5** | M2 | `PRACTICE` | 60p | `M2-O1` | T4 | Cài đặt Middleware Rate Limiting và kiểm tra ủy quyền Tenant | Middleware chặn thành công request vượt ngưỡng và từ chối request truy cập tài nguyên tenant khác với mã 403/404. |
| **T6** | M2 | `PROJECT` | 60p | `M2-O1` | T5 | Tích hợp Observability và diễn tập phòng thủ Abuse API | Log metrics hiển thị đầy đủ tenant_id, test suite bảo mật xác nhận không có lỗ hổng IDOR tồn đọng. |

### S-30 — `E18_DB_DEVOPS_ADVANCED_TIGHT_A` (Kubernetes GitOps, Canary Rollout & Chaos Testing)

- **Trình độ:** `ADVANCED` | **Khung ngày:** `2026-11-02` → `2026-11-16`
- **Cấu trúc đề xuất:** 2 milestones (240 phút) | 4 tasks (240 phút; `THEORY`: 2, `PRACTICE`: 2, `REVIEW`: 0, `PROJECT`: 0) | 3 cạnh phụ thuộc DAG

| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |
|---|---|---|---|---|---|---|
| **T1** | M1 | `THEORY` | 60p | `M1-O1` | Không | Nghiên cứu cơ chế ArgoCD Sync Waves, Hooks và điều kiện Rollback tự động | Giải thích rõ thứ tự thực thi theo annotation sóng sync wave và xác định được điều kiện kích hoạt rollback khi triển khai thất bại. |
| **T2** | M1 | `PRACTICE` | 60p | `M1-O1` | T1 | Cấu hình Helm/Kustomize với ArgoCD Sync Waves và kiểm thử Rollback tự động | ArgoCD Application áp dụng đúng thứ tự wave; kịch bản test lỗi kích hoạt rollback tự động về phiên bản ổn định thành công. |
| **T3** | M2 | `THEORY` | 60p | `M2-O1` | T2 | Lý thuyết Pod Disruption Budgets & SLO-based Alerting | Giải thích được cơ chế Eviction API tôn trọng PDB và xây dựng được cấu hình PDB mẫu cho service có tính khả dụng cao. |
| **T4** | M2 | `PRACTICE` | 60p | `M2-O1` | T3 | Thực hành cấu hình PDB và mô phỏng Node Drain giữ vững SLO | Thực hiện node drain thành công mà tỷ lệ lỗi request duy trì ở mức 0% đáp ứng đúng mục tiêu SLO đã định. |

---

## 4. Kết Quả Sau Giải Mã (Unblinded Comparison Summary: Arm A `monolithic` vs Arm B `milestone_scoped`)

### 4.1. Điểm Trung Bình Theo 5 Tiêu Chí Sư Phạm (15 Cặp Kịch Bản = 30 Mẫu)

| Tiêu chí đánh giá | Arm A: `monolithic` (n=15) | Arm B: `milestone_scoped` (n=15) | Chênh lệch (`B - A`) |
|---|---:|---:|---:|
| **C1 — Logical Progression & Prerequisites (/5)** | 5.000 | **4.933** | **+-0.067** |
| **C2 — Theory-Practice-Review Balance (/5)** | 4.667 | **4.600** | **+-0.067** |
| **C3 — Milestone & Outcome Coverage Fidelity (/5)** | **5.000** | **5.000** | +0.000 |
| **C4 — Effort & Session Realism (/5)** | 4.933 | **5.000** | **+0.067** |
| **C5 — Actionability & Clarity (/5)** | 4.333 | **4.933** | **+0.600** |
| **Tổng điểm trung bình (/25)** | 23.933 | **24.467** | **+0.534** |
| **Điểm trung bình toàn cục (/5)** | 4.787 | **4.893** | **+0.106** |

### 4.2. Tỷ Lệ Thắng / Hòa / Thua Đối Đầu Trực Tiếp (Head-to-Head Win / Tie / Loss trên 15 Cặp)

- **Arm B (`milestone_scoped`) thắng:** **9/15 (60.0%)**
- **Hòa (Tie):** **5/15 (33.3%)**
- **Arm A (`monolithic`) thắng:** **1/15 (6.7%)**

| # | Workload | Kịch bản (`scenario_id`) | Mẫu `monolithic` | Điểm `monolithic` (/25) | Mẫu `milestone_scoped` | Điểm `milestone_scoped` (/25) | Chênh lệch (`B - A`) | Kết quả đối đầu |
|---:|---|---|---|---:|---|---:|---:|---|
| 1 | `golden_18_stage3_c3` | `E01_BACKEND_BEGINNER_WIDE_A` | **S-28** | 24 | **S-19** | **23** | -1 | `monolithic` |
| 2 | `golden_18_stage3_c3` | `E02_BACKEND_INTERMEDIATE_TIGHT_B` | **S-08** | 23 | **S-01** | **24** | +1 | `milestone_scoped` |
| 3 | `golden_18_stage3_c3` | `E03_BACKEND_ADVANCED_WIDE_A_INJ1` | **S-29** | 24 | **S-03** | **25** | +1 | `milestone_scoped` |
| 4 | `golden_18_stage3_c3` | `E04_DSA_BEGINNER_TIGHT_A` | **S-26** | 23 | **S-27** | **24** | +1 | `milestone_scoped` |
| 5 | `golden_18_stage3_c3` | `E05_DSA_INTERMEDIATE_WIDE_B` | **S-11** | 25 | **S-23** | **25** | +0 | `tie` |
| 6 | `golden_18_stage3_c3` | `E07_FRONTEND_BEGINNER_WIDE_A` | **S-24** | 24 | **S-21** | **25** | +1 | `milestone_scoped` |
| 7 | `golden_18_stage3_c3` | `E08_FRONTEND_INTERMEDIATE_TIGHT_B` | **S-07** | 23 | **S-09** | **24** | +1 | `milestone_scoped` |
| 8 | `golden_18_stage3_c3` | `E09_FRONTEND_ADVANCED_WIDE_A_INJ3` | **S-20** | 24 | **S-04** | **24** | +0 | `tie` |
| 9 | `golden_18_stage3_c3` | `E10_SYS_DESIGN_BEGINNER_TIGHT_A` | **S-13** | 23 | **S-02** | **24** | +1 | `milestone_scoped` |
| 10 | `golden_18_stage3_c3` | `E11_SYS_DESIGN_INTERMEDIATE_WIDE_B` | **S-12** | 24 | **S-05** | **25** | +1 | `milestone_scoped` |
| 11 | `golden_18_stage3_c3` | `E12_SYS_DESIGN_ADVANCED_TIGHT_B` | **S-17** | 24 | **S-10** | **25** | +1 | `milestone_scoped` |
| 12 | `golden_18_stage3_c3` | `E13_ML_BEGINNER_WIDE_A` | **S-16** | 25 | **S-06** | **25** | +0 | `tie` |
| 13 | `golden_18_stage3_c3` | `E17_DB_DEVOPS_INTERMEDIATE_WIDE_A` | **S-22** | 25 | **S-25** | **25** | +0 | `tie` |
| 14 | `golden_18_stage3_c3` | `E18_DB_DEVOPS_ADVANCED_TIGHT_A` | **S-14** | 24 | **S-30** | **24** | +0 | `tie` |
| 15 | `hard_6_full_e2e_c3` | `H_E2E_05_FULLSTACK_NEXTJS_PG` | **S-15** | 24 | **S-18** | **25** | +1 | `milestone_scoped` |
