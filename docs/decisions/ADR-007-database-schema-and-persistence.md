# ADR-007: Kiến trúc Cơ sở Dữ liệu PostgreSQL 16 + pgvector (35 Bảng 3NF/BCNF), Khóa Ngoại Đơn (Single Surrogate FK), Cấm ORM JOIN Chéo Context & Ánh xạ FocusFlow Learning Intelligence Harness

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật & Đồng bộ Kiến trúc v3.2: Chuẩn 35 Bảng Vật lý 3NF/BCNF + `pgvector`)
* **Ngày quyết định:** 30/09/2026 (Cập nhật v2.0: 25/10/2026; Cập nhật v3.1: 03/11/2026; Cập nhật v3.2: 05/11/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** `ASR-01`, `ASR-02`, `FR-AUTH-001`, `FR-PLAN-001..005`, `FR-SESSION-001..003`, `FR-TASK-001`, `FR-ADAPT-001..003`, `FR-REPORT-001`, `FR-EVAL-004`, `UC-01` đến `UC-28`, `BUSR-01` đến `BUSR-12`, `OS-01` đến `OS-07`
* **Tài liệu đối chiếu:** [`docs/database/database-schema-design.md`](../database/database-schema-design.md), [`docs/database/data-dictionary.md`](../database/data-dictionary.md), [`docs/database/schema.sql`](../database/schema.sql), [`docs/mentor-alignment-and-gap-report.md`](../mentor-alignment-and-gap-report.md)

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)

Trong quá trình nâng cấp toàn diện hệ thống lên kiến trúc **FocusFlow Learning Intelligence Harness** (bổ sung Knowledge Engine với Hybrid RAG, Structured Learner Memory 4×3, Skill Mastery & Mistake Intelligence, Resilient Deterministic Scheduling với Khối Lịch Học tách rời và Durable Workflow Orchestration), nhóm phát triển cần giải quyết dứt điểm các bài toán thiết kế cơ sở dữ liệu sau trong khi bảo toàn tuyệt đối chuẩn **3NF/BCNF** và chỉ sử dụng **4 container Docker Compose** (`postgres`, `redis`, `backend`, `frontend`):

1. **Tiến hóa từ 28 bảng lên 35 bảng vật lý chuẩn 3NF/BCNF (`12 / 10 / 5 / 4 / 4`):**
   - **Tích hợp `pgvector` ngay trong PostgreSQL 16 (Không thêm container Vector DB riêng):** Bổ sung extension `CREATE EXTENSION IF NOT EXISTS vector;` cùng hai bảng `knowledge_sources` và `knowledge_chunks` trong `planning` Bounded Context để phục vụ truy xuất lai (Hybrid RAG: tìm kiếm từ khóa toàn văn bản `tsvector` GIN kết hợp tìm kiếm tương đồng ngữ nghĩa `vector(768)` HNSW) kèm truy vết nguồn trích dẫn (Provenance).
   - **Tách biệt Khối lượng Ước tính (`tasks.estimated_minutes`) và Khối Lịch Học Thực thi (`schedule_blocks`):** Trong thực tế học tập, một `Task` có nỗ lực ước tính 120 phút (`estimated_effort`) cần được Bộ lập lịch tất định (Deterministic Scheduling Engine) chia thành hai khối học 60 phút (`scheduled_duration_minutes`) ở hai ngày khác nhau, xen kẽ với các khối dự phòng (`BUFFER`), ôn tập (`REVISION`) hoặc phục hồi (`RECOVERY`). Đồng thời, mỗi khối lịch học trên lịch chính thức cần ánh xạ 1:1 với sự kiện trên Google/Outlook Calendar (`external_calendar_event_id`). Lưu trực tiếp các khung giờ rời rạc này trong bảng `tasks` sẽ vi phạm 1NF/3NF; do đó cần tách bảng `schedule_blocks` thuộc `planning` BC.
   - **Trí nhớ Người học Cấu trúc hóa (Structured Learner Memory) & Theo dõi Thành thạo Khái niệm (Skill Mastery):** Bổ sung hai bảng `learner_memory_items` (mô hình hóa ma trận 4 Danh mục `PROFILE`, `BEHAVIORAL`, `KNOWLEDGE`, `INTERACTION` × 3 Mức nhận thức `EXPLICIT`, `OBSERVED`, `INFERRED` kèm `confidence_score`, `sample_size`, `confirmation_status`) và `learner_concept_masteries` (lưu điểm thành thạo `mastery_score`, cấp độ `mastery_level`, tóm tắt lỗi sai và lịch ôn tập `next_review_at` xuyên suốt nhiều lộ trình) vào `account` BC.
   - **Điều phối Workflow Bền vững (Durable Workflow Orchestration):** Để quản lý 5 luồng nghiệp vụ AI nhiều bước có điểm dừng chờ người học xác nhận (`PLAN_CREATION`, `SCHEDULE_GENERATION`, `OVERDUE_RECOVERY`, `WEEKLY_REVIEW`, `CONTINUOUS_LEARNING`), bổ sung hai bảng `workflow_runs` và `workflow_step_executions` vào `shared_kernel` BC.
   - **Tách biệt Nghiêm ngặt giữa `AI Execution Run` và `Learning Event`:** Tuyệt đối không trộn lẫn nhật ký thực thi kỹ thuật của hệ thống AI (`workflow_runs`, `workflow_step_executions`, `ai_usage_logs`) với các sự kiện hành vi học tập của người học (`study_sessions`, `study_notes`, `milestone_proofs`, `schedule_change_logs`).

