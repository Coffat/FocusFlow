# ADR-010: Hồ sơ Năng lực Người học (Zimmerman SRL) qua Transactional Outbox / Taskiq & Ngắt mạch Chống lặp Quá hạn (`reschedule_count >= 3`)

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật Kiến trúc v2.0)
* **Ngày quyết định:** 16/10/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** `ASR-01`, `ASR-02`, `FR-ADAPT-001`, `FR-ADAPT-003`, `FR-PAUSE-001`, `FR-PAUSE-002`, `FR-PROFILE-001`, `UC-03`, `UC-10`, `UC-16`, `UC-17`, `BUSR-06`, `BUSR-07`, `BUSR-09`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Nền tảng lý thuyết cốt lõi của FocusFlow là mô hình **Học tập Tự điều chỉnh của Zimmerman (Self-Regulated Learning — SRL, 2002)** gồm 3 pha khép kín: *Forethought (Hoạch định)* $\to$ *Performance (Thực thi)* $\to$ *Self-Reflection (Phản tư & Thích ứng)*. Để chu trình SRL thực sự khép kín về mặt kỹ thuật trong kiến trúc Context-First Modular Monolith (`ADR-001`), hệ thống phải giải quyết hai vấn đề:
1. **Đồng bộ Dữ liệu Hành vi Học tập Liên Bounded Context mà Không Gây Nghẽn Giao dịch (`ASR-01`, `ASR-02`):**
   * Phiên học (`StudySession`) diễn ra tại Bounded Context **`execution`**, trong khi Hồ sơ năng lực người học (`LearnerProfile` — bảng `learner_profiles`) lại thuộc quyền sở hữu của Bounded Context **`account`** và được sử dụng bởi **`planning`** khi lập lịch AI.
   * Nếu tính toán lại toàn bộ chỉ số thống kê SRL ngay trong HTTP request kết thúc phiên học (`CompleteStudySessionUseCase`) hoặc gọi ORM ghi trực tiếp từ `execution` sang bảng `learner_profiles` của `account`, hệ thống sẽ làm chậm độ trễ API và phá vỡ ranh giới cô lập Bounded Context.
   * Ngược lại, nếu chỉ bắn sự kiện qua bộ nhớ tạm mà không có cơ chế bền vững (như cách gọi Celery rời rạc trước đây), dữ liệu học tập sẽ bị lệch nếu worker gặp sự cố.
2. **Ngăn chặn Hiện tượng "Tuyết lăn Trì hoãn" (Procrastination Snowball) & Ghi nhận Kiểm toán Lịch trình (`FR-ADAPT-003`, `BUSR-06`, `BUSR-07`):**
   * Khi người học bỏ lỡ nhiệm vụ, hệ thống hỗ trợ dời lịch. Tuy nhiên, nếu một nhiệm vụ bị trì hoãn và dời lịch tự động lặp đi lặp lại nhiều lần, lịch trình tương lai sẽ bị dồn ứ ảo và người học mất hoàn toàn động lực cam kết.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Hạng mục 1: Cơ chế Cập nhật Hồ sơ Năng lực Người học (`learner_profiles`)
* **Phương án A — Tính toán Đồng bộ Trực tiếp trong HTTP Request Kết thúc Phiên học:**
  * *Nhược điểm:* Tăng độ trễ API kết thúc phiên học và tạo sự phụ thuộc ghi trực tiếp từ Context `execution` sang Context `account`, vi phạm `ADR-001`.
* **Phương án B — Đẩy Task Trực tiếp sang Celery không có Outbox (Thiết kế cũ v1.0):**
  * *Nhược điểm:* Celery bất tương thích với `SQLAlchemy 2.0 AsyncSession` (`ADR-004`); dễ xảy ra lỗi Dual-Write (commit DB thành công nhưng gửi message sang Redis thất bại làm mất sự kiện cập nhật hồ sơ).
* **Phương án C — Phát `StudySessionCompletedEvent` qua Transactional Outbox (`outbox_events`) $\to$ Taskiq Worker Cập nhật Bất đồng bộ `learner_profiles` (Được chọn):**
  * Đảm bảo cô lập tuyệt đối giữa `execution` và `account`, đồng thời cam kết **0% mất sự kiện (`ASR-02`)** nhờ mẫu Transactional Outbox + Idempotent Consumer (`processed_events`) trên nền **Taskiq + Redis Streams**.

### Hạng mục 2: Cơ chế Kiểm soát Quá hạn & Dịch lịch Thích ứng
* **Phương án A — Tự động Dời lịch Vô hạn không Giới hạn Số lần:**
  * *Nhược điểm:* Gây hiệu ứng tuyết lăn trì hoãn, làm mất ý nghĩa của kế hoạch học tập.
* **Phương án B — Ngắt mạch Chống lặp Quá hạn (`reschedule_count >= 3`) Thực thi bởi Taskiq Scheduler kết hợp `DominoShiftEngine` & Bảng Kiểm toán `schedule_change_logs` (Được chọn):**
  * Khóa tự động dời lịch khi chạm ngưỡng `reschedule_count >= 3` để yêu cầu người học can thiệp chủ động (`UC-17`), đồng thời phân lập rạch ròi với thao tác tạm dừng lộ trình toàn cục (`DominoShiftEngine` - `UC-16`) và lưu vết đầy đủ vào bảng `schedule_change_logs`.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C cho cả hai hạng mục với thiết kế chi tiết v2.0 như sau:**

