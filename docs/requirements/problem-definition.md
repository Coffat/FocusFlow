# FocusFlow — Problem Definition & Requirements Discovery Document

> **Đề tài:** Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI (FocusFlow)  
> **Chuyên ngành:** Công nghệ Phần mềm — Khoa Công nghệ Thông tin  
> **Tài liệu:** Yêu cầu nghiệp vụ & Định nghĩa bài toán (Requirements Discovery Artifact)  
> **Nghiên cứu nền tảng & Đối sánh:** [Khảo sát Nhu cầu Tự học & Đối sánh Giải pháp (Benchmarking)](user-survey-and-benchmarking.md)  
> **Mục tiêu & Đo lường:** [Hệ thống Mục tiêu Nghiệp vụ & 5 Chỉ số KPI Định lượng](business-goals-and-kpis.md)  
> **Mô hình Người dùng:** [Đặc tả Tác nhân Hệ thống & Chân dung Người dùng (Personas)](system-actors-and-personas.md)  
> **Trạng thái:** Đã kiểm chứng, Audit toàn diện và Phê duyệt bởi Sinh viên / Tác giả đề tài (Baseline Frozen)  
> **Căn cứ đánh giá:** Khung Rubric chấm điểm đồ án môn học / tốt nghiệp (Tiêu chí TC1, TC2.1, TC2.3, TC2.7)

---

## 1. Problem Statement & Strategic Positioning (Phát biểu bài toán & Tuyên ngôn định vị)

### 1.1. Bối cảnh & Tuyên ngôn định vị sản phẩm (Problem Context & Positioning)
Trong kỷ nguyên số, nhu cầu tự học và tái đào tạo kỹ năng (self-directed learning & reskilling) như lập trình, ngôn ngữ, công nghệ mới... ngày càng trở nên cấp thiết. Tuy nhiên, người học theo phương thức tự do thường gặp khó khăn lớn do thiếu người hướng dẫn trực tiếp, thiếu cấu trúc lộ trình chuẩn mực và thời gian biểu phân tán không cố định.

FocusFlow không nên được định vị đơn thuần như một “AI chatbot tạo lộ trình học” hay một “ứng dụng lịch tích hợp AI”. Vị trí sản phẩm và kiến trúc chuẩn xác của FocusFlow là:

> **FocusFlow Learning Intelligence Harness — An adaptive AI-powered learning management system (Hệ điều hành & Khung điều phối học tập thích ứng tích hợp AI)** — Nền tảng toàn diện giúp người học thấu hiểu mục tiêu, lập lộ trình cá nhân hóa dựa trên tri thức chuẩn (RAG), phân bổ thời gian biểu tất định, thực thi phiên học tập trung kèm check-in/kiểm chứng thực chất, và liên tục thích ứng, cải tiến mô hình người học khi đời sống làm gián đoạn.

Hệ thống thống nhất **Chu trình Trí tuệ Học tập 6 Bước (6-Step Learning Intelligence Loop: Understand → Plan → Schedule → Adapt → Learn → Improve)** với **Mô hình Học tập Tự điều chỉnh 3 Pha của Zimmerman (SRL)**:
- **Pha 1 — Forethought (Hoạch định & Chuẩn bị) = `Understand + Plan + Schedule`:**
  1. **Understand (Thấu hiểu):** Thu thập mục tiêu (`Goal`), đối thoại làm rõ với AI (`Goal Clarification`), nạp tài liệu học tập đầu vào qua **Knowledge Ingestion & Hybrid RAG Pipeline** (`knowledge_sources`, `knowledge_chunks`), và cấu hình quỹ thời gian rảnh hợp nhất (`UnifiedAvailabilityModel`).
  2. **Plan (Lập lộ trình):** AI phân rã mục tiêu thành lộ trình 2 cấp (`Milestones` & `Tasks` với nỗ lực ước tính `estimated_effort`), đồ thị phụ thuộc tiên quyết DAG, tài nguyên học tập (`Learning Resources`) kèm trích dẫn nguồn (provenance citations), và dự báo tính khả thi (`Goal Feasibility Prediction`).
  3. **Schedule (Lập thời gian biểu):** **Deterministic Scheduling Engine** tự động phân bổ các task thành các phiên học cụ thể (`schedule_blocks` với `scheduled_duration_minutes`, cho phép tách một task 120 phút thành 2 phiên 60 phút), áp dụng quy tắc chống vỡ lịch (**Schedule Resilience**: Buffer Time, Recovery Window, Daily Workload Cap, Protected Sessions, Schedule Stability), đi qua Cổng Kiểm Duyệt 3 Tầng và chờ người học bấm `Apply` thành `OfficialSchedule` (hoặc mô phỏng `What-if Planning`).
- **Pha 2 — Performance (Thực thi & Kiểm chứng) = `Execute + Check-in + Prove` (Nằm giữa Schedule và Adapt/Learn):**
  - **Execute & Daily Learning Check-in:** Giảm ma sát vào phiên học với Today Focus View, Study Workspace (Pomodoro/Stopwatch, MVS Mode 10–15 phút, Scratchpad), và thu thập **Daily Learning Check-in** cuối phiên (`checkin_time_sufficiency`, `checkin_perceived_difficulty`, `checkin_focus_level`).
  - **Prove (Chứng minh năng lực & Mistake Intelligence):** Bắt buộc đúc kết Key Takeaways (Anti-Gaming Gate Tầng 1), kiểm chứng cột mốc qua **Prove Mode** (AI Recall & Blind-Spot Probing), ôn tập ngắt quãng (**Intelligent Revision**) và phân loại lỗi sai (**Mistake Intelligence** trong `milestone_proofs.mistake_taxonomy_json`: `MISSING_FOUNDATION`, `CONCEPT_MISCONCEPTION`, `PROCESS_ERROR`, `LACK_OF_PRACTICE`).
- **Pha 3 — Self-Reflection (Phản tư, Thích ứng & Tiến hóa) = `Adapt + Learn + Improve`:**
  4. **Adapt (Thích ứng & Phục hồi):** Phát hiện quá hạn tất định, tái lập lịch theo cửa sổ trượt (**Rolling-Horizon Overdue Recovery**: Overdue Detection → Impact Analysis → Optional Reason Collection → AI Replanning Strategy + Deterministic Scheduling Engine → 3-Tier Gate → Recovery Proposal Diff Approval), **Adaptive Workload**, thuật toán Domino Shift khi tạm dừng, Weekly Reschedule Budget và Post-Failure Reset Ritual.
  5. **Learn (Thấu hiểu người học & Tích lũy bộ nhớ):** Trích xuất và cập nhật **Structured Learner Memory** (`learner_memory_items` gồm 4 loại `PROFILE`/`BEHAVIORAL`/`KNOWLEDGE`/`INTERACTION` và 3 tầng nhận thức `EXPLICIT`/`OBSERVED`/`INFERRED`) cùng **Skill Mastery Tracking** (`learner_concept_masteries`).
  6. **Improve (Cải tiến liên tục):** Thực hiện **Weekly Review & Reflection** (kết hợp câu hỏi phản tư chủ quan trong `ai_reviews.user_reflection_payload` với số liệu định lượng khách quan) để hiệu chỉnh chiến lược học tập và ước lượng thời gian cho các chu kỳ tiếp theo.