2. **Chiến lược Khóa ngoại Đơn (Single Surrogate FK) kết hợp Định danh Tương quan Đa người thuê Liên Context (Cross-Context Tenant Correlation IDs — `user_id`, `roadmap_id`, `goal_id`):** Trong kiến trúc **Context-First Modular Monolith** cấm tuyệt đối ORM JOIN chéo Bounded Context (`ADR-001`), việc giữ Single Surrogate Primary/Foreign Key chuẩn 3NF/BCNF kết hợp với **Cross-Context Tenant Correlation IDs** cho phép kiểm tra quyền sở hữu chống tấn công IDOR (`NFR-SEC-004`) với độ phức tạp $O(1)$ ngay trên bảng cục bộ.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Giữ nguyên 28 bảng và nhồi nhét toàn bộ Memory, RAG Chunks, Schedule Blocks và Workflow State vào các cột JSONB lớn
* *Nhược điểm:* Vi phạm nghiêm trọng chuẩn 1NF/2NF/3NF; không thể đánh chỉ mục HNSW `pgvector` và GIN `tsvector` trên từng phân đoạn tài liệu; không thể truy vấn từng khối lịch `schedule_blocks` theo ngày hoặc đồng bộ đơn lẻ từng sự kiện với Google Calendar; mất khả năng kiểm toán từng bước của Workflow.

### Phương án B: Thêm container Vector Database riêng (Qdrant/Milvus) và Workflow Engine riêng (Temporal)
* *Nhược điểm:* Phá vỡ giới hạn kiến trúc hạ tầng 4 container Docker Compose đã chốt trong `ADR-001` và `AGENTS.md`; làm tăng độ phức tạp vận hành và chi phí đồng bộ dữ liệu hai pha giữa PostgreSQL và Vector DB.

### Phương án C: Chuẩn hóa Toàn diện 35 Bảng Vật lý Chuẩn 3NF/BCNF trên PostgreSQL 16 (kèm `pgvector`), Phân rã `12 / 10 / 5 / 4 / 4` & Cấm ORM JOIN Chéo Context (Được chọn)
* Chuẩn hóa chính thức **35 bảng trong schema `public` của PostgreSQL 16** đạt chuẩn **3NF/BCNF** nghiêm ngặt theo phân rã `12 account / 10 planning / 5 execution / 4 evaluation / 4 shared_kernel`.
* Kích hoạt `CREATE EXTENSION IF NOT EXISTS vector;` ngay trong PostgreSQL 16 để vận hành Hybrid RAG (`tsvector` GIN + `vector(768)` HNSW) trên bảng `knowledge_chunks`.
* Tách biệt rõ ràng 11 khái niệm logic của **FocusFlow Learning Intelligence Harness** vào 35 bảng vật lý chuẩn hóa mà không trộn lẫn `AI Execution Run` với `Learning Event`.

