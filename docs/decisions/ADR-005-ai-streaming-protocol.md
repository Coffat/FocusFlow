# ADR-005: Kiến trúc LLM Đa nhà cung cấp (`LLMProviderPort`), Giao thức SSE 2 Chặng Đồng nhất & Giữ chỗ Quota ACID 2 Pha

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật Kiến trúc v2.0)
* **Ngày quyết định:** 29/09/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** `ASR-02`, `ASR-03`, `ASR-06`, `FR-PLAN-001`, `FR-PLAN-002`, `FR-PLAN-003`, `FR-QUOTA-001`, `NFR-PERF-001`, `NFR-AI-001`, `BUSR-02`, `BUSR-10`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Trong FocusFlow, trí tuệ nhân tạo (LLM) tham gia vào các luồng nghiệp vụ trọng yếu: phân rã mục tiêu thành cột mốc (`UC-06`), lập lịch chi tiết (`UC-07`), thẩm định sư phạm (`Tier 3 Judge`), chia nhỏ task bị đình trệ (`UC-17`) và sinh báo cáo phản tư định kỳ (`UC-15`). Hệ thống phải giải quyết đồng thời 3 bài toán kiến trúc lớn:
1. **Độc lập Nhà cung cấp AI & Khả năng Bảo vệ Offline (`ASR-06`):** Nếu mã nguồn gọi cứng SDK của một nhà cung cấp duy nhất (ví dụ chỉ gắn chặt vào Google Gemini), hệ thống sẽ bị tê liệt khi nhà cung cấp đó đổi chính sách quota, gặp sự cố mạng hoặc khi nhóm cần chạy đánh giá đối chứng nhiều mô hình (Gemini, OpenAI, Claude, Local Ollama) và demo offline tại phòng bảo vệ khóa luận.
2. **Phản hồi Thời gian thực kết hợp Cổng Duyệt Con người 2 Cấp độ (`ASR-03`, `BUSR-02`):** Quá trình suy luận của LLM kéo dài 8–20 giây. Người học cần thấy token đầu tiên xuất hiện trong $\le 2.5\text{s}$ (TTFT P95) và phải được quyền kiểm duyệt/chỉnh sửa ở cả cấp độ vĩ mô (Milestones) lẫn vi mô (Schedule Proposal `DRAFT`) trước khi áp dụng.
3. **Toàn vẹn Hạn ngạch AI & Chống Trừ Kép khi Mất kết nối (`ASR-02`, `BUSR-10`):** Khi nhiều request đồng thời được gửi lên hoặc khi luồng SSE bị ngắt giữa chừng, hệ thống phải đảm bảo **0% race condition** vượt trần hạn ngạch và tự động hoàn trả lượt gọi nếu LLM gặp lỗi.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Gọi trực tiếp SDK của 1 nhà cung cấp + HTTP POST đồng bộ + Đếm Quota trên Redis
* *Ưu điểm:* Dễ cài đặt ban đầu.
* *Nhược điểm:* Bị khóa chặt vào một nhà cung cấp (Vendor Lock-in); gọi HTTP đồng bộ mất 15–30s gây đơ giao diện và dễ bị Gateway Timeout; quản lý quota rời rạc trên Redis dễ bị lệch trạng thái với CSDL PostgreSQL khi xảy ra sự cố.

### Phương án B: Gộp toàn bộ phân rã vào 1 luồng WebSocket duy nhất
* *Ưu điểm:* Kênh truyền 2 chiều.
* *Nhược điểm:* Vi phạm nguyên tắc **Human-in-the-Loop 2 cấp độ (`BUSR-02`)** khi sinh một mạch từ Goal ra hàng chục Tasks mà không dừng lại cho người học duyệt Milestones; WebSocket phức tạp hóa việc cân bằng tải và tự động kết nối lại so với SSE chuẩn HTTP.

