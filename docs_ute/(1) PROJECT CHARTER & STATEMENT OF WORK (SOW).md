# PROJECT CHARTER & STATEMENT OF WORK (SOW)
## (ĐIỀU LỆ DỰ ÁN & ĐẶC TẢ PHẠM VI CÔNG VIỆC)

---

**Mã Dự Án:** PRJ-FOCUSFLOW  
**Tên Dự Án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Ngày Hiệu Lực:** 01/09/2026  
**Phiên Bản:** 1.0  
**Đơn Vị Chủ Quản:** Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE) — Khoa Công nghệ Thông tin  
**Giảng Viên Hướng Dẫn:** ThS. Vũ Đình Bảo  
**Nhóm Sinh Viên Thực Hiện:**  
- Vũ Toàn Thắng (MSSV: 23110329 — Project Manager / Lead Software Architect)  
- Phan Đình Duẩn (MSSV: 23110192 — Senior Business Analyst / Quality & DevOps Lead)  

---

## 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)

### 1.1. Mục Tiêu Dự Án (Project Objectives)

Mục tiêu cốt lõi của Dự án **FocusFlow** là nghiên cứu, thiết kế và phát triển một nền tảng phần mềm toàn diện hỗ trợ cá nhân tự học (Self-Directed Learners) vượt qua chuỗi đứt gãy kỷ luật trong quá trình học tập độc lập. Hệ thống kết hợp giữa mô hình tự điều chỉnh học tập (Self-Regulated Learning — SRL theo Zimmerman, 2002) với công nghệ Trí tuệ nhân tạo (AI/LLM) nhằm tự động hóa quy trình phân rã mục tiêu, phân bổ lịch trình thông minh theo quỹ thời gian thực tế, hỗ trợ tập trung phiên học và tự động tái cấu trúc kế hoạch khi có biến cố quá hạn phát sinh.

Hệ thống sau khi hoàn thành phải đáp ứng toàn diện các mục tiêu kỹ thuật và nghiệp vụ trọng yếu sau:

| STT | Yêu Cầu Trọng Yếu | Diễn Giải & Mô Tả Chi Tiết |
| :---: | :--- | :--- |
| **1** | **Phân rã mục tiêu 2 cấp độ bằng AI** | Tích hợp AI (Google Gemini API) thực hiện hỏi - đáp làm rõ ngữ cảnh, tự động phân rã mục tiêu học tập trừu tượng thành Lộ trình 2 cấp: Cấp 1 (Milestones vĩ mô) và Cấp 2 (Tasks & Đề xuất Lịch trình vi mô) với định dạng dữ liệu có cấu trúc nghiêm ngặt (Pydantic Structured Outputs / JSON Schema Gate). |
| **2** | **Quản lý thời gian rảnh lai (Hybrid Availability)** | Hỗ trợ người học linh hoạt thiết lập quỹ thời gian theo 2 chế độ: Chế độ A (Hạn ngạch tổng số giờ trong tuần) và Chế độ B (Khung giờ cố định theo từng thứ trong tuần), làm cơ sở thuật toán sắp xếp lịch học khả thi. |
| **3** | **Cơ chế duyệt lịch 2 cổng (Strict Approval Gate)** | Kế hoạch AI sinh ra chỉ ở trạng thái "Đề xuất" (Schedule Proposal). Người học có toàn quyền tùy biến, chỉnh sửa trước khi bấm "Apply" để kích hoạt thành "Lịch chính thức" (Official Schedule), ngăn chặn hoàn toàn hiện tượng AI tự ý ghi đè dữ liệu. |
| **4** | **Không gian thực thi phiên học (Study Tool Suite)** | Cung cấp môi trường học tập tập trung tích hợp: Đồng hồ bấm giờ (Pomodoro/Stopwatch), danh sách công việc kiểm tra (Checklist), bảng ghi nháp (Scratchpad), và sổ tay đọng lại kiến thức (Key Takeaways) kèm cơ chế tự động lưu phục hồi sau sự cố gián đoạn. |
| **5** | **Cơ chế thích ứng tất định khi quá hạn (Deterministic Overdue Adaptation)** | Thay vì dùng AI thiếu nhất quán, hệ thống áp dụng tác vụ nền tự động (Celery Beat) nhận diện bài học quá hạn và cung cấp 3 giải pháp tất định tức thì: Tự động dời sang slot rảnh tiếp theo, Chuyển về hàng đợi Backlog, hoặc Đánh dấu hoàn thành có điều kiện. |
| **6** | **Tạm dừng lộ trình & Domino Shift** | Cho phép người học kích hoạt trạng thái "Tạm dừng" (Pause) khi gặp biến cố bất khả kháng (ốm đau, thi cử). Hệ thống tự động tịnh tiến toàn bộ các task chưa hoàn thành trong tương lai theo đúng số ngày tạm dừng mà không làm xáo trộn cấu trúc học tập. |
| **7** | **Đồng bộ Lịch ngoại vi qua WebCal** | Cung cấp luồng dữ liệu lịch chuẩn hóa (iCalendar RFC 5545) thông qua liên kết WebCal bảo mật bằng Secure Token Feed (`/api/v1/calendar/feed/{token}`), cho phép người dùng đồng bộ lịch học 1 chiều vào Google Calendar, Apple Calendar, Outlook. |
| **8** | **Đo lường định lượng & Báo cáo AI Review tuần** | Tổng hợp số liệu thời gian học thực tế, biểu đồ phân bổ khung giờ và tỷ lệ hoàn thành; cung cấp báo cáo đánh giá định tính định kỳ hàng tuần từ AI nhằm duy trì động lực và phản tư quá trình học tập. |
| **9** | **Phân quyền và Quản trị Hạn ngạch (RBAC & Quota Guard)** | Thiết lập 2 vai trò người dùng (`learner` và `admin`). Tầng bảo vệ Service Quota kiểm soát chặt chẽ số lượt gọi AI hàng ngày/tháng, chống gian lận và tối ưu hóa chi phí API; tích hợp Mock Upgrade Sandbox cho phép người dùng mô phỏng nâng cấp tài khoản. |

---

### 1.2. Hiện Trạng & Bối Cảnh (Current Situation)