---

## 3. Quyết định (Decision)

**Chấp thuận Phương án C với các trụ cột kiến trúc CSDL v3.2:**

### 3.1. Phân bổ Chính thức 35 Bảng Chuẩn 3NF/BCNF theo 4 Bounded Contexts + `shared_kernel`

| Phân vùng (Bounded Context) | Số lượng | Danh sách các Bảng PostgreSQL 16 Sở hữu |
| :--- | :---: | :--- |
| **1. `account`** | **12 bảng** | `users`, `learner_profiles`, `webcal_tokens`, `calendar_connections`, `availabilities`, `availability_slots`, `ai_quotas`, `ai_quota_reservations`, `ai_usage_logs`, `payment_transactions`, `learner_memory_items` *(Mới v3.2)*, `learner_concept_masteries` *(Mới v3.2)* |
| **2. `planning`** | **10 bảng** | `goals`, `roadmaps`, `milestones`, `official_schedules`, `schedule_proposals`, `learning_concepts`, `concept_prerequisites`, `knowledge_sources` *(Mới v3.2)*, `knowledge_chunks` *(Mới v3.2)*, `schedule_blocks` *(Mới v3.2)* |
| **3. `execution`** | **5 bảng** | `tasks`, `task_dependencies`, `study_sessions`, `session_tasks`, `study_notes` |
| **4. `evaluation`** | **4 bảng** | `pause_records`, `ai_reviews`, `schedule_change_logs`, `milestone_proofs` |
| **5. `shared_kernel`** | **4 bảng** | `outbox_events`, `processed_events`, `workflow_runs` *(Mới v3.2)*, `workflow_step_executions` *(Mới v3.2)* |
| **Tổng cộng toàn hệ thống** | **35 bảng** | **Đạt chuẩn 3NF / BCNF 100% với Khóa chính `UUIDv7` tuần tự thời gian & `pgvector`** |

### 3.2. Bảng Ánh xạ 11 Khái niệm Logic của FocusFlow Learning Intelligence Harness sang 35 Bảng Vật lý

