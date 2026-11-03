# Báo cáo đánh giá toàn diện Use Case và Class Diagram — FocusFlow

*Ngày 27/10/2026. Đối chiếu: SRS v1.2, ADR-001…010, 4 tài liệu phân tích dự án, 6 sơ đồ use case, đặc tả 19 UC, class diagram (puml và md).*

## 1. Kết luận điều hành

Bộ mô hình phủ rộng và có chiều sâu (19/19 UC khớp danh mục SRS §3.2; 47 classifier = 29 class + 18 enum), nhưng **chưa đủ hợp lý để đóng băng baseline**. Có ba nhóm vấn đề:

1. **Gốc ở SRS.** Nhiều lỗi của UC (dùng sai `<<extend>>`/`<<include>>`, UC-17, UC-09) xuất hiện vì UC được đặc tả đúng theo SRS trong khi bản thân SRS sai hoặc tự mâu thuẫn. Sửa diagram mà không sửa SRS thì sẽ lệch trở lại.
2. **Lệch chéo giữa các tài liệu.** UC spec, class diagram, SRS và ADR đang mô tả những hệ thống hơi khác nhau (trạng thái thanh toán, bảng dữ liệu, giới hạn thời lượng, nơi lưu OAuth token) dù đều tự ghi “đồng bộ 100%”.
3. **Sai mức trừu tượng.** UC spec lẫn chi tiết cài đặt; class diagram lẫn hạ tầng/CSDL và đi ngược chính ADR-001 và ADR-007 của dự án.

| Hạng mục | Đánh giá | Ghi chú |
| --- | --- | --- |
| Độ phủ chức năng so với SRS | Tốt | 19/19 UC khớp; FR do hệ thống tự kích hoạt chưa có UC “nhà” (mục 3.1) |
| Cấu trúc UML của use case | Cần sửa | `extend`/`include` sai ở UC-04/05, 08, 12 |
| An toàn AI / Human-in-the-Loop | **Nghiêm trọng** | UC-17 ghi thẳng vào lịch, mâu thuẫn BUSR-02 và BUSR-03 |
| Chất lượng đặc tả UC | Cần sửa | Rò rỉ thiết kế, UC gộp nhiều mục tiêu, lỗi ký tự |
| Nhất quán UC–Class–SRS–ADR | **Nghiêm trọng** | Mục 5.1 và mục 6 |
| Class: quan hệ và trách nhiệm | Cần sửa | Quan hệ dư, composition/aggregation sai, trách nhiệm trùng |
| Class: tuân thủ kiến trúc của chính dự án | **Nghiêm trọng** | Liên kết đối tượng xuyên context, ghi chéo context |

**Tám việc nên làm trước** (chi tiết ở mục 7): (1) sửa SRS: BUSR-02 so với FR-ADAPT-002; (2) sửa SRS §3.2 cho UC-04/05, UC-08, UC-12; (3) chốt tập trạng thái thanh toán, nơi lưu OAuth token và audit log; (4) bỏ liên kết đối tượng xuyên context ở class diagram; (5) thêm actor Scheduler/Email và UC hệ thống; (6) tách các UC gộp nhiều mục tiêu; (7) dọn rò rỉ thiết kế khỏi đặc tả; (8) dọn lỗi vệ sinh tài liệu.

### Điều chỉnh so với lượt đánh giá trước

Sau khi đọc SRS và ADR, sáu nhận định trước đó được hiệu chỉnh (gốc lỗi chuyển nguồn, không phải hết lỗi):

- UC-17 bỏ qua cổng kiểm duyệt là **do SRS (FR-ADAPT-002) quy định**; lỗi nằm ở chỗ SRS tự mâu thuẫn.
- Thời lượng task AI 30–120 phút là **đúng SRS** (FR-PLAN-002); con số 15–240 của class và ADR-009 mới là chỗ lệch.
- `REFUNDED` có trong SRS §12 nên class đi theo SRS; mâu thuẫn nằm giữa SRS §12 và SRS §2.5 / ADR-007.
- `refresh_tokens` trong UC spec là **trích dẫn lỗi thời**: ADR-008 lưu refresh token ở Redis, nên class không cần lớp này.
- Task `IN_PROGRESS` **được SRS §6.2 sinh ra** khi Start Session; thiếu sót nằm ở UC-11.
- “Quên mật khẩu” **không có trong SRS**; chỉ ADR-003 nhắc tới (mở rộng phạm vi ngoài SRS).

## 2. Phạm vi, phương pháp và cơ sở đánh giá

**Phương pháp:** truy vết bốn tầng Phân tích → SRS → UC → Class → ADR; đối chiếu bằng script (đếm lớp/enum, so tên bảng giữa hai tài liệu, đếm số bước luồng chính, quét từ khóa thiết kế, quét ký tự lạ). Mỗi phát hiện ghi **nguồn gốc**: \[SRS\] lỗi nằm ở yêu cầu, \[UC\] lỗi ở mô hình use case, \[CLS\] lỗi ở class diagram, \[ADR\] lỗi ở quyết định kiến trúc.

**Cơ sở lý thuyết:**