### 1.1.1. Phân tách Nền tảng 3 Thực thể Cốt lõi (Foundational Separation of 3 Core Entities)
Kiến trúc **FocusFlow Learning Intelligence Harness** tách biệt rạch ròi 3 thực thể cốt lõi (được lưu trữ trên **35 bảng PostgreSQL 16 chuẩn 3NF/BCNF**: 12 `account`, 10 `planning`, 5 `execution`, 4 `evaluation`, 4 `shared_kernel`):
1. **Roadmap (Lộ trình — Học những gì và theo thứ tự nào):** Bao gồm `goals`, `roadmaps`, `milestones`, `tasks` (với `estimated_effort`), `task_dependencies`, `learning_concepts`, `concept_prerequisites`, `knowledge_sources`, `knowledge_chunks`. Định nghĩa cấu trúc sư phạm và thứ tự tiên quyết bất biến của mục tiêu học tập.
2. **Schedule (Thời gian biểu — Học vào thời điểm nào):** Bao gồm `official_schedules`, `schedule_proposals`, `schedule_blocks` (với `scheduled_duration_minutes`). **Tính chất quyết định:** Khi người học thay đổi quỹ thời gian rảnh (ví dụ: giảm từ 2 giờ/ngày xuống 1 giờ/ngày hoặc thêm sự kiện bận trên Google Calendar), hệ thống **chỉ cần chạy lại Schedule Optimization để phân bổ lại `schedule_blocks` mà không phải tạo lại Roadmap**.
3. **Learner Model (Mô hình người học — Học như thế nào và cần hỗ trợ ra sao):** Bao gồm `learner_profiles`, `learner_memory_items` (Structured Learner Memory) và `learner_concept_masteries` (Skill Mastery Tracking). Mô hình này được bảo tồn và tích lũy lâu dài xuyên suốt nhiều Roadmap khác nhau của người học.

### 1.2. Vấn đề cốt lõi & Phân mảnh công cụ (Core Problem & Tool Fragmentation)
Người tự học không thất bại vì thiếu tài liệu, mà vì không duy trì được tính liên tục của hành vi tự học trong điều kiện đời sống không ổn định. Cụ thể, họ đối mặt với 3 đứt gãy lớn:

1. **Rào cản phân rã mục tiêu (Decomposition Barrier):** Người học thường bắt đầu bằng mục tiêu lớn (*"Học Backend trong 3 tháng"*, *"Ôn AWS SAA trong 8 tuần"*), nhưng không biết biến mục tiêu đó thành milestone nào trước, task nào trong tuần, hôm nay học gì, mỗi task cần bao lâu, và thứ tự kiến thức nào không được đảo lộn. ChatGPT có thể sinh roadmap văn bản, nhưng không trở thành hệ thống hành động.
2. **Quá tải và phân mảnh công cụ (Tool Fragmentation & Cognitive Overhead):** Người học phải chắp vá 4–5 công cụ rời rạc để quản lý chu trình học, làm tiêu hao năng lượng ý chí (planning fatigue) trước khi thực sự bắt đầu học:

| Nhu cầu tự học | Công cụ rời rạc thường dùng | Vấn đề & Hệ quả đứt gãy |
|---|---|---|
| Xin lộ trình học | ChatGPT / Claude | Kết quả dạng text thụ động, không có lifecycle, không gắn với thời gian rảnh thực tế |
| Xếp lịch & Nhắc giờ | Google Calendar / Apple Calendar | Lịch tĩnh, coi bài học như cuộc hẹn nha sĩ, không hiểu logic tiên quyết (prerequisites), lỡ 1 buổi là vỡ cả chuỗi |
| Ghi chú & Quản lý tri thức | Notion / Obsidian | Dễ biến thành "kho lưu trữ thụ động" (hoarding), gánh nặng thiết lập template quá cao, không kéo người học vào hành động |
| Bấm giờ tập trung | Pomodoro apps độc lập (Forest, BeFocused) | Tách rời hoàn toàn khỏi Task, Checklist và Note; không lưu vết ngữ cảnh học tập |
| Theo dõi tiến độ | Todoist / Trello / Excel / Sheets | Danh sách việc phẳng, không kết nối với phiên học thực tế, không có cơ chế phục hồi khi vỡ lịch |

> **Hệ quả:** Người học phải đóng vai "project manager bất đắc dĩ của chính mình" thay vì tập trung năng lượng vào việc tiếp thu kiến thức.

3. **Đứt gãy kỷ luật khi có biến cố (Rigid Planning Failure):** Một lộ trình học tập không giống một cuộc họp công sở. Nếu bỏ lỡ một buổi học nền tảng, người học không thể chỉ đơn giản “xóa sự kiện” rồi đi tiếp. Kế hoạch bị dồn ứ, việc kéo thả thủ công từng mốc lịch mất 20–30 phút gây cảm giác tội lỗi và nản chí, dẫn đến 85%–95% người tự học từ bỏ giữa chừng.

---

## 2. Target Users & Stakeholders (Người dùng & Các bên liên quan)

### 2.1. Chân dung người dùng mục tiêu (Primary User Persona)
- **Đối tượng trung tâm:** Người tự học / Cá nhân phát triển kỹ năng (Self-Directed Learners).
- **Đặc điểm hành vi:**
  - Thời gian học linh hoạt, tranh thủ ngoài giờ làm việc hoặc giờ học chính khóa.
  - Trình độ công nghệ ở mức phổ thông đến khá, quen thuộc với các ứng dụng web hiện đại.
  - Có động lực học tập nhưng dễ bị chi phối bởi áp lực thời gian và thiếu tính kỷ luật nếu không có kế hoạch rõ ràng.

### 2.2. Vai trò trong hệ thống (System Actors)
1. **Learner (Người học / End-User - Tác nhân chính):**
   - Đăng ký, đăng nhập tài khoản trước khi tạo kế hoạch để định danh và quản trị hạn ngạch.
   - Thiết lập cấu hình thời gian rảnh theo mô hình lai (Hybrid Availability) và hồ sơ học tập.
   - Tương tác với AI để làm rõ mục tiêu, xem xét đề xuất lịch trình (Schedule Proposal), chỉnh sửa và bấm "Apply" để lưu thành Lịch chính thức (Official Schedule).
   - Sử dụng bộ công cụ hỗ trợ (Study Tool Suite: Timer Pomodoro/Stopwatch, Scratchpad, Key Takeaways, Task Checklist) trong phiên học.
   - Nhận báo cáo thống kê định lượng và phản hồi/đánh giá định tính từ AI Review.
   - Đồng bộ lịch học 2 chiều có kiểm soát với ứng dụng lịch ngoài, đăng ký nhận lịch qua URL WebCal bí mật (Secure Token Feed) hoặc xuất file `.ics`.
   - Nâng cấp gói học tập (Premium) và thực hiện thanh toán trực tuyến qua cổng thanh toán.
