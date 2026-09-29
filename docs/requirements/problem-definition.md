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

## 1. Problem Statement (Phát biểu bài toán)

### 1.1. Bối cảnh (Problem Context)
Trong kỷ nguyên số, nhu cầu tự học và tái đào tạo kỹ năng (self-directed learning & reskilling) như lập trình, ngôn ngữ, công nghệ mới... ngày càng trở nên cấp thiết. Tuy nhiên, người học theo phương thức tự do thường gặp khó khăn lớn do thiếu người hướng dẫn trực tiếp, thiếu cấu trúc lộ trình chuẩn mực và thời gian biểu phân tán không cố định.

### 1.2. Vấn đề cốt lõi (Core Problem)
Người tự học gặp phải chuỗi đứt gãy liên hoàn từ giai đoạn lập kế hoạch đến thực thi hàng ngày:
1. **Rào cản phân rã mục tiêu (Decomposition Barrier):** Khó khăn trong việc chuyển đổi một mục tiêu lớn và trừu tượng (ví dụ: *"Học Backend trong 3 tháng"*) thành các mốc kiến thức (milestones) và các đầu việc (tasks) khả thi theo từng ngày.
2. **Quá tải và phân mảnh công cụ (Tool Fragmentation & Cognitive Overhead):** Người học phải sử dụng rời rạc nhiều công cụ không liên kết: dùng Chatbot AI để xin lộ trình văn bản, dùng Google Calendar để tạo mốc giờ, dùng Notion để tạo template ghi chép, và dùng app Pomodoro riêng để bấm giờ. Việc chuyển đổi qua lại này làm tiêu hao năng lượng ý chí (planning fatigue) trước khi thực sự bắt đầu học.
3. **Đứt gãy kỷ luật khi có biến cố (Rigid Planning Failure):** Lộ trình được lên thủ công hoặc do AI sinh ra ở dạng tĩnh. Khi người học gặp biến cố bất khả kháng (ốm, bận việc đột xuất 1–2 ngày), toàn bộ kế hoạch bị dồn ứ. Việc tự dịch chuyển từng mốc lịch rất tốn công sức, dẫn đến tâm lý nản chí và bỏ cuộc giữa chừng.

---

## 2. Target Users & Stakeholders (Người dùng & Các bên liên quan)

### 2.1. Chân dung người dùng mục tiêu (Primary User Persona)
- **Đối tượng trung tâm:** Người tự học / Cá nhân phát triển kỹ năng (Self-Directed Learners).
- **Đặc điểm hành vi:**
  - Thời gian học linh hoạt, tranh thủ ngoài giờ làm việc hoặc giờ học chính khóa.
  - Trình độ công nghệ ở mức phổ thông đến khá, quen thuộc với các ứng dụng web hiện đại.
  - Có động lực học tập nhưng dễ bị chi phối bởi áp lực thời gian và thiếu tính kỷ luật nếu không có kế hoạch rõ ràng.

### 2.2. Vai trò trong hệ thống (System Actors)
1. **Learner (Người học / End-User):**
   - Đăng ký, đăng nhập tài khoản trước khi tạo kế hoạch để định danh và quản trị hạn ngạch.
   - Thiết lập cấu hình thời gian rảnh theo mô hình lai (Hybrid Availability).
   - Tương tác với AI để làm rõ mục tiêu, xem xét đề xuất lịch trình (Schedule Proposal), chỉnh sửa và bấm "Apply" để lưu thành Lịch chính thức (Official Schedule).
   - Sử dụng bộ công cụ hỗ trợ (Study Tool Suite: Timer Pomodoro/Stopwatch, Scratchpad, Key Takeaways, Task Checklist) trong phiên học.
   - Nhận báo cáo thống kê định lượng và phản hồi/đánh giá định tính từ AI Review.
   - Đăng ký nhận lịch qua URL WebCal bí mật (Secure Token Feed) hoặc xuất file `.ics`.
2. **Administrator (Quản trị viên hệ thống - Service Role):**
   - Quản trị hạn ngạch gọi dịch vụ AI (Token usage & Request Quota) theo phân tầng tài khoản (Free vs. Premium) tại tầng middleware dịch vụ.
   - Giám sát trạng thái hoạt động và các chỉ số sức khỏe của hệ thống qua cấu hình nền tảng.

### 2.3. Các bên liên quan gián tiếp (External Stakeholders)
- **Giảng viên hướng dẫn & Hội đồng chấm tốt nghiệp:** Đánh giá chất lượng kỹ thuật, tính làm chủ sản phẩm, và mức độ hoàn thiện đề tài theo bảng Rubric 100 điểm của Khoa CNTT.

---

## 3. Current Situation & Benchmarking (Hiện trạng & Đối sánh giải pháp)