### Phương án C: Kiến trúc LLM Đa nhà cung cấp (`LLMProviderPort`) + Giao thức SSE 2 Chặng Đồng nhất + Giữ chỗ Quota ACID 2 Pha trên PostgreSQL (Được chọn)
* Thiết kế cổng xuất Hexagonal **`LLMProviderPort`** theo mẫu Strategy/Factory kết hợp **`LiteLLM` / OpenAI-Compatible Async SDK** và **`MockLLMAdapter`**, cấu hình hoàn toàn qua biến môi trường `.env`.
* Áp dụng giao thức **Uniform 2-Stage SSE Protocol** (`POST` khởi tạo & giữ chỗ Quota trả về `202 Accepted` / `job_id` $\to$ `GET` `EventSource` SSE stream gắn với Angular 21 Signals qua `toSignal()`).
* Chuẩn hóa cơ chế **2-Phase ACID Quota Reservation** ngay trong PostgreSQL 16 trên 3 bảng `ai_quotas`, `ai_quota_reservations` và `ai_usage_logs` với khóa hàng `SELECT ... FOR UPDATE`.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C với 3 trụ cột kiến trúc chi tiết sau:**

### 3.1. Kiến trúc LLM Đa Nhà Cung Cấp (`LLMProviderPort` — Provider-Agnostic Architecture)
* Tại `shared_kernel/application/`, định nghĩa giao diện trừu tượng **`LLMProviderPort`** cung cấp 2 phương thức cốt lõi:
  1. `stream_structured_output(prompt, response_schema, ...) -> AsyncIterator[StreamChunk]`: Phục vụ luồng SSE 2 chặng có kiểm định Pydantic v2.
  2. `generate_structured_output(prompt, response_schema, ...) -> T`: Phục vụ các tác vụ chạy nền trên Taskiq Worker (như AI Review, Pedagogical Judge).
* Tại `shared_kernel/infrastructure/external_ai/`, triển khai **Strategy / Factory Pattern**:
  * **`LiteLLMAdapter` / `OpenAICompatibleAdapter`:** Cho phép kết nối thống nhất tới **Google Gemini, OpenAI (GPT-4o/mini), Anthropic Claude, Groq, hoặc Local Ollama / vLLM** mà không cần sửa bất kỳ dòng code nào ở tầng Application hay Domain.
  * **`MockLLMAdapter`:** Trả về luồng dữ liệu kịch bản chuẩn xác ngay lập tức phục vụ kiểm thử tự động (`pytest`), chạy CI/CD và chế độ **Bảo vệ Khóa luận Offline (Offline Defense Mode)**.
* Chuyển đổi nhà cung cấp hoàn toàn thông qua 4 biến môi trường trong `.env`:
  * `LLM_PROVIDER` (`gemini` | `openai` | `anthropic` | `ollama` | `mock`)
  * `LLM_MODEL` (ví dụ: `gemini/gemini-2.5-flash`, `gpt-4o-mini`, `ollama/qwen2.5:7b`)
  * `LLM_API_KEY`
  * `LLM_BASE_URL` (tùy chọn cho Ollama hoặc OpenAI-compatible proxy)

### 3.2. Giao thức SSE Hai Chặng Đồng nhất (Uniform 2-Stage SSE Protocol) & Cổng Duyệt 2 Cấp độ
Mỗi cấp độ trong quy trình lập kế hoạch Human-in-the-Loop (`UC-06` Sinh & Duyệt Milestones $\to$ `UC-07` Sinh & Duyệt Schedule Proposal) đều tuân theo mẫu **2 Chặng Đồng nhất**:
1. **Chặng 1 — Khởi tạo Lệnh & Giữ chỗ Hạn ngạch (`POST` Command):**
   * Client gửi request `POST` (kèm `Idempotency-Key`).
   * Backend thực hiện kiểm tra và tạm giữ 1 lượt gọi AI trong giao dịch ACID (xem Mục 3.3), khởi tạo phiên xử lý và trả về ngay mã **`202 Accepted`** kèm `{ "job_id": "..." }` trong $< 150\text{ms}$.
2. **Chặng 2 — Nhận Luồng Tiến trình Thời gian thực (`GET` SSE Stream):**
   * Frontend Angular 21+ mở kết nối `EventSource` tới endpoint `GET .../jobs/{job_id}/stream` (`withCredentials: true`).
   * Luồng sự kiện SSE (`stage`, `chunk`, `validation_retry`, `completed`, `failed`) được bọc trong RxJS `Observable` và chuyển đổi sang **Angular 21 Signal** qua **`toSignal()`**, giúp giao diện cập nhật mượt mà với $\text{TTFT} \le 2.5\text{s}$ (`ASR-03`).
   * Sau khi kết thúc Cấp độ 1 (Milestones), hệ thống dừng lại để người học xem xét, chỉnh sửa và bấm **"Approve Milestones"** trước khi kích hoạt Cấp độ 2 (Tasks & Schedule Proposal `DRAFT`).