- OMG UML 2.5.1, chương Use Cases (§18): ngữ nghĩa `extend`/`include`, association giữa actor và use case.
- Cockburn, *Writing Effective Use Cases*: mức mục tiêu (summary / user-goal / subfunction), “một phiên làm việc”, luồng chính 3–9 bước, loại UI khỏi kịch bản.
- Larman, *Applying UML and Patterns*: kiểm tra EBP, nguyên tắc domain model (không thêm quan hệ dư hoặc suy diễn được), GRASP (High Cohesion, Information Expert, Pure Fabrication).
- ISO/IEC/IEEE 29148:2018: yêu cầu phải singular, appropriate (không áp đặt cài đặt), consistent, traceable.
- Evans (*DDD*) và Vernon (*Implementing DDD*): bounded context, aggregate, tham chiếu giữa aggregate bằng định danh.
- OWASP Top 10 for LLM Applications (LLM01: Prompt Injection).

**Hạn chế:** không có `schema.sql`, file draw.io và `AGENTS.md`; chưa render PlantUML; một số bằng chứng dựa trên đọc mã nguồn puml.

## 3. Độ phủ: thiếu và thừa

### 3.1 Truy vết SRS → UC

RTM (SRS §16) gán đủ 19 UC. Ba điểm đáng lưu ý:

- **FR do hệ thống tự kích hoạt không có UC “nhà”:** FR-ADAPT-001 (quét 00:05 và gửi Email), FR-PROFILE-001 (tổng hợp hồ sơ), FR-QUOTA-001 (giữ chỗ và thu hồi hạn ngạch), phần chốt phiên theo OS-07 của FR-SESSION-003. Chúng bị nhét vào UC-17, UC-03/07/09, UC-04 (xem U4).
- **UC không có FR riêng:** UC-09. SRS có trạng thái `ARCHIVED` nhưng không có FR hay chuyển trạng thái cho việc lưu trữ và đổi tên mục tiêu; trace của UC-09 trỏ tới FR-AVAIL-003, FR-QUOTA-002 không liên quan (xem U9).
- **FR có hai “nhà”:** kết nối Google Calendar (OAuth) thuộc FR-CALENDAR-002/UC-13 nhưng UC-03 luồng 4a cũng mô tả.

### 3.2 Còn thiếu

| # | Thiếu | Nguồn | Bằng chứng |
| --- | --- | --- | --- |
| 1 | Quên/đổi mật khẩu; cập nhật hồ sơ và múi giờ | \[SRS\] | FR-AUTH chỉ có đăng ký và đăng nhập. ADR-003 slice `auth/` lại liệt kê “quên mật khẩu”. Múi giờ quyết định `OVERDUE` (SRS §12, User) nhưng không UC nào cho đổi |
| 2 | Hết hạn và hạ cấp Premium | \[SRS\] | FR-QUOTA-002 chỉ có nâng cấp; FR-ADM-002 cho đổi PREMIUM→FREE nhưng không có luật cho người đang có hơn 3 roadmap `ACTIVE`; `User` không có thuộc tính hết hạn gói |
| 3 | Sửa/xóa task và milestone khi lộ trình đã `ACTIVE` | \[SRS\] | §6.2 có chuyển `CANCELLED` khi “User xóa/hủy” nhưng không có FR; UC-10 chỉ dời lịch, gán DAG, tick |
| 4 | Security Audit Log và Admin Audit Log | \[SRS\]\[ADR\] | BUSR-11, FR-QUOTA-002, FR-ADM-002 yêu cầu ghi; SRS §12 (18 thực thể) và ADR-007 (24 bảng) không có; UC spec trích `security_audit_logs`, `admin_audit_logs` |
| 5 | Kết nối lịch ngoại vi (`CalendarConnection`) | \[CLS\] | SRS §12 mục 13 cần “trạng thái kết nối”; ADR-008 yêu cầu lưu OAuth token mã hóa; class nhét `oauthRefreshTokenEncrypted` vào `WebCalToken`, vốn chỉ được lưu hash theo OS-05 |
| 6 | Ngữ cảnh làm rõ của Goal | \[CLS\] | FR-GOAL-002 bước 4 và SRS §12 mục 2; `Goal` chỉ có `title`, `rawDescription`, `targetDate`, `status` |
| 7 | Chế độ đồng hồ Pomodoro/Stopwatch; Task → `IN_PROGRESS` khi Start Session | \[CLS\]\[UC\] | FR-SESSION-001 và §6.2; UC-11 không nêu, `StudySession` không có thuộc tính chế độ |
| 8 | `preferredPeriod` (MORNING/AFTERNOON/EVENING/ANY) | \[CLS\] | FR-AVAIL-001; không có trong `WeeklySchedule` |
| 9 | `PaymentTransaction.expiresAt` và `PaymentStatus.EXPIRED` | \[CLS\] | FR-QUOTA-002 (“CANCELLED hoặc EXPIRED”), UC-05 (QR hiệu lực 15 phút) |
| 10 | Actor Scheduler và Email Service | \[UC\] | FR-ADAPT-001 ghi tác nhân kích hoạt là bộ lập lịch; ADR-004/010 dùng `EmailNotificationPort` (SMTP) |
| 11 | Nguồn đo KPI 1: bảng `audit_events` | \[SRS\]\[ADR\] | Tài liệu KPI §3.1 đo bằng sự kiện `GOAL_SUBMITTED` và `OFFICIAL_SCHEDULE_CREATED`, không có trong 24 bảng, class hay UC; ngoại lệ idle trên 5 phút cần telemetry sự kiện |
| 12 | Quan hệ cha–con của Task | \[CLS\] | FR-ADAPT-003 lựa chọn (1) và ADR-010 “AI Micro-Stepping” tách một task thành 2–3 task con |