#### 1.2.1. Quy trình nghiệp vụ hiện tại & Những điểm nghẽn
Trong bối cảnh chuyển đổi số và xu hướng học tập suốt đời (Lifelong Learning), người tự học (đặc biệt là sinh viên công nghệ, người chuyển ngành, nhân sự tự nâng cao nghiệp vụ) thường gặp phải chuỗi đứt gãy liên hoàn:
- **Rào cản phân rã mục tiêu (Decomposition Barrier):** Người học dễ rơi vào trạng thái bế tắc khi đứng trước một mục tiêu lớn (ví dụ: *"Thành thạo lập trình Backend trong 3 tháng"*). Việc thiếu người hướng dẫn có chuyên môn khiến họ không biết phải bắt đầu từ đâu, phân bổ kiến thức theo trình tự nào cho hợp lý.
- **Phân mảnh công cụ & Tê liệt nhận thức (Tool Fragmentation & Cognitive Overhead):** Người học phải sử dụng đồng thời 4–5 ứng dụng rời rạc: dùng ChatGPT xin lộ trình dạng văn bản, dùng Google Calendar tạo lịch hẹn tĩnh, dùng Notion ghi chép kiến thức, dùng app Pomodoro đếm giờ. Việc liên tục chuyển đổi ngữ cảnh gây tiêu hao năng lượng ý chí (planning fatigue) trước khi thực sự bắt đầu học.
- **Đứt gãy kế hoạch khi gặp biến cố (Rigid Planning Failure):** Kế hoạch học tập tĩnh truyền thống rất dễ sụp đổ. Khi người học ốm đau hoặc bận việc đột xuất 1–2 ngày, các task bị dồn ứ. Việc phải tự tính toán và dời lịch thủ công từng bài học khiến người học nản chí, sinh ra tâm lý tội lỗi và dẫn đến từ bỏ mục tiêu (drop-out).

#### 1.2.2. Hạn chế kỹ thuật của các giải pháp hiện hành
Khảo sát đối sánh thực tế (Benchmarking) giữa FocusFlow và các giải pháp hiện có trên thị trường cho thấy khoảng trống lớn về mặt giải pháp kỹ thuật:

| Tiêu Chí Kỹ Thuật | Google Calendar | Notion | ChatGPT / Claude | **FocusFlow (Giải Pháp Đề Xuất)** |
| :--- | :---: | :---: | :---: | :---: |
| **Bản chất hệ thống** | Quản lý lịch biểu tĩnh (Time-blocking) | Không gian ghi chép & cơ sở dữ liệu mở | Mô hình ngôn ngữ lớn dạng hội thoại văn bản | **Nền tảng quản lý lộ trình học thích ứng chuyên sâu** |
| **Phân rã mục tiêu tự động** | Không hỗ trợ | Không hỗ trợ (phải tạo thủ công) | Có sinh văn bản nhưng không sinh thực thể Task có cấu trúc | **AI làm rõ ngữ cảnh $\rightarrow$ Phân rã 2 cấp độ (JSON Schema Gate)** |
| **Kiểm soát quỹ thời gian thực tế** | Thủ công sắp xếp | Không tự động tính toán | Không nắm được lịch rảnh thực tế của người dùng | **Mô hình Hybrid Availability (Hạn ngạch tuần & Khung giờ cố định)** |
| **Không gian phiên học tích hợp** | Không có | Có ghi chép nhưng không có Timer/Checklist tích hợp | Không có | **Tích hợp Timer, Checklist, Scratchpad, Key Takeaways & Crash Recovery** |
| **Cơ chế thích ứng khi quá hạn** | Kéo thả từng sự kiện thủ công | Kéo thả bảng thủ công | Không có khả năng can thiệp dữ liệu lịch trình | **Thuật toán tự động tất định (Auto-shift, Backlog queue, Domino shift)** |
| **Kiểm soát chi phí & Hạn ngạch** | Không áp dụng | Không áp dụng | Giới hạn theo phiên chat trả phí | **Tầng Quota Guard độc lập, Redis rate limit, RBAC 2 phân quyền** |

---

## 2. PHẠM VI CÔNG VIỆC (SCOPE OF WORK)

Dựa trên yêu cầu của các bên liên quan và Chuẩn Yêu cầu Cơ sở Sau Thẩm định (SRS v1.1), phạm vi thực hiện dự án được phân định rành mạch như sau:

### 2.1. Phạm Vi Dự Án (In-Scope)

Dự án bao gồm việc thiết kế, xây dựng, kiểm thử và tài liệu hóa toàn diện các hạng mục công việc sau:

| STT | Hạng Mục Công Việc | Mô Tả Kỹ Thuật & Nghiệp Vụ Chi Tiết |
| :---: | :--- | :--- |
| **1** | **Phát triển Backend API (FastAPI)** | Xây dựng hệ thống RESTful API hiệu năng cao với Python 3.12 theo Kiến trúc Lục giác (Hexagonal Architecture / Ports & Adapters); tích hợp SQLAlchemy 2.x, Pydantic v2, quản lý phụ thuộc bằng Astral `uv`. |
| **2** | **Phát triển Giao diện Web (Next.js 15)** | Xây dựng giao diện Single-Page / Server-Rendered Web hiện đại với Next.js 15 App Router, React 19, TypeScript, TailwindCSS v4, shadcn/ui, Zustand cho trạng thái Workspace và TanStack Query cho Server Cache. |
| **3** | **Cơ sở dữ liệu & Quản lý Migration** | Thiết kế CSDL quan hệ PostgreSQL 16 chuẩn 3NF gồm 10 bảng cốt lõi; áp dụng chuẩn định danh UUIDv7 (RFC 9562); xây dựng bộ kịch bản di chuyển lược đồ tự động với Alembic. |
| **4** | **Phân hệ Xác thực & Quản trị Người dùng (FR-AUTH)** | Đăng ký, đăng nhập tài khoản; bảo mật phiên với JWT Cookie HttpOnly; cơ chế xoay vòng Refresh Token Rotation (RTR) và danh sách đen thu hồi (Blacklist) lưu trữ trên Redis 7; mã hóa mật khẩu với Argon2id. |
| **5** | **Phân hệ Thiết lập Mục tiêu & Lập kế hoạch AI (FR-GOAL, FR-PLAN)** | Luồng Onboarding thu thập ngữ cảnh; tương tác với Google Gemini API qua Server-Sent Events (SSE); sinh lộ trình 2 cấp độ (Milestones & Schedule Proposal); áp dụng Schema Validation Gate trước khi người dùng Review. |
| **6** | **Phân hệ Cấu hình Thời gian rảnh Lai (FR-AVAIL)** | Giao diện và API cấu hình thời gian học khả dụng theo Mode A (Tổng số giờ rảnh tuần) và Mode B (Ma trận khung giờ cố định tuần: Thứ, Bắt đầu, Kết thúc); kiểm tra trùng lắp và tương thích dữ liệu. |
| **7** | **Phân hệ Quản trị Lịch trình & Task (FR-SCHEDULE, FR-TASK)** | Quản lý Lịch chính thức (Official Schedule); quản trị hàng đợi Backlog; chức năng kéo thả và điều chỉnh thời lượng task; kiểm soát tính toàn vẹn trạng thái task (`pending`, `in_progress`, `completed`, `skipped`). |
| **8** | **Phân hệ Không gian Phiên học (FR-SESSION)** | Workspace thực thi bài học: Chế độ Pomodoro / Stopwatch; bảng ghi chú nhanh Scratchpad; tổng hợp đọng lại kiến thức (Key Takeaways); cơ chế bảo vệ phục hồi phiên học sau sự cố đóng trình duyệt đột ngột (Crash Recovery). |
| **9** | **Phân hệ Tác vụ Nền & Thích ứng Quá hạn (FR-ADAPT, FR-PAUSE)** | Cấu hình Celery 5.4+ và Redis Broker/Backend; thiết lập Celery Beat xử lý quét định kỳ: Đóng phiên học treo, nhận diện task quá hạn (Overdue shift), cơ chế tạm dừng lộ trình (Domino shift); bảo đảm tác vụ có tính lũy suy (Idempotent). |
| **10** | **Phân hệ Tích hợp Lịch Ngoại vi (FR-CALENDAR)** | Xây dựng chuẩn định dạng iCalendar (RFC 5545); cấp phát URL đăng ký WebCal bí mật bảo vệ bằng token ngẫu nhiên entropy cao; hỗ trợ xuất tệp tin tĩnh `.ics`. |
| **11** | **Phân hệ Thống kê & AI Review Tuần (FR-REPORT)** | Dashboard đo lường định lượng thời gian học thực tế, biểu đồ phân bổ khung giờ; tích hợp AI tổng hợp báo cáo phân tích định tính hàng tuần dựa trên dữ liệu học và Key Takeaways. |
| **12** | **Phân hệ Quản trị Viên & Quản lý Hạn ngạch (FR-ADM, FR-QUOTA)** | Web Admin Portal tối giản (`/admin`): Giám sát người dùng, cấu hình hạn ngạch gọi AI (Admin Quota Override), theo dõi chỉ số tải hệ thống; giao diện Mock Upgrade Sandbox cho phép người dùng tự thử nghiệm nâng cấp gói. |
| **13** | **Đóng gói Triển khai Docker Compose** | Xây dựng Dockerfile chuẩn Multi-stage build cho Backend và Frontend; tệp `docker-compose.yml` điều phối 5 dịch vụ đồng bộ: `postgres`, `redis`, `api`, `celery_worker`, `frontend` kèm healthcheck và mạng nội bộ cách ly. |
| **14** | **Kiểm thử Phần mềm & Đánh giá NFRs** | Bộ kiểm thử tự động với Pytest (Unit tests, Integration tests, Golden tests cho AI prompt); kiểm chứng hiệu năng, độ trễ và khả năng tiếp cận chuẩn Google Lighthouse ($\ge 90$). |
| **15** | **Tài liệu hóa Kỹ thuật & Báo cáo Học thuật** | Soạn thảo bộ hồ sơ kỹ thuật chuẩn mực (ISO 29148 SRS, arc42 Architecture, C4 Model, UML 2.5, Data Dictionary, 8 ADRs) và Báo cáo Khóa luận Tốt nghiệp hoàn chỉnh. |

---

### 2.2. Giới Hạn Dự Án (Project Boundaries / Out-of-Scope)

Để đảm bảo dự án hoàn thành đúng tiến độ trong thời hạn 15 tuần của học kỳ tốt nghiệp và tập trung giải quyết xuất sắc bài toán cốt lõi, các hạng mục sau được quy định rõ ràng là **KHÔNG THUỘC PHẠM VI** của dự án:

| STT | Hạng Mục Loại Trừ | Lý Do & Giải Pháp Thay Thế |
| :---: | :--- | :--- |
| **1** | **Ứng dụng Native Mobile (iOS/Android)** | Không xây dựng app native bằng Swift/Kotlin/Flutter. Dự án tập trung tối ưu hóa 100% trải nghiệm Responsive Web App trên Next.js 15, tương thích hoàn hảo trên trình duyệt di động và máy tính bảng. |
| **2** | **Đồng bộ 2 chiều (Bidirectional Sync) với Google Calendar / Outlook** | Hệ thống không gọi ghi dữ liệu ngược vào tài khoản cá nhân của người dùng qua Google Calendar API / Microsoft Graph API. Giải pháp thay thế là cung cấp chuẩn WebCal Subscription Feed 1 chiều (RFC 5545) bảo mật, tránh rủi ro bảo mật OAuth scopes rộng và quota API bên thứ ba. |
| **3** | **Tích hợp Cổng Thanh toán Tiền tệ Thực tế** | Không tích hợp cổng thanh toán sản xuất (Production VNPay, MoMo, Stripe) nhằm tránh vướng mắc thủ tục pháp lý doanh nghiệp. Giải pháp thay thế là xây dựng phân hệ **Mock Upgrade Sandbox** cho phép người dùng và hội đồng chấm thi mô phỏng trải nghiệm nâng cấp tài khoản tức thì. |
| **4** | **Mạng xã hội & Tương tác Cộng đồng đa người dùng** | Hệ thống không xây dựng tính năng kết bạn, nhóm học tập, chat trực tiếp giữa các người học. Dự án định vị FocusFlow là công cụ cá nhân hóa chuyên sâu (Single-Learner SRL Tool), loại bỏ tối đa các yếu tố xao nhãng. |
| **5** | **Tự động Chấm điểm & Đánh giá Kiến thức Chuyên môn bằng AI** | FocusFlow không phải là một hệ thống LMS (như Moodle hay Coursera) và không thực hiện việc chấm code, chấm bài luận hay cấp chứng chỉ. AI chỉ đóng vai trò trợ lý cấu trúc lộ trình, phân rã thời gian và phản tư học tập. |
| **6** | **Tích hợp Web Push Notifications qua FCM / APNs** | Hệ thống không cài đặt dịch vụ đẩy thông báo Web Push qua Service Worker phức tạp. Các cảnh báo và nhắc nhở được hiển thị trực tiếp thông qua giao diện In-App và luồng đồng bộ lịch ngoại vi WebCal. |

