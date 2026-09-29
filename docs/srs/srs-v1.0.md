# FocusFlow — Software Requirements Specification (SRS)
## Phiên bản: v1.0 — Chuẩn Yêu cầu Cơ sở Đã Đóng Băng (Requirements Baseline Frozen v1.0)

---

| Thông tin tài liệu | Chi tiết |
|---|---|
| **Dự án** | FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI |
| **Cấp độ tài liệu** | Software Requirements Specification (SRS) |
| **Phiên bản** | v1.0 (Requirements Baseline Frozen) |
| **Trạng thái** | Chuẩn Cơ sở Đã Đóng Băng — Đã giải quyết 100% Quyết định Mở (Milestone M2 Sign-Off) |
| **Vai trò soạn thảo** | Senior Business Analyst / Senior Requirements Engineer |
| **Nguồn chân lý duy nhất (Single Source of Truth)** | `docs/requirements/problem-definition.md` |
| **Tiêu chuẩn Kỹ thuật Yêu cầu** | **ISO/IEC/IEEE 29148:2018** (Tham chiếu lịch sử: IEEE Std 830-1998) |
| **Căn cứ đánh giá học thuật** | Khung Rubric Đồ án Tốt nghiệp / Khóa luận CNTT (Tiêu chí TC1, TC2.1, TC2.3, TC2.7) |

---

## MỤC LỤC