### 3.3 Đang thừa hoặc chưa có cơ sở

| # | Thừa | Bằng chứng |
| --- | --- | --- |
| 1 | `NoteType.GENERAL` (ghi chú ngoài phiên) | SRS §12 có, nhưng không FR hay UC nào tạo ghi chú ngoài phiên (FR-SESSION-002 chỉ có SCRATCHPAD và TAKEAWAY) |
| 2 | `PaymentStatus.REFUNDED` và `markRefunded()` | SRS §2.5 và problem-definition §6.2 loại trừ hoàn tiền; ADR-007 chỉ có 4 trạng thái; không UC nào dùng |
| 3 | `ReviewCycle.MILESTONE` và liên kết `AIReview → Milestone` | FR-REPORT-002 chỉ có điều kiện “≥ 1 tuần hoặc ≥ 3 phiên” |
| 4 | `ChangeActorType.CALENDAR_SYNC` | BUSR-08: chiều inbound chỉ đọc, không sửa lịch. Tên `ChangeActorType` cũng sai nghĩa (giá trị là loại trigger) |
| 5 | `TaskDependency.isMandatory` | FR-TASK-003: mọi tiền đề đều bắt buộc |
| 6 | `OutboxEvent`, `ProcessedEvent` trong class diagram miền | Hạ tầng messaging; ma trận class §6.1 gán chúng cho 6 UC trong khi UC spec không nhắc “Outbox” lần nào |
| 7 | `Goal 1..* Roadmap` | Không UC nào tạo hơn một roadmap cho một goal (SRS §6.1: muốn học tiếp phải tạo Goal mới) |
| 8 | UC-05 và UC-12 như UC độc lập | Xem U2, U3 |

## 4. Đánh giá Use Case (diagram và đặc tả)

Mức độ: **NT** nghiêm trọng, **QT** quan trọng, **N** nhỏ.

### U1 \[NT · SRS\] UC-17 ghi thẳng vào lịch, mâu thuẫn BUSR-02 và BUSR-03

- **Bằng chứng:** BUSR-02 viết AI “tuyệt đối không có quyền tự động ghi” vào Official Schedule; BUSR-03 coi Backend là chốt chặn cuối và tổng giờ “không bao giờ” vượt trần. Nhưng FR-ADAPT-002 bước 4–5 cho AI xếp lại rồi hệ thống “cập nhật lại lịch trình” ngay, chỉ kiểm schema và “dung lượng/trùng lấn cơ bản”, mà vẫn trích BUSR-02 làm căn cứ truy vết. UC-17 bước 5–6 và BR-ADAPT-03 làm đúng như vậy. Lý do ở ADR-009 §3.1.1 (“task đã được thẩm định DAG từ lúc tạo”) không đứng vững: dời ngày có thể đặt task hậu kế trước tiên quyết hoặc đẩy task ra ngoài khung Mode B, hai điều mà kiểm tra “cơ bản” không bao phủ, và đe dọa EVAL-06 (100% Zero Overbooking). Ma trận class §6.1 lại gán `ScheduleProposal` và `DagCycleValidator` cho UC-17, mâu thuẫn tiếp.
- **Cơ sở:** khung mức tự chủ của AI agent (hành động ghi dữ liệu tối thiểu ở mức act-with-approval); ISO 29148, tính nhất quán của tập yêu cầu.
- **Sửa:** (a) FR-ADAPT-002: AI sinh `ScheduleProposal` trong phạm vi một roadmap, người học xem diff rồi Apply; hoặc (b) nếu giữ nguyên thiết kế nhanh, sửa BUSR-02/03 thành có ngoại lệ tường minh, chạy lại Tier 2 tất định (DAG, Mode B, trần ngày; không tốn LLM) và thêm nút Hoàn tác dựa trên `schedule_change_logs`.

### U2 \[NT · SRS §3.2\] `<<extend>>` sai ở UC-08 và UC-12

- **UC-08:** FR-PLAN-004 cho trigger độc lập (“menu tạo Roadmap”) và hậu điều kiện là Roadmap `ACTIVE` kèm Official Schedule, tức một mục tiêu hoàn chỉnh, *thay thế* chứ không *bổ sung*. Nó extend cùng lúc UC-06 và UC-07 với cùng extension point `AI Service Unavailable or Manual Override`, vốn là tên một điều kiện chứ không phải vị trí trong luồng. Luồng 2e3 và 7e của UC-06 kết thúc “thất bại” rồi mới chuyển sang UC-08, tức điều hướng chứ không mở rộng.
- **UC-12:** “Dừng sớm” là luồng 5a của UC-11 (FR-SESSION-003 coi đó là luồng chính của dừng sớm); phục hồi sau mất kết nối xảy ra ở một lần ngồi khác; luồng 1c do tiến trình quét (OS-07) khởi tạo. Trường “Mức độ: Extend Use Case” không thuộc mức nào của Cockburn.
- **Cơ sở:** UML 2.5.1 §18: use case được extend phải có nghĩa độc lập, use case extend bổ sung hành vi tại extension point; Cockburn “one sitting”; Larman EBP.
- **Sửa:** UC-08 độc lập (nối với Learner); UC-06/07 chỉ có luồng thay thế “chuyển sang UC-08”, hoặc dùng generalization “Tạo lộ trình” ← {bằng AI, thủ công}. Gộp UC-12 vào UC-11; phần chốt phiên bỏ dở thành UC hệ thống (U4). Lưu ý: `<<extend>>` UC-15 → UC-14 là **đúng** (UC-14 độc lập, AI Review là tùy chọn).

