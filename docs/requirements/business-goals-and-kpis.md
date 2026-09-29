# FocusFlow — Business Goals & Quantitative KPIs Specification

> **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
> **Chuyên ngành:** Công nghệ Phần mềm — Khoa Công nghệ Thông tin  
> **Cấp độ tài liệu:** Đặc tả Mục tiêu Nghiệp vụ, Chỉ số Đo lường & Giao thức Nghiệm thu Định lượng (Business Goals, Quantitative KPIs & Verification Protocol)  
> **Mã tài liệu:** `DOC-REQ-GOALS-01`  
> **Tài liệu liên kết:** 
> - [**`problem-definition.md`**](problem-definition.md) *(Định nghĩa bài toán & Cơ sở yêu cầu)*
> - [**`user-survey-and-benchmarking.md`**](user-survey-and-benchmarking.md) *(Nghiên cứu đối sánh, dữ liệu thực chứng & Khảo sát)*
> - [**`../srs/srs-v1.0.md`**](../srs/srs-v1.0.md) *(Đặc tả Yêu cầu Phần mềm v1.0 — Mục 4, Mục 9 EVAL-01 đến EVAL-05)*  
> **Căn cứ đánh giá học thuật:** Khung Rubric Chấm Đồ án Tốt nghiệp CNTT:
> - **Tiêu chí TC1 (Mức 5):** "Xác định rõ $\ge 5$ mục tiêu/KPI cụ thể định lượng ngay từ đầu; Phân tích thực tế khách quan."
> - **Tiêu chí TC2.1 (Mức 5):** "Đặc tả các ràng buộc định lượng, đo lường được bằng công cụ kỹ thuật."
> - **Tiêu chí TC2.7 (Mức 5):** "Thực hiện UAT nghiêm túc trên người dùng thật; Đạt các chỉ số đo lường trải nghiệm (SUS $\ge 80$, Task Completion $\ge 90\%$).'

---

## MỤC LỤC