Đáp ứng tiêu chí **TC1 (Mức 5: So sánh $\ge 3$ giải pháp hiện có, nêu rõ khoảng trống với phân tích thực tế khách quan)**:

| Tiêu chí so sánh | Google Calendar | Notion | Chatbots độc lập (ChatGPT/Claude) | **FocusFlow (Hệ thống đề xuất)** |
|---|---|---|---|---|
| **Bản chất công cụ** | Quản lý lịch thời gian tĩnh (Time-blocking) | Không gian ghi chú & quản lý cơ sở dữ liệu tự do | Mô hình ngôn ngữ lớn dạng hội thoại văn bản | Nền tảng chuyên biệt quản lý lộ trình học tập thích ứng |
| **Phân rã mục tiêu tự động** | ❌ Không hỗ trợ | ❌ Không hỗ trợ (phải tự nhập) | ⚠️ Có sinh văn bản gợi ý nhưng không tạo thành đối tượng task có vòng đời | ✅ **Hỏi-đáp làm rõ ngữ cảnh $\rightarrow$ Phân rã 2 cấp (Milestones & Tasks Proposal)** |
| **Tính liên kết ngữ cảnh học tập** | ⚠️ Có mốc giờ và checklist (Google Tasks) nhưng thiếu liên kết mục tiêu học tập, timer, note | ⚠️ Có thể liên kết note và nhúng widget timer độc lập, nhưng phải tự dựng template thủ công | ❌ Văn bản trôi theo lịch sử chat, không lưu thành data entities quản trị được | ✅ **Liên kết khép kín 2 chiều: Lộ trình $\leftrightarrow$ Task $\leftrightarrow$ Timer $\leftrightarrow$ Note $\leftrightarrow$ Review** |
| **Cơ chế thích ứng khi trễ hạn** | ❌ Thụ động, người dùng phải tự kéo thả/sửa từng event thủ công | ❌ Người dùng phải tự lọc và sửa đổi thủ công trong database | ❌ Không có ngữ cảnh tiến độ thực tế để tự tính toán bù lịch | ✅ **Thuật toán tất định phát hiện task tồn đọng $\rightarrow$ Tự động đề xuất lịch bù thông minh** |
| **Không gian thực thi phiên học** | ❌ Không có | ⚠️ Phụ thuộc vào widget ngoại lai, không ghi nhận dữ liệu thời gian thực vào task | ❌ Không có | ✅ **Study Tool Suite tích hợp (Pomodoro/Stopwatch, Scratchpad, Key Takeaways)** |
| **Tổng kết & Đánh giá định kỳ** | ❌ Không có | ⚠️ Phải tự viết công thức Rollup/Formula phức tạp | ❌ Không tự động tổng kết theo chu kỳ thời gian thực | ✅ **Thống kê định lượng toán học chính xác kết hợp nhận xét định tính từ AI Review** |

### Khoảng trống chiến lược (The Strategic Gap)
Thị trường thiếu một giải pháp khép kín toàn bộ chu trình học tập: **Lập kế hoạch thông minh $\rightarrow$ Thực thi tập trung trong phiên $\rightarrow$ Tự động thích ứng khi có sự cố $\rightarrow$ Đánh giá hiệu suất định kỳ**. FocusFlow ra đời để lấp đầy khoảng trống này mà không bắt người học phải làm "thư ký dữ liệu" thủ công.

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
│ - Quét Overdue bằng thuật toán tất định ──> Đưa vào ưu tiên / AI sắp xếp lại  │
│ - Tạm dừng lộ trình (Pause Roadmap) ──> Domino Shift tự động đẩy lùi lịch     │
│ - Xuất lịch ngoại vi: Tải .ics + Cung cấp Secure Token WebCal Feed            │
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
- **Phát hiện quá hạn cốt lõi (Deterministic Overdue - Quyết định M1):** Sử dụng câu lệnh logic backend thuần túy: `task.status != COMPLETED AND task.scheduled_date < TODAY`. Tự động đưa các task này vào danh sách ưu tiên giải quyết. Hoàn toàn không phụ thuộc vào LLM.
- **Tùy chọn AI sắp xếp lại (Optional AI Reprioritization):** Chỉ khi người dùng chủ động yêu cầu, AI mới được cấp danh sách task tồn đọng để gợi ý thứ tự ưu tiên mới.
- **Tạm dừng lộ trình (Pause Roadmap - Quyết định 4A):** Cho phép người học tạm dừng lộ trình từ ngày A đến ngày B (ví dụ: bận thi cử). Hệ thống áp dụng **thuật toán tịnh tiến dây chuyền (Domino Shift)**: toàn bộ các ngày học từ mốc bắt đầu tạm dừng sẽ tự động lùi về sau đúng số ngày rảnh tương ứng, giữ nguyên thứ tự task. Khoảng thời gian tạm dừng không bị tính cảnh báo quá hạn.