2. **Administrator (Quản trị viên hệ thống - Tác nhân chính nội bộ):**
   - Quản lý người dùng, phân tầng gói cước (Free vs. Premium), hạn ngạch gọi dịch vụ AI (Token usage & Request Quota) và tra cứu lịch sử giao dịch thanh toán.
   - Giám sát trạng thái hoạt động, các chỉ số vận hành hệ thống, mức tiêu thụ tài nguyên AI và thống kê doanh thu gói cước.
3. **External LLM Service (Dịch vụ AI ngôn ngữ lớn - Tác nhân hệ thống ngoài):**
   - Cung cấp năng lực phân tích ngữ cảnh mục tiêu, phân rã lộ trình 2 cấp (Milestones & Schedule Proposal), tái cấu trúc lịch khi trễ hạn và đánh giá định kỳ theo cấu trúc JSON Schema nghiêm ngặt.
4. **External Calendar Application (Ứng dụng Lịch ngoại vi - Tác nhân hệ thống ngoài):**
   - Tích hợp đồng bộ 2 chiều có kiểm soát với FocusFlow: cung cấp dữ liệu khoảng thời gian bận (Free/Busy intervals) chiều Inbound từ Google Calendar và tiếp nhận sự kiện Lịch học chính thức (Official Schedule) chiều Outbound qua kết nối API, luồng WebCal bảo mật hoặc tệp `.ics`.
5. **Payment Gateway (Cổng thanh toán trực tuyến - Tác nhân hệ thống ngoài):**
   - Cung cấp API khởi tạo giao dịch thanh toán trực tuyến (mã QR / Checkout URL qua PayOS / VNPay Sandbox) và gửi thông báo kết quả giao dịch tức thời về FocusFlow qua Webhook/IPN có chữ ký số bảo mật (HMAC-SHA256).

### 2.3. Các bên liên quan gián tiếp (External Stakeholders)
- **Giảng viên hướng dẫn & Hội đồng chấm tốt nghiệp:** Đánh giá chất lượng kỹ thuật, tính làm chủ sản phẩm, và mức độ hoàn thiện đề tài theo bảng Rubric 100 điểm của Khoa CNTT.

---

## 3. Current Situation & Benchmarking (Hiện trạng & Đối sánh giải pháp)

Đáp ứng tiêu chí **TC1 (Mức 5: So sánh $\ge 3$ giải pháp hiện có, nêu rõ khoảng trống với phân tích thực tế khách quan)**:  
> *Chi tiết phân tích sâu 8 giải pháp và số liệu thực chứng xem tại:* [Khảo sát Nhu cầu Tự học & Đối sánh Giải pháp](user-survey-and-benchmarking.md) và hồ sơ môn học [WBS 1.1 — Khảo sát & Benchmarking](../../docs_ute/04_wbs_deliverables/WBS%201.1%20-%20Kh%E1%BA%A3o%20s%C3%A1t%20nhu%20c%E1%BA%A7u%20t%E1%BB%B1%20h%E1%BB%8Dc%20v%C3%A0%20nghi%C3%AAn%20c%E1%BB%A9u%20%C4%91%E1%BB%91i%20s%C3%A1nh%20gi%E1%BA%A3i%20ph%C3%A1p%20%28Benchmarking%29.md).

| Tiêu chí so sánh | Google Calendar | Notion | Todoist | Reclaim.ai / Motion | Chatbots độc lập (ChatGPT/Claude) | **FocusFlow (Hệ thống đề xuất)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Bản chất công cụ** | Quản lý lịch tĩnh | Workspace tự do | Quản lý task phẳng (GTD) | AI tự động xếp lịch công sở | Mô hình hội thoại văn bản | **Nền tảng quản lý lộ trình học tập thích ứng khép kín** |
| **Phân rã mục tiêu tự động** | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ⚠️ Task công việc văn phòng | ⚠️ Văn bản tự do, không cấu trúc | ✅ **Làm rõ ngữ cảnh $\rightarrow$ Phân rã 2 cấp (JSON Schema Gate)** |
| **Tính liên kết ngữ cảnh học tập** | ⚠️ Chỉ có mốc giờ | ⚠️ Phải dựng template | ❌ Ghi chú rất ngắn | ❌ Định hướng lịch họp | ❌ Trôi theo lịch sử chat | ✅ **Khép kín: Lộ trình $\leftrightarrow$ Task $\leftrightarrow$ Timer $\leftrightarrow$ Scratchpad $\leftrightarrow$ Review** |
| **Cơ chế thích ứng khi trễ hạn** | ❌ Thụ động, kéo thả tay | ❌ Lọc sửa thủ công | ❌ Kéo thả tay | ⚠️ AI hộp đen xáo trộn | ❌ Không nắm được tiến độ | ✅ **Phát hiện quá hạn tất định + Email báo nhắc $\rightarrow$ AI dời lịch 1 lộ trình & Domino Shift khi tạm dừng** |
| **Không gian thực thi phiên học** | ❌ Không có | ⚠️ Widget bên ngoài | ❌ Không có | ❌ Không có | ❌ Không có | ✅ **Study Tool Suite tích hợp (Pomodoro/Stopwatch, Checklist, Takeaways)** |
| **Tổng kết & Đánh giá định kỳ** | ❌ Không có | ⚠️ Formula phức tạp | ⚠️ Karma điểm | ⚠️ Thống kê thời gian họp | ❌ Hỏi đáp rời rạc | ✅ **Thống kê định lượng toán học + AI Nhận xét định tính dựa trên Takeaways** |
| **Chi phí với Sinh viên** | Miễn phí | Miễn phí / $8+ | Miễn phí / $5 | Đắt ($10–$34/tháng) | Miễn phí / $20 | ✅ **Miễn phí cho tính năng cốt lõi / Open-source** |

### 3 Khoảng trống chiến lược (The 3 Strategic Gaps)
1. **Khoảng trống Quy trình khép kín (Workflow Gap):** Thị trường chỉ giải quyết từng mẩu rời rạc (ChatGPT gợi ý ý tưởng, Calendar giữ giờ, Pomodoro bấm giờ, Notion lưu trữ). Thiếu một nền tảng kết nối khép kín toàn bộ chu trình học tập 3 pha theo Thuyết SRL (Zimmerman).
2. **Khoảng trống Thích ứng tất định & Dời lịch cô lập phạm vi (Deterministic & Scoped Adaptation Gap):** Lịch truyền thống quá tĩnh (không tự dời), trong khi AI xếp lịch thương mại lại tự ý xáo trộn toàn bộ lịch bằng mô hình hộp đen đắt đỏ. FocusFlow áp dụng giải pháp thích ứng lai có kiểm soát: Dùng logic Backend tất định để phát hiện quá hạn kèm thông báo Email và thực thi thuật toán Domino Shift khi tạm dừng; khi người học chủ động bấm "Dời lịch hợp lý bằng AI (AI Reschedule)", AI chỉ dời lịch các task chưa hoàn thành của riêng lộ trình đó mà tuyệt đối không làm xáo trộn lịch của các lộ trình khác hay sự kiện cá nhân.
3. **Khoảng trống Kiểm duyệt có kiểm soát (Human-in-the-Loop Approval Gap):** Người học mất niềm tin nếu AI tự ý ghi đè lịch trình. FocusFlow thiết lập cơ chế kiểm duyệt minh bạch: Kế hoạch AI sinh ra ở trạng thái Đề xuất (Schedule Proposal); người học có quyền tùy biến trước khi bấm "Apply" để kích hoạt thành Lịch chính thức.