| STT | Khái niệm Logic (Logical Harness Concept) | Bảng Vật lý Ánh xạ (`schema.sql` v3.2) | Bounded Context | Luận cứ Chuẩn hóa 3NF/BCNF & Ranh giới Ngữ nghĩa |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **AI Execution Run** | `workflow_runs`, `ai_usage_logs`, `ai_quota_reservations` | `shared_kernel`, `account` | Lưu vết phiên chạy điều phối AI cấp cao, giữ chỗ hạn ngạch 2 pha và chi phí token/độ trễ của LLM (`gemini-2.5-flash`). **Tách biệt 100% khỏi `Learning Event`** vì đây là nhật ký vận hành hệ thống/AI, không phải hành vi học tập của người học. |
| **2** | **Workflow Step Execution** | `workflow_step_executions` | `shared_kernel` | Quan hệ 1:N chuẩn 3NF với `workflow_runs`, lưu checkpoint đầu vào/đầu ra và liên kết `ai_usage_log_id` của từng bước thực thi. |
| **3** | **Knowledge Source** | `knowledge_sources`, `learning_concepts`, `concept_prerequisites` | `planning` | Lưu trữ tài liệu đầu vào của người học (`PDF`, `DOCX`, `TXT`, `URL` đã qua kiểm duyệt SSRF & SHA-256 `content_hash`) cùng đồ thị khái niệm học thuật chuẩn hóa. |
| **4** | **Knowledge Chunk** | `knowledge_chunks` | `planning` | Quan hệ 1:N chuẩn 3NF với `knowledge_sources` (`UNIQUE (source_id, chunk_index)`), lưu văn bản phân đoạn, siêu dữ liệu trích dẫn (`section_title`, `page_number`), `search_vector TSVECTOR` (GIN) và `embedding vector(768)` (HNSW). |
| **5** | **Learning Event** | `study_sessions`, `session_tasks`, `study_notes`, `milestone_proofs`, `schedule_change_logs` | `execution`, `evaluation` | Phản ánh các sự kiện học tập thực tế của người học: phiên Pomodoro + Daily Check-in (`study_sessions`), ghi chép & Takeaway (`study_notes`), bài kiểm chứng năng lực & phân loại lỗi sai (`milestone_proofs.mistake_taxonomy_json`), và biến động lịch (`schedule_change_logs`). **Tuyệt đối không trộn với `AI Execution Run`.** |
| **6** | **Learner Profile** | `users`, `learner_profiles`, `learner_concept_masteries` | `account` | Quản lý định danh, các chỉ số SRL tổng hợp 1:1 (`learner_profiles`), và mức độ thành thạo từng khái niệm 1:N (`learner_concept_masteries`). |
| **7** | **Learner Feature Snapshot** | `learner_memory_items` | `account` | Chuẩn hóa 3NF/BCNF cho các nhận định trí nhớ người học theo ma trận **4 Categories × 3 Epistemic Levels** (`UNIQUE (user_id, memory_category, memory_key)`), lưu `claim_value`, `sample_size`, `confidence_score` và trạng thái xác nhận của người học (`confirmation_status`). |
| **8** | **Availability Snapshot** | `availabilities`, `availability_slots` | `account` | Cấu hình quỹ thời gian rảnh Mode A (`availabilities.daily_quotas`) và các khung giờ rảnh kèm mức năng lượng sinh học Mode B chuẩn 3NF (`availability_slots`). |
| **9** | **Schedule Revision** | `official_schedules`, `schedule_proposals`, `pause_records` | `planning`, `evaluation` | Quản lý lịch cơ sở đóng băng kèm chính sách chống đứt gãy (`official_schedules`: `buffer_minutes_per_week`, `recovery_window_days`, `daily_workload_cap_minutes`, `stability_weight`), các bản nháp đề xuất & mô phỏng What-If (`schedule_proposals`), và lịch sử tạm dừng Domino Shift (`pause_records`). |
| **10** | **Calendar Event Mapping** | `schedule_blocks`, `calendar_connections`, `webcal_tokens` | `planning`, `account` | Bảng `schedule_blocks` tách biệt thời lượng phân bổ lịch (`scheduled_duration_minutes`) khỏi nỗ lực ước tính của nhiệm vụ (`tasks.estimated_minutes`), hỗ trợ nhiều khối lịch cho 1 Task, các khối `BUFFER`/`REVISION`/`RECOVERY`, và ánh xạ `external_calendar_event_id` với kết nối OAuth2 (`calendar_connections`). |
| **11** | **Weekly Review** | `ai_reviews` | `evaluation` | Lưu trữ báo cáo tổng kết định kỳ kết hợp số liệu định lượng (`quantitative_summary`) với phản tư chủ quan 2–3 câu hỏi của người học (`user_reflection_payload`) và khuyến nghị thích ứng từ AI. |

### 3.3. Tại sao tách biệt nghiêm ngặt `AI Execution Run` và `Learning Event`?
1. **Bảo toàn tính đúng đắn của Chuẩn hóa 3NF/BCNF & Domain Semantics:**
   - `AI Execution Run` (`workflow_runs`, `workflow_step_executions`, `ai_usage_logs`) có các thuộc tính đặc trưng của hệ thống suy luận và điều phối (`current_step`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `estimated_cost_usd`, `retry_count`). Một thao tác của người học có thể kích hoạt 0, 1 hoặc nhiều bước gọi LLM/công cụ tất định; ngược lại, một tác vụ nền có thể chạy khi người học không trực tuyến.
   - `Learning Event` (`study_sessions`, `study_notes`, `milestone_proofs`, `schedule_change_logs`) ghi nhận bằng chứng sư phạm và hành vi tự điều chỉnh học tập (Zimmerman SRL: thời gian thực học, điểm tự đánh giá `self_confidence`, câu trả lời truy hồi, cảm nhận `checkin_time_sufficiency`, `checkin_perceived_difficulty`, `checkin_focus_level`).