### U3 \[QT · SRS §3.2\] UC-04 `<<include>>` UC-05 không đạt tiêu chí

- **Bằng chứng:** UC-05 chỉ có UC-04 dùng (include cần tái dùng từ hai nơi). Bước 6–8 do Gateway khởi tạo (webhook), có thể xảy ra sau khi người học đã đóng trình duyệt, nhưng UC-04 bước 6 chờ kết quả “trả về”. UC-04 luồng 4a tái dùng đơn `PENDING` còn UC-05 bước 1 luôn tạo bản ghi mới. Gateway không là actor của UC-04 dù UC-04 chỉ hoàn tất nhờ nó.
- **Sửa:** gộp thành “Nâng cấp gói Premium” (Gateway là secondary actor). Xử lý webhook là UC do Gateway khởi tạo (external system là primary actor) hoặc luồng hệ thống. Thêm luật xử lý đơn `PENDING` cũ.

### U4 \[QT · UC\] Thiếu actor hệ thống; UC-17 gộp hai phiên làm việc

- **Bằng chứng:** SRS §3.1 chỉ có 5 actor, nhưng FR-ADAPT-001 ghi bộ lập lịch là tác nhân kích hoạt và gửi Email qua SMTP; ADR-004 liệt kê 6 nhóm tác vụ nền. UC-17 gộp bước 1 (job 00:05 do hệ thống chạy) với các bước 2–8 (hôm sau người học bấm nút); tiền điều kiện lặp lại đúng bước 1. Gemini, Calendar, PayOS là actor còn SMTP thì không: đối xử không nhất quán. Luật của job nền nằm sai chỗ (BR-QUOTA-03, reset hạn ngạch ngày 01 hàng tháng, nằm trong UC-04).
- **Sửa:** thêm actor «Scheduler» và «Dịch vụ Email»; UC hệ thống: “Quét quá hạn và thông báo”, “Chốt phiên học bỏ dở”, “Làm mới hạn ngạch và thu hồi giữ chỗ”, “Tổng hợp hồ sơ thói quen”. UC-17 chỉ còn phần “Dời lịch bằng AI”.

### U5 \[QT · UC\] UC gộp nhiều mục tiêu và trùng trách nhiệm

- **Bằng chứng:** UC-02 (đăng nhập + làm mới phiên + đăng xuất); UC-03 (tên có chữ “và”: thời gian rảnh + hồ sơ SRL + kết nối lịch); UC-10 (xem lịch, Backlog→lịch, tick nhanh, dời lịch, gán DAG; luồng chính chọn tùy ý một trong bốn mục tiêu); UC-13 (đồng bộ Free/Busy, feed WebCal do Calendar tự poll, tải `.ics`, reset token); UC-18 (tra cứu, khóa/mở, đổi tier, reset quota, đối soát). Luồng chính của UC-09 là “xem danh sách và chuyển ngữ cảnh”, một thao tác giao diện chứ không phải mục tiêu nghiệp vụ. UC-06 và UC-07 có 10 bước (hơn mức 9).
- **Cơ sở:** Larman EBP; Cockburn 3–9 bước; ISO 29148 “singular”.
- **Sửa:** hướng tới khoảng 24–26 UC mức user-goal, ví dụ: “Kết nối Google Calendar” riêng, “Xuất `.ics` / WebCal” riêng, “Cấu hình thời gian rảnh” tách khỏi “Quản lý hồ sơ SRL”, “Xem lịch” tách khỏi “Dời lịch / xếp Backlog”.

### U6 \[QT · UC\] Diagram không khớp đặc tả và tài liệu actor

- Không có association Learner với UC-05, UC-08, UC-12, UC-15 ở cả master lẫn module diagram, dù spec ghi “Actor chính: Learner”; mục tự rà soát §6.2 vẫn ghi “không có phần tử mồ côi”.
- UC-18 không nối Payment Gateway, trong khi actors-and-personas §2.6 giao cho Gateway việc “đối chiếu giao dịch (UC-18)”; SRS §3.2 lại ghi UC-18 “không có actor phụ”. Hai tài liệu đầu vào mâu thuẫn nhau, cần chốt.
- Spec nêu quy tắc mỗi sơ đồ không quá 12 UC, nhưng chính master diagram có 19 UC.

### U7 \[QT · UC + SRS\] Rò rỉ thiết kế vào đặc tả