### 3.1. Ba Trụ cột Cạnh tranh (3 Competitive Pillars), Controlled Adaptive Recovery & 7 Hào Sản Phẩm (Product Moats)
FocusFlow xây dựng năng lực khác biệt vượt trội dựa trên **3 Trụ cột Cạnh tranh Cốt lõi (3 Competitive Pillars)**:
1. **Trụ cột 1 — Lập kế hoạch Học tập Cá nhân hóa Dựa trên Tri thức (Personalized Learning Planning with Knowledge Engine RAG):** Kết hợp đối thoại làm rõ mục tiêu, nạp tài liệu thực tế của người học (PDF, DOCX, TXT, URL) qua Hybrid Search (`tsvector` + `pgvector` HNSW) kèm trích dẫn nguồn (provenance citations), dự báo tính khả thi (`Goal Feasibility Prediction`) và mô phỏng kịch bản (`What-if Planning`).
2. **Trụ cột 2 — Lập lịch & Phục hồi Thích ứng Bền vững (Adaptive Scheduling with Rolling-Horizon & Schedule Resilience):** Phân tách `Roadmap` (nội dung học) khỏi `Schedule` (`schedule_blocks` thời gian biểu), kết hợp **Deterministic Scheduling Engine** với các quy tắc chống vỡ lịch (*Buffer Time, Recovery Window, Daily Workload Cap, Protected Sessions, Schedule Stability*) và cơ chế **Rolling-Horizon Overdue Recovery** có kiểm soát.
3. **Trụ cột 3 — Trí tuệ Người học Liên tục (Continuous Learner Intelligence with Structured Learner Memory):** Tích lũy dài hạn mô hình người học (`learner_profiles`, `learner_memory_items` 4 loại $\times$ 3 tầng nhận thức, `learner_concept_masteries`), kết hợp **Daily Learning Check-in**, **Prove Mode**, **Intelligent Revision** và **Mistake Intelligence** để cá nhân hóa sâu sắc qua từng chu kỳ học.

Lợi thế cạnh tranh mạnh nhất và bền vững nhất của FocusFlow xoay quanh:

> **Controlled Adaptive Recovery for Self-Learning (Khả năng phục hồi kế hoạch học tập thích ứng có kiểm soát khi đời sống làm gián đoạn).**

Khác với các ứng dụng lịch công việc (Motion, Reclaim) tự ý xáo trộn lịch bằng mô hình hộp đen, hay các chatbot AI chỉ tạo lộ trình tĩnh rồi bỏ mặc người học, FocusFlow phục hồi kế hoạch theo cách:
- **Có kiểm soát (Human-in-the-loop):** AI chỉ sinh đề xuất (`ScheduleProposal`), người học luôn giữ quyền quyết định cuối cùng (`Apply`).
- **Có giải thích minh bạch:** Hiển thị trực quan bảng so sánh thay đổi (`Recovery Proposal Diff`) giúp người học hiểu rõ lý do dời lịch và các đánh đổi (trade-offs).
- **Không xáo trộn toàn bộ cuộc sống:** Giới hạn dời lịch trong phạm vi 1 lộ trình (`Single-Roadmap Scope`), bảo vệ nguyên vẹn lịch cá nhân và các lộ trình song song khác.
- **Bảo toàn trật tự sư phạm:** Thuật toán duy trì nghiêm ngặt đồ thị kiến thức tiên quyết (`Prerequisite Graph`), không bao giờ đảo lộn thứ tự bài học.
- **Chống trì hoãn trá hình:** Thiết lập hạn mức dời lịch có trách nhiệm, không để người học dời lịch vô hạn để trốn tránh việc học.

Hệ thống xây dựng **7 Hào sản phẩm (Product Moats)** vững chắc xoay quanh lợi thế cốt lõi này:
1. **Recovery Graph (Đồ thị phục hồi):** Đồ thị phụ thuộc kiến thức và ràng buộc thời gian giúp thuật toán dời lịch chính xác mà không phá vỡ logic tiên quyết.
2. **Reschedule Budget (Ngân sách dời lịch có trách nhiệm):** Giới hạn số lần dời lịch (quota theo tuần/milestone) để phân biệt gián đoạn chính đáng (ốm, thi cử) với thói quen trì hoãn né tránh.
3. **Accountability Log (Nhật ký trách nhiệm):** Lưu vết toàn bộ lịch sử dời lịch kèm phân loại nguyên nhân (`disruption_category`), giúp người học đối diện với thói quen thực tế của bản thân.
4. **Stalled & Dormant Detection (Phát hiện trì hoãn 2 cấp):** Phân biệt chính xác giữa task bị tắc nghẽn (`is_stalled = true`, dời $\ge 3$ lần) và lộ trình chết lâm sàng (`DORMANT`, $\ge 7$ ngày không có hoạt động học) để kích hoạt can thiệp phù hợp.
5. **Minimum Viable Session (MVS Mode 10–15 phút):** Cơ chế cứu vãn phiên học trong những ngày kiệt sức, bảo vệ danh tính tự học ("Identity Preservation") thay vì buông xuôi bỏ cuộc.
6. **Evidence-based Review & Anti-Gaming Gate (Đo lường tiến bộ thực chất):** Đánh giá dựa trên Key Takeaways bắt buộc, chấm điểm đối chiếu với Task gốc và kiểm chứng Prove Mode cuối Milestone nhằm triệt tiêu ảo tưởng năng lực.
7. **Adaptive Learning Profile (Hồ sơ học tập thích ứng):** Liên tục hiệu chuẩn từ dữ liệu thực tế (thời lượng thực học, khung giờ năng lượng cao, tỷ lệ hoàn thành) để đưa ra các ước lượng thời gian ngày càng chính xác.

---

## 4. Business Goals & Quantitative Metrics (Mục tiêu & 5 KPI nghiệp vụ)

Tuân thủ nghiêm ngặt **Nguyên tắc 3 (Chấm theo minh chứng)** và tiêu chí **TC1 Mức 5 (Chốt $\ge 5$ KPI nghiệp vụ định lượng ngay từ đầu)**:

* **KPI 1 — Thời gian khởi tạo lộ trình (Plan Creation Time):** $\le \mathbf{5}$ phút từ khi người dùng nhập mục tiêu đến khi lộ trình chi tiết hoàn chỉnh được lưu vào hệ thống (thay vì mất 30–60 phút thao tác thủ công qua nhiều ứng dụng).
* **KPI 2 — Hiệu quả thực thi buổi học (Session Execution Efficiency):** Tỷ lệ hoàn thành các đầu việc được lên kế hoạch trong mỗi buổi học (Session Task Completion Rate) đạt $\ge \mathbf{80\%}$.
* **KPI 3 — Tỷ lệ duy trì lộ trình (Plan Adherence Rate):** Người dùng duy trì tham gia tối thiểu $\ge \mathbf{70\%}$ số buổi học đã được lên lịch trong đợt thử nghiệm thực tế (loại trừ khoảng thời gian lộ trình ở trạng thái `PAUSED`).
* **KPI 4 — Tỷ lệ hoàn thành tác vụ (Task Success Rate - TC2.7):** Tỷ lệ người dùng thực hiện thành công các luồng chính (tạo lộ trình, chạy phiên Pomodoro, lưu note, xem review) đạt $\ge \mathbf{90\%}$ trong đợt thử nghiệm UAT với người dùng thật.
* **KPI 5 — Độ hài lòng trải nghiệm người dùng (SUS Score - TC2.7):** Đạt điểm đánh giá chuẩn hóa System Usability Scale (SUS) $\ge \mathbf{80/100}$ điểm khi kiểm thử thực tế với ít nhất $\ge 10$ người dùng thật thuộc đối tượng mục tiêu.

---

## 5. Proposed System Capabilities (Năng lực cốt lõi của hệ thống)

Hệ thống FocusFlow quản lý vòng đời học tập qua 4 giai đoạn logic khép kín:

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ Giai đoạn 1: KHỞI TẠO LỘ TRÌNH & DUYỆT LỊCH (Hierarchical Adaptive Planning)   │
│ Onboarding (Auth) ──> Input mục tiêu ──> AI làm rõ ──> Duyệt Milestones       │
│                   ──> AI sinh Schedule Proposal ──> User edits & Clicks APPLY │
│                   ──> Backend Validation ──> Official Schedule (Persist)     │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│ Giai đoạn 2: KHÔNG GIAN THỰC THI (Active Study Workspace)                     │
│ Task Checklist ── Bộ công cụ hỗ trợ (Pomodoro/Timer) ── Scratchpad ── Takeaway│
│ (Xử lý dừng sớm: Lưu phút thực học, task dở dang quay về Backlog)            │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│ Giai đoạn 3: THÍCH ỨNG & QUẢN TRỊ LỊCH (Adaptive Shift & Calendar Management) │
│ - Quét Overdue tất định + Email ──> Dời lịch hợp lý bằng AI (1 lộ trình)       │
│ - Tạm dừng lộ trình (Pause Roadmap) ──> Domino Shift tự động đẩy lùi lịch     │
│ - Đồng bộ lịch 2 chiều có kiểm soát (Free/Busy Inbound + Official Outbound)   │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│ Giai đoạn 4: TỔNG KẾT & CẢI TIẾN (Review & Continuous Retrospective)         │
│ Thống kê định lượng ──> Key Takeaways ──> AI Review & Lời khuyên chu kỳ tới   │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 5.1. Khởi tạo lộ trình 2 cấp độ & Quy trình phê duyệt nghiêm ngặt (Workflow M2)
- **Bắt buộc định danh trước (Onboarding First):** Người dùng phải đăng ký/đăng nhập trước khi sử dụng AI để gắn quyền sở hữu lộ trình và kiểm soát Quota.
- **Làm rõ mục tiêu:** Thu thập thông tin nền tảng, phong cách học và thời gian rảnh.
- **Duyệt 2 cấp độ:**
  - *Cấp 1:* AI sinh **Milestones tổng quan** $\rightarrow$ Người dùng xem xét, chỉnh sửa và bấm duyệt.
  - *Cấp 2:* Dựa trên Milestone đã duyệt và mô hình thời gian rảnh (Hybrid Availability), AI sinh **Schedule Proposal (Bản đề xuất lịch trình)** gồm các task chi tiết.
- **Quy trình phê duyệt (Strict Apply Workflow):** Đề xuất của AI **không bao giờ tự động lưu thành lịch chính thức**. Người dùng xem xét, điều chỉnh các task trong đề xuất và chủ động bấm nút "Apply". Backend tiến hành kiểm tra tính hợp lệ (Validation Gate); khi đạt chuẩn, đề xuất mới được lưu vào cơ sở dữ liệu thành **Official Schedule**.

### 5.2. Mô hình Thời gian rảnh lai (Hybrid Availability Model)
Hệ thống hỗ trợ 2 chế độ cấu hình thời gian học:
1. **Mode A — Daily Hours Quota (Quỹ giờ trong ngày):** Người dùng nhập tổng số giờ rảnh mỗi ngày (ví dụ: Thứ Hai 2h, Thứ Bảy 4h). Hệ thống xếp task sao cho tổng thời lượng không vượt quá số giờ rảnh.
2. **Mode B — Time Slot Window (Khung giờ cố định):** Người dùng thiết lập các khung giờ rảnh cụ thể (ví dụ: 19:00 – 21:00). Các task được gán mốc giờ bắt đầu và kết thúc cụ thể.
   - *Quy tắc tràn biên có kiểm soát (Soft Overflow):* Task bắt buộc phải nằm trong khung giờ rảnh; riêng task cuối cùng trong ngày được phép vượt quá mốc kết thúc tối đa 30 phút kèm cảnh báo để người dùng chủ động xác nhận (Quyết định 3B).
- **Cơ chế xếp đa lộ trình (Multi-roadmap Capacity - Quyết định 1C):** Người dùng có thể học nhiều lộ trình; hệ thống tự động kiểm tra dung lượng thời gian rảnh còn lại và xếp task của lộ trình mới vào các khoảng trống (slots) tiếp theo.

### 5.3. Không gian thực thi phiên học & Xử lý gián đoạn (Session Interruption)
- Bảng danh sách công việc cần hoàn thành trong phiên (Task Checklist).
- Bộ công cụ đa năng: Đồng hồ đếm giờ Pomodoro / Stopwatch linh hoạt.
- Cấu trúc Note 2 tầng: *Scratchpad* (chép nhanh ghi chú thô, code, liên kết) và *Key Takeaway* (1–2 câu đúc kết trước khi kết thúc phiên).
- **Hành vi xử lý khi hủy / dừng sớm (Quyết định Interruption):** Hệ thống lưu chính xác số phút thực học đã trôi qua và đánh dấu hoàn thành cho các task đã tick. Phiên học chuyển trạng thái `CANCELLED` hoặc `PARTIAL_COMPLETED`. Các task chưa hoàn thành tự động quay về hàng đợi Backlog an toàn, không phạt người dùng.

