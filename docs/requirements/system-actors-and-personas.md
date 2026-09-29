# FocusFlow — System Actors & User Personas Analysis Specification

> **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
> **Chuyên ngành:** Công nghệ Phần mềm — Khoa Công nghệ Thông tin  
> **Cấp độ tài liệu:** Đặc tả Tác nhân Hệ thống & Phân tích Chân dung Người dùng (System Actors & User Personas Artifact)  
> **Mã tài liệu:** `DOC-REQ-ACTOR-01`  
> **Tài liệu liên kết:** 
> - [**`problem-definition.md`**](problem-definition.md) *(Định nghĩa bài toán & Ranh giới hệ thống)*
> - [**`user-survey-and-benchmarking.md`**](user-survey-and-benchmarking.md) *(Khảo sát nhu cầu tự học & Đối sánh giải pháp)*
> - [**`business-goals-and-kpis.md`**](business-goals-and-kpis.md) *(Hệ thống Mục tiêu & 5 KPI định lượng)*
> - [**`../srs/srs-v1.0.md`**](../srs/srs-v1.0.md) *(Đặc tả Yêu cầu Phần mềm v1.0 — Mục 3.1 Tác nhân hệ thống)*  
> **Căn cứ đánh giá học thuật:** Khung Rubric Chấm Đồ án Tốt nghiệp CNTT:
> - **Tiêu chí TC1 (Mức 5):** "Xác định rõ người dùng mục tiêu, các bên liên quan và phân tích bối cảnh khách quan."
> - **Tiêu chí TC2.1 (Mức 5):** "Mô hình hóa tác nhân, phân quyền và ranh giới hệ thống chuẩn mực."
> - **Tiêu chí TC2.7 (Mức 5):** "Thiết kế lấy người dùng làm trung tâm (UCD); Thử nghiệm nghiêm túc trên người dùng thật."

---

## MỤC LỤC