- **Bằng chứng (đếm trong UC spec):** `HMAC-SHA256` ×8, `SHA-256` ×4, `/api/v1` ×3, `SMTP` ×3, `Argon2id` ×2, `HttpOnly` ×2; còn `sanitizePromptContext()`, `LogSanitizerMiddleware`, DFS/Kahn, row-level lock, “Local Storage” (UC-12 5e), tên cột `reschedule_count` và `scheduled_date = NULL` ngay trong luồng chính (UC-10 bước 5, UC-17 bước 7). SRS v1.2 tự nhận “trung lập công nghệ” nhưng cũng còn Argon2id (FR-ADM-001), DFS/Kahn (FR-TASK-003), Distributed Lock và Atomic Upsert (FR-PROFILE-001), kèm hai tham chiếu ADR sai: FR-PLAN-005 trỏ ADR-003/008 (đúng là ADR-009), FR-PROFILE-001 trỏ ADR-007/008.
- **Cơ sở:** ISO 29148 “appropriate”; Cockburn: loại UI và thiết kế khỏi kịch bản.
- **Sửa:** chuyển sang NFR hoặc mục “Ghi chú thiết kế” có ID riêng.

### U8 \[QT · UC + SRS\] Thiếu “thuộc tính AI” nhất quán

- **Bằng chứng:** chưa khai báo mức tự chủ cho từng UC có AI (06, 07, 15, 17); BR-REV-02 “không bịa số liệu” thiếu cách kiểm (gợi ý: 100% con số trong review phải khớp số liệu backend, kiểm tự động); PII gửi ra LLM chưa được định nghĩa dù `Key Takeaways` là văn bản tự do; chưa có hành vi quan sát được khi phát hiện prompt injection (OWASP LLM01); UC-17 thiếu ngoại lệ “sai schema sau retry” (UC-06 có 8a).
- **Ba tài liệu mâu thuẫn về hành vi sau 2 lần retry vi phạm:** FR-PLAN-005 (trả bản nháp kèm nhãn cảnh báo), FR-AI-001 (lỗi `AI_SCHEMA_VALIDATION_ERROR` kèm hai nút Thử lại / Lập kế hoạch thủ công), ADR-009 §3.2 (hủy thao tác và RELEASE hạn ngạch). Phải chốt một.

### U9 \[QT · SRS\] UC-09 không có FR, tự sinh luật nghiệp vụ

- SRS §6.1 không có chuyển trạng thái sang `ARCHIVED`. UC-09 luồng 3b tự quy định: lưu trữ sẽ hủy (`CANCELLED`) mọi task chưa xong và giải phóng slot; luồng 3a đổi hạn chót kích hoạt tính lại thứ tự EDF nhưng không nói Official Schedule có tính lại hay không. Cần bổ sung FR và dòng chuyển trạng thái vào SRS.

### U10 \[N\] Vệ sinh tài liệu

- Ký tự lạ do sinh văn bản: `use-case-specifications.md` L434 (“المục”), L839 và L944 (“thời점”); `class-diagrams.md` L901 (“kiểm증”).
- UC-02 bước 3 trích BR-AUTH-01 (chính sách độ mạnh mật khẩu) cho bước đối soát mật khẩu; hai sơ đồ đánh số BR trùng nhau (`BR-005` của SRS và `BR-AUTH-01` cục bộ); đánh số ngoại lệ lạ (`3a.2e`).
- Link `file:///Users/vuthang/...` sẽ hỏng khi nộp; header tự chấm “Rubric Mức 5” và checklist tự tick toàn bộ; UC spec trace `refresh_tokens` (sai, ADR-008 dùng Redis).
- Tên actor chứa sản phẩm (“Google Gemini API”) trong khi SRS dùng “External LLM Provider”; Learner và Admin cùng nối UC-02 nên dùng actor generalization.

### 4.2 UC nên thêm (một `<<include>>` hợp lệ)

“Kiểm định lịch trước khi áp dụng” được dùng bởi UC-07 (Apply), UC-08, UC-10 (dời lịch thủ công), UC-16 (Domino Shift) và UC-17 (sau khi sửa U1): đạt tiêu chí include vì được tái dùng ở nhiều nơi.

## 5. Đánh giá Class Diagram

### C1 \[NT · CLS + SRS + ADR\] Class diagram, UC spec, SRS và ADR mô tả những hệ thống khác nhau