### 5.4. Cơ chế thích ứng khi trễ hạn & Tạm dừng lộ trình (Adaptive Recovery & Pause)
- **Phát hiện quá hạn tất định & Thông báo Email (Deterministic Overdue Detection & Email Notification - Quyết định M1):** Định kỳ lúc `00:05 UTC+7` hàng ngày, tác vụ nền Backend quét phát hiện các task quá hạn theo công thức tất định: `task.status != 'COMPLETED' AND task.scheduled_date < CURRENT_DATE`. Hệ thống **không tự động ghi đè ngầm `scheduled_date`**, mà đánh dấu trạng thái dẫn xuất `OVERDUE` và **gửi Email thông báo nhắc nhở** tới địa chỉ email đăng ký của người học (qua cổng nội bộ `EmailNotificationPort` / SMTP Adapter). Khi người học đăng nhập lại vào ứng dụng Web, hệ thống hiển thị các task quá hạn trong khu vực **"Task Cần Chú Ý (`OVERDUE`)"** kèm nút **"Dời lịch hợp lý bằng AI (AI Reschedule)"** và tùy chọn tự dời lịch thủ công.
- **Dời lịch hợp lý bằng AI trong phạm vi 1 lộ trình (Single-Roadmap AI Reschedule):** Khi người học chủ động bấm nút **"Dời lịch hợp lý bằng AI"**, AI quét danh sách các task chưa hoàn thành còn lại của **riêng lộ trình đó (Single Roadmap)** cùng lịch trình tương lai của người học (tính toán dựa trên cấu hình thời gian rảnh Mode A/B và trừ đi các khoảng thời gian đã bị chiếm dụng bởi các lộ trình khác hoặc sự kiện lịch ngoài) để sắp xếp lại hợp lý **chỉ các task thuộc lộ trình đó**, tuyệt đối **không thay đổi hay xê dịch lịch của các lộ trình khác hoặc lịch cá nhân của người dùng**. Mọi đề xuất dời lịch từ AI **bắt buộc phải đi qua Cổng Kiểm Duyệt 3 Tầng (3-Tier Validation Gate)**: Tầng 1 kiểm tra cú pháp JSON Schema, Tầng 2 kiểm tra tất định tính khả thi dung lượng và xung đột thời gian rảnh, Tầng 3 đánh giá tính hợp lý sư phạm và bảo toàn đồ thị tiên quyết. Đề xuất dời lịch được lưu trữ dưới dạng **`ScheduleProposal` ở trạng thái `DRAFT` (tuyệt đối không tự động ghi đè lên Lịch chính thức `OfficialSchedule`)**, đồng thời hệ thống hiển thị bảng đối chiếu thay đổi **Recovery Proposal Diff** (cho biết rõ task nào bị dời, dời sang ngày nào, lý do dời và tác động lên deadline). Người học bắt buộc phải chủ động xem xét và bấm nút **"Apply"** thì Lịch chính thức mới được cập nhật (`reschedule_count = reschedule_count + 1` đối với các task quá hạn được dời; nếu `reschedule_count >= 3`, đánh dấu `is_stalled = true` và kích hoạt gợi ý chia nhỏ task Micro-stepping, chọn ngày cam kết cố định hoặc đưa về Backlog).
- **Tạm dừng lộ trình (Pause Roadmap - Quyết định 4A):** Cho phép người học tạm dừng lộ trình từ ngày A đến ngày B (ví dụ: bận thi cử). Hệ thống áp dụng **thuật toán tịnh tiến dây chuyền (Domino Shift)**: toàn bộ các ngày học từ mốc bắt đầu tạm dừng sẽ tự động lùi về sau đúng số ngày rảnh tương ứng, giữ nguyên thứ tự task. Khoảng thời gian tạm dừng không bị tính cảnh báo quá hạn.

### 5.5. Đồng bộ Lịch ngoại vi 2 chiều có kiểm soát (Controlled Two-Way Calendar Sync - Quyết định 2A)
- **Chiều Inbound (Lịch ngoài $\rightarrow$ FocusFlow):** Đọc các khoảng thời gian bận (Free/Busy intervals) từ Google Calendar của người học để tự động trừ dung lượng thời gian rảnh khả dụng khi lập lịch hoặc tái cấu trúc lộ trình, đảm bảo lịch học đề xuất không đè lên lịch cá nhân/công việc sẵn có.
- **Chiều Outbound (FocusFlow $\rightarrow$ Lịch ngoài):** Đồng bộ các nhiệm vụ thuộc Lịch học chính thức (Official Schedule) ra ứng dụng lịch ngoài (Google Calendar / Apple Calendar qua kết nối API hoặc luồng đăng ký WebCal Subscription Feed chứa mã bảo mật ngẫu nhiên: `https://focusflow.app/api/v1/feeds/{user_secure_token}.ics`) và hỗ trợ tải về tệp tĩnh `.ics`.
- Người dùng có quyền bấm nút "Tạo lại liên kết mới (Reset Token)" hoặc ngắt kết nối lịch trên giao diện để thu hồi quyền truy cập ngay lập tức khi cần bảo mật.
- Luồng đồng bộ Outbound và WebCal Feed tuyệt đối chỉ xuất các task thuộc Official Schedule đã được Apply.

### 5.6. Báo cáo định lượng và AI Review chu kỳ
- Thống kê định lượng: Tổng thời gian tập trung thực tế, tỷ lệ hoàn thành task theo tuần/tháng bằng các hàm toán học chính xác.
- Báo cáo định tính: AI Review đọc số liệu thống kê thực tế và các Key Takeaways để đưa ra nhận xét, cảnh báo điểm nghẽn và lời khuyên điều chỉnh lộ trình cho chu kỳ tiếp theo.

---

## 6. Scope & Boundaries (Phạm vi dự án)

Nhằm bảo đảm tính khả thi, hoàn thành 100% khối lượng cam kết (TC2.2) và tránh các quy tắc chặn điểm (G1, G9):

### 6.1. Trong phạm vi (In-Scope — Core MVP)
- **Module Quản lý tài khoản & Hồ sơ:** Đăng ký, đăng nhập, bảo vệ phiên, cấu hình thời gian rảnh lai (Mode A / Mode B) và hồ sơ thói quen học tập.
- **Module Quản trị viên Tối giản (Minimal Web Admin Portal):** Cung cấp các màn hình cốt lõi với kiểm soát truy cập theo vai trò (RBAC `role='ADMIN'`): (1) Quản lý danh sách người dùng, trạng thái tài khoản, gói cước và tra cứu giao dịch thanh toán; (2) Khóa/mở khóa tài khoản và điều chỉnh hạn ngạch khi cần thiết; (3) Giám sát tổng quan chỉ số vận hành, mức tiêu thụ hạn ngạch AI và doanh thu gói cước toàn hệ thống.
- **Module Lập kế hoạch AI:** Luồng tương tác hỏi-đáp, sinh Milestone, sinh Schedule Proposal, giao diện review/edit, nút Apply kèm Backend Validation Gate.
- **Module Không gian phiên học:** Bảng task, Study Tool Suite (Pomodoro timer/Stopwatch), Scratchpad note, Key Takeaways, xử lý phiên bị gián đoạn.
- **Module Thích ứng & Lịch trình:** Thuật toán phát hiện quá hạn tất định, tính năng Tạm dừng lộ trình (Domino Shift), và **Đồng bộ lịch ngoại vi 2 chiều có kiểm soát (Controlled Two-Way Calendar Sync: đọc lịch bận Free/Busy + xuất lịch chính thức qua kết nối API / URL WebCal Feed bảo mật / tệp `.ics`)**.
- **Module Báo cáo & AI Review:** Thống kê định lượng chính xác và trợ lý AI Review định kỳ.
- **Module Quản trị Hạn ngạch & Thanh toán (Quota Service & Online Payment Gateway - Quyết định M3):** Middleware kiểm soát số lượt gọi AI theo phân tầng Free/Premium; **Tích hợp Cổng thanh toán trực tuyến (Payment Gateway — PayOS / VNPay Sandbox)** để nâng cấp gói tài khoản lên Premium qua mã QR/liên kết thanh toán và xác thực kết quả giao dịch tự động qua Webhook/IPN có chữ ký số bảo mật.