---

## 3. YÊU CẦU KỸ THUẬT & GIẢI PHÁP (TECHNICAL REQUIREMENTS)

### 3.1. Kiến Trúc & Ngăn Xếp Công Nghệ (Proposed Architecture)

Hệ thống được thiết kế theo mô hình **Kiến trúc Lục giác (Hexagonal Architecture / Ports & Adapters)** ở Backend nhằm cách ly triệt để Business Domain Logic khỏi các công nghệ hạ tầng (Database, LLM API, Cache). Tổng thể hệ thống được đặc tả qua mô hình C4 Container và bộ công nghệ chuẩn hóa:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (Next.js 15)                      │
│   React 19 + TypeScript + Tailwind v4 + Zustand + TanStack Query      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / RESTful API / SSE
┌───────────────────────────────────▼────────────────────────────────────┐
│                    API GATEWAY & BACKEND (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Presentation Layer: Routers (Auth, Goal, Plan, Session, Admin)   │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ Application & Domain Core: Use Cases, Domain Rules, Ports        │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ Infrastructure Adapters: SQLAlchemy Repo, Gemini LLM, Redis Store│  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────┬────────────────────┬────────────────────┬───────────────┘
               │                    │                    │
┌──────────────▼─────┐ ┌────────────▼────────┐ ┌─────────▼──────────────┐
│   PostgreSQL 16    │ │   Redis 7 In-Memory │ │  Celery Worker & Beat  │
│  Relational DB     │ │  Cache, RTR Token   │ │  Scheduled Batch Jobs  │
│  UUIDv7 Primary Key│ │  & Celery Broker    │ │  Overdue Adaptation    │
└────────────────────┘ └─────────────────────┘ └────────────────────────┘
```

| Thành Phần Hệ Thống | Công Nghệ Lựa Chọn | Phiên Bản | Vai Trò & Cơ Chế Hoạt Động |
| :--- | :--- | :---: | :--- |
| **Backend Framework** | FastAPI (Python) | 3.12 | Khung ứng dụng RESTful API bất đồng bộ (asyncio), hiệu năng cao, tự động sinh OpenAPI spec. |
| **Kiến trúc Backend** | Hexagonal Architecture | — | Tách biệt Domain, Application Use Cases, Driven Ports và Driving/Driven Adapters. |
| **Gói Phụ Thuộc Backend** | Astral uv | 0.4+ | Trình quản lý môi trường ảo và giải quyết thư viện Python thế hệ mới, tốc độ cực nhanh. |
| **Frontend Framework** | Next.js (App Router) | 15.0+ | Khung ứng dụng Web hỗ trợ React Server Components (RSC), Client Components, tối ưu SEO và routing. |
| **Thư viện UI / Logic** | React + TypeScript | 19 / 5.x | Xây dựng giao diện an toàn kiểu dữ liệu, tái sử dụng components theo tiêu chuẩn nghiêm ngặt. |
| **Styling & Design System**| TailwindCSS + shadcn/ui | v4 | Bộ giao diện người dùng hiện đại, hỗ trợ chuẩn Design Tokens, linh hoạt và tiếp cận cao. |
| **State Management** | Zustand + TanStack Query | v5 | Zustand quản lý trạng thái cục bộ phiên học; TanStack Query quản lý dữ liệu server cache và refetch. |
| **Cơ sở dữ liệu Quan hệ** | PostgreSQL | 16.x | Quản trị dữ liệu quan hệ ACID, hỗ trợ chuẩn khóa chính UUIDv7 (RFC 9562) sắp xếp theo thời gian. |
| **ORM & Di chuyển Lược đồ**| SQLAlchemy 2.x + Alembic | 2.0 / 1.14 | Ánh xạ đối tượng CSDL khai báo (Declarative), theo dõi và thực thi migration an toàn. |
| **Bộ nhớ đệm & Token Store**| Redis | 7.x | Quản lý phiên làm việc, lưu trữ Refresh Token Hash, kiểm soát Rate Limiting và hàng đợi Celery. |
| **Tác vụ Nền & Định kỳ** | Celery + Celery Beat | 5.4+ | Xử lý các batch jobs: quét phiên học gián đoạn, dịch chuyển lịch quá hạn tự động, báo cáo tuần. |
| **Mô hình Trí tuệ Nhân tạo**| Google Gemini API | 1.5/2.0 Flash | Sinh lộ trình học tập, phản rã công việc, phân tích ngữ cảnh và đánh giá định tính định kỳ. |
| **Tích hợp Lịch Ngoại vi** | icalendar | RFC 5545 | Sinh tệp `.ics` và luồng WebCal Subscription Feed bảo mật với Secure Token. |
| **Đóng gói & Triển khai** | Docker & Docker Compose | 27.x | Đóng gói môi trường đồng nhất cho toàn bộ 5 dịch vụ phát triển và kiểm thử. |

---

### 3.2. Yêu Cầu Bảo Mật & An Toàn Dữ Liệu (Security Requirements)

Hệ thống FocusFlow được thiết kế tuân thủ nghiêm ngặt các nguyên tắc bảo mật phần mềm hiện đại (OWASP Top 10 và Architecture Decision Record ADR-008):

| STT | Tiêu Chí Bảo Mật | Cơ Chế Triển Khai Kỹ Thuật |
| :---: | :--- | :--- |
| **1** | **Xác thực & Quản lý Phiên (Authentication)** | Sử dụng cặp mã thông báo JWT. **Access Token** có thời hạn sống ngắn (15 phút) được lưu trữ an toàn trong Cookie `HttpOnly`, cờ `SameSite=Lax`, `Secure`. Ngăn chặn hoàn toàn nguy cơ rò rỉ mã token qua tấn công XSS (Cross-Site Scripting). |
| **2** | **Xoay vòng Refresh Token (RTR & Blacklist)** | **Refresh Token** có thời hạn 7 ngày, chỉ lưu giá trị băm SHA-256 trong Redis Token Store. Mỗi lần cấp mới Access Token, Refresh Token cũ bị vô hiệu hóa ngay lập tức và sinh token mới (RTR). Nếu phát hiện một token cũ được tái sử dụng, hệ thống lập tức thu hồi toàn bộ phiên đăng nhập của người dùng (Token Family Revocation). |
| **3** | **Mã hóa Mật khẩu Người dùng** | Áp dụng thuật toán băm mật khẩu hiện đại **Argon2id** (chuẩn đạt giải Password Hashing Competition), có khả năng chống lại tấn công vét cạn (brute-force) bằng phần cứng chuyên dụng GPU/ASIC. |
| **4** | **Phân quyền Dựa trên Vai trò (RBAC Gate)** | Hệ thống phân định 2 vai trò: `learner` và `admin`. Các endpoint nhạy cảm (như điều chỉnh Quota hệ thống, quản lý tài khoản người dùng) được bảo vệ bằng Middleware kiểm tra vai trò nghiêm ngặt; mọi truy cập trái phép bị từ chối với mã lỗi `403 Forbidden`. |
| **5** | **Bảo vệ Chống Tấn công Tần suất (Rate Limiting)** | Tích hợp middleware kiểm soát tần suất truy cập dựa trên thuật toán Token Bucket / Fixed Window qua Redis: Giới hạn chung 60 requests/phút cho toàn hệ thống; thắt chặt 5 requests/phút đối với các endpoint nhạy cảm như Đăng nhập, Đăng ký và Yêu cầu sinh Lộ trình AI. |
| **6** | **Chống Giả mạo Yêu cầu (CSRF Protection)** | Kết hợp cờ Cookie `SameSite=Lax` với kỹ thuật Double Submit Cookie Token cho toàn bộ các phương thức thay đổi trạng thái (POST, PUT, PATCH, DELETE). |
| **7** | **Bảo mật Luồng Lịch Ngoại vi (WebCal Security)** | URL đăng ký WebCal Feed sử dụng token định danh ngẫu nhiên có độ dài 64 ký tự hex (entropy cao), không chứa thông tin định danh người dùng. Cho phép người dùng thu hồi và cấp lại token bất kỳ lúc nào để vô hiệu hóa liên kết cũ. |
| **8** | **Kiểm soát An toàn AI (Prompt Injection Defense & Quota Guard)** | Sử dụng cơ chế Pydantic Structured Outputs buộc phản hồi từ AI phải khớp 100% với JSON Schema quy định. Dữ liệu đầu vào của người dùng được chuẩn hóa và khử khuẩn (sanitization). Tầng Quota Guard độc lập ngăn chặn hành vi spam làm cạn kiệt chi phí API. |

---

## 4. KẾ HOẠCH BÀN GIAO & MỐC TIẾN ĐỘ (MILESTONES & DELIVERABLES)

Kế hoạch thực hiện dự án được chuẩn hóa theo 7 Mốc Sự Kiện Quan Trọng (Milestones 1.0 đến 7.0), ánh xạ tương ứng từ Cấu trúc Phân chia Công việc chi tiết (WBS 15 tuần của đề tài tốt nghiệp) được phê duyệt bởi Giảng viên Hướng dẫn:

| ID | Giai Đoạn (Phase) | Mốc Sự Kiện (Milestone Event) | Sản Phẩm Bàn Giao (Deliverables) | Thời Hạn (Deadline) |
| :---: | :--- | :--- | :--- | :---: |
| **1.0** | **Khởi tạo Dự án (Inception)** | Kick-off Meeting & Baseline Formulation | - Điều lệ Dự án & SOW hoàn chỉnh (`PRJ-FOCUSFLOW`)<br>- Kế hoạch WBS & Gantt Chart 15 tuần<br>- Khảo sát người học & Báo cáo Benchmarking đối sánh 3 giải pháp | **Tuần 2**<br>(12/09/2026) |
| **2.0** | **Kỹ nghệ Yêu cầu (Requirements)** | Chốt Cơ sở Yêu cầu (Requirements Freeze) | - Hồ sơ Đặc tả Yêu cầu SRS v1.1 chuẩn ISO/IEC/IEEE 29148<br>- Danh mục 5 Mục tiêu Định lượng & KPIs<br>- Ma trận Truy vết Yêu cầu (Requirement Traceability Matrix - RTM) | **Tuần 4**<br>(26/09/2026) |
| **3.0** | **Thiết kế Hệ thống (System Design)** | Phê duyệt Thiết kế & Kiến trúc (Design Freeze) | - Mô hình Phân tích UML 2.5 (Use Case, Activity, Sequence, State Machine)<br>- Thiết kế Kiến trúc C4 Model & Tài liệu arc42<br>- Sơ đồ CSDL PostgreSQL 16 (DB Diagram), Từ điển Dữ liệu & 8 ADRs | **Tuần 6**<br>(10/10/2026) |
| **4.0** | **Phát triển Nền tảng & Core MVP (Sprint 1)** | Hoàn thành Backend API, DB & Module AI | - Mã nguồn Backend FastAPI chuẩn Hexagonal Architecture<br>- Cơ sở dữ liệu PostgreSQL 16 & Alembic Migrations<br>- Module Xác thực JWT/Redis & Module Lập kế hoạch AI Gemini qua SSE | **Tuần 9**<br>(31/10/2026) |
| **5.0** | **Phát triển Giao diện & Không gian Học (Sprint 2)** | Hoàn thiện Frontend & Toàn bộ Phân hệ | - Giao diện Web Next.js 15 cho Learner & Admin Portal<br>- Không gian thực thi phiên học (Study Tool Suite: Timer, Checklist)<br>- Tác vụ nền Celery Beat (Overdue Shift, Domino Pause, WebCal Feed) | **Tuần 11**<br>(14/11/2026) |
| **6.0** | **Kiểm thử, Đánh giá & UAT (Verification)** | Nghiệm thu UAT & Thẩm định Tiêu chuẩn | - Báo cáo Kiểm thử Tự động (Unit Test, Integration Test > 80% coverage)<br>- Báo cáo Đánh giá NFRs (Lighthouse $\ge 90$, NFR Latency $\le 60$s)<br>- Báo cáo Thực nghiệm UAT với $\ge 10$ người dùng thật & Đo lường SUS Score | **Tuần 13**<br>(28/11/2026) |
| **7.0** | **Đóng Dự án & Bảo vệ Khóa luận (Closure)** | Báo cáo Bảo vệ & Bàn giao Sản phẩm | - Toàn văn Báo cáo Khóa luận Tốt nghiệp định dạng chuẩn HCMUTE<br>- Bộ slide báo cáo khoa học & Video kịch bản demo sản phẩm<br>- Mã nguồn hoàn chỉnh kèm tệp `docker-compose.yml` triển khai 1-click | **Tuần 15**<br>(12/12/2026) |

---

## 5. TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA)

Quá trình nghiệm thu dự án được thực hiện nghiêm ngặt dựa trên kết quả Kiểm thử Chấp nhận Người dùng (User Acceptance Test — UAT) kết hợp với việc kiểm chứng bộ 5 Chỉ số Hiệu quả Định lượng (KPIs) đã cam kết với Giảng viên Hướng dẫn:

### 5.1. Điều Kiện Nghiệm Thu Kỹ Thuật & Nghiệp Vụ

| STT | Điều Kiện Nghiệm Thu | Tiêu Chuẩn Đánh Giá Cụ Thể |
| :---: | :--- | :--- |
| **1** | **Chức năng Đầy đủ & Khớp SRS** | Hệ thống đáp ứng đầy đủ 100% các nhóm chức năng cam kết trong SRS v1.1 (FR-AUTH, FR-GOAL, FR-PLAN, FR-AVAIL, FR-SCHEDULE, FR-TASK, FR-SESSION, FR-ADAPT, FR-PAUSE, FR-CALENDAR, FR-REPORT, FR-QUOTA, FR-ADM). |
| **2** | **Không Tồn tại Lỗi Nghiêm trọng** | Không tồn tại bất kỳ lỗi loại Critical hoặc High nào làm đứt gãy luồng người dùng cốt lõi (đăng ký, tạo kế hoạch AI, phê duyệt lịch, bấm giờ phiên học, đồng bộ lịch ngoại vi). |
| **3** | **Kiểm soát Sinh Kế hoạch AI Khắt khe** | 100% kế hoạch do AI sinh ra phải tuân thủ JSON Schema thông qua Pydantic Gate; không có hiện tượng sinh dữ liệu rác làm sập giao diện; thời gian sinh lộ trình cấp 1 không vượt quá 60 giây. |
| **4** | **Tính Toàn vẹn của Cổng Duyệt Lịch** | Lịch AI sinh ra bắt buộc ở trạng thái Đề xuất (Schedule Proposal); hệ thống chỉ ghi nhận thành Lịch chính thức (Official Schedule) khi người dùng chủ động bấm "Apply" và vượt qua tầng kiểm tra xung đột thời gian. |
| **5** | **Tính Tự động của Thích ứng Quá hạn** | Tác vụ Celery Beat tự động phát hiện chính xác các bài học quá hạn và thực thi 1 trong 3 kịch bản: Auto-shift sang slot rảnh khả dụng gần nhất, chuyển về hàng đợi Backlog, hoặc hoàn tất có ghi chú; cơ chế Domino Shift dịch chuyển lịch chính xác khi Tạm dừng lộ trình. |
| **6** | **Khả năng Phục hồi Phiên học sau Gián đoạn** | Khi người dùng vô tình đóng tab trình duyệt hoặc mất điện trong lúc đang học, dữ liệu phiên học (thời gian đã trôi qua, checklist, ghi chú nháp) được khôi phục chính xác tối thiểu 95% trạng thái khi mở lại ứng dụng. |
| **7** | **Đồng bộ Lịch Ngoại vi Ổn định** | Đường dẫn WebCal Feed được các ứng dụng ngoài (Google Calendar / Apple Calendar / Outlook) nạp thành công, hiển thị chính xác các mốc giờ học với múi giờ của người dùng. |
| **8** | **Bảo mật & Không Rò rỉ Dữ liệu Nhạy cảm** | Điểm số bảo mật đạt chuẩn: Token bí mật lưu trong Cookie `HttpOnly`, mật khẩu được mã hóa Argon2id, không có API Key AI hay mật khẩu CSDL nào bị rò rỉ trong mã nguồn Frontend hoặc Git Repository. |
| **9** | **Đo lường Chỉ số Khả dụng & KPIs** | Tổ chức thử nghiệm UAT thực tế trên tối thiểu 10 người dùng thật; điểm đánh giá trải nghiệm hệ thống theo thang đo **SUS (System Usability Scale) đạt từ 80 điểm trở lên**; tỷ lệ hoàn thành tác vụ cốt lõi đạt trên 85%. |
| **10** | **Bộ Hồ sơ Tài liệu & Mã nguồn Hoàn chỉnh** | Toàn bộ tài liệu thiết kế (SRS, UML, Kiến trúc, DB Diagram, ADRs, Hướng dẫn cài đặt) và mã nguồn được đóng gói đầy đủ, cấu hình Docker Compose khởi chạy thành công với một câu lệnh duy nhất. |

### 5.2. Quy Trình Nghiệm Thu & Đánh Giá

1. **Bàn giao Từng Mốc:** Khi nhóm hoàn thành một Mốc Sự Kiện (Milestone), nhóm gửi Báo cáo Tình trạng Dự án (Project Status Report) kèm bằng chứng thực thi (demo link, test report, tài liệu đính kèm) đến Giảng viên Hướng dẫn.
2. **Thời gian Phản hồi:** Giảng viên Hướng dẫn xem xét, góp ý và đánh giá sản phẩm bàn giao trong vòng 07 ngày làm việc kể từ ngày nhận.
3. **Phê duyệt hoặc Yêu cầu Khắc phục:**
   - **Chấp thuận (Accepted):** Giảng viên ký duyệt (hoặc xác nhận qua email/portal) để nhóm chính thức đóng mốc và chuyển sang giai đoạn tiếp theo.
   - **Chấp thuận có Điều kiện (Conditionally Accepted) / Yêu cầu Chỉnh sửa (Rejected):** Nhóm ghi nhận các điểm chưa đạt vào Bảng Theo dõi Vấn đề (Issue Tracker) và thực hiện khắc phục trong thời hạn tối đa 05 ngày làm việc.

---

## 6. TỔ CHỨC DỰ ÁN & TRÁCH NHIỆM (ROLES & RESPONSIBILITIES)

Mô hình phân công trách nhiệm được chuẩn hóa theo Ma trận RACI (**R**esponsible, **A**ccountable, **C**onsulted, **I**nformed) đảm bảo tính minh bạch, chuyên môn hóa và làm chủ công nghệ của từng thành viên trong nhóm:

### 6.1. Thành Viên Dự Án & Phân Công Vai Trò Cốt Lõi

| Vai Trò (Role) | Nhân Sự Đảm Nhiệm (Resource) | Trách Nhiệm Kỹ Thuật & Quản Trị Chính (Key Responsibilities) |
| :--- | :--- | :--- |
| **Project Manager & Lead Architect** | **Vũ Toàn Thắng**<br>(MSSV: 23110329) | - Lập kế hoạch tổng thể, điều phối WBS, quản lý tiến độ và rủi ro dự án.<br>- Thiết kế Kiến trúc tổng thể hệ thống (Hexagonal Architecture, C4 Model, arc42).<br>- Phụ trách phát triển Backend API cốt lõi, tích hợp LLM (Gemini API), cơ chế SSE và Schema Validation Gate.<br>- Thiết kế sơ đồ CSDL PostgreSQL 16, chiến lược phân vùng Index và quản trị bộ 8 ADRs.<br>- Đầu mối liên lạc chính, báo cáo định kỳ hàng tuần với Giảng viên Hướng dẫn. |
| **Senior BA & Quality / DevOps Lead** | **Phan Đình Duẩn**<br>(MSSV: 23110192) | - Khảo sát bài toán, phân tích người dùng, soạn thảo và chuẩn hóa hồ sơ SRS v1.1 theo chuẩn ISO 29148.<br>- Thiết kế mô hình phân tích hệ thống UML 2.5 (Use Case, Activity Diagrams).<br>- Phụ trách phát triển Frontend Web (Next.js 15, Zustand, shadcn/ui) và không gian phiên học Study Tool Suite.<br>- Thiết lập cấu hình hệ thống nền tảng, Docker Compose, Redis Token Store và các tác vụ nền Celery Beat.<br>- Thiết lập kịch bản kiểm thử tự động (Unit/Integration Tests), tổ chức thử nghiệm UAT và thu thập số liệu SUS. |
| **Project Sponsor & Academic Advisor** | **ThS. Vũ Đình Bảo**<br>(Khoa CNTT, HCMUTE) | - Giám sát tính khoa học, định hướng nghiên cứu và phương pháp luận kỹ nghệ phần mềm.<br>- Thẩm định các mốc sự kiện quan trọng, nghiệm thu các sản phẩm bàn giao (Deliverables).<br>- Đánh giá và chấm điểm tiến độ định kỳ theo khung Rubric Khóa luận Tốt nghiệp. |

### 6.2. Ma Trận Trách Nhiệm RACI Theo Giai Đoạn Dự Án

*Ký hiệu:* **R** = Người trực tiếp thực hiện (Responsible), **A** = Người chịu trách nhiệm phê duyệt cuối cùng (Accountable), **C** = Người được tham vấn chuyên môn (Consulted), **I** = Người được thông báo kết quả (Informed).

| Hạng Mục Công Việc Trọng Yếu | Vũ Toàn Thắng | Phan Đình Duẩn | GVHD (ThS. Vũ Đình Bảo) |
| :--- | :---: | :---: | :---: |
| Lập kế hoạch Dự án, Điều lệ SOW & Quản trị Tiến độ WBS | **A / R** | **C / R** | **I / Phê duyệt** |
| Nghiên cứu Bài toán, Khảo sát & Soạn thảo Hồ sơ SRS v1.1 | **C** | **A / R** | **I / Phê duyệt** |
| Thiết kế Kiến trúc Phần mềm (C4, arc42) & Ra quyết định ADRs | **A / R** | **C** | **C / Góp ý** |
| Mô hình hóa Phân tích Hệ thống (UML 2.5 Diagrams) | **C / R** | **A / R** | **I** |
| Thiết kế CSDL PostgreSQL 16, Data Dictionary & Alembic Migration | **A / R** | **C** | **I** |
| Lập trình Backend API, Tích hợp AI Gemini & Luồng SSE | **A / R** | **C** | **I** |
| Lập trình Frontend Next.js 15, Workspace Phiên học & UI Design | **C** | **A / R** | **I** |
| Tác vụ Nền Celery Beat, Xử lý Quá hạn & WebCal Feed | **A / R** | **C / R** | **I** |
| Thiết lập Docker Compose, CI Pipeline & Kiểm thử Tự động | **C** | **A / R** | **I** |
| Thực nghiệm Đánh giá UAT, Đo lường 5 KPIs & Khảo sát SUS | **A / R** | **A / R** | **C / Đánh giá** |
| Viết Báo cáo Khóa luận Tốt nghiệp & Chuẩn bị Bảo vệ | **A / R** | **A / R** | **Chấm điểm Hội đồng** |

---

## 7. QUẢN LÝ RỦI RO & THAY ĐỔI (RISK & CHANGE MANAGEMENT)

### 7.1. Quản Lý Rủi Ro (Risk Management)

Nhóm áp dụng quy trình nhận diện, đánh giá ma trận xác suất/tác động và thiết lập các biện pháp kỹ thuật giảm thiểu rủi ro ngay từ giai đoạn đầu:

| STT | Mô Tả Rủi Ro Kỹ Thuật / Tiến Độ | Mức Độ | Biện Pháp Phòng Ngừa & Giảm Thiểu (Mitigation Strategy) | Người Phụ Trách |
| :---: | :--- | :---: | :--- | :---: |
| **1** | **Mô hình AI sinh sai cấu trúc (Hallucination) hoặc quá tải/timeout** | **Cao** | Thiết lập lớp kiểm soát dữ liệu nghiêm ngặt **JSON Schema Gate** thông qua Pydantic v2; thiết lập timeout 55s và cơ chế tự động thử lại tối đa 3 lần với Exponential Backoff; chuẩn bị sẵn các mẫu lộ trình dự phòng (Fallback Templates) nếu dịch vụ AI mất kết nối hoàn toàn. | Vũ Toàn Thắng |
| **2** | **Vượt hạn mức ngân sách hoặc cạn kiệt Quota gọi API của LLM** | **Cao** | Xây dựng phân hệ **Quota Guard** độc lập kiểm soát số lượng token và số lượt gọi AI theo người dùng; áp dụng cơ chế khóa phân tán trong Redis để giữ trước hạn ngạch trước khi gọi API (Reserve/Commit Quota); giới hạn rate-limit chặt chẽ 5 requests/phút. | Vũ Toàn Thắng |
| **3** | **Xung đột môi trường phát triển & thư viện giữa các thành viên** | **Trung bình** | Chuẩn hóa công cụ quản lý gói dependencies thế hệ mới: `uv` cho Python và `pnpm` cho Node.js; đồng bộ hóa 100% môi trường cục bộ thông qua Docker Compose; bắt buộc chạy kịch bản pre-commit check trước khi đẩy mã nguồn lên Git. | Phan Đình Duẩn |
| **4** | **Rủi ro rò rỉ mã bí mật hoặc tấn công đánh cắp phiên người dùng** | **Trung bình** | Loại bỏ hoàn toàn việc lưu Access Token trong `localStorage`; áp dụng cơ chế lưu trữ Cookie `HttpOnly` kèm thuật toán xoay vòng Refresh Token (RTR) trong Redis; quét bảo mật tự động ngăn chặn commit file `.env` lên GitHub repository. | Vũ Toàn Thắng |
| **5** | **Khó khăn trong việc thu hút người dùng thử nghiệm UAT thực tế** | **Trung bình** | Lập kế hoạch tuyển chọn nhóm đối tượng mục tiêu (bạn bè sinh viên CNTT, người đang tự học lập trình) ngay từ Tuần 10; xây dựng bộ dữ liệu mẫu phong phú và kịch bản hướng dẫn người dùng chi tiết (Onboarding Guide). | Phan Đình Duẩn |
| **6** | **Trượt thời hạn hoàn thành do khối lượng công việc lớn** | **Cao** | Áp dụng mô hình Agile/Scrum tinh gọn với chu kỳ Sprint 2 tuần; họp kiểm điểm tiến độ và cập nhật Báo cáo Tình trạng Dự án (RAG Status) hàng tuần; tập trung tối đa nguồn lực hoàn thành xuất sắc bộ tính năng Core MVP trước khi phát triển các tiện ích bổ sung. | Vũ Toàn Thắng |

---

### 7.2. Quản Lý Thay Đổi (Change Management)

Nhằm kiểm soát rủi ro phình to phạm vi (Scope Creep) và bảo đảm tính toàn vẹn của chuỗi truy vết từ Yêu cầu đến Mã nguồn, mọi đề xuất thay đổi đều phải tuân thủ nghiêm ngặt quy trình 4 bước sau:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   1. GHI NHẬN    │ ──> │   2. ĐÁNH GIÁ    │ ──> │   3. PHÊ DUYỆT   │ ──> │   4. CẬP NHẬT    │
│ Phiếu Yêu Cầu    │     │ Phân Tích Ma Trận│     │ Giảng Viên / PM  │     │ Hồ Sơ Kỹ Thuật   │
│ Thay Đổi (CRF)   │     │ Tác Động & Rủi Ro│     │ Quyết Định Chốt  │     │ SRS, WBS, Mã Code│
└──────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
```

1. **Ghi nhận (Capture):** Bất kỳ yêu cầu thay đổi nào về mặt tính năng, công nghệ hoặc mốc tiến độ đều phải được lập thành văn bản chính thức thông qua **Phiếu Yêu Cầu Thay Đổi (Change Request Form - CRF)**, mô tả rõ: Nguyên nhân thay đổi, nội dung đề xuất và thành phần bị ảnh hưởng.
2. **Đánh giá Tác động (Impact Analysis):** Nhóm tiến hành phân tích đa chiều tác động của thay đổi đối với:
   - *Phạm vi & Yêu cầu:* Có làm sai lệch chuẩn yêu cầu SRS v1.1 không?
   - *Kiến trúc & Cơ sở dữ liệu:* Có đòi hỏi sửa đổi lược đồ CSDL hoặc phá vỡ các quyết định trong ADRs không?
   - *Tiến độ & Nguồn lực:* Có làm trượt các mốc Milestone chính trong WBS không?
3. **Phê duyệt (Approval Gate):**
   - Các thay đổi nhỏ ở tầng hiện thực mã nguồn (không ảnh hưởng đến SRS và CSDL): Do Project Manager và Technical Lead phê duyệt nội bộ.
   - Các thay đổi trọng yếu liên quan đến phạm vi bài toán, bổ sung/loại trừ tính năng hoặc dời hạn chót: Bắt buộc phải trình bày, tham vấn và nhận được sự chấp thuận bằng văn bản của **Giảng viên Hướng dẫn**.
4. **Cập nhật & Đồng bộ Tài liệu (Baseline Update):** Khi thay đổi được phê duyệt, nhóm có trách nhiệm:
   - Cập nhật số hiệu phiên bản mới trong hồ sơ SRS, Sơ đồ UML, Bản thiết kế Kiến trúc và Từ điển Dữ liệu.
   - Soạn thảo bản ghi quyết định kiến trúc mới (ADR) nếu có thay đổi công nghệ.
   - Điều chỉnh lại thời hạn trong biểu đồ WBS Gantt Chart và cập nhật trạng thái trong Báo cáo Tiến độ tuần gần nhất.

---

## 8. KÝ DUYỆT & XÁC NHẬN CỦA CÁC BÊN (SIGN-OFF & APPROVAL)

Tài liệu này đóng vai trò là thỏa thuận cơ sở chính thức giữa Nhóm Sinh viên thực hiện và Giảng viên Hướng dẫn về mục tiêu, phạm vi công việc, ngăn xếp công nghệ, kế hoạch bàn giao và tiêu chí nghiệm thu của đề tài **FocusFlow**.

Bằng việc ký tên hoặc xác nhận dưới đây, các bên cam kết thực hiện đầy đủ các quyền hạn và nghĩa vụ đã được nêu trong bản Điều lệ Dự án & Đặc tả Phạm vi Công việc này.

<br>

| ĐẠI DIỆN GIẢNG VIÊN HƯỚNG DẪN | ĐẠI DIỆN NHÓM SINH VIÊN THỰC HIỆN |
| :---: | :---: |
| *(Ký và ghi rõ họ tên)* | *(Ký và ghi rõ họ tên)* |
| <br><br><br><br> | <br><br><br><br> |
| **ThS. Vũ Đình Bảo** | **Vũ Toàn Thắng** (Project Manager)<br>**Phan Đình Duẩn** (Quality Lead) |
| Ngày: ..... / ..... / 2026 | Ngày: ..... / ..... / 2026 |