| Khoản mục | SRS | ADR | Class diagram | UC spec | Cần chốt |
| --- | --- | --- | --- | --- | --- |
| Trạng thái thanh toán | FR-QUOTA-002: PENDING, PAID, CANCELLED, EXPIRED. §12: PENDING, PAID, FAILED, CANCELLED, REFUNDED | ADR-007: PENDING, PAID, FAILED, CANCELLED | PENDING, PAID, FAILED, CANCELLED, REFUNDED (không có EXPIRED) | UC-04/05/18 dùng EXPIRED | Tập {PENDING, PAID, FAILED, CANCELLED, EXPIRED}, bỏ REFUNDED |
| Thời lượng task | FR-PLAN-002: 30–120 phút (AI). FR-AVAIL-002: slot từ 30 phút | ADR-009: AI \[15,120\], thủ công \[15,240\] | 15–240 | UC-07: 30–120 | SRS chưa quy định giới hạn thủ công; ghi vào SRS rồi đồng bộ |
| Nơi lưu OAuth Google | §12 mục 13: “trạng thái kết nối” | ADR-008: mã hóa Fernet trong CSDL; ADR-007: 24 bảng không có chỗ | `WebCalToken.oauthRefreshTokenEncrypted` | Trích `calendar_connections` | Tách `CalendarConnection` |
| Refresh token | — | ADR-008: Redis | Không có lớp (đúng) | Trích `refresh_tokens` (sai) | Sửa UC spec |
| Audit log | BUSR-11, FR-ADM-002 yêu cầu ghi | Không có bảng | Không có lớp | Trích `security_audit_logs`, `admin_audit_logs` | Thêm vào SRS §12 và ADR-007, hoặc bỏ yêu cầu |
| Bảng lịch rảnh | — | `availabilities` | `AvailabilityProfile` | Trích `user_availabilities` | Sửa UC spec |
| Trạng thái tài khoản | UC-02/18 dùng ACTIVE, LOCKED | — | `isLocked: Boolean` | UC-02 2e2 nhắc cả SUSPENDED (không có ở đâu) | Enum `AccountStatus` hoặc bỏ SUSPENDED |
| Model LLM mặc định | “External LLM Provider” (trung lập) | ADR-005: đa nhà cung cấp | `AIUsageLog.modelName = "gpt-4o-mini"` | Actor “Google Gemini API” | Bỏ giá trị mặc định cứng |
| Phiên đăng nhập | FR-ADM-001: admin tối đa 8 giờ | ADR-008: access 15 phút, refresh 7 ngày | — | — | Chốt một chính sách |
| Ma trận truy vết §6.1 | — | — | Gán Outbox cho 6 UC; gán `ScheduleProposal` và `DagCycleValidator` cho UC-17 | Spec không nhắc Outbox; UC-17 bỏ cổng | Sửa ma trận |

Hai mục đếm được bằng script: UC spec trích 5 tên bảng không có trong bảng liệt kê của class doc (`admin_audit_logs`, `security_audit_logs`, `refresh_tokens`, `calendar_connections`, `user_availabilities`); class doc có 4 bảng mà UC spec không nhắc (`ai_usage_logs`, `outbox_events`, `processed_events`, `availabilities`). Tuyên bố “đồng bộ tuyệt đối 100%” vì vậy chưa đúng.

### C2 \[NT · CLS + ADR\] Đi ngược ADR-001 và ADR-007 của chính dự án

- **Liên kết đối tượng xuyên context.** Class diagram vẽ association trực tiếp giữa các package (User–Roadmap, Milestone–Task, StudySession–Task, Roadmap–PauseRecord…). ADR-001 §3.1 cấm context này import nội bộ context kia, chỉ được đọc qua `public_api.py` bằng DTO; ADR-007 §3.2 cấm `relationship()` xuyên context và giữ `user_id`, `roadmap_id` làm “Cross-Context Tenant Correlation IDs”. Trong khi đó class doc tuyên bố “No Foreign Key Attributes”, nên `Task` không có `roadmapId` dù SRS §12 và FR-TASK-003 nói Task thuộc Roadmap.
- **Ghi chéo context.** ADR-007 §3.1 quy định mỗi bảng chỉ một context được ghi. Nhưng `DominoShiftEngine` và `PauseRecord` (evaluation) phải cập nhật `tasks.scheduled_date` (execution) và `roadmaps.status` (planning); bộ quét quá hạn (evaluation) tăng `tasks.reschedule_count` (execution). ADR-001 chỉ có cổng đọc (Read-Only Query Port) và sự kiện, không có cổng lệnh. Contract 1 của `import-linter` cũng cấm một domain service trong `evaluation.domain` nhận entity `Task`.
- **Cơ sở:** Vernon, tham chiếu giữa các aggregate bằng định danh; Evans, ranh giới bounded context.
- **Sửa:** chỉ giữ association *trong* context; quan hệ xuyên context vẽ bằng dependency «ref» kèm thuộc tính id (khớp ADR-007). Chọn một: (a) thêm cổng lệnh ghi qua chủ sở hữu bảng (ví dụ `ExecutionCommandPort.shiftTasks`), hoặc (b) chuyển Domino Shift và bộ quét quá hạn về context sở hữu `tasks`.

### C3 \[QT · CLS\] Quan hệ dư, áp dụng nguyên tắc không nhất quán

- Mục 4.1 của class doc lược bỏ `Roadmap–Task` vì “suy diễn”, nhưng vẫn giữ `User–Roadmap` (đã có User→Goal→Roadmap) và `Roadmap–StudySession` (đã có Session→Task→Milestone→Roadmap).
- `Goal 1..* Roadmap` không UC nào dùng; `Goal` và `Roadmap` trùng `title`, `targetDate` nên UC-09 3a (“đổi tên mục tiêu hoặc hạn chót”) không rõ sửa lớp nào. Cân nhắc gộp `Goal` vào `Roadmap`.
- `Roadmap 1 – * StudySession` mâu thuẫn FR-SESSION-001 (chọn từ 1 task trở lên) và FR-SCHEDULE-001 (lịch hiển thị nhiều roadmap): một phiên có thể chứa task của nhiều roadmap. Hoặc UC-11 cấm trộn roadmap, hoặc bỏ liên kết trực tiếp.
- **Cơ sở:** Larman, không thêm quan hệ dư hoặc suy diễn được; dùng derived `/` khi cần.