### 6.2. Ngoài phạm vi (Out-of-Scope — Tuyệt đối không làm trong đồ án này)
- **Sửa đổi/xóa trực tiếp cấu trúc lộ trình học tập từ ứng dụng lịch bên ngoài:** Không cho phép thao tác kéo thả hoặc xóa sự kiện trên Google/Apple Calendar làm thay đổi ngược lại cấu trúc Milestone/Roadmap gốc hoặc tự động ghi đè Official Schedule mà không qua cổng kiểm tra tính hợp lệ (Validation Gate) của FocusFlow.
- **Hoàn tiền tự động đa tiền tệ phức tạp (Complex Multi-currency Automated Refunds & Chargebacks):** Không triển khai hệ thống kế toán hoàn tiền tự động đa tiền tệ quốc tế, xử lý tranh chấp thẻ tín dụng (chargeback) hay chia sẻ doanh thu phức tạp.
- **Hệ thống Quản trị Doanh nghiệp Mở rộng (Enterprise Admin / Multi-tenant CMS):** Không triển khai các tính năng quản trị quy mô doanh nghiệp phức tạp như CMS biên tập khóa học, quản lý tổ chức đa cấp độ, xuất hóa đơn VAT hay phân quyền động tùy biến (chỉ tập trung Minimal Web Admin Portal phục vụ đồ án).
- **Ứng dụng Native Mobile (iOS/Android):** Không viết app native, chỉ tập trung hoàn thiện Web Application responsive đa thiết bị.
- **Tính năng mạng xã hội / Nhóm học tập:** Không làm tính năng kết bạn, chat, chia sẻ lộ trình giữa các người dùng.

### 6.3. Phân tầng Tính năng 3 Nhóm (Nhóm A, Nhóm B, Nhóm C) & Lộ trình Triển khai 5 Giai đoạn (5-Phase Implementation Roadmap)

Để đảm bảo tính khả thi kỹ thuật, tối ưu hóa nguồn lực và mở rộng có chiến lược, các tính năng của **FocusFlow Learning Intelligence Harness** được phân loại thành **3 Nhóm ưu tiên (Feature Tiers)**:
- **Nhóm A — Core Differentiators (Trọng tâm bắt buộc triển khai hoàn chỉnh):**
  - Tách biệt 3 thực thể cốt lõi (`Roadmap`, `Schedule` với `schedule_blocks`, `Learner Model`).
  - Lập kế hoạch thông minh: Goal Clarification, Decoupled Roadmap & Deterministic Schedule Generation, Unified Availability Model (Mode A/B + Google Calendar `freeBusy`/`syncToken`), Schedule Resilience (*Buffer Time, Recovery Window, Daily Workload Cap, Protected Sessions, Schedule Stability*), Goal Feasibility Prediction.
  - Thực thi & Thích ứng: Today Focus View, Study Workspace (Pomodoro/Stopwatch, MVS Mode 10–15p), Daily Learning Check-in, Rolling-Horizon Overdue Recovery qua 3-Tier Validation Gate & Recovery Proposal Diff, Domino Shift, Weekly Reschedule Budget & Anti-Procrastination Mode.
  - Trí tuệ người học & Kiểm chứng: Structured Learner Memory (`learner_memory_items`), Skill Mastery Tracking (`learner_concept_masteries`), Prove Mode (2-Layer Anti-Gaming Gate).
- **Nhóm B — Advanced Intelligence Capabilities (Nâng cao chiều sâu trí tuệ học tập):**
  - Knowledge Ingestion & Hybrid RAG Pipeline (`knowledge_sources`, `knowledge_chunks` với `tsvector` + `pgvector` HNSW, SSRF Guard & `<untrusted_knowledge_context>`).
  - What-if Planning (`WHAT_IF_SIMULATION`), Adaptive Workload, Intelligent Revision (Spaced Repetition Flashcards/Quizzes/Explanation Prompts), Mistake Intelligence (`mistake_taxonomy_json`), Weekly Reflection (`user_reflection_payload`), Post-Failure Reset Ritual.
- **Nhóm C — Future Horizon (Định hướng Mở rộng Giai đoạn 5+):**
  - *Multi-Goal Optimization* (tối ưu hóa đa mục tiêu nâng cao), *Proactive Learning Coach* (huấn luyện viên chủ động), *Dynamic Learning Strategy* (tự động chuyển đổi phương pháp sư phạm), *Learning Resource Recommendation* (gợi ý học liệu bên ngoài tự động), *Personalized Assessment* (đánh giá thích ứng chuyên sâu), *Burnout Prevention Signals* (tín hiệu cảnh báo sớm kiệt sức).

**Lộ trình Triển khai Kỹ thuật 5 Giai đoạn (5-Phase Implementation Roadmap):**
1. **Phase 1 — Foundation & Core Harness Runtime:** Xây dựng nền tảng Context-First Modular Monolith, CSDL PostgreSQL 16 (**35 bảng chuẩn 3NF/BCNF**: 12 `account`, 10 `planning`, 5 `execution`, 4 `evaluation`, 4 `shared_kernel`), Shared AI Harness Runtime, ACID Quota 2 pha và 2-Stage SSE Streaming.
2. **Phase 2 — Intelligent Planning & Knowledge Engine (RAG):** Triển khai Knowledge Ingestion & Hybrid Search (`tsvector` + `pgvector`), Goal Clarification, tách biệt AI Roadmap Generation (`estimated_effort`) và Deterministic Scheduling Engine (`schedule_blocks` với `scheduled_duration`), Unified Availability Model và Schedule Resilience.
3. **Phase 3 — Execution, Daily Check-in & Rolling-Horizon Adaptation:** Hoàn thiện Today Focus View, Study Workspace, MVS Mode, Daily Learning Check-in, Rolling-Horizon Overdue Recovery, Adaptive Workload, Domino Shift, Reschedule Budget và Post-Failure Reset Ritual.
4. **Phase 4 — Learner Intelligence, Mastery & Prove Mode:** Triển khai Structured Learner Memory (`learner_memory_items`), Skill Mastery Tracking (`learner_concept_masteries`), Prove Mode 2 tầng, Mistake Intelligence, Intelligent Revision, What-if Planning và Weekly Review & Reflection.
5. **Phase 5 — Ecosystem & Future Horizon (Nhóm C):** Mở rộng các năng lực Nhóm C (*Multi-Goal Optimization, Proactive Learning Coach, Dynamic Learning Strategy, Learning Resource Recommendation, Personalized Assessment, Burnout Prevention Signals*) và nền tảng di động/cộng đồng.