### 3.3. Cơ chế Giữ chỗ Hạn ngạch ACID 2 Pha trên PostgreSQL (2-Phase ACID Quota Reservation)
Thay vì đếm quota tạm bợ trên Redis dễ mất đồng bộ, FocusFlow chuẩn hóa quản trị hạn ngạch bằng giao dịch ACID trên PostgreSQL 16 với 3 bảng thuộc Bounded Context `account`:
1. **Pha 1 — `RESERVE` (Trước khi gọi LLM):**
   * Thực thi `SELECT ... FROM ai_quotas WHERE user_id = :uid FOR UPDATE` để khóa hàng hạn ngạch của người học, chặn đứng 100% race condition khi người dùng bấm đúp hoặc mở nhiều tab.
   * Kiểm tra điều kiện: `used_calls + reserved_calls < max_calls`. Nếu hợp lệ, tăng `reserved_calls = reserved_calls + 1` và tạo bản ghi mới trong bảng **`ai_quota_reservations`** với `status = 'RESERVED'` và `expires_at = NOW() + INTERVAL '5 minutes'`.
2. **Pha 2a — `COMMIT` (Khi LLM sinh kết quả và vượt qua cổng kiểm duyệt thành công):**
   * Trong cùng giao dịch lưu kết quả: giảm `reserved_calls = reserved_calls - 1`, tăng `used_calls = used_calls + 1`, cộng dồn `tokens_consumed`, cập nhật bản ghi `ai_quota_reservations.status = 'COMMITTED'`, và ghi nhật ký chi tiết vào bảng **`ai_usage_logs`** (model, prompt/completion tokens, latency, status).
3. **Pha 2b — `RELEASE` / `EXPIRE` (Khi LLM lỗi, vi phạm cổng kiểm duyệt sau khi hết số lần retry, hoặc quá hạn 5 phút):**
   * Giảm `reserved_calls = reserved_calls - 1` (không tăng `used_calls`), chuyển trạng thái `ai_quota_reservations` sang `'RELEASED'` (hoặc `'EXPIRED'` thông qua `QuotaSweeperTask` của Taskiq chạy mỗi 60s), đồng thời ghi nhận lỗi vào `ai_usage_logs`. Người học không bao giờ bị mất oan lượt gọi AI.

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Độc lập Nhà cung cấp Tuyệt đối (`ASR-06`):** Nhờ `LLMProviderPort`, dự án có thể chạy thực nghiệm so sánh nhiều mô hình cho khóa luận (Gemini vs GPT-4o-mini vs Ollama) và chuyển sang `MockLLMAdapter` chỉ bằng 1 dòng cấu hình `.env`.
* **Độ tin cậy Tài chính & Hạn ngạch (`ASR-02`):** Kết hợp `SELECT ... FOR UPDATE` trên `ai_quotas` và sổ cái `ai_quota_reservations` đảm bảo tính toàn vẹn toán học tuyệt đối (`used_calls + reserved_calls <= max_calls`).
* **Trải nghiệm Người dùng Tối ưu (`ASR-03`, `BUSR-02`):** Tách `POST` (Command) và `GET` (SSE Stream) giúp trình duyệt tự động kết nối lại (`EventSource`) nếu mạng chập chờn mà không bao giờ kích hoạt trừ quota lần hai.

---

## 5. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Đáp ứng trọn vẹn `ASR-02`, `ASR-03`, `ASR-06` và các quy tắc `BUSR-02`, `BUSR-10`; cung cấp đầy đủ dữ liệu telemetry trong `ai_usage_logs` cho cổng Admin Monitoring (`UC-19`).
* **Kiểm chứng Tự động:** Kiểm thử đồng thời (Concurrency Test) gửi 10 requests song song khi người dùng chỉ còn 1 lượt quota phải chứng minh đúng 1 request thành công và 9 requests nhận mã `429 Too Many Requests / Quota Exhausted`.