### 3.1. Luồng Cập nhật Hồ sơ Năng lực SRL qua Transactional Outbox $\to$ Taskiq Worker
1. **Phát Sự kiện Nguyên tử tại Context `execution`:**
   * Khi người học hoàn thành phiên học (`UC-10`) hoặc khi `AbandonedSessionSweeperTask` chốt phiên `PARTIAL_COMPLETED` (`OS-01`), Aggregate Root `StudySession` phát ra sự kiện miền **`StudySessionCompletedEvent`**.
   * `SqlAlchemyUnitOfWork` ghi nhận trạng thái phiên học vào bảng `study_sessions` và ghi `StudySessionCompletedEvent` vào bảng **`outbox_events`** trong cùng một giao dịch PostgreSQL ACID.
2. **Chuyển tiếp & Xử lý Lũy đẳng trên Taskiq Worker tại Context `account`:**
   * `OutboxRelayTask` đẩy sự kiện qua **Redis Streams (`RedisStreamBroker`)**.
   * Taskiq Worker của Bounded Context `account` (`UpdateLearnerProfileOnSessionCompletedHandler`) nhận sự kiện, kiểm tra `event_id` trong bảng **`processed_events`** để chống xử lý trùng lặp, truy vấn dữ liệu thống kê qua `StudyExecutionQueryPort` (`execution/public_api.py`) và cập nhật bảng **`learner_profiles`**:
     * **Thời lượng Tập trung Tối ưu ($D_{opt}$ — `optimal_focus_duration_mins`):** Tính trung vị (Median) thời lượng thực học hiệu quả khi đủ ngưỡng $\ge 5$ phiên (lọc bỏ nhiễu $< 5$ phút hoặc $> 180$ phút, giới hạn trong `[15, 120]` phút).
     * **Hệ số Chệch Ước lượng Thời gian ($\beta_{bias}$ — `estimation_bias_factor`):** Tỷ số giữa thời gian thực tế và thời gian dự kiến khi đủ $\ge 8$ tasks hoàn thành, được kẹp an toàn trong đoạn $[0.50, 2.00]$.
     * **Khung Giờ Năng suất Đỉnh (`peak_productivity_slots`) & Tỷ lệ Hoàn thành Hàng tuần (`weekly_completion_rate`):** Tổng hợp từ chuỗi phiên học trong 14 ngày gần nhất.
   * **Cơ chế Cold Start & Quyền Tự chủ (`UC-03`):** Khi chưa đủ ngưỡng dữ liệu (`is_cold_start = TRUE`), hệ thống giữ giá trị mặc định chuẩn (**$D_{opt} = 25\text{ phút}$** — `optimal_focus_duration_mins = 25`, $\beta_{bias} = 1.00$ — `estimation_bias_factor = 1.00`, `peak_productivity_slots = ["MORNING", "EVENING"]`). Người học có toàn quyền xem và bấm **Reset Learner Profile** về trạng thái gốc bất cứ lúc nào.

### 3.2. Cơ chế Cảnh báo Email Quá hạn, Tái lập lịch AI Đơn Lộ trình & Ngắt mạch Chống lặp (`reschedule_count >= 3`)
1. **Quét Nhiệm vụ Quá hạn lúc `00:05 UTC+7` & Cảnh báo Email (Không tự động sửa ngầm `scheduled_date`):**
   * `TaskiqScheduler` (`replicas: 1`) kích hoạt `OverdueAntiLoopSweeperTask` (`Overdue Scanner` tại Bounded Context `evaluation` phối hợp với `execution`) lúc **`00:05 UTC+7`** hàng ngày với khóa hàng **`SELECT ... FOR UPDATE SKIP LOCKED`** để phát hiện các nhiệm vụ bị quá hạn (`scheduled_date < CURRENT_DATE` và `status != 'COMPLETED'`).
   * Khi phát hiện task quá hạn, tác vụ nền **tuyệt đối KHÔNG tự ý sửa ngầm `scheduled_date` (does NOT silently mutate `scheduled_date`)**. Thay vào đó, hệ thống gửi **Email Notification** tới địa chỉ email đã đăng ký của người học (qua `EmailNotificationPort` / SMTP Adapter) và hiển thị các task quá hạn trong mục **`Needs Attention`** kèm nút **"AI Reschedule (Dời lịch hợp lý)"** khi người học đăng nhập vào ứng dụng Web.