1. [Tổng quan & Nguyên tắc Xác lập Mục tiêu](#1-tổng-quan--nguyên-tắc-xác-lập-mục-tiêu)
   - 1.1 [Bối cảnh kỹ thuật](#11-bối-cảnh-kỹ-thuật)
   - 1.2 [Nguyên tắc SMART & Độc lập phương pháp luận](#12-nguyên-tắc-smart--độc-lập-phương-pháp-luận)
2. [Hệ thống 5 Mục tiêu Nghiệp vụ Cốt lõi (Business Goals)](#2-hệ-thống-5-mục-tiêu-nghiệp-vụ-cốt-lõi-business-goals)
3. [Đặc tả Chi tiết 5 Chỉ số KPI Định lượng (Detailed KPI Specifications)](#3-đặc-tả-chi-tiết-5-chỉ-số-kpi-định-lượng-detailed-kpi-specifications)
   - 3.1 [KPI 1 — Thời gian khởi tạo lộ trình (Plan Creation Time)](#31-kpi-1--thời-gian-khởi-tạo-lộ-trình-plan-creation-time)
   - 3.2 [KPI 2 — Hiệu quả thực thi buổi học (Session Task Completion Rate)](#32-kpi-2--hiệu-quả-thực-thi-buổi-học-session-task-completion-rate)
   - 3.3 [KPI 3 — Tỷ lệ duy trì lộ trình (Plan Adherence Rate)](#33-kpi-3--tỷ-lệ-duy-trì-lộ-trình-plan-adherence-rate)
   - 3.4 [KPI 4 — Tỷ lệ hoàn thành tác vụ người dùng (Task Success Rate)](#34-kpi-4--tỷ-lệ-hoàn-thành-tác-vụ-người-dùng-task-success-rate)
   - 3.5 [KPI 5 — Điểm hài lòng trải nghiệm chuẩn hóa (System Usability Scale - SUS)](#35-kpi-5--điểm-hài-lòng-trải-nghiệm-chuẩn-hóa-system-usability-scale---sus)
4. [Giao thức Thực nghiệm Nghiệm thu Người dùng Thật (UAT Protocol)](#4-giao-thức-thực-nghiệm-nghiệm-thu-người-dùng-thật-uat-protocol)
   - 4.1 [Quy mô & Tiêu chuẩn chọn mẫu UAT](#41-quy-mô--tiêu-chuẩn-chọn-mẫu-uat)
   - 4.2 [Kịch bản 4 tác vụ cốt lõi đo lường Task Success Rate](#42-kịch-bản-4-tác-vụ-cốt-lõi-đo-lường-task-success-rate)
   - 4.3 [Công cụ & Môi trường đo lường tự động (Telemetry Logging)](#43-công-cụ--môi-trường-đo-lường-tự-động-telemetry-logging)
5. [Ma trận Truy vết & Đánh giá Rủi ro Mục tiêu](#5-ma-trận-truy-vết--đánh-giá-rủi-ro-mục-tiêu)
   - 5.1 [Ma trận ánh xạ từ Nỗi đau khảo sát $\rightarrow$ KPI $\rightarrow$ SRS](#51-ma-trận-ánh-xạ-từ-nỗi-đau-khảo-sát--kpi--srs)
   - 5.2 [Ma trận rủi ro không đạt chỉ tiêu & Biện pháp giảm thiểu](#52-ma-trận-rủi-ro-không-đạt-chỉ-tiêu--biện-pháp-giảm-thiểu)
6. [Góc Nhìn Cố Vấn Khóa Luận (Defense Guidance on KPIs)](#6-góc-nhìn-cố-vấn-khóa-luận-defense-guidance-on-kpis)

---

## 1. Tổng quan & Nguyên tắc Xác lập Mục tiêu

### 1.1 Bối cảnh kỹ thuật
Theo quy chuẩn kiểm định chất lượng đề tài tốt nghiệp ngành Công nghệ Phần mềm (Khoa CNTT), một hệ sinh thái phần mềm không thể chỉ được đánh giá dựa trên việc "mã nguồn có chạy được hay không". Sản phẩm bắt buộc phải có **chỉ tiêu định lượng khách quan (Quantitative Success Criteria)** được xác lập ngay từ pha Khám phá Yêu cầu (Requirements Engineering) để làm căn cứ nghiệm thu khoa học trước Hội đồng bảo vệ.

FocusFlow thiết lập hệ thống mục tiêu kép:
1. **Mục tiêu Nghiệp vụ (Business Goals - BG):** Định hướng định tính về giá trị giải pháp mang lại cho người tự học.
2. **Chỉ số Hiệu suất Cốt lõi (Key Performance Indicators - KPIs):** Hệ thống 5 chỉ số định lượng có công thức toán học giải tích tường minh, có công cụ đo kiểm độc lập và có ngưỡng chấp nhận (Benchmark Threshold) đạt chuẩn mức tối đa (Mức 5) của khung Rubric.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CHU TRÌNH QUẢN TRỊ MỤC TIÊU                           │
│                                                                             │
│   Nghiên cứu đối sánh & Thực chứng ──> Xác lập 5 Business Goals (BG-01..05) │
│                                            │                                │
│                                            ▼                                │
│   Đặc tả 5 Chỉ số KPI Định lượng (Công thức toán + Ngưỡng Benchmark)       │
│                                            │                                │
│                                            ▼                                │
│   Kiến trúc & Cài đặt hệ thống (Backend Telemetry + Logging)               │
│                                            │                                │
│                                            ▼                                │
│   Thực nghiệm UAT (N >= 10 người dùng thật) ──> Nghiệm thu Rubric TC1/TC2.7│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Nguyên tắc SMART & Độc lập phương pháp luận
Toàn bộ 5 chỉ số KPI trong tài liệu này đều tuân thủ nghiêm ngặt nguyên tắc **SMART**:
- **S (Specific):** Đo lường đích danh một hành vi hoặc kết quả kỹ thuật cụ thể (thời gian tạo lịch, tỷ lệ tick task, tỷ lệ duy trì lịch, tỷ lệ hoàn thành luồng, điểm SUS chuẩn).
- **M (Measurable):** Có công thức toán học giải tích xác định, trích xuất dữ liệu từ cơ sở dữ liệu (`Session Logs`, `Official Schedule`) hoặc phiếu khảo sát chuẩn hóa quốc tế.
- **A (Achievable):** Các ngưỡng được tính toán dựa trên kết quả nghiên cứu thứ cấp, thực nghiệm công thái học và nghiên cứu đối sánh (Benchmarking), có tính khả thi trong đợt thử nghiệm thực tế.
- **R (Relevant):** Ánh xạ trực tiếp tới việc giải quyết 3 rào cản cốt tử: Rào cản phân rã, Phân mảnh công cụ, và Đứt gãy kế hoạch khi có biến cố.
- **T (Time-bound):** Được đo lường trong khung thời gian đợt thử nghiệm UAT nghiệm thu đề tài.

> **NGUYÊN TẮC ĐỘC LẬP PHƯƠNG PHÁP LUẬN (METHODOLOGICAL SEPARATION):**  
> Cần phân biệt rạch ròi:
> - **NFR (Non-Functional Requirements):** Là thuộc tính chất lượng nội tại của phần mềm (ví dụ: API phản hồi $\le 200$ms, AI timeout 55s, Lighthouse $\ge 90$). Phần mềm tự thân phải đáp ứng trong môi trường kiểm thử kỹ thuật.
> - **KPI / Evaluation Metrics:** Là chỉ số đo lường hiệu quả tương tác giữa con người và phần mềm trong môi trường thực tế (ví dụ: Người dùng hoàn thành kế hoạch $\le 5$ phút, người dùng duy trì học $\ge 70\%$). Đây là căn cứ đánh giá kết quả đồ án học thuật.

---

## 2. Hệ thống 5 Mục tiêu Nghiệp vụ Cốt lõi (Business Goals)

Hệ thống FocusFlow được định hướng bởi 5 mục tiêu nghiệp vụ cấp cao:

- **BG-01: Tự động hóa phân rã lộ trình học tập thích ứng cá nhân hóa**  
  Giải phóng người học khỏi gánh nặng tìm kiếm và chuyển đổi một mục tiêu lớn, trừu tượng thành các mốc kiến thức (Milestones) và đầu việc (Tasks) chi tiết bám sát quỹ thời gian rảnh thực tế.

- **BG-02: Nâng cao sự tập trung và hiệu suất thực thi trong từng buổi học**  
  Tích hợp không gian học tập thống nhất (Study Workspace) khép kín, triệt tiêu chi phí chuyển đổi ngữ cảnh (Context Switching) qua nhiều ứng dụng rời rạc, hỗ trợ người học hoàn tất các mục tiêu bài học trong ngày.

- **BG-03: Bảo vệ tính liên tục của kế hoạch học tập trước các biến cố đời sống**  
  Cung cấp cơ chế thích ứng lịch thông minh (Deterministic Overdue Detection, Domino Shift khi Pause) giúp kế hoạch tự phục hồi khi người học bận đột xuất, ngăn chặn tâm lý nản chí và từ bỏ lộ trình giữa chừng.

- **BG-04: Đạt độ tin cậy và trải nghiệm tương tác trực quan chuẩn mực**  
  Xây dựng giao diện web responsive đạt chuẩn tiếp cận cao (Accessibility $\ge 90$), thời gian phản hồi tức thì ($\le 500$ms) và quy trình phê duyệt Human-in-the-loop minh bạch giúp người dùng hoàn toàn làm chủ hệ thống.

- **BG-05: Tối ưu hóa chi phí vận hành và kiểm soát rủi ro phụ thuộc AI**  
  Quản trị chặt chẽ việc gọi API mô hình ngôn ngữ lớn thông qua phân tầng Quota tại middleware, chống cạn kiệt ngân sách đồ án, bảo vệ dữ liệu cá nhân nhạy cảm và duy trì phương án dự phòng thủ công (Manual Fallback).

---

## 3. Đặc tả Chi tiết 5 Chỉ số KPI Định lượng (Detailed KPI Specifications)

Đáp ứng chuẩn **Rubric TC1 Mức 5** và liên kết chặt chẽ với các mã đánh giá `EVAL-01` đến `EVAL-05` trong [SRS v1.0](../srs/srs-v1.0.md#1150-1165):

### 3.1 KPI 1 — Thời gian khởi tạo lộ trình (Plan Creation Time)
*Mã truy vết SRS:* `EVAL-01` | *Mục tiêu liên kết:* `BG-01`, `BR-001`

- **Định nghĩa:** Tổng thời gian thực tế tính từ thời điểm người học bắt đầu gửi thông tin mục tiêu ban đầu trên giao diện cho đến khi bản Đề xuất Lịch trình (Schedule Proposal) được người dùng chỉnh sửa, bấm nút "Apply" và Backend Validation Gate lưu trữ thành công thành Lịch chính thức (Official Schedule).
- **Mục tiêu định lượng (Benchmark Threshold):** 
  $$\mathbf{T_{\text{plan}}} \le \mathbf{5\text{ phút (300 giây)}}$$
  *(Đối chứng thực tế: Kết quả khảo sát Mục 3.2 cho thấy người tự học mất trung bình **48.6 phút** khi làm thủ công qua nhiều ứng dụng. FocusFlow rút ngắn $\ge 89.7\%$ thời gian thiết lập).*
- **Công thức tính toán:**
  $$T_{\text{plan}} = t_{\text{apply\_success}} - t_{\text{goal\_submit}}$$
  Trong đó:
  - $t_{\text{goal\_submit}}$: Timestamp hệ thống ghi nhận sự kiện người dùng bấm gửi form mục tiêu ban đầu (`FR-GOAL-001`).
  - $t_{\text{apply\_success}}$: Timestamp hệ thống trả về HTTP 201 Created khi lưu trữ Official Schedule thành công sau khi vượt qua cổng kiểm tra (`FR-PLAN-003`).
- **Nguồn dữ liệu & Công cụ đo:**
  - Bản ghi kiểm toán hành vi (Audit Log / Telemetry): Trích xuất chênh lệch thời gian từ bảng `audit_events` với 2 sự kiện `GOAL_SUBMITTED` và `OFFICIAL_SCHEDULE_CREATED`.
  - Đo kiểm trong đợt thử nghiệm UAT với đồng hồ bấm giờ độc lập.
- **Điều kiện biên & Ngoại lệ:**
  - *Khoảng thời gian nghỉ (Idle Time):* Nếu người dùng tạm ngưng thao tác (không có tương tác chuột/phím) liên tục $> 5$ phút giữa các bước xem xét Proposal, phiên khởi tạo đó bị đánh dấu ngoại lệ và loại khỏi mẫu tính toán để tránh sai lệch do yếu tố ngoại cảnh.
  - *Lỗi nhà cung cấp AI:* Thời gian chờ do lỗi mạng LLM bên ngoài gây timeout được ghi log riêng, kích hoạt luồng retry.

---

### 3.2 KPI 2 — Hiệu quả thực thi buổi học (Session Task Completion Rate)
*Mã truy vết SRS:* `EVAL-02` | *Mục tiêu liên kết:* `BG-02`, `BR-002`

- **Định nghĩa:** Tỷ lệ phần trăm các đầu việc học tập (Tasks) được người học đánh dấu hoàn thành (`COMPLETED`) trong một phiên học tập trung so với tổng số lượng đầu việc đã được lên lịch thực hiện cho phiên đó trong Study Workspace.
- **Mục tiêu định lượng (Benchmark Threshold):** 
  $$\mathbf{CR_{\text{session}}} \ge \mathbf{80\%}$$
  *(Đạt được hiệu suất tập trung cao, phản ánh việc phân bổ khối lượng task của AI là thực tế và vừa sức với thời gian rảnh của người học).*
- **Công thức tính toán:**
  Đối với một phiên học $i$:
  $$CR_i = \left( \frac{N_{\text{completed\_tasks}, i}}{N_{\text{scheduled\_tasks}, i}} \right) \times 100\%$$
  Hiệu quả thực thi trung bình trên toàn bộ $M$ phiên học trong đợt thử nghiệm:
  $$\overline{CR} = \frac{1}{M} \sum_{i=1}^{M} CR_i \ge 80\%$$
  Trong đó:
  - $N_{\text{completed\_tasks}, i}$: Số task chuyển trạng thái `COMPLETED` trong phiên học $i$.
  - $N_{\text{scheduled\_tasks}, i}$: Tổng số task được chọn vào phiên học $i$ lúc bấm Start Session ($N \ge 1$).
- **Nguồn dữ liệu & Công cụ đo:**
  - Cơ sở dữ liệu: Truy vấn bảng `study_sessions` và bảng quan hệ `session_tasks`.
- **Điều kiện biên & Quy tắc xử lý gián đoạn (Interruption Handling):**
  - Đối với các phiên bị gián đoạn hoặc dừng sớm: Các task chưa kịp hoàn thành tự động quay về Backlog theo quy định `BUSR-09`. Nếu phiên đạt điều kiện `PARTIAL_COMPLETED` (theo `OS-01`), tỷ lệ được tính toán trên số task thực tế đã hoàn thành.

---

### 3.3 KPI 3 — Tỷ lệ duy trì lộ trình (Plan Adherence Rate)
*Mã truy vết SRS:* `EVAL-03` | *Mục tiêu liên kết:* `BG-03`, `BR-003`

- **Định nghĩa:** Tỷ lệ phần trăm số ngày/buổi học người dùng thực sự kích hoạt Study Workspace và tham gia học tập so với tổng số ngày/buổi học đã được lên lịch chính thức trong khoảng thời gian theo dõi của lộ trình.
- **Mục tiêu định lượng (Benchmark Threshold):** 
  $$\mathbf{AR_{\text{plan}}} \ge \mathbf{70\%}$$
  *(Đối chứng thực tế: Khảo sát Mục 3.4 chỉ ra 88.9% người học nản chí bỏ cuộc khi bị dồn ứ lịch. Chỉ số $\ge 70\%$ chứng minh tính hiệu quả vượt bậc của cơ chế thích ứng Domino Shift).*
- **Công thức tính toán:**
  $$AR = \left( \frac{D_{\text{attended}}}{D_{\text{scheduled}} - D_{\text{paused}}} \right) \times 100\%$$
  Trong đó:
  - $D_{\text{attended}}$: Số ngày học có phát sinh ít nhất 01 phiên học hợp lệ (`status = COMPLETED` hoặc `PARTIAL_COMPLETED`).
  - $D_{\text{scheduled}}$: Tổng số ngày có task được xếp lịch trong Official Schedule tính đến thời điểm đo lường.
  - $D_{\text{paused}}$: Số ngày học rơi vào khoảng thời gian lộ trình ở trạng thái `PAUSED` (tuân thủ quy tắc loại trừ công bằng: thời gian tạm dừng không bị tính là vi phạm kỷ luật).
- **Nguồn dữ liệu & Công cụ đo:**
  - Bảng `official_schedules`, `study_sessions`, và bảng `pause_records`.
- **Điều kiện biên & Ngoại lệ:**
  - Không tính các ngày nghỉ theo cấu hình Availability của người dùng (những ngày quỹ giờ = 0h).

---

### 3.4 KPI 4 — Tỷ lệ hoàn thành tác vụ người dùng (Task Success Rate - Rubric TC2.7)
*Mã truy vết SRS:* `EVAL-04` | *Mục tiêu liên kết:* `BG-04`, `BR-004`

- **Định nghĩa:** Tỷ lệ người dùng thực nghiệm thực hiện thành công các luồng tác vụ chính trên hệ thống mà không cần sự trợ giúp kỹ thuật trực tiếp từ nhóm phát triển, đánh giá trong đợt kiểm thử chấp nhận người dùng (UAT Phase).
- **Mục tiêu định lượng (Benchmark Threshold):** 
  $$\mathbf{TSR} \ge \mathbf{90\%}$$
- **Công thức tính toán:**
  Đánh giá trên $K$ kịch bản tác vụ trọng yếu đối với tập hợp $U$ người dùng thử nghiệm ($U \ge 10$):
  $$TSR = \left( \frac{\sum_{u=1}^{U} \sum_{k=1}^{K} S_{u, k}}{U \times K} \right) \times 100\% \ge 90\%$$
  Trong đó:
  - $S_{u, k} = 1$ nếu người dùng $u$ hoàn thành tác vụ $k$ thành công đạt tiêu chí chấp nhận.
  - $S_{u, k} = 0$ nếu người dùng $u$ thất bại, từ bỏ hoặc gặp lỗi chặn không thể hoàn tất tác vụ $k$.
- **4 Kịch bản Tác vụ Cốt lõi ($K = 4$):**
  1. *Tác vụ 1 (Onboarding & Planning):* Đăng ký tài khoản $\rightarrow$ Nhập mục tiêu $\rightarrow$ Duyệt Milestone $\rightarrow$ Chỉnh sửa và bấm "Apply" lưu lộ trình.
  2. *Tác vụ 2 (Execution Workspace):* Mở Study Workspace $\rightarrow$ Chạy Timer Pomodoro $\ge 1$ chu kỳ $\rightarrow$ Tick hoàn thành task $\rightarrow$ Lưu Scratchpad note $\rightarrow$ Ghi Key Takeaway và kết thúc phiên.
  3. *Tác vụ 3 (Adaptive Rescheduling):* Thiết lập Tạm dừng lộ trình 3 ngày (Pause Roadmap) $\rightarrow$ Kiểm tra lịch tự động dời tịnh tiến (Domino Shift) trên màn hình Lịch.
  4. *Tác vụ 4 (Integration & Review):* Tạo liên kết WebCal Token $\rightarrow$ Nhúng vào ứng dụng lịch (hoặc tải file `.ics`) $\rightarrow$ Xem báo cáo thống kê tiến độ định kỳ.
- **Nguồn dữ liệu & Công cụ đo:**
  - Bảng chấm điểm UAT (UAT Test Protocol Sheet) ghi nhận kết quả thực hiện trực tiếp của từng người tham gia.

---

### 3.5 KPI 5 — Điểm hài lòng trải nghiệm chuẩn hóa (System Usability Scale - SUS)
*Mã truy vết SRS:* `EVAL-05` | *Mục tiêu liên kết:* `BG-04`, `BR-004`

- **Định nghĩa:** Điểm số đánh giá mức độ khả dụng và độ thỏa mãn trải nghiệm của người dùng đối với hệ thống FocusFlow, được đo lường bằng bảng câu hỏi chuẩn hóa quốc tế **System Usability Scale (SUS)** gồm 10 câu hỏi tiêu chuẩn (Brooke, 1996).
- **Mục tiêu định lượng (Benchmark Threshold):** 
  $$\mathbf{\overline{SUS}} \ge \mathbf{80 / 100\text{ điểm (Xếp loại Grade A / Excellent)}}$$
  *(Vượt xa mức trung bình ngành là 68 điểm, chứng minh sản phẩm có tính hoàn thiện giao diện và công thái học phần mềm cao theo chuẩn Rubric TC2.7).*
- **Công thức tính toán chuẩn mực quốc tế (Brooke, 1996):**
  Bảng câu hỏi gồm 10 mục với thang đo Likert từ 1 (*Rất không đồng ý*) đến 5 (*Rất đồng ý*):
  - Đối với các câu hỏi lẻ (1, 3, 5, 7, 9 - phát biểu tích cực): Điểm thành phần = $\text{Điểm trả lời} - 1$.
  - Đối với các câu hỏi chẵn (2, 4, 6, 8, 10 - phát biểu tiêu cực): Điểm thành phần = $5 - \text{Điểm trả lời}$.
  - Tổng điểm SUS của một người dùng $u$:
    $$SUS_u = \left( \sum_{q=1}^{10} \text{Điểm thành phần}_q \right) \times 2.5$$
  - Điểm SUS trung bình của đợt thử nghiệm trên $U$ người dùng ($U \ge 10$):
    $$\overline{SUS} = \frac{1}{U} \sum_{u=1}^{U} SUS_u \ge 80.0$$
- **Nguồn dữ liệu & Công cụ đo:**
  - Phiếu khảo sát trực tuyến Google Form ẩn danh thu thập kết quả khảo sát SUS ngay sau khi người dùng hoàn tất đợt trải nghiệm UAT.

---

## 4. Giao thức Thực nghiệm Nghiệm thu Người dùng Thật (UAT Protocol)

Nhằm đáp ứng tuyệt đối tiêu chuẩn **TC2.7 (Đánh giá nghiêm túc trên người dùng thật, không số liệu ngụy tạo)**:

### 4.1 Quy mô & Tiêu chuẩn chọn mẫu UAT
- **Cỡ mẫu nghiệm thu:** Tối thiểu **$U = 10 – 15$ người dùng thật**.
- **Cơ cấu phân bổ mẫu:**
  - $\ge 60\%$ (6–9 người): Sinh viên chuyên ngành CNTT / Kỹ thuật Phần mềm đang tự học công nghệ mới.
  - $\ge 25\%$ (3–4 người): Người đi làm trái ngành đang tự học lập trình/kỹ năng số ngoài giờ.
  - $\ge 15\%$ (1–2 người): Người tự học chứng chỉ chuyên môn quốc tế.
- **Thời lượng thử nghiệm:** Mỗi người dùng trải nghiệm tối thiểu trong vòng **07 đến 14 ngày liên tục** để đảm bảo kiểm chứng được đầy đủ chu trình: Tạo lộ trình $\rightarrow$ Học nhiều buổi $\rightarrow$ Gặp biến cố tạm dừng $\rightarrow$ Xem báo cáo định kỳ.

```
TIẾN TRÌNH THỰC NGHIỆM UAT (7 - 14 NGÀY)
┌─────────────┐       ┌───────────────────────┐       ┌────────────────────────┐
│  Ngày 1     │ ────> │  Ngày 2 - Ngày 5      │ ────> │  Ngày 6 - Ngày 7       │
│  Onboarding │       │  Thực thi phiên học   │       │  Kích hoạt Domino Shift│
│  Tạo Roadmap│       │  Đo Task Completion   │       │  & Đánh giá Review tuần│
└─────────────┘       └───────────────────────┘       └───────────┬────────────┘
                                                                  │
                                                                  ▼
                                                      ┌────────────────────────┐
                                                      │  Nghiệm thu:           │
                                                      │  - Đo TSR (KPI 4)      │
                                                      │  - Khảo sát SUS (KPI 5)│
                                                      └────────────────────────┘
```

### 4.2 Kịch bản 4 tác vụ cốt lõi đo lường Task Success Rate

| Tác vụ | Mục tiêu thực hiện | Tiêu chí đạt (Success Criteria) | Thời gian tối đa cho phép |
|---|---|---|:---:|
| **Task 1: Tạo Lộ trình AI** | Đăng ký tài khoản, nhập mục tiêu học tập (ví dụ: "Học NestJS trong 4 tuần"), xem đề xuất, chỉnh sửa 1 task và bấm Apply. | Tạo thành công Official Schedule hiển thị trên trang Lịch; không vượt quá thời gian rảnh. | $\le 5$ phút |
| **Task 2: Thực thi Buổi học** | Vào Study Workspace, khởi động Pomodoro 25 phút, tick hoàn thành task, ghi chép Scratchpad và lưu Key Takeaway. | Phiên học kết thúc thành công; số phút thực học được lưu; task xong chuyển trạng thái `COMPLETED`. | Thời lượng phiên + 3 phút |
| **Task 3: Tạm dừng & Dời lịch** | Giả lập bận việc đột xuất 2 ngày: Vào cài đặt Roadmap bấm "Pause", chọn 2 ngày tạm dừng. | Toàn bộ các buổi học phía sau tự động dời lùi đúng 2 ngày khả dụng; không báo quá hạn đỏ. | $\le 2$ phút |
| **Task 4: Lịch ngoài & Thống kê** | Tạo URL WebCal token an toàn, đồng bộ vào ứng dụng lịch (hoặc tải `.ics`), sau đó mở Dashboard xem báo cáo tuần. | Lịch ngoại vi hiển thị đúng các task chính thức; biểu đồ tiến độ hiển thị đúng số phút thực học. | $\le 3$ phút |

### 4.3 Công cụ & Môi trường đo lường tự động (Telemetry Logging)
Hệ thống cài đặt sẵn các module đo lường kỹ thuật độc lập:
- **Client-side Performance Observer:** Tự động ghi lại thời gian render giao diện và tương tác nút bấm.
- **Backend Audit Event Logger:** Bắt sự kiện tạo lịch, lưu phiên, tính toán toán học chính xác.
- **Google Form SUS Validator:** Script tự động tính điểm theo thuật toán của Brooke (1996), trích xuất biểu đồ phân phối điểm SUS.

---

## 5. Ma trận Truy vết & Đánh giá Rủi ro Mục tiêu

### 5.1 Ma trận ánh xạ từ Nỗi đau khảo sát $\rightarrow$ KPI $\rightarrow$ SRS

| Nỗi đau từ Khảo sát Thực tế ($N=45$) | Business Goal | Chỉ số KPI | Mã SRS tương ứng | Ngưỡng Benchmark Nghiệm thu |
|---|---|---|---|---|
| **82.2%** khó chia nhỏ mục tiêu; mất **48.6 phút** tạo lịch | `BG-01` | **KPI 1** (Plan Creation Time) | `EVAL-01`, `FR-PLAN-001..003` | $\le \mathbf{5}$ phút (giảm 90% thời gian) |
| **77.8%** mệt mỏi vì dùng **3.6 công cụ** rời rạc | `BG-02` | **KPI 2** (Session Efficiency) | `EVAL-02`, `FR-SESSION-001..003` | Hoàn thành $\ge \mathbf{80\%}$ task/buổi |
| **88.9%** nản lòng bỏ cuộc khi bị trễ hạn 2-3 ngày | `BG-03` | **KPI 3** (Plan Adherence) | `EVAL-03`, `FR-PAUSE-001`, `BUSR-07` | Tỷ lệ duy trì $\ge \mathbf{70\%}$ buổi học |
| Người dùng e ngại lỗi phần mềm và giao diện phức tạp | `BG-04` | **KPI 4** (Task Success Rate) | `EVAL-04`, `NFR-UX-001..002` | Tỷ lệ hoàn thành tác vụ $\ge \mathbf{90\%}$ |
| Đòi hỏi độ hoàn thiện cao, tin cậy đối với sinh viên | `BG-04` | **KPI 5** (SUS Usability Score) | `EVAL-05`, `NFR-UX-002` | Điểm $\mathbf{SUS} \ge \mathbf{80/100}$ (Grade A) |

---

### 5.2 Ma trận rủi ro không đạt chỉ tiêu & Biện pháp giảm thiểu

| Chỉ số KPI | Nguy cơ / Rủi ro có thể xảy ra | Nguyên nhân kỹ thuật | Biện pháp Giảm thiểu & Kiểm soát Kỹ thuật |
|---|---|---|---|
| **KPI 1** ($T_{\text{plan}} > 5$m) | External LLM phản hồi chậm hoặc nghẽn mạng. | API latency cao từ OpenAI/Anthropic. | Áp dụng Hard Timeout 55s (`FR-AI-002`), cơ chế Auto-retry không tính quota, hỗ trợ Fallback Manual Plan tức thì. |
| **KPI 2** ($CR < 80\%$) | AI phân bổ khối lượng task quá nặng so với thời gian rảnh. | Prompt thiếu ràng buộc thời lượng task chi tiết. | Backend Hard Ceiling Gate (`BUSR-03`) chặn không cho Apply nếu tổng thời lượng task vượt quá quỹ giờ rảnh đã cấu hình. |
| **KPI 3** ($AR < 70\%$) | Người dùng quên lịch học hoặc bận đột xuất dài ngày. | Không có thông báo nhắc lịch và ngại dời ngày. | Đồng bộ lịch 1 chiều qua WebCal Feed (`FR-CALENDAR-002`); Nút Pause 1 chạm kích hoạt Domino Shift không phạt trễ hạn. |
| **KPI 4** ($TSR < 90\%$) | Giao diện gây hiểu lầm hoặc luồng thao tác có điểm nghẽn. | Thiết kế UX chưa tối ưu công thái học. | Tuân thủ Google Lighthouse Accessibility $\ge 90$ (`NFR-UX-002`); Tối giản luồng thao tác qua Wizard từng bước rõ ràng. |
| **KPI 5** ($SUS < 80$) | Ứng dụng giật lag hoặc phản hồi chậm. | API backend xử lý chậm khi có tải. | Tối ưu hóa API phản hồi $\le 200$ms (`NFR-PERF-002`), áp dụng Optimistic UI cập nhật trạng thái tức thì trên client. |

---

## 6. Góc Nhìn Cố Vấn Khóa Luận (Defense Guidance on KPIs)

### Câu hỏi Phản biện 1: "Tại sao em lại đặt ra chỉ số SUS $\ge 80$ mà không phải là một con số khác như 68 hay 70?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, theo nghiên cứu chuẩn hóa của John Brooke (1996) và thang đo của Sauro & Lewis (2012), điểm SUS trung bình của các phần mềm thông thường là **68 điểm** (tương đương mức Grade C). Đối với một đồ án tốt nghiệp xuất sắc hướng tới mục tiêu người dùng yêu thích và duy trì sử dụng hàng ngày, mức 68 điểm chỉ là mức 'chấp nhận được' chứ chưa tạo ra sự vượt trội. Mức $\ge 80$ điểm là ngưỡng chuẩn quốc tế để xếp hạng sản phẩm vào mức **Grade A (Excellent)**. Đặt ra mục tiêu $\ge 80$ điểm buộc nhóm phát triển phải tối ưu hóa từng mili-giây phản hồi giao diện, đảm bảo chuẩn Accessibility $\ge 90$ điểm của Google và kiểm soát nghiêm ngặt hiện tượng tải nhận thức của người học."*

### Câu hỏi Phản biện 2: "Làm thế nào để Hội đồng tin rằng các số liệu KPI đo lường trong đợt thử nghiệm UAT là trung thực, không phải do sinh viên tự điền vào?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, toàn bộ số liệu đo lường của FocusFlow được bảo chứng bằng cơ chế kép:  
> 1. **Dữ liệu kỹ thuật tự động (Automated Telemetry):** Các chỉ số KPI 1, KPI 2, KPI 3 được trích xuất trực tiếp từ các câu lệnh SQL truy vấn bảng cơ sở dữ liệu `study_sessions`, `official_schedules`, và `audit_events` với đầy đủ timestamp hệ thống không thể làm giả thủ công.  
> 2. **Minh chứng độc lập (Independent Artifacts):** Chỉ số KPI 4 và KPI 5 được lưu trữ qua các biên bản kiểm thử UAT có chữ ký xác nhận của từng người tham gia và file xuất dữ liệu gốc (CSV) từ Google Form khảo sát chuẩn hóa SUS. Nhóm sẵn sàng mở trực tiếp cơ sở dữ liệu và dashboard thống kê trước Hội đồng."*