1. [Phân biệt Lý thuyết giữa Tác nhân Hệ thống & Chân dung Người dùng](#1-phân-biệt-lý-thuyết-giữa-tác-nhân-hệ-thống--chân-dung-người-dùng)
   - 1.1 [Cơ sở khoa học kỹ thuật phần mềm](#11-cơ-sở-khoa-học-kỹ-thuật-phần-mềm)
   - 1.2 [Mối quan hệ tương quan trong chu trình phát triển](#12-mối-quan-hệ-tương-quan-trong-chu-trình-phát-triển)
2. [Đặc tả Chi tiết 4 Tác nhân Hệ thống (System Actors Specification)](#2-đặc-tả-chi-tiết-4-tác-nhân-hệ-thống-system-actors-specification)
   - 2.1 [Tác nhân Người học (Learner - Primary Human Actor)](#21-tác-nhân-người-học-learner---primary-human-actor)
   - 2.2 [Tác nhân Quản trị viên (Administrator - Platform Service Role)](#22-tác-nhân-quản-trị-viên-administrator---platform-service-role)
   - 2.3 [Tác nhân Nhà cung cấp AI (External LLM Provider - External System Actor)](#23-tác-nhân-nhà-cung-cấp-ai-external-llm-provider---external-system-actor)
   - 2.4 [Tác nhân Ứng dụng Lịch Ngoại vi (External Calendar Application - External Consumer)](#24-tác-nhân-ứng-dụng-lịch-ngoại-vi-external-calendar-application---external-consumer)
   - 2.5 [Ma trận Trách nhiệm & Phân quyền Tác nhân (Actor Responsibility Matrix)](#25-ma-trận-trách-nhiệm--phân-quyền-tác-nhân-actor-responsibility-matrix)
3. [Phân tích 3 Chân dung Người dùng Chuyên sâu (In-Depth User Personas)](#3-phân-tích-3-chân-dung-người-dùng-chuyên-sâu-in-depth-user-personas)
   - 3.1 [Phương pháp luận User Archetypes (Alan Cooper's Goal-Directed Design)](#31-phương-pháp-luận-user-archetypes-alan-coopers-goal-directed-design)
   - 3.2 [Persona 1: Nguyễn Văn An — Sinh viên năm cuối ngành CNTT (Primary Persona - IT Student Archetype)](#32-persona-1-nguyễn-văn-an--sinh-viên-năm-cuối-ngành-cntt-primary-persona---it-student-archetype)
   - 3.3 [Persona 2: Trần Minh Hùng — Kỹ sư Cơ khí tự học chuyển ngành IT (Secondary Persona - 24.4%)](#33-persona-2-trần-minh-hùng--kỹ-sư-cơ-khí-tự-học-chuyển-ngành-it-secondary-persona---244)
   - 3.4 [Persona 3: Lê Thu Mai — Chuyên viên Phân tích tự học chứng chỉ AWS (Tertiary Persona - 13.4%)](#34-persona-3-lê-thu-mai--chuyên-viên-phân-tích-tự-học-chứng-chỉ-aws-tertiary-persona---134)
4. [Ma trận Ánh xạ Persona sang Tính năng & Yêu cầu Kỹ thuật](#4-ma-trận-ánh-xạ-persona-sang-tính-năng--yêu-cầu-kỹ-thuật)
5. [Góc Nhìn Cố Vấn Khóa Luận (Defense Guidance on Actors & Personas)](#5-góc-nhìn-cố-vấn-khóa-luận-defense-guidance-on-actors--personas)

---

## 1. Phân biệt Lý thuyết giữa Tác nhân Hệ thống & Chân dung Người dùng

### 1.1 Cơ sở khoa học kỹ thuật phần mềm
Trong công nghệ phần mềm và thiết kế lấy người dùng làm trung tâm (*User-Centered Design - UCD*), sinh viên thường mắc sai lầm đánh đồng giữa **Tác nhân hệ thống (System Actor)** và **Chân dung người dùng (User Persona)**. FocusFlow phân định rõ ràng hai khái niệm này theo chuẩn IEEE:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHÂN ĐỊNH KHÁI NIỆM TRONG CÔNG NGHỆ PHẦN MỀM                │
│                                                                             │
│   USER PERSONA (Tâm lý & Con người thực) ──> SYSTEM ACTOR (Vai trò logic)  │
│   - Tên gọi, tuổi, nghề nghiệp, tâm lý      - Vai trò logic trừu tượng      │
│   - Động lực, nỗi đau, thói quen học        - Ranh giới tương tác hệ thống  │
│   - Ngữ cảnh thực tế đời sống               - Phân quyền API & Bảo mật      │
│   - Dùng để: Thiết kế trải nghiệm (UX)      - Dùng để: Mô hình hóa UML/SRS  │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **System Actor (Tác nhân Hệ thống):**
   - Là một **thực thể logic trừu tượng** (có thể là con người, hệ thống phần cứng, hoặc dịch vụ phần mềm bên ngoài) tương tác trực tiếp với hệ thống phần mềm qua ranh giới hệ thống (*System Boundary*).
   - Actor đại diện cho *vai trò* (Role) chứ không đại diện cho một cá nhân cụ thể. Actor được sử dụng trong Biểu đồ Ca sử dụng (Use Case Diagram), Biểu đồ Tuần tự (Sequence Diagram) và ma trận phân quyền bảo mật (RBAC).
2. **User Persona (Chân dung Người dùng):**
   - Là một **hình mẫu người dùng hợp thành mang tính thực chứng** (*Composite User Archetype*) theo phương pháp luận *Goal-Directed Design* của Alan Cooper (1999), đại diện cho một nhóm người dùng mục tiêu có cùng mô thức hành vi, mục tiêu, động lực và các điểm nghẽn tâm lý.
   - Persona không phải là một cá nhân được chỉ đích danh ngoài đời thực, mà là công cụ mô hình hóa nhận thức giúp đội ngũ phát triển thấu cảm sâu sắc nỗi đau của người dùng (*Empathy*) để đưa ra các quyết định thiết kế công thái học chuẩn mực.

### 1.2 Mối quan hệ tương quan trong chu trình phát triển
Nhiều Personas khác nhau ngoài đời thực (Sinh viên năm cuối, Kỹ sư chuyển ngành, Chuyên viên ôn thi chứng chỉ) khi đăng nhập vào hệ thống đều tương tác dưới cùng một vai trò kỹ thuật duy nhất là **Learner Actor**. Tuy nhiên, các Persona khác nhau sẽ sử dụng các tính năng và chế độ cấu hình khác nhau (ví dụ: An dùng Mode B với khung giờ tối cố định; Hùng dùng Mode A với quỹ giờ linh hoạt; Mai dùng tính năng WebCal Feed để đồng bộ lịch công tác).

---

## 2. Đặc tả Chi tiết 4 Tác nhân Hệ thống (System Actors Specification)

Theo kiến trúc phân tầng trong [SRS v1.0 (Mục 3.1)](../srs/srs-v1.0.md#193-220), hệ thống FocusFlow có đúng 4 tác nhân:

### 2.1 Tác nhân Người học (Learner - Primary Human Actor)
- **Bản chất:** Con người thực tế tương tác với hệ thống qua trình duyệt Web.
- **Ranh giới tương tác:** Giao diện Web Application (Desktop & Mobile).
- **Trách nhiệm chính:**
  - Khởi tạo tài khoản cá nhân, bảo vệ thông tin mật khẩu phiên đăng nhập.
  - Cấu hình thời gian rảnh khả dụng (Mode A hoặc Mode B).
  - Khởi tạo mục tiêu, tương tác làm rõ và chủ động bấm nút "Apply" để lưu Schedule Proposal thành Official Schedule.
  - Vận hành các phiên học trong Study Workspace (bấm giờ Pomodoro, tick hoàn thành task, ghi Scratchpad và Key Takeaways).
  - Kích hoạt yêu cầu sắp xếp lại (AI Reprioritization) hoặc thiết lập Tạm dừng lộ trình (Pause Roadmap) khi có biến cố.
  - Quản lý và làm mới mã WebCal Token của chính mình.
- **Cơ chế xác thực & Bảo mật:** Xác thực qua Email/Mật khẩu băm (Argon2id/bcrypt), cấp phiên làm việc bằng Session Token / JWT mang cờ bảo mật `HttpOnly`, `SameSite`. Mọi thao tác đều bị ràng buộc bởi `user_id`.

---

### 2.2 Tác nhân Quản trị viên (Administrator - Platform Service Role)
- **Bản chất:** Vai trò kỹ thuật vận hành nền tảng (Service Role / Infrastructure Role).
- **Ranh giới tương tác:** Tầng middleware dịch vụ và cấu hình hệ thống (file cấu hình / biến môi trường), **không xây dựng giao diện Web Admin riêng biệt** nhằm tối ưu phạm vi đồ án theo [SRS Mục 2.5](../srs/srs-v1.0.md#182-188).
- **Trách nhiệm chính:**
  - Cấu hình hạn mức gọi AI (Tokens / Requests quota) cho phân tầng tài khoản `FREE` và `PREMIUM` tại Quota Service Middleware.
  - Giám sát trạng thái hoạt động, chỉ số độ sẵn sàng (Uptime Monitor) và độ trễ hệ thống.
  - Quản trị các biến môi trường nhạy cảm (API Keys, JWT Secrets).

---

### 2.3 Tác nhân Nhà cung cấp AI (External LLM Provider - External System Actor)
- **Bản chất:** Hệ thống trí tuệ nhân tạo bên thứ ba (Google Gemini API / OpenAI API / Anthropic Claude API) cung cấp qua giao diện đám mây.
- **Giao thức tương tác:** HTTPS RESTful API qua cổng bảo mật TLS 1.3; bắt buộc hỗ trợ **Structured JSON Outputs (JSON Schema)**.
- **Trách nhiệm chính:**
  - Tiếp nhận prompt chứa thông tin mục tiêu học tập đã được làm sạch (Sanitized).
  - Sinh phản hồi phân rã Milestones, Schedule Proposal hoặc AI Review định kỳ theo đúng định dạng JSON Schema trong thời gian quy định ($\le 55$ giây).
- **Ràng buộc an toàn:** Hệ thống FocusFlow coi External LLM là một hệ thống không đáng tin cậy hoàn toàn; mọi payload trả về đều phải đi qua **Schema Validation Gate** và không được tự động ghi đè cơ sở dữ liệu chính thức.

---

### 2.4 Tác nhân Ứng dụng Lịch Ngoại vi (External Calendar Application - External Consumer)
- **Bản chất:** Các phần mềm lịch tiêu chuẩn trên thiết bị của người dùng (Google Calendar, Apple Calendar, Microsoft Outlook Calendar).
- **Giao thức tương tác:** Giao thức **WebCal HTTP/HTTPS GET 1-Chiều** định dạng iCalendar RFC 5545 (`.ics`).
- **Trách nhiệm chính:**
  - Định kỳ gửi HTTP GET request kèm mã token bảo mật ngẫu nhiên `{user_secure_token}` để kéo dữ liệu lịch học về máy cá nhân của người dùng.
  - Hiển thị các sự kiện học tập song song với lịch sinh hoạt cá nhân.
- **Ràng buộc bảo mật:** Tuyệt đối là luồng đọc dữ liệu một chiều (1-Way Read-Only); hệ thống FocusFlow không tiếp nhận bất kỳ thay đổi nào từ ứng dụng lịch ngoài dội ngược về.

---

### 2.5 Ma trận Trách nhiệm & Phân quyền Tác nhân (Actor Responsibility Matrix)

| Chức năng & Nghiệp vụ Hệ thống | Learner | Administrator | External LLM | External Calendar |
|---|:---:|:---:|:---:|:---:|
| Đăng ký, đăng nhập & quản lý phiên | **Chủ trì** | Giám sát | - | - |
| Cấu hình thời gian rảnh (Mode A / B) | **Chủ trì** | - | - | - |
| Sinh đề xuất Milestones & Proposal | Kích hoạt & Phê duyệt | - | **Thực thi** | - |
| Chặn vượt quỹ giờ (Backend Ceiling) | Chịu ảnh hưởng | Cấu hình | - | - |
| Thực thi phiên học trong Workspace | **Chủ trì** | - | - | - |
| Quét quá hạn tất định (Deterministic) | Nhận thông báo | - | - | - |
| Tạm dừng lộ trình (Domino Shift) | **Chủ trì** | - | - | - |
| Đăng ký theo dõi WebCal Feed | Cấp & Đổi Token | - | - | **Đọc (GET)** |
| Quản lý Hạn ngạch Quota & Mock Sandbox | Người dùng | **Cấu hình** | - | - |
| Tổng kết định kỳ & AI Review | Yêu cầu & Đọc | - | **Phân tích** | - |

---

## 3. Phân tích 3 Chân dung Người dùng Chuyên sâu (In-Depth User Personas)

### 3.1 Phương pháp luận User Archetypes (Alan Cooper's Goal-Directed Design)
Theo phương pháp luận Thiết kế Định hướng Mục tiêu (*Goal-Directed Design - GDD*) của Alan Cooper (1999) — công trình kinh điển đặt nền móng cho kỹ thuật Persona trong kỹ nghệ phần mềm: Persona không phải là một người dùng có thật với họ tên hay số căn cước cá nhân cụ thể, mà là một **Hình mẫu Hợp thành (Synthesized Composite Archetype)** được xây dựng từ việc trừu tượng hóa các mục tiêu, mô thức hành vi, rào cản tâm lý và môi trường kỹ thuật của người dùng.

Dựa trên nghiên cứu báo cáo ngành công nghệ (Stack Overflow Developer Survey, tỷ lệ bỏ cuộc MOOCs 85-95% trên tạp chí *Science*) kết hợp nhật ký thực nghiệm công thái học (Cognitive Walkthrough), FocusFlow thiết lập **3 User Archetypes** chủ đạo:

1. **Archetype 1 — IT Student Archetype (Minh họa: Sinh viên An, 21 tuổi):** Đại diện cho phân khúc sinh viên kỹ thuật/công nghệ (~60%), có nền tảng công nghệ tốt nhưng bị quá tải bởi khối lượng tài liệu khổng lồ và thiếu năng lực phân rã mục tiêu thành các đầu việc hàng ngày.
2. **Archetype 2 — Career Switcher Archetype (Minh họa: Kỹ sư Hùng, 26 tuổi):** Đại diện cho phân khúc người đi làm tự học chuyển nghề (~25%), có quỹ thời gian rất hạn hẹp (1.5h/tối), thường xuyên đối mặt với hiện tượng suy hao ý chí sau giờ làm và lịch trình dễ bị đứt gãy do tăng ca đột xuất.
3. **Archetype 3 — Certification Seeker Archetype (Minh họa: Chuyên viên Mai, 24 tuổi):** Đại diện cho phân khúc người đi làm ôn thi chứng chỉ quốc tế (~15%), lịch trình di chuyển linh hoạt, đòi hỏi sự đồng bộ chặt chẽ với ứng dụng lịch công tác (Google Calendar) và nhu cầu đúc kết kiến thức thi cử ngắn gọn.

---

### 3.2 Persona 1: Nguyễn Văn An — Sinh viên năm cuối ngành CNTT (Primary Persona - IT Student Archetype)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERSONA 1: NGUYỄN VĂN AN (PRIMARY PERSONA - SINH VIÊN CNTT NĂM CUỐI)        │
│ "Em có động lực học rất lớn nhưng luôn bị ngập trong mớ tài liệu hỗn độn."  │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ THÔNG TIN CƠ BẢN                     │ MỤC TIÊU & ĐỘNG LỰC                  │
│ - Tuổi: 21                           │ - Tự học Golang, Docker & K8s trong  │
│ - Trường: ĐH Sư phạm Kỹ thuật TP.HCM │   2 tháng để làm đồ án tốt nghiệp.   │
│ - Chuyên ngành: Kỹ thuật Phần mềm    │ - Chuẩn bị kiến thức phỏng vấn thực  │
│ - Nơi ở: TP. Thủ Đức, TP.HCM         │   tập vị trí Backend Engineer.       │
│ - Trình độ công nghệ: Khá - Giỏi     │ - Xây dựng kỷ luật học tập hàng ngày.│
├──────────────────────────────────────┴──────────────────────────────────────┤
│ ĐIỂM NGHẼN & NỖI ĐAU THỰC TẾ (PAIN POINTS)                                   │
│ 1. Bế tắc phân rã: Không biết chia khối lượng kiến thức Docker/K8s khổng lồ  │
│    thành việc gì cần làm hôm nay, việc gì làm ngày mai.                      │
│ 2. Lộ trình "chết": Dùng ChatGPT tạo roadmap rất hay nhưng nằm nguyên trong  │
│    chatbox, copy sang Notion thì mất cả buổi chiều để trang trí template.    │
│ 3. Đứt gãy lịch: Gặp tuần thi cử bận 3 ngày, quay lại thấy danh sách task    │
│    quá hạn đỏ lòm, áp lực tâm lý quá lớn nên bỏ xó luôn lộ trình.            │
├─────────────────────────────────────────────────────────────────────────────┤
│ THÓI QUEN & MÔI TRƯỜNG KỸ THUẬT                                             │
│ - Thiết bị: Laptop MacBook/Ubuntu (chính), Smartphone Android.              │
│ - Khung giờ học: Thích hợp với Mode B (Cố định 20:00 – 22:30 các tối trong tuần).│
│ - Ứng dụng thường dùng: VS Code, Terminal, Google Calendar, Notion, Spotify.│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Bản đồ Thấu cảm (Empathy Map) của Nguyễn Văn An:
- **Says (Nói):** *"Lộ trình trên mạng nhiều quá, chỗ nào cũng bảo học cái này cái kia, em không biết bắt đầu từ đâu và phân bổ thời gian thế nào cho vừa sức."*
- **Thinks (Nghĩ):** *"Mình sắp ra trường rồi mà kiến thức thực tế còn yếu quá. Nếu không có kế hoạch rõ ràng thì chắc chắn lại lướt mạng hết buổi tối."*
- **Does (Làm):** Hỏi ChatGPT xin roadmap $\rightarrow$ Lưu vào bookmark $\rightarrow$ Mở máy tính định học nhưng loay hoay tìm tài liệu và bấm giờ mất 30 phút $\rightarrow$ Mệt mỏi đóng máy đi ngủ.
- **Feels (Cảm thấy):** Lo âu về tương lai, bất lực khi nhìn kế hoạch bị vỡ nợ thời gian, nản lòng khi thấy công cụ hiện tại quá phức tạp.

#### Kịch bản Sử dụng Điển hình (User Scenario):
An đăng ký FocusFlow, nhập mục tiêu *"Tự học Backend Golang và Docker trong 6 tuần"*, chọn cấu hình Mode B rảnh từ 20h đến 22h tối thứ 2, 4, 6. AI FocusFlow đặt câu hỏi làm rõ nền tảng, sinh ra 3 Milestones. An chỉnh sửa nhẹ và bấm duyệt. Hệ thống sinh Schedule Proposal vừa khít khung giờ tối 2h/ngày. An bấm "Apply". Mỗi tối, An chỉ cần mở FocusFlow, bấm "Start Session" để học theo Pomodoro 25/5, ghi chép nhanh code snippet vào Scratchpad và lưu Takeaway đúc kết trước khi tắt máy.

---

### 3.3 Persona 2: Trần Minh Hùng — Kỹ sư Cơ khí tự học chuyển ngành IT (Secondary Persona - 24.4%)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERSONA 2: TRẦN MINH HÙNG (SECONDARY PERSONA - NGƯỜI CHUYỂN NGÀNH)          │
│ "Đi làm về đã kiệt sức, tôi cần một công cụ xếp lịch sẵn để chỉ việc ngồi học."│
├──────────────────────────────────────┬──────────────────────────────────────┤
│ THÔNG TIN CƠ BẢN                     │ MỤC TIÊU & ĐỘNG LỰC                  │
│ - Tuổi: 26                           │ - Tự học Web Frontend (HTML/CSS/JS/  │
│ - Nghề nghiệp: Kỹ sư thiết kế Cơ khí │   React) trong vòng 6 tháng.         │
│ - Nơi ở: Quận 7, TP.HCM              │ - Chuyển sang làm Web Developer để có│
│ - Quỹ thời gian: Rất hạn hẹp         │   môi trường làm việc linh hoạt hơn. │
│ - Trình độ công nghệ: Cơ bản - Trung bình│ - Tận dụng tối đa 1.5h rảnh buổi tối.│
├──────────────────────────────────────┴──────────────────────────────────────┤
│ ĐIỂM NGHẼN & NỖI ĐAU THỰC TẾ (PAIN POINTS)                                   │
│ 1. Suy hao ý chí (Ego Depletion): Sau 9 tiếng làm việc căng thẳng tại nhà    │
│    máy, năng lượng tinh thần đã cạn kiệt, không còn sức tự lên kế hoạch học. │
│ 2. Phân mảnh công cụ: Mở quá nhiều tab (YouTube, Pomodoro, Google Docs) làm │
│    mất tập trung, rất dễ bị phân tâm sang lướt mạng xã hội.                  │
│ 3. Tăng ca đột xuất: Thường xuyên bị sếp yêu cầu OT đột xuất 1-2 hôm. Khi về │
│    đến nhà thì lỡ giờ học, không biết dời bài học hôm nay sang hôm nào.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ THÓI QUEN & MÔI TRƯỜNG KỸ THUẬT                                             │
│ - Thiết bị: Laptop Windows cũ, Smartphone iPhone.                           │
│ - Khung giờ học: Thích hợp với Mode A (Quỹ giờ 1.5h/ngày, cuối tuần 3h/ngày).│
│ - Ứng dụng thường dùng: Trình duyệt Chrome, Excel, Zalo, YouTube.           │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Bản đồ Thấu cảm (Empathy Map) của Trần Minh Hùng:
- **Says (Nói):** *"Tôi chỉ có đúng 1 tiếng rưỡi mỗi tối. Tôi không muốn làm thư ký đi kéo thả lịch hay học cách dùng Notion phức tạp, tôi chỉ muốn vào là học ngay."*
- **Thinks (Nghĩ):** *"Mình bắt đầu học lập trình ở tuổi 26 là khá muộn. Nếu không kiên trì từng ngày thì sẽ mãi giậm chân tại chỗ ở công việc cũ."*
- **Does (Làm):** Đi làm về mệt $\rightarrow$ Bật máy tính $\rightarrow$ Không biết hôm nay phải học gì tiếp theo $\rightarrow$ Xem video YouTube giải trí rồi đi ngủ trong cảm giác tội lỗi.
- **Feels (Cảm thấy):** Mệt mỏi thể xác, áp lực tài chính và tuổi tác, sợ bị bỏ lại phía sau.

#### Kịch bản Sử dụng Điển hình (User Scenario):
Hùng sử dụng chế độ Mode A (Quỹ giờ rảnh: ngày thường 1.5 tiếng, thứ Bảy 3 tiếng, Chủ Nhật nghỉ). FocusFlow tự động xếp các task ngắn 30–45 phút vừa khít quỹ giờ 1.5h. Thứ Năm tuần này, Hùng phải tăng ca đến 22h, Hùng bấm nút **"Pause Roadmap"** chọn nghỉ 2 ngày. Thuật toán **Domino Shift** của FocusFlow tự động đẩy toàn bộ bài học lùi về sau đúng số ngày tương ứng, giữ nguyên logic bài học. Hùng an tâm làm việc mà không bị cảm giác "nợ bài" dằn vặt.

---

### 3.4 Persona 3: Lê Thu Mai — Chuyên viên Phân tích tự học chứng chỉ AWS (Tertiary Persona - 13.4%)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERSONA 3: LÊ THU MAI (TERTIARY / EDGE PERSONA - ÔN THI CHỨNG CHỈ QUỐC TẾ)  │
│ "Tôi cần lịch học xuất hiện trên Google Calendar công việc để không bị quên."│
├──────────────────────────────────────┬──────────────────────────────────────┤
│ THÔNG TIN CƠ BẢN                     │ MỤC TIÊU & ĐỘNG LỰC                  │
│ - Tuổi: 24                           │ - Ôn thi đỗ chứng chỉ AWS Certified  │
│ - Nghề nghiệp: Data Analyst          │   Solutions Architect Associate (SAA)│
│ - Nơi ở: Quận Cầu Giấy, Hà Nội       │   trong vòng 8 tuần.                 │
│ - Trình độ công nghệ: Khá            │ - Đạt yêu cầu thăng tiến lên Senior. │
├──────────────────────────────────────┴──────────────────────────────────────┤
│ ĐIỂM NGHẼN & NỖI ĐAU THỰC TẾ (PAIN POINTS)                                   │
│ 1. Lịch trình công việc dày đặc: Thường xuyên họp hành, công tác đột xuất    │
│    khiến thời gian học bị xé nhỏ thành các khoảng trống 45 phút - 1 tiếng.   │
│ 2. Quên lịch học: Không có thói quen mở thêm một app riêng để xem lịch; chỉ  │
│    theo dõi duy nhất ứng dụng Google Calendar công ty trên điện thoại.       │
│ 3. Khó tổng kết kiến thức: Các bài lab thực hành AWS rất dài, học xong không │
│    đúc kết được điểm cốt lõi để ôn tập trước ngày thi.                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ THÓI QUEN & MÔI TRƯỜNG KỸ THUẬT                                             │
│ - Thiết bị: MacBook Pro công ty, iPhone, iPad.                              │
│ - Khung giờ học: Linh hoạt (trưa 12:00 – 13:00 hoặc sáng sớm 6:00 – 7:00).   │
│ - Ứng dụng thường dùng: Google Calendar, Slack, Notion, Jira.               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Bản đồ Thấu cảm (Empathy Map) của Lê Thu Mai:
- **Says (Nói):** *"Nếu lịch học không nằm trên Google Calendar của tôi, nó coi như không tồn tại."*
- **Thinks (Nghĩ):** *"Thi chứng chỉ này tốn 150$, mình bắt buộc phải thi đỗ ngay lần đầu, không thể học kiểu tài tử được."*
- **Does (Làm):** Đăng ký thi $\rightarrow$ Lên lịch rất hoành tráng $\rightarrow$ Cuộc họp công ty chèn vào giờ học $\rightarrow$ Quên bẵng lịch học.
- **Feels (Cảm thấy):** Bận rộn liên miên, căng thẳng vì hạn chót ngày thi cận kề.

#### Kịch bản Sử dụng Điển hình (User Scenario):
Mai dùng FocusFlow tạo lộ trình ôn thi AWS. Sau khi Apply lịch chính thức, Mai vào mục Tích hợp lịch, lấy đường dẫn **Secure WebCal Feed Token** và dán vào Google Calendar trên iPhone. Từ đó, các buổi học FocusFlow tự động hiển thị mượt mà trên ứng dụng lịch điện thoại của Mai. Khi kết thúc mỗi buổi học trong FocusFlow, Mai bắt buộc phải điền trường **Key Takeaway** (ví dụ: *"S3 Standard phù hợp dữ liệu truy cập thường xuyên, Glacier Deep Archive mất 12h phục hồi"*). Cuối tuần, tính năng AI Review đọc lại toàn bộ các Takeaways này để tổng hợp cho Mai một bản tóm tắt ôn tập siêu ngắn gọn.

---

## 4. Ma trận Ánh xạ Persona sang Tính năng & Yêu cầu Kỹ thuật

Bảng đối chiếu chứng minh thiết kế hệ thống FocusFlow giải quyết triệt để nỗi đau của từng Persona:

| Nhóm Persona | Nỗi đau cốt tử | Nhu cầu chức năng | Tính năng & Module FocusFlow tương ứng | Yêu cầu Kỹ thuật trong SRS v1.0 |
|---|---|---|---|---|
| **An (Sinh viên CNTT)** | Không biết chia nhỏ mục tiêu lớn; lười trang trí template | Tự động phân rã 2 cấp; xem trước và chỉnh sửa trước khi lưu | Module Lập kế hoạch AI: Đối thoại làm rõ $\rightarrow$ Duyệt Milestone $\rightarrow$ Proposal $\rightarrow$ Nút Apply | `FR-PLAN-001`, `FR-PLAN-002`, `FR-PLAN-003`, `BUSR-02` |
| **An (Sinh viên CNTT)** | Mất tập trung khi mở nhiều tab tài liệu, code | Không gian phiên học tập trung, ghi chú code nhanh | Study Workspace: Pomodoro Timer + Task Checklist + Scratchpad | `FR-SESSION-001`, `FR-SESSION-002`, `NFR-PERF-002` |
| **Hùng (Chuyển ngành)** | Quỹ thời gian phân tán, không cố định khung giờ | Xếp lịch theo tổng số giờ rảnh mỗi ngày | Chế độ Thời gian rảnh Mode A: Daily Hours Quota | `FR-AVAIL-001`, `BUSR-03` |
| **Hùng (Chuyển ngành)** | Tăng ca đột xuất, áp lực nợ task quá hạn | Tạm dừng lộ trình mà không bị phạt, dời lịch tự động | Tính năng Pause Roadmap & Thuật toán tịnh tiến dây chuyền Domino Shift | `FR-PAUSE-001`, `FR-PAUSE-002`, `BUSR-07` |
| **Mai (Ôn chứng chỉ)** | Chỉ xem lịch trên Google Calendar điện thoại | Đồng bộ lịch tự động về ứng dụng lịch cá nhân | Luồng đăng ký WebCal Feed 1 chiều bảo mật token (`.ics`) | `FR-CALENDAR-002`, `FR-CALENDAR-003`, `BUSR-08` |
| **Mai (Ôn chứng chỉ)** | Học xong hay quên, thiếu đúc kết thi cử | Bắt buộc ghi nhận tóm tắt cốt lõi và tổng kết tuần | Trường bắt buộc Key Takeaways & Trợ lý AI Review định kỳ | `FR-SESSION-002`, `FR-REPORT-002`, `BUSR-09` |

---

## 5. Góc Nhìn Cố Vấn Khóa Luận (Defense Guidance on Actors & Personas)

### Câu hỏi Phản biện 1: "Tại sao trong tài liệu của em lại phân chia thành 'System Actors' và 'User Personas'? Sao không gộp chung lại làm một cho đơn giản?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, việc phân định rõ giữa System Actors và User Personas là chuẩn mực bắt buộc trong Công nghệ Phần mềm chuyên nghiệp (chuẩn ISO/IEC/IEEE 29148 và phương pháp UCD):*  
> *1. **System Actor là khái niệm kiến trúc kỹ thuật:** Dùng để trả lời câu hỏi 'Hệ thống có những vai trò logic nào tương tác qua API và cơ chế phân quyền bảo mật ra sao?'. Hệ thống của em có 4 tác nhân kỹ thuật (`Learner`, `Administrator`, `External LLM`, `External Calendar`).*  
> *2. **User Persona là công cụ thiết kế hành vi và tâm lý học:** Dùng để trả lời câu hỏi 'Người dùng thực tế là ai, họ có nỗi đau gì và họ sử dụng hệ thống trong ngữ cảnh nào?'. Cả 3 Persona An, Hùng và Mai ngoài đời đều đóng vai trò là `Learner Actor` khi đăng nhập, nhưng họ có quỹ thời gian khác nhau (Mode A vs Mode B) và thói quen khác nhau (WebCal vs Workspace Pomodoro). Sự phân định này giúp hệ thống vừa chặt chẽ về mặt kiến trúc phần mềm, vừa tối ưu công thái học cho người dùng thật."*

### Câu hỏi Phản biện 2: "Tại sao Administrator lại không có giao diện Web Admin riêng? Liệu điều này có làm giảm tính hoàn thiện của đồ án tốt nghiệp không?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, đây là một **Quyết định Thiết kế có chủ đích (Deliberate Architectural Decision)** nhằm bảo vệ phạm vi cốt lõi của đồ án theo khuyến nghị của ngành Kỹ thuật Phần mềm:*  
> *1. Trọng tâm cốt lõi của FocusFlow là giải quyết bài toán tự học thích ứng cho người dùng cá nhân (End-User Value), không phải là hệ thống quản trị nội dung (CMS/ERP).*  
> *2. Vai trò Administrator trong hệ thống FocusFlow là **Platform Service Role**: quản trị hạn ngạch gọi AI (Tokens / Request Quota) và giám sát hạ tầng. Những tác vụ này được xử lý tối ưu và bảo mật nhất tại tầng middleware cấp dịch vụ và biến môi trường.*  
> *3. Để phục vụ việc đánh giá và nghiệm thu tính năng quản trị hạn ngạch, nhóm đã xây dựng **Mock Upgrade Sandbox** trực quan trên giao diện người dùng. Việc không dàn trải nguồn lực vào trang Admin Portal giúp nhóm tập trung 100% hoàn thiện Study Workspace, thuật toán Domino Shift và tích hợp an toàn AI đạt điểm tối đa ở các tiêu chí chất lượng kỹ thuật cao nhất."*