2. **Tái lập lịch AI Đơn Lộ trình Bỏ qua Cổng 3 Tầng (Single-Roadmap AI Reschedule without 3-Tier Gate):**
   * Khi người học chủ động bấm nút **"AI Reschedule (Dời lịch hợp lý)"** trên một lộ trình có task quá hạn, AI quét danh sách các task chưa hoàn thành của **riêng Lộ trình đó (that specific Roadmap)** cùng lịch trình tương lai của người học (trừ đi các khung giờ đã bị chiếm dụng bởi các lộ trình khác hoặc lịch ngoại vi) để sắp xếp lại **chỉ các task của Lộ trình đó** (tuyệt đối không chạm vào các lộ trình hay công việc khác của người học).
   * Thao tác tái lập lịch này **bỏ qua Cổng Kiểm duyệt 3 Tầng (bypasses the 3-Tier Hybrid Validation Gate — bỏ qua Tier 3 Pedagogical Judge**, chỉ kiểm tra định dạng JSON Schema và ràng buộc dung lượng/tránh xung đột cơ bản cho lộ trình đó), đồng thời tăng biến đếm **`reschedule_count`** của các task được dời lịch thêm 1.
3. **Ngưỡng Ngắt mạch Chống lặp `reschedule_count >= 3` (`BUSR-06`, `UC-17`):**
   * Dựa trên Lý thuyết Động lực Thời gian (Temporal Motivation Theory — Steel, 2007), nếu một nhiệm vụ bị dời lịch quá hạn chạm ngưỡng **`reschedule_count >= 3`**, hệ thống lập tức **ngắt mạch tái lập lịch**, đánh dấu trạng thái cần can thiệp (**`STALLED`**) và phát sự kiện `TaskStalledThresholdReachedEvent`.
   * Trên giao diện Angular 21+ (`tasks` feature slice), hệ thống hiển thị **Hộp thoại Can thiệp Thích ứng (SRL Intervention Dialog)** yêu cầu người học chọn 1 trong 3 giải pháp chủ động:
     1. **Cam kết Ngày Cố định Mới (Re-commit):** Chọn lại khung giờ cụ thể và đặt lại cam kết.
     2. **Nhờ AI Chia nhỏ Nhiệm vụ (AI Micro-Stepping):** Gọi `LLMProviderPort` tách nhiệm vụ đang bị quá tải thành 2–3 nhiệm vụ nhỏ dễ hoàn thành hơn ($\le 30\text{ phút}$).
     3. **Đưa về Backlog / Hủy bỏ (Move to Backlog / Cancel):** Giải phóng áp lực cho lịch học hiện tại.
4. **Phân lập Tuyệt đối với `DominoShiftEngine` (`pause_records`) & Kiểm toán trong `schedule_change_logs` (`BUSR-07`, `UC-16`):**
   * Khi người học chủ động **Tạm dừng và Tiếp tục Lộ trình (`Pause / Resume Roadmap` - `UC-16`, lưu tại bảng `pause_records` thuộc Context `evaluation`)**, Pure Domain Service **`DominoShiftEngine`** thực hiện tịnh tiến toàn bộ các nhiệm vụ chưa hoàn thành theo số ngày tạm dừng `shifted_days` mà **KHÔNG làm tăng `reschedule_count`** của từng task (vì đây là quyết định điều chỉnh kế hoạch chủ động toàn cục, không phải hành vi trì hoãn cá nhân).
   * Mọi thao tác dịch lịch (cả Domino Shift lẫn AI Reschedule quá hạn) đều bắt buộc ghi nhận bản ghi kiểm toán bất biến vào bảng **`schedule_change_logs`** (lưu rõ loại thay đổi, số ngày dịch chuyển, lý do và mốc thời gian).

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Khép kín Vòng lặp Lý thuyết Zimmerman SRL một cách Bền vững (`ASR-02`):** Kết hợp Transactional Outbox và Taskiq Worker đảm bảo mọi nỗ lực trong pha *Performance* (`execution`) đều được phản ánh chính xác vào hồ sơ năng lực ở pha *Self-Reflection* (`account`/`evaluation`) để tối ưu hóa cho lần *Forethought* (`planning`) tiếp theo mà không làm chậm HTTP API.
* **Giá trị Khoa học & Thực tiễn Cao:** Phân biệt rạch ròi giữa trì hoãn cá nhân (`reschedule_count >= 3`) và tạm dừng kế hoạch chủ động (`DominoShiftEngine`), đồng thời lưu vết đầy đủ trong `schedule_change_logs`.
* **Đánh đổi:** Hồ sơ năng lực người học được cập nhật theo mô hình **Nhất quán Cuối cùng (Eventual Consistency)** với độ trễ vài giây sau khi kết thúc phiên học qua Taskiq Worker — hoàn toàn phù hợp với bản chất của chỉ số thống kê tích lũy.

---

## 5. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Hoàn thiện kiến trúc thích ứng thông minh của FocusFlow v2.0, đồng bộ 100% giữa `ADR-001` (Outbox), `ADR-004` (Taskiq) và `ADR-007` (24 bảng PostgreSQL, bao gồm `learner_profiles` và `schedule_change_logs`).
* **Kiểm chứng Tự động:**
  * Unit test kiểm chứng `DominoShiftEngine` dịch chuyển đúng số ngày bảo lưu mà giữ nguyên `reschedule_count`.
  * Integration test kiểm chứng khi hoàn thành phiên học, sự kiện trong `outbox_events` được Taskiq xử lý lũy đẳng qua `processed_events` và cập nhật chính xác bảng `learner_profiles`.