### C4 \[QT · CLS\] Composition và aggregation dùng chưa đúng

- `Roadmap *-- ScheduleChangeLog` (và `PauseRecord`): composition nghĩa là xóa Roadmap thì xóa luôn log, nhưng log được mô tả là kiểm toán bất biến và liên kết Task là `SET NULL`, tức dữ liệu kiểm toán phải sống lâu hơn thực thể nó ghi lại. Vòng đời không nhất quán.
- `OfficialSchedule o-- Task`: lý do “schedule bị thay thế” mâu thuẫn OS-03 (Merge / Future Shift, mỗi roadmap một schedule); tư cách thành viên suy ra được từ `scheduledDate != null`, nên trạng thái bị nhân đôi và dễ lệch. UML 2.5.1 nói shared aggregation không có ngữ nghĩa chính xác; Fowler (*UML Distilled*) khuyên tránh. Thay bằng association suy diễn `/scheduledTasks`.

### C5 \[QT · CLS\] Trách nhiệm trùng giữa entity và domain service

- DAG có ba nơi: `Task.hasDependencyCycle`, `TaskDependency.validateNoCycle`, `DagCycleValidator.canAddEdge`. Lịch rảnh có ba cặp trùng 1–1: `AvailabilityProfile.validateHardCeiling/validateModeBWindow/deductBusyIntervals` với `HybridAvailabilityRuleEngine`. Domino có ba nơi: `Roadmap.applyDominoShift`, `PauseRecord.calculateShiftedDays`, `DominoShiftEngine`. `Roadmap` ôm khoảng 8 nghiệp vụ.
- Logic ứng dụng và hạ tầng nằm trong entity: `Goal.sanitizePromptContext()`, `StudyNote.sanitizeForAIReview()`, `OfficialSchedule.exportIcsEvents(): String` (serialization RFC 5545).
- `ScheduleProposal.proposalData: Object` nhưng `DagCycleValidator` nhận `Task[]`: thiếu lớp `ProposedTask`.
- **Cơ sở:** GRASP (High Cohesion, Information Expert); Evans, dùng domain service khi thao tác *không thuộc* entity nào, không phải vừa ở entity vừa ở service.

### C6 \[QT · CLS\] Lẫn hạ tầng và thiết kế CSDL vào mô hình miền

- `OutboxEvent`, `ProcessedEvent` là pattern hạ tầng (Transactional Outbox, Idempotent Consumer), không phải khái niệm nghiệp vụ. Gọi gói đó là “Shared Kernel” cũng sai nghĩa DDD (chia sẻ một phần *mô hình miền* giữa hai context).
- “Bounded Context” ở đây là bốn package cùng một mô hình và nối trực tiếp, tức module chứ chưa phải context.
- Chi tiết `ON DELETE`, ánh xạ 3NF, UUID thuộc ERD, không thuộc class diagram miền. Kiểu `Object` và `String` “ma thuật” (`actionType`, `operationType`, `status = "SUCCESS"`, `gatewayProvider`) trái với tuyên bố 18 enum ánh xạ CHECK. Stereotype `<<entity>>` chỉ xuất hiện đúng 1 lần trong puml (ở dòng chú thích).
- **Sửa:** tách *class diagram miền (phân tích)* khỏi *ERD / thiết kế persistence*.

### C7 \[N · CLS\] Nhỏ

- `User *-- LearnerProfile 0..1` nhưng UC-01 luôn tạo hồ sơ: bản số đúng là `1`.
- `ChangeActorType` đặt sai tên; `AIQuota.applyTierLimit` trùng `User.upgradeTier`; `peakProductivitySlots: String[1..*]` thiếu enum; bản Mermaid chỉ có 29 class, thiếu 18 enum nên không tương đương bản PlantUML.
- Metric `adherenceRate` chưa xác định đơn vị: FR-REPORT-001 tính theo “buổi học”, KPI-3 tính theo “ngày”, trong khi lịch chính thức xếp theo task, không có thực thể “buổi”.

## 6. Mâu thuẫn trong SRS và ADR cần chốt trước khi sửa diagram

Các điểm này truyền xuống UC và class, nên phải quyết ở nguồn:

| # | Mâu thuẫn | Vị trí |
| --- | --- | --- |
| 1 | AI không bao giờ ghi vào Official Schedule, trần giờ không bao giờ vượt, nhưng AI Reschedule ghi lịch trực tiếp, chỉ kiểm “cơ bản” | BUSR-02, BUSR-03 và FR-ADAPT-002; ADR-009 §3.1.1 |
| 2 | Không hoàn tiền nhưng có trạng thái `REFUNDED` | SRS §2.5 và problem-definition §6.2, với SRS §12 |
| 3 | Sau 2 lần retry vi phạm: trả bản nháp có cảnh báo, hay báo lỗi và hiện nút thủ công, hay hủy và RELEASE quota | FR-PLAN-005, FR-AI-001, ADR-009 §3.2 |
| 4 | Mã quy tắc bị trích sai: ≤120 phút gắn BUSR-04 (đó là Soft Overflow); DAG gắn BUSR-05 (đó là đa lộ trình, DAG là FR-TASK-003) | FR-PLAN-005; ADR-009 |
| 5 | Tham chiếu ADR sai: gate trỏ ADR-003/008 (đúng là ADR-009); lock và upsert của hồ sơ trỏ ADR-007/008 | FR-PLAN-005, FR-PROFILE-001 |
| 6 | Số UC sai: hoàn thành phiên ghi UC-10 (đúng UC-11); slice `tasks/` gắn UC-09 (UC-09 là danh mục lộ trình) | ADR-010; ADR-003 |
| 7 | Thời hạn phiên đăng nhập | FR-ADM-001 và ADR-008 |
| 8 | Hồ sơ thói quen: SRS lấy phiên `COMPLETED` trong 30 ngày, kích hoạt sau mỗi 5 phiên hoặc hằng tuần; ADR-010 lấy 14 ngày, cập nhật ở mỗi sự kiện hoàn thành | FR-PROFILE-001 và ADR-010 §3.1 |
| 9 | UC-18 có hay không có Payment Gateway | SRS §3.2 và actors-and-personas §2.6 |
| 10 | SRS tự nhận “trung lập công nghệ” nhưng còn nhiều tên công nghệ; ADR-003 thêm “quên mật khẩu” ngoài SRS | SRS v1.2; ADR-003 |

## 7. Lộ trình sửa đề xuất

**P0: sửa SRS và chốt quyết định (làm trước, vì mọi thứ phía dưới phụ thuộc)**

1. Giải quyết mâu thuẫn BUSR-02/03 và FR-ADAPT-002 (chọn phương án (a) hoặc (b) ở U1).
2. Sửa SRS §3.2: UC-08 độc lập; UC-04/05 gộp; UC-12 gộp vào UC-11; thêm actor Scheduler và Email; chốt Gateway của UC-18.
3. Chốt tập `PaymentStatus`, giới hạn thời lượng task (AI và thủ công), hành vi sau retry, phiên đăng nhập, nơi lưu OAuth token, audit log.
4. Thêm FR cho lưu trữ lộ trình (UC-09), hạ cấp/hết hạn Premium, sửa/xóa task; quyết định có đưa “quên mật khẩu” và cập nhật múi giờ vào phạm vi hay không.

**P1: Use case**

5. Vẽ lại master và module diagram: thêm association Learner còn thiếu, actor hệ thống, UC hệ thống, include “Kiểm định lịch”.
6. Tách UC-02, 03, 10, 13, 18; rút UC-06/07 xuống tối đa 9 bước.
7. Dọn rò rỉ thiết kế; thêm mục “Thuộc tính AI” cho UC-06, 07, 15, 17; điền Open Questions thật thay cho “Không có”.

**P2: Class diagram**

8. Bỏ association xuyên context; thêm thuộc tính id theo ADR-007; chọn phương án C2 (a) hoặc (b).
9. Bổ sung: `CalendarConnection`, `AdminAuditLog`, `SecurityAuditLog` (nếu giữ yêu cầu), ngữ cảnh làm rõ của `Goal`, chế độ đồng hồ, `preferredPeriod`, `expiresAt`, `EXPIRED`, `ProposedTask`, quan hệ cha–con của `Task`, `AccountStatus`.
10. Loại bỏ: `REFUNDED`, `ReviewCycle.MILESTONE`, `CALENDAR_SYNC`, `isMandatory`, `GENERAL` (nếu không đưa vào FR), `Outbox/Processed` khỏi mô hình miền; đổi `ChangeActorType` thành `ChangeTriggerType`.
11. Dọn trách nhiệm trùng (C5); sửa composition/aggregation (C4); gộp hoặc làm rõ `Goal`–`Roadmap` (C3).

**P3: Vệ sinh**

12. Xóa ký tự lạ, sửa tham chiếu BR/ADR/UC sai, thay link `file:///`, bỏ phần tự chấm điểm và checklist tự tick, đồng bộ lại ma trận §6.1 và bản Mermaid.

**Tiêu chí hoàn tất (kiểm lại bằng script):** tên bảng và enum khớp giữa SRS, ADR, class và UC spec; mọi UC có primary actor trên diagram; 0 ký tự lạ; 0 từ khóa thiết kế trong luồng chính; mọi UC có từ 3 đến 9 bước; mỗi FR có UC nhà hoặc được ghi rõ là yêu cầu xuyên suốt.

## 8. Điểm làm tốt (đã xác minh)

- Hướng mũi tên `include`/`extend` trong PlantUML đúng chiều; actor chính bên trái, actor phụ bên phải.
- Tách `Schedule Proposal` khỏi `Official Schedule` ở UC-06/07 là thiết kế Human-in-the-Loop chuẩn.
- Luồng ngoại lệ phong phú (hết quota, timeout, webhook giả mạo, chu trình DAG, mất kết nối); NFR có số đo; mã BR/OS/EVAL truy vết được.
- `<<extend>>` UC-15 → UC-14 dùng đúng.
- Con số khớp: 29 class + 18 enum = 47 classifier; SRS §16 phủ đủ 19 UC.
- SRS đã gom 8 quyết định mở OS-01…08 có phê duyệt rõ ràng, và các ADR có phần phương án thay thế và kiểm chứng tự động, đây là nền tốt để sửa tiếp.
