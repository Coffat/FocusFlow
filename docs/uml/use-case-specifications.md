# FocusFlow — Tài liệu Đặc tả Ca sử dụng Chi tiết (Use Case Specifications)

| Thông tin tài liệu | Chi tiết |
|---|---|
| **Dự án** | FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI |
| **Cấp độ tài liệu** | Đặc tả Ca sử dụng Chi tiết Toàn diện (Detailed Use Case Specifications — 47 Use Cases Lõi: `UC-ACC-01..11`, `UC-PLAN-01..10`, `UC-EXEC-01..09`, `UC-ADAPT-01..10`, `UC-ADM-01..07`) |
| **Phiên bản** | v5.2 (Chuẩn hóa Baseline Post-CCB — Đồng bộ SRS v1.4 & 43 FRs) |
| **Tiêu chuẩn kỹ thuật** | OMG UML 2.5.1 (Clause 18 — Use Cases), Cockburn Goal-Level (User-Goal & Subfunction), ISO/IEC/IEEE 29148:2018 (Requirements Engineering) |
| **Trạng thái đối chiếu** | Hoàn tất tích hợp thiết kế FocusFlow Learning Intelligence Harness (Zimmerman 3-phase SRL, Durable Workflow Runs, Decoupled Roadmap vs ScheduleBlocks, Structured Learner Memory Governance, What-if Planning Simulation, RAG Knowledge Ingestion, Mistake Intelligence & Skill Mastery) |
| **Tài liệu liên kết** | • Đặc tả Yêu cầu Phần mềm (SRS v1.3): [`srs-v1.3.md`](../srs/srs-v1.3.md)<br>• Bản thiết kế kiến trúc Use Case lõi: [`use-case-redesign-blueprint.md`](../../brain/b362da16-5f49-420f-8d9f-e6fff96d28bf/use-case-redesign-blueprint.md)<br>• Sơ đồ Ca sử dụng Tổng quan: [`use-case-diagram.puml`](./use-cases/use-case-diagram.puml)<br>• Sơ đồ Phân hệ 1..5: [`uc-mod-01-account-profile-billing.puml`](./use-cases/uc-mod-01-account-profile-billing.puml) .. [`uc-mod-05-system-administration.puml`](./use-cases/uc-mod-05-system-administration.puml) |

---

## MỤC LỤC

1. [Tóm tắt Phạm vi & Giả định (Scope Summary & Assumptions)](#1-tóm-tắt-phạm-vi--giả-định-scope-summary--assumptions)
   - 1.1. Hệ thống đích & Khung lý thuyết SRL
   - 1.2. Thống nhất 8 Quyết định Kiến trúc & Nghiệp vụ (D0 – D7)
   - 1.3. Nguyên tắc Quản trị AI & Quyền tự quyết của Người học (Human-in-the-Loop)
   - 1.4. Quy ước Múi giờ IANA & Trạng thái Dẫn xuất Động
   - 1.5. Lý giải Chuẩn mực OMG UML 2.5.1 về Ranh giới Hệ thống, Thành phần Nội bộ và Sự kiện Thời gian (`TimeEvent`)
2. [Bảng Tác nhân Hệ thống (System Actors Table — 8 Tác nhân Chuẩn hóa ACT-00..ACT-07)](#2-bảng-tác-nhân-hệ-thống-system-actors-table--8-tác-nhân-chuẩn-hóa-act-00act-07)
3. [Danh mục 47 Use Cases Lõi Chuẩn hóa (Master 47 Core Use Case Inventory)](#3-danh-mục-47-use-cases-lõi-chuẩn-hóa-master-47-core-use-case-inventory)
   - 3.0. [Bảng đối chiếu Truy vết Toàn diện Mã Use Case SRS v1.4 (UC-01..UC-28) ↔ Mã Chuẩn hóa Domain-Prefixed (v5.2)](#30-bảng-đối-chiếu-truy-vết-toàn-diện-mã-use-case-srs-v14-uc-01uc-28--mã-chuẩn-hóa-domain-prefixed-v52)
4. [Kiến trúc Sơ đồ Use Case (Use Case Diagrams Reference)](#4-kiến-trúc-sơ-đồ-use-case-use-case-diagrams-reference)
5. [Đặc tả Chi tiết Phân tầng Từng Use Case](#5-đặc-tả-chi-tiết-phân-tầng-từng-use-case)
   - **Phân hệ 1: Quản lý Tài khoản, Hồ sơ & Gói dịch vụ** (`UC-ACC-01`, `UC-ACC-02`, `UC-ACC-03`, `UC-ACC-04`, `UC-ACC-05`, `UC-ACC-06`, `UC-ACC-07`, `UC-ACC-08`, `UC-ACC-09`, `UC-ACC-10`, `UC-ACC-11`)
   - **Phân hệ 2: Khởi tạo & Lập kế hoạch Lộ trình** (`UC-PLAN-01`, `UC-PLAN-02`, `UC-PLAN-03`, `UC-PLAN-04`, `UC-PLAN-05`, `UC-PLAN-06`, `UC-PLAN-07`, `UC-PLAN-08`, `UC-PLAN-09`, `UC-PLAN-10`)
   - **Phân hệ 3: Thực thi Học tập & Tích hợp Lịch ngoại vi** (`UC-EXEC-01`, `UC-EXEC-02`, `UC-EXEC-03`, `UC-EXEC-04`, `UC-EXEC-05`, `UC-EXEC-06`, `UC-EXEC-07`, `UC-EXEC-08`, `UC-EXEC-09`)
   - **Phân hệ 4: Phân tích Tiến độ, Kiểm chứng Năng lực & Thích ứng** (`UC-ADAPT-01`, `UC-ADAPT-02`, `UC-ADAPT-03`, `UC-ADAPT-04`, `UC-ADAPT-05`, `UC-ADAPT-06`, `UC-ADAPT-07`, `UC-ADAPT-08`, `UC-ADAPT-09`, `UC-ADAPT-10`)
   - **Phân hệ 5: Quản trị Hệ thống & Vận hành** (`UC-ADM-01`, `UC-ADM-02`, `UC-ADM-03`, `UC-ADM-04`, `UC-ADM-05`, `UC-ADM-06`, `UC-ADM-07`)
6. [Ma trận Truy vết Toàn cục (Master Traceability Matrix) & Rà soát Chất lượng](#6-ma-trận-truy-vết-toàn-cục-master-traceability-matrix--rà-soát-chất-lượng)

---

## 1. Tóm tắt Phạm vi & Giả định (Scope Summary & Assumptions)

### 1.1. Hệ thống đích & Khung lý thuyết SRL
- **Hệ thống đích (System Under Design — SuD)**: **FocusFlow** là nền tảng điều hành tự học thích ứng (Adaptive Self-Learning Operating System) hỗ trợ người học khép kín toàn diện chu trình Tự học có điều tiết theo mô hình **Zimmerman SRL (2002)** thông qua **5 vòng lặp vận hành thực chiến (*Understand -> Plan -> Execute -> Prove -> Adapt*)**:
  1. *Understand (Thấu hiểu mục tiêu)*: Phân tích mục tiêu học tập, đối chiếu kho khái niệm tri thức chuẩn xác và làm rõ ngữ cảnh thông qua tương tác AI (`UC-PLAN-01`).
  2. *Plan (Lập kế hoạch thích ứng)*: Tạo danh sách bài học bằng AI (`UC-PLAN-02`), xếp lịch tối ưu theo nhịp năng lượng nhận thức và khung giờ rảnh khả dụng (`UC-PLAN-03`, `UC-PLAN-04`), bảo đảm 100% tuân thủ cổng kiểm định tất định (`UC-PLAN-09`).
  3. *Execute (Thực thi tập trung)*: Vận hành không gian học tập Focus Mode (Thực hiện phiên học tập trung (Tiêu chuẩn & Rút gọn) Pomodoro/Stopwatch hoặc MVS 10–15 phút, `UC-EXEC-04`), tự động lưu phiên học khi mất kết nối (`UC-EXEC-06`) và kết nối/đồng bộ lịch ngoại vi (`UC-EXEC-07`, `UC-EXEC-08`, `UC-EXEC-09`).
  4. *Prove (Chứng minh năng lực)*: Khắc phục điểm mù và triệt tiêu học vẹt thông qua làm bài kiểm tra cột mốc (`UC-ADAPT-02`), bắt buộc đúc kết Key Takeaways làm bằng chứng học tập khách quan (`UC-EXEC-03`, `UC-EXEC-04`).
  5. *Adapt (Thích ứng có kiểm soát)*: Báo cáo chỉ số Bắc đẩu WRLS (`UC-ADAPT-01`), Đánh giá học tập cuối tuần (`UC-ADAPT-03`), Tiếp tục lộ trình và dời lịch bù ngày dừng (`UC-ADAPT-05`), dời lịch bài quá hạn bằng AI trong hạn mức ngân sách tuần (`UC-ADAPT-06`) và Khôi phục lộ trình bị gián đoạn lâu ngày (`UC-ADAPT-07`).

### 1.2. Thống nhất 8 Quyết định Kiến trúc & Nghiệp vụ (D0 – D7)
1. **D0 (Quy mô danh mục 47 Use Cases Lõi — Core Baseline)**: Tách triệt để các Use Case đa mục tiêu có luồng chính mang nhánh "hoặc" (A1) thành các ca sử dụng đơn mục tiêu độc lập. Giữ các hành vi phụ thuộc, có điều kiện hoặc tùy chọn (như đăng xuất, xem lịch sử thanh toán, bù đúc kết, ngắt kết nối lịch) dưới dạng luồng thay thế/luồng phụ trong Use Case gốc tương ứng.
2. **D1 (Làm mới Ngân sách dời lịch tuần — Weekly Reschedule Budget)**: Áp dụng cơ chế kép an toàn: Sự kiện thời gian tự động (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ nền (`UC-ADAPT-10`) đặt lại ngân sách `weekly_reschedule_used = 0` (cấp đủ 3 lượt) vào đúng `00:00 Thứ Hai` theo múi giờ cá nhân của người học. Đánh giá học tập cuối tuần (`UC-ADAPT-03`) được phép kích hoạt sớm quyền làm mới ngân sách khi người học hoàn tất phản tư, nhưng tối đa 1 lần trong mỗi tuần dương lịch (kiểm tra `last_reset_week`). Ngân sách dời lịch không bao giờ cộng dồn vượt quá 3 lượt.
3. **D2 (Ground Truth & Kiểm duyệt Khái niệm trong Prove Mode)**: Áp dụng cơ chế 2 cấp linh hoạt tại `UC-ADAPT-02` (Làm bài kiểm tra cột mốc): Nếu cột mốc gắn với khái niệm đã được duyệt (`VERIFIED`), hệ thống sử dụng kho khái niệm làm Ground Truth chuẩn mực. Nếu cột mốc gắn với khái niệm do AI mới khởi tạo (`UNVERIFIED`), hệ thống chuyển sang đối chiếu nội dung thực tế của các bài học đã hoàn thành và bản ghi đúc kết của người học thay vì coi AI là chân lý tuyệt đối. Quyền thẩm định và nâng cấp khái niệm lên `VERIFIED` thuộc về Quản trị viên (`UC-ADM-07`). Mục tiêu của Prove Mode là giảm thiểu tối đa gian lận và triệt tiêu tâm lý học vẹt.
4. **D3 (Máy trạng thái thanh toán & Cho phép EXPIRED -> PAID có kiểm soát)**: Cho phép chuyển trạng thái `EXPIRED -> PAID` khi nhận được thông báo Webhook hợp lệ (`UC-ACC-07`): nếu chữ ký xác thực HMAC-SHA256 hợp lệ và số tiền khớp đúng 99.000 VNĐ, hệ thống vẫn kích hoạt nâng gói Premium, ghi nhận cờ đối soát trễ `late_payment_reconciled = true` và ghi nhật ký kiểm toán. Quản trị viên (`UC-ADM-04`) được phép đối soát thủ công chuyển đơn `EXPIRED` sang `PAID` khi có mã tham chiếu ngân hàng và lý do xác minh hợp lệ.
5. **D4 (Bản chất thuần tính động của `isOverdue` và `isDormant`)**: Trạng thái quá hạn (`isOverdue`) và trạng thái ngủ đông (`isDormant`) là các giá trị dẫn xuất động (Derived-only) được tính toán thời gian thực theo múi giờ người dùng, không lưu trữ dạng cờ boolean vật lý trong cơ sở dữ liệu. Khi hoàn thành Khôi phục lộ trình bị gián đoạn lâu ngày (`UC-ADAPT-07`), hệ thống ghi nhận mốc hoạt động học tập mới nhất `last_study_activity_at = NOW()`, từ đó giải phóng ngay lập tức trạng thái ngủ đông mà không cần các bước gán/xóa cờ thủ công.
6. **D5 (Hoàn thành nhanh bắt buộc đúc kết tối thiểu — Quick Complete)**: Tại `UC-EXEC-03`, người học được phép đánh dấu hoàn thành bài học nhanh mà không cần khởi động đồng hồ bấm giờ, nhưng **bắt buộc** phải nhập đúc kết cốt lõi (Key Takeaway $\ge 30$ ký tự) và độ tự tin (1..5). Bản ghi đúc kết này được lưu trữ gắn với bài học để tạo bằng chứng đầu vào bắt buộc cho bài kiểm tra cột mốc (`UC-ADAPT-02`).
7. **D6 (Xác minh Email mềm & Đặt lại mật khẩu)**: Áp dụng cơ chế xác minh email mềm (Soft-verification) tại `UC-ACC-01`: người học có thể đăng nhập và trải nghiệm học tập ngay sau khi đăng ký; hệ thống hiển thị thông báo nhắc nhở xác minh email trên giao diện. Bổ sung `UC-ACC-03` (Đặt lại mật khẩu) qua liên kết an toàn có chữ ký điện tử gửi về email người dùng với thời hạn 15 phút.
8. **D7 (Giá gói dịch vụ, Thời hạn & Cơ chế Gia hạn Premium)**: Chuẩn hóa mức phí gói Premium là **99.000 VNĐ / chu kỳ 30 ngày**. Mở rộng `UC-ACC-06` cho phép cả người dùng đang sở hữu gói Premium mua gia hạn sớm, thời hạn gói được cộng dồn theo công thức `premium_expires_at = MAX(premium_expires_at, NOW()) + 30 ngày`. Nghi thức đối soát thủ công tại `UC-ADM-04` bắt buộc phải nhập mã giao dịch ngân hàng và lý do can thiệp.

### 1.3. Nguyên tắc Quản trị AI & Quyền tự quyết của Người học (Human-in-the-Loop)
- **Không tự động áp dụng (No Auto-Apply)**: Nhà cung cấp dịch vụ LLM (`External LLM Provider`) hoạt động như một tác nhân phụ trợ (Secondary Actor), tuyệt đối không có quyền tự ý cập nhật Lịch học chính thức (`OfficialSchedule`). Mọi kế hoạch do AI sinh ra (`UC-PLAN-02`, `UC-PLAN-03`, `UC-ADAPT-06`, `UC-ADAPT-07`) chỉ tồn tại dưới dạng Bản đề xuất lịch học (`ScheduleProposal`) ở trạng thái nháp (`DRAFT`). Chỉ khi người học chủ động xem xét, kiểm tra bản so sánh khác biệt (Diff Preview) và nhấn **Áp dụng (Apply)** thì hệ thống mới cập nhật vào lịch chính thức.
- **Bảo vệ hạn ngạch 2 pha (Two-Phase Quota Guard)**: Thao tác giữ chỗ hạn ngạch (RESERVE) chỉ diễn ra ngay trước thời điểm phát lệnh gọi AI (Just-In-Time Reservation), không giữ chỗ khi người dùng đang đọc màn hình hoặc điền biểu mẫu. Sau khi nhận kết quả thành công, hệ thống chuyển sang xác nhận trừ thực tế (COMMIT). Nếu cuộc gọi thất bại hoặc bị hủy, hạn ngạch được hoàn trả ngay lập tức (RELEASE). Bộ dọn dẹp tự động (`UC-ACC-08`) thu hồi bản ghi giữ chỗ quá hạn 5 phút (EXPIRE).
- **Ngắt cứng thời gian chờ & Dự phòng (Hard Timeout & Fallback)**: Mọi tương tác gọi AI đều áp dụng ngắt cứng tối đa 55 giây. Nếu quá thời gian chờ hoặc AI gặp sự cố sau tối đa 2 lần thử lại tự động, hệ thống chuyển sang chế độ dự phòng bằng logic tất định hoặc cho phép người học thao tác thủ công mà không làm gián đoạn trải nghiệm người dùng.

### 1.4. Quy ước Múi giờ IANA & Trạng thái Dẫn xuất Động
1. **Quy ước múi giờ IANA**: Toàn bộ mốc thời gian hệ thống được lưu trữ nội bộ theo chuẩn UTC. Khi hiển thị, tính toán khung thời gian rảnh, xác định ranh giới bắt đầu ngày mới (00:00) và phát hiện bài quá hạn, hệ thống luôn quy chiếu động theo chuỗi múi giờ IANA được cấu hình trong hồ sơ cá nhân của người học (mặc định: `Asia/Ho_Chi_Minh`).
2. **Đơn phiên học duy nhất (Single Active Session Invariant)**: Tại mỗi thời điểm, một người học chỉ được phép mở duy nhất **01 phiên học tập trung đang hoạt động** trên toàn hệ thống. Mọi yêu cầu mở phiên học mới khi đang có phiên chưa kết thúc đều bị chặn hoặc yêu cầu chốt phiên cũ.
3. **Đồng bộ lịch ngoại vi an toàn (Non-Destructive Inbound Sync)**: Chiều nạp dữ liệu từ Dịch vụ Lịch ngoại vi (`UC-EXEC-08`) chỉ trích xuất thông tin khoảng thời gian bận (`Free/Busy`) trong 14 ngày tới để khấu trừ quỹ thời gian rảnh khả dụng, tuyệt đối không can thiệp, xóa bỏ hay tự ý dời các bài học đã có trong FocusFlow.

### 1.5. Lý giải Chuẩn mực OMG UML 2.5.1 về Ranh giới Hệ thống, Thành phần Nội bộ và Sự kiện Thời gian (`TimeEvent`)
Theo chuẩn **OMG UML 2.5.1 (Clause 18 — Use Cases)**, một Tác nhân (Actor) bắt buộc phải là một phân loại ngoại vi (external classifier — người dùng con người hoặc hệ thống bên ngoài) nằm hoàn toàn **bên ngoài** ranh giới của Hệ thống đang thiết kế (System Under Design — SuD) và trực tiếp trao đổi thông điệp với SuD.

Nhằm bảo toàn tính toàn vẹn 100% của nguyên tắc ranh giới hộp đen (Black-Box System Boundary), thiết kế tuân thủ nghiêm ngặt hai quy tắc mô hình hóa cốt lõi:
1. **Thành phần hạ tầng nội bộ tuyệt đối không phải là Use Case Actor**: Các thành phần kỹ thuật như **Cơ sở dữ liệu (`PostgreSQL`), tiến trình lập lịch/worker nền (`Taskiq` worker/scheduler daemon), bộ nhớ đệm (`Redis`), hay bộ điều phối AI nội bộ (`Internal AI Harness`)** nằm hoàn toàn **bên trong** ranh giới hệ thống (System Boundary). Chúng được mô hình hóa tại các sơ đồ kiến trúc C4 Container/Component, tuyệt đối không xuất hiện dưới dạng Actor trên Sơ đồ Use Case.
2. **Sự kiện thời gian (`TimeEvent`) là điều kiện kích hoạt (`Trigger`), không phải Actor trên Sơ đồ Use Case**: Theo ngữ nghĩa chặt chẽ của **OMG UML 2.5.1**, thời gian (`TimeEvent`) là một điều kiện kích hoạt sự kiện (`Trigger: TimeEvent / Định kỳ tự động`), không phải là một classifier Tác nhân ngoại vi trên Sơ đồ Use Case. Do đó, 08 ca sử dụng kích hoạt định kỳ theo thời gian (`UC-ACC-08`, `UC-ACC-09`, `UC-ACC-10`, `UC-EXEC-06`, `UC-EXEC-08`, `UC-ADAPT-08`, `UC-ADAPT-09`, `UC-ADAPT-10`) được liên kết trực tiếp trên Sơ đồ Use Case với **Tác nhân Thụ hưởng Chính (Primary Stakeholder / Beneficiary Actors)** nhận giá trị bảo vệ từ ca sử dụng đó (`Learner — ACT-02` và `Administrator — ACT-03` đối với `UC-ACC-08`; `Learner — ACT-02` đối với 7 ca sử dụng định kỳ còn lại) cùng với các **Tác nhân Hệ thống Ngoại vi (External System Actors)** tham gia tương tác (`External Calendar Service — ACT-06` đối với `UC-EXEC-08`, `Email Notification Service — ACT-07` đối với `UC-ADAPT-08`), trong khi thuộc tính `Trigger` trong bảng đặc tả chi tiết ghi nhận tường minh lịch trình `TimeEvent`.


## 2. Bảng Tác nhân Hệ thống (System Actors Table — 8 Tác nhân Chuẩn hóa ACT-00..ACT-07)

| Mã Actor | Tên Tác nhân | Phân loại | Mô tả & Trách nhiệm chuẩn hóa trong hệ thống (Đồng bộ SRS v1.4 §3.1) |
|---|---|---|---|
| **ACT-00** | **Khách vãng lai (`Guest / Anonymous User`)** | Primary | Người dùng chưa đăng ký tài khoản, truy cập vào ứng dụng qua giao diện web công khai để tìm hiểu tính năng và khởi xướng ca sử dụng đăng ký tài khoản mới (`UC-ACC-01`). |
| **ACT-01** | **Người dùng đã đăng ký (`Registered User`)** | Primary (Abstract) | Tác nhân trừu tượng đại diện cho mọi cá nhân đã sở hữu tài khoản hợp lệ trong hệ thống. Đóng vai trò lớp tổng quát hóa (Generalization) cho `Learner` (`ACT-02`) và `Administrator` (`ACT-03`). Khởi xướng trực tiếp các ca sử dụng xác thực chung: `UC-ACC-02` (Đăng nhập & quản lý phiên) và `UC-ACC-03` (Đặt lại mật khẩu qua thư điện tử). *(Thay thế nhãn sai Authenticated User)*. |
| **ACT-02** | **Người học (`Learner`)** | Primary | Tác nhân kế thừa `Registered User` (`Learner --|> Registered User`). Đóng vai trò trung tâm trong toàn bộ chu trình tự học SRL: khởi tạo mục tiêu, cấu hình thời gian rảnh, quản lý hồ sơ và bộ nhớ người học (`UC-ACC-11`), xóa tài khoản theo GDPR (`UC-ACC-05`), tạo lộ trình (thủ công hoặc AI), thực thi phiên học tập trung, ghi chép đúc kết, thực hiện kiểm chứng năng lực (Prove Mode), chốt tuần và thích ứng lộ trình khi gặp gián đoạn. Đồng thời đóng vai trò **Tác nhân chính / Tác nhân thụ hưởng (Primary / Beneficiary Actor)** đối với 8 ca sử dụng tự động theo sự kiện thời gian (`OMG UML 2.5.1 TimeEvent`): thu hồi giữ chỗ hạn ngạch quá hạn (`UC-ACC-08`), làm mới hạn ngạch AI chu kỳ tháng (`UC-ACC-09`), hạ cấp gói cước hết hạn (`UC-ACC-10`), tự động chốt phiên học mất tín hiệu (`UC-EXEC-06`), định kỳ đồng bộ khoảng bận lịch ngoại vi (`UC-EXEC-08`), quét bài quá hạn và gửi email cảnh báo (`UC-ADAPT-08`), tổng hợp hồ sơ thói quen học tập (`UC-ADAPT-09`) và làm mới ngân sách dời lịch tuần (`UC-ADAPT-10`). |
| **ACT-03** | **Quản trị viên hệ thống (`Administrator`)** | Primary | Tác nhân kế thừa `Registered User` (`Administrator --|> Registered User`). Đóng vai trò giám sát và điều hành nền tảng: quản lý trạng thái tài khoản, can thiệp gói cước và hạn ngạch người dùng, đối soát giao dịch thanh toán thủ công, giám sát sức khỏe vận hành và thẩm định chuẩn hóa kho khái niệm tri thức (`UC-ADM-07`). Đồng thời đóng vai trò **Tác nhân chính / Tác nhân thụ hưởng (Primary / Beneficiary Actor)** trong ca sử dụng dọn bản ghi giữ chỗ hạn ngạch quá hạn và đơn thanh toán treo (`UC-ACC-08`) được kích hoạt định kỳ theo `TimeEvent`. |
| **ACT-04** | **Nhà cung cấp dịch vụ LLM (`External LLM Provider`)** | Secondary | Dịch vụ AI đám mây bên ngoài cung cấp khả năng suy luận ngôn ngữ tự nhiên có cấu trúc theo chuẩn JSON schema qua cổng kiểm soát an toàn và hạn ngạch: tạo khung cột mốc (`UC-PLAN-01`), phân rã nhiệm vụ (`UC-PLAN-02`), đề xuất xếp lịch tối ưu (`UC-PLAN-03`), gợi ý đúc kết tùy chọn trong phiên học (`UC-EXEC-04`), chia nhỏ bài học micro-stepping (`UC-EXEC-05`), truy hồi kiểm chứng năng lực (`UC-ADAPT-02`), phân tích phản tư chốt tuần (`UC-ADAPT-03`), đề xuất dời lịch bài quá hạn (`UC-ADAPT-06`) và tái thiết lộ trình ngủ đông (`UC-ADAPT-07`). |
| **ACT-05** | **Cổng thanh toán (`Payment Gateway`)** | Secondary & Primary | Đóng vai trò tác nhân phụ trợ (Secondary) cung cấp liên kết thanh toán và mã QR giao dịch trong luồng tạo đơn (`UC-ACC-06`) và cung cấp dữ liệu đối soát giao dịch (`UC-ADM-04`); đồng thời đóng vai trò tác nhân chủ động (Primary) đẩy thông báo kết quả thanh toán bất đồng bộ (Webhook) vào hệ thống tại `UC-ACC-07`. |
| **ACT-06** | **Dịch vụ Lịch ngoại vi (`External Calendar Service`)** | Secondary | Nền tảng lịch cá nhân của người học (như Google Calendar) cung cấp danh sách các khoảng thời gian bận (`Free/Busy`) theo chiều Inbound (`UC-EXEC-07`, `UC-EXEC-08`) và tiếp nhận tiêu thụ luồng dữ liệu lịch học chính thức theo chiều Outbound qua định dạng `.ics` hoặc liên kết WebCal feed an toàn (`UC-EXEC-09`). |
| **ACT-07** | **Dịch vụ Email (`Email Notification Service`)** | Secondary | Hạ tầng chuyển phát thư điện tử giao dịch bên ngoài: tiếp nhận yêu cầu gửi liên kết xác minh mềm (`UC-ACC-01`), gửi liên kết đặt lại mật khẩu bảo mật (`UC-ACC-03`), gửi email tổng hợp bài học quá hạn và cảnh báo lộ trình ngủ đông định kỳ (`UC-ADAPT-08`). |

---

## 3. Danh mục 47 Use Cases Lõi Chuẩn hóa (Master 47 Core Use Case Inventory)

Hệ thống FocusFlow được tổ chức thành **47 Use Cases Lõi (Core Baseline)** phân bổ trên 5 Phân hệ nghiệp vụ theo chuẩn OMG UML 2.5.1 và cấu trúc Cockburn Goal-Level. Trong đó, 46 Use Cases thuộc mức **User-Goal / System-Goal Level** và duy nhất 01 Use Case thuộc mức **Subfunction Level** (`UC-PLAN-09`) dùng chung qua quan hệ `<<include>>`:

### 3.0. Bảng đối chiếu Truy vết Toàn diện Mã Use Case SRS v1.4 (UC-01..UC-28) ↔ Mã Chuẩn hóa Domain-Prefixed (v5.2)

Nhằm đảm bảo tính nhất quán tuyệt đối theo kiến trúc Context-First Modular Monolith và thuận tiện truy vết hai chiều (bidirectional traceability) giữa danh mục Use Case trong SRS v1.4 (`UC-01`..`UC-28`) và hệ thống mã hóa chuẩn hóa 47 Use Cases theo Bounded Context (v5.2), bảng dưới đây cung cấp ánh xạ chi tiết:

| STT | Mã Use Case SRS v1.4 (UC-01..UC-28) | Mã Mới (Domain-Prefixed) | Phân hệ (Bounded Context) | Tên Use Case | Phân loại & Mức độ (Goal-Level) | Quan hệ UML chính |
|---|---|---|---|---|---|---|
| **1** | **UC-01** | `UC-ACC-01` | Phân hệ 1: Account Context | Đăng ký tài khoản | User-Goal (Tầng 2) | Association |
| **2** | **UC-02** | `UC-ACC-02` | Phân hệ 1: Account Context | Đăng nhập | User-Goal (Tầng 2) | Association |
| **3** | Phát sinh từ FR-AUTH-004 (Tách từ UC-02) | `UC-ACC-03` | Phân hệ 1: Account Context | Đặt lại mật khẩu | User-Goal (Tầng 2) | Association |
| **4** | **UC-03** | `UC-ACC-04` | Phân hệ 1: Account Context | Cấu hình hồ sơ và thời gian rảnh | User-Goal (Tầng 2) | Association |
| **5** | Phát sinh từ FR-PROFILE-002 (GDPR Điều 17) | `UC-ACC-05` | Phân hệ 1: Account Context | Xóa tài khoản | User-Goal (Tầng 2) | Association |
| **6** | **UC-04** | `UC-ACC-06` | Phân hệ 1: Account Context | Nâng cấp hoặc gia hạn gói Premium | User-Goal (Tầng 1) | Association |
| **7** | **UC-05** | `UC-ACC-07` | Phân hệ 1: Account Context | Xử lý thông báo kết quả thanh toán (Webhook) | System-Goal (Tầng 1) | Association |
| **8** | **UC-06** (Dọn dẹp) | `UC-ACC-08` | Phân hệ 1: Account Context | Dọn bản ghi giữ chỗ và đơn thanh toán treo | System-Goal (Tầng 2) | Association |
| **9** | **UC-06** (Reset Quota) | `UC-ACC-09` | Phân hệ 1: Account Context | Làm mới hạn ngạch chu kỳ tháng | System-Goal (Tầng 2) | Association |
| **10** | **UC-06** (Downgrade) | `UC-ACC-10` | Phân hệ 1: Account Context | Hạ cấp gói dịch vụ hết hạn | System-Goal (Tầng 1) | Association |
| **11** | **UC-03** (Learner Memory) | `UC-ACC-11` | Phân hệ 1: Account Context | Quản lý ghi chú thói quen học tập | User-Goal (Tầng 2) | Association |
| **12** | **UC-07** | `UC-PLAN-01` | Phân hệ 2: Planning Context | Tạo khung lộ trình bằng AI | User-Goal (Tầng 1) | Association |
| **13** | **UC-08** (Decompose) | `UC-PLAN-02` | Phân hệ 2: Planning Context | Tạo danh sách bài học bằng AI | User-Goal (Tầng 1) | Association |
| **14** | **UC-08** (Schedule & Apply) | `UC-PLAN-03` | Phân hệ 2: Planning Context | Xếp lịch học bằng AI và áp dụng | User-Goal (Tầng 1) | `<<include>> UC-PLAN-09` |
| **15** | **UC-09** | `UC-PLAN-04` | Phân hệ 2: Planning Context | Tạo lộ trình thủ công | User-Goal (Tầng 1) | `<<include>> UC-PLAN-09` |
| **16** | **UC-10** (Update) | `UC-PLAN-05` | Phân hệ 2: Planning Context | Cập nhật thông tin lộ trình | User-Goal (Tầng 2) | Association |
| **17** | **UC-10** (Archive) | `UC-PLAN-06` | Phân hệ 2: Planning Context | Lưu trữ lộ trình (Archive) | User-Goal (Tầng 2) | Association |
| **18** | **UC-11** | `UC-PLAN-07` | Phân hệ 2: Planning Context | Quản lý công việc và quan hệ tiên quyết | User-Goal (Tầng 2) | `<<include>> UC-PLAN-09` |
| **19** | Phát sinh từ FR-PLAN-006 (Xem/lọc kho lộ trình) | `UC-PLAN-08` | Phân hệ 2: Planning Context | Quản lý cột mốc | User-Goal (Tầng 2) | Association |
| **20** | **UC-12** | `UC-PLAN-09` | Phân hệ 2: Planning Context | Kiểm định tính hợp lệ của lịch học | Subfunction (Tầng 1) | Được `<<include>>` bởi 9 UCs |
| **21** | **UC-08** (What-if) | `UC-PLAN-10` | Phân hệ 2: Planning Context | Mô phỏng kịch bản giả định (What-if Simulation) | User-Goal (Tầng 1) | `<<include>> UC-PLAN-09` |
| **22** | **UC-13** (Today Focus) | `UC-EXEC-01` | Phân hệ 3: Execution Context | Xem lịch học và Tiêu điểm Hôm nay | User-Goal (Tầng 2) | Association |
| **23** | **UC-13** (Reschedule) | `UC-EXEC-02` | Phân hệ 3: Execution Context | Dời lịch công việc thủ công | User-Goal (Tầng 1) | `<<include>> UC-PLAN-09` |
| **24** | **UC-13** (Quick Complete) | `UC-EXEC-03` | Phân hệ 3: Execution Context | Đánh dấu hoàn thành nhanh | User-Goal (Tầng 2) | Association |
| **25** | **UC-14** | `UC-EXEC-04` | Phân hệ 3: Execution Context | Thực hiện phiên học tập trung (Tiêu chuẩn & Rút gọn) | User-Goal (Tầng 1) | Association |
| **26** | Phát sinh từ FR-ADAPT-003 / FR-PLAN-002 (Micro-stepping) | `UC-EXEC-05` | Phân hệ 3: Execution Context | Chia nhỏ bài học bằng AI (Micro-stepping) | User-Goal (Tầng 2) | Association |
| **27** | **UC-16** | `UC-EXEC-06` | Phân hệ 3: Execution Context | Tự động lưu phiên học khi mất kết nối | System-Goal (Tầng 2) | Association |
| **28** | **UC-17** (Connect) | `UC-EXEC-07` | Phân hệ 3: Execution Context | Kết nối tài khoản Google Calendar | User-Goal (Tầng 2) | Association |
| **29** | **UC-17** (Periodic Sync) | `UC-EXEC-08` | Phân hệ 3: Execution Context | Tự động cập nhật thời gian bận từ Google Calendar | System-Goal (Tầng 2) | Association |
| **30** | **UC-18** | `UC-EXEC-09` | Phân hệ 3: Execution Context | Đồng bộ lịch học sang Google Calendar / ứng dụng lịch | User-Goal (Tầng 2) | Association |
| **31** | **UC-19** | `UC-ADAPT-01` | Phân hệ 4: Adaptation Context | Xem báo cáo tiến độ và bằng chứng học tập | User-Goal (Tầng 2) | Association |
| **32** | **UC-20** | `UC-ADAPT-02` | Phân hệ 4: Adaptation Context | Làm bài kiểm tra cột mốc | User-Goal (Tầng 1) | Association |
| **33** | **UC-21** | `UC-ADAPT-03` | Phân hệ 4: Adaptation Context | Đánh giá học tập cuối tuần | User-Goal (Tầng 1) | Association |
| **34** | **UC-22** (Pause) | `UC-ADAPT-04` | Phân hệ 4: Adaptation Context | Tạm dừng lộ trình | User-Goal (Tầng 2) | `<<include>> UC-PLAN-09` |
| **35** | **UC-22** (Resume) | `UC-ADAPT-05` | Phân hệ 4: Adaptation Context | Tiếp tục lộ trình và dời lịch bù ngày dừng | User-Goal (Tầng 1) | `<<include>> UC-PLAN-09` |
| **36** | **UC-23** | `UC-ADAPT-06` | Phân hệ 4: Adaptation Context | Dời lịch bằng AI cho bài quá hạn | User-Goal (Tầng 1) | `<<include>> UC-PLAN-09` |
| **37** | **UC-24** | `UC-ADAPT-07` | Phân hệ 4: Adaptation Context | Khôi phục lộ trình bị gián đoạn lâu ngày | User-Goal (Tầng 1) | `<<include>> UC-PLAN-09` |
| **38** | **UC-25** (Overdue Alert) | `UC-ADAPT-08` | Phân hệ 4: Adaptation Context | Gửi email nhắc nhở bài quá hạn và lộ trình gián đoạn | System-Goal (Tầng 2) | Association |
| **39** | **UC-25** (Profile Summary) | `UC-ADAPT-09` | Phân hệ 4: Adaptation Context | Tổng hợp hồ sơ thói quen học tập | System-Goal (Tầng 2) | Association |
| **40** | **UC-25** (Reset Budget) | `UC-ADAPT-10` | Phân hệ 4: Adaptation Context | Đặt lại ngân sách dời lịch hàng tuần | System-Goal (Tầng 2) | Association |
| **41** | **UC-26** (Lock/Unlock) | `UC-ADM-01` | Phân hệ 5: Administration Context | Khóa hoặc mở khóa tài khoản người dùng | User-Goal (Tầng 2) | Association |
| **42** | **UC-26** (Change Tier) | `UC-ADM-02` | Phân hệ 5: Administration Context | Đổi gói dịch vụ của người dùng | User-Goal (Tầng 2) | Association |
| **43** | **UC-26** (Adjust Quota) | `UC-ADM-03` | Phân hệ 5: Administration Context | Điều chỉnh hạn ngạch AI người dùng | User-Goal (Tầng 2) | Association |
| **44** | **UC-27** | `UC-ADM-04` | Phân hệ 5: Administration Context | Đối soát đơn thanh toán | User-Goal (Tầng 1) | Association |
| **45** | **UC-28** | `UC-ADM-05` | Phân hệ 5: Administration Context | Giám sát vận hành hệ thống và dịch vụ AI | User-Goal (Tầng 2) | Association |
| **46** | Tách từ UC-28 (Giám sát vận hành & hạ tầng) | `UC-ADM-06` | Phân hệ 5: Administration Context | Xem nhật ký kiểm toán quản trị | User-Goal (Tầng 2) | Association |
| **47** | Phát sinh từ FR-PLAN-001 / Domain Model (Quản lý khái niệm) | `UC-ADM-07` | Phân hệ 5: Administration Context | Quản lý kho khái niệm tri thức | User-Goal (Tầng 1) | Association |

---

### Phân hệ 1: Quản lý Tài khoản, Hồ sơ & Gói dịch vụ (11 Use Cases)
- **Sơ đồ 1A: Tài khoản & Xác thực**: `UC-ACC-01`, `UC-ACC-02`, `UC-ACC-03`, `UC-ACC-04`, `UC-ACC-05`, `UC-ACC-11`
- **Sơ đồ 1B: Thanh toán & Hạn ngạch**: `UC-ACC-06`, `UC-ACC-07`, `UC-ACC-08`, `UC-ACC-09`, `UC-ACC-10`

| Mã UC | Tên Use Case | Phân loại | Tác nhân chính | Tác nhân phụ | Quan hệ UML | Mục tiêu nghiệp vụ trọn vẹn |
|---|---|---|---|---|---|---|
| **UC-ACC-01** | Đăng ký tài khoản | User-Goal (Tầng 2) | Khách vãng lai (`ACT-00`) | Dịch vụ Email (`ACT-07`) | Association | Đăng ký tài khoản mới bằng email và mật khẩu, cấp định mức dùng thử FREE khởi đầu và kích hoạt xác minh mềm. |
| **UC-ACC-02** | Đăng nhập | User-Goal (Tầng 2) | Registered User (`ACT-01`) | — | Association | Xác thực danh tính người dùng, cấp cặp mã xác thực an toàn HttpOnly để mở phiên làm việc hợp lệ. *(Đăng xuất là luồng phụ 2a)*. |
| **UC-ACC-03** | Đặt lại mật khẩu | User-Goal (Tầng 2) | Registered User (`ACT-01`) | Dịch vụ Email (`ACT-07`) | Association | Tiếp nhận yêu cầu quên mật khẩu, gửi liên kết signed an toàn qua email và cập nhật mật khẩu mới khi có mã hợp lệ. |
| **UC-ACC-04** | Cấu hình hồ sơ và thời gian rảnh | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Cập nhật thông tin cá nhân, múi giờ IANA, thiết lập khung giờ rảnh theo Chế độ A hoặc Chế độ B và nhịp năng lượng. |
| **UC-ACC-05** | Xóa tài khoản | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Thực thi quyền được lãng quên: vô hiệu hóa tài khoản, hủy mọi lịch học tương lai và xóa/ẩn danh hóa dữ liệu cá nhân. |
| **UC-ACC-06** | Nâng cấp hoặc gia hạn gói Premium | User-Goal (Tầng 1) | Learner (`ACT-02`) | Cổng thanh toán (`ACT-05`) | Association | Khởi tạo đơn thanh toán nâng cấp hoặc gia hạn gói Premium 99.000đ/30 ngày, nhận mã QR thanh toán có hiệu lực 15 phút. |
| **UC-ACC-07** | Xử lý thông báo kết quả thanh toán | System-Goal (Tầng 1) | Cổng thanh toán (`ACT-05`) | — | Association | Tiếp nhận Webhook xác nhận giao dịch thành công (kể cả đơn EXPIRED hợp lệ), nâng hạng PREMIUM và cộng dồn thời hạn. |
| **UC-ACC-08** | Dọn bản ghi giữ chỗ và đơn thanh toán treo | System-Goal (Tầng 2) | Administrator (`ACT-03`), Learner (`ACT-02`) *(TimeEvent)* | — | Association | Định kỳ quét thu hồi hạn ngạch giữ chỗ AI quá hạn 5 phút và chuyển trạng thái các đơn thanh toán PENDING quá hạn 15 phút sang EXPIRED. |
| **UC-ACC-09** | Làm mới hạn ngạch chu kỳ tháng | System-Goal (Tầng 2) | Learner (`ACT-02`) *(TimeEvent)* | — | Association | Định kỳ 00:00 ngày đầu tháng (theo UTC) đặt lại số lượt gọi AI về định mức chuẩn theo gói dịch vụ (FREE: 30, PREMIUM: 300). |
| **UC-ACC-10** | Hạ cấp gói dịch vụ hết hạn | System-Goal (Tầng 1) | Learner (`ACT-02`) *(TimeEvent)* | — | Association | Quét phát hiện người dùng hết hạn Premium, chuyển tài khoản về gói FREE và tự động áp dụng quy tắc giữ tối đa 3 lộ trình ACTIVE. |
| **UC-ACC-11** | Quản lý ghi chú thói quen học tập | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Tra cứu minh bạch 4 danh mục bộ nhớ (Profile, Behavioral, Knowledge, Interaction) qua 3 tầng nhận thức, xác nhận/sửa/từ chối suy luận AI, xem Skill Mastery và khôi phục Cold-Start. |

### Phân hệ 2: Khởi tạo & Lập kế hoạch Lộ trình (10 Use Cases)
- **Sơ đồ 2: Khởi tạo & Lập kế hoạch Lộ trình**: `UC-PLAN-01`, `UC-PLAN-02`, `UC-PLAN-03`, `UC-PLAN-04`, `UC-PLAN-05`, `UC-PLAN-06`, `UC-PLAN-07`, `UC-PLAN-08`, `UC-PLAN-09`, `UC-PLAN-10`

| Mã UC | Tên Use Case | Phân loại | Tác nhân chính | Tác nhân phụ | Quan hệ UML | Mục tiêu nghiệp vụ trọn vẹn |
|---|---|---|---|---|---|---|
| **UC-PLAN-01** | Tạo khung lộ trình bằng AI | User-Goal (Tầng 1) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) | Association | Khởi tạo mục tiêu, nạp học liệu RAG (kiểm tra SSRF), phỏng vấn chẩn đoán phân tầng và phê duyệt khung Cột mốc kiến thức sơ bộ kèm nguồn trích dẫn. |
| **UC-PLAN-02** | Tạo danh sách bài học bằng AI | User-Goal (Tầng 1) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) | Association | Kích hoạt AI tạo danh sách bài học chi tiết Cấp 2 từ các cột mốc đã duyệt với thời lượng chuẩn 30–120 phút. |
| **UC-PLAN-03** | Xếp lịch học bằng AI và áp dụng | User-Goal (Tầng 1) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) | `<<include>> UC-PLAN-09` | Phân bổ bài học vào các khối thời gian (`ScheduleBlocks`) bằng Scheduling Engine tất định (kết hợp AI gợi ý nhịp năng lượng), kiểm định qua UC-PLAN-09, xem Diff Preview và bấm Apply để lưu Lịch học chính thức. |
| **UC-PLAN-04** | Tạo lộ trình thủ công | User-Goal (Tầng 1) | Learner (`ACT-02`) | — | `<<include>> UC-PLAN-09` | Tự tay nhập toàn bộ mục tiêu, cột mốc, danh sách bài học và xếp lịch thủ công (kiểm định qua UC-PLAN-09) không sử dụng AI. |
| **UC-PLAN-05** | Cập nhật thông tin lộ trình | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Đổi tên, mô tả và ngày mục tiêu hoàn thành lộ trình (kiểm tra điều kiện ngày mục tiêu không sớm hơn bài học đã xếp). |
| **UC-PLAN-06** | Lưu trữ lộ trình | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Đưa lộ trình sang trạng thái ARCHIVED, đóng băng lịch học, hủy bài học dở dang và giải phóng chỉ tiêu lộ trình hoạt động. |
| **UC-PLAN-07** | Quản lý công việc và quan hệ tiên quyết | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | `<<include>> UC-PLAN-09` | Thêm, sửa, hủy bài học lẻ, thiết lập quan hệ phụ thuộc DAG không chu trình và xếp lịch bài từ hàng đợi Backlog Queue. |
| **UC-PLAN-08** | Quản lý cột mốc | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Thêm mới, đổi tên, sắp xếp lại thứ tự tuần tự hoặc xóa bớt cột mốc trong quá trình vận hành lộ trình học tập. |
| **UC-PLAN-09** | Kiểm định tính hợp lệ của lịch học | Subfunction (Tầng 1) | Hệ thống | — | Được `<<include>>` bởi 9 UCs | Kiểm tra tất định 100% trong $\le 50$ms: không có chu trình DAG, không trùng khoảng bận, không vượt trần giờ học và tuân thủ 5 quy tắc Schedule Resilience; trả về VALID, SOFT_OVERFLOW hoặc INVALID. |
| **UC-PLAN-10** | Mô phỏng kịch bản giả định (What-if Simulation) | User-Goal (Tầng 1) | Learner (`ACT-02`) | — | `<<include>> UC-PLAN-09` | Mô phỏng thay đổi thời gian rảnh, trần giờ học hoặc deadline trong môi trường sandbox không tốn quota AI (<100ms), kiểm định qua UC-PLAN-09, xem Diff song song và tùy chọn áp dụng vào lịch chính thức. |

### Phân hệ 3: Thực thi Học tập & Tích hợp Lịch ngoại vi (9 Use Cases)
- **Sơ đồ 3: Thực thi Học tập & Lịch ngoại vi**: `UC-EXEC-01`, `UC-EXEC-02`, `UC-EXEC-03`, `UC-EXEC-04`, `UC-EXEC-05`, `UC-EXEC-06`, `UC-EXEC-07`, `UC-EXEC-08`, `UC-EXEC-09`

| Mã UC | Tên Use Case | Phân loại | Tác nhân chính | Tác nhân phụ | Quan hệ UML | Mục tiêu nghiệp vụ trọn vẹn |
|---|---|---|---|---|---|---|
| **UC-EXEC-01** | Xem lịch học và Tiêu điểm Hôm nay | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Hiển thị giao diện Today Focus View tối giản, thời khóa biểu học tập dạng lịch và danh sách các bài học cần chú ý. |
| **UC-EXEC-02** | Dời lịch công việc thủ công | User-Goal (Tầng 1) | Learner (`ACT-02`) | — | `<<include>> UC-PLAN-09` | Kéo thả hoặc chọn ngày mới để dời lịch cho bài học đơn lẻ; tăng bộ đếm dời lịch và kiểm định lịch mới qua UC-PLAN-09. |
| **UC-EXEC-03** | Đánh dấu hoàn thành nhanh | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Đánh dấu hoàn thành bài học ngay mà không cần chạy đồng hồ đếm giờ; bắt buộc nhập Key Takeaway $\ge 30$ ký tự và độ tự tin (1..5). |
| **UC-EXEC-04** | Thực hiện phiên học tập trung (Tiêu chuẩn & Rút gọn) | User-Goal (Tầng 1) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) (tùy chọn) | Association | Khởi động không gian học tập Focus Mode theo chế độ Tiêu chuẩn (Pomodoro/Stopwatch) hoặc phiên rút gọn MVS 10–15 phút, chốt phiên chủ động và ghi chú đúc kết. |
| **UC-EXEC-05** | Chia nhỏ bài học bằng AI | User-Goal (Tầng 2) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) | Association | Yêu cầu AI chia nhỏ một bài học quá dài hoặc gây trở ngại tâm lý thành 2–3 bài học siêu nhỏ (Micro-tasks 15–45 phút). |
| **UC-EXEC-06** | Tự động lưu phiên học khi mất kết nối | System-Goal (Tầng 2) | Learner (`ACT-02`) *(TimeEvent)* | — | Association | Quét phát hiện phiên học mất tín hiệu nhịp tim quá 5 phút, tự động lưu và chốt phiên dở dang, đánh dấu nợ đúc kết trong 24 giờ. |
| **UC-EXEC-07** | Kết nối tài khoản Google Calendar | User-Goal (Tầng 2) | Learner (`ACT-02`) | Dịch vụ Lịch (`ACT-06`) | Association | Thực hiện ủy quyền xác thực OAuth 2.0 để liên kết với tài khoản Google Calendar và lưu trữ khóa truy cập an toàn. *(Ngắt kết nối là luồng thay thế 17a)*. |
| **UC-EXEC-08** | Tự động cập nhật thời gian bận từ Google Calendar | System-Goal (Tầng 2) | Learner (`ACT-02`) *(TimeEvent)* | Dịch vụ Lịch (`ACT-06`) | Association | Định kỳ mỗi 60 phút quét và nạp các khoảng thời gian bận (Free/Busy) trong 14 ngày tới để khấu trừ thời gian rảnh khả dụng. |
| **UC-EXEC-09** | Đồng bộ lịch học sang Google Calendar / ứng dụng lịch | User-Goal (Tầng 2) | Learner (`ACT-02`) | Dịch vụ Lịch (`ACT-06`) | Association | Tải tệp dữ liệu lịch tĩnh dạng `.ics` hoặc khởi tạo/xoay vòng URL liên kết WebCal bảo mật để đồng bộ lịch học sang Google Calendar hoặc ứng dụng lịch cá nhân. |

### Phân hệ 4: Phân tích Tiến độ, Kiểm chứng Năng lực & Thích ứng (10 Use Cases)
- **Sơ đồ 4: Phân tích Tiến độ, Kiểm chứng & Thích ứng**: `UC-ADAPT-01`, `UC-ADAPT-02`, `UC-ADAPT-03`, `UC-ADAPT-04`, `UC-ADAPT-05`, `UC-ADAPT-06`, `UC-ADAPT-07`, `UC-ADAPT-08`, `UC-ADAPT-09`, `UC-ADAPT-10`

| Mã UC | Tên Use Case | Phân loại | Tác nhân chính | Tác nhân phụ | Quan hệ UML | Mục tiêu nghiệp vụ trọn vẹn |
|---|---|---|---|---|---|---|
| **UC-ADAPT-01** | Xem báo cáo tiến độ và bằng chứng học tập | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | Association | Hiển thị bảng tổng hợp các chỉ số học tập định lượng, chỉ số Bắc đẩu WRLS, dòng thời gian các Key Takeaways và độ lệch tự tin. |
| **UC-ADAPT-02** | Làm bài kiểm tra cột mốc | User-Goal (Tầng 1) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) | Association | Thực hiện bài kiểm tra năng lực 2 tầng cuối cột mốc (đối chiếu bằng chứng và truy hồi điểm mù); cấp chứng chỉ hoàn thành hoặc gợi ý bài học bổ trợ. |
| **UC-ADAPT-03** | Đánh giá học tập cuối tuần | User-Goal (Tầng 1) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) | Association | Xem xét dữ liệu học tập tuần qua, nhận nhận xét phản tư từ AI, đặt cam kết tuần mới và làm mới sớm ngân sách dời lịch tuần (tối đa 1 lần/tuần). |
| **UC-ADAPT-04** | Tạm dừng lộ trình | User-Goal (Tầng 2) | Learner (`ACT-02`) | — | `<<include>> UC-PLAN-09` | Chủ động đóng băng lộ trình sang trạng thái PAUSED trong khoảng `[PauseStartDate, PauseEndDate]`, lưu PauseRecord, tự động kích hoạt Domino Shift qua UC-PLAN-09 và vô hiệu hóa cảnh báo quá hạn. |
| **UC-ADAPT-05** | Tiếp tục lộ trình và dời lịch bù ngày dừng | User-Goal (Tầng 1) | Learner (`ACT-02`) | — | `<<include>> UC-PLAN-09` | Mở lại lộ trình tạm dừng, kiểm tra trần số lộ trình hoạt động, tịnh tiến toàn bộ bài học tương lai theo số ngày gián đoạn thực tế qua Domino Shift và kiểm định qua UC-PLAN-09. |
| **UC-ADAPT-06** | Dời lịch bằng AI cho bài quá hạn | User-Goal (Tầng 1) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) | `<<include>> UC-PLAN-09` | Kích hoạt AI sắp xếp lại các bài học đang bị quá hạn trong 1 lộ trình, kiểm định qua UC-PLAN-09 và khấu trừ 1 lượt ngân sách dời lịch tuần khi áp dụng. |
| **UC-ADAPT-07** | Khôi phục lộ trình bị gián đoạn lâu ngày | User-Goal (Tầng 1) | Learner (`ACT-02`) | LLM Provider (`ACT-04`) | `<<include>> UC-PLAN-09` | Vận hành nghi thức phục hồi 4 bước (Reset Ritual) cho lộ trình bị bỏ quên $\ge 7$ ngày, áp dụng 1 trong 3 chiến lược phục hồi, cập nhật mốc hoạt động và tắt trạng thái ngủ đông. |
| **UC-ADAPT-08** | Gửi email nhắc nhở bài quá hạn và lộ trình gián đoạn | System-Goal (Tầng 2) | Learner (`ACT-02`) *(TimeEvent)* | Dịch vụ Email (`ACT-07`) | Association | Định kỳ quét lúc 00:05 (theo múi giờ cá nhân) để thống kê bài quá hạn và gửi email nhắc nhở tập trung cho người học. |
| **UC-ADAPT-09** | Tổng hợp hồ sơ thói quen học tập | System-Goal (Tầng 2) | Learner (`ACT-02`) *(TimeEvent)* | — | Association | Định kỳ phân tích lịch sử các phiên học trong 30 ngày để cập nhật các khung giờ học hiệu quả nhất và thời lượng học tối ưu của người học. |
| **UC-ADAPT-10** | Đặt lại ngân sách dời lịch hàng tuần | System-Goal (Tầng 2) | Learner (`ACT-02`) *(TimeEvent)* | — | Association | Tự động quét lúc 00:00 Thứ Hai (theo múi giờ cá nhân) để đặt lại số lượt dời lịch đã dùng về 0 (cấp đủ 3 lượt dời lịch mới). |

### Phân hệ 5: Quản trị Hệ thống & Vận hành (7 Use Cases)
- **Sơ đồ 5: Quản trị Hệ thống & Vận hành**: `UC-ADM-01`, `UC-ADM-02`, `UC-ADM-03`, `UC-ADM-04`, `UC-ADM-05`, `UC-ADM-06`, `UC-ADM-07`

| Mã UC | Tên Use Case | Phân loại | Tác nhân chính | Tác nhân phụ | Quan hệ UML | Mục tiêu nghiệp vụ trọn vẹn |
|---|---|---|---|---|---|---|
| **UC-ADM-01** | Khóa hoặc mở khóa tài khoản người dùng | User-Goal (Tầng 2) | Administrator (`ACT-03`) | — | Association | Quản trị viên vô hiệu hóa hoặc mở lại quyền truy cập của tài khoản người dùng kèm theo lý do can thiệp và ghi nhật ký. |
| **UC-ADM-02** | Đổi gói dịch vụ của người dùng | User-Goal (Tầng 2) | Administrator (`ACT-03`) | — | Association | Quản trị viên điều chỉnh thủ công gói dịch vụ (FREE sang PREMIUM hoặc ngược lại) phục vụ mục đích hỗ trợ người dùng. |
| **UC-ADM-03** | Điều chỉnh hạn ngạch AI người dùng | User-Goal (Tầng 2) | Administrator (`ACT-03`) | — | Association | Quản trị viên can thiệp tăng hoặc giảm định mức lượt gọi AI của tài khoản người dùng kèm lý do kiểm toán. |
| **UC-ADM-04** | Đối soát đơn thanh toán | User-Goal (Tầng 1) | Administrator (`ACT-03`) | Cổng thanh toán (`ACT-05`) | Association | Tra cứu, đối chiếu giao dịch với cổng thanh toán và xử lý đơn EXPIRED sang PAID khi có bằng chứng chuyển khoản hợp lệ. |
| **UC-ADM-05** | Giám sát vận hành hệ thống và dịch vụ AI | User-Goal (Tầng 2) | Administrator (`ACT-03`) | — | Association | Theo dõi bảng điều khiển chỉ số hiệu năng hệ thống, độ trễ phản hồi, tỷ lệ lỗi và mức tiêu thụ tài nguyên AI thời gian thực. |
| **UC-ADM-06** | Xem nhật ký kiểm toán quản trị | User-Goal (Tầng 2) | Administrator (`ACT-03`) | — | Association | Tra cứu lịch sử chi tiết các hành động can thiệp quản trị nhạy cảm (khóa tài khoản, can thiệp gói cước, đối soát tiền, chỉnh hạn ngạch). |
| **UC-ADM-07** | Quản lý kho khái niệm tri thức | User-Goal (Tầng 1) | Administrator (`ACT-03`) | — | Association | Rà soát, chuẩn hóa và phê duyệt chuyển đổi trạng thái khái niệm từ UNVERIFIED sang VERIFIED làm căn cứ Ground Truth cho Prove Mode. |

---

## 4. Kiến trúc Sơ đồ Use Case (Use Case Diagrams Reference)

Nhằm tuân thủ nguyên tắc giới hạn nhận thức trực quan (mỗi sơ đồ chứa $\le 12$ Use Cases theo hướng dẫn chuẩn hóa), kiến trúc sơ đồ Use Case của FocusFlow được tổ chức thành 01 Sơ đồ Tổng quan và 06 Sơ đồ Phân hệ chuyên sâu:

| STT | Tên Sơ đồ | Số lượng UC | Tệp mã nguồn PlantUML (`.puml`) | Tệp thiết kế Draw.io (`.drawio`) | Ảnh kết xuất (`.png`) |
|---|---|---|---|---|---|
| **0** | **Sơ đồ Ca sử dụng Tổng quan Toàn hệ thống** | 47 UCs / 5 Packages | [`use-case-diagram.puml`](./use-cases/use-case-diagram.puml) | [`UC_Master.drawio`](./use-cases/UC_Master.drawio) | [`FocusFlow_UseCase_Diagram.png`](./images/FocusFlow_UseCase_Diagram.png) |
| **1** | **Phân hệ 1: Quản lý Tài khoản, Hồ sơ & Gói dịch vụ** | 11 UCs (Gói 1A: 6 UCs, Gói 1B: 5 UCs) | [`uc-mod-01-account-profile-billing.puml`](./use-cases/uc-mod-01-account-profile-billing.puml) | [`UC_Module_01_Account_Profile_Billing.drawio`](./use-cases/UC_Module_01_Account_Profile_Billing.drawio) | [`uc-mod-01-account-profile-billing.png`](./images/uc-mod-01-account-profile-billing.png) |
| **2** | **Phân hệ 2: Khởi tạo & Lập kế hoạch Lộ trình** | 10 UCs (`UC-PLAN-01`, `UC-PLAN-02`, `UC-PLAN-03`, `UC-PLAN-04`, `UC-PLAN-05`, `UC-PLAN-06`, `UC-PLAN-07`, `UC-PLAN-08`, `UC-PLAN-09`, `UC-PLAN-10`) | [`uc-mod-02-roadmap-planning.puml`](./use-cases/uc-mod-02-roadmap-planning.puml) | [`UC_Module_02_Roadmap_Planning.drawio`](./use-cases/UC_Module_02_Roadmap_Planning.drawio) | [`uc-mod-02-roadmap-planning.png`](./images/uc-mod-02-roadmap-planning.png) |
| **3** | **Phân hệ 3: Thực thi Học tập & Lịch ngoại vi** | 9 UCs (`UC-EXEC-01`, `UC-EXEC-02`, `UC-EXEC-03`, `UC-EXEC-04`, `UC-EXEC-05`, `UC-EXEC-06`, `UC-EXEC-07`, `UC-EXEC-08`, `UC-EXEC-09`, kèm `UC-PLAN-09`) | [`uc-mod-03-study-execution-calendar.puml`](./use-cases/uc-mod-03-study-execution-calendar.puml) | [`UC_Module_03_Study_Execution_Calendar.drawio`](./use-cases/UC_Module_03_Study_Execution_Calendar.drawio) | [`uc-mod-03-study-execution-calendar.png`](./images/uc-mod-03-study-execution-calendar.png) |
| **4** | **Phân hệ 4: Phân tích Tiến độ, Kiểm chứng & Thích ứng** | 10 UCs (`UC-ADAPT-01`, `UC-ADAPT-02`, `UC-ADAPT-03`, `UC-ADAPT-04`, `UC-ADAPT-05`, `UC-ADAPT-06`, `UC-ADAPT-07`, `UC-ADAPT-08`, `UC-ADAPT-09`, `UC-ADAPT-10`, kèm `UC-PLAN-09`) | [`uc-mod-04-analytics-adaptation.puml`](./use-cases/uc-mod-04-analytics-adaptation.puml) | [`UC_Module_04_Analytics_Adaptation.drawio`](./use-cases/UC_Module_04_Analytics_Adaptation.drawio) | [`uc-mod-04-analytics-adaptation.png`](./images/uc-mod-04-analytics-adaptation.png) |
| **5** | **Phân hệ 5: Quản trị Hệ thống & Vận hành** | 7 UCs (`UC-ADM-01`, `UC-ADM-02`, `UC-ADM-03`, `UC-ADM-04`, `UC-ADM-05`, `UC-ADM-06`, `UC-ADM-07`) | [`uc-mod-05-system-administration.puml`](./use-cases/uc-mod-05-system-administration.puml) | [`UC_Module_05_System_Administration.drawio`](./use-cases/UC_Module_05_System_Administration.drawio) | [`uc-mod-05-system-administration.png`](./images/uc-mod-05-system-administration.png) |

---

## 5. Đặc tả Chi tiết Phân tầng Từng Use Case

Hệ thống đặc tả được phân tầng theo cấu trúc 2 cấp độ chi tiết:
- **Tầng 1 — Đặc tả Đầy đủ Chi tiết (18 Use Cases lõi, tài chính, AI, mô phỏng & thuật toán phức tạp)**: Áp dụng cấu trúc bảng thuộc tính mở rộng, phân rã luồng chính đánh số chủ động, danh mục luồng thay thế và ngoại lệ toàn diện, hệ thống quy tắc nghiệp vụ mã hóa không trùng lặp, khối quản trị AI & an toàn dữ liệu chuyên sâu. Toàn bộ thông tin chi tiết nội bộ công nghệ (tên bảng dữ liệu vật lý, tên lớp mã nguồn, câu lệnh SQL) được gỡ bỏ tuyệt đối để bảo toàn góc nhìn hộp đen theo chuẩn BA.
- **Tầng 2 — Đặc tả Rút gọn Chuẩn hóa (29 Use Cases tiêu chuẩn & chức năng hỗ trợ)**: Trình bày theo định dạng tinh gọn 1 trang bao gồm Mục tiêu, Tác nhân, Tiền/Hậu điều kiện thành công & bảo đảm tối thiểu, Luồng chính tinh gọn (4–7 bước), Các luồng nhánh then chốt và Quy tắc nghiệp vụ trọng yếu.


### PHÂN HỆ 1: QUẢN LÝ TÀI KHOẢN, HỒ SƠ & GÓI DỊCH VỤ

Phân hệ bao gồm 11 Use Cases chịu trách nhiệm quản lý vòng đời tài khoản người dùng, xác thực danh tính, cấu hình thời gian rảnh, quản lý ghi chú thói quen học tập, chu trình thanh toán gói Premium và điều tiết hạn ngạch sử dụng hệ thống.

```
Sơ đồ 1A: Tài khoản & Xác thực (UC-ACC-01, UC-ACC-02, UC-ACC-03, UC-ACC-04, UC-ACC-05, UC-ACC-11)
Sơ đồ 1B: Thanh toán & Hạn ngạch (UC-ACC-06, UC-ACC-07, UC-ACC-08, UC-ACC-09, UC-ACC-10)
```

---

#### UC-ACC-01: Đăng ký tài khoản

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ACC-01: Đăng ký tài khoản** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Khách vãng lai (`ACT-00`) |
| **Tác nhân phụ** | Dịch vụ Email (`ACT-07`) |
| **Tiền điều kiện** | Người dùng chưa đăng nhập, truy cập vào giao diện đăng ký công khai của hệ thống. |
| **Hậu điều kiện thành công** | Tài khoản mới được khởi tạo ở trạng thái hoạt động với gói dịch vụ `FREE`, cấp hạn ngạch AI dùng thử ban đầu (30 lượt/tháng), khởi tạo hồ sơ người học mặc định; hệ thống gửi email xác minh mềm và tự động mở phiên đăng nhập. |
| **Bảo đảm tối thiểu** | Nếu thông tin không hợp lệ hoặc email đã tồn tại, không tạo tài khoản, không cấp tài nguyên. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-AUTH-001`, `BUSR-10`, `BUSR-12` |

- **Luồng chính (Basic Flow)**:
  1. Khách vãng lai nhập thông tin đăng ký gồm họ tên, địa chỉ email và mật khẩu mong muốn.
  2. Khách vãng lai xác nhận đồng ý với điều khoản sử dụng và gửi yêu cầu đăng ký.
  3. Hệ thống kiểm tra định dạng email, độ phức tạp của mật khẩu (`BR-AUTH-01`) và xác thực email chưa từng được đăng ký trong hệ thống.
  4. Hệ thống tạo tài khoản mới với gói dịch vụ `FREE`, hạn mức 30 lượt gọi AI/tháng và tối đa 3 lộ trình hoạt động đồng thời.
  5. Hệ thống gửi thư điện tử chứa liên kết xác minh đến email người dùng theo cơ chế xác minh mềm (`BR-AUTH-02`).
  6. Hệ thống tự động thiết lập phiên làm việc hợp lệ và chuyển hướng người học đến trang thiết lập hồ sơ ban đầu (`UC-ACC-04`). Use case kết thúc thành công.

- **Luồng ngoại lệ (Exception Flows)**:
  - **3a. Địa chỉ email đã tồn tại trong hệ thống**: Hệ thống từ chối tạo tài khoản, hiển thị thông báo email đã được đăng ký và gợi ý chuyển sang màn hình Đăng nhập (`UC-ACC-02`) hoặc Đặt lại mật khẩu (`UC-ACC-03`). Use case kết thúc (thất bại).
  - **3b. Mật khẩu không đạt tiêu chuẩn an toàn (NFR-SEC-002)**: Hệ thống từ chối tạo tài khoản, thông báo rõ các tiêu chí độ phức tạp chưa đạt (độ dài tối thiểu 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt) để người dùng điều chỉnh.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-AUTH-01 (Tiêu chuẩn độ phức tạp mật khẩu — NFR-SEC-002)**: Mật khẩu bắt buộc có độ dài tối thiểu 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt. Mật khẩu được băm một chiều an toàn bằng thuật toán Argon2id trước khi lưu trữ (tuân thủ `ADR-008`).
  - **BR-AUTH-02 (Cơ chế xác minh mềm — Soft-Verification)**: Cho phép người học đăng nhập và trải nghiệm lập lộ trình ngay sau khi đăng ký; hệ thống gửi email xác minh qua Dịch vụ Email (`ACT-07`) và hiển thị banner nhắc nhở xác minh email trên đầu trang. Việc xác minh email là điều kiện bắt buộc trước khi kích hoạt tính năng gửi email báo bài quá hạn (`UC-ADAPT-08`).

---

#### UC-ACC-02: Đăng nhập

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ACC-02: Đăng nhập** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người dùng đã đăng ký (`ACT-01`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người dùng đã có tài khoản hợp lệ trong hệ thống. |
| **Hậu điều kiện thành công** | Danh tính người dùng được xác thực; hệ thống cấp mã định danh phiên an toàn và chuyển hướng về bảng điều khiển tương ứng theo vai trò (`Learner` hoặc `Administrator`). |
| **Bảo đảm tối thiểu** | Nếu thông tin xác thực sai hoặc tài khoản bị khóa, từ chối cấp quyền truy cập, ghi nhận số lần thất bại. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-AUTH-002`, `FR-ADM-001` |

- **Luồng chính (Basic Flow)**:
  1. Người dùng nhập địa chỉ email và mật khẩu tại giao diện đăng nhập.
  2. Hệ thống kiểm tra tài khoản tồn tại và trạng thái tài khoản đang hoạt động (`BR-AUTH-03`).
  3. Hệ thống đối chiếu mật khẩu đã mã hóa.
  4. Hệ thống thiết lập phiên làm việc bảo mật (thông qua cookie bảo mật chuyên dụng chỉ đọc từ máy chủ).
  5. Hệ thống đặt lại bộ đếm số lần đăng nhập sai về 0 và chuyển hướng người dùng vào giao diện học tập cá nhân (hoặc giao diện quản trị nếu là Quản trị viên). Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **2a. Luồng Đăng xuất chủ động (UC-02b)**: Người dùng đang đăng nhập chọn chức năng Đăng xuất; hệ thống thu hồi mã định danh phiên làm việc, xóa cookie bảo mật và chuyển hướng người dùng về trang giới thiệu. Use case kết thúc.

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Tài khoản đang bị khóa hoặc bị vô hiệu hóa**: Hệ thống từ chối đăng nhập và thông báo rõ tài khoản đang bị tạm khóa hoặc đã bị vô hiệu hóa bởi Quản trị viên (`UC-ADM-01`), hướng dẫn liên hệ hỗ trợ.
  - **3e. Sai mật khẩu**: Hệ thống tăng bộ đếm số lần đăng nhập sai của tài khoản. Nếu số lần sai liên tiếp chạm ngưỡng 5 lần, hệ thống kích hoạt tạm khóa tài khoản trong 15 phút để bảo vệ (`BR-AUTH-03`).

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-AUTH-03 (Chính sách khóa tạm thời)**: Nhập sai mật khẩu liên tiếp 5 lần sẽ kích hoạt khóa tài khoản tạm thời trong vòng 15 phút để phòng chống tấn công dò mật khẩu tự động.

---

#### UC-ACC-03: Đặt lại mật khẩu

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ACC-03: Đặt lại mật khẩu** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người dùng đã đăng ký (`ACT-01`) |
| **Tác nhân phụ** | Dịch vụ Email (`ACT-07`) |
| **Tiền điều kiện** | Người dùng đã có tài khoản và có quyền truy cập vào hòm thư điện tử đã đăng ký. |
| **Hậu điều kiện thành công** | Mật khẩu tài khoản được cập nhật mới an toàn; toàn bộ các phiên đăng nhập đang hoạt động trước đó bị thu hồi; gửi email thông báo cập nhật mật khẩu thành công. |
| **Bảo đảm tối thiểu** | Nếu liên kết hết hạn hoặc mã xác thực không hợp lệ, không thay đổi mật khẩu cũ. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-AUTH-004`, `BUSR-01`, `ADR-008` |

- **Luồng chính (Basic Flow)**:
  1. Người dùng chọn chức năng Quên mật khẩu tại màn hình đăng nhập và nhập địa chỉ email đã đăng ký.
  2. Hệ thống kiểm tra và sinh một mã xác thực đặt lại mật khẩu duy nhất kèm chữ ký số bảo mật có thời hạn 15 phút (`BR-AUTH-04`).
  3. Hệ thống gửi thư điện tử chứa liên kết khôi phục mật khẩu thông qua Dịch vụ Email (`ACT-07`).
  4. Người dùng bấm vào liên kết trong email, giao diện hiển thị biểu mẫu thiết lập mật khẩu mới.
  5. Người dùng nhập mật khẩu mới hợp lệ thỏa mãn chính sách độ phức tạp (`NFR-SEC-002`) và xác nhận gửi.
  6. Hệ thống băm mật khẩu mới bằng Argon2id (`ADR-008`), cập nhật vào hệ thống, hủy toàn bộ các phiên làm việc hiện có trên các thiết bị (`Family Session Revocation`) và chuyển hướng người dùng đến trang đăng nhập với thông báo thành công. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **2a. Email không tồn tại trong hệ thống (Chống dò quét tài khoản — FR-AUTH-004)**: Nhằm bảo mật chống Account Enumeration, hệ thống vẫn hiển thị thông báo trung lập: *"Nếu địa chỉ email tồn tại trên hệ thống, hướng dẫn đặt lại mật khẩu đã được gửi đến hòm thư của bạn"*, không gửi thư thực tế ra ngoài. Use case kết thúc.

- **Luồng ngoại lệ (Exception Flows)**:
  - **4a. Liên kết đặt lại mật khẩu đã hết hạn (> 15 phút) hoặc đã qua sử dụng**: Hệ thống từ chối cập nhật mật khẩu, hiển thị thông báo liên kết không còn hiệu lực và hướng dẫn người dùng yêu cầu lại liên kết mới.
  - **5a. Mật khẩu mới không đạt chuẩn an toàn**: Hệ thống hiển thị cảnh báo các tiêu chí độ phức tạp chưa đạt (tối thiểu 8 ký tự, gồm chữ hoa, chữ thường, số, ký tự đặc biệt) để người dùng nhập lại.
  - **2b. Tài khoản đang bị khóa (`LOCKED`)**: Hệ thống từ chối gửi liên kết khôi phục và hướng dẫn liên hệ Quản trị viên hệ thống.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-AUTH-04 (Thời hạn và tính đơn nhất của liên kết khôi phục — FR-AUTH-004)**: Liên kết đặt lại mật khẩu chỉ có giá trị sử dụng một lần duy nhất và tự động hết hiệu lực sau đúng 15 phút kể từ thời điểm phát hành. Khi đổi mật khẩu thành công, toàn bộ Refresh Token cũ bị thu hồi ngay lập tức (`ADR-008`).

---

#### UC-ACC-04: Cấu hình hồ sơ và thời gian rảnh

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ACC-04: Cấu hình hồ sơ và thời gian rảnh** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập hợp lệ vào hệ thống. |
| **Hậu điều kiện thành công** | Thông tin cá nhân, múi giờ IANA, cấu hình khung thời gian rảnh (Chế độ A hoặc B) và mức độ năng lượng học tập được lưu lại, làm căn cứ đầu vào cho thuật toán xếp lịch. |
| **Bảo đảm tối thiểu** | Nếu dữ liệu cấu hình vi phạm giới hạn, từ chối lưu và giữ nguyên cấu hình hiện tại. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-AUTH-003`, `FR-AVAIL-001`, `FR-AVAIL-002`, `FR-AVAIL-003` |

- **Luồng chính (Basic Flow)**:
  1. Người học mở trang Cấu hình hồ sơ học tập cá nhân.
  2. Hệ thống hiển thị các thông tin hiện tại: họ tên, múi giờ chuẩn IANA, chế độ thời gian rảnh đang áp dụng và bảng phân bổ năng lượng theo các buổi trong ngày.
  3. Người học cập nhật thông tin cá nhân hoặc lựa chọn chế độ thời gian rảnh mong muốn:
     - *Chế độ A (Theo định mức giờ)*: Đặt số giờ học tối đa mỗi ngày (0.5–14 giờ/ngày theo `OS-06`) và chọn các ngày trong tuần có thể học.
     - *Chế độ B (Theo khung giờ cố định)*: Khai báo cụ thể các khoảng thời gian rảnh trong từng ngày (ví dụ: Thứ Hai 19:30 – 21:30, tối thiểu 30 phút/khung).
  4. Người học chọn mức năng lượng nhận thức tương ứng cho các buổi học (`HIGH`, `MEDIUM`, `LOW`).
  5. Người học nhấn Lưu cấu hình. Hệ thống kiểm tra tính hợp lệ của dữ liệu (`BR-AVAIL-01`) và ghi nhận thay đổi thành công. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Người học thay đổi múi giờ cá nhân**: Hệ thống lưu chuỗi múi giờ chuẩn IANA mới và áp dụng để tính toán ranh giới ngày học bắt đầu từ chu kỳ kế tiếp mà không xáo trộn lịch sử các phiên học đã hoàn thành (`BR-AVAIL-02`).

- **Luồng ngoại lệ (Exception Flows)**:
  - **5a. Định mức hoặc khung giờ cấu hình vi phạm quy tắc**: Nếu Chế độ A đặt ngoài khoảng 0.5h đến 14h/ngày, hoặc Chế độ B có khung giờ < 30 phút hoặc chồng chéo trong ngày, hệ thống từ chối lưu và hiển thị thông báo lỗi cụ thể để Người học điều chỉnh.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-AVAIL-01 (Giới hạn định mức thời gian rảnh — OS-06)**: Trong Chế độ A, định mức học tập hàng ngày giới hạn trong khoảng từ 0.5 đến 14.0 giờ/ngày (khớp quyết định mở `OS-06`). Trong Chế độ B, mỗi khung giờ rảnh tối thiểu là 30 phút và không được giao nhau.
  - **BR-AVAIL-02 (Quy tắc hiệu lực của thay đổi thời gian rảnh)**: Việc thay đổi cấu hình thời gian rảnh không tự ý làm thay đổi các bài học đã được xếp lịch trong quá khứ, chỉ áp dụng cho các lần xếp lịch hoặc dời lịch mới phát sinh.

---

#### UC-ACC-05: Xóa tài khoản

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ACC-05: Xóa tài khoản (Right to Erasure / GDPR Điều 17)** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập; tài khoản không có đơn thanh toán nào đang ở trạng thái chờ xử lý (`PENDING`). |
| **Hậu điều kiện thành công** | Tài khoản chuyển sang trạng thái đã xóa (`DELETED`, `is_active = false`); toàn bộ thông tin định danh cá nhân (PII) bị ẩn danh hóa triệt để; thu hồi toàn bộ các phiên làm việc hiện hành; mọi lịch học và nhiệm vụ tương lai bị hủy bỏ; bản ghi giao dịch tài chính được bảo lưu ẩn danh cho đối soát kế toán. |
| **Bảo đảm tối thiểu** | Nếu người dùng hủy xác nhận, nhập sai mật khẩu xác minh hoặc tài khoản có đơn thanh toán `PENDING`, tài khoản giữ nguyên trạng thái hoạt động bình thường 100%. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-PROFILE-002`, `GDPR Điều 17 (Quyền được lãng quên)`, `BUSR-01`, `ADR-008` |

- **Luồng chính (Basic Flow)**:
  1. Người học truy cập phần Cài đặt Tài khoản & Quyền riêng tư, chọn chức năng "Xóa tài khoản vĩnh viễn".
  2. Hệ thống hiển thị hộp thoại cảnh báo nguy cơ nghiêm trọng: việc xóa tài khoản là vĩnh viễn không thể khôi phục, toàn bộ lộ trình, lịch sử học tập, ghi chú đúc kết và quyền lợi gói Premium chưa sử dụng sẽ bị hủy bỏ; yêu cầu người học nhập mật khẩu hiện tại.
  3. Người học nhập đúng mật khẩu và bấm xác nhận "Tôi hiểu và muốn xóa vĩnh viễn tài khoản".
  4. Hệ thống kiểm tra mật khẩu hợp lệ (Argon2id) và xác nhận tài khoản không có đơn thanh toán nào đang ở trạng thái chờ xử lý (`PENDING`).
  5. Hệ thống thực thi giao dịch nguyên tử áp dụng quy trình Soft Delete an toàn kết hợp ẩn danh hóa triệt để dữ liệu nhận dạng cá nhân (PII Scrubbing — `BR-USER-01`):
     - Chuyển trạng thái tài khoản sang `status = 'DELETED'` và `is_active = false`.
     - Ẩn danh hóa triệt để PII: thay thế `email` bằng chuỗi giả danh mã hóa một chiều, xóa sạch `full_name`, `password_hash`, ảnh đại diện.
     - Vô hiệu hóa vĩnh viễn mã băm WebCal (`WebCalToken.is_active = false`) và thu hồi liên kết OAuth lịch ngoài.
     - Hủy bỏ toàn bộ các nhiệm vụ học tập chưa hoàn thành (`TODO`, `IN_PROGRESS`) trong tương lai trên `OfficialSchedule` và giải phóng toàn bộ các khối thời gian `schedule_blocks`.
     - Bảo lưu duy nhất các bản ghi giao dịch tài chính (`PaymentTransaction`) ở dạng ẩn danh hóa phi định danh nhằm phục vụ công tác đối soát kế toán và lưu trữ chứng từ tài chính theo luật định.
     - Thu hồi toàn bộ các phiên làm việc (Access Token / Refresh Token) hiện hành trong Redis (`Family Revocation`).
     - Ghi nhận sự kiện `AccountDeleted` vào Luồng Kiểm toán Tập trung.
  6. Hệ thống xóa cookie xác thực HttpOnly, hiển thị thông báo hoàn tất xóa tài khoản theo quy định bảo vệ dữ liệu cá nhân và chuyển hướng về trang chủ công khai. Use case kết thúc thành công.

- **Luồng ngoại lệ (Exception Flows)**:
  - **4a. Mật khẩu xác nhận không chính xác**: Hệ thống từ chối thao tác, hiển thị thông báo: *"Mật khẩu xác nhận không chính xác. Yêu cầu xóa tài khoản bị từ chối."* và giữ nguyên tài khoản hoạt động.
  - **4b. Tài khoản đang có đơn thanh toán PENDING**: Hệ thống từ chối xóa, hiển thị thông báo: *"Tài khoản đang có giao dịch thanh toán chờ xử lý. Vui lòng hoàn tất hoặc chờ đơn thanh toán hết hạn (15 phút) trước khi thực hiện xóa tài khoản."*

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-USER-01 (Quy trình Soft Delete & Ẩn danh hóa PII tuân thủ GDPR Điều 17 — FR-PROFILE-002)**: Khi thực thi quyền được lãng quên, hệ thống không xóa cứng (hard delete) bản ghi vật lý để tránh phá vỡ toàn vẹn tham chiếu cơ sở dữ liệu và chứng từ kế toán, mà áp dụng Soft Delete: cập nhật `status = 'DELETED'`, `is_active = false`, tẩy sạch PII, hủy lịch học tương lai và ẩn danh hóa chứng từ thanh toán. Tài khoản đã xóa không thể phục hồi hoặc đăng nhập lại.

---

#### UC-ACC-06: Nâng cấp hoặc gia hạn gói Premium

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ACC-06** |
| **Tên Use Case** | **Nâng cấp hoặc gia hạn gói Premium** |
| **Mô tả ngắn** | Người học yêu cầu nâng cấp tài khoản từ gói `FREE` lên `PREMIUM` hoặc người học đang ở gói `PREMIUM` yêu cầu mua gia hạn; hệ thống kiểm tra, tái sử dụng đơn thanh toán đang chờ (`PENDING`) còn hạn hoặc tạo đơn mới có thời hạn hiệu lực 15 phút và phối hợp với Cổng thanh toán để hiển thị mã QR chuyển khoản cùng thông tin thanh toán cho Người học. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Cổng thanh toán (`Payment Gateway` — `ACT-05`) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học chọn "Nâng cấp Premium" hoặc "Gia hạn gói" từ trang Quản lý gói dịch vụ hoặc từ thông báo chạm giới hạn gói `FREE`. |
| **Tiền điều kiện** | Người học đã đăng nhập hợp lệ vào hệ thống. |
| **Hậu điều kiện – thành công** | Đơn giao dịch thanh toán ở trạng thái `PENDING` với thời hạn hiệu lực 15 phút được tạo mới (hoặc được tái sử dụng nếu còn hạn); thông tin thanh toán gồm mã QR chuyển khoản chính xác và đồng hồ đếm ngược được hiển thị cho Người học. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Không tạo đơn thanh toán sai lệch hoặc trùng lặp; gói dịch vụ và thời hạn hiện tại của Người học không bị biến động. |
| **Include / Extend** | Không có *(Xử lý kết quả thanh toán bất đồng bộ được tách thành `UC-ACC-07`)* |
| **Tần suất / Độ ưu tiên** | Trung bình / Quan trọng (P1 — Should have) |
| **Tham chiếu SRS** | `FR-QUOTA-001`, `FR-QUOTA-002`, `BUSR-10`, `D7` |

**Luồng chính (Basic Flow)**:
1. Người học mở trang Quản lý gói dịch vụ và hạn ngạch AI.
2. Hệ thống hiển thị thông tin gói cước hiện tại, thời hạn còn lại (nếu đang là Premium), số lộ trình đang hoạt động và bảng so sánh quyền lợi:
   - Gói `FREE`: 03 lộ trình hoạt động đồng thời, 30 lượt gọi AI/tháng.
   - Gói `PREMIUM`: 15 lộ trình hoạt động đồng thời, 300 lượt gọi AI/tháng, giá tiêu chuẩn **99.000 VNĐ / chu kỳ 30 ngày** (`BR-PAY-01`).
3. Người học chọn lệnh Nâng cấp (nếu đang ở Free) hoặc Gia hạn thêm 30 ngày (nếu đang ở Premium).
4. Hệ thống kiểm tra xem Người học có đơn thanh toán nào đang ở trạng thái `PENDING` mà vẫn còn thời hạn hiệu lực hay không (`BR-PAY-02`).
5. Hệ thống tạo một đơn giao dịch thanh toán mới ở trạng thái `PENDING` với mức phí chuẩn 99.000 VNĐ, thời hạn hết hạn được thiết lập chính xác là 15 phút kể từ thời điểm tạo (`expires_at = NOW() + 15 phút`).
6. Hệ thống gửi yêu cầu khởi tạo giao dịch sang Cổng thanh toán (`Payment Gateway`) và tiếp nhận mã QR chuyển khoản ngân hàng hợp lệ kèm thông tin nội dung thanh toán đối soát.
7. Hệ thống hiển thị mã QR thanh toán, số tiền 99.000 VNĐ, mã nội dung chuyển khoản bắt buộc và đồng hồ đếm ngược thời gian còn lại của đơn hàng (15 phút). Hệ thống thông báo kết quả sẽ tự động được cập nhật khi thanh toán hoàn tất (`UC-ACC-07`). Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **4a. Tái sử dụng đơn thanh toán đang chờ còn thời hạn hiệu lực**:
  1. Hệ thống phát hiện Người học đang có một đơn thanh toán ở trạng thái `PENDING` với thời gian hiệu lực còn lại ($> 0$ giây).
  2. Hệ thống tái sử dụng ngay đơn hàng này, không phát sinh đơn trùng lặp, giữ nguyên mã QR và đồng hồ đếm ngược thời gian còn lại.
  3. Hệ thống chuyển thẳng sang bước 7 của luồng chính.
- **7a. Người học đang ở gói Premium mua gia hạn sớm**:
  1. Tại bước 3, Người học đang sở hữu gói Premium còn thời hạn bấm chọn "Gia hạn thêm 30 ngày".
  2. Hệ thống hiển thị thông báo rõ ràng: "Thời hạn mới sẽ được cộng dồn tiếp nối vào hạn sử dụng hiện tại sau khi thanh toán thành công" (`BR-PAY-03`).
  3. Tiếp tục từ bước 4 của luồng chính.
- **7b. Người học chủ động hủy đơn thanh toán đang chờ**:
  1. Trong khi đồng hồ 15 phút đang đếm ngược, Người học chọn nút "Hủy đơn thanh toán này".
  2. Hệ thống cập nhật trạng thái đơn hàng sang `CANCELLED` và đóng màn hình chờ thanh toán. Use case kết thúc.
- **2a. Luồng phụ — Xem lịch sử giao dịch thanh toán**:
  1. Tại trang Quản lý gói cước, Người học chọn tab "Lịch sử giao dịch".
  2. Hệ thống truy xuất và hiển thị danh sách các đơn thanh toán trong quá khứ kèm mã đơn, ngày tạo, số tiền, phương thức và trạng thái (`PAID`, `EXPIRED`, `CANCELLED`, `FAILED`). Người học có thể tải hóa đơn điện tử cho các đơn `PAID`.

**Luồng ngoại lệ (Exception Flows)**:
- **6e. Cổng thanh toán không phản hồi hoặc báo lỗi khởi tạo**:
  1. Hệ thống không thể lấy được mã QR từ Cổng thanh toán sau 2 lần thử lại tự động.
  2. Hệ thống chuyển đơn thanh toán sang trạng thái `FAILED`, thông báo dịch vụ thanh toán đang bảo trì hoặc gián đoạn tạm thời và đề nghị người học quay lại sau vài phút.
  3. Use case kết thúc (thất bại).
- **7e. Hết thời gian chờ thanh toán 15 phút**:
  1. Người học vẫn giữ màn hình thanh toán nhưng đồng hồ đếm ngược 15 phút chạm mốc 0:00 mà chưa phát sinh giao dịch.
  2. Hệ thống thông báo đơn thanh toán đã hết hạn hiệu lực, vô hiệu hóa mã QR hiển thị và hướng dẫn người học bấm nút để tạo đơn mới nếu vẫn có nhu cầu.
  3. Use case kết thúc.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-PAY-01 (Mức giá và định mức gói dịch vụ — D7)**: Gói Premium có mức giá niêm yết cố định là 99.000 VNĐ cho mỗi chu kỳ 30 ngày, cung cấp định mức 300 lượt gọi AI/tháng và cho phép tối đa 15 lộ trình hoạt động đồng thời.
- **BR-PAY-02 (Thời hạn hiệu lực đơn thanh toán)**: Mỗi đơn thanh toán có hiệu lực tối đa 15 phút kể từ thời điểm khởi tạo. Tại một thời điểm, mỗi người học chỉ được phép tồn tại tối đa một đơn thanh toán ở trạng thái `PENDING`.
- **BR-PAY-03 (Quy tắc cộng dồn gia hạn — D7)**: Khi người dùng đang ở gói Premium thực hiện thanh toán gia hạn thành công, mốc hết hạn mới được tính theo công thức: `Thời hạn mới = MAX(Thời hạn hiện tại, Thời điểm hiện tại) + 30 ngày`.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Lựa chọn nâng cấp hoặc gia hạn gói cước của Người học.
- **Đầu ra**: Đơn giao dịch thanh toán (`PENDING`, thời hạn 15 phút), mã QR chuyển khoản, nội dung đối soát và đồng hồ đếm ngược.

---

#### UC-ACC-07: Xử lý thông báo kết quả thanh toán

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ACC-07** |
| **Tên Use Case** | **Xử lý thông báo kết quả thanh toán** |
| **Mô tả ngắn** | Cổng thanh toán gửi thông báo kết quả giao dịch bất đồng bộ (Webhook) về hệ thống; hệ thống xác thực chữ ký bảo mật, kiểm tra tính lũy đẳng chống xử lý trùng lặp, chuyển trạng thái đơn thanh toán sang `PAID` và tự động kích hoạt nâng gói hoặc gia hạn gói Premium cho tài khoản Người học. |
| **Tác nhân chính** | Cổng thanh toán (`Payment Gateway` — `ACT-05`) |
| **Tác nhân phụ** | Không có |
| **Mức độ** | Mục tiêu hệ thống tích hợp (System-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Cổng thanh toán phát lệnh gọi Webhook HTTP POST chứa dữ liệu giao dịch đến điểm tiếp nhận của FocusFlow. |
| **Tiền điều kiện** | Đơn giao dịch thanh toán tương ứng đã được khởi tạo trong hệ thống trước đó (`UC-ACC-06`). |
| **Hậu điều kiện – thành công** | Trạng thái đơn thanh toán được cập nhật nguyên tử sang `PAID`; tài khoản Người học được nâng hạng lên `PREMIUM` hoặc cộng thêm 30 ngày thời hạn; trần lộ trình hoạt động nâng lên 15 và hạn ngạch AI nâng lên 300 lượt/tháng; phản hồi mã 200 OK cho Cổng thanh toán. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Thông báo sai chữ ký hoặc sai số tiền bị từ chối; không cấp quyền lợi gói Premium; ghi nhận cảnh báo bảo mật. |
| **Include / Extend** | Không có |
| **Tần suất / Độ ưu tiên** | Trung bình (Tự động theo giao dịch) / Cực kỳ quan trọng (P0 — Must have) |
| **Tham chiếu SRS** | `FR-QUOTA-002`, `BUSR-10`, `D3`, `D7` |

**Luồng chính (Basic Flow)**:
1. Cổng thanh toán gửi thông báo Webhook chứa mã đơn hàng, số tiền thực nhận, mã giao dịch phía cổng, trạng thái thanh toán và chuỗi chữ ký điện tử xác thực.
2. Hệ thống tiếp nhận thông báo và tiến hành xác minh tính toàn vẹn thông qua việc giải mã và đối chiếu chữ ký điện tử HMAC-SHA256 (`BR-PAY-04`).
3. Hệ thống tra cứu đơn thanh toán trong kho dữ liệu dựa trên mã đơn hàng nhận được.
4. Hệ thống kiểm tra tính lũy đẳng: xác nhận đơn hàng đang ở trạng thái chờ xử lý (`PENDING`) và số tiền thực nhận khớp đúng 99.000 VNĐ (`BR-PAY-04`).
5. Hệ thống thực hiện giao dịch cập nhật nguyên tử:
   - Cập nhật trạng thái đơn thanh toán thành `PAID` kèm mã tham chiếu giao dịch cổng và thời điểm thanh toán thành công.
   - Nâng cấp gói dịch vụ của tài khoản Người học lên `PREMIUM`.
   - Tính toán và cập nhật thời điểm hết hạn gói Premium: cộng thêm 30 ngày kể từ mốc hiện tại hoặc cộng dồn vào thời hạn cũ nếu đang là Premium (`BR-PAY-03`).
   - Cập nhật trần số lộ trình hoạt động lên tối đa 15 lộ trình và nâng hạn ngạch gọi AI tháng lên 300 lượt.
6. Hệ thống ghi nhật ký giao dịch tài chính thành công vào hệ thống kiểm toán.
7. Hệ thống phản hồi mã trạng thái 200 OK xác nhận đã xử lý hoàn tất cho Cổng thanh toán. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **4a. Xử lý thông báo thành công cho đơn thanh toán đã hết hạn (EXPIRED -> PAID có kiểm soát — D3)**:
  1. Tại bước 4, hệ thống phát hiện đơn thanh toán trong hệ thống đang ở trạng thái `EXPIRED` (do người dùng chuyển khoản trễ sau 15 phút).
  2. Hệ thống kiểm tra chữ ký HMAC hợp lệ và số tiền chuyển khoản khớp đúng 99.000 VNĐ.
  3. Hệ thống cho phép chuyển trạng thái đơn hàng từ `EXPIRED` sang `PAID`, đồng thời gắn cờ kiểm toán đối soát trễ `late_payment_reconciled = true` (`BR-PAY-05`).
  4. Hệ thống tiến hành nâng cấp gói Premium cho Người học bình thường như bước 5 của luồng chính và ghi nhận nhật ký kiểm toán đặc biệt.
  5. Tiếp tục bước 7 để phản hồi thành công cho Cổng thanh toán.
- **4b. Cổng thanh toán gửi thông báo giao dịch thất bại hoặc bị hủy**:
  1. Thông báo Webhook chỉ ra giao dịch không thành công từ phía ngân hàng của người dùng.
  2. Hệ thống cập nhật trạng thái đơn hàng sang `FAILED`.
  3. Không thay đổi quyền lợi hay gói dịch vụ của Người học.
  4. Hệ thống phản hồi 200 OK để Cổng thanh toán không gửi lại thông báo. Use case kết thúc.
- **4c. Thông báo Webhook bị gửi lặp lại (Idempotent Webhook Retry)**:
  1. Cổng thanh toán gửi lại Webhook cho một đơn hàng đã được cập nhật thành `PAID` trước đó.
  2. Hệ thống nhận diện đơn hàng đã hoàn tất, không thực hiện cộng thời hạn hay nâng cấp lặp lại lần 2.
  3. Hệ thống trả ngay mã 200 OK để xác nhận đã tiếp nhận thành công. Use case kết thúc.

**Luồng ngoại lệ (Exception Flows)**:
- **2e. Chữ ký xác thực HMAC không hợp lệ hoặc dữ liệu bị giả mạo**:
  1. Việc tính toán chữ ký số từ nội dung thông báo không khớp với chữ ký gửi kèm từ Cổng thanh toán.
  2. Hệ thống lập tức từ chối xử lý, ghi nhận cảnh báo an ninh nghiêm trọng về nghi vấn giả mạo Webhook.
  3. Hệ thống phản hồi mã lỗi 401 Unauthorized / 400 Bad Request cho bên gửi.
  4. Use case kết thúc (thất bại).
- **4e. Số tiền thanh toán không khớp đúng mức phí gói (99.000 VNĐ)**:
  1. Số tiền trong thông báo Webhook sai lệch so với giá trị 99.000 VNĐ của đơn hàng.
  2. Hệ thống ghi nhận đơn hàng ở trạng thái lỗi đối soát tiền `DISCREPANCY_HOLD`, không tự động kích hoạt gói Premium.
  3. Hệ thống gửi cảnh báo đến kênh quản trị để Quản trị viên can thiệp đối soát thủ công (`UC-ADM-04`).
  4. Use case kết thúc (thất bại).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-PAY-04 (Bảo mật Webhook và Tính lũy đẳng)**: Mọi thông báo Webhook bắt buộc phải được ký số bằng thuật toán HMAC-SHA256 với khóa bí mật chia sẻ trước. Hệ thống phải đảm bảo tính lũy đẳng (Idempotency) tuyệt đối: việc nhận nhiều lần cùng một thông báo không bao giờ dẫn đến việc cộng dồn thời hạn gói nhiều lần.
- **BR-PAY-05 (Cơ chế chuyển trạng thái EXPIRED sang PAID có kiểm soát — D3)**: Cho phép chuyển trạng thái từ `EXPIRED` sang `PAID` duy nhất khi hội đủ 3 điều kiện: (1) Chữ ký số HMAC-SHA256 hoàn toàn hợp lệ, (2) Số tiền thực nhận khớp đúng 99.000 VNĐ, và (3) Gắn cờ ghi chú `late_payment_reconciled = true` kèm nhật ký kiểm toán phục vụ tra soát.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Dữ liệu Webhook từ Cổng thanh toán (mã đơn, số tiền, mã giao dịch, chữ ký HMAC).
- **Đầu ra**: Đơn hàng chuyển sang `PAID`, tài khoản người học nâng cấp/gia hạn gói `PREMIUM`, phản hồi HTTP 200 OK.

---

#### UC-ACC-08: Dọn bản ghi giữ chỗ và đơn thanh toán treo

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ACC-08: Dọn bản ghi giữ chỗ và đơn thanh toán treo** |
| **Mức độ & Phân tầng** | Mục tiêu hệ thống nền (System-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Quản trị viên hệ thống (`Administrator — ACT-03`), Người học (`Learner — ACT-02`) *(Kích hoạt tự động theo sự kiện thời gian nội bộ — OMG UML TimeEvent)* |
| **Tác nhân phụ** | Không có |
| **Trigger** | Tác vụ nền được kích hoạt định kỳ theo lịch trình cấu hình sẵn (mỗi 5 phút) (`OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Hệ thống vận hành bình thường; lịch trình quét định kỳ 5 phút được kích hoạt. |
| **Hậu điều kiện thành công** | Các bản ghi giữ chỗ hạn ngạch AI quá hạn 5 phút được chuyển sang `EXPIRED`; các đơn thanh toán `PENDING` quá thời hạn 15 phút được chuyển sang `EXPIRED`. |
| **Bảo đảm tối thiểu** | Các đơn thanh toán và bản ghi giữ chỗ còn trong thời hạn hiệu lực được giữ nguyên vẹn. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-QUOTA-001`, `FR-QUOTA-002`, `D3` |

- **Luồng chính (Basic Flow)**:
  1. Sự kiện thời gian định kỳ (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ dọn dẹp tài nguyên treo theo chu kỳ 5 phút một lần.
  2. Hệ thống quét các bản ghi giữ chỗ hạn ngạch AI đang ở trạng thái `RESERVED` có thời điểm tạo vượt quá 5 phút mà chưa được xác nhận hoàn tất.
  3. Hệ thống chuyển trạng thái các bản ghi giữ chỗ này sang `EXPIRED` và hoàn lại định mức khả dụng cho người dùng (`BR-QUOTA-03`).
  4. Hệ thống quét danh sách các đơn thanh toán đang ở trạng thái `PENDING` có thời điểm hết hạn nhỏ hơn thời điểm hiện tại (`expires_at < NOW()`).
  5. Hệ thống cập nhật trạng thái các đơn thanh toán này từ `PENDING` sang `EXPIRED`. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **2a. Không có bản ghi nào bị treo**: Hệ thống hoàn thành lượt quét trong thời gian dưới 10ms và ghi nhận trạng thái bình thường.

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Lỗi kết nối cơ sở dữ liệu khi dọn dẹp**: Hệ thống ghi nhật ký cảnh báo lỗi và tự động kích hoạt lại tác vụ dọn dẹp trong chu kỳ quét 5 phút kế tiếp; không làm gián đoạn các luồng nghiệp vụ khác.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-QUOTA-03 (Thời hạn giữ chỗ hạn ngạch AI — JIT Reservation)**: Bản ghi giữ chỗ hạn ngạch AI chỉ có hiệu lực tối đa 5 phút. Nếu sau 5 phút không có lệnh xác nhận tiêu thụ (COMMIT) hoặc hoàn trả (RELEASE), hệ thống tự động thu hồi để tránh chiếm dụng tài nguyên.
  - **BR-PAY-06 (Thời hạn đóng đơn PENDING)**: Đơn thanh toán PENDING tự động chuyển trạng thái EXPIRED sau khi hết hạn 15 phút nếu chưa tiếp nhận được thông báo Webhook thanh toán thành công.

---

#### UC-ACC-09: Làm mới hạn ngạch chu kỳ tháng

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ACC-09: Làm mới hạn ngạch chu kỳ tháng** |
| **Mức độ & Phân tầng** | Mục tiêu hệ thống nền (System-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`Learner — ACT-02`) *(Kích hoạt tự động theo sự kiện thời gian nội bộ — OMG UML TimeEvent)* |
| **Tác nhân phụ** | Không có |
| **Trigger** | Thời điểm hệ thống chạm mốc 00:00 ngày đầu tiên của tháng dương lịch mới (theo chuẩn UTC) (`OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Tác vụ định kỳ đầu tháng được kích hoạt vào lúc 00:00 ngày 01 hàng tháng (theo chuẩn UTC). |
| **Hậu điều kiện thành công** | Số lượt gọi AI đã dùng trong tháng được đặt lại về 0 cho toàn bộ tài khoản người dùng; khôi phục đầy đủ hạn ngạch theo gói dịch vụ hiện hành. |
| **Bảo đảm tối thiểu** | Quá trình cập nhật được phân khối an toàn, không làm gián đoạn các yêu cầu học tập thời gian thực. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-QUOTA-001` |

- **Luồng chính (Basic Flow)**:
  1. Sự kiện thời gian định kỳ (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ làm mới hạn ngạch vào đúng 00:00 ngày 01 hàng tháng (giờ UTC).
  2. Hệ thống phân chia toàn bộ tài khoản người dùng đang hoạt động thành các khối xử lý độc lập (mỗi khối 500 tài khoản).
  3. Với từng khối, hệ thống thực hiện đặt lại bộ đếm số lượt gọi AI đã tiêu thụ trong tháng về 0 (`BR-QUOTA-04`).
  4. Hệ thống thiết lập lại mức hạn ngạch khả dụng căn cứ theo gói dịch vụ hiện tại của từng người dùng: 30 lượt đối với tài khoản `FREE` và 300 lượt đối với tài khoản `PREMIUM`.
  5. Hệ thống ghi nhật ký vận hành hoàn tất chu kỳ làm mới hạn ngạch tháng. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **2a. Không có tài khoản hoạt động**: Tác vụ quét hoàn tất sau 5ms, ghi nhật ký không có tài khoản cần cập nhật.

- **Luồng ngoại lệ (Exception Flows)**:
  - **3e. Một khối xử lý gặp sự cố cơ sở dữ liệu**: Hệ thống cô lập khối bị lỗi, ghi nhật ký cảnh báo và tự động thử lại khối đó sau 30 giây mà không ảnh hưởng đến các khối đã hoàn thành thành công.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-QUOTA-04 (Chính sách không cộng dồn hạn ngạch tháng)**: Số lượt gọi AI chưa sử dụng hết trong tháng trước sẽ tự động mất đi và không được cộng dồn sang tháng tiếp theo. Đầu tháng mới, tài khoản nhận đúng định mức chuẩn của gói hiện hành.

---

#### UC-ACC-10: Hạ cấp gói dịch vụ hết hạn

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ACC-10** |
| **Tên Use Case** | **Hạ cấp gói dịch vụ hết hạn** |
| **Mô tả ngắn** | Tác vụ nền theo lịch trình thời gian quét định kỳ hàng ngày để phát hiện các tài khoản người dùng có thời hạn gói Premium đã kết thúc; hệ thống tự động chuyển tài khoản về gói `FREE`, điều chỉnh hạn ngạch AI và tự động áp dụng quy tắc Ưu tiên hạn hoàn thành sớm nhất (EDF) để giữ lại tối đa 3 lộ trình hoạt động, tạm dừng các lộ trình vượt trần. |
| **Tác nhân chính** | Người học (`Learner — ACT-02`) *(Kích hoạt tự động theo sự kiện thời gian nội bộ — OMG UML TimeEvent)* |
| **Tác nhân phụ** | Không có |
| **Mức độ** | Mục tiêu hệ thống nền (System-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Tự động kích hoạt tác vụ quét vào lúc 00:10 UTC hàng ngày (`OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Có ít nhất một tài khoản người dùng đang ở gói `PREMIUM` có mốc thời gian hết hạn nhỏ hơn thời điểm quét (`premium_expires_at < NOW()`). |
| **Hậu điều kiện – thành công** | Gói dịch vụ của tài khoản được chuyển về `FREE`; hạn ngạch AI được đưa về định mức chuẩn gói Free (30 lượt/tháng); nếu người dùng có trên 3 lộ trình đang hoạt động (`ACTIVE`), hệ thống tự động giữ 3 lộ trình ưu tiên nhất và chuyển các lộ trình còn lại sang trạng thái tạm dừng (`PAUSED`). |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Tài khoản Premium còn hạn không bị ảnh hưởng; dữ liệu bài học và lộ trình của người học được bảo lưu toàn vẹn 100%. |
| **Include / Extend** | Không có |
| **Tần suất / Độ ưu tiên** | Hàng ngày (00:10 UTC) / Quan trọng (P1 — Should have) |
| **Tham chiếu SRS** | `FR-QUOTA-001`, `FR-QUOTA-002`, `FR-PLAN-006`, `BUSR-10` |

**Luồng chính (Basic Flow)**:
1. Sự kiện thời gian định kỳ (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ quét hạ cấp gói dịch vụ hết hạn lúc 00:10 UTC.
2. Hệ thống tìm kiếm danh sách các tài khoản đang ở gói dịch vụ `PREMIUM` có thời điểm hết hạn nhỏ hơn thời điểm hiện tại (`premium_expires_at < NOW()`).
3. Với mỗi tài khoản tìm thấy, hệ thống thực hiện hạ cấp gói dịch vụ từ `PREMIUM` về `FREE`.
4. Hệ thống điều chỉnh lại hạn mức trần gọi AI tháng về 30 lượt. Nếu số lượt đã dùng trong tháng vượt quá 30, số dư khả dụng sẽ về 0 (không phạt âm).
5. Hệ thống kiểm tra số lượng lộ trình đang ở trạng thái hoạt động (`ACTIVE`) của tài khoản:
   - Nếu số lộ trình `ACTIVE` $> 3$, hệ thống áp dụng thuật toán Lập lịch ưu tiên hạn chót sớm nhất (Earliest Deadline First — EDF, `BR-DOWN-01`) để sắp xếp danh sách các lộ trình theo ngày mục tiêu hoàn thành (`target_date`) tăng dần.
   - Hệ thống giữ lại đúng 03 lộ trình có ngày mục tiêu hoàn thành sớm nhất tiếp tục ở trạng thái `ACTIVE`.
   - Toàn bộ các lộ trình `ACTIVE` còn lại vượt quá trần 3 lộ trình được hệ thống tự động chuyển sang trạng thái tạm dừng (`PAUSED`) kèm ghi chú hệ thống: "Tự động tạm dừng do hạ cấp về gói Free (vượt trần 3 lộ trình hoạt động)".
6. Hệ thống tạo thông báo trong ứng dụng gửi đến Người học giải thích rõ về việc gói cước đã hết hạn, các lộ trình đã được tự động tạm dừng và hướng dẫn nâng cấp lại nếu muốn mở khóa toàn bộ.
7. Hệ thống ghi nhật ký kiểm toán cho từng trường hợp hạ cấp. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **5a. Tài khoản chỉ có từ 3 lộ trình hoạt động trở xuống ($\le 3$ ACTIVE)**:
  1. Hệ thống nhận thấy số lộ trình hoạt động không vượt quá trần quy định của gói `FREE`.
  2. Hệ thống giữ nguyên trạng thái `ACTIVE` cho toàn bộ các lộ trình hiện có, không cần chuyển lộ trình nào sang `PAUSED`.
  3. Chuyển tiếp sang bước 6 của luồng chính.
- **5b. Lộ trình không có ngày mục tiêu hoàn thành (Target Date rỗng)**:
  1. Khi sắp xếp theo thuật toán EDF, các lộ trình không khai báo ngày mục tiêu sẽ được xếp độ ưu tiên dựa trên thời điểm có phiên học tập gần nhất (`last_study_activity_at`).
  2. Tiếp tục quy trình phân loại giữ lại 3 lộ trình và tạm dừng phần còn lại theo luồng chính.

**Luồng ngoại lệ (Exception Flows)**:
- **2e. Tiến trình quét gặp sự cố kết nối dữ liệu**:
  1. Hệ thống ghi nhật ký lỗi chi tiết và tự động lên lịch chạy lại tác vụ quét sau 15 phút.
  2. Use case kết thúc (thất bại tạm thời).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-DOWN-01 (Thuật toán EDF điều tiết trần lộ trình gói Free)**: Người dùng gói `FREE` chỉ được phép duy trì tối đa 03 lộ trình ở trạng thái `ACTIVE` đồng thời. Khi bị hạ cấp từ Premium về Free, hệ thống áp dụng thuật toán Earliest Deadline First (EDF) để giữ lại 3 lộ trình có hạn chót sớm nhất; toàn bộ các lộ trình còn lại buộc phải chuyển sang trạng thái `PAUSED`.
- **BR-DOWN-02 (Bảo toàn dữ liệu khi hạ cấp)**: Thao tác hạ cấp gói dịch vụ và tạm dừng lộ trình tuyệt đối không xóa bỏ bất kỳ cột mốc, bài học, ghi chú đúc kết hay lịch sử học tập nào của người dùng. Khi người dùng nâng cấp lại gói Premium, các lộ trình `PAUSED` có thể được kích hoạt lại bình thường thông qua `UC-ADAPT-05`.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Danh sách các tài khoản có gói cước Premium đã hết hạn.
- **Đầu ra**: Tài khoản chuyển về gói `FREE`, các lộ trình vượt trần chuyển sang `PAUSED`, thông báo giải thích gửi cho người học và nhật ký kiểm toán hệ thống.

---

#### UC-ACC-11: Quản lý ghi chú thói quen học tập (Structured Learner Memory Governance)

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ACC-11: Quản lý ghi chú thói quen học tập** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Không có *(Tương tác trực tiếp cơ sở dữ liệu nội bộ, tiêu tốn 0 lượt gọi AI)* |
| **Tiền điều kiện** | Người học đã đăng nhập hệ thống, truy cập màn hình Cài đặt Hồ sơ & Bộ nhớ Người học (`settings/learner-memory`). |
| **Hậu điều kiện thành công** | Người học xem danh sách mục nhớ phân loại theo 4 danh mục (`PROFILE`, `BEHAVIORAL`, `KNOWLEDGE`, `INTERACTION`) và 3 mức độ nhận thức (`EXPLICIT`, `OBSERVED`, `INFERRED`); kiểm tra 7 trường siêu dữ liệu của các nhận định suy luận; thực hiện xác nhận (`CONFIRMED`), chỉnh sửa (`EDITED`) hoặc từ chối (`REJECTED`) các nhận định suy luận của AI; xem ma trận năng lực khái niệm (`Skill Mastery`); hoặc khôi phục hồ sơ về trạng thái ban đầu (`Cold-Start Reset`). |
| **Bảo đảm tối thiểu** | Nếu người học hủy thao tác hoặc xảy ra lỗi mạng, trạng thái bộ nhớ hiện tại được giữ nguyên vẹn 100%. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-PROFILE-001` (Structured Learner Memory), `SRS UC-03`, `BUSR-10`, `BUSR-12`, `ADR-010` |

- **Luồng chính (Basic Flow)**:
  1. Người học truy cập trang Quản trị Bộ nhớ Người học (`settings/learner-memory`).
  2. Hệ thống tải và hiển thị danh mục các mục nhớ dài hạn (`Learner Memory Items`) được chia thành 4 nhóm ngữ cảnh: Thông tin cá nhân & phong cách (`PROFILE`), Thói quen & hành vi học tập (`BEHAVIORAL`), Năng lực & mức độ nắm vững tri thức (`KNOWLEDGE`), Tương tác & phản hồi lịch sử (`INTERACTION`).
  3. Mỗi mục nhớ được gắn nhãn mức độ nhận thức minh bạch: Khai báo tường minh (`EXPLICIT`), Quan sát hành vi khách quan (`OBSERVED`), hoặc Suy luận từ AI (`INFERRED`).
  4. Người học chọn xem chi tiết một nhận định suy luận (`INFERRED`). Hệ thống hiển thị đầy đủ 7 trường siêu dữ liệu kiểm toán chuẩn hóa theo `FR-PROFILE-001`:
     - (1) Giá trị nhận định có cấu trúc (`claim_value` dạng JSONB),
     - (2) Bằng chứng nguồn gốc thực chứng (`source_evidence`),
     - (3) Quy mô mẫu quan sát (`sample_size` $\ge 3$ phiên học/nhiệm vụ),
     - (4) Điểm tin cậy thống kê (`confidence_score` từ 0.0 đến 1.0, yêu cầu $\ge 0.70$),
     - (5) Thời điểm kiểm chứng gần nhất (`last_validated_at`),
     - (6) Trạng thái xác nhận (`status`: `'INFERRED'`, `'CONFIRMED'`, `'EDITED'`, `'REJECTED'`),
     - (7) Cờ cảnh báo trôi dạt nhận thức (`drift_flag`: `BOOLEAN`).
  5. Người học cũng có thể chuyển sang thẻ Ma trận Năng lực Khái niệm (`Skill Mastery Matrix`) để xem mức độ làm chủ kiến thức (`NOVICE`, `BEGINNER`, `COMPETENT`, `PROFICIENT`, `EXPERT`) được tích lũy xuyên suốt qua nhiều lộ trình.
  6. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **4a. Người học xác nhận, chỉnh sửa hoặc từ chối nhận định suy luận AI**:
    1. Tại mục nhớ suy luận đang ở trạng thái `PENDING`, Người học chọn **Xác nhận (Confirm)**, **Sửa nội dung (Edit)** hoặc **Từ chối (Reject)**.
    2. Nếu chọn Confirm: Hệ thống chuyển trạng thái sang `CONFIRMED`, nâng bậc ưu tiên nhận thức lên ngang mức tường minh, ghi nhận thời điểm xác nhận.
    3. Nếu chọn Edit: Người học chỉnh sửa giá trị nội dung; hệ thống lưu nội dung mới, chuyển trạng thái sang `EDITED` và lưu vết bản gốc trong nhật ký.
    4. Nếu chọn Reject: Hệ thống chuyển trạng thái sang `REJECTED` (Soft-delete / Suppressed) và lập tức loại bỏ mục nhớ này khỏi ngữ cảnh cung cấp cho các lần gọi Prompt tiếp theo của AI Harness Runtime.
    5. Hệ thống hiển thị thông báo cập nhật thành công và làm mới danh sách.
  - **5a. Người học thực hiện Khôi phục khởi đầu lạnh (Cold-Start Reset)**:
    1. Người học nhấn nút **"Khôi phục Hồ sơ Học tập Ban đầu (Cold-Start Reset)"**.
    2. Hệ thống hiển thị hộp thoại cảnh báo kèm hai lựa chọn phạm vi: (a) *Chỉ xóa nhận định suy luận và thói quen hành vi* (giữ lại thông tin cá nhân và ma trận Skill Mastery đã kiểm chứng), hoặc (b) *Xóa toàn bộ bộ nhớ và ma trận năng lực về mặc định ban đầu*.
    3. Người học chọn phạm vi và nhập xác nhận để phê duyệt.
    4. Hệ thống thực thi xóa/thu hồi các mục nhớ theo phạm vi đã chọn, đặt lại cờ Cold-Start cho hồ sơ người học và ghi nhật ký kiểm toán.

- **Luồng ngoại lệ (Exception Flows)**:
  - **4e. Xung đột chỉnh sửa đồng thời**: Nếu mục nhớ đã bị cập nhật bởi tiến trình nền khác, hệ thống tải lại dữ liệu mới nhất và yêu cầu người học thao tác lại.

- **Quy tắc nghiệp vụ (Business Rules)**:
  - **BR-MEM-01 (Thứ bậc Nhận thức & Quyền phủ quyết của Người học — Epistemic Hierarchy)**: Dữ liệu do người học khai báo tường minh (`EXPLICIT`) và dữ liệu suy luận đã được người học xác nhận (`CONFIRMED`/`EDITED`) luôn có độ ưu tiên nhận thức cao nhất. AI Harness Runtime tuyệt đối không được sử dụng các nhận định đã bị từ chối (`REJECTED`) để xây dựng Context Prompt.
  - **BR-MEM-02 (Minh bạch Nguồn gốc Suy luận — Provenance Audit Trail)**: Mọi nhận định do AI suy luận (`INFERRED`) bắt buộc phải lưu kèm đầy đủ 7 trường siêu dữ liệu kiểm toán. Hệ thống không lưu trữ bất kỳ nhận định "hộp đen" nào không rõ căn cứ bằng chứng.
  - **BR-MEM-03 (Không tiêu tốn Hạn ngạch AI)**: Toàn bộ các thao tác tra cứu, phân loại, xác nhận, chỉnh sửa và khôi phục bộ nhớ tại `UC-ACC-11` được xử lý tất định thông qua truy vấn cơ sở dữ liệu nội bộ, hoàn toàn không tiêu tốn hạn ngạch gọi AI (`AI Quota = 0`).

---

### PHÂN HỆ 2: KHỞI TẠO & LẬP KẾ HOẠCH LỘ TRÌNH

Phân hệ bao gồm 10 Use Cases chịu trách nhiệm thấu hiểu mục tiêu học tập, sinh khung kiến thức, phân rã nhiệm vụ chi tiết, lập lịch học thích ứng, mô phỏng kịch bản giả định và kiểm định chặt chẽ tính hợp lệ của thời khóa biểu.

```
Sơ đồ 2: Khởi tạo & Lập kế hoạch Lộ trình (UC-PLAN-01, UC-PLAN-02, UC-PLAN-03, UC-PLAN-04, UC-PLAN-05, UC-PLAN-06, UC-PLAN-07, UC-PLAN-08, UC-PLAN-09, UC-PLAN-10)
```

---

#### UC-PLAN-01: Tạo khung lộ trình bằng AI

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-PLAN-01** |
| **Tên Use Case** | **Tạo khung lộ trình bằng AI** |
| **Mô tả ngắn** | Người học nhập mục tiêu học tập, tải lên tài liệu tham khảo (PDF, DOCX, TXT) hoặc nhập URL tài liệu; hệ thống kiểm tra an toàn SSRF, trích xuất tri thức RAG (`Knowledge Ingestion`), vận hành phỏng vấn chẩn đoán phân tầng (`Diagnostic Interview`) có hỗ trợ tạm dừng/tiếp tục (`Pause/Resume`), kết hợp Hồ sơ người học (`Learner Model`) và tổng hợp khung Cột mốc kiến thức Cấp 1 sơ bộ kèm nguồn trích dẫn tri thức để Người học phê duyệt. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04`) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học chọn "Tạo lộ trình bằng AI" từ bảng điều khiển chính hoặc trang danh mục lộ trình. |
| **Tiền điều kiện** | Người học đã đăng nhập; tài khoản chưa vượt trần số lộ trình hoạt động (`ACTIVE`) theo gói cước (FREE $\le 3$, PREMIUM $\le 15$); hạn ngạch AI tháng còn khả dụng ($> 0$). |
| **Hậu điều kiện – thành công** | Lộ trình mới được khởi tạo ở trạng thái vừa khởi tạo (`INITIALIZED`) hoặc hoạt động (`ACTIVE`); tài liệu học tập được chia đoạn và đánh chỉ mục ngữ nghĩa; quy trình phỏng vấn chẩn đoán lưu vết bền vững (`workflow_runs`); danh sách Cột mốc Cấp 1 (kèm tiêu chí hoàn thành và nguồn trích dẫn) được Người học phê duyệt; các khái niệm tri thức mới sinh được gắn trạng thái `UNVERIFIED` trong kho tri thức; trừ 1 lượt hạn ngạch AI thực tế. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Không tạo lộ trình rác; hạn ngạch AI được hoàn trả nguyên vẹn nếu xảy ra lỗi gọi dịch vụ AI. |
| **Include / Extend** | Không có |
| **Tần suất / Độ ưu tiên** | Trung bình / Cực kỳ quan trọng (P0 — Must have) |
| **Tham chiếu SRS** | `FR-GOAL-001`, `FR-GOAL-002`, `FR-GOAL-003`, `FR-PLAN-001`, `FR-QUOTA-001`, `FR-AI-001`, `FR-AI-002`, `D2` |

**Luồng chính (Basic Flow)**:
1. Người học nhập mục tiêu học tập ban đầu (tên mục tiêu, mô tả, trình độ hiện tại, thời lượng học mong muốn, deadline mục tiêu) và có thể tải lên tệp tài liệu (PDF, DOCX, TXT $\le 20$MB theo `FR-GOAL-003`) hoặc đường dẫn URL học liệu.
2. Hệ thống kiểm tra số lộ trình `ACTIVE` hiện tại của tài khoản (`BR-PLAN-01`) và kiểm tra số dư hạn ngạch AI khả dụng (`BR-QUOTA-01`).
3. Nếu có tài liệu đính kèm hoặc URL:
   - Hệ thống quét kiểm tra an toàn SSRF đối với URL (`BR-SEC-SSRF`).
   - Hệ thống thực hiện bóc tách nội dung, phân đoạn văn bản (`Chunking`), trích xuất provenance và lưu trữ chỉ mục hỗn hợp từ khóa & vector ngữ nghĩa (`Knowledge Ingestion`). Toàn bộ ngữ cảnh tri thức ngoài được bọc an toàn trong thẻ `<untrusted_knowledge_context>` để ngăn chặn tấn công Prompt Injection (`BR-SEC-INJECT`).
4. Hệ thống khởi tạo phiên quy trình có lưu trạng thái bền vững (`workflow_runs`), thực hiện giữ chỗ 1 lượt gọi AI (JIT Reservation) và kích hoạt AI sinh 3–5 câu hỏi phỏng vấn chẩn đoán phân tầng (`Diagnostic Interview` theo `FR-GOAL-002`) dựa trên mục tiêu, tài liệu nạp vào và Bộ nhớ Người học hiện có (`Learner Memory Items`).
5. Hệ thống hiển thị các câu hỏi phỏng vấn chẩn đoán từng lượt. Người học nhập câu trả lời hoặc chọn phương án gợi ý.
6. Hệ thống tập hợp Learning Context hoàn chỉnh (Goal Context + Material Context + Interview Context + Learner Profile & Memory) và gửi yêu cầu sinh khung lộ trình sang LLM Provider với yêu cầu phản hồi JSON có cấu trúc (bao gồm: tên lộ trình chuẩn hóa, mô tả mục tiêu, 3–7 Cột mốc kiến thức Cấp 1 tuần tự, kết quả học tập kỳ vọng, tiêu chí hoàn thành, ước lượng thời gian và liên kết trích dẫn học liệu `learning_resources_json`).
7. LLM Provider phản hồi dữ liệu trong thời gian cho phép ($\le 55$ giây). Hệ thống kiểm định cấu trúc JSON đầu ra (`BR-AI-01`).
8. Hệ thống xác nhận trừ 1 lượt hạn ngạch AI (COMMIT), cập nhật `workflow_runs` sang `COMPLETED`, khởi tạo bản ghi lộ trình ở trạng thái `INITIALIZED` và lưu các Cột mốc kiến thức. Các khái niệm học tập do AI đề xuất được gán trạng thái `UNVERIFIED` trong kho tri thức (`BR-KNOW-01`).
9. Hệ thống hiển thị danh sách các Cột mốc Cấp 1 kèm nguồn trích dẫn học liệu trên giao diện. Người học xem xét, có thể chỉnh sửa tên, sắp xếp lại thứ tự hoặc thêm/xóa cột mốc.
10. Người học nhấn nút **"Phê duyệt khung lộ trình"**. Hệ thống chuyển trạng thái lộ trình sang `ACTIVE` và điều hướng sang bước phân rã nhiệm vụ chi tiết (`UC-PLAN-02`). Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **5a. Người học tạm dừng phỏng vấn chẩn đoán để trả lời sau (Pause/Resume)**:
  1. Người học chọn "Lưu và tiếp tục sau".
  2. Hệ thống lưu trạng thái bước phỏng vấn và câu trả lời hiện tại vào bản ghi `workflow_runs` (`status = 'PAUSED_WAITING_USER'`).
  3. Khi Người học quay lại, hệ thống nạp lại ngữ cảnh từ `workflow_runs` và tiếp tục phỏng vấn từ câu hỏi còn dở dang mà không mất dữ liệu.
- **5b. Người học bỏ qua phỏng vấn chẩn đoán**:
  1. Người học chọn "Bỏ qua phỏng vấn và tạo nhanh".
  2. Hệ thống sử dụng các giả định mặc định từ mục tiêu ban đầu và chuyển tiếp sang bước 6.
- **9a. Người học không hài lòng với khung cột mốc và yêu cầu AI sinh lại**:
  1. Người học nhập thêm yêu cầu điều chỉnh (ví dụ: "Bổ sung phần học về Scikit-learn và triển khai mô hình").
  2. Hệ thống kiểm tra hạn ngạch AI, thực hiện giữ chỗ mới và gọi lại LLM Provider theo các bước 6–9.
- **10a. Người học lưu bản nháp để xem lại sau**:
  1. Người học chọn "Lưu bản thảo".
  2. Hệ thống lưu lộ trình ở trạng thái `INITIALIZED` để Người học có thể tiếp tục chỉnh sửa sau này. Use case kết thúc.

**Luồng ngoại lệ (Exception Flows)**:
- **1e. URL tài liệu vi phạm quy tắc an toàn SSRF hoặc định dạng tệp không hợp lệ**:
  1. Hệ thống phát hiện URL trỏ về dải IP nội bộ/loopback hoặc tệp vượt quá 20MB / định dạng không hỗ trợ.
  2. Hệ thống từ chối tệp/URL, hiển thị cảnh báo bảo mật và yêu cầu người học cung cấp đường dẫn hoặc tệp hợp lệ ($\le 20$MB theo `FR-GOAL-003`).
  3. Người học sửa lại học liệu hoặc tiếp tục mà không nạp tài liệu.
- **2e. Tài khoản đã đạt trần số lộ trình hoạt động (FREE: 3, PREMIUM: 15)**:
  1. Hệ thống hiển thị thông báo tài khoản đã đạt số lộ trình `ACTIVE` tối đa.
  2. Hệ thống hướng dẫn người học lưu trữ một lộ trình cũ (`UC-PLAN-06`) hoặc nâng cấp gói Premium (`UC-ACC-06`).
  3. Use case kết thúc (thất bại).
- **2e2. Hết hạn ngạch AI tháng**:
  1. Hệ thống thông báo số dư gọi AI tháng đã hết.
  2. Hệ thống hướng dẫn người học tạo lộ trình thủ công (`UC-PLAN-04`) hoặc nâng cấp gói cước.
  3. Use case kết thúc (thất bại).
- **7e. LLM Provider không phản hồi (quá 55s) hoặc cấu trúc dữ liệu lỗi (FR-AI-001 / FR-AI-002)**:
  1. Hệ thống tự động kích hoạt cơ chế thử lại tối đa 2 lần (`Auto-retry <= 2`) kèm phản hồi lỗi cấu trúc (Corrective Feedback Prompt) trong cùng một giao dịch giữ chỗ hạn ngạch (`RESERVED`), không trừ thêm quota của người học.
  2. Nếu sau 2 lần thử lại vẫn thất bại hoặc quá 55 giây, hệ thống giải phóng lượt giữ chỗ hạn ngạch (`RELEASE` — không trừ quota của người học), ghi nhận trạng thái `workflow_runs = FAILED`, thông báo lỗi dịch vụ AI tạm thời gián đoạn và hiển thị 2 lựa chọn: `[Thử lại (Retry)]` hoặc chuyển sang `[Tạo lộ trình thủ công (UC-PLAN-04)]`.
  3. Use case kết thúc (thất bại).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-PLAN-01 (Giới hạn số lộ trình hoạt động đồng thời)**: Tài khoản gói `FREE` được phép duy trì tối đa 03 lộ trình ở trạng thái `ACTIVE`; tài khoản gói `PREMIUM` được phép duy trì tối đa 15 lộ trình `ACTIVE`.
- **BR-PLAN-02 (Quy chuẩn Cột mốc kiến thức Cấp 1)**: Mỗi lộ trình học tập do AI đề xuất phải chứa từ 3 đến 7 cột mốc kiến thức được sắp xếp theo trình tự tăng dần độ phức tạp và bảo đảm tính sư phạm.
- **BR-KNOW-01 (Cơ chế gắn nhãn khái niệm sơ bộ — D2)**: Toàn bộ các khái niệm học tập và quan hệ tiên quyết do AI sinh ra trong quá trình tạo lộ trình mặc định mang trạng thái `UNVERIFIED`. Chỉ Quản trị viên (`UC-ADM-07`) mới có quyền thẩm định và nâng cấp khái niệm lên `VERIFIED` làm Ground Truth chuẩn mực.
- **BR-SEC-SSRF (Chặn dò quét mạng nội bộ SSRF)**: Mọi URL tài liệu do người học cung cấp phải được phân giải DNS và xác thực không thuộc dải địa chỉ IP riêng (RFC 1918), loopback (127.0.0.0/8), link-local hoặc metadata cloud (169.254.169.254).
- **BR-SEC-INJECT (Đóng gói Ngữ cảnh Tri thức Ngoại vi)**: Toàn bộ nội dung trích xuất từ tài liệu/URL bắt buộc phải được đóng gói bên trong thẻ `<untrusted_knowledge_context>` khi đưa vào prompt của LLM để triệt tiêu nguy cơ chiếm đoạt chỉ dẫn (Prompt Injection).

**Quản trị AI & An toàn**:
- **Cơ chế JIT Reservation**: Giữ chỗ hạn ngạch chỉ kích hoạt ngay tại bước 4 và bước 6, giải phóng ngay nếu người học hủy hoặc mạng lỗi.
- **Ngắt cứng 55 giây & Fallback**: Bảo đảm giao diện không bị treo vô hạn; nếu AI gặp sự cố, hệ thống không trừ hạn ngạch và cung cấp phương án tạo thủ công ngay lập tức.
- **Trạng thái quy trình bền vững (`workflow_runs`)**: Cho phép bảo lưu trạng thái tương tác qua nhiều bước API hoặc tạm dừng phỏng vấn mà không bị mất dữ liệu khi worker khởi động lại.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Mục tiêu học tập, trình độ hiện tại, tài liệu đính kèm / URL, câu trả lời phỏng vấn chẩn đoán, Bộ nhớ Người học.
- **Đầu ra**: Lộ trình mới (`ACTIVE`/`INITIALIZED`), danh sách Cột mốc Cấp 1 đã duyệt (kèm `learning_resources_json`), chỉ mục tri thức RAG, các khái niệm tri thức `UNVERIFIED`.

---

#### UC-PLAN-02: Tạo danh sách bài học bằng AI

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-PLAN-02** |
| **Tên Use Case** | **Tạo danh sách bài học bằng AI** |
| **Mô tả ngắn** | Người học yêu cầu AI phân rã các Cột mốc kiến thức Cấp 1 đã được phê duyệt thành danh sách các bài học/công việc chi tiết Cấp 2 có thời lượng chuẩn từ 30 đến 120 phút, gán nhịp năng lượng nhận thức và thiết lập đồ thị phụ thuộc tiên quyết (DAG). |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04`) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học chọn "Phân rã bài học bằng AI" sau khi duyệt khung cột mốc (`UC-PLAN-01`) hoặc từ màn hình chi tiết lộ trình. |
| **Tiền điều kiện** | Lộ trình đang ở trạng thái `ACTIVE` hoặc `INITIALIZED`, có ít nhất 01 Cột mốc chưa được phân rã; hạn ngạch AI còn lượt khả dụng. |
| **Hậu điều kiện – thành công** | Danh sách bài học chi tiết Cấp 2 được khởi tạo ở trạng thái `TODO` (chưa gán lịch: `scheduled_date = NULL`, chưa có `schedule_blocks`); thời lượng mỗi bài học chuẩn hóa 30–120 phút; quan hệ tiên quyết không chu trình (DAG) được thiết lập; trừ 1 lượt hạn ngạch AI. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Giữ nguyên danh sách bài học hiện có; hoàn trả hạn ngạch AI nếu có lỗi. |
| **Include / Extend** | Không có *(Việc xếp lịch vào thời khóa biểu được tách thành `UC-PLAN-03`)* |
| **Tần suất / Độ ưu tiên** | Trung bình / Quan trọng (P1 — Should have) |
| **Tham chiếu SRS** | `FR-PLAN-02`, `FR-TASK-001`, `FR-TASK-003`, `FR-AI-001`, `FR-AI-002` |

**Luồng chính (Basic Flow)**:
1. Người học chọn lộ trình và chỉ định các Cột mốc cần phân rã bài học chi tiết.
2. Hệ thống kiểm tra số dư hạn ngạch AI của Người học (`BR-QUOTA-01`).
3. Hệ thống thực hiện giữ chỗ 1 lượt gọi AI (JIT Reservation).
4. Hệ thống trích xuất thông tin các Cột mốc đã chọn và gửi yêu cầu sang LLM Provider với định dạng JSON schema nghiêm ngặt: yêu cầu sinh các bài học chi tiết Cấp 2 cho từng cột mốc, mỗi bài học có tên rõ ràng, mục tiêu cụ thể, thời lượng ước tính chuẩn từ 30 đến 120 phút (`BR-PLAN-03`), mức độ năng lượng nhận thức yêu cầu (`energyLevel: HIGH | MEDIUM | LOW`) và chỉ định các bài học điều kiện tiên quyết.
5. LLM Provider phản hồi dữ liệu trong thời gian tối đa 55 giây.
6. Hệ thống thực hiện kiểm định cấu trúc JSON và xác thực thuật toán: đảm bảo đồ thị quan hệ tiên quyết giữa các bài học không tồn tại chu trình khép kín (`BR-PLAN-04`).
7. Hệ thống chuyển đổi trạng thái giữ chỗ sang trừ 1 lượt hạn ngạch AI thực tế (COMMIT).
8. Hệ thống lưu danh sách các bài học mới vào lộ trình ở trạng thái `TODO` (chưa xếp lịch: `scheduled_date = NULL`).
9. Hệ thống hiển thị danh sách bài học phân rã theo từng cột mốc. Người học có thể xem xét, điều chỉnh thời lượng ước tính hoặc gán lại thứ tự phụ thuộc.
10. Người học bấm xác nhận "Hoàn tất phân rã nhiệm vụ" và chuẩn bị chuyển sang bước xếp lịch (`UC-PLAN-03`). Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **6a. AI sinh bài học có thời lượng ngoài khoảng chuẩn (ví dụ $> 120$ phút hoặc $< 30$ phút)**:
  1. Bộ chuẩn hóa dữ liệu của hệ thống tự động điều chỉnh: các bài học $> 120$ phút được chia nhỏ thành các phần liên tiếp (Part 1, Part 2); các bài học $< 30$ phút được gộp hợp lý vào bài học lân cận.
  2. Hệ thống ghi chú điều chỉnh tự động cho người học xem xét tại bước 9.
- **9a. Người học chỉnh sửa thủ công danh sách bài học**:
  1. Người học tự đổi tên bài học, xóa bớt bài không cần thiết hoặc thêm bài học cá nhân hóa.
  2. Hệ thống kiểm tra tính hợp lệ của quan hệ tiên quyết DAG và lưu lại các thay đổi. Tiếp tục bước 10.

**Luồng ngoại lệ (Exception Flows)**:
- **2e. Hạn ngạch AI tháng đã cạn kiệt**:
  1. Hệ thống thông báo hết hạn ngạch AI và gợi ý người học thêm bài học thủ công qua chức năng Quản lý công việc (`UC-PLAN-07`).
  2. Use case kết thúc (thất bại).
- **5e. LLM Provider bị ngắt kết nối hoặc phản hồi quá 55 giây**:
  1. Hệ thống hủy yêu cầu, hoàn trả lượt giữ chỗ hạn ngạch (RELEASE) và thông báo lỗi kết nối AI.
  2. Hệ thống hướng dẫn người học thử lại sau hoặc tự nhập bài học thủ công.
  3. Use case kết thúc (thất bại).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-PLAN-03 (Thời lượng bài học chuẩn hóa)**: Mỗi bài học học tập chi tiết do AI phân rã bắt buộc phải có thời lượng ước tính từ 30 phút đến 120 phút nhằm tối ưu hóa sự tập trung và phù hợp với phương pháp Pomodoro.
- **BR-PLAN-04 (Kiểm soát đồ thị tiên quyết DAG)**: Quan hệ phụ thuộc tiên quyết giữa các bài học trong một lộ trình bắt buộc phải tạo thành đồ thị có hướng không chu trình (Directed Acyclic Graph — DAG). Tuyệt đối cấm tồn tại quan hệ phụ thuộc vòng tròn (A cần B, B cần A).

**Quản trị AI & An toàn**:
- Kiểm soát định dạng JSON schema hai tầng (tầng schema và tầng thuật toán chu trình DAG) trước khi lưu dữ liệu vào hệ thống.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Danh sách Cột mốc Cấp 1 đã duyệt.
- **Đầu ra**: Danh sách bài học chi tiết Cấp 2 (`status = TODO`, `scheduled_date = NULL`), thời lượng ước tính (30–120 phút), mức năng lượng và quan hệ DAG.

---

#### UC-PLAN-03: Xếp lịch học bằng AI và áp dụng

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-PLAN-03** |
| **Tên Use Case** | **Xếp lịch học bằng AI và áp dụng** |
| **Mô tả ngắn** | Hệ thống tách bạch rạch ròi giữa Lộ trình kiến thức (`Roadmap`) và Các khối lịch học thực tế (`ScheduleBlocks`); Động cơ Lập lịch tất định (`Deterministic Scheduling Engine`) kết hợp với khuyến nghị nhịp năng lượng sinh học từ AI phân bổ thời lượng ước lượng của bài học (`tasks.estimated_minutes`) vào các khoảng thời gian rảnh khả dụng (`UnifiedAvailabilityModel`); tạo Bản đề xuất lịch học nháp (`ScheduleProposal` ở trạng thái `DRAFT`), kiểm định qua cổng tất định (`UC-PLAN-09`), hiển thị bản đối chiếu xem trước (Diff Preview) và Người học chủ động nhấn Áp dụng để cập nhật Lịch học chính thức. Hỗ trợ Tái tối ưu hóa lịch học độc lập (`Schedule-Only Reoptimization`) khi người học thay đổi giờ rảnh mà không tác động cấu trúc lộ trình. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04`) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học chọn "Xếp lịch tự động" sau khi phân rã nhiệm vụ (`UC-PLAN-02`), hoặc kích hoạt "Tái tối ưu hóa thời gian biểu" sau khi cập nhật cấu hình thời gian rảnh (`UC-ACC-04`). |
| **Tiền điều kiện** | Lộ trình có danh sách bài học; người học đã cấu hình thời gian rảnh; tài khoản có số dư hạn ngạch AI khả dụng (nếu chọn chế độ có AI tư vấn nhịp năng lượng). |
| **Hậu điều kiện – thành công** | Bản đề xuất lịch học (`ScheduleProposal`, `proposal_type` là `INITIAL_SCHEDULE` hoặc `SCHEDULE_ONLY_REOPTIMIZE`; tiến trình `workflow_runs.workflow_type = 'SCHEDULE_GENERATION'`) được phê duyệt và áp dụng; các khối thời gian học (`schedule_blocks`) được tạo hoặc cập nhật trong Lịch học chính thức (`OfficialSchedule`); bài học giữ trạng thái `TODO` và được cập nhật mốc lịch (`scheduled_date`, `scheduled_start`, `scheduled_end`) kèm khối lịch `schedule_blocks` (`status = 'PLANNED'`); trừ 1 lượt hạn ngạch AI (nếu có sử dụng tư vấn AI). Cấu trúc Milestone/Task của Roadmap được bảo toàn nguyên vẹn 100%. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Lịch học chính thức và Roadmap giữ nguyên không bị xáo trộn; hoàn trả hạn ngạch AI nếu có sự cố. |
| **Include / Extend** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` *(Bắt buộc 100%)* |
| **Tần suất / Độ ưu tiên** | Trung bình / Cực kỳ quan trọng (P0 — Must have) |
| **Tham chiếu SRS** | `FR-PLAN-002`, `FR-PLAN-003`, `FR-PLAN-005`, `FR-AVAIL-001`, `FR-AVAIL-002`, `BUSR-02`, `BUSR-03`, `SRS UC-08` |

**Luồng chính (Basic Flow)**:
1. Người học yêu cầu xếp lịch tự động cho các bài học của lộ trình và chỉ định ngày bắt đầu mong muốn (hoặc yêu cầu tái tối ưu hóa lịch học khi giờ rảnh thay đổi).
2. Hệ thống thu thập thông tin ngữ cảnh: mô hình thời gian rảnh hợp nhất (`UnifiedAvailabilityModel`: cấu hình Mode A/Mode B trừ đi các khoảng bận từ lịch ngoại vi `UC-EXEC-08`), thời lượng ước lượng của từng nhiệm vụ (`tasks.estimated_minutes`), các ràng buộc tiên quyết DAG và ngày mục tiêu hoàn thành lộ trình.
3. Hệ thống giữ chỗ 1 lượt gọi AI (JIT Reservation) và kích hoạt AI tư vấn mức độ ưu tiên xếp lịch theo nhịp năng lượng sinh học và thời điểm nhận thức tối ưu (`placementRationale`).
4. Động cơ Lập lịch tất định (`Deterministic Scheduling Engine`) tiếp nhận các khuyến nghị, thực thi thuật toán phân bổ tối ưu hóa ràng buộc (Constraint-based Bin-Packing) để gán từng nhiệm vụ vào các khối thời gian học cụ thể (`schedule_blocks`) trong các ngày khả dụng mà không vi phạm trần thời gian học ngày.
5. Hệ thống tạo Bản đề xuất lịch học (`ScheduleProposal`, `proposal_type` là `INITIAL_SCHEDULE` hoặc `SCHEDULE_ONLY_REOPTIMIZE`) ở trạng thái nháp (`DRAFT`). **Tuyệt đối không ghi đè trực tiếp vào Lịch học chính thức** (`BR-PLAN-05`).
6. Hệ thống thực hiện kiểm định tính hợp lệ và độ bền vững của bản đề xuất bằng cách **gọi `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include)**.
7. `UC-PLAN-09` kiểm tra 5 quy tắc bền vững (`Schedule Resilience Rules`) và trả về kết quả kiểm định là `VALID`.
8. Hệ thống xác nhận trừ 1 lượt hạn ngạch AI (COMMIT).
9. Hệ thống hiển thị giao diện Đối chiếu khác biệt (Diff Preview): trình bày chi tiết từng bài học được xếp vào ngày nào, khung giờ nào, phân bổ khối lượng hàng ngày và lý do đề xuất.
10. Người học xem xét bản xem trước, có thể kéo thả tinh chỉnh một số bài học nếu muốn.
11. Người học bấm nút **"Áp dụng lịch học (Apply)"**.
12. Hệ thống chuyển trạng thái Bản đề xuất sang `APPLIED`, lưu các khối lịch học vào Lịch học chính thức (`OfficialSchedule`), khởi tạo các khối `schedule_blocks` (`status = 'PLANNED'`) và cập nhật thông tin mốc lịch (`scheduled_date`, `scheduled_start`, `scheduled_end`) cho các bài học (giữ `tasks.status = 'TODO'`). Cấu trúc cột mốc và nhiệm vụ của Roadmap giữ nguyên vẹn. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **1a. Tái tối ưu hóa lịch học khi thay đổi giờ rảnh (Schedule-Only Reoptimization)**:
  1. Người học thay đổi khung giờ rảnh (ví dụ giảm từ 2 giờ/ngày xuống 1 giờ/ngày).
  2. Người học kích hoạt tính năng "Tái tối ưu hóa lịch học cho lộ trình hiện tại".
  3. Hệ thống giữ nguyên 100% cấu trúc Roadmap (milestones, tasks, prerequisites), chỉ gọi Động cơ Lập lịch tất định tính toán lại các `schedule_blocks` mới dãn đều theo quỹ thời gian mới.
  4. Hệ thống sinh `ScheduleProposal(proposal_type='SCHEDULE_ONLY_REOPTIMIZE')`, kiểm định qua `UC-PLAN-09` và hiển thị Diff ngày hoàn thành mới để người học Apply.
- **7a. `UC-PLAN-09` trả về kết quả `SOFT_OVERFLOW` (Cảnh báo quá tải thời gian rảnh)**:
  1. `UC-PLAN-09` phát hiện có một số ngày tổng thời lượng học vượt nhẹ định mức cấu hình từ 10% đến 30% (nhưng đồ thị DAG và khoảng bận vẫn hợp lệ).
  2. Hệ thống hiển thị hộp thoại cảnh báo: "Lịch học đề xuất có những ngày vượt nhẹ định mức thời gian học của bạn. Bạn có sẵn sàng cam kết học thêm trong các ngày này không?".
  3. Người học chọn "Tôi hiểu và đồng ý tiếp tục".
  4. Hệ thống tiếp tục từ bước 8 của luồng chính.
- **11a. Người học từ chối đề xuất**:
  1. Người học xem bản xem trước và không đồng ý với phương án xếp lịch.
  2. Người học chọn "Hủy bỏ bản đề xuất".
  3. Hệ thống xóa Bản đề xuất nháp, giữ nguyên lịch cũ, không thay đổi Lịch học chính thức. Use case kết thúc.

**Luồng ngoại lệ (Exception Flows)**:
- **7e. `UC-PLAN-09` trả về kết quả `INVALID` (Vi phạm quy tắc cứng)**:
  1. `UC-PLAN-09` phát hiện phương án xếp lịch bị lỗi logic (ví dụ vi phạm thứ tự DAG hoặc trùng khoảng bận).
  2. Động cơ Lập lịch tự động nới lỏng cửa sổ xếp lịch hoặc dời sang ngày tiếp theo và kiểm định lại.
  3. Nếu vẫn không thể xếp lịch hợp lệ mà không vượt quá ngày mục tiêu, hệ thống thông báo quỹ thời gian rảnh hiện tại không đủ để hoàn thành khối lượng lộ trình trước hạn chót và đề xuất người học tăng giờ rảnh hoặc kéo dài hạn chót.
  4. Use case kết thúc (thất bại).
- **3e. LLM Provider không phản hồi hoặc lỗi kết nối**:
  1. Quá thời gian chờ 55 giây không nhận được tư vấn năng lượng từ AI.
  2. Hệ thống tự động chuyển sang chế độ dự phòng tất định (Fallback Deterministic Bin-Packing) thuần túy dựa trên thuật toán xếp ưu tiên, hoàn trả hạn ngạch AI (RELEASE) và tiếp tục tạo bản đề xuất lịch học mà không làm gián đoạn người dùng.
  3. Chuyển tiếp sang bước 5 của luồng chính.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-PLAN-05 (Nguyên tắc Human-in-the-Loop — Quyền quyết định của Người học)**: AI và Động cơ xếp lịch chỉ có vai trò đề xuất bản nháp (`ScheduleProposal` ở trạng thái `DRAFT`). Tuyệt đối không một quy trình tự động nào được phép ghi đè lên Lịch học chính thức (`OfficialSchedule`) nếu chưa có hành động bấm Áp dụng (Apply) rõ ràng từ Người học.
- **BR-PLAN-06 (Phân tách Độc lập Roadmap vs. ScheduleBlocks)**: Cấu trúc lộ trình học tập (`Roadmap`: milestones, tasks, DAG prerequisites, estimated effort) và thời gian biểu học tập thực tế (`ScheduleBlocks`: start_time, end_time, scheduled_date) là hai thực thể quản trị độc lập. Thay đổi thời gian rảnh hoặc dời lịch chỉ tính toán lại `ScheduleBlocks`, tuyệt đối không bắt buộc tạo lại hoặc xóa sửa cấu trúc Roadmap.
- **BR-PLAN-07 (Quy tắc xếp lịch theo nhịp năng lượng sinh học)**: Các bài học yêu cầu mức năng lượng nhận thức cao (`energyLevel: HIGH`) phải được ưu tiên xếp vào các khung giờ mà người học tự đánh giá có mức năng lượng cao nhất trong ngày.

**Quản trị AI & An toàn**:
- Đảm bảo 100% đề xuất xếp lịch phải đi qua cổng kiểm định toán học tất định `UC-PLAN-09` trước khi được hiển thị cho người học.
- Hỗ trợ chế độ Fallback tất định 100% khi AI gặp sự cố mà không làm gãy quy trình lập lịch của người dùng.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Danh sách bài học, cấu hình thời gian rảnh hợp nhất, khoảng bận ngoại vi, ngày bắt đầu mong muốn.
- **Đầu ra**: Bản đề xuất lịch học (`ScheduleProposal`), các khối thời gian (`ScheduleBlocks`) trong Lịch học chính thức (`OfficialSchedule`) sau khi Apply.

---

#### UC-PLAN-04: Tạo lộ trình thủ công

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-PLAN-04** |
| **Tên Use Case** | **Tạo lộ trình thủ công** |
| **Mô tả ngắn** | Người học tự tay nhập toàn bộ thông tin mục tiêu, tạo các Cột mốc kiến thức, định nghĩa từng bài học và tự xếp ngày học vào thời khóa biểu mà hoàn toàn không sử dụng dịch vụ AI; hệ thống kiểm định lịch học qua cổng tất định (`UC-PLAN-09`) trước khi kích hoạt. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học chọn "Tạo lộ trình thủ công" từ bảng điều khiển chính. |
| **Tiền điều kiện** | Người học đã đăng nhập; tài khoản chưa vượt trần số lộ trình hoạt động của gói cước (FREE $\le 3$, PREMIUM $\le 15$). |
| **Hậu điều kiện – thành công** | Lộ trình mới cùng toàn bộ Cột mốc và bài học được tạo; Lịch học chính thức được lưu trữ hợp lệ sau khi vượt qua kiểm định `UC-PLAN-09`; trạng thái lộ trình chuyển sang `ACTIVE`. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Không lưu dữ liệu lỗi; không làm xáo trộn các lộ trình sẵn có. |
| **Include / Extend** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` *(Bắt buộc 100%)* |
| **Tần suất / Độ ưu tiên** | Trung bình / Quan trọng (P1 — Should have) |
| **Tham chiếu SRS** | `FR-GOAL-001`, `FR-PLAN-004`, `FR-PLAN-005`, `FR-TASK-001`, `FR-TASK-003` |

**Luồng chính (Basic Flow)**:
1. Người học chọn chức năng Tạo lộ trình thủ công.
2. Hệ thống kiểm tra tài khoản chưa vượt trần số lộ trình hoạt động (`BR-PLAN-01`).
3. Người học nhập thông tin cơ bản của lộ trình: tên lộ trình, mô tả mục tiêu, ngày bắt đầu và ngày mục tiêu hoàn thành (`target_date`).
4. Người học thêm các Cột mốc kiến thức (tối thiểu 1 cột mốc).
5. Trong từng cột mốc, Người học thêm danh sách các bài học: nhập tên bài học, thời lượng dự kiến (từ 15 đến 240 phút, `BR-PLAN-08`), mức năng lượng và chọn bài học điều kiện tiên quyết nếu có.
6. Người học gán ngày học cụ thể (`scheduled_date`) và khung giờ học cho từng bài học trên giao diện lịch trực quan.
7. Người học nhấn nút **"Lưu và Kích hoạt lộ trình"**.
8. Hệ thống bắt buộc thực thi kiểm định toàn bộ thời gian biểu bằng cách **gọi tất định vô điều kiện `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include)** theo chuẩn OMG UML 2.5.1 Clause 18.
9. `UC-PLAN-09` kiểm tra và trả về kết quả `VALID`.
10. Hệ thống lưu lộ trình vào kho dữ liệu ở trạng thái `ACTIVE`, chính thức ghi nhận các bài học vào Lịch học chính thức (`OfficialSchedule`).
11. Hệ thống thông báo lộ trình đã được khởi tạo thành công và chuyển hướng người học về giao diện chi tiết lộ trình. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **9a. `UC-PLAN-09` trả về kết quả `SOFT_OVERFLOW` (BUSR-04, A4)**:
  1. `UC-PLAN-09` cảnh báo có bài học cuối cùng trong ngày thuộc chế độ Mode B kết thúc muộn hơn khung rảnh tối đa $\le 30$ phút.
  2. Hệ thống hiển thị hộp thoại cảnh báo Soft Overflow kèm chi tiết thời gian tràn giờ và yêu cầu Người học xác nhận.
  3. Người học chọn "Xác nhận chấp nhận lịch học này".
  4. Hệ thống tiếp tục bước 10 của luồng chính.

**Luồng ngoại lệ (Exception Flows)**:
- **2e. Tài khoản đã đạt trần số lộ trình hoạt động**:
  1. Hệ thống thông báo đã chạm giới hạn gói cước, hướng dẫn lưu trữ lộ trình cũ (`UC-PLAN-06`) hoặc nâng cấp Premium (`UC-ACC-06`).
  2. Use case kết thúc (thất bại).
- **9e. `UC-PLAN-09` trả về kết quả `INVALID`**:
  1. Hệ thống thông báo lịch học thủ công không hợp lệ và chỉ rõ nguyên nhân (ví dụ: phát hiện chu trình phụ thuộc giữa các bài học, bài phụ thuộc xếp trước bài tiên quyết, hoặc khung giờ chọn trùng với lịch bận ngoại vi).
  2. Hệ thống đánh dấu trực quan vị trí các bài học bị lỗi trên giao diện lịch để Người học điều chỉnh lại.
  3. Người học sửa lại thời gian hoặc quan hệ phụ thuộc và quay lại bước 7.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-PLAN-07 (Độc lập hoàn toàn với AI)**: Ca sử dụng Tạo lộ trình thủ công hoàn toàn độc lập với dịch vụ AI, không đòi hỏi hạn ngạch AI và không bao giờ bị ảnh hưởng bởi sự cố mạng của bên thứ ba.
- **BR-PLAN-08 (Thời lượng bài học thủ công linh hoạt)**: Bài học do người dùng tự tạo cho phép dải thời lượng linh hoạt từ 15 phút đến 240 phút (phù hợp với các buổi tự nghiên cứu sâu hoặc bài tập lớn).

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Tên lộ trình, mô tả, danh sách cột mốc, danh sách bài học, quan hệ tiên quyết và ngày giờ xếp lịch.
- **Đầu ra**: Lộ trình mới (`ACTIVE`), Lịch học chính thức (`OfficialSchedule`).

---

#### UC-PLAN-05: Cập nhật thông tin lộ trình

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-PLAN-05: Cập nhật thông tin lộ trình** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập; lộ trình cần cập nhật đang ở trạng thái `ACTIVE` hoặc `INITIALIZED`. |
| **Hậu điều kiện thành công** | Tên, mô tả hoặc ngày mục tiêu hoàn thành (`target_date`) của lộ trình được cập nhật thành công; hệ thống tính toán lại độ ưu tiên EDF cho lộ trình. |
| **Bảo đảm tối thiểu** | Nếu ngày mục tiêu vi phạm quy tắc ngày của bài học đã xếp, từ chối cập nhật và giữ nguyên ngày cũ. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-PLAN-006`, `B14` |

- **Luồng chính (Basic Flow)**:
  1. Người học mở trang Quản lý lộ trình và chọn chức năng Chỉnh sửa thông tin lộ trình.
  2. Hệ thống hiển thị các thông tin hiện hành: tên lộ trình, mô tả và ngày mục tiêu hoàn thành (`target_date`).
  3. Người học thay đổi tên, mô tả hoặc chọn một ngày mục tiêu mới.
  4. Người học bấm Lưu thay đổi.
  5. Hệ thống kiểm tra tính hợp lệ của ngày mục tiêu mới: đảm bảo ngày mục tiêu không được sớm hơn ngày của bài học cuối cùng đã được lên lịch trong lộ trình (`BR-PLAN-09`).
  6. Hệ thống cập nhật thông tin lộ trình và tính lại độ ưu tiên EDF của lộ trình trong danh mục học tập. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Người học chỉ thay đổi tên hoặc mô tả lộ trình**: Hệ thống cập nhật thông tin văn bản trực tiếp mà không cần kiểm tra lại ngày của bài học đã xếp lịch. Tiếp tục bước 6.

- **Luồng ngoại lệ (Exception Flows)**:
  - **5e. Ngày mục tiêu mới sớm hơn ngày của bài học đã xếp lịch (B14)**: Hệ thống từ chối lưu và hiển thị thông báo lỗi: "Ngày mục tiêu mới không thể sớm hơn ngày [dd/mm/yyyy] của bài học cuối cùng đã lên lịch. Vui lòng dời lịch các bài học trước hoặc chọn ngày mục tiêu phù hợp".

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-PLAN-09 (Tính nhất quán của ngày mục tiêu lộ trình — B14)**: Ngày mục tiêu hoàn thành của một lộ trình (`target_date`) luôn luôn phải lớn hơn hoặc bằng ngày lên lịch của bài học có mốc thời gian muộn nhất trong lộ trình đó.

---

#### UC-PLAN-06: Lưu trữ lộ trình

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-PLAN-06: Lưu trữ lộ trình** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập; lộ trình đang ở trạng thái hoạt động (`ACTIVE`) hoặc tạm dừng (`PAUSED`). |
| **Hậu điều kiện thành công** | Trạng thái lộ trình chuyển sang `ARCHIVED`; toàn bộ các bài học chưa hoàn thành trong tương lai bị đóng băng/hủy lịch để giải phóng thời khóa biểu; giải phóng 1 chỉ tiêu lộ trình hoạt động; toàn bộ lịch sử học tập và ghi chú đúc kết quá khứ được bảo lưu trọn vẹn. |
| **Bảo đảm tối thiểu** | Nếu người dùng hủy xác nhận, lộ trình giữ nguyên trạng thái cũ. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-PLAN-006` |

- **Luồng chính (Basic Flow)**:
  1. Người học chọn chức năng Lưu trữ lộ trình từ menu cài đặt của một lộ trình cụ thể.
  2. Hệ thống hiển thị hộp thoại xác nhận lưu trữ, giải thích rõ: lộ trình sẽ được chuyển vào mục Lưu trữ, các bài học chưa học trong tương lai sẽ được gỡ khỏi thời khóa biểu, giải phóng 1 chỉ tiêu lộ trình hoạt động, nhưng toàn bộ lịch sử các phiên học đã hoàn thành sẽ được giữ nguyên vẹn.
  3. Người học bấm xác nhận "Tôi đồng ý lưu trữ".
  4. Hệ thống cập nhật trạng thái lộ trình sang `ARCHIVED`.
  5. Hệ thống gỡ bỏ các bài học chưa hoàn thành khỏi Lịch học chính thức, giải phóng các khung thời gian rảnh tương ứng.
  6. Hệ thống hiển thị thông báo đã lưu trữ thành công và cập nhật lại danh mục lộ trình. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **1a. Đánh dấu hoàn thành toàn bộ lộ trình**: Khi người học hoàn thành bài học cuối cùng và toàn bộ các cột mốc đều đạt chứng chỉ kiểm chứng năng lực, hệ thống hiển thị màn hình chúc mừng vinh danh và tự động gợi ý lưu trữ lộ trình sang trạng thái đã hoàn thành (`COMPLETED/ARCHIVED`).

- **Luồng ngoại lệ (Exception Flows)**:
  - **3e. Người học hủy xác nhận lưu trữ**: Người học bấm hủy trên hộp thoại xác nhận. Hệ thống giữ nguyên trạng thái lộ trình (`ACTIVE` hoặc `PAUSED`), bảo toàn nguyên trạng thời khóa biểu.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-PLAN-10 (Bảo toàn lịch sử khi lưu trữ)**: Việc lưu trữ lộ trình (`ARCHIVED`) chỉ đóng băng các hoạt động trong tương lai để giải phóng thời gian, tuyệt đối không làm mất dữ liệu phiên học, điểm North Star WRLS hay các ghi chú đúc kết đã tích lũy trong quá khứ.

---

#### UC-PLAN-07: Quản lý công việc và quan hệ tiên quyết

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-PLAN-07: Quản lý công việc và quan hệ tiên quyết** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập; lộ trình đang ở trạng thái `ACTIVE` hoặc `INITIALIZED`. |
| **Hậu điều kiện thành công** | Bài học được thêm mới, cập nhật nội dung, hủy bỏ hoặc gán quan hệ tiên quyết; các bài học chưa xếp lịch được sắp xếp thứ tự ưu tiên trong Hàng đợi phục hồi (`Backlog Queue`) căn cứ theo 4 trọng số; nếu có xếp lịch thì lịch học mới phải vượt qua kiểm định `UC-PLAN-09`. |
| **Bảo đảm tối thiểu** | Không cho phép tạo chu trình phụ thuộc (DAG cycle); từ chối xóa bài học đang trong phiên học hoặc đã hoàn thành. |
| **Quan hệ UML** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` |
| **Tham chiếu SRS** | `FR-TASK-001`, `FR-TASK-002`, `FR-TASK-003` |

- **Luồng chính (Basic Flow)**:
  1. Người học mở danh sách bài học của một lộ trình hoặc mở Hàng đợi công việc tồn đọng (`Backlog Recovery Queue`).
  2. Người học chọn thao tác mong muốn: thêm bài học mới, chỉnh sửa thông tin bài học, xóa bài học hoặc thiết lập bài học điều kiện tiên quyết.
  3. Người học thực hiện chỉnh sửa và thiết lập quan hệ phụ thuộc giữa các bài học.
  4. Hệ thống kiểm tra thuật toán đồ thị: đảm bảo quan hệ tiên quyết không tạo thành chu trình phụ thuộc kín (`BR-TASK-02`).
  5. Khi người học gán/thay đổi ngày học cho bài học hoặc xếp lịch lại từ Backlog Queue vào thời gian biểu, hệ thống **bắt buộc thực hiện gọi tất định vô điều kiện `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include)** theo chuẩn OMG UML 2.5.1 Clause 18 để thẩm định toàn diện ràng buộc DAG, khoảng bận và quy tắc Schedule Resilience.
  6. `UC-PLAN-09` trả về `VALID` (hoặc `SOFT_OVERFLOW` đã được người học xác nhận).
  7. Hệ thống cập nhật thông tin bài học, tự động tính lại thứ tự ưu tiên trong Backlog Queue theo thuật toán thứ tự từ điển 4 tiêu chí (`BR-TASK-01`) và lưu vào Lịch học chính thức. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **2a. Người học hủy một bài học chưa học**: Hệ thống chuyển trạng thái bài học sang `CANCELLED`, gỡ khỏi lịch học và cập nhật lại quan hệ của các bài học phụ thuộc phía sau.
  - **6a. `UC-PLAN-09` trả về `SOFT_OVERFLOW`**: Hệ thống hiển thị cảnh báo task cuối cùng Mode B vượt tối đa 30 phút; người học bấm xác nhận cam kết; hệ thống tiếp tục bước 7.

- **Luồng ngoại lệ (Exception Flows)**:
  - **4a. Phát hiện quan hệ phụ thuộc chu trình (ví dụ bài A đòi bài B, bài B đòi bài A)**: Hệ thống chặn ngay lập tức, hiển thị cảnh báo đỏ và không cho phép lưu quan hệ tiên quyết này.
  - **6e. `UC-PLAN-09` trả về `INVALID`**: Hệ thống từ chối cập nhật lịch học, hiển thị thông báo chi tiết vi phạm (chu trình DAG, vi phạm thứ tự tiên quyết, hoặc đè lịch bận) để người học điều chỉnh.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-TASK-01 (Thuật toán Xếp hạng Ưu tiên Hàng đợi Backlog theo Thứ tự Từ điển — FR-TASK-002)**: Độ ưu tiên của các bài học tồn đọng trong Backlog Recovery Queue được sắp xếp tự động bằng thuật toán tất định `BacklogPriorityRanker` theo 4 tiêu chí toán học theo thứ tự từ điển (Lexicographical Ordering):
    1. **Số lượng task hậu kế bị chặn trên đồ thị DAG (`out_degree` giảm dần)**: Task nào mở khóa nhiều task sau hơn được ưu tiên lên đầu để giải phóng tiến độ;
    2. **Thứ tự tuần tự Cột mốc (`sequence_order` tăng dần)**: Task thuộc Milestone hiện tại hoặc sớm hơn được ưu tiên trước;
    3. **Số lần đã bị dời lịch (`reschedule_count` giảm dần)**: Task đã bị dời nhiều lần được ưu tiên cứu trước để tránh tồn đọng mãn tính;
    4. **Thời lượng ước tính ngắn (`estimated_minutes` tăng dần)**: Trong cùng mức ưu tiên, task ngắn hơn (15–30 phút) được ưu tiên xếp trước để người học lấy đà thành công (Quick Win).
  - **BR-TASK-02 (Ràng buộc bất biến DAG — FR-TASK-003)**: Quan hệ tiên quyết giữa các bài học bắt buộc phải là đồ thị có hướng không chu trình. Một bài học chỉ có thể bắt đầu khi toàn bộ các bài học tiên quyết trực tiếp của nó đã được đánh dấu hoàn thành.

---

#### UC-PLAN-08: Quản lý cột mốc

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-PLAN-08: Quản lý cột mốc** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập; lộ trình đang ở trạng thái `ACTIVE` hoặc `INITIALIZED`. |
| **Hậu điều kiện thành công** | Cột mốc mới được thêm, đổi tên, điều chỉnh thứ tự tuần tự hoặc xóa bớt; cấu trúc các giai đoạn của lộ trình được cập nhật nhất quán. |
| **Bảo đảm tối thiểu** | Không cho phép xóa cột mốc đã có bài học hoàn thành hoặc đã được cấp chứng chỉ kiểm chứng năng lực (`PROVEN`). |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-PLAN-001`, `FR-PLAN-006` |

- **Luồng chính (Basic Flow)**:
  1. Người học truy cập phần quản lý cấu trúc lộ trình và chọn chức năng Quản lý Cột mốc.
  2. Hệ thống hiển thị danh sách các Cột mốc hiện tại theo thứ tự tuần tự kèm trạng thái tiến độ của từng cột mốc.
  3. Người học thực hiện một trong các thao tác:
     - Thêm cột mốc kiến thức mới vào vị trí mong muốn.
     - Đổi tên hoặc cập nhật mô tả tiêu chí hoàn thành của cột mốc.
     - Kéo thả để thay đổi vị trí tuần tự của các cột mốc trong lộ trình.
     - Xóa một cột mốc chưa có hoạt động học tập.
  4. Người học bấm Lưu thay đổi cấu trúc cột mốc.
  5. Hệ thống kiểm tra tính hợp lệ: đảm bảo cột mốc bị xóa không chứa bài học đã hoàn thành (`BR-PLAN-11`).
  6. Hệ thống cập nhật lại thứ tự tuần tự và liên kết các bài học tương ứng. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Thay đổi vị trí tuần tự cột mốc rỗng**: Hệ thống hoán đổi thứ tự hiển thị tức thì mà không ảnh hưởng đến đồ thị DAG của các bài học.

- **Luồng ngoại lệ (Exception Flows)**:
  - **5e. Xóa cột mốc đã có bài học hoàn tất hoặc đã đạt PROVEN (BR-PLAN-11)**: Hệ thống từ chối xóa và hiển thị thông báo lỗi: "Không thể xóa cột mốc này do đã có bài học hoàn thành hoặc đã kiểm chứng năng lực. Bạn chỉ có thể đổi tên hoặc đánh dấu lưu trữ".

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-PLAN-11 (Bảo vệ tính toàn vẹn của Cột mốc đã học)**: Cột mốc đã có ít nhất một bài học ở trạng thái hoàn thành (`COMPLETED`) hoặc đã được cấp chứng chỉ kiểm chứng năng lực (`PROVEN`) tuyệt đối không thể bị xóa bỏ khỏi lộ trình.

---

#### UC-PLAN-09: Kiểm định tính hợp lệ của lịch học

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-PLAN-09** |
| **Tên Use Case** | **Kiểm định tính hợp lệ của lịch học** |
| **Mô tả ngắn** | Use Case mức chức năng con (Subfunction Level) chịu trách nhiệm kiểm định tất định 100% thời gian thực ($\le 50$ms) toàn bộ các ràng buộc toán học, nghiệp vụ và 5 quy tắc Bền vững Lịch trình (`Schedule Resilience`) đối với mọi thay đổi thời gian biểu: kiểm tra đồ thị tiên quyết không chu trình (DAG), thứ tự tuần tự của bài học tiên quyết, độ khít với khung thời gian rảnh (Mode B), không trùng lấn khoảng bận lịch ngoại vi, kiểm soát khoảng nghỉ đệm (`Buffer Time`), khối phục hồi (`Recovery Window` $\ge 15\%$), trần tải ngày (`Daily Workload Cap` mặc định 180 phút/ngày theo SRS §12), bảo vệ phiên học then chốt (`Protected Sessions`) và độ ổn định lịch học (`Schedule Stability`); trả về một trong ba kết quả chuẩn hóa `{VALID, SOFT_OVERFLOW, INVALID}`. |
| **Tác nhân chính** | Không có con người trực tiếp *(Subfunction Level — kích hoạt bởi Hệ thống khi được include)* |
| **Tác nhân phụ** | Không có |
| **Mức độ** | Chức năng con dùng chung (Subfunction Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Được gọi thông qua quan hệ `<<include>>` bởi 09 Use Cases: `UC-PLAN-03`, `UC-PLAN-04`, `UC-PLAN-07`, `UC-PLAN-10`, `UC-EXEC-02`, `UC-ADAPT-04`, `UC-ADAPT-05`, `UC-ADAPT-06`, `UC-ADAPT-07`. |
| **Tiền điều kiện** | Tiếp nhận danh sách các khối lịch học (`schedule_blocks`) cần xếp lịch kèm thông tin ngày giờ dự kiến, cấu hình thời gian rảnh của người học và danh sách các khoảng bận ngoại vi hiện hành. |
| **Hậu điều kiện – thành công** | Trả về kết quả đánh giá phân loại rõ ràng: `VALID` (hợp lệ hoàn toàn và thỏa mãn 5 quy tắc bền vững), `SOFT_OVERFLOW` (chỉ áp dụng đối với task cuối cùng trong một ngày học thuộc chế độ Mode B khi task kết thúc muộn hơn khung rảnh tối đa 30 phút tuyệt đối theo `BUSR-04`), hoặc `INVALID` (vi phạm quy tắc cứng kèm danh sách chi tiết các vi phạm cụ thể). |
| **Bảo đảm tối thiểu** | Quá trình kiểm định là thuần tính toán logic (In-memory deterministic algorithm), không thay đổi trạng thái dữ liệu trong kho lưu trữ, thời gian thực thi $\le 50$ms. |
| **Include / Extend** | Được `<<include>>` bởi 09 Use Cases |
| **Tần suất / Độ ưu tiên** | Cực kỳ cao / Cốt lõi hệ thống (P0 — Must have) |
| **Tham chiếu SRS** | `FR-PLAN-005`, `FR-TASK-003`, `FR-AVAIL-002`, `FR-AVAIL-003`, `SRS UC-12`, `BUSR-04`, `BUSR-05`, `A3`, `A4` |

**Luồng chính (Basic Flow)**:
1. Hệ thống tiếp nhận yêu cầu kiểm định chứa: danh sách các khối lịch học (`schedule_blocks`), cấu hình thời gian rảnh của người học (Chế độ A hoặc Chế độ B), các khoảng thời gian bận đã đồng bộ từ lịch ngoại vi và ngày mục tiêu hoàn thành lộ trình.
2. Hệ thống thực hiện kiểm tra thuật toán đồ thị có hướng (Directed Graph): duyệt toàn bộ quan hệ phụ thuộc tiên quyết để xác nhận đồ thị hoàn toàn không tồn tại chu trình khép kín (`BR-VAL-01`).
3. Hệ thống kiểm tra tính tuần tự về mặt thời gian: đảm bảo rằng mọi bài học phụ thuộc đều có thời điểm bắt đầu học sau thời điểm kết thúc của toàn bộ các bài học điều kiện tiên quyết trực tiếp của nó (`BR-VAL-02`).
4. Hệ thống kiểm tra xung đột thời gian với khung giờ rảnh và lịch ngoại vi:
   - Trong Chế độ B: bài học phải nằm trọn vẹn bên trong một trong các khung giờ rảnh đã khai báo (ngoại trừ task cuối cùng được xét Soft Overflow).
   - Chiều lịch ngoại vi: khung giờ bài học tuyệt đối không được đè lấn hoặc giao cắt với bất kỳ khoảng thời gian bận (`Free/Busy`) nào đã được nạp từ Google Calendar (`BR-VAL-03`).
5. Hệ thống kiểm tra 5 quy tắc Bền vững Lịch trình (`Schedule Resilience Rules`, `BR-VAL-05`):
   - *Buffer Time*: Giữa hai khối học liền kề trong cùng một ngày phải có khoảng nghỉ tối thiểu 10–15 phút.
   - *Recovery Window*: Giữ dung lượng dự phòng tuần $\ge 15\%$ tổng quỹ giờ rảnh khả dụng của tuần (`FR-PLAN-005`) để sẵn sàng hấp thụ độ trễ bài học mà không làm vỡ lịch.
   - *Daily Workload Cap*: Tổng thời lượng học trong ngày không được vượt quá trần cấu hình (mặc định tối đa đúng **180 phút / 3 giờ/ngày** theo SRS §12 để ngăn ngừa kiệt sức nhận thức, trần tuyệt đối $\le 8$ giờ/ngày).
   - *Protected Sessions*: Không dời lịch hoặc xáo trộn các phiên học đã được người học gán cờ bảo vệ (`is_protected = true`).
   - *Schedule Stability*: Mức độ xáo trộn lịch hiện có (Schedule Churn) phải ở mức tối thiểu đối với các bài học đã lên lịch trong vòng 48 giờ tới.
6. Hệ thống tính toán sự phù hợp thời gian đối với khung giờ rảnh và khối lượng học tập hàng ngày:
   - Nếu tổng thời lượng trong ngày $\le$ định mức cấu hình và toàn bộ bài học nằm gọn trong khung giờ rảnh: Hợp lệ.
   - Nếu trong chế độ Mode B, duy nhất bài học cuối cùng trong ngày kết thúc muộn hơn mốc kết thúc của khung giờ rảnh tối đa **30 phút tuyệt đối** (và đồ thị DAG hợp lệ, không đè lịch bận): Ghi nhận trạng thái tràn giờ mềm (`SOFT_OVERFLOW`, `BR-VAL-04`).
   - Nếu bài học không phải bài cuối kết thúc ngoài khung rảnh, hoặc bài cuối Mode B tràn quá 30 phút, hoặc tổng tải vượt quá Daily Workload Cap (180 phút/ngày): Đánh dấu vi phạm quá tải (INVALID).
7. Hệ thống tổng hợp kết quả kiểm định:
   - Nếu không có bất kỳ vi phạm nào và không phát sinh tràn giờ mềm: Trả về mã kết quả `{ status: "VALID" }`.
   - Nếu đồ thị DAG hợp lệ, không xung đột khoảng bận ngoại vi, nhưng có task cuối cùng trong ngày Mode B tràn tối đa 30 phút: Trả về mã kết quả `{ status: "SOFT_OVERFLOW", overflow_details: [...] }`.
   - Nếu có chu trình DAG, bài phụ thuộc xếp trước bài tiên quyết, đè lấn lịch bận ngoại vi, vi phạm phiên bảo vệ hoặc vượt trần Daily Workload Cap / tràn quá 30 phút: Trả về mã kết quả `{ status: "INVALID", violation_errors: [...] }`.
8. Hệ thống hoàn tất kiểm định và trả kết quả về cho Use Case cha đang gọi. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- Không có luồng thay thế (đây là quy trình kiểm định tất định đơn hướng). Mọi trường hợp bất thường đều được phân loại chính xác thành các mã trả về `SOFT_OVERFLOW` hoặc `INVALID` tại bước 7.

**Luồng ngoại lệ (Exception Flows)**:
- **1e. Dữ liệu đầu vào bị thiếu trường bắt buộc (ví dụ thiếu ngày xếp lịch hoặc thiếu thời lượng bài học)**:
  1. Hệ thống phát hiện dữ liệu không đầy đủ để chạy thuật toán.
  2. Trả về ngay lập tức `{ status: "INVALID", violation_errors: ["Dữ liệu bài học không đầy đủ để kiểm định"] }`.
  3. Use case kết thúc.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-VAL-01 (Bảo đảm đồ thị DAG tuyệt đối không chu trình)**: Thuật toán kiểm tra đồ thị (dựa trên thuật toán sắp xếp topo - Topological Sort / Tarjan) bắt buộc trả về hợp lệ khi và chỉ khi không tồn tại bất kỳ chu trình lặp nào giữa các bài học.
- **BR-VAL-02 (Ràng buộc thứ tự thời gian tiên quyết)**: Với hai bài học A và B, nếu B phụ thuộc vào A ($A \rightarrow B$), thì thời điểm bắt đầu của B phải sau thời điểm kết thúc của A ít nhất 0 phút: `Start(B) >= End(A)`.
- **BR-VAL-03 (Bảo vệ khoảng bận lịch ngoại vi)**: Tuyệt đối không cho phép bất kỳ bài học nào được xếp đè lấn lên các khoảng thời gian bận đã được đồng bộ từ Google Calendar nhằm tôn trọng cuộc sống thực tế của người học.
- **BR-VAL-04 (Quy tắc Tràn giờ mềm có kiểm soát — BUSR-04, A3, A4)**: Trạng thái `SOFT_OVERFLOW` **chỉ áp dụng đối với bài học cuối cùng trong một ngày học thuộc chế độ Mode B (Time Slot Window)**, khi bài học đó kết thúc muộn hơn mốc kết thúc của khung giờ rảnh tối đa **30 phút tuyệt đối** (đúng quy tắc `BUSR-04`). Xóa bỏ hoàn toàn định nghĩa sai lệch về tỷ lệ phần trăm tràn giờ cho mọi ngày. Mọi Use Case cha gọi include `UC-PLAN-09` bắt buộc phải có luồng hiển thị cảnh báo trực quan về thời gian tràn giờ và yêu cầu Người học xác nhận cam kết trước khi cho phép "Apply" ghi vào `OfficialSchedule`.
- **BR-VAL-05 (5 Quy tắc Bền vững Lịch học — Schedule Resilience & FR-PLAN-005)**:
  1. *Buffer Time*: Duy trì $\ge 10$–15 phút nghỉ ngơi giữa 2 khối học liên tiếp trong ngày.
  2. *Recovery Window*: Giữ dung lượng thời gian đệm dự phòng tuần $\ge 15\%$ tổng thời gian rảnh tuần (`FR-PLAN-005`) để hấp thu bài dồn ứ mà không vỡ kế hoạch.
  3. *Daily Workload Cap*: Giới hạn trần học tập hàng ngày mặc định tối đa đúng **180 phút (3 giờ/ngày)** theo SRS §12 (ngăn chặn tình trạng kiệt sức - Burnout).
  4. *Protected Sessions*: Không can thiệp hoặc dời các khối học mang cờ `is_protected = true`.
  5. *Schedule Stability*: Giữ nguyên lịch học trong vòng 48 giờ tới, hạn chế tối đa xáo trộn giờ giấc cận kề.

**Đặc tả Phi chức năng**:
- **Hiệu năng kiểm định tất định**: Toàn bộ thuật toán kiểm định chạy trong bộ nhớ với thời gian phản hồi $\le 50$ms cho bộ dữ liệu lộ trình lên tới 200 bài học, bảo đảm phản hồi tức thì cho trải nghiệm người dùng kéo thả.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Danh sách khối lịch học dự kiến xếp lịch, cấu hình thời gian rảnh, danh sách khoảng bận ngoại vi.
- **Đầu ra**: Cấu trúc kết quả kiểm định `{ status: VALID | SOFT_OVERFLOW | INVALID, details: [...] }`.

---

#### UC-PLAN-10: Mô phỏng kịch bản giả định (What-if Planning Simulation)

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-PLAN-10** |
| **Tên Use Case** | **Mô phỏng kịch bản giả định (What-if Planning Simulation)** |
| **Mô tả ngắn** | Người học thử nghiệm các kịch bản thay đổi điều kiện học tập trong môi trường sandbox giả lập (ví dụ: điều chỉnh quỹ giờ rảnh từ 2h/ngày xuống 1h/ngày, đổi trần giờ học, thay đổi ngày bắt đầu hoặc ngày mục tiêu hoàn thành); Động cơ Lập lịch tất định (`Deterministic Scheduling Engine`) mô phỏng lại phân bổ các khối lịch (`schedule_blocks`) trong thời gian thực (<100ms) mà không tiêu tốn hạn ngạch AI; tạo Bản đề xuất mô phỏng (`ScheduleProposal(proposal_type='WHAT_IF_SIMULATION')`), kiểm định qua `UC-PLAN-09`, hiển thị giao diện đối chiếu song song (Side-by-side Diff Preview); Người học có thể chọn hủy bỏ không lưu hoặc nhấn Áp dụng để ghi đè vào Lịch học chính thức. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Không có *(Thuần thuật toán tất định in-memory, tiêu tốn 0 lượt gọi AI)* |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học chọn tính năng "Mô phỏng kịch bản What-if" từ giao diện quản lý kế hoạch lộ trình hoặc trang chi tiết thời gian biểu. |
| **Tiền điều kiện** | Lộ trình đang ở trạng thái hoạt động (`ACTIVE`) và đã có lịch học chính thức (`OfficialSchedule`). |
| **Hậu điều kiện – thành công** | Bản mô phỏng được tạo và hiển thị trực quan; nếu Người học bấm Áp dụng: các khối lịch mới được ghi nhận vào `OfficialSchedule` và các chỉ số lộ trình được cập nhật; nếu Người học hủy: toàn bộ bản mô phỏng sandbox bị xóa bỏ, lịch chính thức giữ nguyên vẹn 100%. Tiêu tốn 0 lượt hạn ngạch AI. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Lịch học chính thức và cấu hình gốc được bảo toàn nguyên vẹn 100%. |
| **Include / Extend** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` *(Bắt buộc 100%)* |
| **Tần suất / Độ ưu tiên** | Trung bình / Quan trọng (P1 — Should have) |
| **Tham chiếu SRS** | `FR-PLAN-002`, `FR-PLAN-003`, `FR-PLAN-005`, `SRS UC-08`, `BUSR-02`, `BUSR-03` |

**Luồng chính (Basic Flow)**:
1. Người học truy cập công cụ Mô phỏng kịch bản giả định (What-if Simulation) của một lộ trình đang học.
2. Giao diện sandbox hiển thị các tham số giả định hiện tại kèm các thanh điều khiển:
   - Quỹ thời gian rảnh mỗi ngày (Daily Available Hours).
   - Ngày bắt đầu kịch bản mới (Simulation Start Date).
   - Ngày mục tiêu mong muốn hoàn thành (Simulated Target Date).
   - Trần thời gian học tối đa hàng ngày (Daily Workload Cap).
3. Người học tinh chỉnh một hoặc nhiều tham số giả định (ví dụ: kéo thanh trượt giảm giờ rảnh từ 2 giờ/ngày xuống 1 giờ/ngày).
4. Người học nhấn nút **"Chạy mô phỏng (Run Simulation)"**.
5. Động cơ Lập lịch tất định (`Deterministic Scheduling Engine`) tiếp nhận các tham số sandbox, chạy thuật toán phân bổ khối lượng in-memory trong thời gian $\le 100$ms mà không tiêu tốn hạn ngạch AI (`BR-PLAN-10-01`), bảo toàn 100% cấu trúc Roadmap (`BR-PLAN-10-02`).
6. Hệ thống tạo Bản đề xuất kịch bản giả lập (`ScheduleProposal`, `proposal_type = 'WHAT_IF_SIMULATION'`) ở trạng thái nháp (`DRAFT`).
7. Hệ thống gọi `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include) để xác thực tính hợp lệ của kịch bản mô phỏng.
8. `UC-PLAN-09` trả về kết quả kiểm định `VALID`.
9. Hệ thống hiển thị Bảng đối chiếu song song (Side-by-side Diff Preview):
   - Cột hiện tại vs. Cột mô phỏng.
   - Chênh lệch ngày hoàn thành dự kiến ($\Delta$ ngày, ví dụ: "Lùi lại 14 ngày so với kế hoạch gốc").
   - Biểu đồ phân bổ tải học tập hàng ngày (Workload Heatmap).
   - Đánh giá chỉ số rủi ro trễ hạn (Overdue Risk Index: Thấp / Trung bình / Cao).
10. Người học xem xét kết quả mô phỏng. Sau khi cân nhắc kỹ lưỡng, Người học quyết định nhấn nút **"Áp dụng kịch bản này vào Lịch chính thức (Apply to Official Schedule)"**.
11. Hệ thống yêu cầu xác nhận lần cuối: "Thao tác này sẽ cập nhật lại toàn bộ các khối lịch học trong tương lai của lộ trình này. Cấu trúc bài học và tiến độ đã học không thay đổi.".
12. Người học xác nhận. Hệ thống chuyển `ScheduleProposal` sang trạng thái `APPLIED`, cập nhật các `schedule_blocks` mới vào `OfficialSchedule` và đồng bộ lại ngày mục tiêu của lộ trình nếu có thay đổi. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **8a. `UC-PLAN-09` trả về kết quả `SOFT_OVERFLOW` (Cảnh báo quá tải nhẹ)**:
  1. Kịch bản giả định khiến một số ngày vượt nhẹ trần thời gian học (10% đến 30%).
  2. Bảng Side-by-side Diff đánh dấu màu vàng tại các ngày bị quá tải nhẹ và hiển thị thông báo cảnh báo.
  3. Người học có thể chấp nhận tiếp tục hoặc điều chỉnh lại thanh trượt tham số để chạy lại mô phỏng.
- **10a. Người học hủy bỏ hoặc đóng sandbox mô phỏng**:
  1. Người học nhận thấy kịch bản mới không tối ưu hoặc chỉ muốn xem thử hiệu ứng.
  2. Người học chọn "Hủy bỏ kịch bản" hoặc đóng màn hình sandbox.
  3. Hệ thống hủy bản ghi `ScheduleProposal` nháp trong sandbox, giữ nguyên 100% Lịch học chính thức hiện hành. Use case kết thúc.
- **10b. Người học tiếp tục điều chỉnh thêm tham số khác**:
  1. Người học thay đổi thêm tham số (ví dụ tăng ngày mục tiêu hoàn thành thêm 3 tuần).
  2. Quay lại bước 4 của luồng chính để tái lập kịch bản mới tức thì.

**Luồng ngoại lệ (Exception Flows)**:
- **8e. `UC-PLAN-09` trả về `INVALID` (Kịch bản bất khả thi)**:
  1. Người học đặt tham số quá khắt khe (ví dụ giảm giờ rảnh xuống 15 phút/ngày nhưng yêu cầu hoàn thành trước hạn chót 1 tuần).
  2. Hệ thống phát hiện không thể xếp đủ tổng thời lượng ước lượng của các bài học còn lại vào quỹ thời gian giả định mà không vi phạm trần thời gian học ngày.
  3. Hệ thống hiển thị thông báo lỗi cụ thể: "Kịch bản bất khả thi: Quỹ thời gian rảnh còn thiếu tổng cộng X giờ để hoàn thành khối lượng lộ trình trước ngày mục tiêu đã chọn.".
  4. Hệ thống gợi ý tăng giờ rảnh hoặc dời ngày mục tiêu và cho phép người học chỉnh lại tham số.
  5. Use case kết thúc.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-PLAN-10-01 (Mô phỏng Tất định Không tốn Quota AI — Zero-Quota Invariant)**: Toàn bộ quá trình tính toán mô phỏng What-if được thực thi bởi Động cơ Lập lịch tất định (Deterministic Scheduling Engine) trong thời gian $\le 100$ms, hoàn toàn không tiêu tốn hạn ngạch gọi AI (`AI Quota = 0`).
- **BR-PLAN-10-02 (Bảo toàn Tuyệt đối Cấu trúc Roadmap — Roadmap Invariance)**: Mô phỏng What-if chỉ tác động lên việc tính toán lại các khối thời gian (`schedule_blocks`), tuyệt đối không được thêm, bớt, đổi tên, hoặc sửa đổi quan hệ phụ thuộc DAG của các Milestone/Task trong Roadmap.
- **BR-PLAN-10-03 (Chỉ ghi vào Lịch chính thức khi có xác nhận Apply)**: Kết quả mô phỏng chỉ tồn tại tạm thời trong trạng thái nháp (`DRAFT`). Lịch học chính thức (`OfficialSchedule`) chỉ bị thay đổi khi Người học chủ động nhấn Áp dụng và vượt qua xác nhận 2 bước.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Lộ trình hiện tại, các bài học tương lai chưa hoàn thành, các tham số giả định điều chỉnh (giờ rảnh, trần tải, ngày bắt đầu, ngày mục tiêu).
- **Đầu ra**: Bảng đối chiếu song song Side-by-side Diff Preview, `ScheduleProposal` nháp, `OfficialSchedule` được cập nhật (nếu người học bấm Apply).

---


### PHÂN HỆ 3: THỰC THI HỌC TẬP & TÍCH HỢP LỊCH NGOẠI VI

Phân hệ bao gồm 9 Use Cases chịu trách nhiệm vận hành không gian học tập tập trung (Focus Mode), theo dõi nhịp tim phiên học, quản lý bằng chứng đúc kết tức thời, chia nhỏ bài học và tích hợp đồng bộ hai chiều với các ứng dụng lịch cá nhân bên ngoài.

```
Sơ đồ 3: Thực thi Học tập & Tích hợp Lịch ngoại vi (UC-EXEC-01, UC-EXEC-02, UC-EXEC-03, UC-EXEC-04, UC-EXEC-05, UC-EXEC-06, UC-EXEC-07, UC-EXEC-08, UC-EXEC-09, kèm UC-PLAN-09)
```

---

#### UC-EXEC-01: Xem lịch học và Tiêu điểm Hôm nay

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-EXEC-01: Xem lịch học và Tiêu điểm Hôm nay** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập vào hệ thống. |
| **Hậu điều kiện thành công** | Giao diện Thẻ Tiêu điểm Hôm nay (`Today Focus Card`) được hiển thị với bài học tiếp theo cần tập trung, kèm lịch học theo dạng tuần/tháng và các cảnh báo bài học quá hạn được tính toán động theo múi giờ cá nhân. |
| **Bảo đảm tối thiểu** | Không làm biến đổi dữ liệu lịch học khi chỉ thực hiện thao tác xem. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-SCHEDULE-001`, `FR-SESSION-001`, `D4` |

- **Luồng chính (Basic Flow)**:
  1. Người học truy cập vào bảng điều khiển học tập hoặc giao diện Lịch học.
  2. Hệ thống xác định ngày hiện tại theo múi giờ IANA của Người học và truy vấn các bài học đã lên lịch.
  3. Hệ thống tính toán động trạng thái quá hạn (`isOverdue`): bài học chưa hoàn thành có ngày lên lịch nhỏ hơn ngày hiện tại sẽ được gắn cờ quá hạn thời gian thực (`BR-EXEC-01`).
  4. Hệ thống hiển thị Thẻ Tiêu điểm Hôm nay (`Today Focus Card`) ở vị trí trung tâm nổi bật: tên bài học ưu tiên kế tiếp, thời lượng ước tính, mức năng lượng yêu cầu và hai nút hành động nhanh: "Bắt đầu học ngay (Tiêu chuẩn)" hoặc "Học phiên tối thiểu (MVS)".
  5. Hệ thống hiển thị thời khóa biểu học tập dạng tuần/tháng với các khối thời gian rõ ràng, phân biệt màu sắc theo trạng thái khối lịch `schedule_blocks.status` (`PLANNED`, `COMPLETED`, `MISSED`, `RESCHEDULED`, `CANCELLED`), trạng thái bài học `tasks.status` (`TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`) và cờ quá hạn dẫn xuất. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Có nhiều bài học đang bị quá hạn (Overdue Alert Banner)**: Hệ thống hiển thị dải cảnh báo màu hổ phách phía trên lịch học, cung cấp nút chuyển hướng nhanh sang Dời lịch bằng AI (`UC-ADAPT-06`) hoặc Nghi thức Tái thiết (`UC-ADAPT-07`).
  - **4a. Ngày hôm nay không có bài học nào được lên lịch**: Thẻ Tiêu điểm hiển thị thông báo "Hôm nay bạn không có lịch học! Hãy tận hưởng thời gian nghỉ ngơi hoặc chọn một bài học từ Backlog để học trước".

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Lỗi kết nối mạng khi tải thời khóa biểu**: Hệ thống hiển thị dữ liệu lịch đã lưu tạm trên bộ nhớ cache trình duyệt và thông báo đang ở chế độ xem ngoại tuyến; người học vẫn xem được các bài học đã tải.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-EXEC-01 (Bản chất dẫn xuất động của trạng thái quá hạn — D4)**: Trạng thái bài học quá hạn (`isOverdue`) là giá trị tính toán động thời gian thực (`scheduled_date < CURRENT_DATE(user_timezone)` và trạng thái chưa hoàn thành), không lưu trữ dưới dạng cờ vật lý trong cơ sở dữ liệu.

---

#### UC-EXEC-02: Dời lịch công việc thủ công

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-EXEC-02** |
| **Tên Use Case** | **Dời lịch công việc thủ công** |
| **Mô tả ngắn** | Người học chủ động kéo thả trên giao diện lịch hoặc chọn ngày giờ mới để dời lịch cho một bài học; hệ thống kiểm tra tình trạng quá hạn để yêu cầu nhập lý do gián đoạn, tăng bộ đếm số lần dời lịch (`reschedule_count`), kiểm tra cảnh báo trì hoãn (`STALLED`), kiểm định tính hợp lệ của lịch mới qua `UC-PLAN-09` và cập nhật Lịch học chính thức. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học kéo thả một khối bài học sang ngày khác trên giao diện lịch hoặc chọn nút "Dời lịch" trong menu ngữ cảnh của bài học. |
| **Tiền điều kiện** | Bài học đang ở trạng thái `TODO` hoặc `IN_PROGRESS` và đã được xếp lịch (`scheduled_date IS NOT NULL` / có `schedule_blocks` ở trạng thái `PLANNED`); người học đã đăng nhập. |
| **Hậu điều kiện – thành công** | Bài học được chuyển sang ngày và khung giờ mới trong Lịch học chính thức (`OfficialSchedule`); bộ đếm `reschedule_count` tăng thêm 1; nếu là bài quá hạn thì lý do gián đoạn được ghi nhận; lịch học mới vượt qua kiểm định của `UC-PLAN-09`. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Giữ nguyên ngày học cũ của bài học; không ghi nhận dời lịch nếu vi phạm ràng buộc tiên quyết hoặc xung đột lịch bận. |
| **Include / Extend** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` *(Bắt buộc 100%)* |
| **Tần suất / Độ ưu tiên** | Thường xuyên / Cực kỳ quan trọng (P0 — Must have) |
| **Tham chiếu SRS** | `FR-SCHEDULE-001`, `FR-TASK-001`, `FR-PLAN-005`, `FR-ADAPT-003`, `BUSR-06`, `A4` |

**Luồng chính (Basic Flow)**:
1. Người học thực hiện thao tác kéo thả bài học sang một ngày/khung giờ mới trên giao diện lịch học hoặc chọn "Dời ngày học" từ menu bài học.
2. Hệ thống kiểm tra xem bài học có đang bị quá hạn (`isOverdue = true`, tức `scheduled_date < CURRENT_DATE` theo múi giờ cá nhân) hay không.
3. Nếu bài học bị quá hạn, hệ thống hiển thị hộp thoại bắt buộc người học lựa chọn Lý do gián đoạn (`disruptionCategory`: Công việc đột xuất, Mệt mỏi/Thiếu năng lượng, Nội dung quá khó/Cần thêm tài liệu, Việc cá nhân/Gia đình, Khác) để lưu vào hồ sơ thích ứng SRL (`BR-EXEC-02`).
4. Người học chọn lý do gián đoạn và xác nhận ngày học mới.
5. Hệ thống xử lý cập nhật bộ đếm dời lịch (`FR-SCHEDULE-001`):
   - Nếu bài học đang ở điều kiện quá hạn (`isOverdue = true`): Hệ thống tăng bộ đếm số lần dời lịch `reschedule_count = reschedule_count + 1`.
   - Nếu người học chủ động dời lịch khi task chưa quá hạn (`scheduled_date >= CURRENT_DATE`): Hệ thống chuẩn bị cập nhật `scheduled_date` mới mà **KHÔNG tăng `reschedule_count`**.
6. Hệ thống kiểm tra ngưỡng cảnh báo trì hoãn:
   - Nếu `reschedule_count >= 3` (bài học đã ở trạng thái `STALLED` theo `FR-ADAPT-003`): **Hệ thống KHÓA tính năng dời lịch thông thường**, kích hoạt hộp thoại can thiệp chống trì hoãn SRL bắt buộc Người học chọn 1 trong 3 giải pháp: (1) Chia nhỏ bài học qua AI Micro-stepping $\le 30$ phút (`UC-EXEC-05`), (2) Thiết lập Hợp đồng Cam kết (Commitment Contract) cam kết học tối thiểu $\ge 15$ phút, hoặc (3) Đưa bài học về Hàng đợi phục hồi (`Backlog Recovery Queue`, `scheduled_date = NULL`).
7. Hệ thống chuẩn bị dữ liệu lịch mới và **gọi tất định `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include)**.
8. `UC-PLAN-09` kiểm định và trả về kết quả `VALID` (không vi phạm chu trình DAG, không vi phạm thứ tự tiên quyết, không trùng lịch bận ngoại vi và không vượt trần giờ học ngày).
9. Hệ thống cập nhật ngày học và khung giờ mới vào Lịch học chính thức (`OfficialSchedule`).
10. Hệ thống hiển thị thông báo đã dời lịch thành công và làm mới giao diện lịch học. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **2a. Bài học không bị quá hạn (Dời lịch chủ động trước hạn — FR-SCHEDULE-001)**:
  1. Bài học có `scheduled_date >= CURRENT_DATE`.
  2. Hệ thống không bắt buộc nhập lý do gián đoạn và không tăng bộ đếm `reschedule_count`.
  3. Hệ thống bỏ qua bước 3–4 và chuyển thẳng sang bước 7.
- **8a. `UC-PLAN-09` trả về kết quả `SOFT_OVERFLOW` (BUSR-04, A4)**:
  1. `UC-PLAN-09` phát hiện bài học cuối cùng trong ngày thuộc chế độ Mode B kết thúc muộn hơn khung rảnh tối đa $\le 30$ phút.
  2. Hệ thống hiển thị hộp thoại cảnh báo tràn giờ mềm và yêu cầu Người học xác nhận cam kết.
  3. Người học chọn "Xác nhận dời lịch".
  4. Hệ thống tiếp tục bước 9 của luồng chính.

**Luồng ngoại lệ (Exception Flows)**:
- **6e. Bài học bị STALLED từ chối can thiệp**:
  1. Người học đóng hộp thoại can thiệp mà không chọn 1 trong 3 nhánh xử lý SRL.
  2. Hệ thống giữ nguyên vị trí bài học, từ chối dời lịch tự do. Use case kết thúc.
- **8e. `UC-PLAN-09` trả về kết quả `INVALID` (Vi phạm quy tắc cứng)**:
  1. `UC-PLAN-09` phát hiện việc dời lịch vi phạm thứ tự tiên quyết (ví dụ: dời bài B về ngày trước bài tiên quyết A của nó) hoặc đè lấn lên khoảng thời gian bận từ Google Calendar.
  2. Hệ thống thông báo lỗi chi tiết, từ chối thực hiện dời lịch và tự động đưa bài học trở lại ngày học ban đầu trên giao diện.
  3. Use case kết thúc (thất bại).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-EXEC-02 (Bắt buộc phân loại lý do khi dời bài quá hạn)**: Mọi thao tác dời lịch cho bài học đã quá hạn bắt buộc phải ghi nhận Lý do gián đoạn (`disruptionCategory`) làm dữ liệu đầu vào cho báo cáo phản tư chốt tuần và thuật toán thích ứng lộ trình. Thao tác dời lịch thủ công đơn lẻ không trừ vào Ngân sách dời lịch tuần (`weeklyRescheduleBudget` chỉ áp dụng cho dời lịch tự động bằng AI tại `UC-ADAPT-06`).
- **BR-EXEC-03 (Cơ chế ngắt mạch cảnh báo STALLED)**: Khi một bài học bị dời lịch từ 3 lần trở lên (`reschedule_count >= 3`), hệ thống tự động gán nhãn cảnh báo `STALLED`. Hệ thống chủ động hiển thị các biện pháp can thiệp hành vi nhằm triệt tiêu tâm lý sợ hãi/trì hoãn thay vì cho phép dời lịch vô hạn.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Bài học được chọn, ngày/giờ mới, lý do gián đoạn (nếu quá hạn).
- **Đầu ra**: Lịch học chính thức được cập nhật, `reschedule_count` tăng 1, nhãn `STALLED` (nếu $\ge 3$).

---

#### UC-EXEC-03: Đánh dấu hoàn thành nhanh

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-EXEC-03: Đánh dấu hoàn thành nhanh** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập; bài học đang ở trạng thái `TODO` hoặc `IN_PROGRESS` (đã xếp lịch hoặc chưa xếp lịch); người học đã tự hoàn thành nội dung ở nguồn ngoài mà không chạy đồng hồ đếm giờ. |
| **Hậu điều kiện thành công** | Bài học được chuyển sang trạng thái hoàn thành (`COMPLETED`); bản ghi đúc kết cốt lõi (Key Takeaway) được lưu trữ làm bằng chứng học tập có căn cứ; cập nhật mốc hoạt động `last_study_activity_at = NOW()`. |
| **Bảo đảm tối thiểu** | Bắt buộc phải có Key Takeaway $\ge 30$ ký tự hợp lệ và điểm tự tin 1..5; nếu không nhập hoặc nội dung vô nghĩa, tuyệt đối từ chối đánh dấu hoàn thành. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-TASK-001`, `FR-SESSION-002`, `D5`, `B2` |

- **Luồng chính (Basic Flow)**:
  1. Người học chọn nút "Đánh dấu đã học xong" từ danh sách bài học hoặc thẻ bài học.
  2. Hệ thống hiển thị biểu mẫu Xác nhận hoàn thành nhanh, thông báo quy định bắt buộc phải cung cấp đúc kết cốt lõi để làm bằng chứng cho vòng kiểm chứng năng lực (`BR-EXEC-04`).
  3. Người học nhập nội dung đúc kết cốt lõi (Key Takeaway) và chọn điểm tự tin cá nhân từ 1 đến 5 sao (`selfConfidence`).
  4. Hệ thống kiểm tra tính hợp lệ qua Cổng kiểm soát đúc kết tất định (Deterministic Takeaway Guard): kiểm tra độ dài $\ge 30$ ký tự và loại trừ các chuỗi ký tự rác/vô nghĩa (`BR-EXEC-05`).
  5. Hệ thống lưu bản ghi đúc kết vào mục ghi chú học tập (gắn trực tiếp mã bài học và phân loại là `TAKEAWAY`).
  6. Hệ thống chuyển trạng thái bài học sang `COMPLETED`, cập nhật mốc thời gian hoạt động học tập mới nhất `last_study_activity_at = NOW()` và thông báo thành công. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Người học điều chỉnh lại điểm tự tin**: Người học thay đổi đánh giá mức tự tin từ 1 đến 5 sao trước khi bấm xác nhận lưu hoàn thành.

- **Luồng ngoại lệ (Exception Flows)**:
  - **4e. Nội dung đúc kết không đạt chuẩn Deterministic Takeaway Guard (BR-EXEC-05)**: Chuỗi ký tự đúc kết $< 30$ ký tự, chứa ít hơn 6 từ có nghĩa, độ trùng lặp token $\ge 85\%$ hoặc có ký tự lặp quá 5 lần liên tiếp. Hệ thống từ chối ghi nhận hoàn thành, hiển thị cảnh báo đỏ và yêu cầu người học nhập nội dung đúc kết hợp lệ.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-EXEC-04 (Bắt buộc đúc kết tối thiểu khi Hoàn thành nhanh — D5, B2)**: Tuyệt đối không cho phép bấm hoàn thành nhanh một bài học mà không cung cấp Key Takeaway ($\ge 30$ ký tự) và điểm tự tin (`selfConfidence: 1..5`). Bản ghi này là tài sản bằng chứng không thể thiếu để đối chiếu Ground Truth trong `UC-ADAPT-02`.
  - **BR-EXEC-05 (Deterministic Takeaway Guard — FR-SESSION-002, FR-REPORT-003)**: Cổng kiểm duyệt tất định Tầng 1 bắt buộc chuỗi đúc kết phải có độ dài $\ge 30$ ký tự, chứa tối thiểu **6 từ có nghĩa**, độ trùng lặp token (token overlap) $< 85\%$ so với nội dung gần nhất, và không được lặp lại một ký tự liên tục quá 5 lần.

---

#### UC-EXEC-04: Thực hiện phiên học tập trung (Tiêu chuẩn & Rút gọn)

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-EXEC-04** |
| **Tên Use Case** | **Thực hiện phiên học tập trung (Tiêu chuẩn & Rút gọn)** |
| **Mô tả ngắn** | Người học khởi động không gian học tập Focus Mode theo Chế độ Tiêu chuẩn (Pomodoro/Stopwatch) hoặc Chế độ Phiên tối thiểu (Minimum Viable Session — MVS 10–15 phút); hệ thống duy trì tín hiệu nhịp tim (Heartbeat 60s), cho phép ghi chép nháp hoặc chia nhỏ bài học (`UC-EXEC-05`); khi chốt phiên, người học chủ động tích chọn các bài hoàn thành, bắt buộc nhập Key Takeaway để lưu bằng chứng học tập và hoàn tất Thẻ Check-in Học tập Hàng ngày 3 lựa chọn (`Daily Learning Check-in`) để cập nhật mô hình người học. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04` — tùy chọn khi yêu cầu gợi ý đúc kết) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học chọn "Bắt đầu học" hoặc "Phiên tối thiểu MVS" từ Thẻ Tiêu điểm Hôm nay (`UC-EXEC-01`) hoặc từ chi tiết bài học. |
| **Tiền điều kiện** | Người học đã đăng nhập; không có phiên học nào khác đang ở trạng thái `IN_PROGRESS` (`BR-SESS-02`); không có khoản nợ đúc kết chưa xử lý quá 24 giờ (`BR-SESS-01`). |
| **Hậu điều kiện – thành công** | Phiên học được chốt thành công ở trạng thái `COMPLETED` (hoặc `PARTIAL_COMPLETED`); thời lượng học thực tế tích lũy qua Heartbeat được ghi nhận; các bài học được người học tích chọn chuyển sang `COMPLETED`; bản ghi Key Takeaway được lưu trữ; dữ liệu Daily Check-in 3 trường (`time_sufficiency`, `perceived_difficulty`, `focus_level`) được cập nhật vào Bộ nhớ Người học; điểm WRLS và mốc `last_study_activity_at = NOW()` được cập nhật. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Nếu người học hủy phiên trước ngưỡng thời lượng tối thiểu, phiên bị hủy (`CANCELLED`), không ghi nhận giờ học vào chỉ số WRLS. |
| **Include / Extend** | Không có |
| **Tần suất / Độ ưu tiên** | Hàng ngày / Cốt lõi hệ thống (P0 — Must have) |
| **Tham chiếu SRS** | `FR-SESSION-001`, `FR-SESSION-002`, `FR-SESSION-003`, `FR-REPORT-001`, `SRS UC-14`, `BUSR-04`, `BUSR-05`, `OS-01`, `B3`, `B15` |

**Luồng chính (Basic Flow)**:
1. Người học chọn bài học cần thực thi và chọn chế độ học:
   - *Chế độ Tiêu chuẩn*: Đồng hồ Pomodoro đếm lùi 25 phút hoặc Đồng hồ bấm giờ tăng dần (Stopwatch).
   - *Chế độ Phiên tối thiểu (MVS)*: Phiên học ngắn cố định 10–15 phút nhằm vượt qua sức ỳ tâm lý (`BR-SESS-04`).
2. Hệ thống kiểm tra điều kiện tiên quyết: xác nhận Người học không còn nợ đúc kết quá 24h (`BR-SESS-01`) và không có phiên nào đang chạy (`BR-SESS-02`).
3. Hệ thống khởi tạo phiên học ở trạng thái `IN_PROGRESS` và chuyển đổi giao diện sang Không gian học tập tập trung (Focus Mode): ẩn toàn bộ thanh điều hướng gây xao nhãng, hiển thị đồng hồ thời gian lớn, tên bài học mục tiêu và khu vực ghi chú nhanh (Scratchpad).
4. Thiết bị của người học định kỳ gửi tín hiệu duy trì nhịp tim (Heartbeat) 60 giây một lần về hệ thống để xác nhận người học vẫn đang hiện diện tích cực (`BR-SESS-06`).
5. Trong quá trình học, người học có thể ghi chép các ý tưởng quan trọng vào Scratchpad. Nếu bài học quá dài hoặc gặp bế tắc, người học có thể chọn chức năng Chia nhỏ bài học qua AI (`UC-EXEC-05`).
6. Khi đồng hồ kết thúc hoặc người học chủ động chọn nút "Hoàn thành phiên học":
   - Hệ thống dừng đồng hồ và tổng hợp tổng thời lượng hiện diện thực tế dựa trên số tín hiệu nhịp tim nhận được.
   - Hệ thống hiển thị hộp thoại Chốt phiên học: liệt kê danh sách các bài học gắn với phiên để Người học chủ động tích chọn bài nào đã thực sự hoàn thành (`BR-SESS-03`).
   - Với các bài học được tích hoàn thành, hệ thống yêu cầu Người học nhập Đúc kết cốt lõi (Key Takeaway $\ge 30$ ký tự) và tự đánh giá độ tự tin tiếp thu (`selfConfidence: 1..5`).
   - Hệ thống hiển thị Thẻ Phản xạ Nhanh cuối phiên (Daily Learning Check-in) gồm 3 chip lựa chọn trực quan: (1) Mức độ đủ thời gian (`checkin_time_sufficiency`: Vừa vặn / Thiếu / Thừa), (2) Độ khó cảm nhận (`checkin_perceived_difficulty`: Dễ / Phù hợp / Khó), (3) Mức độ tập trung (`checkin_focus_level`: Cao / Trung bình / Xao nhãng) (`BR-SESS-08`).
7. Người học nhập nội dung Key Takeaway, chọn điểm tự tin và chọn 3 chip phản xạ nhanh.
8. Hệ thống kiểm tra tính hợp lệ qua Cổng kiểm soát đúc kết tất định (`BR-EXEC-05`).
9. Người học nhấn nút **"Lưu và Chốt phiên học"**.
10. Hệ thống cập nhật trạng thái phiên học sang `COMPLETED`, lưu bản ghi Key Takeaway vào kho bằng chứng, lưu kết quả Daily Check-in vào hồ sơ người học, chuyển trạng thái các bài học được tích chọn sang `COMPLETED`, cập nhật mốc hoạt động `last_study_activity_at = NOW()` và cộng điểm chuyên cần vào chỉ số Bắc đẩu WRLS (`BR-SESS-07`). Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **1a. Vận hành theo Chế độ Phiên học tối thiểu (Minimum Viable Session — MVS)**:
  1. Người học chọn bắt đầu với chế độ MVS (10–15 phút).
  2. Phiên học vận hành với đồng hồ đếm lùi trong khoảng thời gian này.
  3. Tại bước 6, nếu thời lượng thực học tích lũy $\ge 10$ phút và người học nhập Key Takeaway hợp lệ, hệ thống công nhận phiên học đạt chuẩn tối thiểu thành công theo ngoại lệ quy tắc `OS-01`.
  4. Hệ thống ghi nhận phiên học là `PARTIAL_COMPLETED` (hoặc `COMPLETED`), khấu trừ thời lượng học vào bài học và tính 1 điểm ngày chuyên cần vào chỉ số WRLS (tối đa 1 phiên MVS được tính điểm mỗi ngày — `BR-SESS-04`).
- **6a. Kết thúc sớm chủ động (Người học muốn dừng phiên trước thời hạn)**:
  1. Người học bấm "Dừng phiên học sớm".
  2. Nếu thời lượng thực học đã đạt $\ge 50\%$ thời lượng dự kiến của bài học: Hệ thống cho phép nhập Key Takeaway để chốt phiên ở trạng thái hoàn thành một phần (`PARTIAL_COMPLETED`), bài học chưa chuyển sang completed nhưng được ghi nhận thời lượng đã học.
  3. Nếu thời lượng thực học $< 50\%$ (và không phải MVS): Hệ thống cảnh báo thời lượng học chưa đủ để ghi nhận kết quả và hỏi người học có muốn chuyển đổi phiên này thành MVS (nếu đã học $\ge 10$ phút) hay hủy phiên. Nếu người học chọn hủy, phiên học chuyển sang `CANCELLED` và không tính giờ học.
- **7a. Người học yêu cầu AI gợi ý đúc kết (AI Takeaway Assistant)**:
  1. Người học bấm nút "Gợi ý đúc kết từ ghi chép nháp".
  2. Hệ thống kiểm tra hạn ngạch AI, trích xuất nội dung trong Scratchpad và gửi sang LLM Provider để gợi ý 2–3 phương án đúc kết súc tích.
  3. Người học chọn một phương án, tự chỉnh sửa theo ngôn từ của mình và tiếp tục bước 8.

**Luồng ngoại lệ (Exception Flows)**:
- **2e. Người học còn bài học bị nợ đúc kết quá 24 giờ (`pending_takeaway = true`)**:
  1. Hệ thống chặn không cho mở phiên học mới.
  2. Hệ thống hiển thị hộp thoại bắt buộc hoàn thành nộp đúc kết cho bài học bị gián đoạn trước đó kèm nội dung Scratchpad đã lưu để Người học nhớ lại ngữ cảnh.
  3. Sau khi Người học hoàn thành nộp đúc kết bù, hệ thống mới giải phóng quyền mở phiên học mới.
- **4e. Người học tắt trình duyệt đột ngột hoặc mất kết nối mạng**:
  1. Thiết bị ngừng gửi tín hiệu nhịp tim Heartbeat.
  2. Phiên học vẫn tạm thời giữ trạng thái `IN_PROGRESS` trên máy chủ trong 5 phút để chờ người học mở lại trang (phục hồi phiên học).
  3. Nếu sau 5 phút không có tín hiệu kết nối lại, hệ thống sẽ kích hoạt ca sử dụng tự động chốt phiên gián đoạn (`UC-EXEC-06`).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-SESS-01 (Chính sách xử lý nợ đúc kết — Pending Takeaway Gate)**: Nếu người học có phiên học bị gián đoạn chưa nộp đúc kết (`pending_takeaway = true`), hệ thống cho phép ân hạn nộp bù trong vòng tối đa 24 giờ. Quá 24 giờ không nộp bù, hệ thống tự động khóa quyền mở phiên học mới cho đến khi nghĩa vụ đúc kết được giải tỏa.
- **BR-SESS-02 (Quy tắc bất biến đơn phiên duy nhất — Single Active Session)**: Tại một thời điểm trên toàn hệ thống, một tài khoản người học chỉ được phép tồn tại duy nhất 01 phiên học ở trạng thái `IN_PROGRESS`.
- **BR-SESS-03 (Chủ động chọn bài hoàn thành — B3)**: Hệ thống tuyệt đối không tự động gán trạng thái `COMPLETED` cho toàn bộ các bài học trong phiên. Người học phải là người chủ động tích chọn bài nào đã thực sự hiểu và hoàn thành tại thời điểm chốt phiên.
- **BR-SESS-04 (Quy chuẩn Chế độ MVS và Giới hạn WRLS — B15)**: Chế độ MVS kéo dài từ 10 đến 15 phút. Để được công nhận hoàn thành một phần hợp lệ, phiên MVS bắt buộc phải tích lũy tối thiểu 10 phút nhịp tim thực tế và có Key Takeaway hợp lệ. Để chống lạm dụng cày điểm, mỗi ngày người học chỉ được tính tối đa 01 phiên MVS vào công thức tính chỉ số WRLS.
- **BR-SESS-06 (Quy tắc tín hiệu nhịp tim Heartbeat)**: Thiết bị người học gửi tín hiệu Heartbeat định kỳ 60 giây. Tổng thời lượng học được tính dựa trên số tín hiệu Heartbeat thực tế nhận được nhằm triệt tiêu hành vi mở trình duyệt treo máy gian lận thời gian học.
- **BR-SESS-07 (Cập nhật mốc hoạt động — D4)**: Mỗi khi một phiên học được chốt thành công (`COMPLETED` hoặc `PARTIAL_COMPLETED`), hệ thống cập nhật `last_study_activity_at = NOW()`, điều này ngay lập tức giải tỏa trạng thái ngủ đông (`isDormant = false`) của người học.
- **BR-SESS-08 (Nghi thức Check-in Học tập Hàng ngày — Daily Learning Check-in)**: Dữ liệu phản xạ 3 chip (`time_sufficiency`, `perceived_difficulty`, `focus_level`) là công cụ nhận biết mức độ nhận thức nhẹ (Metacognitive Prompting) giúp người học phản tư mà không gây mỏi mệt nhận thức. Dữ liệu này được lưu trữ để tính toán nhịp học và cập nhật hồ sơ hành vi người học trong `learner_memory_items`.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Chế độ học chọn (Tiêu chuẩn/MVS), tín hiệu Heartbeat định kỳ, ghi chú Scratchpad, danh sách bài tích hoàn thành, Key Takeaway, điểm tự tin, 3 chip Daily Check-in.
- **Đầu ra**: Phiên học (`COMPLETED`/`PARTIAL_COMPLETED`), bài học hoàn thành, bản ghi đúc kết, kết quả Daily Check-in, cập nhật mốc hoạt động và điểm WRLS.

---

#### UC-EXEC-05: Chia nhỏ bài học bằng AI (Micro-stepping)

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-EXEC-05: Chia nhỏ bài học bằng AI (Micro-stepping)** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04`) |
| **Tiền điều kiện** | Người học đang trong không gian học tập Focus Mode (`UC-EXEC-04`) hoặc đang xem chi tiết bài học; bài học có thời lượng $\ge 45$ phút hoặc bài học bị gán cờ `STALLED`; hạn ngạch AI còn lượt khả dụng. |
| **Hậu điều kiện thành công** | Bài học cha được phân tách thành các bài học siêu nhỏ (Micro-tasks $\le 30$ phút) có liên kết `parent_task_id`; tạo bản ghi `ScheduleProposal(DRAFT)`; sau khi Người học bấm "Apply", hệ thống chính thức cập nhật `OfficialSchedule` và trừ 1 lượt hạn ngạch AI. |
| **Bảo đảm tối thiểu** | Nếu AI gặp sự cố hoặc người học hủy bỏ đề xuất, giữ nguyên vẹn bài học cha ban đầu, hoàn trả hạn ngạch AI (`RELEASE`). |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-TASK-001`, `FR-PLAN-002`, `FR-ADAPT-003`, `FR-AI-001`, `BUSR-02` |

- **Luồng chính (Basic Flow)**:
  1. Người học nhận thấy bài học hiện tại quá dài, phức tạp hoặc gặp tâm lý sợ hãi/trì hoãn (hoặc can thiệp bài học `STALLED`), bấm nút "Chia nhỏ bài học này (Micro-Stepping)".
  2. Hệ thống kiểm tra hạn ngạch AI và thực hiện giữ chỗ (JIT Reservation).
  3. Hệ thống gửi thông tin bài học hiện tại sang LLM Provider với yêu cầu phân tách thành các bước học siêu nhỏ có thời lượng $\le 30$ phút (`BR-TASK-03`).
  4. LLM Provider phản hồi danh sách các bài học con kèm tiêu đề cụ thể, thời lượng phân bổ hợp lý ($\le 30$ phút) và kết quả cần đạt.
  5. Hệ thống kiểm tra cấu trúc dữ liệu: đảm bảo tổng thời lượng các bài con xấp xỉ bài cha, kế thừa vị trí DAG và liên kết `parent_task_id = original_task.id`.
  6. Tuân thủ nghiêm ngặt nguyên tắc **`BUSR-02` (Không tự động áp dụng — No Auto-Apply)**: Hệ thống tạo bản ghi Đề xuất lịch học (`ScheduleProposal`) ở trạng thái **`DRAFT`**, hiển thị giao diện xem trước (Diff Preview) danh sách micro-tasks cho Người học đối chiếu.
  7. Người học xem xét danh sách các bước học siêu nhỏ và bấm nút **"Xác nhận Áp dụng (Apply)"**.
  8. Hệ thống trừ 1 lượt hạn ngạch AI (COMMIT), chuyển `ScheduleProposal` sang `APPLIED`, thay thế bài học cha bằng các bài học siêu nhỏ trên Lịch học chính thức (`OfficialSchedule`) và cập nhật giao diện học tập. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **7a. Người học hủy bỏ bản đề xuất micro-tasks**: Người học không đồng ý với phương án phân tách; hệ thống hủy `ScheduleProposal` (`DISCARDED`), hoàn trả lượt giữ chỗ quota (`RELEASE`), giữ nguyên bài học cha.
  - **3a. Người học đang học dở dang trong phiên học**: Khi Apply, phiên học hiện tại được liên kết ngay với bài học siêu nhỏ đầu tiên trong chuỗi vừa tạo mà không làm gián đoạn đồng hồ bấm giờ.

- **Luồng ngoại lệ (Exception Flows)**:
  - **4e. Dịch vụ AI timeout hoặc lỗi cấu trúc JSON (FR-AI-001 / FR-AI-002)**: Hệ thống tự động thử lại tối đa 2 lần. Nếu vẫn thất bại, hệ thống hoàn trả hạn ngạch (`RELEASE`), thông báo lỗi và giữ nguyên bài học cha ban đầu. Use case kết thúc (thất bại).

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-TASK-03 (Quy chuẩn Micro-Stepping & Bảo vệ BUSR-02 — FR-PLAN-002, FR-ADAPT-003)**: Kỹ thuật chia nhỏ bài học phân tách một bài học thành các micro-tasks có thời lượng $\le 30$ phút, kế thừa vị trí trong đồ thị tiên quyết DAG và lưu `parent_task_id`. Bản đề xuất bắt buộc phải ở trạng thái `DRAFT`, tuyệt đối không tự ý ghi đè vào `OfficialSchedule` khi chưa có hành động Apply rõ ràng từ Người học.

---

#### UC-EXEC-06: Tự động lưu phiên học khi mất kết nối

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-EXEC-06: Tự động lưu phiên học khi mất kết nối** |
| **Mức độ & Phân tầng** | Mục tiêu hệ thống nền (System-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`Learner — ACT-02`) *(Kích hoạt tự động theo sự kiện thời gian nội bộ — OMG UML TimeEvent)* |
| **Tác nhân phụ** | Không có |
| **Trigger** | Tác vụ kiểm tra phiên học treo định kỳ mỗi 2 phút một lần (`OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Có phiên học ở trạng thái `IN_PROGRESS` không nhận được tín hiệu nhịp tim Heartbeat trong hơn 5 phút liên tục (`OS-07`). |
| **Hậu điều kiện thành công** | Phiên học được tự động chuyển sang trạng thái kết thúc phù hợp (`PARTIAL_COMPLETED` hoặc `CANCELLED`); nếu đạt ngưỡng thời lượng tối thiểu thì gắn cờ nợ đúc kết (`pending_takeaway = true`) với thời hạn ân hạn 24 giờ; giải phóng trạng thái đơn phiên để người học có thể học tiếp. |
| **Bảo đảm tối thiểu** | Các phiên học đang phát tín hiệu nhịp tim bình thường tuyệt đối không bị chốt nhầm; nợ đúc kết quá hạn 24 giờ được giải phóng an toàn mà không làm treo tài khoản người học. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-SESSION-003`, `OS-01`, `OS-07`, `B15` |

- **Luồng chính (Basic Flow)**:
  1. Sự kiện thời gian định kỳ (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ kiểm tra phiên học treo định kỳ mỗi 2 phút một lần.
  2. Hệ thống tìm kiếm các phiên học đang ở trạng thái `IN_PROGRESS` có thời điểm nhận tín hiệu nhịp tim cuối cùng cách hiện tại $> 5$ phút.
  3. Với từng phiên học phát hiện được, hệ thống tính toán tổng thời gian học thực tế căn cứ theo số tín hiệu Heartbeat đã nhận được trước khi mất kết nối:
     - Nếu thời gian học thực tế $\ge 50\%$ thời lượng bài học dự kiến (hoặc $\ge 10$ phút đối với phiên học MVS): Hệ thống chuyển trạng thái phiên sang `PARTIAL_COMPLETED`, ghi nhận thời lượng thực học, đánh dấu cờ nợ đúc kết `pending_takeaway = true` với thời hạn ân hạn 24 giờ (`BR-SESS-05`).
     - Nếu thời gian học thực tế $< 50\%$ thời lượng (và $< 10$ phút đối với MVS): Hệ thống chuyển trạng thái phiên sang bị hủy (`CANCELLED`) theo quy tắc `OS-01`, không ghi nhận thời lượng vào chỉ số WRLS.
  4. Hệ thống giải phóng phiên học để tài khoản người học không còn bị khóa bởi ràng buộc đơn phiên duy nhất.
  5. Hệ thống gửi thông báo trong ứng dụng cho Người học giải thích về việc phiên học đã được tự động chốt do gián đoạn kết nối. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Xử lý nợ đúc kết quá hạn 24 giờ không nộp bù (B15, FR-SESSION-003)**: Tác vụ nền quét các bản ghi có `pending_takeaway = true` quá 24 giờ kể từ thời điểm chốt phiên gián đoạn. Thống nhất với `UC-EXEC-04`: hệ thống tự động hủy trạng thái nợ, không công nhận hoàn thành bài học (thu hồi partial credit), đưa các bài học dở dang về Hàng đợi phục hồi (`Backlog Recovery Queue`, `scheduled_date = NULL`) và khôi phục quyền mở phiên học mới cho người học.

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Lỗi kết nối cơ sở dữ liệu khi quét định kỳ**: Tiến trình nền ghi nhận lỗi vào log kiểm toán hệ thống, tự động thử lại ở chu kỳ kế tiếp sau 2 phút mà không làm gián đoạn các phiên học đang phát tín hiệu bình thường.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-SESS-05 (Ngưỡng chốt phiên gián đoạn và Ân hạn nợ đúc kết)**: Mất tín hiệu nhịp tim quá 5 phút kích hoạt tự động chốt phiên. Thời gian ân hạn nộp đúc kết bù cho phiên hoàn thành một phần là đúng 24 giờ.

---

#### UC-EXEC-07: Kết nối tài khoản Google Calendar

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-EXEC-07: Kết nối tài khoản Google Calendar** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Dịch vụ Lịch ngoại vi (`External Calendar Service` — `ACT-06`) |
| **Tiền điều kiện** | Người học đã đăng nhập; sở hữu tài khoản Google Calendar còn hoạt động. |
| **Hậu điều kiện thành công** | Tài khoản Google Calendar được liên kết thành công; mã ủy quyền truy cập (OAuth token) được mã hóa bảo mật và lưu trữ an toàn; kích hoạt tiến trình đồng bộ khoảng bận định kỳ (`UC-EXEC-08`). |
| **Bảo đảm tối thiểu** | Nếu người dùng từ chối cấp quyền hoặc quá trình xác thực thất bại, không lưu trữ thông tin lỗi, không ảnh hưởng đến lịch hiện tại. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-CALENDAR-002`, `B12` |

- **Luồng chính (Basic Flow)**:
  1. Người học mở trang Cài đặt Lịch học và chọn "Kết nối với Google Calendar".
  2. Hệ thống chuyển hướng Người học đến trang ủy quyền chính thức của Google (OAuth 2.0 Consent Screen) với phạm vi quyền hạn chỉ đọc lịch (`calendar.readonly` / `calendar.freebusy`).
  3. Người học đăng nhập Google và chấp thuận cấp quyền truy cập.
  4. Google chuyển hướng Người học quay trở lại FocusFlow kèm mã ủy quyền an toàn (Authorization Code).
  5. Hệ thống trao đổi mã ủy quyền để nhận cặp khóa truy cập an toàn, thực hiện mã hóa đối xứng mạnh (`BR-CAL-01`) trước khi lưu trữ vào hồ sơ kết nối của người học.
  6. Hệ thống kích hoạt ngay một lượt đồng bộ khoảng bận đầu tiên (`UC-EXEC-08`) và hiển thị thông báo đã kết nối thành công. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **1a. Ngắt kết nối Google Calendar (B12)**: Người học chọn "Ngắt kết nối Google Calendar"; hệ thống gửi yêu cầu thu hồi mã truy cập sang Google, xóa khóa mã hóa trong kho dữ liệu, xóa toàn bộ các khoảng thời gian bận đã đồng bộ trước đó và giải phóng thời gian rảnh. Use case kết thúc.

- **Luồng ngoại lệ (Exception Flows)**:
  - **3e. Người học từ chối cấp quyền trên màn hình Google OAuth**: Google chuyển hướng về FocusFlow với mã lỗi `access_denied`. Hệ thống không lưu bất kỳ token nào, hiển thị thông báo kết nối không thành công và giữ nguyên cài đặt lịch hiện tại.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-CAL-01 (Mã hóa an toàn mã truy cập lịch ngoại vi)**: Toàn bộ khóa truy cập và mã làm mới (OAuth Tokens) nhận được từ Google bắt buộc phải được mã hóa đối xứng bằng thuật toán mạnh (Fernet) trước khi lưu vào kho dữ liệu, tuyệt đối không lưu khóa ở dạng văn bản rõ.

---

#### UC-EXEC-08: Tự động cập nhật thời gian bận từ Google Calendar

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-EXEC-08: Tự động cập nhật thời gian bận từ Google Calendar** |
| **Mức độ & Phân tầng** | Mục tiêu hệ thống nền (System-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`Learner — ACT-02`) *(Kích hoạt tự động theo sự kiện thời gian nội bộ — OMG UML TimeEvent)* |
| **Tác nhân phụ** | Dịch vụ Lịch ngoại vi (`External Calendar Service` — `ACT-06`) |
| **Trigger** | Tác vụ quét định kỳ được khởi chạy theo chu kỳ 60 phút (`OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Người học có kết nối Google Calendar hợp lệ đang ở trạng thái kích hoạt; tác vụ quét định kỳ được khởi chạy theo chu kỳ 60 phút. |
| **Hậu điều kiện thành công** | Các khoảng thời gian bận (`Free/Busy`) trong 14 ngày tới được nạp và cập nhật; quỹ thời gian rảnh khả dụng của người học được tự động khấu trừ; nếu có xung đột với bài học đã xếp thì gửi cảnh báo nhận diện. |
| **Bảo đảm tối thiểu** | Tuyệt đối không tự ý xóa, hủy hoặc dời bất kỳ bài học nào trong FocusFlow khi phát hiện xung đột lịch (`BUSR-08`). |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-CALENDAR-002`, `FR-AVAIL-003`, `BUSR-08`, `B12` |

- **Luồng chính (Basic Flow)**:
  1. Sự kiện thời gian định kỳ (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ đồng bộ khoảng bận định kỳ mỗi 60 phút một lần.
  2. Hệ thống tìm kiếm danh sách các kết nối lịch ngoại vi đang hoạt động của người dùng.
  3. Với từng kết nối, hệ thống giải mã khóa truy cập OAuth và gửi yêu cầu truy vấn các khoảng bận (`Free/Busy Query`) trong cửa sổ 14 ngày tới sang Google Calendar API.
  4. Hệ thống tiếp nhận danh sách các khoảng thời gian bận (chỉ bao gồm mốc thời gian bắt đầu và kết thúc, không lưu nội dung chi tiết sự kiện cá nhân nhằm bảo vệ quyền riêng tư).
  5. Hệ thống cập nhật danh sách khoảng bận của người học, tự động khấu trừ vào quỹ thời gian rảnh khả dụng làm căn cứ cho việc kiểm định lịch (`UC-PLAN-09`).
  6. Hệ thống kiểm tra xem có bài học nào trong FocusFlow bị trùng giờ với khoảng bận mới nạp hay không. Nếu có, hệ thống tạo thông báo Cảnh báo xung đột lịch để Người học chủ động xem xét dời lịch (`BR-CAL-02`). Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **6a. Phát hiện xung đột với bài học đã xếp (Conflict Warning)**: Hệ thống phát hiện khoảng bận mới đè lấn lên bài học đã xếp, hiển thị biểu tượng cảnh báo xung đột trên giao diện để người học chủ động dời bài (`BR-CAL-02`).

- **Luồng ngoại lệ (Exception Flows)**:
  - **3e. Khóa truy cập Google bị hết hạn hoặc bị thu hồi**: Hệ thống sử dụng Refresh Token để làm mới. Nếu Refresh Token cũng không hợp lệ, hệ thống đánh dấu trạng thái kết nối là `NEEDS_REAUTH` và gửi thông báo cho Người học cập nhật ủy quyền.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-CAL-02 (Quy tắc không xâm lấn của đồng bộ Inbound — BUSR-08, B12)**: Dữ liệu đồng bộ từ lịch ngoại vi vào FocusFlow chỉ dùng để khấu trừ thời gian rảnh và cảnh báo xung đột. Hệ thống tuyệt đối không được tự ý xóa, hủy bỏ hoặc thay đổi lịch của bất kỳ bài học nào đã được người học sắp xếp.

---

#### UC-EXEC-09: Đồng bộ lịch học sang Google Calendar / ứng dụng lịch

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-EXEC-09: Đồng bộ lịch học sang Google Calendar / ứng dụng lịch** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Dịch vụ Lịch ngoại vi (`External Calendar Service` — `ACT-06`) |
| **Tiền điều kiện** | Người học đã đăng nhập; có ít nhất 01 lộ trình học tập đang hoạt động. |
| **Hậu điều kiện thành công** | Tệp lịch tĩnh chuẩn định dạng `.ics` được kết xuất và tải về máy người học HOẶC một liên kết WebCal đăng ký một chiều an toàn được cấp phát kèm mã định danh bảo mật duy nhất. |
| **Bảo đảm tối thiểu** | Liên kết WebCal không để lộ thông tin đăng nhập cá nhân; mã bảo mật chỉ lưu chuỗi băm một chiều SHA-256 trên máy chủ. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-CALENDAR-001`, `FR-CALENDAR-002`, `FR-CALENDAR-003`, `B13` |

- **Luồng chính (Basic Flow)**:
  1. Người học truy cập trang Quản lý đồng bộ lịch và chọn một trong hai phương thức xuất lịch:
     - *Phương thức A: Tải tệp lịch tĩnh `.ics`*: Tải toàn bộ các bài học đã lên lịch về để nạp thủ công vào các phần mềm lịch.
     - *Phương thức B: Sử dụng liên kết WebCal tự động*: Lấy đường dẫn URL đăng ký lịch (Subscription Feed) để các ứng dụng lịch ngoại vi tự động cập nhật lịch học định kỳ.
  2. Nếu người học chọn Phương thức A: Hệ thống trích xuất toàn bộ bài học có lịch trong lộ trình, đóng gói thành tệp tin chuẩn iCalendar (RFC 5545 `.ics`) và gửi về trình duyệt để người học tải xuống. Use case kết thúc.
  3. Nếu người học chọn Phương thức B: Hệ thống kiểm tra xem người học đã có mã bảo mật WebCal đang hoạt động hay chưa:
     - Nếu chưa có: Hệ thống sinh một chuỗi khóa bí mật ngẫu nhiên có độ dài 32 ký tự, lưu mã băm an toàn SHA-256 vào hệ thống (`BR-CAL-03`) và tạo đường dẫn liên kết WebCal an toàn dạng: `webcal://focusflow.app/api/calendar/feed/{token}`.
     - Nếu đã có: Hệ thống hiển thị trạng thái kết nối và cung cấp nút "Tạo lại liên kết mới (Xoay vòng mã bảo mật)" (`BR-CAL-04`).
  4. Hệ thống hiển thị đường dẫn liên kết WebCal và nút sao chép tiện lợi kèm hướng dẫn đăng ký trên Google Calendar, Apple Calendar hoặc Outlook.
  5. Các ứng dụng lịch ngoại vi định kỳ gọi đến đường dẫn WebCal này để đọc dữ liệu Lịch học chính thức theo chuẩn một chiều mà không cần đăng nhập lại. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Đặt lại mã bảo mật WebCal (Rotate WebCal Token — B13)**: Người học nhận thấy liên kết WebCal cũ bị lộ hoặc muốn ngắt đồng bộ các thiết bị cũ, bấm "Đặt lại liên kết mới". Hệ thống vô hiệu hóa mã băm cũ, sinh mã ngẫu nhiên mới và tạo URL WebCal mới. Toàn bộ các ứng dụng lịch sử dụng URL cũ sẽ bị từ chối truy cập ngay lập tức (`BR-CAL-04`).

- **Luồng ngoại lệ (Exception Flows)**:
  - **1e. Lộ trình chưa có bài học nào được lên lịch**: Người học yêu cầu xuất file `.ics` nhưng lộ trình chưa có bài học nào có ngày học cụ thể. Hệ thống hiển thị thông báo nhắc nhở xếp lịch trước khi xuất file.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-CAL-03 (Bảo mật liên kết WebCal Feed)**: Đường dẫn WebCal chỉ cấp quyền đọc dữ liệu một chiều đối với các bài học đã được lên lịch. Khóa bí mật trong liên kết chỉ được lưu trữ dưới dạng mã băm SHA-256 trên máy chủ để chống rò rỉ nếu cơ sở dữ liệu bị lộ.
  - **BR-CAL-04 (Chính sách xoay vòng mã bảo mật WebCal)**: Việc đặt lại liên kết mới có hiệu lực tức thì; toàn bộ các kết nối từ phía bên ngoài đang dùng mã bảo mật cũ sẽ bị trả về mã lỗi 401 Unauthorized.


### PHÂN HỆ 4: PHÂN TÍCH TIẾN ĐỘ, KIỂM CHỨNG NĂNG LỰC & THÍCH ỨNG

Phân hệ bao gồm 10 Use Cases đóng vai trò trái tim của mô hình tự học thích ứng (SRL): đo lường chỉ số Bắc đẩu WRLS, kiểm chứng năng lực chống học vẹt (Prove Mode), nghi thức chốt tuần phản tư, tịnh tiến lịch học Domino Shift, phục hồi bài quá hạn và tái thiết lộ trình ngủ đông.

```
Sơ đồ 4: Phân tích Tiến độ, Kiểm chứng Năng lực & Thích ứng (UC-ADAPT-01, UC-ADAPT-02, UC-ADAPT-03, UC-ADAPT-04, UC-ADAPT-05, UC-ADAPT-06, UC-ADAPT-07, UC-ADAPT-08, UC-ADAPT-09, UC-ADAPT-10, kèm UC-PLAN-09)
```

---

#### UC-ADAPT-01: Xem báo cáo tiến độ và bằng chứng học tập

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADAPT-01: Xem báo cáo tiến độ và bằng chứng học tập** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập; có dữ liệu học tập đã phát sinh. |
| **Hậu điều kiện thành công** | Báo cáo định lượng toàn diện được hiển thị bao gồm: chỉ số Bắc đẩu WRLS, tỷ lệ tuân thủ kế hoạch (Adherence Rate), Dòng thời gian Bằng chứng học tập (`Learning Evidence Timeline`) và biểu đồ độ lệch siêu nhận thức (`calibrationGap`). |
| **Bảo đảm tối thiểu** | Việc xem báo cáo chỉ đọc dữ liệu, không làm biến đổi số liệu học tập. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-REPORT-001`, `BUSR-09` |

- **Luồng chính (Basic Flow)**:
  1. Người học truy cập trang Phân tích & Báo cáo học tập.
  2. Hệ thống tổng hợp các chỉ số thực học trong 7 ngày và 30 ngày gần nhất.
  3. Hệ thống tính toán chỉ số Bắc đẩu WRLS (Weekly Roadmap Learning Score) theo công thức kết hợp đa chiều: tỷ lệ ngày học thành công ($D_{\text{attended}} / D_{\text{planned}}$), tỷ lệ hoàn thành khối lượng bài học và điểm chất lượng đúc kết (`BR-PROVE-01`).
  4. Hệ thống hiển thị Dòng thời gian Bằng chứng học tập (`Learning Evidence Timeline`): liệt kê tuần tự các Key Takeaways đã ghi nhận gắn với từng bài học và chứng chỉ Cột mốc (`PROVEN`).
  5. Hệ thống hiển thị biểu đồ phân tích Khoảng cách siêu nhận thức (`calibrationGap`): so sánh giữa mức độ tự tin chủ quan của người học (`selfConfidence 1..5`) với điểm số đánh giá khách quan trong các bài kiểm chứng năng lực Prove Mode. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **4a. Người học lọc bằng chứng theo cột mốc hoặc lộ trình cụ thể**: Hệ thống làm mới dòng thời gian và tính toán lại các chỉ số tập trung cho riêng phạm vi được chọn.

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Tài khoản mới chưa có dữ liệu học tập**: Hệ thống hiển thị bảng báo cáo rỗng kèm đồ họa hướng dẫn Người học hoàn thành phiên học đầu tiên để bắt đầu ghi nhận dữ liệu bằng chứng và tính toán WRLS.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-PROVE-01 (Công thức chỉ số Bắc đẩu WRLS)**: Chỉ số WRLS thang điểm 0–100 phản ánh tính kỷ luật và chất lượng tự học thực chất, tích hợp tỷ lệ chuyên cần ngày học, tỷ lệ hoàn thành khối lượng và điểm kiểm chứng năng lực cột mốc.

---

#### UC-ADAPT-02: Làm bài kiểm tra cột mốc

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ADAPT-02** |
| **Tên Use Case** | **Làm bài kiểm tra cột mốc** |
| **Mô tả ngắn** | Người học thực hiện bài kiểm chứng năng lực 2 tầng cuối cột mốc; hệ thống trích xuất Ground Truth (ưu tiên khái niệm `VERIFIED`, nếu `UNVERIFIED` thì đối chiếu nội dung bài học và Key Takeaways thực tế), gửi sang LLM Provider qua cơ chế giữ chỗ để sinh câu hỏi truy hồi xoáy vào điểm mù nhận thức, chấm điểm bằng chứng khách quan, cập nhật mức độ Nắm vững Kỹ năng (`Skill Mastery`), phân loại lỗi sai theo Trí tuệ Sai lầm 4 nhóm (`Mistake Intelligence`), lên lịch Ôn tập Thông minh (`Intelligent Revision`), cấp chứng chỉ cột mốc `PROVEN` hoặc gợi ý bài học bổ trợ nếu chưa đạt. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04`) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học bấm "Kiểm chứng năng lực (Prove Mode)" sau khi hoàn thành 100% bài học trong một Cột mốc kiến thức. |
| **Tiền điều kiện** | Toàn bộ bài học trong Cột mốc đã ở trạng thái `COMPLETED`; cột mốc chưa được cấp chứng chỉ `PROVEN`; số lần thử lại bài kiểm chứng cho cột mốc này chưa vượt quá 3 lần (`BR-PROVE-04`); hạn ngạch AI còn lượt khả dụng. |
| **Hậu điều kiện – thành công** | Cột mốc được cấp chứng chỉ `PROVEN`; bản ghi chứng nhận kiểm chứng năng lực (`milestone_proofs`) được lưu trữ kèm phân loại lỗi sai (`mistake_taxonomy_json`); ma trận `Skill Mastery` (`learner_concept_masteries`) được cập nhật; phiên ôn tập thông minh ngắt quãng được lên lịch; tính toán khoảng cách siêu nhận thức `calibrationGap`; nếu không đạt điểm chuẩn thì hiển thị danh sách bài học bổ trợ đề xuất (không tự động chèn). |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Không cấp chứng chỉ; hoàn trả hạn ngạch AI nếu có sự cố gọi dịch vụ; ghi nhận 1 lần thử lại thất bại. |
| **Include / Extend** | Không có |
| **Tần suất / Độ ưu tiên** | Định kỳ cuối mỗi cột mốc / Cực kỳ quan trọng (P0 — Must have) |
| **Tham chiếu SRS** | `FR-REPORT-003`, `SRS UC-20`, `BUSR-04`, `BUSR-05`, `D2`, `B4`, `B5` |

**Luồng chính (Basic Flow)**:
1. Người học chọn một Cột mốc đã hoàn thành toàn bộ bài học và nhấn nút "Bắt đầu kiểm chứng năng lực (Prove Mode)".
2. Hệ thống kiểm tra điều kiện tiên quyết: xác nhận 100% bài học đã `COMPLETED`, số lần đã thử lại của cột mốc $< 3$ (`BR-PROVE-04`) và số dư hạn ngạch AI khả dụng.
3. Hệ thống tổng hợp dữ liệu căn cứ Ground Truth theo cơ chế 2 cấp linh hoạt (`BR-PROVE-02`, `D2`):
   - Nếu cột mốc gắn với các khái niệm đã được duyệt (`VERIFIED`): Trích xuất định nghĩa và quan hệ chuẩn mực của khái niệm từ kho tri thức.
   - Nếu cột mốc gắn với các khái niệm chưa kiểm duyệt (`UNVERIFIED` do AI sinh ở `UC-PLAN-01`): Trích xuất nội dung thực tế của các bài học đã học kèm toàn bộ các ghi chú đúc kết (Key Takeaways) mà người học đã nhập để làm căn cứ đối chiếu.
4. Hệ thống giữ chỗ 1 lượt gọi AI (JIT Reservation).
5. Hệ thống gửi dữ liệu Ground Truth sang LLM Provider thông qua Cổng làm sạch câu lệnh (Sanitization Gate để chống Prompt Injection, `BR-PROVE-05`), yêu cầu sinh 2–3 câu hỏi truy hồi tình huống xoáy sâu vào điểm mù nhận thức và yêu cầu giải thích bản chất thay vì kiểm tra trắc nghiệm lý thuyết thuộc lòng.
6. LLM Provider phản hồi câu hỏi. Hệ thống COMMIT trừ 1 lượt hạn ngạch AI và hiển thị giao diện kiểm chứng cho Người học.
7. Người học nhập câu trả lời tự luận cho các câu hỏi truy hồi và bấm "Nộp bài kiểm chứng".
8. Hệ thống giữ chỗ tiếp 1 lượt AI và gửi câu trả lời của người học kèm Ground Truth sang LLM Provider để chấm điểm bằng chứng khách quan (`aiEvidenceScore` theo thang điểm chuẩn **1.00–5.00** khớp `FR-REPORT-003`) theo bộ tiêu chí rubrics chặt chẽ (`BR-PROVE-03`), đồng thời trích xuất phân loại lỗi sai nếu có câu trả lời chưa hoàn thiện (`BR-PROVE-07`).
9. LLM Provider phản hồi điểm số, phân tích lỗi sai và nhận xét chi tiết từng câu hỏi. Hệ thống COMMIT trừ lượt hạn ngạch.
10. Hệ thống so sánh điểm số với ngưỡng đạt chuẩn ($\ge 3.50 / 5.00$ điểm):
    - Điểm $\ge 3.50$: Cột mốc chính thức được công nhận đạt chuẩn, chuyển trạng thái sang `PROVEN`, ghi nhận chứng chỉ năng lực vào `milestone_proofs`.
    - Hệ thống cập nhật bảng ma trận năng lực khái niệm (`learner_concept_masteries` — `Skill Mastery`) của người học: nâng bậc thành thạo theo 5 cấp độ chuẩn hóa (`NOVICE` $\rightarrow$ `BEGINNER` $\rightarrow$ `COMPETENT` $\rightarrow$ `PROFICIENT` $\rightarrow$ `EXPERT`, `BR-PROVE-08`).
    - Hệ thống lên lịch phiên Ôn tập Thông minh (Intelligent Revision Slot) theo chu kỳ ngắt quãng Spaced Repetition vào thời gian biểu tương lai.
    - Hệ thống tính toán Khoảng cách siêu nhận thức có dấu:
      $$\text{calibrationGap} = \text{selfConfidence} - \text{aiEvidenceScore}$$
      (Giữ nguyên dấu; nếu $\text{calibrationGap} \ge +1.5$, hệ thống chẩn đoán hiện tượng Ảo tưởng năng lực — Illusion of Competence / Overconfidence).
11. Hệ thống lưu phân loại sai sót vào `mistake_taxonomy_json` (nếu có lỗi sai phát hiện ở các câu trả lời cụ thể) để tích lũy dữ liệu Trí tuệ Sai lầm (`Mistake Intelligence`) cho các đợt ôn tập tiếp theo.
12. Hệ thống hiển thị kết quả chúc mừng, nhận xét phân tích điểm mạnh, mức độ Skill Mastery đạt được và điểm mù kiến thức cần lưu ý cho Người học. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **10a. Điểm kiểm chứng không đạt chuẩn (< 3.50/5.00 điểm)**:
  1. Hệ thống không cấp chứng chỉ `PROVEN` cho Cột mốc, chuyển trạng thái kết quả sang `RETRY_REQUIRED`.
  2. Hệ thống tăng số lần đã thử lại của cột mốc lên 1: `retry_count = retry_count + 1`.
  3. Hệ thống phân loại nguyên nhân sai sót theo 4 nhóm Trí tuệ Sai lầm (`Mistake Intelligence`, `BR-PROVE-07`): (1) Thiếu kiến thức nền tảng (`MISSING_FOUNDATION`), (2) Hiểu sai bản chất khái niệm (`CONCEPT_MISCONCEPTION`), (3) Sai sót trong quy trình thao tác (`PROCESS_ERROR`), hoặc (4) Thiếu kỹ năng luyện tập (`LACK_OF_PRACTICE`), lưu vào `milestone_proofs.mistake_taxonomy_json`.
  4. Hệ thống đưa ra danh sách các bài học bổ trợ đề xuất (Corrective Tasks) tương ứng với nhóm lỗi sai dưới dạng gợi ý tự chọn trên giao diện, **tuyệt đối không tự ý chèn bài học vào Lịch học chính thức** (`BR-PROVE-06`).
  5. Người học có thể chọn học lại các bài bổ trợ này và quay lại kiểm chứng năng lực sau (tối đa 3 lần). Use case kết thúc.
- **7a. Người học tạm dừng và lưu bài làm dở**:
  1. Người học có việc đột xuất khi đang làm bài kiểm chứng.
  2. Hệ thống lưu bản nháp câu trả lời trong vòng 60 phút để người học có thể quay lại hoàn tất.

**Luồng ngoại lệ (Exception Flows)**:
- **2e. Cột mốc đã thử lại quá 3 lần thất bại (`retry_count >= 3`)**:
  1. Hệ thống khóa chức năng Prove Mode tự động cho cột mốc này.
  2. Hệ thống khuyến nghị Người học nên xem xét lại lộ trình, liên hệ người hướng dẫn hoặc đưa cột mốc vào kế hoạch ôn tập lại dài hạn.
  3. Use case kết thúc (thất bại).
- **5e / 8e. Dịch vụ AI không phản hồi hoặc vi phạm kiểm duyệt đầu ra**:
  1. Quá thời gian chờ 55 giây hoặc kết quả trả về sai cấu trúc.
  2. Hệ thống hoàn trả lượt giữ chỗ hạn ngạch (RELEASE), thông báo bài kiểm chứng tạm thời gián đoạn và cho phép người học thử lại mà không bị tính mất lượt thi.
  3. Use case kết thúc (thất bại).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-PROVE-02 (Cơ chế Ground Truth 2 cấp linh hoạt — D2, B4)**: Nếu cột mốc gắn với khái niệm `VERIFIED`, Ground Truth lấy từ kho khái niệm chuẩn. Nếu gắn với khái niệm `UNVERIFIED`, Ground Truth được tổng hợp từ nội dung bài học thực tế và các Key Takeaways của người học. Mục tiêu của Prove Mode là giảm thiểu tối đa gian lận và triệt tiêu thói quen học vẹt (không tuyên bố triệt tiêu 100% gian lận).
- **BR-PROVE-03 (Bộ tiêu chí chấm điểm khách quan Rubrics — FR-REPORT-003)**: Điểm kiểm chứng `aiEvidenceScore` chuẩn hóa theo thang điểm thực chứng 1.00–5.00 đánh giá dựa trên: (1) Khả năng giải thích khái niệm bằng ngôn từ cá nhân (40%), (2) Vận dụng giải quyết tình huống thực tế (35%), và (3) Độ chính xác đối chiếu Ground Truth Outcomes (25%). Ngưỡng đạt chuẩn cấp chứng chỉ `PROVEN` là $\ge 3.50/5.00$.
- **BR-PROVE-04 (Giới hạn số lần thử lại)**: Mỗi Cột mốc chỉ được phép thực hiện bài kiểm chứng tối đa 03 lần để chống hành vi thử sai liên tục nhằm vượt qua hệ thống kiểm tra.
- **BR-PROVE-05 (Cổng làm sạch câu lệnh Sanitization Gate — B5)**: Toàn bộ câu trả lời của người học phải được lọc qua bộ kiểm duyệt nội dung nhằm ngăn chặn các hành vi Prompt Injection (cố tình chèn lệnh buộc AI chấm điểm tuyệt đối).
- **BR-PROVE-06 (Khuyến nghị bài học bổ trợ không tự động chèn — B5)**: Khi không đạt kiểm chứng, các bài học bổ trợ (Corrective Tasks) chỉ được hiển thị dưới dạng đề xuất khuyến nghị để người học chủ động chọn thêm vào Backlog, hệ thống không tự động ép buộc chèn vào lịch học.
- **BR-PROVE-07 (Phân loại Lỗi sai 4 nhóm — Mistake Intelligence Taxonomy)**: Mọi câu trả lời chưa đạt phải được phân loại vào đúng 1 trong 4 danh mục chuẩn hóa: `MISSING_FOUNDATION`, `CONCEPT_MISCONCEPTION`, `PROCESS_ERROR`, hoặc `LACK_OF_PRACTICE`. Dữ liệu này được lưu trữ để làm giàu hồ sơ học tập và định hướng ôn tập thông minh.
- **BR-PROVE-08 (Cập nhật 5 Bậc Năng lực Khái niệm — Skill Mastery Level)**: Cấp độ nắm vững của mỗi khái niệm tri thức (`learner_concept_masteries`) tuân thủ nghiêm ngặt thang 5 bậc: `NOVICE` (vừa hoàn thành bài học) $\rightarrow$ `BEGINNER` (hoàn tất các bài luyện tập cơ bản) $\rightarrow$ `COMPETENT` (vượt qua Prove Mode với `aiEvidenceScore >= 3.50`) $\rightarrow$ `PROFICIENT` (vượt qua bài ôn tập ngắt quãng sau 7–14 ngày) $\rightarrow$ `EXPERT` (làm chủ chuyên sâu qua kiểm chứng đa lộ trình).

**Quản trị AI & An toàn**:
- Áp dụng kiểm duyệt prompt đầu vào, ngắt cứng 55s, cơ chế chấm đối chiếu kép kết hợp logic tất định và suy luận ngữ nghĩa của LLM.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Cột mốc kiến thức, Ground Truth, câu trả lời tự luận của người học.
- **Đầu ra**: Điểm `aiEvidenceScore`, chứng chỉ `PROVEN` (nếu đạt), cập nhật `Skill Mastery`, phân loại lỗi sai `mistake_taxonomy_json`, lịch ôn tập thông minh, nhận xét điểm mù, danh sách bài bổ trợ gợi ý (nếu không đạt).

---

#### UC-ADAPT-03: Đánh giá học tập cuối tuần

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ADAPT-03** |
| **Tên Use Case** | **Đánh giá học tập cuối tuần** |
| **Mô tả ngắn** | Người học kích hoạt nghi thức phản tư định kỳ cuối tuần gồm 2 pha riêng biệt: Pha 1 tính toán tất định tóm tắt định lượng (`quantitative_summary`), Pha 2 người học trả lời 2–3 câu hỏi tự phản tư ngắn (`Weekly Reflection`); hệ thống phối hợp với LLM Provider để tổng hợp nhận xét phản tư 3 phần theo chuẩn mô hình SRL của Zimmerman, hỗ trợ người học đặt cam kết cho tuần mới và thực hiện làm mới sớm Ngân sách dời lịch tuần (tối đa 1 lần/tuần). |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04`) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học bấm "Thực hiện Nghi thức Chốt tuần" từ thông báo nhắc nhở cuối tuần (Thứ Bảy/Chủ Nhật) hoặc từ trang Báo cáo học tập. |
| **Tiền điều kiện** | Người học đã đăng nhập; đã có ít nhất 01 tuần hoạt động học tập trong hệ thống. |
| **Hậu điều kiện – thành công** | Báo cáo nhận xét phản tư tuần được lưu lại (gồm `quantitative_summary`, `user_reflection_payload` và `ai_feedback`); cam kết mục tiêu tuần mới được thiết lập; Ngân sách dời lịch tuần được làm mới sớm (`weekly_reschedule_used = 0`) nếu tuần này chưa từng được làm mới sớm (`BR-REV-02`); trừ 1 lượt hạn ngạch AI (nếu dùng AI). |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Không ghi nhận báo cáo phản tư sai lệch; hoàn trả hạn ngạch AI nếu dịch vụ AI lỗi; ngân sách dời lịch giữ nguyên. |
| **Include / Extend** | Không có |
| **Tần suất / Độ ưu tiên** | Hàng tuần (Cuối tuần) / Quan trọng (P1 — Should have) |
| **Tham chiếu SRS** | `FR-REPORT-002`, `FR-ADAPT-001`, `SRS UC-21`, `BUSR-09`, `BUSR-10`, `D1`, `B6` |

**Luồng chính (Basic Flow)**:
1. Người học chọn chức năng Thực hiện Nghi thức Chốt tuần.
2. **Pha 1 — Tổng hợp Số liệu Định lượng Tất định (`Quantitative Summary`)**:
   - Hệ thống tự động tính toán 100% tất định (không dùng AI, không tốn quota): tổng giờ học thực tế so với kế hoạch, tỷ lệ tuân thủ kế hoạch (Plan Adherence Rate), số nhiệm vụ hoàn thành, số lượt dời lịch, xu hướng chỉ số WRLS và tổng hợp phân bổ từ các chip Daily Check-in trong tuần (`BR-REV-03`).
   - Hệ thống hiển thị bảng tóm tắt định lượng trực quan để người học rà soát.
3. **Pha 2 — Tự Phản tư Định tính (`Subjective Weekly Reflection`)**:
   - Hệ thống hiển thị 2–3 câu hỏi phản tư có định hướng: (1) Trở ngại hoặc sự cố lớn nhất làm gián đoạn lịch học tuần này là gì? (2) Khái niệm hoặc kỹ năng nào bạn cảm thấy tự tin nhất và phần nào còn mơ hồ? (3) Bạn dự định điều chỉnh thói quen hoặc khung giờ nào trong tuần tới?
   - Người học nhập câu trả lời tự phản tư ngắn (`user_reflection_payload`).
4. Hệ thống giữ chỗ 1 lượt gọi AI (JIT Reservation).
5. Hệ thống gửi kết hợp số liệu định lượng (`quantitative_summary`) và phản tư cá nhân của người học (`user_reflection_payload`) sang LLM Provider với yêu cầu sinh báo cáo nhận xét cố vấn sư phạm theo cấu trúc 3 phần Zimmerman SRL (`BR-REV-01`):
   - *Pha 1: Đánh giá thành tựu (Forethought Alignment)*: Đối chiếu kết quả thực học với mục tiêu tuần đã cam kết.
   - *Pha 2: Nhận diện rào cản (Performance Barriers)*: Phân tích sâu các nguyên nhân gián đoạn dựa trên phản tư của người học và số liệu thực tế.
   - *Pha 3: Điều chỉnh chiến lược (Adaptive Strategies)*: Đưa ra lời khuyên cụ thể về việc điều chỉnh khung giờ rảnh hoặc phân bổ bài học tuần tới.
6. LLM Provider phản hồi nội dung nhận xét trong thời gian cho phép ($\le 55$ giây).
7. Hệ thống COMMIT trừ 1 lượt hạn ngạch AI và hiển thị giao diện phân tích hoàn chỉnh kèm đề xuất cam kết cho tuần mới.
8. Người học đọc nhận xét, chọn số giờ cam kết cho tuần mới, điều chỉnh Backlog nếu cần và bấm **"Xác nhận hoàn tất Chốt tuần"**.
9. Hệ thống lưu bản ghi Báo cáo Chốt tuần (kèm `quantitative_summary`, `user_reflection_payload`, `ai_coaching_feedback`) vào hồ sơ người học.
10. Hệ thống kiểm tra điều kiện làm mới sớm Ngân sách dời lịch tuần theo cơ chế kép an toàn (`BR-REV-02`, `D1`):
    - Nếu tuần hiện tại chưa từng được làm mới sớm (`last_reset_week != CURRENT_WEEK`): Hệ thống đặt lại `weekly_reschedule_used = 0` (cấp đủ 3 lượt mới) và cập nhật `last_reset_week = CURRENT_WEEK`.
    - Nếu tuần này đã được làm mới trước đó: Hệ thống giữ nguyên số lượt hiện tại (không cộng dồn quá trần 3 lượt).
11. Hệ thống hiển thị thông báo chúc mừng hoàn thành nghi thức chốt tuần và cập nhật trạng thái sẵn sàng cho tuần học mới. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **3a. Người học không muốn dùng nhận xét AI (tự phản tư thủ công)**:
  1. Người học chọn "Tự phản tư không dùng AI".
  2. Hệ thống bỏ qua bước gọi AI, không trừ hạn ngạch AI, hiển thị bảng số liệu thống kê thuần túy để người học tự điền ghi chép đúc kết cá nhân.
  3. Tiếp tục từ bước 6 của luồng chính.

**Luồng ngoại lệ (Exception Flows)**:
- **5e. LLM Provider bị lỗi kết nối hoặc quá thời gian chờ**:
  1. Hệ thống giải phóng lượt giữ chỗ hạn ngạch (RELEASE), thông báo tính năng nhận xét AI đang gián đoạn.
  2. Hệ thống tự động chuyển sang chế độ phản tư thủ công (luồng thay thế 3a) để Người học không bị gián đoạn nghi thức.
  3. Use case kết thúc thành công theo chế độ thủ công.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-REV-01 (Cấu trúc nhận xét phản tư Zimmerman SRL)**: Báo cáo nhận xét chốt tuần do AI sinh ra bắt buộc phải bám sát cấu trúc 3 phần chuẩn sư phạm SRL: Đánh giá thành tựu, Nhận diện rào cản và Đề xuất thích ứng, mang giọng điệu khích lệ và tập trung vào giải pháp hành động thực tế.
- **BR-REV-02 (Cơ chế kép làm mới Ngân sách dời lịch an toàn — D1, B6)**: Việc làm mới ngân sách dời lịch tuần (`weekly_reschedule_used = 0`, trần 3 lượt) được điều tiết bởi 2 kênh: (1) Tự động bởi Bộ lập lịch lúc 00:00 Thứ Hai (`UC-ADAPT-10`), và (2) Cho phép làm mới sớm khi hoàn thành Nghi thức Chốt tuần (`UC-ADAPT-03`), nhưng mỗi tuần dương lịch chỉ được phép làm mới sớm tối đa 01 lần duy nhất (kiểm tra `last_reset_week`). Tuyệt đối không cho phép cộng dồn vượt quá 3 lượt.
- **BR-REV-03 (Phân tách Rạch ròi Pha Định lượng và Pha Định tính)**: Tóm tắt định lượng (`quantitative_summary`) bắt buộc phải được tính toán 100% bằng logic toán học tất định từ cơ sở dữ liệu trước khi gửi sang AI, đảm bảo AI không tự bịa đặt hay suy diễn sai lệch các con số thực học của người dùng.

**Quản trị AI & An toàn**:
- Dữ liệu gửi sang AI được ẩn danh hóa thông tin định danh cá nhân; chỉ gửi số liệu thống kê thời gian và tên bài học phục vụ phân tích.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Dữ liệu thực học trong tuần (`quantitative_summary`), ghi chép phản tư của người học (`user_reflection_payload`), cam kết giờ học tuần mới.
- **Đầu ra**: Báo cáo phản tư chốt tuần, ngân sách dời lịch tuần được làm mới (nếu đủ điều kiện), cập nhật `last_reset_week`.

---

#### UC-ADAPT-04: Tạm dừng lộ trình

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADAPT-04: Tạm dừng lộ trình** |
| **Mức độ & Phân tầng** | Mục tiêu người dùng (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Người học đã đăng nhập; lộ trình cần tạm dừng đang ở trạng thái hoạt động (`ACTIVE`). |
| **Hậu điều kiện thành công** | Trạng thái lộ trình chuyển sang `PAUSED`; lưu bản ghi `PauseRecord` gắn với lộ trình gồm `[PauseStartDate, PauseEndDate]`; tự động kích hoạt Thuật toán Domino Shift (`FR-PAUSE-002`) kết hợp cổng kiểm định `UC-PLAN-09` để tịnh tiến an toàn toàn bộ bài học chưa hoàn thành kể từ `PauseStartDate` ra sau ngày `PauseEndDate`; vô hiệu hóa toàn bộ cảnh báo quá hạn trong suốt thời gian tạm dừng; không tăng `reschedule_count` và không trừ `weekly_reschedule_used`. |
| **Bảo đảm tối thiểu** | Toàn bộ tiến độ và dữ liệu quá khứ được bảo lưu nguyên vẹn 100%; nếu người học hủy hoặc nhập khoảng ngày không hợp lệ, lộ trình giữ nguyên trạng thái `ACTIVE`; không có bài học nào bị xóa hay thay đổi sai lệch. |
| **Quan hệ UML** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` |
| **Tham chiếu SRS** | `FR-PAUSE-001`, `FR-PAUSE-002`, `BUSR-03`, `BUSR-07` |

- **Luồng chính (Basic Flow)**:
  1. Người học có việc đột xuất cá nhân (ốm đau, công tác, thi cử), chọn chức năng "Tạm dừng lộ trình" từ trang chi tiết hoặc menu cài đặt lộ trình.
  2. Hệ thống hiển thị hộp thoại Tạm dừng lộ trình, yêu cầu Người học chọn khoảng ngày tạm dừng xác định `[PauseStartDate, PauseEndDate]` (với quy tắc: `PauseStartDate >= CURRENT_DATE` và `PauseEndDate >= PauseStartDate`), đồng thời giải thích rõ các ngày tạm dừng sẽ không bị tính là ngày trễ hạn, không làm suy giảm chỉ số WRLS, và hệ thống sẽ tự động tịnh tiến lịch học an toàn (Domino Shift) không bị phạt số lần dời lịch.
  3. Người học xác nhận khoảng ngày tạm dừng và nhấn "Xác nhận Tạm dừng".
  4. Hệ thống kiểm tra điều kiện ngày hợp lệ, tạo bản ghi `PauseRecord` gắn với lộ trình (`roadmap_id`, `pause_start_date`, `pause_end_date`, `created_at = NOW()`) và chuyển trạng thái lộ trình sang `PAUSED`.
  5. Hệ thống tự động kích hoạt **Thuật toán Domino Shift (`FR-PAUSE-002`)**:
     - Lọc toàn bộ các bài học chưa hoàn thành có `scheduled_date >= PauseStartDate`.
     - Sắp xếp các bài học này theo thứ tự thời gian và thứ tự tiên quyết DAG ban đầu.
     - Bỏ qua toàn bộ các ngày nằm trong khoảng `[PauseStartDate, PauseEndDate]`.
     - Lần lượt xếp lại từng bài học vào các ngày khả dụng tiếp theo kể từ sau ngày `PauseEndDate` theo cấu hình Availability của Người học.
     - **Gọi `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include)** để xác thực không vi phạm giới hạn tải và không xung đột lịch bận.
     - Cập nhật ngày học mới cho toàn bộ các bài học bị ảnh hưởng trong `OfficialSchedule` và ghi nhận nhật ký `ScheduleChangeLog`.
  6. Thao tác tịnh tiến dây chuyền Domino Shift được gắn nhãn miễn trừ đặc biệt: **tuyệt đối không tăng `reschedule_count` của bài học và không khấu trừ vào Ngân sách dời lịch tuần (`weekly_reschedule_used`)** (`BR-SHIFT-03`).
  7. Trong toàn bộ khoảng thời gian từ `PauseStartDate` đến `PauseEndDate`, hệ thống vô hiệu hóa mọi thông báo, email và cảnh báo quá hạn đối với lộ trình này (`BUSR-07`); không tính ngày trễ hạn và không làm suy giảm tỷ lệ Plan Adherence hay chỉ số Bắc đẩu WRLS. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **5a. `UC-PLAN-09` trả về kết quả `SOFT_OVERFLOW` (Cảnh báo quá tải sau tịnh tiến — BUSR-04)**: Phát hiện sau khi tịnh tiến có bài học cuối cùng trong một ngày ở Chế độ B kết thúc muộn hơn khung rảnh $\le 30$ phút. Hệ thống hiển thị hộp thoại cảnh báo Soft Overflow, Người học bấm "Xác nhận áp dụng", hệ thống tiếp tục bước 6.

- **Luồng ngoại lệ (Exception Flows)**:
  - **3e. Khoảng ngày tạm dừng không hợp lệ**: Người học nhập `PauseStartDate < CURRENT_DATE` hoặc `PauseEndDate < PauseStartDate`. Hệ thống từ chối lưu, hiển thị thông báo lỗi và yêu cầu chọn lại khoảng ngày hợp lệ.
  - **5e. `UC-PLAN-09` trả về `INVALID` (Xung đột với lịch bận ngoại vi)**: Việc tịnh tiến làm phát sinh xung đột với các sự kiện bận trên Google Calendar. Hệ thống hiển thị chi tiết xung đột, đề xuất Người học điều chỉnh lại `PauseEndDate` hoặc dời các bài học bị xung đột trước khi hoàn tất tạm dừng.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-SHIFT-01 (Đóng băng tiến độ khi tạm dừng — BUSR-07, FR-PAUSE-001)**: Khoảng thời gian từ `PauseStartDate` đến `PauseEndDate` không bao giờ bị tính vào thời gian trễ hạn của các bài học hay làm suy giảm chỉ số Bắc đẩu WRLS hoặc tỷ lệ Plan Adherence của người học.
  - **BR-SHIFT-03 (Chính sách miễn trừ phạt của Domino Shift — FR-PAUSE-002)**: Mọi thao tác tịnh tiến lịch học do Tạm dừng (`UC-ADAPT-04`) hoặc Tiếp tục lộ trình (`UC-ADAPT-05`) đều được miễn trừ phạt: không tăng `reschedule_count` của bài học và không trừ vào Ngân sách dời lịch tuần (`weekly_reschedule_used`).

---

#### UC-ADAPT-05: Tiếp tục lộ trình và dời lịch bù ngày dừng

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ADAPT-05** |
| **Tên Use Case** | **Tiếp tục lộ trình và dời lịch bù ngày dừng** |
| **Mô tả ngắn** | Người học kích hoạt lại hoặc hệ thống tự động tiếp tục lộ trình đang tạm dừng (`PAUSED`); hệ thống kiểm tra trần số lộ trình hoạt động của gói cước, xử lý chuẩn hóa luồng Resume khi hết hạn hoặc tiếp tục sớm, tịnh tiến điều chỉnh các bài học tương lai mà không phạt bộ đếm hay trừ ngân sách, kiểm định lịch mới qua `UC-PLAN-09` và khôi phục trạng thái hoạt động (`ACTIVE`). |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Không có |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học bấm "Tiếp tục học (Resume)" trên một lộ trình đang ở trạng thái `PAUSED`, HOẶC khoảng thời gian tạm dừng kết thúc (`CURRENT_DATE > PauseEndDate` — `OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Lộ trình đang ở trạng thái `PAUSED` và có bản ghi `PauseRecord` (`[PauseStartDate, PauseEndDate]`) hợp lệ; người học đã đăng nhập. |
| **Hậu điều kiện – thành công** | Lộ trình chuyển sang trạng thái hoạt động (`ACTIVE`); toàn bộ bài học tương lai được căn chỉnh ngày học xuôi theo thời gian bắt đầu từ ngày hợp lệ gần nhất; không tăng `reschedule_count` và không trừ ngân sách dời lịch tuần (`BR-SHIFT-03`); lịch học mới vượt qua kiểm định `UC-PLAN-09`; cập nhật `last_study_activity_at = NOW()`. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Lộ trình giữ nguyên trạng thái `PAUSED`; lịch học không bị thay đổi nếu người dùng chưa giải quyết vượt trần lộ trình hoặc lịch mới không hợp lệ. |
| **Include / Extend** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` *(Bắt buộc 100%)* |
| **Tần suất / Độ ưu tiên** | Thấp – Trung bình / Cực kỳ quan trọng (P0 — Must have) |
| **Tham chiếu SRS** | `FR-PAUSE-001`, `FR-PAUSE-002`, `FR-PLAN-005`, `BUSR-07`, `OS-02`, `BUSR-04` |

**Luồng chính (Basic Flow)**:
1. Trigger kích hoạt: Người học chủ động nhấn "Tiếp tục học lộ trình này (Resume)" trên giao diện danh mục lộ trình, HOẶC sự kiện thời gian (`OMG UML 2.5.1 TimeEvent`) ghi nhận ngày hiện tại đã vượt qua ngày kết thúc tạm dừng (`CURRENT_DATE > PauseEndDate`).
2. Hệ thống kiểm tra trần số lộ trình hoạt động (`ACTIVE`) theo gói cước của Người học (`BR-PLAN-01`, `OS-02`):
   - Nếu tài khoản gói `FREE` hiện tại đã có đủ 3 lộ trình đang `ACTIVE`, hệ thống thông báo trần lộ trình đã đạt tối đa và yêu cầu Người học chọn tạm dừng hoặc lưu trữ một lộ trình khác trước khi tiếp tục lộ trình này (`2a`).
3. Hệ thống xác định phương thức tiếp tục lộ trình căn cứ theo mốc thời gian:
   - **Trường hợp 1: Người học chủ động tiếp tục sớm (`CURRENT_DATE <= PauseEndDate`)**:
     - Người học muốn quay lại học sớm hơn dự kiến. Hệ thống cập nhật bản ghi `PauseRecord` với `actual_end_date = CURRENT_DATE - 1`.
     - Do bài học đã được dời ra sau `PauseEndDate` từ trước (`UC-ADAPT-04`), hệ thống kích hoạt lại Domino Shift điều chỉnh để kéo các bài học chưa hoàn thành về bắt đầu từ ngày hôm nay (`CURRENT_DATE`), tự động điều chỉnh nhảy qua các ngày nghỉ theo cấu hình Availability.
   - **Trường hợp 2: Hết hạn tạm dừng hoặc tiếp tục sau hạn (`CURRENT_DATE >= PauseEndDate + 1`)**:
     - Toàn bộ bài học đã được xếp sẵn sàng từ sau `PauseEndDate` tại thời điểm Pause (`UC-ADAPT-04`).
     - Nếu `CURRENT_DATE > PauseEndDate + 1` (Người học quay lại muộn hơn ngày kết thúc tạm dừng), hệ thống tính số ngày trễ thêm: $\text{shiftedDays} = \text{CURRENT\_DATE} - (\text{PauseEndDate} + 1)$ và thực hiện tịnh tiến thêm $\text{shiftedDays}$ ngày khả dụng cho các bài học chưa hoàn thành.
4. Thao tác tiếp tục lộ trình được gắn nhãn miễn trừ đặc biệt: **tuyệt đối không tăng `reschedule_count` của bài học và không khấu trừ vào Ngân sách dời lịch tuần** (`BR-SHIFT-03`).
5. Hệ thống chuẩn bị phương án lịch mới và **gọi `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include)**.
6. `UC-PLAN-09` kiểm định và trả về kết quả `VALID` (toàn bộ đồ thị DAG, khung giờ rảnh và khoảng bận ngoại vi đều hợp lệ).
7. Hệ thống cập nhật trạng thái lộ trình từ `PAUSED` sang `ACTIVE`.
8. Hệ thống chính thức lưu lịch học đã tịnh tiến vào Lịch học chính thức (`OfficialSchedule`), cập nhật mốc hoạt động học tập `last_study_activity_at = NOW()`.
9. Hệ thống hiển thị thông báo chào mừng người học quay trở lại, trình bày tóm tắt lịch học mới đã được điều chỉnh và đưa bài học phù hợp vào Thẻ Tiêu điểm Hôm nay. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **2a. Tài khoản chạm trần 3 lộ trình ACTIVE (Gói Free — OS-02)**:
  1. Hệ thống phát hiện người dùng gói Free đang có 3 lộ trình `ACTIVE` khác.
  2. Hệ thống hiển thị danh sách 3 lộ trình đang chạy và yêu cầu người học bấm chọn 1 lộ trình để chuyển sang `PAUSED` hoặc `ARCHIVED`.
  3. Người học chọn một lộ trình để tạm dừng.
  4. Hệ thống chuyển lộ trình đó sang `PAUSED`, giải phóng 1 chỉ tiêu hoạt động và quay lại bước 3 của luồng chính để mở lại lộ trình mong muốn.
- **6a. `UC-PLAN-09` trả về kết quả `SOFT_OVERFLOW` (Cảnh báo quá tải sau tịnh tiến — BUSR-04)**:
  1. `UC-PLAN-09` phát hiện sau khi tịnh tiến có bài học cuối cùng trong một ngày ở Chế độ B kết thúc muộn hơn khung rảnh $\le 30$ phút (`BUSR-04`).
  2. Hệ thống hiển thị hộp thoại cảnh báo: "Lịch học sau khi tịnh tiến có bài học cuối ngày kết thúc muộn hơn khung rảnh tối đa 30 phút. Bạn có muốn tiếp tục áp dụng không?".
  3. Người học chọn "Xác nhận áp dụng".
  4. Hệ thống tiếp tục từ bước 7 của luồng chính.

**Luồng ngoại lệ (Exception Flows)**:
- **2e. Người học từ chối giải phóng lộ trình khi chạm trần**: Người học bấm hủy khi được yêu cầu tạm dừng/lưu trữ lộ trình khác. Hệ thống giữ nguyên trạng thái `PAUSED` của lộ trình này, không thay đổi lịch học. Use case kết thúc.
- **6e. `UC-PLAN-09` trả về kết quả `INVALID` (Xung đột với lịch bận ngoại vi)**:
  1. `UC-PLAN-09` phát hiện việc tịnh tiến làm một số bài học đè lấn lên các sự kiện bận từ Google Calendar vừa mới phát sinh trong thời gian người học tạm dừng.
  2. Hệ thống hiển thị thông báo xung đột chi tiết và tự động đề xuất chuyển sang ca sử dụng Dời lịch bằng AI (`UC-ADAPT-06`) hoặc tự điều chỉnh thủ công (`UC-EXEC-02`) để giải quyết xung đột trước khi kích hoạt lại lộ trình.
  3. Lộ trình tạm thời giữ nguyên trạng thái `PAUSED`. Use case kết thúc (thất bại tạm thời).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-SHIFT-02 (Chuẩn hóa Thuật toán Domino Shift — FR-PAUSE-002)**: Thuật toán Domino Shift luôn bảo toàn 100% thứ tự trước sau và quan hệ tiên quyết DAG của các bài học. Khi tịnh tiến ngày học, hệ thống bắt buộc tự động nhảy qua các ngày nghỉ không có thời gian rảnh theo cấu hình cá nhân của Người học.
- **BR-SHIFT-03 (Chính sách miễn trừ phạt của Domino Shift — FR-PAUSE-002)**: Mọi thao tác tịnh tiến lịch học do Tạm dừng (`UC-ADAPT-04`) hoặc Tiếp tục lộ trình (`UC-ADAPT-05`) đều được miễn trừ phạt: không tăng `reschedule_count` của bài học và không trừ vào Ngân sách dời lịch tuần (`weekly_reschedule_used`).

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Lộ trình `PAUSED`, bản ghi `PauseRecord` (`[PauseStartDate, PauseEndDate]`), ngày hiện tại `CURRENT_DATE`.
- **Đầu ra**: Lộ trình chuyển sang `ACTIVE`, toàn bộ bài học tương lai được tịnh tiến ngày học an toàn, cập nhật `last_study_activity_at = NOW()`, Lịch học chính thức được cập nhật.

---

#### UC-ADAPT-06: Dời lịch bằng AI cho bài quá hạn (Rolling-Horizon Overdue Recovery)

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ADAPT-06** |
| **Tên Use Case** | **Phục hồi Quá hạn theo Cửa sổ trượt & Điều chỉnh Tải học tập (Rolling-Horizon Overdue Recovery)** |
| **Mô tả ngắn** | Người học kích hoạt AI và Động cơ Lập lịch để tự động tái phân bổ các bài học quá hạn theo cơ chế Cửa sổ trượt 7–14 ngày (`Rolling-Horizon Window`) và Điều chỉnh Tải học tập thích ứng (`Adaptive Workload`); ưu tiên hấp thụ độ trễ vào các khối thời gian đệm (`BUFFER` blocks), bảo vệ tuyệt đối các phiên học then chốt (`is_protected = true`), kiểm định qua `UC-PLAN-09`, hiển thị Bảng đối chiếu phục hồi (Recovery Proposal Diff) và chỉ khấu trừ 1 lượt Ngân sách dời lịch tuần (`weeklyRescheduleBudget`) khi Người học chủ động nhấn Áp dụng. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04`) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học bấm "Dời lịch thông minh bằng AI" từ cảnh báo bài quá hạn hoặc từ trang chi tiết lộ trình. |
| **Tiền điều kiện** | Lộ trình có ít nhất 01 bài học đang bị quá hạn (`isOverdue = true`); Ngân sách dời lịch tuần còn lượt khả dụng (`weekly_reschedule_used < 3`, `BR-ADAPT-01`); hạn ngạch AI còn lượt. |
| **Hậu điều kiện – thành công** | Bản đề xuất phục hồi theo cửa sổ trượt được áp dụng; các bài học quá hạn được phân bổ vào các khối đệm hoặc ngày mới hợp lệ trong cửa sổ 7–14 ngày; các khối học mang cờ `is_protected = true` được bảo toàn nguyên vẹn; trạng thái bài học cập nhật theo Lịch học chính thức mới; tăng số lượt ngân sách đã dùng `weekly_reschedule_used = weekly_reschedule_used + 1`; trừ 1 lượt hạn ngạch AI. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Giữ nguyên ngày học hiện tại của các bài học; không trừ ngân sách dời lịch tuần nếu người học hủy hoặc dịch vụ AI gặp sự cố. |
| **Include / Extend** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` *(Bắt buộc 100%)* |
| **Tần suất / Độ ưu tiên** | Trung bình / Cực kỳ quan trọng (P0 — Must have) |
| **Tham chiếu SRS** | `FR-ADAPT-001`, `FR-ADAPT-002`, `FR-PLAN-005`, `SRS UC-23`, `BUSR-02`, `BUSR-06`, `BUSR-10`, `D1`, `A4` |

**Luồng chính (Basic Flow)**:
1. Người học chọn chức năng Dời lịch thông minh bằng AI cho lộ trình có các bài học quá hạn.
2. Hệ thống kiểm tra điều kiện Ngân sách dời lịch tuần: xác nhận số lượt dời lịch AI đã sử dụng trong tuần còn nhỏ hơn 3 (`weekly_reschedule_used < 3`, `BR-ADAPT-01`).
3. Hệ thống kiểm tra số dư hạn ngạch AI và thực hiện giữ chỗ 1 lượt (JIT Reservation).
4. Hệ thống trích xuất ngữ cảnh phục hồi giới hạn trong **Cửa sổ trượt 7–14 ngày tới (`Rolling-Horizon Window`)** (`BR-ADAPT-03`): danh sách bài học quá hạn, các khối học đã lên lịch trong cửa sổ này, các khối học được bảo vệ (`is_protected = true`), các khối thời gian đệm (`BUFFER` slots) và khoảng bận ngoại vi.
5. Hệ thống kích hoạt AI kết hợp Động cơ Lập lịch tất định thực thi thuật toán phục hồi 7 bước:
   - Ưu tiên 1: Chèn bài quá hạn vào các khối thời gian đệm (`BUFFER` blocks) sẵn có trong tuần để hấp thu độ trễ mà không làm dịch chuyển các bài học khác.
   - Ưu tiên 2: Điều chỉnh tải thích ứng (`Adaptive Workload`): nới lỏng tạm thời trần tải hàng ngày trong giới hạn cho phép ($\le 30\%$ định mức) đối với các ngày có năng lượng cao.
   - Ưu tiên 3: Tuyệt đối không thay đổi ngày hoặc giờ của các khối học mang cờ `is_protected = true` (`BR-VAL-05`).
   - Ưu tiên 4: Chỉ dịch chuyển các bài học thông thường chưa được bảo vệ sang các ngày khả dụng kế tiếp trong cửa sổ trượt.
6. Hệ thống khởi tạo Bản đề xuất lịch học phục hồi (`ScheduleProposal`, `proposal_type = 'AI_RECOVERY'`, sinh bởi tiến trình `workflow_runs.workflow_type = 'OVERDUE_RECOVERY'`) ở trạng thái nháp (`DRAFT`). **Tuyệt đối không cập nhật trực tiếp vào Lịch học chính thức**.
7. Hệ thống gọi `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include) để xác thực độ bền vững của phương án phục hồi.
8. `UC-PLAN-09` kiểm định và trả về kết quả `VALID` (hoặc `SOFT_OVERFLOW` được chấp nhận).
9. Hệ thống COMMIT trừ 1 lượt hạn ngạch AI tháng.
10. Hệ thống hiển thị Bảng đối chiếu phục hồi (Recovery Proposal Diff Preview): hiển thị rõ ràng từng bài quá hạn được hấp thu vào buffer slot nào hoặc dời sang ngày nào, tổng thời lượng tải mỗi ngày, các phiên bảo vệ được giữ nguyên và số lượt Ngân sách dời lịch tuần sẽ bị trừ nếu bấm áp dụng.
11. Người học xem xét phương án và bấm nút **"Áp dụng phương án phục hồi"**.
12. Hệ thống thực hiện giao dịch cập nhật:
    - Chuyển trạng thái Bản đề xuất sang `APPLIED`.
    - Cập nhật các `schedule_blocks` mới vào Lịch học chính thức (`OfficialSchedule`).
    - Khấu trừ 1 lượt ngân sách dời lịch tuần: `weekly_reschedule_used = weekly_reschedule_used + 1` (`BR-ADAPT-01`).
13. Hệ thống thông báo dời lịch thành công và làm mới giao diện Thẻ Tiêu điểm Hôm nay. Cấu trúc bài học quá hạn được giải tỏa. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **8a. `UC-PLAN-09` trả về kết quả `SOFT_OVERFLOW` (A4)**:
  1. `UC-PLAN-09` phát hiện phương án dời lịch có áp dụng Điều chỉnh Tải thích ứng (Adaptive Workload) làm một số ngày vượt nhẹ từ 10% đến 30% định mức ngày.
  2. Hệ thống hiển thị hộp thoại cảnh báo: "Phương án phục hồi đề xuất tăng nhẹ thời gian học trong 2 ngày tới để dứt điểm bài tồn đọng. Bạn có sẵn sàng cam kết học thêm không?".
  3. Người học bấm "Xác nhận đồng ý".
  4. Hệ thống tiếp tục từ bước 9 của luồng chính.
- **11a. Người học từ chối áp dụng phương án dời lịch**:
  1. Người học xem bảng đối chiếu và chọn "Hủy bỏ bản đề xuất".
  2. Hệ thống xóa Bản đề xuất nháp, giữ nguyên lịch cũ, không trừ ngân sách dời lịch tuần (`weekly_reschedule_used` giữ nguyên). Use case kết thúc.

**Luồng ngoại lệ (Exception Flows)**:
- **2e. Ngân sách dời lịch tuần đã cạn kiệt (`weekly_reschedule_used >= 3`)**:
  1. Hệ thống chặn không cho phép gọi AI dời lịch tự động.
  2. Hệ thống thông báo rõ: "Bạn đã sử dụng hết 3/3 lượt dời lịch AI trong tuần này. Ngân sách sẽ tự động được làm mới vào 00:00 Thứ Hai tới hoặc bạn có thể thực hiện Đánh giá học tập cuối tuần để làm mới sớm".
  3. Hệ thống gợi ý người học dời lịch thủ công (`UC-EXEC-02`) hoặc nếu lộ trình đã bị gián đoạn dài ngày thì kích hoạt Khôi phục lộ trình bị gián đoạn lâu ngày (`UC-ADAPT-07`).
  4. Use case kết thúc (thất bại).
- **8e. `UC-PLAN-09` trả về kết quả `INVALID`**:
  1. Phương án phục hồi vi phạm quy tắc cứng hoặc không thể xếp trong cửa sổ trượt 14 ngày.
  2. Hệ thống tự động yêu cầu Động cơ lập lịch mở rộng cửa sổ trượt lên 21 ngày hoặc chuyển phần bài dư vào Backlog Queue.
  3. Nếu vẫn không tìm được phương án hợp lệ, hệ thống giải phóng lượt giữ chỗ hạn ngạch (RELEASE), hiển thị thông báo lỗi và hướng dẫn dời lịch thủ công.
  4. Use case kết thúc (thất bại).

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-ADAPT-01 (Quản trị Ngân sách dời lịch tuần — Weekly Reschedule Budget)**: Mỗi tuần người học chỉ có tối đa 03 lượt sử dụng AI để dời lịch tự động (`weekly_reschedule_used <= 3`). Thao tác khấu trừ ngân sách chỉ diễn ra khi và chỉ khi người học bấm nút Áp dụng (Apply) bản đề xuất. Việc sinh bản nháp hoặc hủy bỏ không làm mất lượt ngân sách.
- **BR-ADAPT-02 (Phạm vi dời lịch đơn lộ trình — Single Roadmap Scope)**: Để kiểm soát độ phức tạp và tránh xáo trộn dây chuyền, mỗi lệnh gọi dời lịch AI chỉ xử lý các bài học quá hạn trong phạm vi duy nhất 01 lộ trình học tập được chọn, không tự ý đảo lộn lịch của các lộ trình khác.
- **BR-ADAPT-03 (Nguyên lý Cửa sổ trượt & Hấp thụ Đệm — Rolling-Horizon & Buffer Absorption)**: Phục hồi quá hạn chỉ tối ưu hóa cục bộ trong cửa sổ trượt từ 7 đến 14 ngày tới. Hệ thống bắt buộc phải ưu tiên lấp đầy các khoảng đệm (`BUFFER` slots) trước khi dịch chuyển các khối học thông thường khác, bảo đảm tính ổn định dài hạn của lộ trình.

**Quản trị AI & An toàn**:
- Tuân thủ nguyên tắc Human-in-the-loop: AI chỉ tạo bản thảo `DRAFT`, người học kiểm tra bản Diff Preview và phê duyệt mới cập nhật lịch chính thức.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Lộ trình có bài quá hạn, cửa sổ trượt 7–14 ngày, các khối buffer, các khối protected sessions.
- **Đầu ra**: Bản đề xuất phục hồi (`ScheduleProposal`), cập nhật Lịch học chính thức, tăng `weekly_reschedule_used` lên 1.

---

#### UC-ADAPT-07: Khôi phục lộ trình bị gián đoạn lâu ngày

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ADAPT-07** |
| **Tên Use Case** | **Khôi phục lộ trình bị gián đoạn lâu ngày** |
| **Mô tả ngắn** | Kích hoạt nghi thức tái thiết tâm lý và lịch trình 4 bước cho một lộ trình bị rơi vào trạng thái ngủ đông (`isDormant = true`, không có hoạt động $\ge 7$ ngày) hoặc bị bế tắc do hết ngân sách dời lịch; người học phân loại nguyên nhân gián đoạn, chọn 1 trong 3 chiến lược phục hồi (*Khởi động nhẹ 7 ngày*, *Thu hẹp phạm vi Cột mốc*, hoặc *Lưu trữ chủ động*); hệ thống kiểm định qua `UC-PLAN-09`, cập nhật mốc hoạt động mới `last_study_activity_at = NOW()` để giải phóng ngay trạng thái ngủ đông, và cấp đủ 3 lượt ngân sách dời lịch mới. |
| **Tác nhân chính** | Người học (`Learner` — `ACT-02`) |
| **Tác nhân phụ** | Nhà cung cấp dịch vụ LLM (`External LLM Provider` — `ACT-04`) |
| **Mức độ** | Mục tiêu người dùng (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Người học bấm "Tái thiết lộ trình (Reset Ritual)" từ banner cảnh báo lộ trình ngủ đông (`isDormant = true`) hoặc khi hết ngân sách dời lịch mà còn bài tồn đọng. |
| **Tiền điều kiện** | Lộ trình đang ở trạng thái `ACTIVE` và bị ngủ đông ($\ge 7$ ngày không có phiên học hợp lệ, `last_study_activity_at < NOW() - 7 ngày`) HOẶC đã hết ngân sách dời lịch tuần (`weekly_reschedule_used >= 3`); người học đã đăng nhập. |
| **Hậu điều kiện – thành công** | Lộ trình được tái thiết lập theo chiến lược đã chọn; cập nhật `last_study_activity_at = NOW()` giải phóng ngay trạng thái ngủ đông (`isDormant = false`, `D4`); đặt lại ngân sách dời lịch tuần `weekly_reschedule_used = 0` và cập nhật `last_reset_week = CURRENT_WEEK` (nếu chưa reset trong tuần theo `FR-ADAPT-001`); tăng bộ đếm số lần tái thiết `reset_ritual_count = reset_ritual_count + 1`. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Lộ trình giữ nguyên trạng thái cũ nếu người học hủy bỏ giữa chừng. |
| **Include / Extend** | `<<include>> UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` *(Bắt buộc đối với Chiến lược A và B)* |
| **Tần suất / Độ ưu tiên** | Không thường xuyên (Theo sự cố gián đoạn) / Quan trọng (P1 — Should have) |
| **Tham chiếu SRS** | `FR-ADAPT-003`, `FR-PLAN-005`, `BUSR-06`, `BUSR-07`, `D1`, `D4`, `B9`, `B10` |

**Luồng chính (Basic Flow)**:
1. Người học bấm nút "Tái thiết lộ trình (Reset Ritual)" trên lộ trình đang bị ngủ đông hoặc bị bế tắc lịch học.
2. **Bước 1: Giải tỏa áp lực tâm lý & Phân loại gián đoạn**:
   - Hệ thống hiển thị thông điệp thấu cảm không phán xét: "Gián đoạn là một phần tất yếu của quá trình tự học. Hãy cùng FocusFlow tái thiết kế lại kế hoạch để bạn dễ dàng bắt nhịp trở lại mà không có bất kỳ áp lực nào!".
   - Hệ thống yêu cầu Người học chọn Nguyên nhân chính dẫn đến việc gián đoạn (`disruptionCategory`: Biến cố công việc/học tập đột xuất, Quá tải khối lượng/Kiệt sức, Mất động lực học, Khác).
3. **Bước 2: Lựa chọn 1 trong 3 Chiến lược phục hồi (`BR-RESET-01`, `B10`)**:
   - *Chiến lược A: Khởi động nhẹ 7 ngày (7-Day Light Reboot)*: Giảm 50% khối lượng học trong 7 ngày tới, chỉ xếp 1–2 bài học ngắn mỗi ngày để tìm lại nhịp điệu.
   - *Chiến lược B: Thu hẹp phạm vi Cột mốc (Re-scope Milestones — B10)*: Cho phép người học rà soát và bỏ chọn bớt các Cột mốc không cốt lõi, đưa các bài học phụ về Backlog để tập trung vào mục tiêu tối thiểu khả thi.
   - *Chiến lược C: Lưu trữ chủ động (Intentional Archive — B10)*: Chủ động đóng gói và chuyển lộ trình vào mục Lưu trữ một cách tự hào mà không cảm thấy tội lỗi.
4. Người học chọn Chiến lược A (hoặc Chiến lược B).
5. **Bước 3: AI sinh đề xuất tái thiết kế lịch học**:
   - Hệ thống giữ chỗ 1 lượt hạn ngạch AI và gửi yêu cầu sang LLM Provider để tái sắp xếp các bài học căn cứ theo chiến lược đã chọn.
   - LLM Provider phản hồi bản đề xuất lịch phục hồi dạng JSON.
   - Hệ thống tạo Bản đề xuất lịch học nháp (`ScheduleProposal` ở trạng thái `DRAFT`).
6. Hệ thống thực hiện kiểm định tính hợp lệ của lịch phục hồi bằng cách **gọi `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (include)**.
7. `UC-PLAN-09` kiểm định và trả về kết quả `VALID` (hoặc `SOFT_OVERFLOW` được người học xác nhận).
8. Hệ thống COMMIT trừ 1 lượt hạn ngạch AI và hiển thị chi tiết kế hoạch phục hồi mới cho Người học xem trước.
9. **Bước 4: Xác nhận và Tái kích hoạt lộ trình**:
   - Người học nhấn nút **"Xác nhận Tái thiết lộ trình"**.
   - Hệ thống áp dụng lịch học mới vào Lịch học chính thức (`OfficialSchedule`).
   - Hệ thống cập nhật mốc hoạt động học tập mới nhất: `last_study_activity_at = NOW()`, từ đó giải phóng ngay lập tức trạng thái ngủ đông (`isDormant = false`, `D4`, `B9`).
   - **Xác thực và cập nhật ngân sách dời lịch tuần**: Hệ thống kiểm tra điều kiện tuần:
     - Nếu `last_reset_week != CURRENT_WEEK` (hoặc `NULL`), hệ thống cập nhật `last_reset_week = CURRENT_WEEK` và đặt lại bộ đếm ngân sách dời lịch tuần `weekly_reschedule_used = 0` (cấp đủ 3 lượt dời lịch mới theo `FR-ADAPT-001`, `D1`).
     - Nếu `last_reset_week == CURRENT_WEEK` (người học đã thực hiện Reset Ritual trong tuần hiện tại), hệ thống KHÔNG đặt lại `weekly_reschedule_used` nhằm chống lạm dụng reset ngân sách nhiều lần trong cùng một tuần (`FR-ADAPT-001`).
   - Hệ thống tăng bộ đếm số lần tái thiết: `reset_ritual_count = reset_ritual_count + 1`.
10. Hệ thống hiển thị thông báo chúc mừng người học đã sẵn sàng trở lại và cập nhật bài học đầu tiên của kế hoạch mới lên Thẻ Tiêu điểm Hôm nay. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **4a. Người học chọn Chiến lược C: Lưu trữ chủ động (Intentional Archive — B10)**:
  1. Người học nhận thấy lộ trình này hiện không còn phù hợp với mục tiêu cuộc sống hiện tại và chọn Chiến lược C.
  2. Hệ thống hiển thị hộp thoại xác nhận bắt buộc: "Bạn có chắc chắn muốn lưu trữ lộ trình này? Toàn bộ các bài học chưa hoàn thành sẽ được đóng băng và bạn có thể mở lại bất cứ lúc nào trong tương lai".
  3. Người học bấm xác nhận "Đồng ý lưu trữ".
  4. Hệ thống chuyển trạng thái lộ trình sang `ARCHIVED`, giải phóng các bài học khỏi Lịch học chính thức, cập nhật `last_study_activity_at = NOW()`. Không gọi `UC-PLAN-09` và không trừ hạn ngạch AI. Use case kết thúc.
- **7a. `UC-PLAN-09` trả về kết quả `SOFT_OVERFLOW` (A4)**:
  1. `UC-PLAN-09` cảnh báo một số ngày trong kế hoạch phục hồi có thời lượng vượt nhẹ định mức.
  2. Hệ thống hiển thị thông báo để Người học xác nhận cam kết. Người học bấm đồng ý và tiếp tục bước 8.
- **9a. Đã thực hiện Reset Ritual trong tuần hiện tại (FR-ADAPT-001)**:
  1. Tại bước 9, hệ thống phát hiện `last_reset_week == CURRENT_WEEK`.
  2. Hệ thống thông báo rõ: kế hoạch học tập mới đã được kích hoạt, nhưng số lượt dời lịch tuần hiện tại được bảo lưu nguyên trạng để đảm bảo tính kỷ luật SRL và sẽ tự động được làm mới vào 00:00 Thứ Hai tới.
  3. Hệ thống tiếp tục bước 10.

**Luồng ngoại lệ (Exception Flows)**:
- **5e. LLM Provider gặp sự cố kết nối**:
  1. Hệ thống hoàn trả hạn ngạch AI (RELEASE).
  2. Hệ thống chuyển sang chế độ tự động phục hồi tất định: áp dụng công thức tịnh tiến giản đơn toàn bộ các bài học quá hạn sang các ngày có khung giờ rảnh kế tiếp trong 7 ngày tới mà không cần qua AI.
  3. Tiếp tục bước 6 để kiểm định qua `UC-PLAN-09`.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-RESET-01 (Bộ ba chiến lược phục hồi chuẩn mực — B10)**: Nghi thức Tái thiết bắt buộc cung cấp đủ 3 chiến lược: (1) Khởi động nhẹ 7 ngày (giảm 50% tải), (2) Thu hẹp phạm vi Cột mốc (cắt giảm nội dung không cốt lõi), và (3) Lưu trữ chủ động kèm xác nhận rõ ràng.
- **BR-RESET-02 (Cơ chế giải phóng trạng thái ngủ đông và cấp mới ngân sách có kiểm soát — FR-ADAPT-001, D1, D4, B9)**: Trạng thái ngủ đông (`isDormant`) là thuộc tính dẫn xuất động. Khi người học hoàn tất Reset Ritual, hệ thống ghi nhận `last_study_activity_at = NOW()`, điều này ngay lập tức làm cho điều kiện ngủ đông trở thành sai mà không cần bất kỳ thao tác xóa cờ vật lý nào. Đồng thời, hệ thống chỉ cho phép cấp lại 3 lượt ngân sách dời lịch (`weekly_reschedule_used = 0`) tối đa 1 lần mỗi tuần bằng cách xác thực và cập nhật `last_reset_week = CURRENT_WEEK`, ngăn chặn triệt để hành vi lạm dụng reset tuần nhiều lần theo `FR-ADAPT-001`.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Lộ trình ngủ đông, lý do gián đoạn, chiến lược phục hồi chọn.
- **Đầu ra**: Lộ trình phục hồi hoạt động, `last_study_activity_at = NOW()`, `weekly_reschedule_used = 0`, `reset_ritual_count` tăng 1.

---

#### UC-ADAPT-08: Gửi email nhắc nhở bài quá hạn và lộ trình gián đoạn

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADAPT-08: Gửi email nhắc nhở bài quá hạn và lộ trình gián đoạn** |
| **Mức độ & Phân tầng** | Mục tiêu hệ thống nền (System-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`Learner — ACT-02`) *(Kích hoạt tự động theo sự kiện thời gian nội bộ — OMG UML TimeEvent)* |
| **Tác nhân phụ** | Dịch vụ Email (`ACT-07`) |
| **Trigger** | Thời điểm đồng hồ hệ thống chạm mốc 00:05 theo múi giờ cá nhân IANA của từng người dùng (`OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Thời điểm đồng hồ hệ thống chạm mốc 00:05 theo múi giờ cá nhân IANA của từng người dùng; tài khoản đã hoàn tất xác minh email (`BR-AUTH-02`). |
| **Hậu điều kiện thành công** | Các bài học quá hạn được phát hiện bằng logic động thời gian thực; email tổng hợp danh sách bài quá hạn và cảnh báo lộ trình ngủ đông ($\ge 7$ ngày không học) được chuyển phát đến hòm thư người học; thông báo trong ứng dụng được tạo. |
| **Bảo đảm tối thiểu** | Tuyệt đối không tự ý gán hay sửa đổi cờ boolean vật lý trong cơ sở dữ liệu (`D4`); nếu người dùng đã tắt nhận thông báo thì không gửi email. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-ADAPT-001`, `D4`, `B9` |

- **Luồng chính (Basic Flow)**:
  1. Sự kiện thời gian định kỳ (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ quét hàng ngày vào lúc 00:05 theo múi giờ địa phương của Người học.
  2. Hệ thống thực hiện truy vấn động các bài học có `scheduled_date < CURRENT_DATE(user_timezone)` và trạng thái chưa hoàn thành (`BR-CRON-01`).
  3. Hệ thống kiểm tra điều kiện lộ trình ngủ đông động: các lộ trình `ACTIVE` có mốc `last_study_activity_at < NOW() - 7 ngày`.
  4. Nếu có bài học quá hạn hoặc có lộ trình ngủ đông, hệ thống kiểm tra người dùng đã xác minh email và cho phép nhận thông báo học tập.
  5. Hệ thống đóng gói danh sách bài học quá hạn kèm đường dẫn truy cập nhanh đến chức năng Dời lịch AI (`UC-ADAPT-06`) và Khôi phục lộ trình bị gián đoạn lâu ngày (`UC-ADAPT-07`).
  6. Hệ thống chuyển tiếp nội dung thư sang Dịch vụ Email (`ACT-07`) để gửi cho Người học, đồng thời tạo một thông báo nội bộ trên bảng điều khiển. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **4a. Người dùng chưa xác minh email (Soft-verification — D6)**: Hệ thống bỏ qua bước gửi email ngoài, chỉ tạo thông báo nội bộ trên giao diện web kèm lời nhắc xác minh email.

- **Luồng ngoại lệ (Exception Flows)**:
  - **6e. Dịch vụ Email gặp sự cố gián đoạn**: Lỗi gửi thư được ghi nhận vào nhật ký kiểm toán hệ thống; thông báo nội bộ trong ứng dụng vẫn được tạo đầy đủ để người học không bị bỏ lỡ cảnh báo quá hạn.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-CRON-01 (Quét động không ghi cờ vật lý — D4, B9)**: Tiến trình quét lúc 00:05 hoàn toàn là phép truy vấn dữ liệu động để gửi thông báo; tuyệt đối không thực hiện ghi các cờ `isOverdue = true` hay `isDormant = true` xuống cơ sở dữ liệu nhằm giữ tính nhất quán theo thời gian thực.

---

#### UC-ADAPT-09: Tổng hợp hồ sơ thói quen học tập

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADAPT-09: Tổng hợp hồ sơ thói quen học tập** |
| **Mức độ & Phân tầng** | Mục tiêu hệ thống nền (System-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`Learner — ACT-02`) *(Kích hoạt tự động theo sự kiện thời gian nội bộ — OMG UML TimeEvent)* |
| **Tác nhân phụ** | Không có |
| **Trigger** | Tác vụ nền chạy định kỳ hàng tuần vào lúc 01:00 sáng Thứ Hai (giờ UTC) (`OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Tác vụ nền chạy định kỳ hàng tuần vào lúc 01:00 sáng Thứ Hai (giờ UTC). |
| **Hậu điều kiện thành công** | Hồ sơ thói quen học tập (`LearnerProfile`) của người dùng được cập nhật các chỉ số phân tích: khung giờ học tập trung nhất trong tuần, thời lượng phiên học tối ưu thực tế và mức độ tuân thủ nhịp năng lượng. |
| **Bảo đảm tối thiểu** | Dữ liệu tổng hợp được tính toán khách quan từ các phiên học hợp lệ đã hoàn thành; không ảnh hưởng đến quyền riêng tư. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-PROFILE-001` |

- **Luồng chính (Basic Flow)**:
  1. Sự kiện thời gian định kỳ (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ phân tích hồ sơ thói quen vào 01:00 UTC Thứ Hai hàng tuần.
  2. Hệ thống truy vấn toàn bộ dữ liệu các phiên học tập trung (`COMPLETED` và `PARTIAL_COMPLETED`) trong cửa sổ 30 ngày gần nhất của từng người học.
  3. Hệ thống tính toán các chỉ số thống kê thói quen:
     - Khung giờ có số phiên học tập trung cao nhất và ít bị gián đoạn nhất.
     - Thời lượng trung bình của một phiên học hiệu quả (thường dao động 25–50 phút).
     - Tỷ lệ hoàn thành bài học theo từng mức năng lượng nhận thức (`HIGH`, `MEDIUM`, `LOW`).
  4. Hệ thống cập nhật các chỉ số này vào bản ghi Hồ sơ thói quen học tập của Người học (`BR-CRON-02`).
  5. Các chỉ số này được cung cấp làm ngữ cảnh đầu vào cho các ca sử dụng AI lập lịch (`UC-PLAN-03`) và dời lịch (`UC-ADAPT-06`) trong tương lai. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **2a. Người học mới chưa có đủ 5 phiên học trong 30 ngày**: Hệ thống giữ các giá trị tham chiếu mặc định (khung giờ 19:00–21:00, thời lượng 45 phút) và ghi nhận chưa đủ mẫu thống kê.

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Lỗi truy vấn cơ sở dữ liệu khi tổng hợp dữ liệu lịch sử**: Hệ thống ghi nhận cảnh báo lỗi và tự động lên lịch chạy lại tác vụ sau 1 giờ; không ảnh hưởng đến dữ liệu hồ sơ hiện hành.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-CRON-02 (Cửa sổ dữ liệu hồ sơ thói quen)**: Dữ liệu hồ sơ thói quen chỉ được tính toán trượt trong phạm vi 30 ngày gần nhất để đảm bảo phản ánh đúng nhịp sinh học và phong độ học tập hiện tại của người học.

---

#### UC-ADAPT-10: Đặt lại ngân sách dời lịch hàng tuần

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADAPT-10: Đặt lại ngân sách dời lịch hàng tuần** |
| **Mức độ & Phân tầng** | Mục tiêu hệ thống nền (System-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Người học (`Learner — ACT-02`) *(Kích hoạt tự động theo sự kiện thời gian nội bộ — OMG UML TimeEvent)* |
| **Tác nhân phụ** | Không có |
| **Trigger** | Thời điểm đồng hồ hệ thống chạm mốc 00:00 ngày Thứ Hai theo múi giờ chuẩn IANA của từng người dùng (`OMG UML 2.5.1 TimeEvent`). |
| **Tiền điều kiện** | Thời điểm đồng hồ hệ thống chạm mốc 00:00 ngày Thứ Hai theo múi giờ chuẩn IANA của từng người dùng. |
| **Hậu điều kiện thành công** | Ngân sách dời lịch tuần được tự động đặt lại về 0 (`weekly_reschedule_used = 0`), cấp đủ định mức 3 lượt dời lịch AI mới cho tuần học mới; ghi nhận tuần làm mới `last_reset_week = CURRENT_WEEK`. |
| **Bảo đảm tối thiểu** | Không bao giờ cộng dồn số lượt chưa dùng sang tuần mới; không vượt quá trần 3 lượt. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-ADAPT-001`, `D1`, `B6` |

- **Luồng chính (Basic Flow)**:
  1. Sự kiện thời gian định kỳ (`OMG UML 2.5.1 TimeEvent`) kích hoạt tác vụ kiểm tra làm mới ngân sách dời lịch theo múi giờ của người dùng vào đúng 00:00 ngày Thứ Hai hàng tuần.
  2. Hệ thống tìm kiếm các tài khoản người dùng có múi giờ đang bước sang 00:00 Thứ Hai.
  3. Hệ thống kiểm tra xem tài khoản này trong tuần mới đã được làm mới sớm qua Nghi thức Chốt tuần (`UC-ADAPT-03`) hay chưa (`BR-CRON-03`, `D1`):
     - Nếu `last_reset_week != CURRENT_WEEK`: Hệ thống cập nhật `weekly_reschedule_used = 0` và gán `last_reset_week = CURRENT_WEEK`.
     - Nếu `last_reset_week == CURRENT_WEEK` (người dùng đã hoàn tất Chốt tuần vào Chủ Nhật và đã nhận ngân sách mới): Hệ thống giữ nguyên trạng thái, không đặt lại lặp lại.
  4. Hệ thống ghi nhật ký hoàn tất tác vụ định kỳ. Use case kết thúc thành công.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Người dùng đã được làm mới ngân sách sớm qua Đánh giá học tập cuối tuần (UC-ADAPT-03)**: Phát hiện `last_reset_week == CURRENT_WEEK`, hệ thống ghi nhận tính lũy đẳng, bỏ qua tài khoản này và không tăng thêm lượt để đảm bảo đúng trần 3 lượt/tuần.

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Lỗi kết nối cơ sở dữ liệu theo múi giờ**: Hệ thống tự động kích hoạt cơ chế thử lại sau 5 phút để bảo đảm tất cả tài khoản người học đều được làm mới ngân sách khi bắt đầu tuần mới.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-CRON-03 (Cơ chế đồng bộ làm mới ngân sách tuần — D1, B6)**: Tác vụ theo sự kiện thời gian lúc 00:00 Thứ Hai (`OMG UML 2.5.1 TimeEvent`) là kênh làm mới ngân sách mặc định bắt buộc. Nếu người học đã làm mới sớm qua Nghi thức Chốt tuần (`UC-ADAPT-03`), tác vụ này ghi nhận tính lũy đẳng và không cấp thêm lượt (tổng ngân sách khả dụng đầu tuần luôn là 3 lượt, tuyệt đối không cộng dồn thành 6 lượt).


### PHÂN HỆ 5: QUẢN TRỊ HỆ THỐNG & VẬN HÀNH

Phân hệ bao gồm 7 Use Cases chịu trách nhiệm cung cấp các công cụ điều hành nền tảng cho Quản trị viên: quản lý tài khoản người dùng, điều chỉnh gói cước và hạn ngạch, đối soát tài chính giao dịch, giám sát sức khỏe vận hành, tra cứu nhật ký kiểm toán và chuẩn hóa kho khái niệm tri thức Ground Truth.

```
Sơ đồ 5: Quản trị Hệ thống & Vận hành (UC-ADM-01, UC-ADM-02, UC-ADM-03, UC-ADM-04, UC-ADM-05, UC-ADM-06, UC-ADM-07)
```

---

#### UC-ADM-01: Khóa hoặc mở khóa tài khoản người dùng

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADM-01: Khóa hoặc mở khóa tài khoản người dùng** |
| **Mức độ & Phân tầng** | Mục tiêu quản trị (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Quản trị viên hệ thống (`Administrator` — `ACT-03`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Quản trị viên đã đăng nhập với quyền hạn phù hợp (RBAC: `ADMIN` hoặc `SUPER_ADMIN`). |
| **Hậu điều kiện thành công** | Trạng thái tài khoản người dùng được chuyển đổi giữa `ACTIVE` và `LOCKED`; toàn bộ phiên đăng nhập hiện tại của tài khoản bị thu hồi ngay lập tức nếu bị khóa; lý do can thiệp được ghi vào nhật ký kiểm toán (`UC-ADM-06`). |
| **Bảo đảm tối thiểu** | Không cho phép tự khóa tài khoản của chính mình hoặc tài khoản Quản trị viên cấp cao hơn. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-ADM-001`, `FR-ADM-002` |

- **Luồng chính (Basic Flow)**:
  1. Quản trị viên tra cứu tài khoản người dùng cần xử lý qua email hoặc họ tên trên Cổng quản trị.
  2. Hệ thống hiển thị thông tin chi tiết tài khoản: trạng thái hiện tại, gói cước, số lộ trình và lịch sử hoạt động.
  3. Quản trị viên chọn thao tác "Khóa tài khoản" (hoặc "Mở khóa tài khoản").
  4. Hệ thống yêu cầu Quản trị viên nhập Lý do khóa/mở khóa bắt buộc.
  5. Quản trị viên nhập lý do và bấm xác nhận.
  6. Hệ thống kiểm tra quyền hạn (`BR-ADM-01`), cập nhật trạng thái tài khoản sang `LOCKED`, vô hiệu hóa toàn bộ mã phiên làm việc của người dùng này trên mọi thiết bị và ghi nhật ký kiểm toán. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Thao tác Mở khóa tài khoản**: Quản trị viên chọn mở khóa cho một tài khoản đang bị `LOCKED`; hệ thống cập nhật trạng thái về `ACTIVE`, đặt lại số lần đăng nhập sai về 0 và ghi nhật ký kiểm toán.

- **Luồng ngoại lệ (Exception Flows)**:
  - **5e. Quản trị viên cố gắng khóa chính mình hoặc Super Admin cấp cao hơn**: Hệ thống từ chối thực hiện theo nguyên tắc an toàn, hiển thị thông báo lỗi bảo mật và ghi nhật ký cảnh báo vi phạm phân quyền RBAC.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-ADM-01 (Thu hồi phiên tức thì khi khóa tài khoản)**: Việc chuyển trạng thái tài khoản sang `LOCKED` có hiệu lực ngay lập tức; toàn bộ các yêu cầu gọi API từ thiết bị của người dùng này đều bị từ chối với mã lỗi 403 Forbidden.

---

#### UC-ADM-02: Đổi gói dịch vụ của người dùng

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADM-02: Đổi gói dịch vụ của người dùng** |
| **Mức độ & Phân tầng** | Mục tiêu quản trị (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Quản trị viên hệ thống (`Administrator` — `ACT-03`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Quản trị viên đã đăng nhập và có quyền quản lý tài khoản người dùng. |
| **Hậu điều kiện thành công** | Gói dịch vụ của người dùng được chuyển đổi (`FREE` sang `PREMIUM` hoặc ngược lại); thời hạn gói được cập nhật; áp dụng tự động các quy tắc giới hạn lộ trình hoạt động; ghi nhật ký kiểm toán. |
| **Bảo đảm tối thiểu** | Nếu hạ cấp thủ công về FREE, dữ liệu lộ trình vượt trần phải được tạm dừng an toàn (`PAUSED`), không xóa bài học. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-ADM-002`, `FR-QUOTA-002` |

- **Luồng chính (Basic Flow)**:
  1. Quản trị viên tra cứu tài khoản người dùng cần can thiệp trên Cổng quản trị.
  2. Quản trị viên chọn chức năng "Điều chỉnh gói dịch vụ".
  3. Quản trị viên chọn gói cước mới (`FREE` hoặc `PREMIUM`), nhập số ngày gia hạn thêm (nếu nâng lên Premium) và nhập lý do can thiệp hỗ trợ.
  4. Quản trị viên bấm Lưu thay đổi.
  5. Hệ thống cập nhật gói cước của người dùng:
     - Nếu nâng lên `PREMIUM`: Thiết lập thời hạn `premium_expires_at` mới, nâng hạn ngạch AI lên 300 lượt và trần lộ trình lên 15.
     - Nếu hạ cấp về `FREE`: Áp dụng thuật toán EDF (`BR-DOWN-01`) để giữ lại tối đa 3 lộ trình `ACTIVE`, chuyển các lộ trình vượt trần sang `PAUSED`.
  6. Hệ thống ghi nhật ký kiểm toán chi tiết người thực hiện, thời gian, gói cũ, gói mới và lý do. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **5a. Người dùng có $\le 3$ lộ trình đang hoạt động khi hạ cấp**: Hệ thống giữ nguyên trạng thái `ACTIVE` cho cả 3 lộ trình mà không cần tạm dừng lộ trình nào.

- **Luồng ngoại lệ (Exception Flows)**:
  - **4e. Quản trị viên nhập số ngày gia hạn không hợp lệ**: Nhập số ngày âm hoặc không phải số nguyên. Hệ thống từ chối lưu và yêu cầu nhập số ngày hợp lệ $\ge 1$.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-ADM-02 (Ràng buộc trần lộ trình khi can thiệp gói)**: Mọi hành động hạ cấp gói dịch vụ do Quản trị viên thực hiện bắt buộc phải tuân thủ nghiêm ngặt quy tắc trần 3 lộ trình hoạt động của gói `FREE`, tự động áp dụng quy tắc EDF để bảo toàn dữ liệu.

---

#### UC-ADM-03: Điều chỉnh hạn ngạch AI người dùng

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADM-03: Điều chỉnh hạn ngạch AI người dùng** |
| **Mức độ & Phân tầng** | Mục tiêu quản trị (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Quản trị viên hệ thống (`Administrator` — `ACT-03`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Quản trị viên đã đăng nhập và có quyền điều chỉnh hạn ngạch tài nguyên. |
| **Hậu điều kiện thành công** | Số lượt gọi AI tháng của người dùng được tăng thêm (hoặc đặt lại) kèm lý do giải trình; hạn ngạch mới có hiệu lực ngay lập tức; ghi nhật ký kiểm toán. |
| **Bảo đảm tối thiểu** | Không cho phép điều chỉnh vượt quá trần an toàn kỹ thuật (tối đa 1000 lượt/tháng). |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-ADM-002`, `FR-QUOTA-001` |

- **Luồng chính (Basic Flow)**:
  1. Quản trị viên xem chi tiết tài khoản người dùng gặp sự cố hoặc cần hỗ trợ đền bù hạn ngạch (ví dụ do lỗi hệ thống làm mất lượt AI).
  2. Quản trị viên chọn chức năng "Điều chỉnh hạn ngạch AI".
  3. Quản trị viên nhập số lượt gọi AI cần cộng thêm (hoặc đặt lại số lượt đã dùng về 0) và nhập lý do bắt buộc.
  4. Hệ thống kiểm tra số lượt điều chỉnh không vượt quá trần kỹ thuật 1000 lượt (`BR-ADM-03`).
  5. Hệ thống cập nhật lại số dư hạn ngạch khả dụng của tài khoản.
  6. Hệ thống ghi nhận bản ghi kiểm toán tài nguyên AI. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Đặt lại số lượt đã dùng về 0**: Quản trị viên chọn khôi phục toàn bộ hạn ngạch tháng mà không cộng dồn thêm; hệ thống đặt `ai_requests_used = 0`.

- **Luồng ngoại lệ (Exception Flows)**:
  - **4e. Số lượt điều chỉnh vượt quá trần kỹ thuật (> 1000 lượt/tháng)**: Hệ thống chặn thao tác theo `BR-ADM-03`, hiển thị cảnh báo đỏ và yêu cầu nhập số lượng trong khoảng an toàn cho phép.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-ADM-03 (Trần an toàn điều chỉnh hạn ngạch)**: Mọi thao tác điều chỉnh hạn ngạch AI thủ công không được phép nâng tổng số dư khả dụng của một tài khoản vượt quá 1000 lượt/tháng nhằm ngăn chặn lạm dụng chi phí dịch vụ AI đám mây.

---

#### UC-ADM-04: Đối soát đơn thanh toán

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ADM-04** |
| **Tên Use Case** | **Đối soát đơn thanh toán** |
| **Mô tả ngắn** | Quản trị viên tra cứu, rà soát và đối chiếu các đơn giao dịch thanh toán bị treo hoặc phát sinh khiếu nại với Cổng thanh toán; xử lý các đơn hàng bị hết hạn (`EXPIRED`) nhưng đã nhận được tiền thực tế từ ngân hàng sang trạng thái `PAID` có kiểm soát, nhập mã tham chiếu giao dịch ngân hàng và lý do xác minh để kích hoạt gói Premium cho người học. |
| **Tác nhân chính** | Quản trị viên hệ thống (`Administrator` — `ACT-03`) |
| **Tác nhân phụ** | Cổng thanh toán (`Payment Gateway` — `ACT-05`) |
| **Mức độ** | Mục tiêu quản trị (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Quản trị viên mở trang Đối soát tài chính trên Cổng quản trị hoặc nhận được yêu cầu tra soát khiếu nại thanh toán từ người học. |
| **Tiền điều kiện** | Quản trị viên đã đăng nhập và sở hữu quyền hạn quản trị tài chính (`FINANCE_ADMIN` hoặc `SUPER_ADMIN`). |
| **Hậu điều kiện – thành công** | Đơn thanh toán được cập nhật trạng thái chính xác (`PAID`, `CANCELLED` hoặc `FAILED`); nếu chuyển sang `PAID`, gói Premium của người học được kích hoạt/gia hạn thêm 30 ngày; mã tham chiếu ngân hàng, số tiền và lý do đối soát được lưu vào nhật ký kiểm toán tài chính bắt buộc (`BR-RECON-01`). |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Không làm sai lệch trạng thái đơn hàng nếu không có bằng chứng chứng từ hợp lệ; bảo lưu nguyên vẹn doanh thu. |
| **Include / Extend** | Không có *(Quy trình duyệt 2 bước áp dụng trong luồng thay thế khi số tiền đặc biệt)* |
| **Tần suất / Độ ưu tiên** | Hàng tuần hoặc theo khiếu nại / Cực kỳ quan trọng (P0 — Must have) |
| **Tham chiếu SRS** | `FR-ADM-002`, `FR-QUOTA-002`, `D3`, `D7`, `B7`, `B8` |

**Luồng chính (Basic Flow)**:
1. Quản trị viên truy cập màn hình Đối soát giao dịch thanh toán trên Cổng quản trị.
2. Hệ thống hiển thị bộ lọc tìm kiếm đơn hàng: theo mã đơn, email người dùng, trạng thái đơn (`PENDING`, `EXPIRED`, `PAID`, `FAILED`) và khoảng thời gian tạo đơn.
3. Quản trị viên tìm thấy một đơn thanh toán đang ở trạng thái `EXPIRED` hoặc `PENDING` bị lỗi nghẽn thông báo (người học đã chuyển khoản thành công nhưng Cổng thanh toán chưa gửi hoặc bị trượt Webhook).
4. Quản trị viên chọn chức năng "Đối chiếu & Khớp lệnh thủ công".
5. Hệ thống gửi yêu cầu tra cứu trạng thái giao dịch sang Cổng thanh toán (`Payment Gateway API`) theo mã đơn hàng để lấy thông tin đối soát tự động.
6. Cổng thanh toán trả về thông tin xác nhận giao dịch ngân hàng đã nhận đủ số tiền 99.000 VNĐ.
7. Quản trị viên kiểm tra chứng từ ủy nhiệm chi hoặc đối chiếu với sao kê tài khoản ngân hàng.
8. Quản trị viên chọn thao tác "Duyệt đơn chuyển thành PAID" (`BR-RECON-02`, `D3`).
9. Hệ thống hiển thị biểu mẫu bắt buộc: yêu cầu Quản trị viên nhập Mã giao dịch ngân hàng (Bank Reference Code), kiểm tra số tiền khớp đúng 99.000 VNĐ và nhập Lý do đối soát giải trình (`BR-RECON-01`, `D7`).
10. Quản trị viên điền đầy đủ thông tin xác thực và bấm xác nhận duyệt.
11. Hệ thống thực hiện cập nhật nguyên tử:
    - Chuyển trạng thái đơn thanh toán từ `EXPIRED` (hoặc `PENDING`) sang `PAID`.
    - Ghi nhận cờ `manual_reconciled = true`, lưu mã giao dịch ngân hàng và tên Quản trị viên thực hiện.
    - Tự động nâng cấp hoặc gia hạn gói `PREMIUM` cho tài khoản Người học thêm 30 ngày (`BR-PAY-03`).
    - Nâng trần hạn ngạch AI và số lộ trình hoạt động cho tài khoản Người học.
12. Hệ thống ghi nhật ký kiểm toán tài chính không thể chỉnh sửa vào kho lưu trữ kiểm toán (`UC-ADM-06`).
13. Hệ thống hiển thị thông báo đối soát thành công và tự động gửi thông báo trong ứng dụng cho Người học xác nhận gói cước đã được kích hoạt. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **5a. Cổng thanh toán không tìm thấy giao dịch hoặc xác nhận chưa nhận được tiền**:
  1. Cổng thanh toán báo giao dịch không tồn tại hoặc người học chưa thực hiện chuyển khoản.
  2. Quản trị viên từ chối khiếu nại, giữ nguyên trạng thái đơn hàng là `EXPIRED` (hoặc chuyển sang `FAILED`).
  3. Quản trị viên nhập nội dung phản hồi hướng dẫn người học kiểm tra lại với ngân hàng phát hành. Use case kết thúc.
- **8a. Luồng phụ — Duyệt 2 bước cho các đơn hàng điều chỉnh đặc biệt (UC-38 phụ thuộc)**:
  1. Nếu thao tác đối soát có tính chất nhạy cảm hoặc hoàn tiền ngoại lệ, hệ thống yêu cầu chữ ký phê duyệt thứ hai từ Giám đốc vận hành (Super Admin).
  2. Đơn hàng chuyển sang trạng thái chờ phê duyệt cấp cao (`PENDING_APPROVAL`). Khi Super Admin đăng nhập và duyệt, đơn hàng mới chuyển sang `PAID`.

**Luồng ngoại lệ (Exception Flows)**:
- **9e. Quản trị viên không nhập mã tham chiếu ngân hàng hoặc lý do**:
  1. Hệ thống chặn thao tác duyệt, hiển thị thông báo đỏ: "Bắt buộc phải nhập Mã giao dịch ngân hàng và Lý do đối soát giải trình để phục vụ kiểm toán tài chính".
  2. Không thay đổi dữ liệu đơn hàng.
  3. Quản trị viên bổ sung thông tin hoặc hủy thao tác.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-RECON-01 (Yêu cầu bằng chứng đối soát bắt buộc — D7, B8)**: Mọi thao tác can thiệp chuyển trạng thái đơn hàng thủ công sang `PAID` bắt buộc phải ghi nhận: (1) Mã giao dịch tham chiếu của ngân hàng, (2) Số tiền thực nhận khớp đúng 99.000 VNĐ, (3) Tên định danh của Quản trị viên thực hiện, và (4) Lý do giải trình cụ thể.
- **BR-RECON-02 (Quy định đối soát đơn EXPIRED sang PAID — D3, B7)**: Cho phép Quản trị viên đối soát chuyển đơn từ `EXPIRED` sang `PAID` khi có căn cứ chứng minh người học đã chuyển tiền thực tế trong tài khoản ngân hàng của hệ thống. Hệ thống tự động kích hoạt gói Premium ngay khi duyệt thành công.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Mã đơn hàng, mã giao dịch ngân hàng, lý do đối soát của Quản trị viên.
- **Đầu ra**: Đơn thanh toán chuyển sang `PAID`, tài khoản người học nâng cấp gói `PREMIUM`, nhật ký kiểm toán tài chính.

---

#### UC-ADM-05: Giám sát vận hành hệ thống và dịch vụ AI

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADM-05: Giám sát vận hành hệ thống và dịch vụ AI** |
| **Mức độ & Phân tầng** | Mục tiêu quản trị (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Quản trị viên hệ thống (`Administrator` — `ACT-03`) |
| **Tác nhân phụ** | Không có *(Gỡ bỏ tác nhân phụ LLM Provider theo lỗi mô hình hóa A7)* |
| **Tiền điều kiện** | Quản trị viên đã đăng nhập và có quyền giám sát kỹ thuật (`SYSTEM_MONITOR` hoặc `ADMIN`). |
| **Hậu điều kiện thành công** | Bảng điều khiển giám sát thời gian thực hiển thị đầy đủ các chỉ số sức khỏe hệ thống: độ trễ phản hồi API, tỷ lệ lỗi HTTP 5xx, tình trạng hàng đợi tác vụ nền và mức tiêu thụ tài nguyên/chi phí của dịch vụ AI. |
| **Bảo đảm tối thiểu** | Việc đọc các số liệu giám sát không làm suy giảm hiệu năng của các tiến trình xử lý người dùng. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-ADM-003`, `A7` |

- **Luồng chính (Basic Flow)**:
  1. Quản trị viên truy cập màn hình Bảng điều khiển Giám sát vận hành (Observability Dashboard).
  2. Hệ thống thu thập và tổng hợp các chỉ số hoạt động trong 1 giờ, 24 giờ và 7 ngày qua:
     - Tỷ lệ lỗi toàn hệ thống và phân bố lỗi theo từng dịch vụ.
     - Độ trễ phản hồi trung bình ($p50, p95, p99$) của các API người dùng.
     - Tình trạng hàng đợi tác vụ nền: số lượng tác vụ đang xử lý, số tác vụ chờ và tác vụ thất bại.
     - Thống kê dịch vụ AI: tổng số lượt gọi LLM, số token tiêu thụ, chi phí ước tính và tỷ lệ các cuộc gọi chạm ngưỡng thời gian chờ 55 giây.
  3. Hệ thống hiển thị các biểu đồ trực quan kèm trạng thái cảnh báo theo màu sắc (Xanh: Bình thường, Vàng: Cảnh báo, Đỏ: Nguy hiểm).
  4. Quản trị viên có thể chọn xem chi tiết các nhật ký lỗi gần nhất để chẩn đoán sự cố. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **3a. Một chỉ số vượt ngưỡng nguy hiểm (ví dụ tỷ lệ lỗi AI > 10%)**: Hệ thống hiển thị thông báo nhấp nháy trên đầu trang và kích hoạt kênh cảnh báo khẩn cấp đến đội ngũ kỹ thuật.

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Một dịch vụ giám sát thành phần tạm thời mất kết nối**: Hệ thống hiển thị cảnh báo trạng thái ngoại tuyến cho riêng dịch vụ đó, các số liệu giám sát khác vẫn hiển thị bình thường.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-ADM-04 (Ngưỡng cảnh báo hiệu năng hệ thống)**: Tỷ lệ lỗi API $> 5\%$ hoặc độ trễ phản hồi trung bình của dịch vụ AI $> 15$ giây được phân loại là trạng thái cảnh báo nghiêm trọng đòi hỏi can thiệp kỹ thuật ngay lập tức.

---

#### UC-ADM-06: Xem nhật ký kiểm toán quản trị

| Thuộc tính | Nội dung |
|---|---|
| **ID & Tên** | **UC-ADM-06: Xem nhật ký kiểm toán quản trị** |
| **Mức độ & Phân tầng** | Mục tiêu quản trị (User-Goal Level) — **Tầng 2 (Rút gọn)** |
| **Tác nhân chính** | Quản trị viên hệ thống (`Administrator` — `ACT-03`) |
| **Tác nhân phụ** | Không có |
| **Tiền điều kiện** | Quản trị viên đã đăng nhập với vai trò kiểm toán viên hoặc quản trị viên cấp cao. |
| **Hậu điều kiện thành công** | Danh sách các bản ghi nhật ký kiểm toán nhạy cảm (khóa tài khoản, can thiệp gói cước, điều chỉnh hạn ngạch, đối soát tài chính) được hiển thị đầy đủ, minh bạch và không thể bị sửa đổi. |
| **Bảo đảm tối thiểu** | Kho lưu trữ nhật ký kiểm toán là bất biến (Append-only); không ai (kể cả Super Admin) có quyền chỉnh sửa hay xóa các bản ghi nhật ký kiểm toán. |
| **Quan hệ UML** | Association |
| **Tham chiếu SRS** | `FR-ADM-002`, `FR-ADM-003`, `ISO 29148` |

- **Luồng chính (Basic Flow)**:
  1. Quản trị viên mở trang Nhật ký kiểm toán hệ thống (Audit Trail).
  2. Hệ thống hiển thị danh sách các bản ghi kiểm toán gần nhất theo thứ tự thời gian giảm dần.
  3. Mỗi bản ghi hiển thị đầy đủ: Thời điểm (UTC), Tên và email Quản trị viên thực hiện, Địa chỉ IP nguồn, Loại hành động can thiệp (`USER_LOCK`, `TIER_OVERRIDE`, `QUOTA_ADJUST`, `PAYMENT_RECONCILE`, `CONCEPT_VERIFY`), Tài khoản mục tiêu chịu tác động, Giá trị dữ liệu trước/sau khi đổi và Lý do giải trình bắt buộc.
  4. Quản trị viên có thể lọc theo loại hành động, theo tài khoản người thực hiện hoặc theo mốc thời gian để phục vụ công tác thanh tra.
  5. Quản trị viên có thể xuất báo cáo kiểm toán ra tệp tin bảo mật dạng CSV hoặc PDF có chữ ký số. Use case kết thúc.

- **Luồng thay thế (Alternative Flows)**:
  - **4a. Lọc nhật ký theo đối tượng thao tác hoặc khoảng thời gian**: Hệ thống trả về danh sách sự kiện kiểm toán khớp với bộ lọc trong thời gian $\le 500$ms.

- **Luồng ngoại lệ (Exception Flows)**:
  - **2e. Không tìm thấy bản ghi kiểm toán phù hợp**: Hệ thống hiển thị bảng kết quả trống với thông báo không có bản ghi nào trong khoảng thời gian đã chọn.

- **Quy tắc nghiệp vụ trọng yếu**:
  - **BR-ADM-05 (Tính bất biến của nhật ký kiểm toán)**: Nhật ký kiểm toán quản trị là kho dữ liệu chỉ ghi (Append-only), nghiêm cấm mọi thao tác sửa đổi (`UPDATE`) hoặc xóa (`DELETE`), và phải được lưu trữ tối thiểu 365 ngày phục vụ đối soát pháp lý và an toàn thông tin.

---

#### UC-ADM-07: Quản lý kho khái niệm tri thức

| Thuộc tính | Nội dung |
|---|---|
| **ID** | **UC-ADM-07** |
| **Tên Use Case** | **Quản lý kho khái niệm tri thức** |
| **Mô tả ngắn** | Quản trị viên (hoặc Quản lý tri thức — Knowledge Manager) rà soát danh sách các khái niệm học tập do AI tự động khởi tạo ở trạng thái chưa kiểm duyệt (`UNVERIFIED` từ `UC-PLAN-01`); thực hiện chỉnh sửa định nghĩa, gộp các khái niệm trùng lặp, thiết lập đồ thị tiên quyết chuẩn mực và phê duyệt chuyển đổi trạng thái khái niệm sang `VERIFIED` để làm căn cứ Ground Truth chuẩn mực phục vụ bài kiểm chứng năng lực Prove Mode (`UC-ADAPT-02`). |
| **Tác nhân chính** | Quản trị viên hệ thống / Quản lý tri thức (`Administrator` — `ACT-03`) |
| **Tác nhân phụ** | Không có |
| **Mức độ** | Mục tiêu quản trị (User-Goal Level) — **Tầng 1 (Đầy đủ chi tiết)** |
| **Trigger** | Quản trị viên mở trang Quản lý kho tri thức trên Cổng quản trị để thẩm định các khái niệm mới phát sinh. |
| **Tiền điều kiện** | Quản trị viên đã đăng nhập và sở hữu quyền quản lý nội dung tri thức (`KNOWLEDGE_ADMIN` hoặc `SUPER_ADMIN`). |
| **Hậu điều kiện – thành công** | Khái niệm tri thức được chuẩn hóa nội dung, chuyển trạng thái sang `VERIFIED` (hoặc bị loại bỏ sang `REJECTED`/`DEPRECATED`); các mối quan hệ tiên quyết giữa các khái niệm được cập nhật vào Đồ thị tri thức chuẩn mực (Knowledge Graph); nâng cấp chất lượng Ground Truth cho toàn bộ các bài kiểm chứng năng lực Prove Mode trong tương lai. |
| **Bảo đảm tối thiểu (Minimal Guarantee)** | Không làm hỏng các lộ trình đang học dở gắn với khái niệm; bảo lưu dữ liệu. |
| **Include / Extend** | Không có |
| **Tần suất / Độ ưu tiên** | Định kỳ hàng tuần / Quan trọng (P1 — Should have) |
| **Tham chiếu SRS** | `FR-REPORT-003`, `FR-PLAN-001`, `D2`, `B4` |

**Luồng chính (Basic Flow)**:
1. Quản trị viên truy cập vào giao diện Quản lý kho khái niệm tri thức trên Cổng quản trị.
2. Hệ thống hiển thị danh sách các khái niệm học tập đang ở trạng thái chưa kiểm duyệt (`status = UNVERIFIED`) được gom nhóm theo lĩnh vực chủ đề, kèm số lượng lộ trình đang tham chiếu đến khái niệm đó.
3. Quản trị viên chọn một khái niệm cụ thể để xem xét thông tin chi tiết: tên khái niệm, định nghĩa chuẩn, các thuật ngữ đồng nghĩa, mức độ phức tạp nhận thức và danh sách các khái niệm điều kiện tiên quyết do AI đề xuất.
4. Quản trị viên thực hiện thẩm định và chuẩn hóa nội dung:
   - Tinh chỉnh câu chữ trong định nghĩa khái niệm cho chuẩn xác về mặt học thuật.
   - Bổ sung hoặc gỡ bỏ các liên kết tiên quyết với các khái niệm khác nhằm đảm bảo tính sư phạm.
   - Nếu phát hiện khái niệm này bị trùng lặp với một khái niệm đã có, Quản trị viên chọn tính năng Gộp khái niệm (Merge Concepts) vào khái niệm chuẩn mực (`BR-KNOW-03`).
5. Quản trị viên bấm nút **"Phê duyệt khái niệm (Verify Concept)"**.
6. Hệ thống kiểm tra đồ thị quan hệ giữa các khái niệm: đảm bảo không tạo thành chu trình phụ thuộc khép kín trong kho tri thức.
7. Hệ thống cập nhật trạng thái khái niệm từ `UNVERIFIED` sang `VERIFIED` (`BR-KNOW-02`, `D2`).
8. Hệ thống lưu lại định danh của Quản trị viên phê duyệt và mốc thời gian thẩm định vào bản ghi khái niệm.
9. Từ thời điểm này, toàn bộ các Cột mốc học tập tham chiếu đến khái niệm này sẽ sử dụng định nghĩa và bộ câu hỏi chuẩn mực của khái niệm làm Ground Truth chính thống cho ca sử dụng Kiểm chứng năng lực Prove Mode (`UC-ADAPT-02`).
10. Hệ thống hiển thị thông báo đã thẩm định thành công và ghi nhật ký kiểm toán quản trị tri thức. Use case kết thúc thành công.

**Luồng thay thế (Alternative Flows)**:
- **4a. Quản trị viên phát hiện khái niệm do AI sinh ra bị sai lệch hoặc rác**:
  1. Quản trị viên nhận thấy khái niệm vô nghĩa, sai kiến thức cơ bản hoặc là nội dung không phù hợp.
  2. Quản trị viên chọn thao tác "Từ chối khái niệm (Reject)".
  3. Hệ thống chuyển trạng thái khái niệm sang `REJECTED`, gỡ bỏ liên kết với các lộ trình trong tương lai (các bài học hiện tại gắn với nó sẽ chuyển sang cơ chế đối chiếu bằng chứng thực tế tại `UC-ADAPT-02`). Use case kết thúc.
- **4b. Gộp khái niệm trùng lặp (Merge Concepts — B4)**:
  1. Ví dụ AI sinh khái niệm "Python Basic Syntax" trong khi hệ thống đã có khái niệm `VERIFIED` là "Python Syntax Fundamentals".
  2. Quản trị viên chọn chức năng Gộp và chỉ định khái niệm đích.
  3. Hệ thống chuyển toàn bộ các tham chiếu của cột mốc và bài học từ khái niệm cũ sang khái niệm đích, sau đó đánh dấu khái niệm cũ là `DEPRECATED`. Use case kết thúc.

**Luồng ngoại lệ (Exception Flows)**:
- **6e. Quan hệ tiên quyết mới tạo thành chu trình phụ thuộc giữa các khái niệm**:
  1. Hệ thống phát hiện việc thêm quan hệ tiên quyết dẫn đến quan hệ vòng tròn giữa các khái niệm trong kho tri thức.
  2. Hệ thống từ chối lưu, hiển thị đường dẫn chu trình cụ thể và yêu cầu Quản trị viên điều chỉnh lại quan hệ.
  3. Quản trị viên sửa lại và tiếp tục từ bước 5.

**Quy tắc nghiệp vụ (Business Rules)**:
- **BR-KNOW-02 (Quyền hạn thẩm định Ground Truth — D2, B4)**: Duy nhất Quản trị viên hoặc Quản lý tri thức (`Administrator` / `Knowledge Manager`) mới có thẩm quyền chuyển đổi trạng thái của khái niệm từ `UNVERIFIED` sang `VERIFIED`. Các khái niệm `VERIFIED` trở thành tài sản tri thức chuẩn mực của nền tảng làm Ground Truth cho Prove Mode.
- **BR-KNOW-03 (Bảo toàn tính toàn vẹn khi gộp hoặc bãi bỏ khái niệm)**: Khi một khái niệm bị gộp hoặc bãi bỏ, toàn bộ các chứng chỉ cột mốc `PROVEN` đã được cấp trong quá khứ của người học vẫn được bảo toàn nguyên vẹn giá trị, không bị thu hồi hay làm biến động điểm số lịch sử.

**Dữ liệu vào / ra chính**:
- **Đầu vào**: Khái niệm `UNVERIFIED`, định nghĩa đã chuẩn hóa, quan hệ tiên quyết.
- **Đầu ra**: Khái niệm chuyển sang `VERIFIED`, cập nhật Đồ thị tri thức, nhật ký kiểm toán quản trị.


## 6. Ma trận Truy vết Toàn cục (Master Traceability Matrix) & Rà soát Chất lượng

### 6.1. Bảng đối chiếu Truy vết Hai chiều giữa 43 Yêu cầu Chức năng (SRS v1.4 Post-CCB) và 47 Use Cases Lõi

Bảng dưới đây xác nhận độ bao phủ 100% hai chiều giữa toàn bộ 43 Yêu cầu Chức năng (`FR-*`) quy định trong SRS v1.4 Post-CCB và danh mục 47 Use Cases Lõi của kiến trúc v5.2:

| Mã FR | Tên Yêu cầu Chức năng (SRS v1.4) | Nhóm Bounded Context | Danh sách Use Cases hiện thực hóa | Ghi chú quy chuẩn & Cổng kiểm tra |
|---|---|---|---|---|
| **FR-AUTH-001** | Đăng ký tài khoản Người học | Account Context | `UC-ACC-01` | Xác minh mềm (Soft-verification), mật khẩu $\ge 8$ ký tự, cấp hạn ngạch FREE khởi đầu. |
| **FR-AUTH-002** | Đăng nhập & Quản lý Phiên Xác thực | Account Context | `UC-ACC-02` | Bảo mật cookie HttpOnly, khóa tạm sau 5 lần sai liên tiếp trong 15 phút. |
| **FR-AUTH-003** | Quản lý Hồ sơ Cá nhân & Múi giờ | Account Context | `UC-ACC-04` | Múi giờ IANA, cấu hình giờ rảnh, điều chỉnh thời gian biểu. |
| **FR-AUTH-004** | Tự đặt lại Mật khẩu qua Thư điện tử | Account Context | `UC-ACC-03` | Liên kết token ký số HMAC-SHA256 hạn 15 phút, thu hồi phiên toàn cục, chống enum email. |
| **FR-GOAL-001** | Nhập mục tiêu học tập ban đầu | Planning Context | `UC-PLAN-01`, `UC-PLAN-04` | Hỗ trợ cả hai luồng tạo qua AI (kèm nạp tài liệu RAG) và tạo thủ công. |
| **FR-GOAL-002** | Tương tác hỏi-đáp làm rõ ngữ cảnh với AI | Planning Context | `UC-PLAN-01` | Phỏng vấn chẩn đoán phân tầng 3–5 câu hỏi, hỗ trợ lưu trạng thái Pause/Resume. |
| **FR-GOAL-003** | Nạp Tài liệu Học tập & Khai thác Tri thức (RAG) | Planning Context | `UC-PLAN-01` | Upload file $\le 20$MB (PDF/MD/TXT/DOCX), kiểm tra SSRF, trích xuất vào `<untrusted_knowledge_context>`. |
| **FR-PLAN-001** | Sinh và Phê duyệt Cột mốc tổng quan Cấp 1 | Planning Context | `UC-PLAN-01`, `UC-PLAN-04`, `UC-PLAN-08` | Cột mốc 3–7 giai đoạn kèm tiêu chí hoàn thành và trích dẫn học liệu, quản lý an toàn. |
| **FR-PLAN-002** | Sinh Đề xuất Lịch trình chi tiết Cấp 2 | Planning Context | `UC-PLAN-02`, `UC-PLAN-03`, `UC-PLAN-10` | Phân rã bài học 30–120 phút, xếp lịch tất định tách biệt Roadmap vs ScheduleBlocks, mô phỏng What-if. |
| **FR-PLAN-003** | Xem xét, Chỉnh sửa và Áp dụng Lịch trình | Planning Context | `UC-PLAN-03`, `UC-PLAN-10`, `UC-ADAPT-06`, `UC-ADAPT-07` | Human-in-the-loop: Chỉ Apply mới ghi OfficialSchedule; Diff Preview song song. |
| **FR-PLAN-004** | Tạo và Lập kế hoạch Lộ trình Thủ công | Planning Context | `UC-PLAN-04` | Hoạt động độc lập hoàn toàn với AI, không tốn hạn ngạch, thời lượng linh hoạt 15–240 phút. |
| **FR-PLAN-005** | Kiểm định Tính hợp lệ của Lịch học Đa tầng | Planning Context | `UC-PLAN-09` (include bởi 9 UCs) | Thuật toán tất định $\le 50$ms: DAG, khoảng bận, 5 quy tắc Schedule Resilience. |
| **FR-PLAN-006** | Quản lý Danh mục, Cập nhật & Lưu trữ Lộ trình | Planning Context | `UC-PLAN-05`, `UC-PLAN-06`, `UC-ACC-10` | Kiểm tra targetDate $\ge$ ngày bài học cuối, trần 3 ACTIVE cho gói FREE. |
| **FR-AVAIL-001** | Cấu hình Thời gian rảnh Chế độ A | Account / Planning | `UC-ACC-04`, `UC-PLAN-03`, `UC-PLAN-10` | Định mức giờ/ngày (0.5h–14h/ngày theo OS-06) và ngày học trong tuần; hỗ trợ Schedule-Only Reoptimization. |
| **FR-AVAIL-002** | Cấu hình Thời gian rảnh Chế độ B | Account / Planning | `UC-ACC-04`, `UC-PLAN-03`, `UC-PLAN-09`, `UC-PLAN-10` | Khung giờ cố định $\ge 30$ phút, kiểm định khớp khung giờ qua UC-PLAN-09. |
| **FR-AVAIL-003** | Năng lực Đa Lộ trình & Lịch Ngoại vi | Planning Context | `UC-ACC-04`, `UC-EXEC-08`, `UC-ACC-10` | Cân đối thời gian rảnh tổng thể giữa các lộ trình và lịch cá nhân theo thuật toán EDF. |
| **FR-SCHEDULE-001**| Hiển thị Lịch học & Dời lịch Thủ công | Execution Context | `UC-EXEC-01`, `UC-EXEC-02` | Today Focus Card; dời lịch thủ công chỉ tăng reschedule_count khi quá hạn. |
| **FR-TASK-001** | Quản lý Công việc & Trạng thái Hoàn thành | Execution Context | `UC-PLAN-07`, `UC-EXEC-03`, `UC-EXEC-04`, `UC-EXEC-05` | Quick Complete bắt buộc Takeaway $\ge 30$ ký tự, micro-stepping $\le 30$ phút. |
| **FR-TASK-002** | Hàng đợi Backlog Queue & Xếp lịch Ưu tiên | Planning / Execution | `UC-PLAN-07` | Thuật toán thứ tự từ điển 4 tiêu chí (out_degree, sequence_order, reschedule_count, estimated_minutes). |
| **FR-TASK-003** | Quan hệ Tiên quyết & Kiểm soát DAG | Planning Context | `UC-PLAN-07`, `UC-PLAN-09`, `UC-PLAN-02`, `UC-PLAN-04`, `UC-PLAN-10` | Ràng buộc bất biến: đồ thị có hướng không chu trình. |
| **FR-SESSION-001** | Khởi động Phiên học, Today Focus & Chế độ MVS | Execution Context | `UC-EXEC-01`, `UC-EXEC-04` | Giao diện Focus Mode, đồng hồ Pomodoro/Stopwatch hoặc MVS 10–15 phút, Daily Check-in 3 chip. |
| **FR-SESSION-002** | Bắt buộc Đúc kết Key Takeaways & Scratchpad | Execution Context | `UC-EXEC-03`, `UC-EXEC-04` | Cổng Deterministic Takeaway Guard ($\ge 30$ ký tự, $\ge 6$ từ, token overlap $< 85\%$), lưu bằng chứng cho Prove Mode. |
| **FR-SESSION-003** | Xử lý Gián đoạn & Tự động Chốt Phiên | Execution Context | `UC-EXEC-04`, `UC-EXEC-06` | Mất tín hiệu nhịp tim 5 phút chốt phiên dở dang, ân hạn nợ đúc kết 24h. |
| **FR-ADAPT-001** | Quét Quá hạn, Gửi Email & Ngân sách Tuần | Adaptation Context | `UC-ADAPT-08`, `UC-ADAPT-10`, `UC-ADAPT-03`, `UC-ADAPT-06` | Quét động lúc 00:05 theo múi giờ, cơ chế kép làm mới ngân sách dời lịch tuần (trần 3 lượt). |
| **FR-ADAPT-002** | Dời lịch Hợp lý Bằng AI Trong 1 Lộ trình | Adaptation Context | `UC-ADAPT-06` | Rolling-Horizon 7–14 ngày, Adaptive Workload, hấp thụ buffer, trừ 1 ngân sách tuần khi Apply. |
| **FR-ADAPT-003** | Cơ chế STALLED, Chống trì hoãn & Reset Ritual | Adaptation Context | `UC-EXEC-02`, `UC-ADAPT-07`, `UC-EXEC-05` | Cảnh báo STALLED khi dời $\ge 3$ lần, 3 chiến lược Reset Ritual khi lộ trình ngủ đông $\ge 7$ ngày. |
| **FR-PAUSE-001** | Thiết lập Tạm dừng và Tiếp tục Lộ trình | Adaptation Context | `UC-ADAPT-04`, `UC-ADAPT-05` | Đóng băng lộ trình theo [PauseStart, PauseEnd], không tính trễ hạn, kiểm tra trần gói khi mở lại. |
| **FR-PAUSE-002** | Thuật toán Domino Shift | Adaptation Context | `UC-ADAPT-04`, `UC-ADAPT-05` | Tịnh tiến dây chuyền lịch học không phạt bộ đếm reschedule_count và không trừ ngân sách tuần. |
| **FR-CALENDAR-001**| Xuất Tệp tin Lịch Tĩnh `.ics` | Execution Context | `UC-EXEC-09` | Xuất file chuẩn iCalendar RFC 5545 một lần. |
| **FR-CALENDAR-002**| Kết nối Lịch Ngoại vi & Cung cấp WebCal | Execution Context | `UC-EXEC-07`, `UC-EXEC-08`, `UC-EXEC-09` | OAuth Google Calendar Inbound, WebCal feed an toàn Outbound. |
| **FR-CALENDAR-003**| Đặt lại Mã Bảo mật WebCal | Execution Context | `UC-EXEC-09` | Xoay vòng token WebCal vô hiệu hóa URL cũ tức thì, lưu băm SHA-256. |
| **FR-REPORT-001** | Thống kê Định lượng & Chỉ số Bắc đẩu WRLS | Evaluation Context | `UC-ADAPT-01`, `UC-EXEC-04`, `UC-ADAPT-03` | Chỉ số WRLS 0–100, Dòng thời gian Bằng chứng, tách biệt thống kê định lượng tất định. |
| **FR-REPORT-002** | Tạo Nhận xét Định tính & Nghi thức Chốt Tuần | Evaluation Context | `UC-ADAPT-03` | Tự phản tư 2–3 câu hỏi + AI coaching Zimmerman SRL 3 phần, cam kết tuần mới, làm mới sớm ngân sách. |
| **FR-REPORT-003** | Chế độ Kiểm chứng Cột mốc (Prove Mode) | Evaluation Context | `UC-ADAPT-02`, `UC-ADM-07`, `UC-ACC-11` | Kiểm chứng 2 tầng, thang điểm 1.00–5.00, khoảng cách siêu nhận thức có dấu, Mistake Intelligence 4 nhóm, Skill Mastery 5 cấp, ôn tập thông minh. |
| **FR-AI-001** | Kiểm tra Schema Đầu ra AI & Cơ chế Thử lại | Cross-Cutting | `UC-PLAN-01`, `UC-PLAN-02`, `UC-PLAN-03`, `UC-ADAPT-02`, `UC-ADAPT-03`, `UC-ADAPT-06`, `UC-ADAPT-07`, `UC-EXEC-05` | Xác thực JSON schema nghiêm ngặt, thử lại tối đa 1–2 lần. |
| **FR-AI-002** | Ngắt cứng Thời gian chờ AI & Fallback | Cross-Cutting | `UC-PLAN-01`, `UC-PLAN-02`, `UC-PLAN-03`, `UC-ADAPT-02`, `UC-ADAPT-03`, `UC-ADAPT-06`, `UC-ADAPT-07`, `UC-EXEC-05` | Hard timeout 55 giây, giải phóng hạn ngạch và chuyển sang chế độ dự phòng. |
| **FR-QUOTA-001** | Hạn ngạch AI Cấp Dịch vụ & Làm mới Định kỳ | Account Context | `UC-ACC-08`, `UC-ACC-09`, `UC-ADM-03`, `UC-ACC-06` | Giữ chỗ 2 pha JIT, dọn giữ chỗ quá 5 phút, làm mới đầu tháng (FREE 30, PREM 300). |
| **FR-QUOTA-002** | Nâng cấp Premium, Webhook & Hạ cấp Gói | Account Context | `UC-ACC-06`, `UC-ACC-07`, `UC-ACC-10`, `UC-ADM-02`, `UC-ADM-04` | Giá 99.000đ/30 ngày, gia hạn cộng dồn, Webhook HMAC, hạ cấp tự động EDF. |
| **FR-ADM-001** | Đăng nhập Quản trị viên, Phân quyền RBAC | Account Context | `UC-ACC-02`, `UC-ADM-01` | Xác thực Admin, RBAC chặt chẽ, thu hồi phiên khi tài khoản bị khóa. |
| **FR-ADM-002** | Quản trị Người dùng, Gói cước, Đối soát | Operations Context | `UC-ADM-01`, `UC-ADM-02`, `UC-ADM-03`, `UC-ADM-04` | Quản trị toàn diện, đối soát đơn EXPIRED -> PAID khi có mã ngân hàng. |
| **FR-ADM-003** | Bảng điều khiển Giám sát Vận hành & Doanh thu | Operations Context | `UC-ADM-05`, `UC-ADM-06` | Giám sát độ trễ, lỗi hệ thống, token AI, nhật ký kiểm toán bất biến. |
| **FR-PROFILE-001** | Quản trị Bộ nhớ Người học có Cấu trúc (Structured Learner Memory) | Account / Evaluation | `UC-ACC-11`, `UC-ADAPT-09` | 4 nhóm bộ nhớ $\times$ 3 tầng nhận thức, 7 trường metadata chuẩn, khôi phục Cold-Start. |
| **FR-PROFILE-002** | Đóng & Xóa vĩnh viễn Tài khoản theo Quyền được Lãng quên (GDPR Điều 17) | Account Context | `UC-ACC-05` | Soft delete kết hợp ẩn danh hóa PII, status='DELETED', hủy lịch tương lai, bảo lưu giao dịch kế toán. |

---

### 6.2. Kiểm tra Tuân thủ Tiêu chuẩn & Rà soát Chất lượng (Definition of Ready & Done)

Toàn bộ tài liệu đặc tả phiên bản v5.2 này đã vượt qua đầy đủ các tiêu chí thẩm định chất lượng theo các bộ tiêu chuẩn quốc tế:

1. **Tuân thủ Chuẩn OMG UML 2.5.1 (Clause 18)**:
   - Các Tác nhân (Actors) đều là thực thể ngoại vi nằm ngoài ranh giới hệ thống: **8 Tác nhân chuẩn hóa (`ACT-00` đến `ACT-07`)**, phân loại chính xác thành Primary (người dùng con người, tác nhân chủ động Webhook) và Secondary (hệ thống dịch vụ bên ngoài). Các thành phần hạ tầng nội bộ (`PostgreSQL`, `Taskiq` scheduler/worker, `Redis`, `Internal AI Harness`) nằm hoàn toàn bên trong ranh giới hệ thống và không xuất hiện làm Actor.
   - Các ca sử dụng kích hoạt định kỳ theo thời gian (`UC-ACC-08`, `UC-ACC-09`, `UC-ACC-10`, `UC-EXEC-06`, `UC-EXEC-08`, `UC-ADAPT-08`, `UC-ADAPT-09`, `UC-ADAPT-10`) tuân thủ nghiêm ngặt ngữ nghĩa `TimeEvent` của OMG UML 2.5.1: mô hình hóa thời gian dưới dạng điều kiện kích hoạt (`Trigger: OMG UML 2.5.1 TimeEvent`) trong bảng đặc tả và liên kết trực tiếp với Tác nhân Thụ hưởng Chính (`Learner — ACT-02`, `Administrator — ACT-03`) cùng các Tác nhân Hệ thống Ngoại vi tham gia (`ACT-06`, `ACT-07`).
   - Tác nhân trừu tượng `Registered User` thay thế chính xác nhãn sai `Authenticated User` tại `UC-ACC-02` và `UC-ACC-03`.
   - Quan hệ `<<include>>` chỉ áp dụng duy nhất cho `UC-PLAN-09: Kiểm định tính hợp lệ của lịch học` (Subfunction Level) được include bởi đúng 9 Use Cases (`UC-PLAN-03`, `UC-PLAN-04`, `UC-PLAN-07`, `UC-PLAN-10`, `UC-EXEC-02`, `UC-ADAPT-04`, `UC-ADAPT-05`, `UC-ADAPT-06`, `UC-ADAPT-07`) với hợp đồng bắt buộc xử lý đầy đủ các kết quả `{VALID, SOFT_OVERFLOW, INVALID}` và kiểm tra Schedule Resilience.
   - Loại bỏ hoàn toàn các quan hệ `<<extend>>` sai ngữ nghĩa (chuyển MVS thành chế độ trong `UC-EXEC-04`, Làm bài kiểm tra cột mốc `UC-ADAPT-02` và Đánh giá học tập cuối tuần `UC-ADAPT-03` thành các ca sử dụng độc lập).

2. **Tuân thủ Chuẩn Cockburn Goal-Level**:
   - 46 Use Cases đạt chuẩn mức mục tiêu người dùng / hệ thống (User-Goal / System-Goal Level) với luồng chính đánh số chủ động rõ ràng, giải quyết trọn vẹn một mục tiêu nghiệp vụ.
   - 01 Use Case đạt chuẩn mức chức năng con dùng chung (`UC-PLAN-09` Subfunction Level).
   - Tổng cộng: **47 Use Cases** bao phủ toàn diện 5 Bounded Contexts.

3. **Mô hình hóa theo Góc nhìn Hộp đen Phân tích Nghiệp vụ (Black-box BA View) Bảo toàn Thuộc tính Dữ liệu**:
   - Tài liệu loại bỏ toàn bộ chi tiết triển khai nội bộ tầng công nghệ (như thư viện ORM, câu lệnh SQL vật lý, chi tiết framework hạ tầng) để giữ ranh giới hệ thống thuần túy hướng mục tiêu người dùng.
   - Đồng thời, tài liệu **bảo toàn nghiêm ngặt tính toàn vẹn của các thuộc tính và cấu trúc dữ liệu miền nghiệp vụ** theo chuẩn ISO/IEC/IEEE 29148:2018 (như `claim_value`, `source_evidence`, `sample_size`, `confidence_score`, `reschedule_count`, `isOverdue`, `isDormant`, `calibrationGap`, `mistake_taxonomy_json`, `parent_task_id`, `disruptionCategory`), đảm bảo tính sẵn sàng tối đa cho các giai đoạn thiết kế CSDL (ERD/DDL) và phân tích Class Diagram kế tiếp.

4. **Khép kín 7 Quyết định Nghiệp vụ Thẩm định Chốt (D1 – D7)**:
   - Ngân sách dời lịch tuần: Cơ chế kép (Sự kiện thời gian 00:00 Thứ Hai + Chốt tuần sớm tối đa 1 lần/tuần, trần 3).
   - Ground Truth: 2 cấp linh hoạt (ưu tiên VERIFIED, nếu UNVERIFIED thì đối chiếu Task + Takeaways, chỉ Admin duyệt ở UC-ADM-07).
   - Thanh toán: Cho phép `EXPIRED -> PAID` có kiểm soát qua Webhook hoặc đối soát thủ công với mã ngân hàng.
   - Cờ quá hạn & ngủ đông: Thuần tính động thời gian thực (`isOverdue`, `isDormant`), Reset Ritual cập nhật `last_study_activity_at = NOW()`.
   - Hoàn thành nhanh: Bắt buộc nhập Key Takeaway $\ge 30$ ký tự và độ tự tin 1..5 lưu vào kho bằng chứng.
   - Xác minh email: Cơ chế mềm (Soft-verification) cho phép học ngay; bổ sung UC-ACC-03 Đặt lại mật khẩu qua signed email link.
   - Gói Premium: Giá 99.000đ/30 ngày, gia hạn cộng dồn `MAX(expires, NOW()) + 30` ngày.