---

## 7. System Constraints & Non-Functional Requirements (Ràng buộc NFRs kỹ thuật)

Tuân thủ tiêu chí **TC2.1 (Mức 5: Có $\ge 5$ yêu cầu phi chức năng có ràng buộc định lượng, đo lường được bằng công cụ kỹ thuật)**:

1. **NFR 1 — Thời gian phản hồi AI & Ngắt cứng (AI Latency & Hard Timeout - Quyết định C2):** Quá trình sinh lộ trình từ AI hoàn tất trong vòng $\le \mathbf{60}$ giây. Backend áp dụng ngắt cứng (hard timeout) ở giây thứ 55; nếu quá thời gian hoặc gặp lỗi nhà cung cấp (503, 429), backend trả về mã lỗi có cấu trúc để giao diện hiển thị thông báo kèm nút [Thử lại] và [Tạo kế hoạch thủ công].
2. **NFR 2 — Độ trễ thao tác thường nhật (UI Interaction Latency):** Các tác vụ tương tác cơ bản nội bộ (tick task, khởi động/dừng timer, lưu scratchpad) phản hồi giao diện tức thì trong vòng $\le \mathbf{500}$ ms; API backend tương ứng phản hồi $\le \mathbf{200}$ ms ở mức tải 20 người dùng đồng thời.
3. **NFR 3 — Bảo mật và Quyền riêng tư (Privacy & Sanitization):** Dữ liệu nhạy cảm (mật khẩu người dùng, ghi chú bí mật cá nhân) tuyệt đối không được gửi vào prompt của LLM bên ngoài; 100% mật khẩu được băm (hashing); 100% API key và secrets được quản lý qua biến môi trường an toàn (đáp ứng tiêu chí TC2.4: 0 secret bị lộ).
4. **NFR 4 — Độ sẵn sàng hệ thống (System Availability):** Hệ thống triển khai trên môi trường staging/production công khai đạt độ sẵn sàng tối thiểu $\ge \mathbf{95\%}$ trong suốt đợt thử nghiệm người dùng.
5. **NFR 5 — Tính tương thích & Tiếp cận kỹ thuật (Responsive Web & Accessibility - Quyết định C1):** Giao diện web tương thích hoàn toàn trên Desktop ($\ge 1024$px) và Mobile ($375$px – $768$px) không bị lỗi tràn bố cục; đạt điểm kiểm định Google Lighthouse Accessibility $\ge \mathbf{90}$ điểm.

---

## 8. Assumptions & AI Risk Controls (Giả định & Kiểm soát rủi ro AI - TC2.3)

Để đạt điểm tối đa ở tiêu chí **TC2.3 (Mức độ làm chủ và năng lực kiểm soát khi sử dụng LLM / Agentic AI)**:

### 8.1. Các giả định chính (Key Assumptions)
- Người dùng có kết nối mạng Internet ổn định trong quá trình tương tác với hệ thống.
- Dịch vụ mô hình ngôn ngữ lớn (LLM API) bên thứ ba hỗ trợ cơ chế Structured Outputs (JSON Schema).

### 8.2. Ma trận rủi ro AI và Cơ chế kiểm soát kỹ thuật

| Rủi ro AI (AI Failure Mode) | Biểu hiện cụ thể | Cơ chế kiểm soát kỹ thuật của FocusFlow (TC2.3) |
|---|---|---|
| **1. Lỗi cấu trúc / Hỏng định dạng (Schema Failure)** | AI trả về văn bản tự do, JSON thiếu trường hoặc sai cú pháp. | **Validation Gate:** Backend kiểm tra schema nghiêm ngặt trước khi trả về client. Tự động gửi lại yêu cầu (Auto-retry) tối đa 2 lần kèm thông báo lỗi cấu trúc cho LLM. |
| **2. Timeout hoặc Dịch vụ AI quá tải (Timeout / 503 / 429)** | AI xử lý quá lâu hoặc API nhà cung cấp bị nghẽn mạng. | **Hard Timeout & Fallback (Quyết định C2):** Ngắt kết nối ở giây 55, trả về mã lỗi cấu trúc, kích hoạt luồng giao diện cho phép người dùng Thử lại hoặc Tạo kế hoạch thủ công. |
| **3. Quá tải thời gian học (Overload Scheduling)** | AI phân bổ khối lượng task vượt quá quỹ thời gian rảnh của người dùng. | **Backend Hard Ceiling Enforcement:** Mã nguồn backend kiểm tra tổng thời lượng task so với quỹ thời gian rảnh của chế độ Mode A/Mode B trước khi cho phép Apply; cấm vượt quá giới hạn đã định. |
| **4. Ảo giác nội dung (Hallucination)** | AI gợi ý kiến thức hoặc công nghệ sai lệch, không có thật. | **Human-in-the-loop Approval:** Lộ trình AI sinh ra chỉ là Proposal; người dùng có toàn quyền chỉnh sửa/xóa trước khi bấm Apply để trở thành Official Schedule. |
| **5. Cạn kiệt chi phí do lạm dụng gọi AI (Cost / Quota Exhaustion)** | Người dùng liên tục gửi request làm cạn kiệt API credits. | **Service-level Quota Guard (Quyết định M3):** Middleware backend chặn yêu cầu nếu tài khoản Free vượt quá định mức tháng trước khi gửi prompt ra dịch vụ ngoài. |

---

## 9. Requirement Baseline Traceability Matrix (Ma trận truy vết nền tảng)

| Vấn đề thực tế (Problem) | Mục tiêu / KPI | Năng lực hệ thống (Capability) | Ràng buộc nghiệp vụ / NFR chi phối |
|---|---|---|---|
| **P1: Khó phân rã mục tiêu lớn** | KPI 1 (Tạo kế hoạch $\le 5$m) | Onboarding $\rightarrow$ Clarify $\rightarrow$ Milestones $\rightarrow$ Tasks Proposal $\rightarrow$ Apply | BR-Approval, Mode A/B Availability, NFR 1 ($\le 60$s) |
| **P2: Phân mảnh công cụ** | KPI 2 (Hiệu quả buổi học $\ge 80\%$), SUS $\ge 80$ | Study Tool Suite (Pomodoro, Checklist, Scratchpad, Key Takeaway) | NFR 2 (UI $\le 500$ms), Session Interruption Rule |
| **P3: Đứt gãy lịch khi trễ hạn** | KPI 3 (Bám sát lộ trình $\ge 70\%$) | Deterministic Overdue Detection + Email Notification, Single-Roadmap AI Reschedule, Pause Roadmap (Domino Shift), Controlled 2-Way Calendar Sync & WebCal Feed | BR-Deterministic Overdue, Quyết định 2A (2-Way Sync & WebCal Token), Quyết định 4A (Domino Shift) |
| **Quản trị chi phí & Vận hành** | Giữ chi phí API $\le$ Ngân sách đồ án | Quota Middleware (Free vs Premium) & Online Payment Gateway (PayOS/VNPay) | Quyết định M3 (Service-level Quota & Payment Webhook), NFR 3 (Bảo mật API secret) |