### 5.5. Tích hợp Lịch ngoại vi an toàn (Calendar Integration - Quyết định 2A)
- Cung cấp tính năng tải về file tĩnh `.ics`.
- Cung cấp tính năng đăng ký theo dõi lịch (1-Way WebCal Subscription Feed) cho Google Calendar và Apple Calendar qua đường dẫn chứa mã bảo mật ngẫu nhiên: `https://focusflow.app/api/v1/feeds/{user_secure_token}.ics`.
- Người dùng có quyền bấm nút "Tạo lại liên kết mới (Reset Token)" trên giao diện để thu hồi URL cũ khi cần bảo mật.
- WebCal Feed tuyệt đối chỉ xuất các task thuộc Official Schedule đã được Apply.

### 5.6. Báo cáo định lượng và AI Review chu kỳ
- Thống kê định lượng: Tổng thời gian tập trung thực tế, tỷ lệ hoàn thành task theo tuần/tháng bằng các hàm toán học chính xác.
- Báo cáo định tính: AI Review đọc số liệu thống kê thực tế và các Key Takeaways để đưa ra nhận xét, cảnh báo điểm nghẽn và lời khuyên điều chỉnh lộ trình cho chu kỳ tiếp theo.

---

## 6. Scope & Boundaries (Phạm vi dự án)

Nhằm bảo đảm tính khả thi, hoàn thành 100% khối lượng cam kết (TC2.2) và tránh các quy tắc chặn điểm (G1, G9):

### 6.1. Trong phạm vi (In-Scope — Core MVP)
- **Module Quản lý tài khoản & Hồ sơ:** Đăng ký, đăng nhập, bảo vệ phiên, cấu hình thời gian rảnh lai (Mode A / Mode B).
- **Module Lập kế hoạch AI:** Luồng tương tác hỏi-đáp, sinh Milestone, sinh Schedule Proposal, giao diện review/edit, nút Apply kèm Backend Validation Gate.
- **Module Không gian phiên học:** Bảng task, Study Tool Suite (Pomodoro timer/Stopwatch), Scratchpad note, Key Takeaways, xử lý phiên bị gián đoạn.
- **Module Thích ứng & Lịch trình:** Thuật toán phát hiện quá hạn tất định, tính năng Tạm dừng lộ trình (Domino Shift), xuất file `.ics` và cung cấp URL WebCal Feed bảo mật.
- **Module Báo cáo & AI Review:** Thống kê định lượng chính xác và trợ lý AI Review định kỳ.
- **Module Quản trị Hạn ngạch (Quota Service & Mock Sandbox - Quyết định M3):** Middleware kiểm soát số lượt gọi AI theo phân tầng Free/Premium; giao diện người dùng có trang hiển thị hạn ngạch và nút bấm mô phỏng nâng cấp (Mock Upgrade Sandbox).

### 6.2. Ngoài phạm vi (Out-of-Scope — Tuyệt đối không làm trong đồ án này)
- **Đồng bộ 2 chiều phức tạp với Google Calendar:** Không làm cơ chế giải quyết xung đột lịch 2 chiều từ Google Calendar ngược lại FocusFlow (đưa vào Future Work).
- **Cổng thanh toán thực tế (Production Payment Gateway):** Không kết nối cổng thanh toán thật (VNPay, Momo, Stripe) nhằm tránh rủi ro pháp lý và phụ thuộc hạ tầng bên ngoài.
- **Giao diện Dashboard Quản trị viên (Admin Portal):** Quản trị hạn ngạch được thực hiện tại tầng dịch vụ/cấu hình, không dựng trang web admin riêng biệt.
- **Ứng dụng Native Mobile (iOS/Android):** Không viết app native, chỉ tập trung hoàn thiện Web Application responsive đa thiết bị.
- **Tính năng mạng xã hội / Nhóm học tập:** Không làm tính năng kết bạn, chat, chia sẻ lộ trình giữa các người dùng.

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
| **P3: Đứt gãy lịch khi trễ hạn** | KPI 3 (Bám sát lộ trình $\ge 70\%$) | Deterministic Overdue Shift, Pause Roadmap (Domino Shift), WebCal Feed | BR-Deterministic Overdue, Quyết định 2A (WebCal Token), Quyết định 4A (Domino Shift) |
| **Quản trị chi phí & Vận hành** | Giữ chi phí API $\le$ Ngân sách đồ án | Quota Middleware (Free vs Premium) & Mock Sandbox | Quyết định M3 (Service-level Quota), NFR 3 (Bảo mật API secret) |