1. [Giới thiệu (Introduction)](#1-giới-thiệu-introduction)
   - 1.1 [Mục đích (Purpose)](#11-mục-đích-purpose)
   - 1.2 [Phạm vi (Scope)](#12-phạm-vi-scope)
   - 1.3 [Đối tượng độc giả (Intended Audience)](#13-đối-tượng-độc-giả-intended-audience)
   - 1.4 [Tổng quan sản phẩm (Product Overview)](#14-tổng-quan-sản-phẩm-product-overview)
   - 1.5 [Hệ thống Thuật ngữ Chuẩn hóa (Canonical Definitions & Terminology)](#15-hệ-thống-thuật-ngữ-chuẩn-hóa-canonical-definitions--terminology)
   - 1.6 [Tài liệu tham khảo (References)](#16-tài-liệu-tham-khảo-references)
2. [Phạm vi & Bối cảnh Sản phẩm (Product Scope & Context)](#2-phạm-vi--bối-cảnh-sản-phẩm-product-scope--context)
   - 2.1 [Người dùng mục tiêu](#21-người-dùng-mục-tiêu)
   - 2.2 [Mục tiêu sản phẩm](#22-mục-tiêu-sản-phẩm)
   - 2.3 [Ranh giới hệ thống (System Boundaries)](#23-ranh-giới-hệ-thống-system-boundaries)
   - 2.4 [Các tính năng trong phạm vi (In-Scope — Core MVP)](#24-các-tính-năng-trong-phạm-vi-in-scope--core-mvp)
   - 2.5 [Các tính năng ngoài phạm vi (Out-of-Scope)](#25-các-tính-năng-ngoài-phạm-vi-out-of-scope)
3. [Tổng quan Tác nhân & Use Cases (Actors & Use Cases Overview)](#3-tổng-quan-tác-nhân--use-cases-actors--use-cases-overview)
   - 3.1 [Các tác nhân hệ thống (System Actors)](#31-các-tác-nhân-hệ-thống-system-actors)
   - 3.2 [Danh mục Use Cases Cấp Yêu cầu (Use Case Inventory)](#32-danh-mục-use-cases-cấp-yêu-cầu-use-case-inventory)
4. [Yêu cầu Nghiệp vụ (Business Requirements - BR)](#4-yêu-cầu-nghiệp-vụ-business-requirements---br)
5. [Quy tắc Nghiệp vụ Cốt lõi (Business Rules - BUSR)](#5-quy-tắc-nghiệp-vụ-cốt-lõi-business-rules---busr)
6. [Quy tắc Chuyển đổi Trạng thái (State Transition Rules)](#6-quy-tắc-chuyển-đổi-trạng-thái-state-transition-rules)
   - 6.1 [Vòng đời Lộ trình (Roadmap Lifecycle)](#61-vòng-đời-lộ-trình-roadmap-lifecycle)
   - 6.2 [Vòng đời Task & Điều kiện Quá hạn (Task Lifecycle & Derived Overdue Condition)](#62-vòng-đời-task--điều-kiện-quá-hạn-task-lifecycle--derived-overdue-condition)
   - 6.3 [Vòng đời Phiên học (Study Session Lifecycle)](#63-vòng-đời-phiên-học-study-session-lifecycle)
   - 6.4 [Vòng đời Đề xuất Lịch & Lịch Chính thức (Schedule Proposal & Official Schedule Lifecycle)](#64-vòng-đời-đề-xuất-lịch--lịch-chính-thức-schedule-proposal--official-schedule-lifecycle)
7. [Yêu cầu Chức năng (Functional Requirements - FR)](#7-yêu-cầu-chức-năng-functional-requirements---fr)
   - 7.1 [Xác thực & Quản lý Tài khoản (FR-AUTH)](#71-xác-thực--quản-lý-tài-khoản-fr-auth)
   - 7.2 [Thiết lập Mục tiêu & Thu thập Ngữ cảnh (FR-GOAL)](#72-thiết-lập-mục-tiêu--thu-thập-ngữ-cảnh-fr-goal)
   - 7.3 [Khởi tạo Kế hoạch & Duyệt 2 cấp độ bằng AI (FR-PLAN)](#73-khởi-tạo-kế-hoạch--duyệt-2-cấp-độ-bằng-ai-fr-plan)
   - 7.4 [Cấu hình Thời gian rảnh Lai (FR-AVAIL)](#74-cấu-hình-thời-gian-rảnh-lai-fr-avail)
   - 7.5 [Quản lý Lịch trình Chính thức (FR-SCHEDULE)](#75-quản-lý-lịch-trình-chính-thức-fr-schedule)
   - 7.6 [Quản trị Task & Hàng đợi Backlog (FR-TASK)](#76-quản-trị-task--hàng-đợi-backlog-fr-task)
   - 7.7 [Không gian Thực thi Phiên học & Phục hồi (FR-SESSION)](#77-không-gian-thực-thi-phiên-học--phục-hồi-fr-session)
   - 7.8 [Cơ chế Thích ứng khi Quá hạn (FR-ADAPT)](#78-cơ-chế-thích-ứng-khi-quá-hạn-fr-adapt)
   - 7.9 [Tạm dừng Lộ trình & Domino Shift (FR-PAUSE)](#79-tạm-dừng-lộ-trình--domino-shift-fr-pause)
   - 7.10 [Tích hợp Lịch ngoại vi WebCal & .ics (FR-CALENDAR)](#710-tích-hợp-lịch-ngoại-vi-webcal--ics-fr-calendar)
   - 7.11 [Báo cáo & AI Review Định kỳ (FR-REPORT)](#711-báo-cáo--ai-review-định-kỳ-fr-report)
   - 7.12 [Kiểm soát An toàn & Cơ chế Thử lại AI (FR-AI)](#712-kiểm-soát-an-toàn--cơ-chế-thử-lại-ai-fr-ai)
   - 7.13 [Quản trị Hạn ngạch & Mock Upgrade Sandbox (FR-QUOTA)](#713-quản-trị-hạn-ngạch--mock-upgrade-sandbox-fr-quota)
8. [Yêu cầu Phi Chức năng (Non-Functional Requirements - NFR)](#8-yêu-cầu-phi-chức-năng-non-functional-requirements---nfr)
   - 8.1 [Hiệu năng & Thời gian Phản hồi (NFR-PERF)](#81-hiệu-năng--thời-gian-phản-hồi-nfr-perf)
   - 8.2 [An toàn & Bảo mật Hệ thống (NFR-SEC)](#82-an-toàn--bảo-mật-hệ-thống-nfr-sec)
   - 8.3 [Độ sẵn sàng Hệ thống (NFR-AVAIL)](#83-độ-sẵn-sàng-hệ-thống-nfr-avail)
   - 8.4 [Khả năng Tương thích & Tiếp cận Giao diện (NFR-UX)](#84-khả-năng-tương-thích--tiếp-cận-giao-diện-nfr-ux)
   - 8.5 [Ràng buộc Đặc thù về AI (NFR-AI)](#85-ràng-buộc-đặc-thù-về-ai-nfr-ai)
9. [Tiêu chí Đánh giá Dự án & Thử nghiệm (Evaluation Metrics & Benchmarks)](#9-tiêu-chí-đánh-giá-dự-án--thử-nghiệm-evaluation-metrics--benchmarks)
10. [Kiểm soát Rủi ro & Kiến trúc An toàn AI (AI Risk Controls & Architecture Consistency)](#10-kiểm-soát-rủi-ro--kiến-trúc-an-toàn-ai-ai-risk-controls--architecture-consistency)
11. [Bảo mật & Quyền Sở hữu Dữ liệu (Security & Data Ownership)](#11-bảo-mật--quyền-sở-hữu-dữ-liệu-security--data-ownership)
12. [Yêu cầu Dữ liệu Cấp Khái niệm (Conceptual Data Requirements)](#12-yêu-cầu-dữ-liệu-cấp-khái-niệm-conceptual-data-requirements)
13. [Yêu cầu Giao diện Ngoại vi (External Interface Requirements)](#13-yêu-cầu-giao-diện-ngoại-vi-external-interface-requirements)
14. [Xử lý Ngoại lệ & Kịch bản Lỗi Toàn diện (Exception & Failure Handling)](#14-xử-lý-ngoại-lệ--kịch-bản-lỗi-toàn-diện-exception--failure-handling)
15. [Danh mục Điểm Chưa Đặc tả & Quyết định Mở (Open Specification / TBD Register)](#15-danh-mục-điểm-chưa-đặc-tả--quyết-định-mở-open-specification--tbd-register)
16. [Ma trận Truy vết Toàn diện (Comprehensive Traceability Matrix)](#16-ma-trận-truy-vết-toàn-diện-comprehensive-traceability-matrix)
17. [Kết luận & Tình trạng Chuẩn Cơ sở (Quality Sign-Off & Baseline Status)](#17-kết-luận--tình-trạng-chuẩn-cơ-sở-quality-sign-off--baseline-status)

---

## 1. Giới thiệu (Introduction)

### 1.1 Mục đích (Purpose)
Tài liệu **Software Requirements Specification (SRS) v1.0** này đặc tả chi tiết, đầy đủ và chuẩn hóa các yêu cầu chức năng, yêu cầu phi chức năng, quy tắc nghiệp vụ, ràng buộc an toàn AI và các giao diện tích hợp cho hệ thống **FocusFlow** — Nền tảng hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI.

Tài liệu đóng vai trò là chuẩn cơ sở kỹ thuật phục vụ phân tích hệ thống, mô hình hóa UML, thiết kế kiến trúc, thiết kế cơ sở dữ liệu và nghiệm thu kiểm thử phần mềm. Đối với các chi tiết nghiệp vụ chưa được giải quyết dứt khoát từ tài liệu gốc, tài liệu ghi nhận tường minh dưới dạng **Quyết định Mở của Chủ sở hữu Sản phẩm (Open Decision — Product Owner)** thay vì tự ý suy đoán.

### 1.2 Phạm vi (Scope)
Hệ thống FocusFlow được xây dựng dưới dạng ứng dụng web (Web Application) responsive, phục vụ người tự học thông qua quy trình 4 giai đoạn logic khép kín:
1. **Khởi tạo lộ trình & Duyệt lịch 2 cấp (Hierarchical Adaptive Planning & Human Approval)**: Định danh người dùng, thu thập mục tiêu, AI làm rõ ngữ cảnh, sinh Milestone, sinh Schedule Proposal và áp dụng validation gate để lưu Official Schedule.
2. **Không gian thực thi phiên học (Active Study Workspace)**: Hỗ trợ phiên học tập trung với bộ công cụ Study Tool Suite (Pomodoro/Stopwatch, Scratchpad, Key Takeaways, Task Checklist) và xử lý gián đoạn/phục hồi phiên học.
3. **Thích ứng & Quản trị lịch (Adaptive Shift & Calendar Management)**: Tự động phát hiện task quá hạn bằng thuật toán tất định, cung cấp tùy chọn AI sắp xếp lại, hỗ trợ tạm dừng lộ trình với thuật toán tịnh tiến dây chuyền (Domino Shift), xuất lịch tĩnh `.ics` và đăng ký luồng 1 chiều bảo mật WebCal.
4. **Tổng kết & Cải tiến chu kỳ (Review & Continuous Retrospective)**: Báo cáo định lượng toán học chính xác kết hợp nhận xét định tính từ AI Review.
5. **Kiểm soát hạn ngạch dịch vụ (Quota Guard & Mock Sandbox)**: Quản lý quota gọi AI theo phân tầng Free/Premium tại tầng middleware dịch vụ kèm sandbox mô phỏng nâng cấp.

### 1.3 Đối tượng độc giả (Intended Audience)
- **Sinh viên / Tác giả đề tài**: Định hướng phân tích thiết kế, lập trình, kiểm thử và viết khóa luận tốt nghiệp.
- **Giảng viên hướng dẫn & Hội đồng đánh giá**: Căn cứ chấm điểm đồ án dựa trên bảng Rubric chuẩn (tiêu chí TC1, TC2.1, TC2.3, TC2.7).
- **Kỹ sư kiểm thử (QA/Tester) & Người dùng thử nghiệm (UAT Participants)**: Căn cứ thiết kế test case và kiểm chứng tiêu chí chấp nhận.

### 1.4 Tổng quan sản phẩm (Product Overview)
FocusFlow là nền tảng chuyên biệt giải quyết triệt để 3 nút thắt của người tự học:
- **Rào cản phân rã mục tiêu (Decomposition Barrier)**: Giải quyết bằng cơ chế hỏi đáp làm rõ và phân rã 2 cấp (Milestones & Schedule Proposal).
- **Phân mảnh công cụ (Tool Fragmentation)**: Giải quyết bằng Study Workspace tích hợp khép kín giữa Lộ trình $\leftrightarrow$ Task $\leftrightarrow$ Timer $\leftrightarrow$ Notes $\leftrightarrow$ Review.
- **Đứt gãy kế hoạch khi có biến cố (Rigid Planning Failure)**: Giải quyết bằng thuật toán tất định phát hiện trễ hạn, tùy chọn AI Reprioritization và thuật toán Pause Roadmap với Domino Shift.

### 1.5 Hệ thống Thuật ngữ Chuẩn hóa (Canonical Definitions & Terminology)

| Thuật ngữ chuẩn | Khái niệm phân biệt & Định nghĩa nghiệp vụ |
|---|---|
| **Goal** | Ý định học tập ban đầu do Learner nhập vào hệ thống (ví dụ: *"Học Backend Golang trong 3 tháng"*), là đầu vào cho quy trình làm rõ và sinh lộ trình. |
| **Roadmap** | Lộ trình học tập tổng thể của một mục tiêu, bao gồm danh sách Milestones và các nhiệm vụ tương ứng, có trạng thái vòng đời riêng (`INITIALIZED`, `ACTIVE`, `PAUSED`, `COMPLETED`). |
| **Milestone** | Cột mốc kiến thức/kỹ năng trung gian (Cấp độ 1 của lộ trình) cần đạt được trong một giai đoạn cụ thể. |
| **Task** | Đầu việc/nhiệm vụ học tập cụ thể (Cấp độ 2), có thời lượng dự tính, trạng thái vòng đời và mốc ngày thực hiện. |
| **Scheduled Task** | Task đã được phân bổ ngày học cụ thể (`scheduled_date != NULL`) trong Official Schedule hoặc Schedule Proposal. |
| **Backlog Task** | Task chưa được gán ngày thực hiện (`scheduled_date == NULL`), nằm trong hàng đợi Backlog của Roadmap. |
| **Overdue Task** | Điều kiện suy diễn (derived condition) của task khi thỏa mãn: $\text{task.status} \neq \text{COMPLETED} \land \text{task.scheduled\_date} < \text{CURRENT\_DATE}$. |
| **Schedule Proposal** (hoặc **AI Proposal**) | Bản đề xuất lịch trình tạm thời do AI sinh ra dựa trên Milestone đã duyệt và cấu hình thời gian rảnh; mang tính dự thảo (`DRAFT`), chưa có giá trị chính thức và Learner có toàn quyền chỉnh sửa. |
| **Official Schedule** | Lịch trình học tập chính thức đã được Backend kiểm tra tính hợp lệ (Validation Gate) sau khi Learner chủ động bấm "Apply"; là nguồn dữ liệu duy nhất để hiển thị lịch làm việc, tính toán tiến độ và xuất ra WebCal. |
| **Learner** | Người học / Người dùng cuối (End-User) trực tiếp sử dụng hệ thống để tạo lộ trình và thực thi các phiên học. |
| **Administrator** | Vai trò cấp dịch vụ/hệ thống (Service Role), thực hiện cấu hình quota và giám sát hạ tầng tại middleware; không có giao diện Admin Portal riêng. |
| **Availability** | Cấu hình thời gian rảnh của Learner dùng để làm căn cứ xếp lịch học. |
| **Availability Mode A — Daily Hours Quota** | Chế độ thời gian rảnh theo quỹ tổng số giờ khả dụng mỗi ngày (Ví dụ: Thứ Hai 2h, Thứ Bảy 4h). |
| **Availability Mode B — Time Slot Window** | Chế độ thời gian rảnh theo các khung giờ cố định cụ thể trong ngày (Ví dụ: Thứ Hai 19:00 – 21:00). |
| **Study Session** (hoặc **Session**) | Phiên học tập trung thời gian thực trong Study Workspace gắn liền với một danh sách task cụ thể. |
| **Study Workspace** | Không gian làm việc tập trung trong phiên học, tích hợp Task Checklist, Timer/Stopwatch, Scratchpad và Key Takeaways. |
| **Pause Roadmap** | Tính năng cho phép tạm dừng một lộ trình học tập trong một khoảng thời gian xác định (từ ngày A đến ngày B). |
| **Domino Shift** | Thuật toán tịnh tiến dây chuyền: dời toàn bộ các ngày học kể từ ngày bắt đầu tạm dừng lùi về sau đúng bằng số ngày khả dụng tương ứng, bảo toàn nguyên vẹn thứ tự các task. |
| **Adaptive Recovery** | Cơ chế thích ứng và phục hồi kế hoạch khi xảy ra quá hạn, kết hợp phát hiện tất định phía Backend và tùy chọn AI sắp xếp lại. |
| **Plan Adherence** | Tỷ lệ tuân thủ kế hoạch học tập, đo bằng tỷ lệ phần trăm số buổi học người dùng tham gia trên tổng số buổi đã lên lịch (loại trừ khoảng thời gian PAUSED). |
| **AI Planning** | Quy trình tương tác với mô hình ngôn ngữ lớn để làm rõ mục tiêu, phân rã kiến thức và sinh đề xuất kế hoạch. |
| **AI Reprioritization** | Tính năng tùy chọn do người dùng chủ động kích hoạt để nhờ AI gợi ý lại thứ tự ưu tiên cho danh sách task tồn đọng. |
| **WebCal** | Giao thức đăng ký theo dõi lịch ngoại vi một chiều qua URL bảo mật định dạng `.ics`. |
| **`.ics`** | Định dạng tệp tin lịch chuẩn iCalendar tĩnh được hệ thống kết xuất để tải về. |
| **AI Quota** | Định mức hạn ngạch gọi dịch vụ AI (Token usage & Request Quota) được cấp cho tài khoản theo phân tầng Free/Premium. |
| **Mock Upgrade Sandbox** | Giao diện mô phỏng việc nâng cấp gói tài khoản để thử nghiệm tính năng nới rộng hạn ngạch, không tích hợp cổng thanh toán thực tế. |
| **Review / Retrospective** | Hoạt động tổng kết định kỳ gồm phân tích số liệu định lượng toán học và nhận xét định tính từ AI Review. |

### 1.6 Tài liệu tham khảo (References)
1. **ISO/IEC/IEEE 29148:2018** — Systems and software engineering — Life cycle processes — Requirements engineering *(Chuẩn kỹ thuật chính)*.
2. IEEE Std 830-1998 — Recommended Practice for Software Requirements Specifications *(Tham chiếu lịch sử)*.
3. `docs/requirements/problem-definition.md` — FocusFlow Problem Definition & Requirements Discovery Document (Approved Baseline).
4. `docs/requirements/user-survey-and-benchmarking.md` — FocusFlow User Needs Survey & Competitive Benchmarking Report (DOC-REQ-SURVEY-01).
5. `docs/requirements/business-goals-and-kpis.md` — FocusFlow Business Goals & Quantitative KPIs Specification (DOC-REQ-GOALS-01).
6. `docs/requirements/system-actors-and-personas.md` — FocusFlow System Actors & User Personas Analysis Specification (DOC-REQ-ACTOR-01).
7. `AGENTS.md` — FocusFlow Agent Instructions & Engineering Governance Rules.
8. RFC 5545 — Internet Calendaring and Scheduling Core Object Specification (iCalendar).

---

## 2. Phạm vi & Bối cảnh Sản phẩm (Product Scope & Context)

### 2.1 Người dùng mục tiêu
Cá nhân tự học (Self-Directed Learners) có nhu cầu nâng cao kỹ năng nghề nghiệp, công nghệ, ngoại ngữ; có quỹ thời gian hạn hẹp cần tối ưu hóa và có xu hướng nản lòng khi kế hoạch học tập bị đổ vỡ do biến cố đời sống.

### 2.2 Mục tiêu sản phẩm
Xây dựng một hệ thống khép kín hỗ trợ người học chuyển hóa mục tiêu trừu tượng thành hành động khả thi mỗi ngày, duy trì sự tập trung tối đa trong từng phiên học, thích ứng linh hoạt trước biến cố mà không làm gãy đổ kỷ luật cá nhân, và phản tư định kỳ để cải tiến hiệu suất.

### 2.3 Ranh giới hệ thống (System Boundaries)
```
+-------------------------------------------------------------------------------+
|                               FOCUSFLOW SYSTEM                                |
|                                                                               |
|  [Auth & Quota] <---> [Planning Engine] <---> [Active Study Workspace]        |
|         ^                     |                              |                |
|         |                     v                              v                |
|  [User Database]      [Official Schedule] <--------> [Session Logs & Notes]   |
|                               |                              |                |
|                               v                              v                |
|                    [Adaptive Recovery / Pause]      [Quantitative Reporting]  |
+-------------------------------|------------------------------|----------------+
                                |                              |
           +--------------------+                              v
           v                                            [AI Review Engine]
   [1-Way WebCal Feed / .ics]                                  |
           |                                                   v
           v                                         [External LLM Provider]
 [Apple / Google Calendar]
```

### 2.4 Các tính năng trong phạm vi (In-Scope — Core MVP)
- **Module Quản lý tài khoản & Hồ sơ**: Đăng ký, đăng nhập email/mật khẩu, xác thực phiên làm việc, thiết lập cấu hình thời gian rảnh lai (Mode A / Mode B).
- **Module Lập kế hoạch AI**: Thu thập thông tin mục tiêu, đối thoại làm rõ, sinh Milestone, sinh Schedule Proposal, giao diện xem lại/chỉnh sửa, thao tác "Apply" và Backend Validation Gate.
- **Module Không gian phiên học**: Danh sách kiểm tra task, bộ công cụ Study Tool Suite (Pomodoro / Stopwatch), ghi chú Scratchpad, ghi chú đúc kết Key Takeaways, cơ chế xử lý phiên gián đoạn và phục hồi phiên học.
- **Module Thích ứng & Lịch trình**: Quét phát hiện task quá hạn bằng logic tất định, tùy chọn AI Reprioritization, tính năng Tạm dừng lộ trình (Domino Shift), kết xuất file `.ics` và luồng WebCal 1 chiều bảo mật token.
- **Module Báo cáo & Đánh giá**: Bảng điều khiển số liệu thống kê định lượng và trợ lý AI Review đưa ra nhận xét định tính chu kỳ.
- **Module Quản trị Hạn ngạch (Quota Service & Mock Sandbox)**: Middleware kiểm soát hạn ngạch Free/Premium và giao diện thử nghiệm nâng cấp mô phỏng Mock Upgrade.

### 2.5 Các tính năng ngoài phạm vi (Out-of-Scope)
- **Đồng bộ hai chiều với Google Calendar / Apple Calendar**: Không hỗ trợ đọc ngược sự kiện từ lịch ngoài về hệ thống hoặc xử lý xung đột hai chiều.
- **Cổng thanh toán thực tế (Payment Gateway)**: Không tích hợp các cổng thanh toán thực tế (Stripe, VNPay, Momo...); mọi luồng nâng cấp đều thông qua Mock Upgrade Sandbox.
- **Giao diện bảng điều khiển quản trị viên (Admin Portal/Dashboard Web)**: Quản trị viên chỉ cấu hình qua file/biến môi trường hoặc middleware cấp dịch vụ.
- **Ứng dụng Native Mobile (iOS/Android)**: Không phát triển ứng dụng di động gốc; tập trung duy nhất vào Web Application responsive.
- **Mạng xã hội & Tương tác cộng đồng**: Không hỗ trợ kết bạn, bảng tin, chia sẻ công khai lộ trình hoặc nhắn tin giữa các người học.

---

## 3. Tổng quan Tác nhân & Use Cases (Actors & Use Cases Overview)

### 3.1 Các tác nhân hệ thống (System Actors)

#### 1. Learner (Tác nhân người dùng chính)
Cá nhân trực tiếp trải nghiệm toàn bộ vòng đời sản phẩm.
- **Trách nhiệm của Learner**:
  - Đăng ký và bảo vệ thông tin xác thực tài khoản cá nhân.
  - Cung cấp chính xác mục tiêu học tập và thiết lập thời gian rảnh (Availability).
  - Chủ động xem xét, tinh chỉnh và bấm "Apply" để phê duyệt Schedule Proposal thành Official Schedule.
  - Thực hiện phiên học trong Study Workspace, ghi nhận kết quả và đúc kết Key Takeaway.
  - Kích hoạt yêu cầu sắp xếp lại (AI Reprioritization) hoặc tạm dừng lộ trình (Pause Roadmap) khi cần.
  - Quản lý và đổi mã bảo mật WebCal token của chính mình.

#### 2. Administrator (Tác nhân dịch vụ / Hệ thống)
Vai trò quản trị dịch vụ nền tảng (Service Role).
- **Trách nhiệm của Administrator**:
  - Thiết lập và bảo trì định mức hạn ngạch gọi AI (Tokens / Requests) cho các phân tầng Free và Premium tại tầng middleware/cấu hình dịch vụ.
  - Giám sát độ sẵn sàng và chỉ số vận hành của hệ thống.

#### 3. External LLM Provider (Hệ thống ngoài)
Dịch vụ mô hình ngôn ngữ lớn cung cấp qua giao diện API hỗ trợ Structured JSON Outputs.
- **Trách nhiệm của External LLM**:
  - Nhận prompt yêu cầu từ FocusFlow backend.
  - Phản hồi kết quả phân rã mục tiêu, tạo đề xuất lịch và nhận xét định kỳ theo đúng JSON schema được chỉ định trong thời gian quy định.

#### 4. External Calendar Application (Hệ thống ngoài)
Các ứng dụng lịch tiêu chuẩn của bên thứ ba (Google Calendar, Apple Calendar, Outlook...).
- **Trách nhiệm**: Đọc dữ liệu định dạng `.ics` hoặc định kỳ truy vấn luồng WebCal 1 chiều qua URL kèm token bảo mật.

### 3.2 Danh mục Use Cases Cấp Yêu cầu (Use Case Inventory)

| Mã Use Case | Tên Use Case | Tác nhân chính | Tác nhân hỗ trợ |
|---|---|---|---|
| **UC-AUTH-01** | Đăng ký tài khoản mới | Learner | Hệ thống |
| **UC-AUTH-02** | Đăng nhập hệ thống | Learner | Hệ thống |
| **UC-AVAIL-01** | Cấu hình thời gian rảnh (Mode A / Mode B) | Learner | Hệ thống |
| **UC-PLAN-01** | Khởi tạo mục tiêu & Đối thoại làm rõ | Learner | External LLM |
| **UC-PLAN-02** | Xem xét & Phê duyệt Milestones (Cấp 1) | Learner | Hệ thống |
| **UC-PLAN-03** | Tạo Schedule Proposal & Phê duyệt Lịch (Cấp 2 - Apply) | Learner | External LLM, Hệ thống |
| **UC-PLAN-04** | Lập kế hoạch thủ công (Fallback Manual Plan) | Learner | Hệ thống |
| **UC-SESS-01** | Thực hiện phiên học trong Study Workspace | Learner | Hệ thống |
| **UC-SESS-02** | Xử lý gián đoạn / Dừng phiên học sớm | Learner | Hệ thống |
| **UC-TASK-01** | Cập nhật trạng thái hoàn thành Task | Learner | Hệ thống |
| **UC-ADAPT-01** | Quét phát hiện task quá hạn tất định | Hệ thống (Tự động) | - |
| **UC-ADAPT-02** | Yêu cầu AI sắp xếp lại danh sách task tồn đọng | Learner | External LLM |
| **UC-PAUSE-01** | Thiết lập tạm dừng lộ trình & Domino Shift | Learner | Hệ thống |
| **UC-CAL-01** | Xuất tệp lịch tĩnh `.ics` | Learner | Hệ thống |
| **UC-CAL-02** | Đăng ký & Quản lý Token WebCal 1 chiều | Learner | External Calendar App |
| **UC-REP-01** | Xem báo cáo tiến độ định lượng | Learner | Hệ thống |
| **UC-REP-02** | Yêu cầu nhận xét định tính từ AI Review | Learner | External LLM |
| **UC-QUOTA-01** | Trải nghiệm nâng cấp giả lập (Mock Upgrade) | Learner | Hệ thống |

---

## 4. Yêu cầu Nghiệp vụ (Business Requirements - BR)

- **BR-001: Rút ngắn thời gian khởi tạo kế hoạch học tập**
  - **Mô tả**: Hệ thống phải cung cấp quy trình phân rã tự động và giao diện phê duyệt tập trung cho phép hoàn tất việc tạo và lưu lộ trình chi tiết trong vòng $\le 5$ phút.
  - **Nguồn gốc**: `problem-definition.md` (Mục 1.2, Mục 4 - KPI 1).
  - **Tiêu chuẩn đo lường**: Thời gian từ lúc gửi mục tiêu đến khi hoàn tất lưu Official Schedule đạt $\le 300$ giây trong điều kiện kết nối mạng chuẩn.

- **BR-002: Nâng cao hiệu quả thực thi trong buổi học**
  - **Mô tả**: Hệ thống phải cung cấp không gian học tập tích hợp (Study Workspace) hỗ trợ người học theo dõi và thực thi các nhiệm vụ đã lên lịch trong từng buổi học.
  - **Nguồn gốc**: `problem-definition.md` (Mục 4 - KPI 2, Mục 5.3).
  - **Chỉ tiêu đánh giá**: Hỗ trợ người học hướng đến tỷ lệ hoàn thành nhiệm vụ trong phiên $\ge 80\%$.

- **BR-003: Duy trì tính liên tục và giảm thiểu tỷ lệ bỏ cuộc**
  - **Mô tả**: Hệ thống phải hỗ trợ các cơ chế thích ứng lịch (Adaptive Recovery, Domino Shift) để bảo vệ tính liên tục của kế hoạch học tập khi xảy ra sự cố.
  - **Nguồn gốc**: `problem-definition.md` (Mục 4 - KPI 3, Mục 5.4).
  - **Chỉ tiêu đánh giá**: Hỗ trợ người học hướng đến tỷ lệ tuân thủ kế hoạch (Plan Adherence) $\ge 70\%$ (loại trừ các khoảng thời gian lộ trình ở trạng thái `PAUSED`).

- **BR-004: Đảm bảo khả năng sử dụng và mức độ hài lòng cao**
  - **Mô tả**: Hệ thống phải được thiết kế trực quan, dễ thao tác, có khả năng đo lường tỷ lệ hoàn thành tác vụ (Task Success Rate) và điểm đánh giá khả năng sử dụng chuẩn hóa SUS khi thử nghiệm với người dùng thật.
  - **Nguồn gốc**: `problem-definition.md` (Mục 4 - KPI 4, KPI 5, Tiêu chí TC2.7).
  - **Chỉ tiêu đánh giá**: Đo lường trong đợt thử nghiệm UAT đạt Task Success Rate $\ge 90\%$ và điểm SUS $\ge 80/100$ trên tối thiểu 10 người dùng thật.

- **BR-005: Kiểm soát chặt chẽ chi phí và sự phụ thuộc vào AI**
  - **Mô tả**: Hệ thống phải kiểm soát tuyệt đối hạn ngạch gọi dịch vụ LLM, không bao giờ để người dùng chưa xác thực hoặc vượt hạn ngạch gọi ra dịch vụ AI ngoài; giữ chi phí trong phạm vi ngân sách đồ án.
  - **Nguồn gốc**: `problem-definition.md` (Mục 5.1, Mục 8.2, Mục 9).
  - **Tiêu chuẩn đo lường**: 100% request gọi AI được xác thực danh tính và kiểm tra quota tại backend trước khi phát sinh request ra nhà cung cấp LLM.

---

## 5. Quy tắc Nghiệp vụ Cốt lõi (Business Rules - BUSR)

- **BUSR-01: Định danh bắt buộc trước khi tạo kế hoạch (Onboarding First)**
  - Người dùng bắt buộc phải hoàn tất Đăng ký / Đăng nhập trước khi được phép nhập mục tiêu và yêu cầu AI tạo kế hoạch.
  - Kế hoạch học tập, dữ liệu phiên học và hạn ngạch AI bắt buộc phải gắn liền với ID định danh của người dùng đã xác thực.

- **BUSR-02: Phân tách tuyệt đối giữa Schedule Proposal và Official Schedule (Human-in-the-Loop Gate)**
  - Mọi kết quả phân rã thời gian do AI sinh ra chỉ là **Schedule Proposal** (Bản đề xuất lịch trình tạm thời).
  - AI tuyệt đối không có quyền tự động ghi dữ liệu vào Official Schedule.
  - Chỉ khi người dùng thực hiện hành động bấm nút **"Apply"** rõ ràng và dữ liệu vượt qua cổng kiểm tra tính hợp lệ của Backend (Validation Gate), đề xuất mới được chuyển đổi và lưu thành **Official Schedule**.

- **BUSR-03: Thực thi giới hạn thời gian rảnh cứng từ Backend (Backend Hard Ceiling)**
  - Backend là chốt chặn cuối cùng kiểm tra sự hợp lệ về mặt thời gian.
  - Tổng thời lượng task được xếp trong một ngày hoặc khung giờ không bao giờ được vượt quá thời gian rảnh khả dụng đã cấu hình của người dùng, ngoại trừ trường hợp thỏa mãn quy tắc Tràn giờ mềm (Soft Overflow).
  - Giới hạn hợp lệ của cấu hình quỹ giờ mỗi ngày (Mode A) tuân theo quy định tại `OS-06`.

- **BUSR-04: Quy tắc Tràn giờ mềm có kiểm soát (Soft Overflow Rule)**
  - Chỉ áp dụng đối với task cuối cùng trong một ngày học thuộc chế độ Mode B (Time Slot Window).
  - Task cuối cùng được phép kết thúc muộn hơn mốc kết thúc của khung giờ rảnh tối đa **30 phút**.
  - Hệ thống phải hiển thị cảnh báo trực quan về thời gian tràn giờ và yêu cầu người dùng xác nhận rõ ràng trước khi cho phép "Apply".

- **BUSR-05: Dung lượng đa lộ trình (Multi-Roadmap Capacity Rule)**
  - Người dùng có quyền sở hữu nhiều Roadmap đồng thời.
  - Khi xếp lịch cho Roadmap mới hoặc dời lịch, hệ thống phải trừ đi các khoảng thời gian đã được cam kết cho Official Schedule của các Roadmap hiện có.
  - Các task mới chỉ được xếp vào các khoảng trống thời gian (available capacity slots) còn lại.
  - Thứ tự ưu tiên giải quyết khi có xung đột cạnh tranh slot giữa các Roadmap tuân theo quyết định mở `OS-04`.

- **BUSR-06: Phát hiện quá hạn tất định (Deterministic Overdue Formula)**
  - Tình trạng task quá hạn là một điều kiện suy diễn (derived condition) được tính toán thuần túy bởi logic phía backend theo công thức:
    $$\text{task.status} \neq \text{COMPLETED} \quad \land \quad \text{task.scheduled\_date} < \text{CURRENT\_DATE}$$
  - Điều kiện quá hạn không phụ thuộc vào LLM và được cập nhật tự động khi ngày mới bắt đầu.

- **BUSR-07: Cơ chế tịnh tiến dây chuyền khi tạm dừng (Domino Shift Rule)**
  - Khi người dùng thiết lập Tạm dừng lộ trình (Pause Roadmap) từ ngày A đến ngày B:
    - Tất cả các buổi học đã lên lịch từ ngày A trở đi sẽ được tịnh tiến lùi về sau đúng bằng số ngày khả dụng tương ứng với khoảng thời gian tạm dừng.
    - Toàn bộ thứ tự tuần tự và liên kết logic của các task được bảo toàn nguyên vẹn.
    - Trong khoảng thời gian từ ngày A đến ngày B, hệ thống không phát sinh bất kỳ cảnh báo quá hạn nào cho lộ trình bị tạm dừng.

- **BUSR-08: Bảo mật dữ liệu lịch ngoại vi (1-Way WebCal Security Rule)**
  - Luồng WebCal chỉ là luồng đăng ký **một chiều (1-Way Subscription)**; hệ thống không tiếp nhận hoặc xử lý bất kỳ thay đổi nào từ ứng dụng lịch bên ngoài dội ngược về.
  - Luồng WebCal và file `.ics` tuyệt đối **chỉ xuất bản các task thuộc Official Schedule**. Các task thuộc Schedule Proposal hoặc Backlog không bao giờ được đưa vào feed.
  - Mỗi liên kết WebCal gắn liền với một mã token ngẫu nhiên bảo mật (user secure token). Khi người dùng bấm "Reset Token", token cũ bị hủy hiệu lực ngay lập tức.
  - URL và mã token WebCal tuyệt đối không được ghi vào log truy cập máy chủ (access logs) ở dạng bản rõ.

- **BUSR-09: Bảo toàn dữ liệu khi gián đoạn phiên học (Session Interruption Rule)**
  - Khi phiên học bị hủy hoặc dừng sớm trước thời gian dự kiến:
    - Hệ thống phải lưu chính xác số phút thực học đã trôi qua vào lịch sử hoạt động.
    - Giữ nguyên trạng thái `COMPLETED` cho các task đã được người dùng tick hoàn thành.
    - Toàn bộ các task chưa hoàn thành trong phiên học tự động được trả về danh sách Backlog an toàn mà không phạt người học.
    - Trạng thái kết thúc của phiên học gián đoạn (`PARTIAL_COMPLETED` hoặc `CANCELLED`) tuân theo quy tắc chuyển đổi trạng thái tại Mục 6.3 và quyết định mở `OS-01`.

- **BUSR-10: Kiểm soát hạn ngạch và quyền riêng tư AI (AI Quota & Privacy Guard)**
  - Middleware hệ thống phải kiểm tra hạn ngạch khả dụng của tài khoản trước khi chuyển tiếp yêu cầu đến nhà cung cấp LLM.
  - Giao dịch kiểm tra và trừ hạn ngạch phải đảm bảo tính nguyên tử (atomic transaction).
  - Các request gọi AI thất bại (503, 429, timeout) hoặc các lượt auto-retry do lỗi schema nội bộ tuyệt đối không được trừ thêm hạn ngạch của người dùng.
  - Thông tin nhạy cảm của người dùng (mật khẩu, ghi chú cá nhân bảo mật) tuyệt đối không được đưa vào prompt gửi ra mô hình AI bên ngoài.

---

## 6. Quy tắc Chuyển đổi Trạng thái (State Transition Rules)

Mục này chuẩn hóa toàn bộ các máy trạng thái (State Machines) của hệ thống. Mọi chuyển đổi trạng thái phải có điều kiện tiên quyết, sự kiện kích hoạt và trạng thái đích rõ ràng.

### 6.1 Vòng đời Lộ trình (Roadmap Lifecycle)

```
       [Tạo mới Goal]
             │
             ▼
     ┌───────────────┐
     │  INITIALIZED  │ (Đang làm rõ mục tiêu / Milestones)
     └───────┬───────┘
             │ [Apply Official Schedule thành công]
             ▼
     ┌───────────────┐  [Bấm Pause Roadmap]   ┌───────────────┐
     │    ACTIVE     │ ─────────────────────> │    PAUSED     │
     │               │ <───────────────────── │ (Domino Shift)│
     └───────┬───────┘  [Hết hạn Pause/Resume]└───────────────┘
             │
             │ [100% Task hoàn thành]
             ▼
     ┌───────────────┐
     │   COMPLETED   │
     └───────────────┘
```

| Trạng thái Nguồn | Sự kiện / Hành động (Trigger) | Điều kiện Tiên quyết (Preconditions) | Trạng thái Đích | Hậu điều kiện / Hành vi Kèm theo |
|---|---|---|---|---|
| *(Khởi tạo)* | Nhập mục tiêu ban đầu (FR-GOAL-001) | User đã đăng nhập | `INITIALIZED` | Tạo bản ghi Goal, bắt đầu luồng làm rõ và sinh Milestone. |
| `INITIALIZED` | Apply Official Schedule (FR-PLAN-003) | Proposal vượt qua Backend Validation Gate | `ACTIVE` | Lịch trình chính thức được lưu bền vững, bắt đầu theo dõi tiến độ. |
| `ACTIVE` | Thiết lập Pause Roadmap (FR-PAUSE-001) | Chọn khoảng ngày tạm dừng hợp lệ `[PauseStart, PauseEnd]` | `PAUSED` | Kích hoạt Domino Shift (FR-PAUSE-002), vô hiệu hóa cảnh báo quá hạn. |
| `PAUSED` | Hết hạn Pause hoặc bấm Tiếp tục sớm | Ngày hiện tại $> \text{PauseEnd}$ hoặc User hủy Pause | `ACTIVE` | Kích hoạt lại việc theo dõi lịch và cảnh báo quá hạn theo lịch đã dời. |
| `ACTIVE` | Hoàn thành task cuối cùng | 100% task thuộc Roadmap có trạng thái `COMPLETED` | `COMPLETED` | Ghi nhận thời điểm hoàn tất lộ trình, hiển thị lời chúc mừng. |
| `COMPLETED` | Bất kỳ hành động sửa đổi nào | Không cho phép | *Bất biến* | Lộ trình đã hoàn thành không được kích hoạt lại (muốn học tiếp phải tạo Goal mới). |

### 6.2 Vòng đời Task & Điều kiện Quá hạn (Task Lifecycle & Derived Overdue Condition)

> **LÀM RÕ KIẾN TRÚC**: Căn cứ vào công thức tại `problem-definition.md` (`task.status != COMPLETED AND task.scheduled_date < TODAY`), `OVERDUE` là một **điều kiện tính toán suy diễn (Derived Condition / Computed Status)** tại thời điểm truy vấn, **không phải** là một giá trị trạng thái vòng đời bền vững (persisted lifecycle state). Vòng đời dữ liệu của Task gồm trạng thái thực hiện (`PENDING`, `COMPLETED`) kết hợp với thuộc tính lịch (`scheduled_date` có giá trị hoặc `NULL`).

```
       [AI / User tạo Task]
             │
             ▼
     ┌───────────────┐
     │    PENDING    │ <─── Trạng thái vòng đời bền vững
     └───────┬───────┘
             │
             ├── [scheduled_date < CURRENT_DATE] ──> [DERIVED: OVERDUE] (Hiển thị cảnh báo)
             │
             ├── [Tick hoàn thành]
             │
             ▼
     ┌───────────────┐
     │   COMPLETED   │ <─── Trạng thái kết thúc bền vững
     └───────────────┘
```

| Trạng thái / Thuộc tính | Hành động (Trigger) | Điều kiện Tiên quyết | Trạng thái Đích | Hành vi Hệ thống |
|---|---|---|---|---|
| *(Mới tạo)* | Sinh từ AI Proposal hoặc tạo thủ công | Proposal được Apply hoặc User thêm task | `PENDING`<br>*(scheduled)* | Gán `scheduled_date` cụ thể theo lịch trình. |
| `PENDING` *(scheduled)* | Gián đoạn phiên học (FR-SESSION-003) | Phiên học kết thúc khi task chưa tick | `PENDING`<br>*(Backlog)* | Đặt `scheduled_date = NULL`, chuyển về danh sách Backlog. |
| `PENDING` *(Backlog)* | Xếp lịch lại từ Backlog (FR-TASK-002) | User chọn ngày mới hợp lệ | `PENDING`<br>*(scheduled)* | Gán `scheduled_date` mới, đưa vào Official Schedule. |
| `PENDING` *(scheduled)* | Sang ngày mới mà chưa hoàn thành | `CURRENT_DATE > scheduled_date` | `PENDING`<br>*(Derived OVERDUE)* | Hệ thống tính toán gắn cờ hiển thị quá hạn, đưa vào hàng đợi ưu tiên. |
| `PENDING` | User tick hoàn thành (FR-TASK-001) | User bấm tick hoàn thành | `COMPLETED` | Ghi nhận `completed_at = CURRENT_TIMESTAMP`, cập nhật tiến độ. |
| `COMPLETED` | User bỏ tick hoàn thành | User bỏ chọn hoàn thành task | `PENDING` | Xóa `completed_at`, tính toán lại tiến độ tương ứng. |

### 6.3 Vòng đời Phiên học (Study Session Lifecycle)

```
     [User bấm Start Session]
                │
                ▼
      ┌──────────────────┐
      │   IN_PROGRESS    │
      └─────────┬────────┘
                │
    ┌───────────┴─────────────────────────────┐
    │ [Hết giờ / Bấm Kết thúc]                │ [Bấm Dừng sớm / Gián đoạn]
    ▼                                         ▼
┌───────────┐                         ┌───────────────────────────────────────────────┐
│ COMPLETED │                         │ [Phân định trạng thái gián đoạn]              │
└───────────┘                         │                                               │
                                      │ TH1: Có task hoàn thành HOẶC đạt ngưỡng thời  │
                                      │      gian quy định theo OS-01                 │
                                      │      ──> PARTIAL_COMPLETED                    │
                                      │                                               │
                                      │ TH2: Chưa có task xong VÀ dưới ngưỡng thời gian│
                                      │      ──> CANCELLED                            │
                                      └───────────────────────────────────────────────┘
```

| Trạng thái Nguồn | Sự kiện Kích hoạt (Trigger) | Điều kiện Tiên quyết (Preconditions) | Trạng thái Đích | Hành vi Hệ thống |
|---|---|---|---|---|
| *(Chưa bắt đầu)* | Bấm "Start Session" (FR-SESSION-001) | Chọn $\ge 1$ task có lịch trong ngày | `IN_PROGRESS` | Khởi tạo bản ghi Session, lưu `started_at = CURRENT_TIMESTAMP`, mở Study Workspace. |
| `IN_PROGRESS` | Hoàn tất phiên bình thường | Hết thời lượng dự kiến hoặc User bấm kết thúc khi đã hoàn tất các task | `COMPLETED` | Ghi nhận `ended_at`, tính tổng số phút thực học, giữ nguyên các task đã tick hoàn thành. |
| `IN_PROGRESS` | Dừng sớm / Gián đoạn có kết quả | User bấm dừng sớm HOẶC gián đoạn mạng/trình duyệt MÀ thỏa mãn: Có ít nhất 01 task đã tick `COMPLETED` HOẶC đạt thời lượng tối thiểu theo `OS-01` | `PARTIAL_COMPLETED` | Lưu số phút thực học; giữ nguyên task đã tick `COMPLETED`; chuyển toàn bộ task chưa xong về Backlog (`scheduled_date = NULL`). |
| `IN_PROGRESS` | Dừng sớm / Gián đoạn không có kết quả | User bấm dừng sớm HOẶC gián đoạn mạng/trình duyệt MÀ: Chưa có task nào `COMPLETED` VÀ thời gian học dưới ngưỡng quy định theo `OS-01` | `CANCELLED` | Lưu số phút thực học (để thống kê nỗ lực); chuyển toàn bộ task về Backlog (`scheduled_date = NULL`). |
| `COMPLETED` / `PARTIAL_COMPLETED` / `CANCELLED` | Bất kỳ hành động nào | Trạng thái phiên đã kết thúc | *Bất biến* | Không cho phép mở lại phiên học đã đóng; muốn học tiếp phải tạo phiên mới. |

### 6.4 Vòng đời Đề xuất Lịch & Lịch Chính thức (Schedule Proposal & Official Schedule Lifecycle)

```
        [AI sinh lịch Cấp 2]
                │
                ▼
     ┌──────────────────────┐
     │   PROPOSAL: DRAFT    │
     └──────────┬───────────┘
                │
        ┌───────┴────────────────────────┐
        │ [User bấm Apply & Pass Gate]   │ [User hủy / Tạo đề xuất mới]
        ▼                                ▼
┌──────────────────────┐        ┌──────────────────────┐
│  PROPOSAL: APPLIED   │        │  PROPOSAL: DISCARDED │
└──────────┬───────────┘        └──────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ TẠO / CẬP NHẬT OFFICIAL SCHEDULE:                           │
│ - Nếu chưa có Official Schedule: Lưu thành ACTIVE           │
│ - Nếu ĐÃ CÓ Official Schedule: Hành vi Replace / Merge /    │
│   Versioning tuân theo [Open Decision OS-03].               │
└─────────────────────────────────────────────────────────────┘
```

| Trạng thái Nguồn | Sự kiện Kích hoạt | Điều kiện Tiên quyết | Trạng thái Đích | Hành vi Hệ thống |
|---|---|---|---|---|
| *(Khởi tạo)* | AI sinh task Cấp 2 (FR-PLAN-002) | Milestones đã Approved, có cấu hình Availability | `PROPOSAL: DRAFT` | Hiển thị bảng xem trước (preview), cho phép chỉnh sửa task, chưa ghi vào lịch chính thức. |
| `PROPOSAL: DRAFT` | User hủy đề xuất hoặc bấm tạo lại | User bấm "Hủy" hoặc sinh lại Proposal mới | `PROPOSAL: DISCARDED` | Hủy bản đề xuất dự thảo; không làm thay đổi Official Schedule hiện hành. |
| `PROPOSAL: DRAFT` | User bấm "Apply" (FR-PLAN-003) | Vượt qua Backend Validation Gate (BUSR-03, 04, 05) | `PROPOSAL: APPLIED` | Chuyển đổi dữ liệu sang Official Schedule: nếu đã có Official Schedule thì xử lý theo `OS-03`. |

---

## 7. Yêu cầu Chức năng (Functional Requirements - FR)

### 7.1 Xác thực & Quản lý Tài khoản (FR-AUTH)

#### FR-AUTH-001: Đăng ký tài khoản Người học
- **Tiêu đề**: Đăng ký tài khoản Learner mới.
- **Mô tả**: Hệ thống phải cho phép người dùng mới đăng ký tài khoản Learner bằng địa chỉ email và mật khẩu hợp lệ.
- **Tiền điều kiện**: Người dùng chưa đăng nhập hệ thống.
- **Tác nhân kích hoạt**: Người dùng gửi biểu mẫu đăng ký.
- **Dữ liệu đầu vào**: Họ tên, Địa chỉ Email, Mật khẩu, Xác nhận mật khẩu.
- **Luồng chính**:
  1. Người dùng nhập thông tin đăng ký và bấm "Đăng ký".
  2. Hệ thống kiểm tra định dạng email và độ mạnh mật khẩu (tối thiểu 8 ký tự, gồm chữ và số).
  3. Hệ thống kiểm tra tính duy nhất của email trong cơ sở dữ liệu.
  4. Hệ thống băm mật khẩu bằng thuật toán an toàn (tuân thủ NFR-SEC-002), khởi tạo bản ghi User với phân tầng mặc định là `FREE`, cấp hạn ngạch ban đầu theo `OS-02`.
  5. Hệ thống tạo phiên đăng nhập an toàn và chuyển hướng người dùng đến luồng Onboarding.
- **Luồng thay thế**: Không có.
- **Luồng ngoại lệ**:
  - *Email đã tồn tại*: Hệ thống từ chối tạo tài khoản, trả về thông báo lỗi: *"Email đã được sử dụng"*.
  - *Mật khẩu không đạt chuẩn*: Hệ thống từ chối tạo tài khoản, hiển thị yêu cầu về độ mạnh mật khẩu.
- **Hậu điều kiện**: Bản ghi User mới được lưu trữ; token xác thực phiên được cấp cho client.
- **Tiêu chí chấp nhận**:
  - Không cho phép tạo 2 tài khoản trùng email.
  - 100% mật khẩu được băm trước khi lưu cơ sở dữ liệu.
- **Phương pháp kiểm chứng**: Kiểm thử tự động (Integration Test) kiểm tra tính duy nhất của email và kiểm tra trực tiếp bảng dữ liệu không chứa mật khẩu thô.
- **Truy vết**: BR-005, BUSR-01, NFR-SEC-002.

#### FR-AUTH-002: Đăng nhập & Xác thực phiên làm việc
- **Tiêu đề**: Đăng nhập và quản lý phiên làm việc.
- **Mô tả**: Hệ thống phải xác thực thông tin đăng nhập của Learner và cấp phiên làm việc an toàn.
- **Tiền điều kiện**: Tài khoản đã được tạo trên hệ thống.
- **Tác nhân kích hoạt**: Learner gửi biểu mẫu đăng nhập.
- **Dữ liệu đầu vào**: Địa chỉ Email, Mật khẩu.
- **Luồng chính**:
  1. Learner nhập email, mật khẩu và bấm "Đăng nhập".
  2. Hệ thống tìm kiếm tài khoản theo email, đối soát mã băm mật khẩu.
  3. Hệ thống xác thực thành công, cấp token phiên làm việc an toàn (Session Token / JWT).
  4. Hệ thống trả về thông tin định danh và chuyển hướng người dùng tới Dashboard.
- **Luồng ngoại lệ**:
  - *Sai email hoặc mật khẩu*: Hệ thống trả về thông báo lỗi chung: *"Thông tin đăng nhập không chính xác"*, không tiết lộ trường cụ thể để phòng chống quét tài khoản.
- **Hậu điều kiện**: Phiên đăng nhập được thiết lập; mọi request nghiệp vụ tiếp theo đều mang định danh người dùng.
- **Tiêu chí chấp nhận**: Xác thực thành công cấp token hợp lệ; từ chối truy cập khi sai thông tin.
- **Phương pháp kiểm chứng**: Unit Test và API Integration Test.
- **Truy vết**: BR-005, BUSR-01, NFR-SEC-001.

---

### 7.2 Thiết lập Mục tiêu & Thu thập Ngữ cảnh (FR-GOAL)

#### FR-GOAL-001: Nhập mục tiêu học tập ban đầu
- **Tiêu đề**: Thu thập mục tiêu học tập ban đầu.
- **Mô tả**: Hệ thống phải cho phép Learner đã đăng nhập nhập mục tiêu học tập tự do kèm thời hạn mong muốn.
- **Tiền điều kiện**: Learner đã xác thực thành công phiên làm việc.
- **Tác nhân kích hoạt**: Learner gửi mục tiêu học tập.
- **Dữ liệu đầu vào**: Chuỗi mô tả mục tiêu (chuỗi ký tự), Ngày hoàn thành mong muốn (Target Date).
- **Luồng chính**:
  1. Learner nhập mô tả mục tiêu và thời hạn vào giao diện Onboarding / Tạo mới lộ trình.
  2. Hệ thống kiểm tra độ dài văn bản mục tiêu (tối thiểu 10 ký tự, tối đa 500 ký tự) và kiểm tra ngày mục tiêu phải ở tương lai (`TargetDate > CURRENT_DATE`).
  3. Hệ thống lưu bản ghi Goal tạm thời gắn liền với `user_id` và chuyển tiếp sang bước AI làm rõ ngữ cảnh.
- **Luồng ngoại lệ**:
  - *Mục tiêu rỗng hoặc quá ngắn*: Hệ thống hiển thị cảnh báo yêu cầu mô tả rõ hơn.
  - *Ngày mục tiêu ở quá khứ*: Hệ thống yêu cầu chọn ngày trong tương lai.
- **Hậu điều kiện**: Bản ghi Goal được tạo ở trạng thái `INITIALIZED`.
- **Tiêu chí chấp nhận**: Ghi nhận chính xác mục tiêu của đúng người dùng đã đăng nhập.
- **Phương pháp kiểm chứng**: Kiểm thử giao diện và kiểm thử dữ liệu API.
- **Truy vết**: BR-001, BUSR-01.

#### FR-GOAL-002: Tương tác hỏi-đáp làm rõ ngữ cảnh với AI (AI Clarification)
- **Tiêu đề**: Đối thoại làm rõ ngữ cảnh với AI.
- **Mô tả**: Hệ thống phải hỗ trợ luồng đối thoại có cấu trúc để AI đặt câu hỏi làm rõ trình độ hiện tại, phong cách học và mức độ chuyên sâu mong muốn.
- **Tiền điều kiện**: Goal đã được khởi tạo; tài khoản còn hạn ngạch AI (tuân thủ FR-QUOTA-001).
- **Tác nhân kích hoạt**: Hệ thống tự động chuyển tiếp sau khi Goal được nhập.
- **Dữ liệu đầu vào**: Câu trả lời của Learner cho các câu hỏi gợi ý từ AI.
- **Luồng chính**:
  1. Backend gửi prompt kèm thông tin Goal đến External LLM Provider yêu cầu sinh 2–3 câu hỏi định hình năng lực.
  2. Hệ thống hiển thị các câu hỏi cho Learner dưới dạng trắc nghiệm hoặc nhập liệu ngắn.
  3. Learner chọn hoặc nhập câu trả lời và bấm "Tiếp tục".
  4. Hệ thống tổng hợp câu trả lời vào hồ sơ ngữ cảnh của Goal để chuẩn bị cho giai đoạn sinh Milestone.
- **Luồng ngoại lệ**:
  - *AI gặp lỗi hoặc timeout*: Kích hoạt cơ chế Fallback (FR-AI-002), cho phép bỏ qua bước làm rõ để sinh kế hoạch cơ bản hoặc lập kế hoạch thủ công.
- **Hậu điều kiện**: Goal được cập nhật ngữ cảnh bổ sung, sẵn sàng cho việc phân rã Milestones.
- **Tiêu chí chấp nhận**: Hoàn tất trao đổi trong giới hạn thời gian NFR-PERF-001; cung cấp đường thoát manual plan khi có lỗi.
- **Phương pháp kiểm chứng**: Mock LLM Service Integration Test.
- **Truy vết**: BR-001, BUSR-10, NFR-PERF-001.

---

### 7.3 Khởi tạo Kế hoạch & Duyệt 2 cấp độ bằng AI (FR-PLAN)

#### FR-PLAN-001: Sinh và Phê duyệt Cột mốc tổng quan (Milestones - Cấp 1)
- **Tiêu đề**: Phân rã và phê duyệt Milestones Cấp 1.
- **Mô tả**: Hệ thống phải yêu cầu AI sinh danh sách các cột mốc kiến thức (Milestones) tổng quan, hiển thị cho Learner xem xét, chỉnh sửa và bấm duyệt.
- **Tiền điều kiện**: Goal đã thu thập đủ ngữ cảnh; tài khoản còn hạn ngạch AI.
- **Tác nhân kích hoạt**: Learner xác nhận hoàn tất bước làm rõ ngữ cảnh.
- **Dữ liệu đầu vào**: Thông tin Goal và ngữ cảnh người học.
- **Luồng chính**:
  1. Backend gửi yêu cầu đến External LLM với schema định sẵn yêu cầu sinh danh sách 3–7 Milestones tuần tự.
  2. Backend kiểm tra schema kết quả trả về từ AI (Validation Gate, tuân thủ FR-AI-001).
  3. Giao diện hiển thị danh sách Milestones cho Learner.
  4. Learner có quyền: thêm mới, sửa đổi tên/mô tả/thứ tự, hoặc xóa bớt Milestone.
  5. Learner bấm "Duyệt Milestones (Approve Milestones)".
  6. Hệ thống lưu danh sách Milestones đã duyệt gắn liền với Roadmap.
- **Luồng ngoại lệ**:
  - *AI trả về sai cấu trúc*: Tự động thử lại tối đa 2 lần theo FR-AI-001; nếu kiệt số lần, cho phép tạo thủ công.
- **Hậu điều kiện**: Roadmap được khởi tạo với danh sách Milestones ở trạng thái `APPROVED`.
- **Tiêu chí chấp nhận**: Hệ thống không bao giờ tự động sinh task chi tiết nếu Learner chưa bấm duyệt Milestones.
- **Phương pháp kiểm chứng**: End-to-end Automated Test.
- **Truy vết**: BR-001, BUSR-02, NFR-AI-001.

#### FR-PLAN-002: Sinh Đề xuất Lịch trình chi tiết (Schedule Proposal - Cấp 2)
- **Tiêu đề**: Sinh Đề xuất Lịch trình chi tiết (Schedule Proposal).
- **Mô tả**: Dựa trên Milestones đã duyệt và cấu hình Availability của Learner, hệ thống phải yêu cầu AI phân rã thành các Tasks chi tiết và xếp vào một Schedule Proposal.
- **Tiền điều kiện**: Milestones đã ở trạng thái `APPROVED`; Learner đã có cấu hình Availability hợp lệ.
- **Tác nhân kích hoạt**: Learner bấm "Tạo Đề xuất Lịch trình".
- **Dữ liệu đầu vào**: Danh sách Milestones đã duyệt, Cấu hình Availability của Learner, Thời hạn mục tiêu.
- **Luồng chính**:
  1. Backend tính toán các khoảng thời gian trống theo cấu hình Availability và quỹ thời gian đã cam kết của các Roadmap khác (BUSR-05).
  2. Backend gửi prompt kèm schema nghiêm ngặt đến External LLM để phân rã mỗi Milestone thành các task cụ thể (thời lượng dự kiến từ 30–120 phút).
  3. Backend nhận kết quả, ánh xạ các task vào các khung thời gian khả dụng để tạo thành đối tượng `Schedule Proposal` ở trạng thái `DRAFT`.
  4. Hệ thống hiển thị Schedule Proposal dưới dạng bảng lịch trực quan cho Learner xem xét.
- **Luồng ngoại lệ**:
  - *Thời gian xử lý vượt quá 55 giây*: Backend kích hoạt ngắt cứng (FR-AI-002), trả về mã lỗi cấu trúc.
- **Hậu điều kiện**: Schedule Proposal được tạo ở trạng thái `DRAFT`, chưa ghi vào Official Schedule.
- **Tiêu chí chấp nhận**: Nhãn trạng thái hiển thị rõ là "Bản đề xuất (Proposal)"; dữ liệu chưa được lưu vào Official Schedule.
- **Phương pháp kiểm chứng**: Database assertion và UI test kiểm tra không có bản ghi mới trong bảng Official Schedule.
- **Truy vết**: BR-001, BUSR-02, BUSR-03, NFR-PERF-001.

#### FR-PLAN-003: Xem xét, Chỉnh sửa và Áp dụng Lịch trình (Apply Schedule Proposal)
- **Tiêu đề**: Xem xét, chỉnh sửa và áp dụng Lịch trình chính thức.
- **Mô tả**: Hệ thống phải cho phép Learner chỉnh sửa các task trên Schedule Proposal và chủ động bấm nút "Apply" để kích hoạt Backend Validation Gate chuyển đổi thành Official Schedule.
- **Tiền điều kiện**: Schedule Proposal đang hiển thị ở trạng thái `DRAFT`.
- **Tác nhân kích hoạt**: Learner bấm nút "Apply Lịch trình".
- **Dữ liệu đầu vào**: Danh sách task trên Proposal (đã chỉnh sửa nếu có).
- **Luồng chính**:
  1. Learner thực hiện chỉnh sửa tùy chọn trên giao diện Proposal (đổi ngày, đổi thời lượng, đổi vị trí, xóa task).
  2. Learner bấm nút "Apply".
  3. **Backend Validation Gate** tiến hành kiểm tra:
     - Xác thực quyền sở hữu Roadmap của người dùng (`user_id`).
     - Kiểm tra tổng thời lượng task trong từng ngày so với Availability Mode A/Mode B (BUSR-03).
     - Kiểm tra quy tắc Soft Overflow nếu có task tràn biên (BUSR-04).
     - Kiểm tra xung đột với Official Schedule hiện có của các Roadmap khác (BUSR-05).
  4. Khi toàn bộ kiểm tra hợp lệ:
     - Nếu đây là lần áp dụng đầu tiên cho Roadmap: Hệ thống lưu trữ thành Official Schedule với trạng thái Roadmap là `ACTIVE`.
     - Nếu Roadmap **đã có Official Schedule đang hoạt động**: Cơ chế xử lý (Replace, Merge, hay Versioning) **phải tuân theo Quyết định Mở OS-03 của Product Owner**. Hệ thống thực thi theo chính sách được Product Owner phê duyệt mà không tự ý áp đặt một giải pháp kỹ thuật ngầm định.
  5. Hệ thống gửi thông báo thành công và chuyển hướng người dùng về màn hình Lịch học chính thức.
- **Luồng thay thế (Xác nhận Soft Overflow)**:
  - Nếu task cuối cùng trong ngày vượt quá khung giờ từ 1–30 phút: Hệ thống hiển thị hộp thoại cảnh báo: *"Task cuối ngày vượt quá khung giờ rảnh X phút. Bạn có đồng ý tiếp tục?"*. Nếu Learner bấm đồng ý, hệ thống tiếp tục lưu trữ; nếu từ chối, giữ nguyên màn hình chỉnh sửa.
- **Luồng ngoại lệ**:
  - *Vi phạm giới hạn thời gian rảnh*: Backend từ chối lưu trữ, trả về mã lỗi `VALIDATION_OVERLOAD` kèm danh sách ngày bị quá tải để người dùng điều chỉnh lại.
- **Hậu điều kiện**: Schedule Proposal chuyển sang `APPLIED`; Official Schedule được lưu trữ bền vững.
- **Tiêu chí chấp nhận**: Không có bất kỳ lịch trình vi phạm thời gian rảnh nào được ghi vào Official Schedule; thao tác hoàn tất trong $\le 500$ ms.
- **Phương pháp kiểm chứng**: Automated Integration Tests với các kịch bản hợp lệ, quá tải, và tràn giờ mềm.
- **Truy vết**: BR-001, BUSR-02, BUSR-03, BUSR-04, BUSR-05, OS-03.

#### FR-PLAN-004: Tự tạo Lập kế hoạch Thủ công (Fallback Manual Plan)
- **Tiêu đề**: Lập kế hoạch học tập thủ công.
- **Mô tả**: Khi gặp sự cố với AI hoặc khi người dùng có nhu cầu tự chủ, hệ thống phải cung cấp giao diện cho phép tự tạo Milestone và tự thêm Task thủ công vào lịch trình mà không cần gọi AI.
- **Tiền điều kiện**: Learner đã đăng nhập hệ thống.
- **Tác nhân kích hoạt**: Learner chọn nút "Tạo kế hoạch thủ công" (từ màn hình lỗi AI hoặc menu tạo Roadmap).
- **Dữ liệu đầu vào**: Tên Milestone, Tên Task, Ngày học, Thời lượng dự kiến.
- **Luồng chính**:
  1. Learner nhập thông tin Milestone và thêm các Task trực tiếp vào lịch.
  2. Learner bấm "Lưu Lịch trình".
  3. Backend thực hiện Validation Gate kiểm tra Availability tương tự luồng chuẩn.
  4. Lưu trữ thành Official Schedule (xử lý lịch hiện có tuân thủ `OS-03`).
- **Hậu điều kiện**: Official Schedule được tạo mà không tiêu tốn hạn ngạch AI.
- **Tiêu chí chấp nhận**: Hệ thống hoạt động trơn tru ngay cả khi ngắt toàn bộ kết nối đến External LLM.
- **Phương pháp kiểm chứng**: Integration Test ngắt kết nối mạng ngoại vi (offline mock).
- **Truy vết**: BR-001, NFR-AVAIL-001.

---

### 7.4 Cấu hình Thời gian rảnh Lai (FR-AVAIL)

#### FR-AVAIL-001: Cấu hình Thời gian rảnh Chế độ A — Daily Hours Quota
- **Tiêu đề**: Cấu hình Thời gian rảnh Chế độ A (Quỹ giờ mỗi ngày).
- **Mô tả**: Hệ thống phải cho phép Learner thiết lập số giờ rảnh tối đa cho từng ngày trong tuần (Thứ Hai đến Chủ Nhật).
- **Tiền điều kiện**: Learner đã đăng nhập.
- **Tác nhân kích hoạt**: Learner gửi biểu mẫu cấu hình Mode A.
- **Dữ liệu đầu vào**: Số giờ rảnh cho từng ngày trong tuần. Ngưỡng giá trị hợp lệ (cận dưới và cận trên) **tuân theo Quyết định Mở OS-06**.
- **Luồng chính**:
  1. Learner chọn "Chế độ A — Quỹ giờ mỗi ngày" trên trang cài đặt Availability.
  2. Learner điền số giờ rảnh cho từng ngày trong tuần.
  3. Learner bấm "Lưu cấu hình".
  4. Hệ thống kiểm tra giá trị nằm trong khoảng hợp lệ theo quy định của `OS-06` và lưu vào hồ sơ người dùng.
- **Luồng ngoại lệ**:
  - *Giá trị ngoài khoảng hợp lệ*: Hệ thống từ chối lưu, hiển thị thông báo giới hạn giờ theo quy định của `OS-06`.
- **Hậu điều kiện**: Cấu hình Availability Mode A được kích hoạt làm căn cứ phân bổ task.
- **Tiêu chí chấp nhận**: Tổng thời lượng task được xếp trong ngày không được vượt quá số giờ rảnh đã cấu hình cho ngày đó.
- **Phương pháp kiểm chứng**: Unit Test kiểm tra tính hợp lệ của dải dữ liệu và thuật toán kiểm tra trần thời gian.
- **Truy vết**: BUSR-03, OS-06.

#### FR-AVAIL-002: Cấu hình Thời gian rảnh Chế độ B — Time Slot Window
- **Tiêu đề**: Cấu hình Thời gian rảnh Chế độ B (Khung giờ cố định).
- **Mô tả**: Hệ thống phải cho phép Learner thiết lập các khung giờ rảnh cố định (bắt đầu - kết thúc) theo từng ngày trong tuần.
- **Tiền điều kiện**: Learner đã đăng nhập.
- **Tác nhân kích hoạt**: Learner gửi biểu mẫu cấu hình Mode B.
- **Dữ liệu đầu vào**: Danh sách các khoảng thời gian `[StartTime, EndTime]` cho từng ngày trong tuần (Ví dụ: Thứ 2 từ 19:00 đến 21:00).
- **Luồng chính**:
  1. Learner chọn "Chế độ B — Khung giờ cố định".
  2. Learner thêm các khung giờ rảnh cho từng ngày.
  3. Hệ thống kiểm tra: `StartTime < EndTime`, các khung giờ trong cùng một ngày không được chồng lấn nhau.
  4. Learner bấm "Lưu cấu hình".
  5. Hệ thống lưu cấu hình Mode B vào hồ sơ người dùng.
- **Luồng ngoại lệ**:
  - *Khung giờ không hợp lệ hoặc chồng lấn*: Hệ thống từ chối lưu, hiển thị thông báo lỗi cụ thể.
- **Hậu điều kiện**: Cấu hình Availability Mode B được kích hoạt; các task được xếp sẽ có giờ bắt đầu và kết thúc cụ thể.
- **Tiêu chí chấp nhận**: Hệ thống từ chối lưu khung giờ nếu thời gian kết thúc trước hoặc bằng thời gian bắt đầu.
- **Phương pháp kiểm chứng**: Unit Test kiểm tra logic không chồng lấn khung giờ (Interval Overlap Check).
- **Truy vết**: BUSR-03, BUSR-04.

#### FR-AVAIL-003: Quản lý Năng lực Đa Lộ trình (Multi-Roadmap Capacity Management)
- **Tiêu đề**: Quản trị dung lượng thời gian rảnh đa lộ trình.
- **Mô tả**: Hệ thống phải tính toán dung lượng thời gian rảnh khả dụng thực tế bằng cách lấy tổng thời gian rảnh trừ đi thời gian đã phân bổ cho các Official Schedule hiện có trước khi xếp lịch mới.
- **Tiền điều kiện**: Learner sở hữu ít nhất một Roadmap đang ở trạng thái `ACTIVE`.
- **Tác nhân kích hoạt**: Yêu cầu tạo lịch hoặc cập nhật lịch cho một Roadmap mới/khác.
- **Luồng chính**:
  1. Hệ thống truy vấn toàn bộ các task thuộc Official Schedule của tất cả Roadmap đang hoạt động của Learner.
  2. Xác định các khoảng thời gian đã bị chiếm dụng trên từng ngày.
  3. Trả về tập hợp các khoảng thời gian rảnh còn lại (Remaining Available Slots) cho Planning Engine.
  4. Trường hợp có xung đột cạnh tranh khoảng thời gian trống giữa các lộ trình, hệ thống áp dụng nguyên tắc ưu tiên theo quy định tại `OS-04`.
- **Hậu điều kiện**: Lộ trình mới chỉ được xếp vào các khoảng thời gian chưa có cam kết học tập trước đó.
- **Tiêu chí chấp nhận**: Tuyệt đối không tự ý xếp trùng giờ giữa 2 task thuộc 2 Roadmap khác nhau của cùng một Learner.
- **Phương pháp kiểm chứng**: Automated Integration Test với 2 Roadmap chạy song song.
- **Truy vết**: BUSR-05, OS-04.

---

### 7.5 Quản lý Lịch trình Chính thức (FR-SCHEDULE)

#### FR-SCHEDULE-001: Hiển thị Lịch trình Học tập Chính thức
- **Tiêu đề**: Hiển thị Lịch trình Học tập Chính thức.
- **Mô tả**: Hệ thống phải hiển thị toàn bộ các task thuộc Official Schedule theo chế độ xem ngày, tuần và danh sách theo Milestone.
- **Tiền điều kiện**: Learner có ít nhất một Roadmap đã có Official Schedule.
- **Tác nhân kích hoạt**: Learner truy cập trang Lịch trình (Schedule View).
- **Luồng chính**:
  1. Hệ thống truy vấn các task chính thức của Learner theo khoảng thời gian được chọn.
  2. Hiển thị trực quan: Tên task, thời lượng, khung giờ (nếu Mode B), trạng thái (`PENDING`, `COMPLETED`, và gắn cờ cảnh báo nếu thỏa mãn điều kiện `OVERDUE`).
  3. Đánh dấu rõ các task thuộc các Roadmap khác nhau bằng màu sắc nhận diện.
- **Hậu điều kiện**: Giao diện hiển thị trực quan, hỗ trợ tương tác nhanh.
- **Tiêu chí chấp nhận**: Tải dữ liệu lịch trình hiển thị hoàn tất trong vòng $\le 500$ ms (NFR-PERF-002).
- **Phương pháp kiểm chứng**: Performance testing đo thời gian render client và latency API backend.
- **Truy vết**: BR-002, NFR-PERF-002.

---

### 7.6 Quản trị Task & Hàng đợi Backlog (FR-TASK)

#### FR-TASK-001: Cập nhật Trạng thái Task Hoàn thành
- **Tiêu đề**: Cập nhật trạng thái hoàn thành task.
- **Mô tả**: Hệ thống phải cho phép Learner đánh dấu hoàn thành (tick checkbox) cho một task trực tiếp từ giao diện Lịch trình hoặc từ Study Workspace.
- **Tiền điều kiện**: Task tồn tại và thuộc quyền sở hữu của Learner (`user_id == resource.user_id`).
- **Tác nhân kích hoạt**: Learner bấm tick chọn hoàn thành task.
- **Luồng chính**:
  1. Learner bấm vào ô trạng thái của task.
  2. Hệ thống cập nhật trạng thái `task.status = COMPLETED` và ghi nhận `completed_at = CURRENT_TIMESTAMP`.
  3. Giao diện cập nhật trạng thái gạch ngang hoàn thành ngay lập tức trong vòng $\le 500$ ms (Optimistic UI).
  4. Hệ thống tính toán lại tiến độ phần trăm của Milestone và Roadmap tương ứng.
- **Luồng thay thế**: Nếu Learner bấm bỏ tick, hệ thống cập nhật `task.status = PENDING`, đặt `completed_at = NULL` và tính lại tiến độ.
- **Hậu điều kiện**: Dữ liệu task được lưu trạng thái hoàn thành bền vững.
- **Tiêu chí chấp nhận**: Trạng thái hoàn thành được đồng bộ tức thì trên toàn bộ các view liên quan.
- **Phương pháp kiểm chứng**: Automated UI and API Test.
- **Truy vết**: BR-002, NFR-PERF-002.

#### FR-TASK-002: Quản trị Hàng đợi Backlog
- **Tiêu đề**: Quản trị hàng đợi công việc tồn đọng (Backlog).
- **Mô tả**: Hệ thống phải duy trì danh sách Backlog lưu trữ các task chưa được xếp lịch cụ thể (`scheduled_date == NULL`) hoặc các task bị tồn đọng do phiên học gián đoạn.
- **Tiền điều kiện**: Task thuộc quyền sở hữu của Learner.
- **Tác nhân kích hoạt**: Dừng phiên học sớm hoặc người dùng chuyển task về Backlog.
- **Luồng chính**:
  1. Hệ thống cập nhật `task.scheduled_date = NULL`, đưa task vào danh sách Backlog của Roadmap tương ứng.
  2. Hiển thị danh sách Backlog ở bảng quản lý task.
  3. Cho phép Learner chọn ngày để xếp lịch lại cho task từ Backlog vào Official Schedule khi có thời gian rảnh.
- **Hậu điều kiện**: Task được bảo toàn toàn vẹn dữ liệu, không bị thất lạc.
- **Tiêu chí chấp nhận**: Mọi task chưa hoàn thành từ phiên học gián đoạn đều xuất hiện đầy đủ trong Backlog.
- **Phương pháp kiểm chứng**: Integration Test kiểm tra luồng gián đoạn phiên học và kiểm tra danh sách Backlog.
- **Truy vết**: BUSR-09, Mục 6.2 State Transition.

---

### 7.7 Không gian Thực thi Phiên học & Phục hồi (FR-SESSION)

#### FR-SESSION-001: Khởi động Phiên học Tập trung (Active Study Workspace)
- **Tiêu đề**: Khởi động phiên học tập trung.
- **Mô tả**: Hệ thống phải cung cấp không gian Study Workspace chuyên biệt khi Learner bắt đầu buổi học, tích hợp đầy đủ: Task Checklist, Đồng hồ bấm giờ Pomodoro/Stopwatch, Scratchpad và Key Takeaways.
- **Tiền điều kiện**: Learner có các task được lên lịch trong ngày hiện tại.
- **Tác nhân kích hoạt**: Learner bấm nút "Bắt đầu buổi học (Start Session)".
- **Dữ liệu đầu vào**: Danh sách task chọn học trong phiên.
- **Luồng chính**:
  1. Learner chọn $\ge 1$ task cần giải quyết và bấm "Start Session".
  2. Hệ thống khởi tạo bản ghi Session ở trạng thái `IN_PROGRESS`, ghi nhận `started_at = CURRENT_TIMESTAMP`.
  3. Màn hình chuyển sang chế độ tập trung (Study Workspace) hiển thị:
     - Danh sách kiểm tra task (Task Checklist) cho phép tick hoàn thành.
     - Bộ công cụ thời gian: Bộ đếm Pomodoro (mặc định 25 phút học / 5 phút nghỉ) hoặc Đồng hồ đếm xuôi (Stopwatch).
     - Bảng ghi chú nhanh (Scratchpad) để chép nháp code, liên kết, công thức.
     - Ô đúc kết bài học (Key Takeaways).
- **Hậu điều kiện**: Phiên học được kích hoạt và đồng bộ thời gian thực.
- **Tiêu chí chấp nhận**: Giao diện tập trung khởi động trong $\le 500$ ms; hiển thị đúng danh sách task đã chọn.
- **Phương pháp kiểm chứng**: Automated UI Test.
- **Truy vết**: BR-002, Mục 6.3 State Transition.

#### FR-SESSION-002: Tự động Lưu trữ Ghi chú Scratchpad & Key Takeaways
- **Tiêu đề**: Lưu trữ ghi chú phiên học.
- **Mô tả**: Hệ thống phải tự động lưu định kỳ các ghi chú thô trong Scratchpad và bắt buộc lưu Key Takeaways khi kết thúc phiên.
- **Tiền điều kiện**: Phiên học đang ở trạng thái `IN_PROGRESS`.
- **Tác nhân kích hoạt**: Learner nhập văn bản vào Scratchpad hoặc Key Takeaways.
- **Luồng chính**:
  1. Khi Learner gõ nội dung vào Scratchpad, hệ thống tự động lưu sau mỗi 3 giây không có thao tác phím (debounce 3s).
  2. Khi chuẩn bị kết thúc phiên, giao diện nhắc nhở người học điền 1–2 câu tóm tắt cốt lõi vào ô Key Takeaways.
  3. Hệ thống lưu nội dung ghi chú gắn liền với bản ghi Session.
- **Hậu điều kiện**: Ghi chú được lưu trữ bền vững, dùng làm dữ liệu đầu vào cho AI Review sau này.
- **Tiêu chí chấp nhận**: Không bị mất dữ liệu ghi chú ngay cả khi người dùng tải lại trang.
- **Phương pháp kiểm chứng**: Unit Test và E2E persistence test.
- **Truy vết**: BR-002.

#### FR-SESSION-003: Xử lý Gián đoạn & Phục hồi Phiên học (Session Interruption & Recovery)
- **Tiêu đề**: Xử lý gián đoạn và phục hồi phiên học.
- **Mô tả**: Khi phiên học bị gián đoạn (do người dùng dừng sớm, mất kết nối mạng, tải lại trang hoặc đóng trình duyệt), hệ thống phải bảo toàn số phút thực học đã trôi qua, giữ nguyên trạng thái các task đã hoàn thành, chuyển các task chưa xong về Backlog và xác định trạng thái phiên học theo quy tắc tiền định.
- **Tiền điều kiện**: Phiên học đang ở trạng thái `IN_PROGRESS`.
- **Tác nhân kích hoạt**: Learner bấm "Dừng phiên học sớm" HOẶC hệ thống phát hiện mất kết nối/đóng phiên bất thường.
- **Dữ liệu đầu vào**: Thời điểm bắt đầu `started_at`, Thời điểm gián đoạn/kết thúc `interrupted_at`, Danh sách task trong phiên.
- **Luồng chính (Dừng sớm chủ động)**:
  1. Learner bấm nút dừng phiên học sớm.
  2. Hệ thống tính toán thời gian thực tế đã trôi qua: `actual_duration_minutes = (CURRENT_TIMESTAMP - session.started_at)`.
  3. Hệ thống ghi nhận số phút thực học vào bản ghi Session và cộng dồn vào thống kê học tập.
  4. Hệ thống giữ nguyên trạng thái `COMPLETED` cho các task đã được tick trong phiên.
  5. Đối với các task chưa hoàn thành: Hệ thống tự động chuyển về hàng đợi Backlog (`scheduled_date = NULL`).
  6. **Quy tắc phân định trạng thái phiên gián đoạn (Deterministic Outcome)**:
     - Nếu có ít nhất 01 task đã được tick `COMPLETED` HOẶC đạt ngưỡng thời lượng theo quy định tại `OS-01`: Hệ thống cập nhật `session.status = PARTIAL_COMPLETED`.
     - Nếu chưa có task nào hoàn thành VÀ dưới ngưỡng thời lượng theo quy định tại `OS-01`: Hệ thống cập nhật `session.status = CANCELLED`.
     *(Lưu ý: Ngưỡng tỷ lệ thời gian cụ thể là quyết định mở do Product Owner xác nhận tại `OS-01`)*.
  7. Hiển thị tóm tắt phiên học và thông báo task dở dang đã về Backlog an toàn.
- **Luồng phục hồi khi sự cố bất thường (Browser Crash / Tab Close / Disconnect / Refresh)**:
  - *Browser Refresh / Tab Close / Reconnect*: Khi Learner tải lại trang hoặc mở lại hệ thống trong khi Session vẫn ở trạng thái `IN_PROGRESS`, hệ thống khôi phục giao diện Study Workspace, tính lại thời gian đã trôi qua dựa trên `started_at` và tiếp tục đếm giờ.
  - *Duplicate Resume*: Nếu người học mở đồng thời Study Workspace trên nhiều tab/thiết bị cho cùng một Session, hệ thống chỉ cho phép phiên hoạt động trên tab kích hoạt sau cùng và hiển thị thông báo trên các tab cũ để tránh trùng lặp đếm giờ.
  - *Thời gian học được chốt*: Trường hợp phiên học bị bỏ quên hoặc ngắt kết nối kéo dài vượt quá thời lượng dự kiến, hệ thống tự động đóng phiên học tại mốc kết thúc dự kiến và áp dụng quy tắc phân định trạng thái như trên. Cơ chế đồng bộ nhịp thời gian chi tiết tuân theo quyết định mở `OS-07`.
- **Hậu điều kiện**: Số phút thực học được lưu chính xác; không mất trạng thái task đã hoàn thành; task chưa xong nằm an toàn trong Backlog.
- **Tiêu chí chấp nhận**:
  - Không mất dữ liệu số phút thực học đã trôi qua.
  - Task đã tick giữ nguyên `COMPLETED`; task dở dang về Backlog.
  - Trạng thái kết thúc phiên tuân thủ nghiêm ngặt logic của `OS-01`.
- **Phương pháp kiểm chứng**: Automated integration tests mô phỏng hủy sớm, ngắt mạng và tải lại trang.
- **Truy vết**: BR-002, BUSR-09, Mục 6.3 State Transition, OS-01, OS-07.

---

### 7.8 Cơ chế Thích ứng khi Quá hạn (FR-ADAPT)

#### FR-ADAPT-001: Quét Phát hiện Task Quá hạn Bằng Logic Tất định
- **Tiêu đề**: Quét phát hiện task quá hạn bằng logic tất định.
- **Mô tả**: Hệ thống phải tự động quét và đánh dấu điều kiện quá hạn cho các task chưa hoàn thành có ngày học trong quá khứ bằng logic tất định thuần túy phía Backend mà không sử dụng AI.
- **Tiền điều kiện**: Có task tồn tại trong hệ thống.
- **Tác nhân kích hoạt**: Sự kiện chuyển ngày mới (00:00 hàng ngày) hoặc khi Learner truy cập trang Lịch trình.
- **Luồng chính**:
  1. Backend thực thi truy vấn tìm kiếm các task thỏa mãn điều kiện toán học:
     $$\text{task.status} \neq \text{'COMPLETED'} \quad \land \quad \text{task.scheduled\_date} < \text{CURRENT\_DATE}$$
  2. Hệ thống gán nhãn hiển thị `OVERDUE` cho các task này trên giao diện và đưa vào danh sách "Task Cần Chú Ý (Needs Attention)" của Learner.
  3. Hệ thống hiển thị các tùy chọn hành động cho Learner: tự dời lịch thủ công hoặc bấm nhờ AI gợi ý sắp xếp lại.
- **Hậu điều kiện**: Các task quá hạn được định danh minh bạch, không làm thay đổi trạng thái lifecycle bền vững của task.
- **Tiêu chí chấp nhận**: Phát hiện chính xác 100% các task quá hạn theo công thức; hoàn toàn không gọi LLM trong quá trình phát hiện.
- **Phương pháp kiểm chứng**: Unit Test với các mốc ngày giả lập (Mock System Time).
- **Truy vết**: BR-003, BUSR-06, Mục 6.2 State Transition.

#### FR-ADAPT-002: Tùy chọn Nhờ AI Sắp xếp lại Độ ưu tiên (Optional AI Reprioritization)
- **Tiêu đề**: Tùy chọn AI sắp xếp lại danh sách task tồn đọng.
- **Mô tả**: Hệ thống chỉ được phép gọi AI để phân tích và gợi ý lại thứ tự ưu tiên cho danh sách task tồn đọng khi và chỉ khi Learner chủ động bấm yêu cầu.
- **Tiền điều kiện**: Có ít nhất một task ở điều kiện quá hạn hoặc tồn đọng; Learner còn hạn ngạch AI.
- **Tác nhân kích hoạt**: Learner bấm nút "Nhờ AI sắp xếp lại (AI Reprioritize)".
- **Dữ liệu đầu vào**: Danh sách các task tồn đọng, Thời gian rảnh còn lại trong các ngày tới.
- **Luồng chính**:
  1. Learner bấm nút "Nhờ AI sắp xếp lại".
  2. Backend tổng hợp danh sách task tồn đọng và quỹ thời gian rảnh tương lai của Learner gửi đến External LLM.
  3. AI phân tích độ phụ thuộc kiến thức và đề xuất thứ tự ưu tiên mới cùng phương án xếp lịch bù dưới dạng Schedule Proposal mới.
  4. Hệ thống hiển thị bản đề xuất sắp xếp lại cho Learner xem xét.
  5. Learner có quyền chỉnh sửa và bấm "Áp dụng Lịch mới".
  6. Backend kiểm tra Validation Gate và cập nhật lại Official Schedule (theo quy định tại `OS-03`).
- **Luồng ngoại lệ**:
  - *Learner không bấm yêu cầu*: Hệ thống tuyệt đối không tự động gọi AI.
- **Hậu điều kiện**: Lịch trình được tái cấu trúc thích ứng theo sự chủ động của người học.
- **Tiêu chí chấp nhận**: Phân tách hoàn toàn giữa phát hiện quá hạn (tất định) và sắp xếp lại (tùy chọn bởi người dùng).
- **Phương pháp kiểm chứng**: Automated E2E Test kiểm tra request mạng ngoại vi chỉ phát sinh sau thao tác click của User.
- **Truy vết**: BR-003, BUSR-02, BUSR-06, OS-03.

---

### 7.9 Tạm dừng Lộ trình & Domino Shift (FR-PAUSE)

#### FR-PAUSE-001: Thiết lập Tạm dừng Lộ trình (Pause Roadmap)
- **Tiêu đề**: Thiết lập Tạm dừng Lộ trình.
- **Mô tả**: Hệ thống phải cho phép Learner tạm dừng một Roadmap cụ thể trong một khoảng thời gian xác định từ ngày bắt đầu (`PauseStartDate`) đến ngày kết thúc (`PauseEndDate`).
- **Tiền điều kiện**: Roadmap đang ở trạng thái `ACTIVE`.
- **Tác nhân kích hoạt**: Learner gửi lệnh tạm dừng lộ trình.
- **Dữ liệu đầu vào**: ID của Roadmap, `PauseStartDate`, `PauseEndDate`.
- **Luồng chính**:
  1. Learner chọn lộ trình cần tạm dừng, chọn khoảng ngày tạm dừng và bấm "Xác nhận Tạm dừng".
  2. Hệ thống kiểm tra: `PauseStartDate >= CURRENT_DATE` và `PauseEndDate >= PauseStartDate`.
  3. Hệ thống tạo bản ghi Pause gắn với Roadmap và chuyển trạng thái Roadmap sang `PAUSED`.
  4. Hệ thống tự động kích hoạt **Thuật toán Domino Shift** (FR-PAUSE-002) để dời lịch học.
  5. Trong toàn bộ khoảng thời gian từ `PauseStartDate` đến `PauseEndDate`, hệ thống vô hiệu hóa mọi thông báo và cảnh báo quá hạn đối với Roadmap này.
- **Hậu điều kiện**: Lộ trình chuyển sang `PAUSED`; lịch trình tương lai được tịnh tiến an toàn.
- **Tiêu chí chấp nhận**: Không phát sinh bất kỳ cảnh báo quá hạn nào trong suốt khoảng thời gian tạm dừng; tỷ lệ Plan Adherence không bị trừ điểm trong thời gian này.
- **Phương pháp kiểm chứng**: Automated Test với Mock System Clock trong khoảng ngày tạm dừng.
- **Truy vết**: BR-003, BUSR-07, Mục 6.1 State Transition.

#### FR-PAUSE-002: Thực thi Thuật toán Tịnh tiến Dây chuyền (Domino Shift)
- **Tiêu đề**: Thực thi Thuật toán Domino Shift.
- **Mô tả**: Hệ thống phải tự động dời toàn bộ các ngày học kể từ ngày bắt đầu tạm dừng lùi về sau đúng bằng số ngày khả dụng tương ứng, bảo toàn nguyên vẹn thứ tự và mối liên kết của các task.
- **Tiền điều kiện**: Lệnh tạm dừng lộ trình hợp lệ được xác nhận.
- **Tác nhân kích hoạt**: Hoàn tất lưu cấu hình Pause Roadmap.
- **Luồng chính**:
  1. Xác định tập hợp tất cả các task đã lên lịch có `scheduled_date >= PauseStartDate`.
  2. Sắp xếp các task này theo thứ tự thời gian và thứ tự ưu tiên ban đầu.
  3. Bỏ qua toàn bộ các ngày nằm trong khoảng `[PauseStartDate, PauseEndDate]`.
  4. Lần lượt xếp lại từng task vào các ngày khả dụng tiếp theo kể từ sau ngày `PauseEndDate` theo cấu hình Availability của Learner, đảm bảo không vi phạm giới hạn thời gian mỗi ngày.
  5. Cập nhật ngày học mới cho toàn bộ các task bị ảnh hưởng trong Official Schedule.
- **Hậu điều kiện**: Toàn bộ lịch trình tương lai được dời lùi đều đặn; thứ tự bài học giữ nguyên 100%.
- **Tiêu chí chấp nhận**: Không có task nào bị đảo lộn thứ tự trước sau; ngày học mới hoàn toàn nằm ngoài khoảng thời gian tạm dừng.
- **Phương pháp kiểm chứng**: Algorithm Unit Test so sánh chuỗi thứ tự task trước và sau khi dời lịch.
- **Truy vết**: BR-003, BUSR-07.

---

### 7.10 Tích hợp Lịch ngoại vi WebCal & .ics (FR-CALENDAR)

#### FR-CALENDAR-001: Xuất Tệp tin Lịch Tĩnh `.ics`
- **Tiêu đề**: Xuất lịch tĩnh định dạng `.ics`.
- **Mô tả**: Hệ thống phải cho phép Learner tải về tệp tin lịch tĩnh chuẩn iCalendar (`.ics`) chứa toàn bộ các task thuộc Official Schedule.
- **Tiền điều kiện**: Learner có ít nhất một Roadmap đã có Official Schedule.
- **Tác nhân kích hoạt**: Learner bấm nút "Tải tệp .ics (Export .ics)".
- **Luồng chính**:
  1. Learner bấm nút xuất tệp `.ics`.
  2. Backend truy vấn các task thuộc Official Schedule của người dùng.
  3. Chuyển đổi dữ liệu thành định dạng chuẩn RFC 5545 (mỗi task tương ứng với một `VEVENT` gồm: UID, SUMMARY, DESCRIPTION, DTSTART, DTEND hoặc DTSTAMP).
  4. Trả về tệp tin `.ics` đính kèm để trình duyệt của Learner tải về máy.
- **Hậu điều kiện**: Tệp `.ics` được tải về máy thành công, có thể nhập thủ công vào các ứng dụng lịch ngoài.
- **Tiêu chí chấp nhận**: Tệp `.ics` tuân thủ chuẩn RFC 5545, không phát sinh lỗi cú pháp khi import; chỉ xuất các task thuộc Official Schedule.
- **Phương pháp kiểm chứng**: RFC 5545 iCalendar Linter / Validator tự động.
- **Truy vết**: BUSR-08.

#### FR-CALENDAR-002: Cung cấp Luồng Đăng ký Lịch Một chiều Bảo mật WebCal (WebCal Feed)
- **Tiêu đề**: Cung cấp luồng đăng ký lịch WebCal một chiều.
- **Mô tả**: Hệ thống phải cung cấp một URL duy nhất chứa mã bảo mật ngẫu nhiên (secure token) cho phép các ứng dụng lịch bên ngoài đăng ký theo dõi luồng sự kiện 1 chiều.
- **Tiền điều kiện**: Learner có tài khoản hợp lệ.
- **Tác nhân kích hoạt**: Learner truy cập trang Tích hợp Lịch.
- **Luồng chính**:
  1. Hệ thống khởi tạo cho mỗi Learner một mã bảo mật ngẫu nhiên mã hóa an toàn (chuẩn định dạng cụ thể tuân theo `OS-05`).
  2. Hiển thị đường dẫn đăng ký cá nhân: `https://focusflow.app/api/v1/feeds/{user_secure_token}.ics` kèm nút sao chép.
  3. Khi ứng dụng lịch ngoài gửi request `GET` đến URL trên:
     - Backend kiểm tra tính hợp lệ của `{user_secure_token}`.
     - Nếu token hợp lệ: Backend trả về luồng dữ liệu lịch iCalendar (MIME type: `text/calendar`) chứa các task thuộc Official Schedule của đúng người dùng sở hữu token.
  4. Toàn bộ URL và token WebCal không được ghi vào access log của máy chủ ở dạng bản rõ (tuân thủ NFR-SEC-004 và BUSR-08).
- **Luồng ngoại lệ**:
  - *Token không tồn tại hoặc đã bị thu hồi*: Trả về mã lỗi HTTP `404 Not Found` hoặc `401 Unauthorized`, tuyệt đối không trả về dữ liệu lịch.
- **Hậu điều kiện**: Ứng dụng lịch ngoài tự động đồng bộ sự kiện định kỳ một chiều.
- **Tiêu chí chấp nhận**: Tuyệt đối không cho phép truy cập feed nếu không có token hoặc token sai; dữ liệu chỉ gồm Official Schedule; không hỗ trợ đồng bộ 2 chiều.
- **Phương pháp kiểm chứng**: Automated Security and Feed Validation Test.
- **Truy vết**: BR-004, BUSR-08, NFR-SEC-004, OS-05.

#### FR-CALENDAR-003: Đặt lại Mã Bảo mật WebCal (Reset WebCal Token)
- **Tiêu đề**: Đặt lại mã bảo mật WebCal.
- **Mô tả**: Hệ thống phải cho phép Learner chủ động bấm nút đặt lại mã bảo mật WebCal để hủy quyền truy cập của các thiết bị/ứng dụng cũ khi nghi ngờ bị lộ liên kết.
- **Tiền điều kiện**: Learner đã đăng nhập hệ thống.
- **Tác nhân kích hoạt**: Learner bấm nút "Tạo lại liên kết mới (Reset Token)".
- **Luồng chính**:
  1. Learner bấm "Reset Token" trên trang cấu hình WebCal.
  2. Hệ thống hiển thị hộp thoại cảnh báo: *"Liên kết cũ trên các ứng dụng lịch ngoài sẽ ngừng hoạt động ngay lập tức. Bạn có chắc chắn muốn đổi mã mới?"*.
  3. Learner xác nhận đồng ý.
  4. Backend hủy hiệu lực (revoke) ngay lập tức của token cũ trong cơ sở dữ liệu.
  5. Backend sinh một token ngẫu nhiên mới và liên kết với tài khoản Learner.
  6. Giao diện cập nhật URL mới để người dùng sao chép.
- **Hậu điều kiện**: Token cũ bị vô hiệu hóa hoàn toàn; mọi request sử dụng token cũ đều bị từ chối truy cập.
- **Tiêu chí chấp nhận**: Token cũ bị chặn ngay lập tức sau thời điểm reset; token mới hoạt động bình thường.
- **Phương pháp kiểm chứng**: Integration Test kiểm tra request tới token cũ trả về 401/404 ngay sau khi reset.
- **Truy vết**: BUSR-08, NFR-SEC-004.

---

### 7.11 Báo cáo & AI Review Định kỳ (FR-REPORT)

#### FR-REPORT-001: Báo cáo Thống kê Tiến độ Định lượng (Quantitative Analytics)
- **Tiêu đề**: Báo cáo thống kê tiến độ định lượng.
- **Mô tả**: Hệ thống phải tính toán và hiển thị trực quan các chỉ số thống kê học tập định lượng bằng các công thức toán học chính xác, không dùng AI để suy đoán số liệu.
- **Tiền điều kiện**: Learner có lịch sử hoạt động học tập.
- **Tác nhân kích hoạt**: Learner truy cập trang Báo cáo (Analytics / Progress).
- **Luồng chính**:
  1. Hệ thống tổng hợp dữ liệu lịch sử từ bảng Session và Official Schedule.
  2. Tính toán các chỉ số toán học:
     - **Tổng thời gian tập trung thực tế (Total Focused Hours)**: $\frac{\sum \text{actual\_duration\_minutes}}{60}$.
     - **Tỷ lệ hoàn thành nhiệm vụ (Task Completion Rate)**: $\frac{\text{Số task COMPLETED}}{\text{Tổng số task đã lên lịch}} \times 100\%$.
     - **Tỷ lệ tuân thủ kế hoạch (Plan Adherence Rate)**: $\frac{\text{Số buổi học có tham gia}}{\text{Tổng số buổi học đã lên lịch (loại trừ ngày PAUSED)}} \times 100\%$.
     - Biểu đồ phân bổ thời gian học theo từng ngày trong tuần/tháng.
  3. Hiển thị báo cáo trực quan dưới dạng biểu đồ và thẻ tóm tắt.
- **Hậu điều kiện**: Báo cáo định lượng hiển thị chính xác, minh bạch.
- **Tiêu chí chấp nhận**: Số liệu khớp chính xác 100% với log thực tế; thời gian hiển thị báo cáo $\le 500$ ms.
- **Phương pháp kiểm chứng**: Unit Test kiểm tra công thức toán học với tập dữ liệu mẫu đã biết trước kết quả.
- **Truy vết**: BR-002, BR-003.

#### FR-REPORT-002: Tạo Nhận xét & Đánh giá Định tính Từ AI Review (AI Retrospective)
- **Tiêu đề**: Tạo nhận xét và đánh giá định tính từ AI Review.
- **Mô tả**: Hệ thống phải cho phép Learner yêu cầu AI đọc số liệu thống kê định lượng và các ghi chú Key Takeaways để đưa ra nhận xét định tính, phát hiện điểm nghẽn và đưa ra lời khuyên cải tiến chu kỳ tiếp theo.
- **Tiền điều kiện**: Có dữ liệu thống kê của ít nhất 1 tuần học hoặc 3 phiên học hoàn tất; Learner còn hạn ngạch AI.
- **Tác nhân kích hoạt**: Learner bấm "Yêu cầu AI Đánh giá (Generate AI Review)".
- **Dữ liệu đầu vào**: Số liệu thống kê toán học, Danh sách các ghi chú Key Takeaways, Danh sách các task thường xuyên bị trễ hạn.
- **Luồng chính**:
  1. Learner bấm nút yêu cầu nhận xét.
  2. Backend chuẩn bị dữ liệu báo cáo đã làm sạch (sanitized data, không chứa thông tin nhạy cảm cá nhân).
  3. Backend gửi yêu cầu đến External LLM với prompt chuyên gia cố vấn học tập.
  4. AI sinh báo cáo định tính gồm 3 phần: (1) Khen ngợi điểm mạnh & sự kiên trì, (2) Cảnh báo điểm nghẽn hoặc thói quen gây trễ hạn, (3) Lời khuyên điều chỉnh quỹ thời gian rảnh cho tuần tới.
  5. Hệ thống lưu bản ghi AI Review và hiển thị cho Learner.
- **Hậu điều kiện**: Nhận xét định tính được lưu vào lịch sử đánh giá của Learner.
- **Tiêu chí chấp nhận**: AI đưa ra nhận xét dựa đúng trên dữ liệu thực tế được cung cấp, không tự bịa đặt số liệu thống kê.
- **Phương pháp kiểm chứng**: Prompt Assertion Test kiểm tra output chứa các thành phần cấu trúc quy định.
- **Truy vết**: BR-003, BUSR-10.

---

### 7.12 Kiểm soát An toàn & Cơ chế Thử lại AI (FR-AI)

#### FR-AI-001: Kiểm tra Schema Đầu ra của AI & Cơ chế Thử lại (Schema Validation & Retry Semantics)
- **Tiêu đề**: Kiểm tra Schema đầu ra và ngữ nghĩa thử lại của AI.
- **Mô tả**: Hệ thống phải kiểm tra tính hợp lệ của cấu trúc dữ liệu JSON trả về từ External LLM theo schema định sẵn; phân loại lỗi và áp dụng quy tắc thử lại chính xác.
- **Tiền điều kiện**: Có request gửi đến External LLM và nhận được phản hồi.
- **Tác nhân kích hoạt**: Backend nhận phản hồi từ LLM API.
- **Phân loại lỗi & Hành vi thử lại**:
  - **Lỗi có thể thử lại tự động (Retryable Failure - Schema Failure)**: Phản hồi thành công về mặt mạng nhưng sai cú pháp JSON hoặc thiếu trường bắt buộc của schema.
    - *Số lần thử lại*: Tối đa **2 lần** (Auto-retry $\le 2$).
    - *Ngữ nghĩa thử lại*: Gửi lại yêu cầu kèm thông báo lỗi cấu trúc cụ thể cho LLM. Lượt thử lại nằm trong cùng một giao dịch logic, **tuyệt đối không trừ thêm hạn ngạch của người dùng**.
    - *Hành vi khi kiệt số lần thử lại*: Nếu sau 2 lần thử lại vẫn lỗi, Backend trả về mã lỗi `AI_SCHEMA_VALIDATION_ERROR`, kích hoạt giao diện hiển thị 2 nút bấm: `[Thử lại thủ công]` và `[Tự lập kế hoạch thủ công]`.
  - **Lỗi quá tải mạng tạm thời (Transient Upstream Failure - 429 / 503)**:
    - Backend bắt lỗi HTTP 429 (Rate Limit) hoặc 503 (Service Unavailable); không tự động retry ngầm vô hạn để tránh làm nghẽn thread.
    - Trả về mã lỗi cấu trúc `AI_SERVICE_UNAVAILABLE` cho client, hiển thị nút `[Thử lại]` (có khuyến nghị chờ) và `[Tự lập kế hoạch thủ công]`. Thuật toán backoff chi tiết của upstream do Product Owner / Kỹ thuật quyết định tại `OS-08`.
  - **Lỗi không thể thử lại (Non-Retryable Failure)**:
    - Lỗi client/prompt sai định dạng (HTTP 400), lỗi xác thực API Key (HTTP 401/403), hoặc tài khoản hết hạn ngạch.
    - Chấm dứt request ngay lập tức, ghi log lỗi hệ thống, không retry.
  - **Tính bất biến và Idempotency**: Mỗi request tạo kế hoạch phải mang một mã định danh duy nhất (`idempotency_key`) để đảm bảo không bị xử lý trùng lặp phía backend.
- **Hậu điều kiện**: Không bao giờ để dữ liệu sai schema lọt vào tầng lưu trữ.
- **Tiêu chí chấp nhận**: Auto-retry kích hoạt đúng tối đa 2 lần cho lỗi schema; không trừ thêm quota khi retry; cung cấp tùy chọn Fallback Manual Plan.
- **Phương pháp kiểm chứng**: Automated Mock LLM Tests mô phỏng payload sai schema lần 1, lần 2, lần 3.
- **Truy vết**: BR-005, NFR-AI-001, OS-08.

#### FR-AI-002: Ngắt cứng Thời gian chờ AI & Cơ chế Dự phòng (Hard Timeout & Fallback)
- **Tiêu đề**: Ngắt cứng thời gian chờ AI và cơ chế dự phòng.
- **Mô tả**: Backend phải áp dụng thời gian ngắt cứng ở giây thứ 55 đối với mọi yêu cầu gọi External LLM; nếu quá thời gian, hủy kết nối, trả về mã lỗi cấu trúc và hiển thị tùy chọn cho người dùng.
- **Tiền điều kiện**: Request gọi AI đang được xử lý ở tầng Backend.
- **Tác nhân kích hoạt**: Bộ đếm thời gian backend chạm mốc 55.000 ms.
- **Luồng chính**:
  1. Ngay khi phát lệnh gọi LLM API, Backend kích hoạt bộ đếm thời gian timeout độc lập ở mức 55 giây.
  2. Nếu nhận được phản hồi hợp lệ trước giây thứ 55: Xử lý bình thường.
- **Luồng ngoại lệ (Hard Timeout)**:
  1. Khi bộ đếm chạm mốc 55 giây: Backend chủ động hủy kết nối (abort request), ghi log `AI_GATEWAY_TIMEOUT`.
  2. Request bị timeout **không được trừ hạn ngạch của người dùng**.
  3. Backend trả về cho Client mã lỗi có cấu trúc chuẩn JSON:
     ```json
     {
       "success": false,
       "error_code": "AI_GATEWAY_TIMEOUT",
       "message": "Dịch vụ AI phản hồi chậm hơn 55 giây. Vui lòng thử lại hoặc tự tạo kế hoạch thủ công.",
       "allow_retry": true,
       "allow_manual_fallback": true
     }
     ```
  4. Giao diện hiển thị thông báo thân thiện kèm 2 nút bấm: `[Thử lại]` và `[Tự tạo kế hoạch thủ công]`.
- **Hậu điều kiện**: Luồng kết nối phía client không bị treo; người dùng luôn có đường thoát chủ động.
- **Tiêu chí chấp nhận**: Backend ngắt chính xác ở giây thứ 55; không trừ quota; hiển thị đầy đủ tùy chọn dự phòng.
- **Phương pháp kiểm chứng**: Mock Test với LLM trễ 60s, kiểm tra backend ngắt ở 55s và trả về đúng payload.
- **Truy vết**: BR-005, NFR-PERF-001.

---

### 7.13 Quản trị Hạn ngạch & Mock Upgrade Sandbox (FR-QUOTA)

#### FR-QUOTA-001: Kiểm soát Hạn ngạch Gọi AI Cấp Dịch vụ (Service-Level Quota Guard)
- **Tiêu đề**: Kiểm soát hạn ngạch AI cấp dịch vụ.
- **Mô tả**: Middleware Backend phải kiểm tra và quản lý hạn ngạch gọi AI của tài khoản trước khi thực hiện bất kỳ lệnh gọi nào đến External LLM; chặn ngay lập tức nếu đã hết hạn ngạch.
- **Tiền điều kiện**: Request có phát sinh gọi AI gửi đến Backend.
- **Tác nhân kích hoạt**: Middleware nhận request liên quan đến AI (Tạo lộ trình, AI Reprioritize, AI Review).
- **Quy tắc Kiểm tra & Khấu trừ Hạn ngạch**:
  1. **Thời điểm kiểm tra**: Diễn ra tại Middleware Backend ngay trước khi gửi request ra nhà cung cấp LLM.
  2. **Thời điểm khấu trừ / Đặt trước (Reservation & Consumption)**:
     - Middleware kiểm tra số dư hạn ngạch khả dụng của tài khoản.
     - Thực hiện kiểm tra và giữ chỗ hạn ngạch bằng **giao dịch nguyên tử (Atomic Transaction)** để chống xung đột tương tranh (race conditions) khi có nhiều request đồng thời từ cùng một tài khoản.
     - Hạn ngạch chỉ bị khấu trừ thực sự khi request gọi AI thành công và vượt qua kiểm tra schema. Nếu request thất bại do lỗi 503, 429, timeout hoặc lỗi schema sau 2 lần retry, khoản giữ chỗ phải được hoàn trả nguyên vẹn cho tài khoản.
  3. **Xử lý khi không đủ hạn ngạch**:
     - Middleware chặn request ngay tại chỗ, tuyệt đối không gửi prompt ra bên ngoài.
     - Trả về mã lỗi có cấu trúc `QUOTA_EXHAUSTED`.
     - Giao diện người dùng hiển thị thông báo hết hạn ngạch kèm liên kết chuyển hướng đến Mock Upgrade Sandbox.
  4. **Định mức phân tầng & Chu kỳ làm mới**:
     - Định mức cụ thể cho phân tầng `FREE` và `PREMIUM` cũng như chu kỳ làm mới (tháng/tuần) **tuân theo Quyết định Mở OS-02 của Product Owner**.
- **Hậu điều kiện**: 100% request hết hạn ngạch bị chặn; bảo vệ toàn vẹn chi phí API.
- **Tiêu chí chấp nhận**: Không có bất kỳ request nào được gửi đến External LLM khi tài khoản hết hạn ngạch; thao tác kiểm tra đảm bảo tính nguyên tử.
- **Phương pháp kiểm chứng**: Concurrency Load Test (k6) kiểm tra race condition với tài khoản chỉ còn 1 lượt gọi.
- **Truy vết**: BR-005, BUSR-10, OS-02.

#### FR-QUOTA-002: Trải nghiệm Nâng cấp Giả lập (Mock Upgrade Sandbox)
- **Tiêu đề**: Nâng cấp tài khoản giả lập trong môi trường Sandbox.
- **Mô tả**: Hệ thống phải cung cấp giao diện mô phỏng nâng cấp tài khoản từ Free lên Premium trong môi trường sandbox giả lập, không sử dụng cổng thanh toán thực tế và không lưu thông tin thẻ ngân hàng thật.
- **Tiền điều kiện**: Learner đã đăng nhập tài khoản ở phân tầng `FREE`.
- **Tác nhân kích hoạt**: Learner truy cập trang Quản lý Hạn ngạch hoặc bấm nâng cấp từ thông báo hết quota.
- **Luồng chính**:
  1. Hệ thống hiển thị bảng so sánh quyền lợi giữa gói Free và Premium.
  2. Hiển thị thông báo rõ ràng: *"Đây là môi trường thử nghiệm mô phỏng (Mock Sandbox). Không có giao dịch tiền tệ thực tế nào được thực hiện."*.
  3. Learner bấm nút "Mô phỏng Nâng cấp lên Premium (Mock Upgrade Now)".
  4. Hệ thống cập nhật phân tầng tài khoản của Learner thành `PREMIUM`, làm mới và cộng thêm hạn ngạch AI tương ứng vào cơ sở dữ liệu (theo định mức tại `OS-02`).
  5. Giao diện hiển thị thông báo chúc mừng nâng cấp thành công và chuyển hướng người dùng về trang làm việc với đầy đủ hạn ngạch mới.
- **Hậu điều kiện**: Tài khoản được nâng cấp lên `PREMIUM` trong cơ sở dữ liệu; hạn ngạch mới có hiệu lực ngay lập tức.
- **Tiêu chí chấp nhận**: Nâng cấp thành công tức thì; tuyệt đối không yêu cầu nhập thông tin thanh toán thật; không gọi đến bất kỳ cổng thanh toán ngoài nào.
- **Phương pháp kiểm chứng**: Automated UI Test và assertion kiểm tra thuộc tính phân tầng trong database.
- **Truy vết**: BR-005, OS-02.

---

## 8. Yêu cầu Phi Chức năng (Non-Functional Requirements - NFR)

### 8.1 Hiệu năng & Thời gian Phản hồi (NFR-PERF)
- **NFR-PERF-001: Giới hạn Thời gian Tạo Lịch AI (AI Generation Latency & Hard Timeout)**
  - Quá trình xử lý sinh lộ trình và đề xuất lịch từ External LLM phải hoàn tất hiển thị cho người dùng trong thời gian $\le \mathbf{60}$ giây.
  - Backend phải áp dụng thời gian ngắt cứng (Hard Timeout) chính xác ở giây thứ **55**; nếu quá thời gian này, kết nối phải bị hủy và trả về mã lỗi cấu trúc kèm phương án dự phòng.
  - *Phương pháp kiểm chứng*: Đo lường tự động bằng công cụ kiểm thử hiệu năng API (k6 / Postman) và đồng hồ mạng.
  - *Truy vết*: BR-001, FR-AI-002, TC2.1.

- **NFR-PERF-002: Độ trễ Thao tác Giao diện & Phản hồi Backend (Interaction Latency)**
  - Các tương tác cơ bản của người dùng trên giao diện web (tick hoàn thành task, khởi động/dừng đồng hồ timer, chuyển tab không gian học tập) phải phản hồi thị giác trong vòng $\le \mathbf{500}$ ms.
  - Các API Backend nội bộ tương ứng phải phản hồi với thời gian xử lý $\le \mathbf{200}$ ms ở mức tải đồng thời tối thiểu **20 người dùng hoạt động đồng thời (20 concurrent users)**.
  - *Phương pháp kiểm chứng*: Đo lường bằng Performance Observer API trên client và công cụ kiểm thử tải (k6) trên backend.
  - *Truy vết*: BR-002, FR-TASK-001, FR-SESSION-001, TC2.1.

### 8.2 An toàn & Bảo mật Hệ thống (NFR-SEC)
- **NFR-SEC-001: Quản lý Bí mật Tuyệt đối (Zero Secret Leakage)**
  - 100% các khóa bí mật hệ thống (API Keys dịch vụ AI, Database Credentials, JWT Secret Keys) phải được lưu trữ và nạp thông qua biến môi trường an toàn (Environment Variables).
  - Tuyệt đối không hard-code hoặc để lộ bất kỳ khóa bí mật nào trong mã nguồn client, mã nguồn public repository hoặc trong phản hồi API gửi về trình duyệt.
  - *Phương pháp kiểm chứng*: Quét tự động mã nguồn bằng công cụ kiểm tra bảo mật (Secret Scanner) đạt 0 cảnh báo trước khi triển khai.
  - *Truy vết*: BR-005, TC2.4.

- **NFR-SEC-002: Băm Mật khẩu & Bảo mật Xác thực (Password Security)**
  - 100% mật khẩu người dùng phải được băm bằng các thuật toán mã hóa một chiều đạt chuẩn công nghiệp an toàn (Argon2id hoặc bcrypt với cost factor $\ge 10$) trước khi lưu vào cơ sở dữ liệu.
  - Không bao giờ lưu trữ mật khẩu ở dạng văn bản thô (plaintext) trong bất kỳ tầng nào của hệ thống.
  - *Phương pháp kiểm chứng*: Kiểm tra cấu trúc bảng dữ liệu và mã nguồn xác thực.
  - *Truy vết*: BR-005, FR-AUTH-001.

- **NFR-SEC-003: Làm sạch Dữ liệu Gửi đến LLM Ngoài (Privacy & LLM Sanitization)**
  - Dữ liệu người dùng gửi vào prompt chuyển tiếp sang External LLM Provider phải được qua bộ lọc làm sạch: tuyệt đối không gửi mật khẩu, thông tin nhận dạng cá nhân nhạy cảm hoặc ghi chú bảo mật cá nhân ra ngoài.
  - Chỉ gửi dữ liệu về mục tiêu học tập, năng lực hiện tại và các ghi chú tóm tắt bài học cần thiết cho việc phân rã kiến thức.
  - *Phương pháp kiểm chứng*: Unit Test kiểm tra payload gửi đến LLM Provider không chứa các trường nhạy cảm.
  - *Truy vết*: BR-005, BUSR-10.

- **NFR-SEC-004: Kiểm soát Phân quyền & Bảo mật Token WebCal (Authorization & Feed Security)**
  - Mọi thao tác truy xuất, chỉnh sửa hoặc xóa Roadmap, Milestone, Task, Session đều phải kiểm tra quyền sở hữu của chính người dùng đang đăng nhập (`user_id == resource.user_id`).
  - Đường dẫn WebCal chỉ được cung cấp dữ liệu lịch của đúng người sở hữu mã token hợp lệ; token ngẫu nhiên phải có độ dài tối thiểu 32 ký tự mã hóa an toàn.
  - URL và mã token WebCal tuyệt đối không được ghi vào access log máy chủ ở dạng bản rõ.
  - *Phương pháp kiểm chứng*: Automated Security Testing kiểm tra lỗ hổng IDOR và kiểm tra cấu hình log máy chủ.
  - *Truy vết*: BUSR-08, FR-CALENDAR-002, FR-CALENDAR-003.

### 8.3 Độ sẵn sàng Hệ thống (NFR-AVAIL)
- **NFR-AVAIL-001: Độ sẵn sàng trong Đợt Thử nghiệm (System Availability)**
  - Hệ thống khi triển khai trên môi trường staging/production công khai phải duy trì tỷ lệ sẵn sàng tối thiểu $\ge \mathbf{95\%}$ trong suốt đợt thử nghiệm người dùng (UAT phase).
  - Thời gian ngưng trệ do sự cố kỹ thuật không vượt quá 5% tổng thời gian thử nghiệm.
  - *Phương pháp kiểm chứng*: Giám sát thông qua công cụ theo dõi uptime độc lập (Uptime Monitor).
  - *Truy vết*: BR-004, TC2.1.

### 8.4 Khả năng Tương thích & Tiếp cận Giao diện (NFR-UX)
- **NFR-UX-001: Tương thích Đa Thiết bị (Responsive Web Layout)**
  - Giao diện hệ thống phải tương thích hoàn toàn, hiển thị đầy đủ và không bị vỡ bố cục, không bị tràn thanh cuộn ngang (horizontal overflow) trên 2 phân dải thiết bị chính:
    - Màn hình Desktop: Độ rộng hiển thị $\ge \mathbf{1024}$ px.
    - Màn hình Di động (Mobile View): Độ rộng hiển thị từ $\mathbf{375}$ px đến $\mathbf{768}$ px.
  - *Phương pháp kiểm chứng*: Kiểm tra tự động trên công cụ giả lập đa thiết bị và kiểm thử thủ công trên thiết bị thực.
  - *Truy vết*: BR-004.

- **NFR-UX-002: Tiêu chuẩn Tiếp cận Web (Web Accessibility Standard)**
  - Toàn bộ các trang giao diện người dùng chính (Onboarding, Study Workspace, Calendar, Analytics) phải đạt điểm kiểm định Google Lighthouse Accessibility tối thiểu $\ge \mathbf{90}$ điểm.
  - Đảm bảo độ tương phản màu sắc văn bản, nhãn thẻ aria-label cho các nút bấm và hỗ trợ điều hướng cơ bản bằng bàn phím.
  - *Phương pháp kiểm chứng*: Báo cáo kiểm định tự động từ Google Lighthouse Audit.
  - *Truy vết*: BR-004, TC2.1.

### 8.5 Ràng buộc Đặc thù về AI (NFR-AI)
- **NFR-AI-001: Định dạng Đầu ra Có cấu trúc Nghiêm ngặt (Structured JSON Outputs)**
  - 100% các phản hồi từ External LLM phục vụ cho nghiệp vụ phân rã Milestones, Tasks và AI Review phải tuân thủ nghiêm ngặt định dạng JSON Schema được khai báo trước.
  - Hệ thống phải từ chối xử lý và kích hoạt quy trình thử lại đối với bất kỳ văn bản tự do không khớp cấu trúc nào.
  - *Phương pháp kiểm chứng*: Schema Validation Test trên toàn bộ các prompt template.
  - *Truy vết*: BR-005, FR-AI-001, TC2.3.

---

## 9. Tiêu chí Đánh giá Dự án & Thử nghiệm (Evaluation Metrics & Benchmarks)

> **PHÂN BIỆT RÕ RÀNG VỀ MẶT PHƯƠNG PHÁP LUẬN**: Các chỉ số dưới đây là **Tiêu chí Đánh giá Nghiệp vụ và Kết quả Dự án (Evaluation Metrics & Benchmarks)** trong đợt thử nghiệm thực tế (UAT Phase). Chúng phản ánh mức độ thành công của đề tài học thuật theo chuẩn Rubric CNTT, **không phải** là các yêu cầu phi chức năng nội tại mà phần mềm có thể tự đơn phương bảo đảm nếu không có sự tham gia của con người.

| Mã Chỉ số | Tên Chỉ số Nghiệp vụ / Đánh giá | Mục tiêu Định lượng (Benchmark) | Phương pháp & Công cụ Đo lường | Tiêu chí Rubric Căn cứ |
|---|---|---|---|---|
| **EVAL-01** | **Thời gian khởi tạo lộ trình (Plan Creation Time - KPI 1)** | $\le \mathbf{5}$ phút (300 giây) | Đo lường thực tế từ lúc người dùng bắt đầu gửi mục tiêu đến khi bấm Apply lưu Official Schedule thành công trên hệ thống. | KPI 1, TC1 Mức 5 |
| **EVAL-02** | **Hiệu quả thực thi buổi học (Session Execution Efficiency - KPI 2)** | $\ge \mathbf{80\%}$ hoàn thành | Công thức toán học: $\frac{\text{Số task tick COMPLETED trong Session}}{\text{Tổng số task dự kiến của Session}} \times 100\%$. | KPI 2, TC1 Mức 5 |
| **EVAL-03** | **Tỷ lệ duy trì lộ trình (Plan Adherence Rate - KPI 3)** | $\ge \mathbf{70\%}$ tham gia | Công thức toán học: $\frac{\text{Số buổi học có tham gia}}{\text{Tổng số buổi đã lên lịch (loại trừ ngày PAUSED)}} \times 100\%$. | KPI 3, TC1 Mức 5 |
| **EVAL-04** | **Tỷ lệ hoàn thành tác vụ (Task Success Rate - KPI 4)** | $\ge \mathbf{90\%}$ thành công | Đánh giá qua kịch bản kiểm thử UAT 4 tác vụ chính: (1) Tạo lộ trình, (2) Chạy phiên học Pomodoro, (3) Lưu ghi chú Scratchpad & Takeaway, (4) Đăng ký WebCal / Xem báo cáo. | KPI 4, TC2.7 Mức 5 |
| **EVAL-05** | **Độ hài lòng trải nghiệm người dùng (SUS Usability Score - KPI 5)** | $\ge \mathbf{80 / 100}$ điểm | Khảo sát chuẩn hóa bằng bảng câu hỏi System Usability Scale (SUS) gồm 10 câu hỏi tiêu chuẩn quốc tế trên tối thiểu $\ge \mathbf{10}$ người dùng thật thuộc đối tượng mục tiêu. | KPI 5, TC2.7 Mức 5 |

---

## 10. Kiểm soát Rủi ro & Kiến trúc An toàn AI (AI Risk Controls & Architecture Consistency)

Hệ thống FocusFlow tuân thủ nghiêm ngặt mô hình kiến trúc kiểm soát đa tầng:

```
[User Request] 
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 1: Chốt chặn Hạn ngạch (Service-Level Quota Guard)     │  <-- Chặn request vượt hạn ngạch (Atomic check)
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 2: Làm sạch Dữ liệu Nhạy cảm (Sanitization Pipeline)   │  <-- Lọc mật khẩu, thông tin cá nhân
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 3: Ngắt cứng 55s & Fallback (Hard Timeout & Fallback)  │  <-- Chặn treo mạng / lỗi 503 / 429
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 4: Kiểm tra Schema & Tự động Retry tối đa 2 lần        │  <-- Chặn dữ liệu sai cấu trúc (Không trừ quota)
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 5: Backend Hard Ceiling Validation Gate               │  <-- Chặn xếp lịch vượt thời gian rảnh
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 6: Phê duyệt từ Con người (Human-in-the-Loop Approval) │  <-- Schedule Proposal -> Apply -> Official Schedule
└─────────────────────────────────────────────────────────────┘
```

Nguyên tắc kiến trúc cốt lõi bất biến:
$$\text{AI} \longrightarrow \text{Proposal} \longrightarrow \text{Deterministic Backend Validation} \longrightarrow \text{User Approval} \longrightarrow \text{Official System State}$$

AI **tuyệt đối không bao giờ** là nguồn chân lý trực tiếp ghi đè lên trạng thái chính thức của hệ thống mà không qua cổng kiểm tra tính hợp lệ của backend và sự phê duyệt rõ ràng từ con người.

---

## 11. Bảo mật & Quyền Sở hữu Dữ liệu (Security & Data Ownership)

### 11.1 Xác thực & Phân quyền Truy cập (Authentication & Access Control)
- Áp dụng cơ chế xác thực phiên bảo mật (Session Token / JWT) với cờ bảo vệ `HttpOnly` và `SameSite`.
- Mọi câu truy vấn dữ liệu từ API bắt buộc phải kèm điều kiện lọc theo `user_id` của phiên hiện tại để ngăn ngừa lỗ hổng truy cập trái phép ngang quyền (IDOR).

### 11.2 Quyền Sở hữu Dữ liệu Độc quyền (Data Ownership Integrity)
- **Quyền sở hữu Roadmap**: Một Learner chỉ có quyền xem, chỉnh sửa, xóa và áp dụng các Roadmap do chính mình tạo ra.
- **Quyền sở hữu Task & Session**: Chỉ Learner sở hữu task mới có quyền cập nhật trạng thái `COMPLETED` hoặc ghi nhận số phút thực học.
- **Quyền sở hữu WebCal Token**: Token WebCal thuộc về riêng từng tài khoản. Không người dùng nào có thể đọc dữ liệu lịch của tài khoản khác.

### 11.3 Quản lý Biến môi trường & Bảo mật Log (Secrets Governance & Log Hygiene)
- Toàn bộ API Keys gọi dịch vụ ngoài, chuỗi kết nối cơ sở dữ liệu và khóa ký token phải được cô lập tuyệt đối trong file biến môi trường, cấm commit vào Git.
- Máy chủ ứng dụng phải cấu hình lọc sạch URL (URL masking / sanitization) để mã token WebCal bí mật không xuất hiện trong access logs, error logs hoặc các công cụ giám sát hiệu năng bên thứ ba.

---

## 12. Yêu cầu Dữ liệu Cấp Khái niệm (Conceptual Data Requirements)

> **RÀNG BUỘC PHÂN CẤP**: Mục này chỉ mô tả các thực thể khái niệm (Conceptual Entities) ở cấp độ logic nghiệp vụ. Mục này **tuyệt đối không** thiết kế bảng cơ sở dữ liệu vật lý, không viết mã SQL DDL, không chỉ định kiểu dữ liệu DBMS cụ thể và không thiết kế ORM mapping.

Hệ thống FocusFlow quản lý các thực thể logic sau:

1. **User (Người dùng)**: Quản lý thông tin định danh (`user_id`), email, mật khẩu băm, phân tầng tài khoản (Free / Premium), ngày tạo và thời điểm hoạt động.
2. **Goal (Mục tiêu học tập)**: Quản lý mục tiêu tự học ban đầu, gắn liền với một User; chứa mô tả mục tiêu, ngày mục tiêu hoàn thành, thông tin ngữ cảnh làm rõ.
3. **Roadmap (Lộ trình học tập)**: Quản lý lộ trình hoàn chỉnh, gắn liền với một User; quản lý trạng thái (`INITIALIZED`, `ACTIVE`, `PAUSED`, `COMPLETED`), ngày bắt đầu, ngày kết thúc.
4. **Milestone (Cột mốc kiến thức - Cấp 1)**: Quản lý các mốc kiến thức trung gian tuần tự thuộc một Roadmap; chứa tên cột mốc, mô tả, thứ tự tuần tự, trạng thái phê duyệt (`PENDING`, `APPROVED`).
5. **Task (Nhiệm vụ học tập - Cấp 2)**: Quản lý đầu việc chi tiết; thuộc về một Milestone và một Roadmap; chứa tên task, mô tả, thời lượng dự tính, ngày lên lịch (`scheduled_date` có thể là `NULL` nếu là Backlog), khung giờ (nếu Mode B), trạng thái thực hiện (`PENDING`, `COMPLETED`), thời điểm hoàn thành.
6. **Availability (Thời gian rảnh)**: Quản lý cấu hình thời gian rảnh của User; chứa chế độ lựa chọn (`MODE_A` hoặc `MODE_B`), chi tiết cấu hình theo từng ngày trong tuần theo quy định của `OS-06`.
7. **Schedule Proposal (Bản đề xuất lịch trình)**: Thực thể tạm thời chứa cấu trúc lịch do AI gợi ý; thuộc về một Roadmap và User; chứa danh sách task dự thảo, trạng thái (`DRAFT`, `APPLIED`, `DISCARDED`).
8. **Official Schedule (Lịch trình chính thức)**: Đại diện cho lịch học tập hợp lệ đã được kiểm duyệt và lưu trữ bền vững; là nguồn dữ liệu duy nhất liên kết các task chính thức với các mốc ngày học.
9. **Study Session (Phiên học tập trung)**: Quản lý buổi học thực tế trong Study Workspace; gắn liền với User và các Task được chọn; lưu trữ thời điểm bắt đầu, thời điểm kết thúc, thời lượng thực học (phút), trạng thái phiên (`IN_PROGRESS`, `COMPLETED`, `PARTIAL_COMPLETED`, `CANCELLED`).
10. **Study Note (Ghi chú học tập)**: Quản lý nội dung ghi chép trong phiên học; gắn với một Session; gồm 2 loại: ghi chú nháp (*Scratchpad*) và ghi chú đúc kết (*Key Takeaways*).
11. **Pause Record (Bản ghi tạm dừng lộ trình)**: Ghi nhận lịch sử và khoảng thời gian tạm dừng của một Roadmap; chứa ngày bắt đầu tạm dừng, ngày kết thúc tạm dừng và số ngày đã tịnh tiến dời lịch.
12. **AI Quota & Usage (Hạn ngạch & Sử dụng AI)**: Quản lý định mức và số lượt gọi AI của User; gắn với User; lưu trữ chu kỳ áp dụng, tổng hạn ngạch được cấp, số lượt/tokens đã tiêu thụ, thời điểm làm mới (theo `OS-02`).
13. **WebCal Token (Mã bảo mật lịch ngoại vi)**: Quản lý mã bí mật dùng cho luồng đăng ký lịch WebCal; gắn duy nhất với một User (quan hệ 1-1); chứa chuỗi token ngẫu nhiên, trạng thái kích hoạt, thời điểm tạo và thời điểm đặt lại gần nhất (theo `OS-05`).
14. **AI Review & Report (Báo cáo & Đánh giá định kỳ)**: Lưu trữ các nhận xét định tính do AI sinh ra dựa trên số liệu thống kê; gắn với User và Roadmap; chứa chu kỳ đánh giá, nội dung khen ngợi, điểm nghẽn cảnh báo và lời khuyên điều chỉnh.

---

## 13. Yêu cầu Giao diện Ngoại vi (External Interface Requirements)

### 13.1 Giao diện Người dùng (User Interfaces)
- **Công nghệ**: Nền tảng Web Application hiển thị trên trình duyệt hiện đại (Chrome, Safari, Firefox, Edge).
- **Yêu cầu Bố cục**: Thiết kế Responsive Web Design thích ứng trên Desktop ($\ge 1024$px) và Mobile ($375$px – $768$px) (NFR-UX-001).
- **Yêu cầu Tiếp cận**: Đạt chuẩn Google Lighthouse Accessibility $\ge 90$ điểm (NFR-UX-002).
- **Tương tác**: Phản hồi thao tác nội bộ $\le 500$ ms; áp dụng Optimistic UI khi tick hoàn thành task.

### 13.2 Giao diện Nhà cung cấp AI (External LLM Provider Interface)
- **Giao thức**: HTTPS RESTful API / JSON Payload qua kết nối bảo mật TLS 1.3.
- **Ràng buộc Schema**: Yêu cầu nhà cung cấp hỗ trợ cơ chế Structured JSON Outputs hoặc JSON Object Mode nghiêm ngặt.
- **Xử lý Mạng**: Quản lý timeout 55s, bắt mã lỗi HTTP chuẩn (400, 401, 429, 500, 503), hỗ trợ `idempotency_key`.

### 13.3 Giao diện Người tiêu thụ Lịch Ngoại vi (External Calendar Consumers)
- **Định dạng Tệp Tĩnh**: Tệp văn bản chuẩn RFC 5545 iCalendar (`.ics`), mã hóa ký tự UTF-8.
- **Giao thức Luồng WebCal**: HTTP/HTTPS GET Endpoint phản hồi MIME type `text/calendar`.
- **Ràng buộc chiều dữ liệu**: Luồng một chiều (One-Way Feed) duy nhất; không tiếp nhận dữ liệu ngược chiều.

---

## 14. Xử lý Ngoại lệ & Kịch bản Lỗi Toàn diện (Exception & Failure Handling)

| Tình huống Ngoại lệ / Lỗi | Nguyên nhân Kích hoạt | Phản hồi của Hệ thống | Trải nghiệm Giao diện Người dùng | Tác động Dữ liệu Bền vững | Hướng Phục hồi Sự cố |
|---|---|---|---|---|---|
| **AI Hard Timeout** | External LLM không phản hồi sau 55 giây. | Backend ngắt kết nối chủ động; ghi log `AI_GATEWAY_TIMEOUT`. | Hiển thị thông báo "Dịch vụ AI phản hồi chậm" kèm nút [Thử lại] và [Tạo kế hoạch thủ công]. | Không ghi nhận dữ liệu hỏng; **không trừ hạn ngạch AI của người dùng**. | Learner bấm Thử lại hoặc chọn chuyển sang tự tạo kế hoạch thủ công. |
| **Lỗi AI Provider 429 (Rate Limit)** | LLM API bên ngoài bị quá tải hoặc vượt giới hạn request. | Backend bắt mã 429; trả về mã lỗi cấu trúc `AI_RATE_LIMIT_EXCEEDED`. | Hiển thị thông báo: "Hệ thống AI đang tiếp nhận nhiều yêu cầu, vui lòng đợi giây lát" kèm nút Thử lại / Thủ công. | Không phát sinh dữ liệu rác; **không trừ hạn ngạch**. | Learner đợi giây lát rồi thử lại hoặc tạo thủ công. |
| **Lỗi AI Provider 503 (Unavailable)** | Dịch vụ AI bên ngoài bị sập hoặc bảo trì mạng. | Backend bắt mã 503; ghi log lỗi hạ tầng nhà cung cấp. | Hiển thị thông báo "Dịch vụ AI tạm thời gián đoạn" kèm nút [Tạo kế hoạch thủ công]. | Không ghi nhận bản ghi mới; **không trừ hạn ngạch**. | Learner chuyển sang lập kế hoạch thủ công mà không phụ thuộc vào AI. |
| **Lỗi Schema AI (Schema Failure)** | AI trả về văn bản tự do hoặc JSON thiếu trường bắt buộc. | Backend phát hiện qua Schema Validator; tự động kích hoạt Auto-retry tối đa 2 lần. | Trong 2 lần đầu: Giao diện hiển thị đang xử lý. Nếu vẫn lỗi: hiển thị hộp thoại báo lỗi cấu trúc kèm 2 nút bấm. | Không bao giờ lưu trữ payload sai vào cơ sở dữ liệu; **các lần retry không trừ thêm quota**. | Tự động retry tối đa 2 lần; nếu kiệt thì người dùng chọn Thử lại hoặc tạo thủ công. |
| **Áp dụng Lịch Không Hợp lệ (Invalid Apply)** | Learner chỉnh sửa task trên Proposal làm tổng giờ vượt quá Availability. | Backend Validation Gate từ chối lưu trữ; trả về mã lỗi `VALIDATION_OVERLOAD`. | Đánh dấu đỏ các ngày bị quá tải thời gian kèm thông báo số phút bị vượt. | Tuyệt đối từ chối ghi vào Official Schedule. | Learner điều chỉnh giảm thời lượng task hoặc dời ngày cho phù hợp rồi bấm Apply lại. |
| **Cạn kiệt Hạn ngạch AI (Quota Exhausted)** | Người dùng đạt tới giới hạn số lượt gọi AI của gói tài khoản. | Middleware Backend chặn ngay tại chỗ; không gửi request ra LLM ngoài. | Hiển thị thông báo hết hạn ngạch kèm nút [Trải nghiệm Nâng cấp Giả lập]. | Hạn ngạch giữ nguyên ở mức 0; không phát sinh chi phí. | Learner truy cập Mock Upgrade Sandbox để mô phỏng nâng cấp lên gói Premium. |
| **Gián đoạn Phiên học (Browser Crash / Disconnect)** | Learner mất mạng, đóng trình duyệt hoặc bấm dừng phiên sớm. | Hệ thống bắt sự kiện hoặc tính lại khi kết nối lại; tính số phút thực học đã trôi qua. | Khi mở lại: Hiển thị tóm tắt phiên, task xong giữ nguyên, task dở dang về Backlog. | Lưu chính xác số phút thực học vào Session; cập nhật trạng thái `PARTIAL_COMPLETED` hoặc `CANCELLED` theo `OS-01`. | Người dùng truy cập danh sách Backlog để xếp lịch lại cho các task chưa hoàn thành. |
| **Lộ Liên kết WebCal** | Người dùng nghi ngờ lộ URL bí mật cho bên thứ ba. | Learner bấm nút "Reset Token" trên trang tích hợp. | Hiển thị cảnh báo xác nhận; sau khi đổi hiển thị URL mới kèm nút sao chép. | Token cũ bị hủy hiệu lực tức thì trong DB; sinh token mới thay thế. | Các ứng dụng lịch cũ dùng token cũ bị từ chối 401/404 ngay lập tức; Learner dán URL mới vào ứng dụng lịch. |

---

## 15. Danh mục Quyết định Kỹ thuật Đã Phê duyệt (Approved Open Decisions Register - Milestone M2)

Toàn bộ 8 quyết định mở kỹ thuật (`OS-01` đến `OS-08`) đã được Chủ sở hữu Sản phẩm (Product Owner) và Trưởng nhóm Kỹ thuật phê duyệt chính thức tại Biên bản Thẩm định & Đóng băng Cơ sở Yêu cầu (Milestone M2 - WBS 2.4, ngày 17/09/2026):

| Mã ID | Vấn đề Quyết định (Decision Subject) | Yêu cầu Chi phối | Quyết định Chính thức Được Phê duyệt (Approved Resolution) |
|---|---|---|---|
| **OS-01** | **Ranh giới phân định trạng thái `CANCELLED` và `PARTIAL_COMPLETED` của Session** | FR-SESSION-003, BUSR-09, Mục 6.3 | **Phê duyệt**: Phiên học bị dừng sớm hoặc mất mạng được ghi nhận là `PARTIAL_COMPLETED` nếu có **$\ge 1$ task đã hoàn thành (`COMPLETED`)** HOẶC **thời gian thực học đạt $\ge 50\%$ thời lượng dự kiến**. Dưới cả 2 ngưỡng này, phiên ghi nhận là `CANCELLED`. |
| **OS-02** | **Định mức số lượng gọi AI cụ thể cho phân tầng Free và Premium** | FR-QUOTA-001, FR-QUOTA-002, BUSR-10 | **Phê duyệt**: Gói **Free** cấp tối đa 3 Roadmap hoạt động đồng thời và 30 lượt gọi AI/tháng. Gói **Premium** cấp tối đa 15 Roadmap hoạt động đồng thời và 300 lượt gọi AI/tháng. Chu kỳ đặt lại hạn ngạch: ngày 01 hàng tháng. |
| **OS-03** | **Cơ chế xử lý khi Apply Lịch mới trong khi Official Schedule đã tồn tại** | FR-PLAN-003, FR-SCHEDULE-001, BUSR-02 | **Phê duyệt**: Áp dụng chính sách **Merge / Future Shift**: Giữ nguyên toàn bộ các task và phiên học đã `COMPLETED` trong quá khứ; chỉ xóa và thay thế các task chưa hoàn thành trong tương lai bằng Proposal mới. |
| **OS-04** | **Thuật toán giải quyết xung đột ưu tiên giữa nhiều Roadmap khi xếp lịch tự động** | FR-AVAIL-003, BUSR-05 | **Phê duyệt**: Áp dụng giải thuật **Earliest Deadline First (EDF)**: Ưu tiên phân bổ slot thời gian trống cho Roadmap có hạn chót mục tiêu gần hơn. |
| **OS-05** | **Thuật toán mã hóa và định dạng cụ thể của WebCal Secure Token** | FR-CALENDAR-002, NFR-SEC-004 | **Phê duyệt**: Sử dụng chuỗi ngẫu nhiên độ dài **32-byte hex (CSPRN)** sinh bằng thư viện mật mã an toàn (`crypto.randomBytes`). Gắn quan hệ 1-1 với User và tự động vô hiệu hóa token cũ khi bấm Reset. |
| **OS-06** | **Dải giá trị hợp lệ của Quỹ giờ rảnh mỗi ngày (Mode A Availability Bounds)** | FR-AVAIL-001, BUSR-03 | **Phê duyệt**: Cận dưới tối thiểu là **0.5 giờ (30 phút)/ngày**; Cận trên tối đa là **14 giờ/ngày**. |
| **OS-07** | **Cơ chế kỹ thuật chốt giờ và đồng bộ phiên học khi mất kết nối kéo dài** | FR-SESSION-003 | **Phê duyệt**: Client gửi định kỳ nhịp **Heartbeat ping mỗi 60 giây**. Nếu server không nhận được ping quá **5 phút**, hệ thống tự động chốt phiên học theo thời điểm ping thành công gần nhất. |
| **OS-08** | **Chính sách Backoff và Giới hạn chờ cho lỗi quá tải AI 429/503** | FR-AI-001, FR-AI-002 | **Phê duyệt**: Áp dụng chiến lược **Exponential Backoff với Full Jitter** (khoảng chờ lần lượt 2s, 4s, tối đa 10s) cho tối đa 2 lần retry tự động. |

---

## 16. Ma trận Truy vết Toàn diện (Comprehensive Traceability Matrix)

> **XÁC NHẬN ĐỘ PHỦ TRUY VẾT**: Độ phủ truy vết được duy trì đầy đủ cho toàn bộ các yêu cầu đã được xác định trong hệ thống; 100% quyết định mở (OS-01 đến OS-08) đã được giải quyết và chuẩn hóa tại Mục 15.

| Nguồn Chân lý (Problem Definition) | Mã BR | Mã Quy tắc (BUSR) | Mã Yêu cầu Chức năng (FR) | Mã NFR chi phối | Tiêu chí Đánh giá & Chấp nhận (EVAL / AC) |
|---|---|---|---|---|---|
| **Mục 1.2, 4 (P1: Khó phân rã mục tiêu)** | BR-001 | BUSR-01, BUSR-02 | FR-AUTH-001, FR-AUTH-002, FR-GOAL-001, FR-GOAL-002, FR-PLAN-001, FR-PLAN-002, FR-PLAN-003 | NFR-PERF-001 ($\le 60$s), NFR-AI-001 (Schema), NFR-SEC-001 | **EVAL-01**: Tạo kế hoạch $\le 5$ phút.<br>**AC**: Proposal không tự lưu; chỉ lưu khi bấm Apply qua Validation Gate (tuân thủ OS-03). |
| **Mục 5.2 (Mô hình Thời gian rảnh Lai)** | BR-001, BR-003 | BUSR-03, BUSR-04, BUSR-05 | FR-AVAIL-001 (Mode A), FR-AVAIL-002 (Mode B), FR-AVAIL-003 (Đa Roadmap) | NFR-PERF-002 (UI $\le 500$ms, API $\le 200$ms) | **AC**: Chặn vượt quỹ giờ Mode A (theo OS-06); chặn lệch khung giờ Mode B; Soft Overflow tối đa 30 phút có cảnh báo và xác nhận. |
| **Mục 1.2, 5.3 (P2: Phân mảnh công cụ)** | BR-002 | BUSR-09 | FR-SESSION-001, FR-SESSION-002, FR-SESSION-003, FR-TASK-001, FR-TASK-002 | NFR-PERF-002, NFR-UX-001 (Responsive), NFR-UX-002 (Lighthouse $\ge 90$) | **EVAL-02**: Hiệu quả buổi học $\ge 80\%$.<br>**EVAL-04**: Task Success Rate $\ge 90\%$.<br>**EVAL-05**: SUS $\ge 80/100$.<br>**AC**: Lưu đúng số phút thực học; task xong giữ nguyên, task dở dang về Backlog (tuân thủ OS-01, OS-07). |
| **Mục 1.2, 5.4 (P3: Đứt gãy lịch khi trễ hạn)** | BR-003 | BUSR-06, BUSR-07 | FR-ADAPT-001 (Overdue), FR-ADAPT-002 (AI Reprioritize), FR-PAUSE-001, FR-PAUSE-002 (Domino Shift) | NFR-PERF-002, NFR-AVAIL-001 ($\ge 95\%$) | **EVAL-03**: Plan Adherence $\ge 70\%$.<br>**AC**: Phát hiện quá hạn tất định thuần túy backend; Domino Shift dời lùi đúng số ngày khả dụng, không báo quá hạn khi Pause. |
| **Mục 5.5 (Tích hợp Lịch ngoại vi)** | BR-004 | BUSR-08 | FR-CALENDAR-001 (.ics), FR-CALENDAR-002 (WebCal), FR-CALENDAR-003 (Reset Token) | NFR-SEC-004 (Bảo mật Token & Log Hygiene), RFC 5545 | **AC**: Chỉ xuất Official Schedule; WebCal 1 chiều bảo mật; token cũ bị hủy hiệu lực ngay lập tức khi bấm reset (tuân thủ OS-05). |
| **Mục 5.6 (Báo cáo & Đánh giá định kỳ)** | BR-002, BR-003 | BUSR-10 | FR-REPORT-001 (Thống kê toán), FR-REPORT-002 (AI Review) | NFR-PERF-002, NFR-SEC-003 (Sanitization) | **AC**: Thống kê toán học chính xác 100%; AI Review nhận xét đúng số liệu, không bịa đặt số liệu. |
| **Mục 5.1, 8.2 (Quản trị Chi phí & Rủi ro AI)** | BR-005 | BUSR-10 | FR-QUOTA-001, FR-QUOTA-002 (Mock Sandbox), FR-AI-001 (Retry Semantics), FR-AI-002 (Timeout 55s / Fallback) | NFR-PERF-001 (Timeout 55s), NFR-SEC-001 (Zero secret leak), NFR-AI-001 | **AC**: Kiểm tra hạn ngạch nguyên tử; chặn 100% request hết quota tại middleware (theo OS-02); retry tối đa 2 lần không trừ quota; ngắt ở giây 55; Mock Sandbox không thanh toán thật. |

---

## 17. Kết luận & Tình trạng Chuẩn Cơ sở (Quality Sign-Off & Baseline Status)

Tài liệu **Software Requirements Specification (SRS) v1.0 — FocusFlow** đã được rà soát và chuẩn hóa toàn diện theo chuẩn quốc tế **ISO/IEC/IEEE 29148:2018**.

Tài liệu hiện đang ở trạng thái:
> **Phiên bản v1.0 — Chuẩn Yêu cầu Cơ sở Đã Đóng Băng (Requirements Baseline Frozen v1.0)**

Tất cả 10 quy tắc nghiệp vụ cốt lõi và 8 quyết định mở kỹ thuật (`OS-01` đến `OS-08`) đã được phê chuẩn chính thức, đảm bảo tính nhất quán tuyệt đối, tính độc lập giải pháp và sẵn sàng chuyển giao làm đầu vào chuẩn mực cho **Giai đoạn 2: Phân tích Hệ thống & Thiết kế Kiến trúc, CSDL (UML 2.5)**. Mọi yêu cầu thay đổi tiếp theo bắt buộc phải qua quy trình Quản lý Thay đổi (Change Control Board - CCB).