2. **Chống nhiễu Dữ liệu Phân tích Học tập (Learning Analytics Integrity):**
   - Việc tách riêng hoàn toàn giúp các bộ tổng hợp chỉ số học tập (`LearnerProfileAggregator`, `MistakeIntelligenceAnalyzer`, `PlanAdherenceCalculator`) chỉ đọc trên các bảng `Learning Event` mà không bao giờ bị làm sai lệch bởi các lần retry kỹ thuật hay các phiên chạy mô phỏng What-If (`WHAT_IF_SIMULATION`) của AI.

### 3.4. Khóa Ngoại Đơn (Single Surrogate FK), Thứ tự DDL Hợp lệ 100%, Chống IDOR $O(1)$ & Cấm ORM JOIN Chéo Context
1. **Ở cấp độ CSDL Vật lý (`PostgreSQL 16` — `schema.sql` v3.2):**
   - Giữ đầy đủ các ràng buộc `FOREIGN KEY` vật lý xuyên Bounded Context để bảo toàn tính toàn vẹn tham chiếu dữ liệu (Defense-in-Depth) ở tầng database engine PostgreSQL.
   - Đối với hai khóa ngoại tham chiếu chéo giữa các bảng được định nghĩa ở các phần kế tiếp trong tệp DDL (`learner_concept_masteries.concept_id -> learning_concepts(concept_id)` và `schedule_blocks.task_id -> tasks(id)`), `schema.sql` sử dụng câu lệnh `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` ngay sau khi bảng đích được khởi tạo, đảm bảo thực thi `psql -f docs/database/schema.sql` từ trên xuống dưới với **0 lỗi**.
2. **Ở cấp độ Mã nguồn Ứng dụng (`SQLAlchemy 2.0 ORM`):**
   - Cấm tuyệt đối khai báo `relationship()` hoặc viết câu lệnh `JOIN` ORM trực tiếp giữa các bảng thuộc hai Bounded Context khác nhau (được kiểm soát và cưỡng chế bởi `import-linter`).
   - Giao tiếp đọc dữ liệu liên Context bắt buộc đi qua Query Port (`public_api.py`), giao tiếp ghi có hiệu ứng phụ đi qua sự kiện Transactional Outbox (`outbox_events`).

### 3.5. Ràng buộc Toàn vẹn, Trigger Cập nhật Thời gian & Chỉ mục Hiệu năng (B-Tree, GIN, HNSW)
* **Khóa chính UUIDv7 (RFC 9562):** Sinh tại tầng Domain Backend Python (`uuid_utils`/`uuid6`), sắp xếp tuần tự thời gian, loại bỏ phân mảnh B-Tree.
* **Hàm Trigger `fn_set_updated_at()`:** Áp dụng tự động trên toàn bộ **26 bảng vật lý** có cột `updated_at` (bổ sung 5 trigger mới: `trg_learner_memory_items_updated_at`, `trg_learner_concept_masteries_updated_at`, `trg_knowledge_sources_updated_at`, `trg_schedule_blocks_updated_at`, `trg_workflow_runs_updated_at`).
* **67 Chỉ mục Chuyên biệt:** Bao gồm 7 chỉ mục duy nhất toàn phần/bộ phận (Partial Unique Indexes), 58 chỉ mục B-Tree tối ưu hóa truy vấn nóng, 1 chỉ mục **GIN** (`idx_knowledge_chunks_search_vector`) cho tìm kiếm toàn văn bản `tsvector`, và 1 chỉ mục **HNSW** (`idx_knowledge_chunks_embedding_hnsw` với `vector_cosine_ops`) cho tìm kiếm tương đồng ngữ nghĩa `pgvector`.

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)

| Tiêu chí | Quyết định Lựa chọn v3.2 | Lý do & Giá trị Đạt được |
| :--- | :--- | :--- |
| **Chuẩn hóa 3NF/BCNF trên 35 Bảng** | Bổ sung 7 bảng chuyên biệt (`learner_memory_items`, `learner_concept_masteries`, `knowledge_sources`, `knowledge_chunks`, `schedule_blocks`, `workflow_runs`, `workflow_step_executions`). | Mọi thuộc tính không khóa phụ thuộc hàm toàn phần và trực tiếp vào khóa ứng viên; loại bỏ hoàn toàn nhồi nhét mảng lồng nhau vào JSONB. |
| **Hybrid RAG trong PostgreSQL 16** | Dùng `pgvector` (`vector(768)`) + `tsvector` ngay trên bảng `knowledge_chunks`. | Giữ nguyên kiến trúc 4 container Docker Compose tối giản, đảm bảo giao dịch ACID đồng nhất giữa tài liệu nguồn, phân đoạn vector và lộ trình học. |
| **Tách `tasks.estimated_minutes` và `schedule_blocks.scheduled_duration_minutes`** | `tasks` lưu nỗ lực ước tính tổng; `schedule_blocks` lưu từng khối lịch cụ thể kèm `block_type` và `external_calendar_event_id`. | Cho phép chia 1 Task lớn thành nhiều buổi học, chèn Buffer/Revision/Recovery blocks, và đồng bộ chính xác từng khối với Google Calendar. |
| **Đồng bộ Nguồn Chân lý 100%** | Thống nhất con số **35 bảng (`12 / 10 / 5 / 4 / 4`)** và mô hình mặc định `'gemini-2.5-flash'` trên toàn bộ tài liệu CSDL. | Loại bỏ triệt để mọi mâu thuẫn số lượng bảng và cấu trúc thuộc tính giữa các tài liệu kiến trúc. |

---

## 5. Nguồn Chân Lý của Schema & Chiến Lược Migration (Schema Source of Truth & Migration Strategy)

* **Alembic là Nguồn Chân lý khi chạy (Runtime Source of Truth):**
  - Mọi thay đổi cấu trúc CSDL vật lý đều được hiện thực hóa thông qua các phiên bản di chuyển dữ liệu (migrations) được quản lý chặt chẽ bởi **Alembic Async** (`alembic/versions/`).
  - Khi triển khai môi trường Docker Compose hoặc Cloud Production, tiến trình khởi động của dịch vụ `backend` sẽ tự động thực thi lệnh `alembic upgrade head` trước khi khởi chạy máy chủ ASGI `uvicorn`.
* **Vai trò của `docs/database/schema.sql`:**
  - `schema.sql` (v3.2 — 35 bảng 3NF/BCNF + `pgvector`) đóng vai trò là **tài liệu thiết kế kiến trúc chuẩn mực (Design Specification Target)** và là bản DDL phục vụ cho Hội đồng chấm đồ án tốt nghiệp.
  - Kiểm thử CI (CI Pipeline) sẽ tự động kiểm tra tính tương đồng (diff check) giữa kết quả xuất từ `alembic upgrade head` trên CSDL mới với tệp `docs/database/schema.sql` để đảm bảo không xảy ra hiện tượng trôi dạt lược đồ (schema drift).

---

## 6. Hệ quả & Kiểm chứng (Consequences & Verification)

* **Tích cực:** Lược đồ CSDL 35 bảng đạt độ chuẩn xác học thuật và kỹ thuật cao nhất (Rubric TC2.1 & TC2.3 Mức 5), đáp ứng trọn vẹn cả 28 Use Cases của SRS v1.3 lẫn toàn bộ năng lực của **FocusFlow Learning Intelligence Harness**.
* **Kiểm chứng Tự động:**
  - Tập lệnh `schema.sql` v3.2 kích hoạt `CREATE EXTENSION IF NOT EXISTS vector;` và định nghĩa chính xác 35 câu lệnh `CREATE TABLE` (`12 account, 10 planning, 5 execution, 4 evaluation, 4 shared_kernel`).
  - Đầy đủ 26 triggers `fn_set_updated_at()`, 67 chỉ mục chuyên biệt (B-Tree, Partial Unique, GIN, HNSW), tất cả các ràng buộc `CHECK`, `UNIQUE`, và `FOREIGN KEY`.
  - Không có bất kỳ mâu thuẫn hay trôi dạt nào giữa các tài liệu CSDL cốt lõi.
