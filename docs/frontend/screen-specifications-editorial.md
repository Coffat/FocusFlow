# FocusFlow — Đặc tả Toàn diện Danh mục Màn hình Web & Thiết kế Giao diện (Screen Specifications & UI/UX Design Blueprint)

> **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
> **Chuyên ngành:** Kỹ thuật Phần mềm — Khóa luận Tốt nghiệp CNTT  
> **Căn cứ kỹ thuật & Tiêu chuẩn:**
> - **SRS v1.0:** Truy vết toàn bộ 14 phân hệ yêu cầu chức năng (`FR-AUTH` đến `FR-ADM`) và yêu cầu phi chức năng (`NFR-UX-001`, `NFR-UX-002`, `NFR-SEC-001`).
> - **ADR-003:** Angular 19 (Standalone Components, Signals & Computed), TypeScript Strict, Tailwind CSS v4, Spartan UI (Brain/Helm primitives), RxJS & Reactive Services.
> - **Tiêu chuẩn Tiếp cận & Công thái học:** WCAG 2.2 Level AA, Google Lighthouse Accessibility $\ge 90/100$, Rubric Đồ án Tốt nghiệp TC2.1 & TC2.7 (Mức 5).
> - **Đối tượng Người dùng Trọng tâm:** Sinh viên Đại học & Người tự học mọi khối ngành (General College Students & Lifelong Learners) — bao gồm Ngoại ngữ (IELTS, HSK, JLPT), Chứng chỉ nghề nghiệp (CFA, ACCA, PMP, AWS), Kinh tế, Kỹ thuật và Công nghệ.
> - **Phong cách Thiết kế Chủ đạo (Design Aesthetic):** **Modern Minimalist Luxury Editorial** — Tối giản cao cấp lấy cảm hứng từ website kiến trúc trong ảnh tham chiếu: nền trắng/đen tương phản mạnh, typography sans-serif cỡ lớn, bố cục editorial bất đối xứng, ảnh giàu tính kể chuyện, lưới nội dung tinh gọn, khoảng trắng có chủ đích và CTA đen dạng pill. Áp dụng có chọn lọc cho SaaS học tập: landing page giàu tính thương hiệu; màn hình làm việc và dashboard vẫn ưu tiên khả năng đọc, thao tác nhanh và mật độ thông tin hợp lý.

---

## MỤC LỤC
1. [Hệ thống Thiết kế & Ngôn ngữ Thị giác (Design System & Visual Language)](#1-hệ-thống-thiết-kế--ngôn-ngữ-thị-giác-design-system--visual-language)
2. [Sơ đồ Điều hướng & Kiến trúc Thông tin (Information Architecture & Navigation Flow)](#2-sơ-đồ-điều-hướng--kiến-trúc-thông-tin-information-architecture--navigation-flow)
3. [Đặc tả Chi tiết 11 Màn hình Chuẩn SRS (Comprehensive 11 Screen Specifications)](#3-đặc-tả-chi-tiết-11-màn-hình-chuẩn-srs-comprehensive-11-screen-specifications)
   - [SCR-01: Authentication & Onboarding Access](#scr-01-authentication--onboarding-access)
   - [SCR-02: Goal Setup & Baseline Context Wizard](#scr-02-goal-setup--baseline-context-wizard)
   - [SCR-03: AI 2-Level Proposal Streaming & Approval](#scr-03-ai-2-level-proposal-streaming--approval)
   - [SCR-04: Roadmap Management Dashboard & Timeline](#scr-04-roadmap-management-dashboard--timeline)
   - [SCR-05: Weekly Adaptive Schedule & Hybrid Availability](#scr-05-weekly-adaptive-schedule--hybrid-availability)
   - [SCR-06: Backlog & Task Queue Management](#scr-06-backlog--task-queue-management)
   - [SCR-07: Study Workspace (Deep Focus Engine)](#scr-07-study-workspace-deep-focus-engine)
   - [SCR-08: Adaptation & Overdue Resolution Modal/Flow](#scr-08-adaptation--overdue-resolution-modalflow)
   - [SCR-09: Periodic Analytics & AI Retrospective Review](#scr-09-periodic-analytics--ai-retrospective-review)
   - [SCR-10: Quota Management & Mock Upgrade Sandbox](#scr-10-quota-management--mock-upgrade-sandbox)
   - [SCR-11: Platform Governance & Admin Dashboard](#scr-11-platform-governance--admin-dashboard)
4. [Bộ Prompt Chuẩn Google Stitch Design Cho 11 Màn Hình Web FocusFlow](#4-bộ-prompt-chuẩn-google-stitch-design-cho-11-màn-hình-web-focusflow)

---

## 1. Hệ thống Thiết kế & Ngôn ngữ Thị giác (Design System & Visual Language)

### 1.1 Triết lý Thiết kế (Design Philosophy)

**Tham chiếu thị giác bắt buộc:** ảnh website bất động sản người dùng cung cấp trong cuộc trò chuyện — hero với tiêu đề sans-serif đen cực lớn, ảnh kiến trúc nổi bật hòa vào nền sáng, thanh điều hướng nhỏ gọn, CTA đen hình viên thuốc, bố cục chia cột editorial, đường phân tách mảnh và các section có nhịp điệu rõ ràng. Đây là tham chiếu về ngôn ngữ thị giác, không phải nội dung ngành bất động sản.

- **Luxury Editorial thay cho dashboard template:** tạo cá tính bằng tỷ lệ chữ, khoảng trắng, hình ảnh và bố cục; không dựa vào gradient tím, glassmorphism, bóng đổ dày hay hàng loạt card bo tròn.
- **Phân tầng theo ngữ cảnh:** landing page/onboarding dùng tiêu đề lớn và section thoáng; dashboard dùng lưới có kỷ luật; workspace làm bài tập trung, giảm trang trí; admin ưu tiên dữ liệu và khả năng quét nhanh.
- **Ảnh là một phần của art direction:** dùng ảnh học tập, sách, không gian học, chi tiết ghi chú hoặc hình minh họa kiến thức có chất lượng cao khi thật sự bổ trợ nội dung. Không chèn ảnh stock vào mọi màn hình; không dùng ảnh kiến trúc/bất động sản trong sản phẩm FocusFlow.
- **Tương phản chức năng:** nền trắng và mực đen là chủ đạo; một màu nhấn lạnh hoặc xanh trầm chỉ dùng để mã hóa trạng thái. Màu sắc không thay thế nhãn trạng thái, icon hoặc văn bản.
- **SaaS trước, phô diễn sau:** không áp dụng kiểu hero 120px hay khoảng trắng cực lớn vào màn hình có dữ liệu dày. Tính cao cấp đến từ hệ thống nhất quán, không phải làm khó thao tác.
- **Editorial Clarity:** Nền trắng trung tính (`#FAFAFA` / `#F1F1F1`), chữ đen có độ tương phản cao và đường kẻ mảnh. Tạo cảm giác cao cấp bằng nhịp điệu thị giác, không bằng trang trí thừa.
- **Mật độ Thông tin Thoáng đãng & Tinh tế (Mindful Breathing Space):** Bố cục sử dụng các khoảng đệm rộng rãi (`p-6`, `gap-4`), các thẻ màu trắng tinh (`#ffffff`) nổi nhẹ trên nền giấy bằng đường viền mảnh xám trung tính (`#DCDCDC`) và hầu như không dùng bóng đổ (`shadow-[0_1px_2px_rgba(0,0,0,0.03)]`).
- **Thao tác Tối giản & Tiếp cận Toàn diện (Universal Usability):** Giao diện trực quan cho người học ở bất kỳ chuyên ngành nào, hỗ trợ đầy đủ phím tắt (`Cmd+K`, `Space`, `Esc`) cho người dùng nâng cao, đạt chuẩn quốc tế **WCAG 2.2 AA / Lighthouse $\ge 90$**.

### 1.2 Bảng Mã màu Chuẩn OKLCH — Luxury Editorial Monochrome

FocusFlow dùng hệ màu đơn sắc làm nền tảng, gần với ảnh tham chiếu: trắng sạch, đen/mực than, xám trung tính và một màu nhấn chức năng có kiểm soát. Các giá trị dưới đây là token thiết kế đề xuất; cần kiểm tra contrast thực tế để đáp ứng WCAG 2.2 AA.

```css
@theme {
  /* Editorial canvas */
  --color-canvas-base: oklch(0.99 0 0);          /* #FAFAFA - nền chính */
  --color-canvas-subtle: oklch(0.965 0 0);       /* #F1F1F1 - vùng phụ/sidebar */
  --color-canvas-card: oklch(1 0 0);             /* #FFFFFF - bề mặt */
  --color-border-subtle: oklch(0.88 0 0);        /* #DCDCDC - đường phân cách mảnh */
  --color-border-hover: oklch(0.72 0 0);         /* #B5B5B5 - hover */

  /* High-contrast typography */
  --color-text-primary: oklch(0.12 0 0);         /* gần #111111 - tiêu đề/chữ chính */
  --color-text-secondary: oklch(0.38 0 0);       /* gần #555555 - mô tả */
  --color-text-muted: oklch(0.52 0 0);           /* gần #777777 - metadata */

  /* Functional accents: tiết chế, không dùng làm trang trí */
  --color-focus-sage: oklch(0.48 0.10 150);      /* xanh trầm - đang tập trung/hoàn thành */
  --color-ai-lavender: oklch(0.48 0.10 285);     /* tím trầm - tính năng AI */
  --color-warning-terracotta: oklch(0.58 0.13 55); /* cam đất - cảnh báo/quá hạn */
  --color-danger-coral: oklch(0.52 0.17 25);     /* đỏ - lỗi/phá hủy */
  --color-info-slate: oklch(0.48 0.08 235);      /* xanh slate - lịch/đồng bộ */
  --color-cta: oklch(0.12 0 0);                  /* đen - CTA chính */
  --color-cta-foreground: oklch(1 0 0);          /* trắng - chữ CTA */
}
```

**Quy tắc dùng màu:** 80–90% giao diện là trắng/đen/xám; màu semantic chỉ xuất hiện tại badge, icon trạng thái, thanh tiến độ hoặc thành phần cần nhận diện. Không tô mỗi card một màu. Không dùng gradient trang trí làm nền mặc định. CTA chính màu đen, chữ trắng, dạng pill; CTA phụ nền trắng, viền mảnh, chữ đen.

---

### 1.3 Hệ thống Phông chữ (Typography Hierarchy)
- **Primary Font (Giao diện chính):** `Inter`, `Geist` hoặc `Plus Jakarta Sans` — sans-serif hiện đại, nét gọn và rõ. Dùng weight 700–800 cho headline/hero, 500–600 cho heading cấp hai và 400–500 cho body. Headline marketing có thể rất lớn; nội dung trong dashboard không hy sinh khả năng đọc để tạo hiệu ứng editorial.
- **Monospace Font (Dữ liệu số & Bộ đếm):** `JetBrains Mono` hoặc `Geist Mono` — Sử dụng trang trọng cho:
  - Đồng hồ Pomodoro & Stopwatch đếm giây (`00:24:59`).
  - Mốc thời gian bắt đầu - kết thúc slot học (`20:00 - 21:30`).
  - Tỷ lệ phần trăm hoàn thành lộ trình (`87.5%`), mã định danh bài học (`#TSK-01`).

---

## 2. Sơ đồ Điều hướng & Kiến trúc Thông tin (Information Architecture & Navigation Flow)

```
[Khách truy cập] ───────────────► /login & /register (SCR-01)
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼ (Chưa có lộ trình)                        ▼ (Đã có lộ trình hoạt động)
          /onboarding/goal (SCR-02)                     /roadmaps (SCR-04)
                   │                                           │
                   ▼ (SSE Streaming)                           ├────────► /schedule (SCR-05)
          /roadmaps/create/proposal (SCR-03)                   │             ▲
                   │                                           │             │ (Mở Modal Quá hạn)
                   ▼ (Phê duyệt Lịch chính thức)               ├────────► [Adaptation Modal] (SCR-08)
          /schedule (SCR-05)                                   │
                   │                                           ├────────► /tasks (SCR-06 - Drawer)
                   ▼ (Bấm "Bắt đầu Học")                       │
          /workspace/[sessionId] (SCR-07)                      ├────────► /reports (SCR-09)
                   │                                           │
                   ▼ (Kết thúc phiên học)                      ├────────► /settings/billing (SCR-10)
          [Key Takeaways Modal] ──► /schedule                  │
                                                               └────────► /admin (SCR-11 - Phân quyền ADM)
```

---

## 3. Đặc tả Chi tiết 11 Màn hình Chuẩn SRS (Comprehensive 11 Screen Specifications)

---

### SCR-01: Authentication & Onboarding Access
- **Mã màn hình:** `SCR-01`
- **Tuyến đường (Route):** `/login`, `/register`
- **Truy vết Yêu cầu:** `FR-AUTH-001` (Đăng ký), `FR-AUTH-002` (Đăng nhập mật khẩu băm Argon2id), `FR-AUTH-003` (Phiên làm việc HttpOnly Cookie), `NFR-SEC-001`.
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Linear Login** & **Supabase Auth Portal**.
  - *Nên học hỏi:* Form tối giản đặt chính giữa màn hình, viền `1px solid border-subtle`, hiệu ứng ánh sáng gradient nền cực kỳ tinh tế (subtle ambient radial glow). Tự động focus vào ô Input đầu tiên.
  - *Anti-patterns cần tránh:* Sử dụng Captcha hình ảnh gây nghẽn; popup quảng cáo; lưu token vào `localStorage`.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
|                                                                         |
|                       [ Logo FocusFlow + Gradient Glow ]                 |
|                                                                         |
|                   +----------------------------------+                  |
|                   |  Đăng nhập FocusFlow             |                  |
|                   |  Quản trị lộ trình tự học cá nhân|                  |
|                   |----------------------------------|                  |
|                   |  Email                           |                  |
|                   |  [ student@university.edu.vn   ] |                  |
|                   |                                  |                  |
|                   |  Mật khẩu              [Quên?]   |                  |
|                   |  [ •••••••••••••••••••••••••   ] |                  |
|                   |                                  |                  |
|                   |  [ Đăng nhập vào Không gian Học ]|                  |
|                   |                                  |                  |
|                   |  ------------------------------- |                  |
|                   |  Chưa có tài khoản? [Đăng ký]    |                  |
|                   +----------------------------------+                  |
|                                                                         |
|                Bảo mật theo tiêu chuẩn HttpOnly Cookie (RFC 6265)       |
+-------------------------------------------------------------------------+
```

#### Phân chia Ranh giới Kỹ thuật & Quản trị Trạng thái (Angular 19)
- `src/app/features/auth/login/login.component.ts` (Standalone Component): Bảo vệ bằng `canActivate: [guestGuard]`, tự động chuyển hướng sang `/roadmaps` nếu đã đăng nhập.
- Form đăng nhập quản lý bằng Angular Reactive Forms (`FormBuilder`, `Validators.email`); trạng thái `loading`, `errorMessage` quản lý bằng Signals (`signal<boolean>(false)`); hiển thị thông báo Toast qua Spartan UI Toast service.

#### Trạng thái Giao diện (States)
- **Loading:** Nút đăng nhập hiển thị spinner `Loader2` mờ dần, các ô input bị disable.
- **Error:** Viền đỏ `border-danger-rose`, thông điệp lỗi trực tiếp bên dưới trường nhập (VD: *"Email hoặc mật khẩu không chính xác"*), mã lỗi `AUTH_INVALID_CREDENTIALS`.
- **Success:** Chuyển hướng êm ái (`router.push('/roadmaps')`) không gây giật màn hình.

---

### SCR-02: Goal Setup & Baseline Context Wizard
- **Mã màn hình:** `SCR-02`
- **Tuyến đường (Route):** `/onboarding/goal` hoặc `/roadmaps/new`
- **Truy vết Yêu cầu:** `FR-GOAL-001` (Thu thập mục tiêu), `FR-GOAL-002` (Đánh giá nền tảng & Giờ tự học/tuần), `FR-GOAL-003` (Hạn chót cam kết Deadline), `BR-001` (Giới hạn 1 lộ trình ACTIVE).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Typeform (Single-focus Flow)** & **Linear Project Setup Wizard**.
  - *Nên học hỏi:* Thiết kế dạng thẻ bước (Step-by-step Card), phím tắt `Tab` và `Enter` để sang bước kế tiếp. Thanh tiến trình phân đoạn (Segmented Progress Bar) ở đỉnh màn hình.
  - *Anti-patterns cần tránh:* Đưa ra một form dài 20 trường làm người dùng quá tải nhận thức.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| [FocusFlow]          [== 1. Mục tiêu ==] ── 2. Nền tảng ── 3. Quỹ giờ   |
+-------------------------------------------------------------------------+
|                                                                         |
|           Bước 1/3: Bạn muốn chinh phục kỹ năng/môn học nào?            |
|                                                                         |
|   +-----------------------------------------------------------------+   |
|   | Tên mục tiêu học tập (Target Goal)                              |   |
|   | [ Master Backend FastAPI & Hexagonal Architecture             ] |   |
|   +-----------------------------------------------------------------+   |
|                                                                         |
|   Chọn cấp độ xuất phát điểm hiện tại:                                  |
|   +-------------------+  +-------------------+  +-------------------+   |
|   | [x] Beginner      |  | [ ] Intermediate  |  | [ ] Advanced      |   |
|   | Mới bắt đầu, cần  |  | Đã nắm cú pháp cơ |  | Đã đi làm, muốn   |   |
|   | học từ nền tảng   |  | bản, cần thực hành|  | đào sâu kiến trúc |   |
|   +-------------------+  +-------------------+  +-------------------+   |
|                                                                         |
|   Cam kết số giờ học mỗi tuần: [  12  ] giờ / tuần                      |
|   Hạn chót hoàn thành dự kiến: [ 30/11/2026 ] (Cách 7 tuần)             |
|                                                                         |
|               [ < Quay lại ]          [ Tiếp tục: Phân rã AI > ]        |
+-------------------------------------------------------------------------+
```

#### Phân chia Ranh giới Kỹ thuật & Quản trị Trạng thái (Angular 19)
- `src/app/features/goals/goal-wizard/goal-wizard.component.ts` (Standalone Component): Tích hợp Route Guard kiểm tra điều kiện nghiệp vụ `BR-001` (chuyển hướng nếu đã có lộ trình `ACTIVE`).
- Quản lý các bước Wizard thông qua Angular Signal State (`currentStep = signal(1)`); form đa bước với Reactive Forms, xác thực giá trị `hours_per_week` từ 3 đến 40 giờ.

---

### SCR-03: AI 2-Level Proposal Streaming & Approval
- **Mã màn hình:** `SCR-03`
- **Tuyến đường (Route):** `/roadmaps/create/proposal`
- **Truy vết Yêu cầu:** `FR-PLAN-001` (Sinh lộ trình AI), `FR-PLAN-002` (Duyệt Cấp 1: Milestones), `FR-PLAN-003` (Duyệt Cấp 2: Tasks & Lịch chi tiết), `FR-AI-001` (SSE Streaming), `FR-AI-002` (Kiểm soát 55s timeout & Retry).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Claude Artifacts Split View** & **Cursor Composer / Notion AI**.
  - *Nên học hỏi:* Giao diện chia 2 cột: Cột trái hiển thị tiến trình suy luận và luồng log trực tiếp (Thought Stream via SSE); Cột phải hiển thị cấu trúc Milestone/Task dạng cây tương tác (Interactive Tree) tự động bung nở theo thời gian thực với hiệu ứng fade-in.
  - *Anti-patterns cần tránh:* Màn hình loading trắng trơn hoặc spinner xoay vòng vô tận trong lúc chờ AI xử lý 20-30 giây.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| [FocusFlow] AI Roadmap Generator: Master FastAPI Hexagonal    [Hủy bỏ]  |
+-------------------------------------------------------------------------+
| Tiến độ AI: [=====================>              ] 65% (Tạo Tasks Cấp 2)|
+------------------------------------+------------------------------------+
|  CỘT 1: LUỒNG SUY LUẬN AI (SSE)    |  CỘT 2: BẢN THẢO LỘ TRÌNH ĐỀ XUẤT  |
|                                    |                                    |
|  [v] Đã phân tích nền tảng Python  |  ▼ MỐC 1: Domain-Driven Design     |
|  [v] Đã tối ưu khối lượng 12h/tuần |    (Tuần 1-2 | 16 giờ học)         |
|  [>] Đang phân bổ 8 tasks chi tiết |    ├── [v] Task 1: Entities & Value|
|                                    |    ├── [v] Task 2: Repositories    |
|  "Phân bổ 4 Pomodoro cho lý thuyết |    └── [v] Task 3: Unit Tests Mock |
|   Hexagonal Ports & Adapters nhằm  |                                    |
|   đảm bảo tiếp thu vững chắc..."   |  ► MỐC 2: Asynchronous & Celery   |
|                                    |    (Tuần 3-4 | 14 giờ học)         |
|  Tốc độ sinh: 42 tokens/sec        |                                    |
|  Thời gian còn lại ước tính: 8s    |  [+ Thêm Task]  [Chỉnh sửa mốc]    |
+------------------------------------+------------------------------------+
| [ Trợ giúp AI hiệu chỉnh thêm ]    |  [ Từ chối ] [ Phê duyệt Lịch này ]|
+-------------------------------------------------------------------------+
```

#### Phân chia Ranh giới Kỹ thuật & Quản trị Trạng thái (Angular 19)
- `src/app/features/roadmaps/roadmap-stream/roadmap-stream.component.ts` (Standalone Component): Sử dụng `RoadmapStreamService` lắng nghe SSE stream `/api/v1/roadmaps/generate-stream` qua RxJS `Observable` / `EventSource`.
- Trạng thái phản ứng: Cập nhật từng node của Cây Milestone/Task vào Angular Signals khi nhận event SSE `milestone_chunk` và `task_chunk`.
- Cơ chế Safety & Timeout: Tích hợp bộ đếm ngược 55 giây. Nếu quá hạn hiển thị nút `[Thử lại]` và `[Chuyển sang Lập kế hoạch Thủ công]`.

---

### SCR-04: Roadmap Management Dashboard & Timeline
- **Mã màn hình:** `SCR-04`
- **Tuyến đường (Route):** `/roadmaps` và `/roadmaps/[id]`
- **Truy vết Yêu cầu:** `FR-GOAL-004` (Dashboard tổng quan lộ trình), `FR-PAUSE-001` (Tạm dừng lộ trình), `FR-PAUSE-002` (Domino Shift tịnh tiến hạn chót), `FR-TASK-001` (Xem trạng thái Tasks).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Linear Project View** & **Roadmap.sh**.
  - *Nên học hỏi:* Thanh tiến độ tổng quan (Hero Progress Bar), thẻ Milestone có huy hiệu trạng thái (Active, In-Progress, Completed, Overdue), nút bấm "Tạm dừng Lộ trình (Pause)" với tooltip giải thích rõ cơ chế đóng băng Domino Shift.
  - *Anti-patterns cần tránh:* Nhồi nhét biểu đồ tròn phức tạp gây rối mắt; thiếu hiển thị ngày tháng hạn chót cụ thể.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| [FocusFlow]   Lộ trình: Master FastAPI Hexagonal    [Trạng thái: ACTIVE]|
| Tiến độ chung: [===============>            ] 48% (12/25 Tasks)         |
| Deadline: 30/11/2026 (Còn 32 ngày)             [ Tạm dừng Lộ trình (P) ]|
+-------------------------------------------------------------------------+
| [Chế độ xem: Timeline / Gantt]   [Danh sách Cột]   [Lọc: Tất cả / Quá hạn] |
|-------------------------------------------------------------------------|
|  MỐC 1: Domain-Driven Design & Core Entities      [ HOÀN THÀNH 100% ]   |
|  [v] TSK-01: Entity & Value Objects (4h)         Hoàn thành 02/10/2026  |
|  [v] TSK-02: Repository Interfaces (3h)          Hoàn thành 05/10/2026  |
|-------------------------------------------------------------------------|
|  MỐC 2: Hexagonal Ports & Adapters Architecture    [ ĐANG HỌC - 45% ]    |
|  [>] TSK-03: Triển khai SQLAlchemy 2.0 Adapter     [Học ngay (Enter)]   |
|      Thời gian: Hôm nay, 20:00 - 21:30 | 2 Pomodoro                     |
|  [ ] TSK-04: Viết Router FastAPI & DI Container   Dự kiến: Ngày mai    |
|-------------------------------------------------------------------------|
|  MỐC 3: Background Jobs & Celery Worker            [ SẮP TỚI - 0% ]     |
|  [ ] TSK-05: Cấu hình Redis & Task Idempotency    Dự kiến: 22/10/2026   |
+-------------------------------------------------------------------------+
```

#### Phân chia Ranh giới Kỹ thuật & Quản trị Trạng thái (Angular 19)
- `src/app/features/roadmaps/roadmap-detail/roadmap-detail.component.ts` (Standalone Component): Tải dữ liệu Roadmap, Milestones và Tasks qua `RoadmapService` sử dụng Angular `toSignal(http.get(...))`.
- `src/app/features/roadmaps/components/roadmap-toolbar.component.ts`: Nút Tạm dừng lộ trình (Pause/Resume), mở Modal xác nhận Domino Shift với lời cảnh báo số ngày tịnh tiến tự động (`FR-PAUSE`).

---

### SCR-05: Weekly Adaptive Schedule & Hybrid Availability
- **Mã màn hình:** `SCR-05`
- **Tuyến đường (Route):** `/schedule`
- **Truy vết Yêu cầu:** `FR-AVAIL-001` (Cấu hình Thời gian rảnh Lai Mode A & Mode B), `FR-SCHEDULE-001` (Hiển thị Lịch chính thức), `FR-CALENDAR-001` (Xuất luồng WebCal/iCal), `FR-ADAPT-001` (Nhận diện Task quá hạn trên lịch).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Cron (minimal calendar)** & **Amie.so**.
  - *Nên học hỏi:* Giao diện dạng lưới tuần 7 ngày (Time Grid 24h hoặc 07:00 - 23:00). Các block giờ học được bo góc 2–4px, viền màu semantic (Xanh Emerald cho slot học sắp diễn ra, Cam Amber cho slot bị trễ, Xám Subtle cho khung giờ bận). Nút "Đồng bộ Apple/Google Calendar (WebCal)" dạng 1-click copy link.
  - *Anti-patterns cần tránh:* Bắt người dùng kéo thả phức tạp mà không có phím tắt; không phân biệt rõ giữa "Giờ rảnh cá nhân" và "Phiên học thực tế".

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| [FocusFlow]  LỊCH HỌC CHÍNH THỨC  [Tuần này: 14 - 20/10] [WebCal Feed]  |
| Cấu hình rảnh: Mode A (Thứ 2,4,6) & Mode B (Tối 20:00-22:30) [Đổi cấu hình] |
+-------+------------+------------+------------+------------+------------+
| Giờ   | Thứ 2 (14) | Thứ 3 (15) | Thứ 4 (16) | Thứ 5 (17) | Thứ 6 (18) |
+-------+------------+------------+------------+------------+------------+
| 08:00 | [Trường ĐH]|            | [Trường ĐH]|            | [Trường ĐH]|
| 14:00 |            | [Làm thêm] |            | [Làm thêm] |            |
| 19:30 |            |            |            |            |            |
| 20:00 |+----------+|            |+----------+|            |+----------+|
|       || TSK-03   ||            || TSK-04   ||            || TSK-05   ||
|       || 2 Pomo   ||            || 2 Pomo   ||            || 3 Pomo   ||
|       ||[Vào học] ||            ||[Sắp tới] ||            ||[Sắp tới] ||
| 21:30 |+----------+|            |+----------+|            |+----------+|
| 22:00 | [Nghỉ ngơi]|            | [Nghỉ ngơi]|            | [Nghỉ ngơi]|
+-------+------------+------------+------------+------------+------------+
| Phím tắt: [T] Về Hôm nay | [W] Chuyển Tuần | [C] Copy Link WebCal .ics  |
+-------------------------------------------------------------------------+
```

#### Phân chia Ranh giới Kỹ thuật & Quản trị Trạng thái (Angular 19)
- `src/app/features/schedule/weekly-calendar/weekly-calendar.component.ts` (Standalone Component): Quản lý tuần hiện tại và danh sách tasks bằng Signals (`currentWeek = signal(new Date())`). Hỗ trợ tương tác bấm vào slot để bắt đầu phiên học tức thì (`SCR-07`).
- `src/app/features/schedule/components/day-override-drawer.component.ts`: Quick Drawer cho phép điều chỉnh đột xuất lịch học hôm nay (dời phiên, tăng/giảm giờ) thông qua API ngoại lệ của `FR-PAUSE`, tuyệt đối không ghi đè khuôn mẫu tuần tại `/settings` (D-03).
- `src/app/features/schedule/components/webcal-sync-modal.component.ts`: Hiển thị URL `webcal://focusflow.edu.vn/api/v1/calendar/feed/{token}.ics`, kèm hướng dẫn tích hợp Google Calendar, Apple Calendar và Outlook trong 3 bước.

---

### SCR-06: Backlog & Task Queue Management
- **Mã màn hình:** `SCR-06`
- **Tuyến đường (Route):** `/tasks` (hoặc Slide-over Drawer từ bất kỳ màn hình nào qua phím tắt `B`)
- **Truy vết Yêu cầu:** `FR-TASK-001` (Quản lý hàng đợi Backlog), `FR-TASK-002` (Điều chỉnh ước lượng Pomodoro), `FR-ADAPT-002` (Hạ task quá hạn về Backlog).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Linear Issues List** & **Things 3**.
  - *Nên học hỏi:* Danh sách công việc phẳng có nhóm theo Milestone; hỗ trợ điều hướng bằng phím mũi tên `Up/Down`, phím `Space` để chọn, phím `Cmd+E` để sửa ước lượng Pomodoro. Badge hiển thị số Pomodoro trực quan (`🍅 x 2`).
  - *Anti-patterns cần tránh:* Phải mở modal popup chỉ để đổi tên hoặc tăng giảm số Pomodoro.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| HÀNG ĐỢI CÔNG VIỆC (TASK BACKLOG)      [+ Thêm Task nhanh] [Tìm kiếm: /]|
| Sắp xếp theo: [Ưu tiên cao nhất]  |  Lọc: [Tất cả] [Chưa xếp lịch] [Quá hạn]|
+-------------------------------------------------------------------------+
| [!] QUÁ HẠN CẦN XỬ LÝ (2 Tasks)                                         |
| ├── [!] TSK-03: Sửa lỗi connection pool DB      🍅x2  Hạn: 12/10 [Xếp lại]
| └── [!] TSK-02: Viết Integration Test Redis     🍅x1  Hạn: 13/10 [Hạ Backlog]
|                                                                         |
| [*] ĐÃ LÊN LỊCH TUẦN NÀY (SCHEDULED - 5 Tasks)                          |
| ├── [>] TSK-04: Cài đặt Alembic Migration       🍅x2  Tối nay 20:00     |
| └── [ ] TSK-05: Tích hợp Celery Beat Scheduler  🍅x3  Thứ 4, 20:00      |
|                                                                         |
| [ ] CHƯA XẾP LỊCH (UNSCHEDULED BACKLOG - 8 Tasks)                       |
| ├── [ ] TSK-08: Nghiên cứu Redis Lock Redlock   🍅x2  [Kéo vào Thứ 6]   |
| └── [ ] TSK-09: Tối ưu hóa Docker Multi-stage   🍅x1  [Kéo vào Thứ 7]   |
+-------------------------------------------------------------------------+
```

---

### SCR-07: Study Workspace (Deep Focus Engine)
- **Mã màn hình:** `SCR-07`
- **Tuyến đường (Route):** `/workspace/[sessionId]`
- **Truy vết Yêu cầu:** `FR-SESSION-001` (Pomodoro Timer & Stopwatch thực thời), `FR-SESSION-002` (Tín hiệu duy trì phiên Heartbeat 60s), `FR-SESSION-003` (Bảo toàn trạng thái mất kết nối), `FR-SESSION-004` (Bản nháp Scratchpad & Checklist), `FR-SESSION-005` (Thu thập Key Takeaways khi kết thúc).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Forest**, **Endel**, **Brain.fm** & **Raycast Focus Mode**.
  - *Nên học hỏi:* Chế độ Toàn màn hình (Zen Focus Mode). Đồng hồ kỹ thuật số kích thước lớn font `JetBrains Mono`. Vòng tròn tiến độ SVG chạy mượt mà. Phím tắt `Space` để Pause/Resume. Khu vực Scratchpad tự động lưu nháp cục bộ (Auto-save Local Persistence).
  - *Anti-patterns cần tránh:* Bất kỳ banner quảng cáo, menu điều hướng gây xao nhãng; làm mất nội dung Scratchpad của người dùng khi lỡ tay F5 hoặc mất mạng.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| FocusFlow Workspace  | TSK-03: SQLAlchemy 2.0 Adapter       [ Rời phòng ]|
+-------------------------------------------------------------------------+
|                                                                         |
|                     +---------------------------+                       |
|                     |       HIỆP 1 / 2          |                       |
|                     |        21 : 45            |                       |
|                     |    [|| Tạm dừng (Space)]  |                       |
|                     +---------------------------+                       |
|                    Chế độ: Deep Focus (25 phút)                          |
|              Kết nối: Đã đồng bộ 12 giây trước (Live •)                 |
|                                                                         |
+------------------------------------+------------------------------------+
|  CHECKLIST CÔNG VIỆC TRONG PHIÊN   |  BẢN NHÁP NHẬN THỨC (SCRATCHPAD)   |
|                                    |                                    |
|  [x] Định nghĩa User SQLAlchemy Model|  Ghi chú nhanh khi đang code:      |
|  [>] Tạo AsyncSession Generator    |  - Chú ý lazy='selectin' để tránh  |
|  [ ] Viết test mock SessionFactory |    lỗi N+1 query.                  |
|                                    |  - Cần catch IntegrityError ở repo |
|  [+ Thêm gạch đầu dòng con]        |                                    |
|                                    |  (Tự động lưu nháp vào máy cục bộ) |
+------------------------------------+------------------------------------+
| Phím tắt: [Space] Pause/Play | [Esc] Thu nhỏ | [N] Ghi chú nhanh        |
+-------------------------------------------------------------------------+
```

#### Modal Thu hoạch Tri thức Kết thúc Phiên (Key Takeaways Modal)
Khi bấm "Hoàn thành Phiên học", modal bật lên bắt buộc người học ghi lại 1-2 đúc kết ngắn gọn trước khi lưu lịch sử:
```
+-------------------------------------------------------------------------+
|  CHÚC MỪNG BẠN ĐÃ HOÀN THÀNH PHIÊN HỌC! 🎓                              |
|  Tổng thời gian tập trung thực tế: 52 phút (2 Pomodoros)                |
|-------------------------------------------------------------------------|
|  Đúc kết quan trọng nhất bạn học được trong phiên này là gì?            |
|  [ Đã hiểu rõ cơ chế async session của SQLAlchemy 2.0 và cách inject  ]|
|  [ repository vào use-case FastAPI.                                   ]|
|                                                                         |
|  Đánh giá mức độ tự tin: [ ⭐ ⭐ ⭐ ⭐ ☆ ] (4/5)                         |
|                                                                         |
|                        [ Lưu & Cập nhật Lộ trình ]                      |
+-------------------------------------------------------------------------+
```

#### Phân chia Ranh giới Kỹ thuật & Quản trị Trạng thái (Angular 19)
- `src/app/features/workspace/pomodoro-timer/pomodoro-timer.component.ts` (Standalone Component): Quản lý bằng `SessionStateService` (Angular Signals). Đồng hồ tính toán dựa trên mốc thời gian tuyệt đối (`elapsed = (now - startedAt) - pausedMs`), triệt tiêu sai số trôi thời gian khi tab chạy ngầm.
- Lắng nghe sự kiện `document.visibilitychange` để tái đồng bộ ngay khi người dùng kích hoạt lại tab.
- Gửi tín hiệu duy trì phiên Heartbeat ping `/api/v1/sessions/{id}/heartbeat` định kỳ 60 giây qua RxJS `interval(60000)` có hủy tự động khi rời phòng (`destroyRef`).

---

### SCR-08: Adaptation & Overdue Resolution Modal/Flow
- **Mã màn hình:** `SCR-08`
- **Tuyến đường (Route):** Trigger tự động qua Modal khi người dùng vào `/schedule` hoặc `/roadmaps` mà có task bị quá hạn (`DERIVED: OVERDUE`).
- **Truy vết Yêu cầu:** `FR-ADAPT-001` (Nhận diện Task quá hạn), `FR-ADAPT-002` (3 Lựa chọn thích ứng), `BR-002` (Nguyên tắc bù giờ Domino Shift).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Reclaim.ai Reschedule Assistant** & **GitHub Merge Conflict Resolution**.
  - *Nên học hỏi:* So sánh rõ ràng trước và sau khi điều chỉnh. 3 phương án giải quyết dứt khoát dạng Radio Card lớn, có nhãn khuyến nghị (Recommended).
  - *Anti-patterns cần tránh:* Tự động dời lịch ngầm mà không hỏi ý kiến người dùng, làm người dùng mất cảm giác kiểm soát.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
|  CẢNH BÁO: BẠN CÓ 2 CÔNG VIỆC BỊ QUÁ HẠN HÔM NAY ⚠️                     |
|  Hệ thống nhận thấy bạn đã bỏ lỡ 2 phiên học ngày hôm qua.              |
+-------------------------------------------------------------------------+
|  Hãy chọn phương án điều chỉnh thích ứng:                               |
|                                                                         |
|  (•) PHƯƠNG ÁN 1 (KHUYẾN NGHỊ): DOMINO SHIFT TỰ ĐỘNG                     |
|      Đẩy lùi toàn bộ các phiên học tiếp theo về sau tương ứng 2 ngày.   |
|      -> Hạn chót mới của lộ trình: 02/12/2026 (Tịnh tiến thêm 2 ngày).  |
|                                                                         |
|  ( ) PHƯƠNG ÁN 2: TĂNG CƯỜNG ĐỘ (COMPACT RE-BALANCE)                    |
|      Giữ nguyên hạn chót 30/11/2026. Chèn 2 task này vào các khung rảnh |
|      cuối tuần này (Thứ 7 & Chủ Nhật).                                  |
|                                                                         |
|  ( ) PHƯƠNG ÁN 3: HẠ VỀ HÀNG ĐỢI BACKLOG                                |
|      Chuyển 2 task này về Backlog để tự xếp lịch thủ công khi rảnh.     |
|                                                                         |
|                [ Bỏ qua (Tự xử lý sau) ]    [ Áp dụng Phương án đã chọn]|
+-------------------------------------------------------------------------+
```

---

### SCR-09: Periodic Analytics & AI Retrospective Review
- **Mã màn hình:** `SCR-09`
- **Tuyến đường (Route):** `/reports` (hoặc `/reports/weekly/[weekNumber]`)
- **Truy vết Yêu cầu:** `FR-REPORT-001` (Báo cáo tiến độ tuần), `FR-REPORT-002` (AI Nhận xét & Khuyến nghị thích ứng), `EVAL-01` (Tỷ lệ hoàn thành Task), `EVAL-02` (Độ trôi lịch).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **GitHub Contribution Graph**, **WakaTime Dashboard** & **Reflect Notes AI Summary**.
  - *Nên học hỏi:* Biểu đồ nhiệt (Heatmap) thể hiện giờ học mỗi ngày trong tuần; chỉ số KPI hiển thị dạng số to rõ ràng (`JetBrains Mono`); Khung AI Insight dùng nền trắng, đường kẻ mảnh và nhãn AI màu tím trầm; không dùng viền gradient hoặc hiệu ứng phát sáng.
  - *Anti-patterns cần tránh:* Biểu đồ 3D rối mắt; các con số vô nghĩa không gắn liền với mục tiêu ban đầu.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| [FocusFlow]  BÁO CÁO HỌC TẬP TUẦN 41 (07/10 - 13/10/2026)  [Tải PDF /]  |
+-------------------------------------------------------------------------+
|  +-------------------+  +-------------------+  +-------------------+    |
|  | Tổng giờ học thật |  | Tỷ lệ hoàn thành  |  | Độ lệch kế hoạch  |    |
|  | 10.5 / 12.0 giờ   |  | 87.5%             |  | +1.2 ngày (Chậm)  |    |
|  | [=== 87.5% ===]   |  | (7 / 8 Tasks)     |  | (Đã Domino Shift) |    |
|  +-------------------+  +-------------------+  +-------------------+    |
|                                                                         |
|  PHÂN BỔ GIỜ HỌC TRONG TUẦN (HOURS/DAY):                                |
|   4h |                                                                  |
|   2h |      [■]             [■]             [■]      [■]                |
|   0h +-------T2------T3------T4------T5------T6-------T7------CN--------+
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | ✨ NHẬN XÉT & ĐÁNH GIÁ TỪ TRỢ LÝ AI (AI RETROSPECTIVE)             |  |
|  |                                                                   |  |
|  | "Bạn duy trì phong độ tập trung rất tốt vào các buổi tối T2 và T4 |  |
|  | (trung bình 2.5 giờ liên tục không ngắt quãng). Tuy nhiên phiên   |  |
|  | tối T6 có dấu hiệu mệt mỏi dẫn đến bỏ dở hiệp 2.                  |  |
|  | Khuyến nghị: Tuần tới nên giảm 1 Pomodoro vào tối T6 và chuyển    |  |
|  | sang sáng Thứ 7 để đạt trạng thái tỉnh táo nhất."                 |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

### SCR-10: Quota Management & Mock Upgrade Sandbox
- **Mã màn hình:** `SCR-10`
- **Tuyến đường (Route):** `/settings/billing`
- **Truy vết Yêu cầu:** `FR-QUOTA-001` (Kiểm soát hạn ngạch AI Calls), `FR-QUOTA-002` (Cảnh báo chạm ngưỡng 80% & 100%), `FR-QUOTA-003` (Sandbox Giả lập Nâng cấp Gói), `NFR-SEC-001`.
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Stripe Billing Portal**, **Vercel Usage Dashboard** & **OpenAI API Usage**.
  - *Nên học hỏi:* Đồng hồ đo hạn ngạch trực quan (Progress Meter Bar), thẻ so sánh tính năng giữa gói Miễn phí (Free Tier) và gói Pro mô phỏng. Nút "Nâng cấp Giả lập (Sandbox Simulation)" cho phép sinh viên trải nghiệm thanh toán mô phỏng an toàn phục vụ chấm điểm đồ án.
  - *Anti-patterns cần tránh:* Yêu cầu thẻ tín dụng thật của người dùng; giấu nhẹm số lượt gọi AI đã dùng.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| [Cài đặt] > Quản lý Hạn ngạch & Gói Trải nghiệm (Quota & Billing)       |
+-------------------------------------------------------------------------+
|  GÓI HIỆN TẠI CỦA BẠN: GÓI MIỄN PHÍ SINH VIÊN (FREE TIER)               |
|                                                                         |
|  Lượt tạo Lộ trình AI chuyên sâu:  [===========>     ] 8 / 10 lượt     |
|  Lượt AI Review đánh giá tuần:     [=======>         ] 3 / 4 tuần       |
|  (Hạn ngạch sẽ được làm mới tự động vào ngày 01 tháng sau)              |
|                                                                         |
|  +----------------------------------+---------------------------------+ |
|  | GÓI MIỄN PHÍ HIỆN TẠI            | GÓI PRO UNLIMITED (MÔ PHỎNG)    | |
|  | - 10 lượt tạo lộ trình / tháng   | - Không giới hạn lượt gọi AI   | |
|  | - Nhận xét AI tuần cơ bản        | - AI Review chuyên sâu hàng ngày| |
|  | - Đồng bộ 1 lịch WebCal          | - Không giới hạn thiết bị WebCal| |
|  |                                  |                                 | |
|  | [ Đang sử dụng ]                 | [ Trải nghiệm Nâng cấp Giả lập] | |
|  +----------------------------------+---------------------------------+ |
|                                                                         |
|  (*) Lưu ý phục vụ Đồ án Tốt nghiệp: Hệ thống sử dụng cơ chế Sandbox    |
|      mô phỏng, không thực hiện giao dịch tài chính thật.                |
+-------------------------------------------------------------------------+
```

---

### SCR-11: Platform Governance & Admin Dashboard
- **Mã màn hình:** `SCR-11`
- **Tuyến đường (Route):** `/admin` (hoặc `/admin/metrics`)
- **Truy vết Yêu cầu:** `FR-ADM-001` (Dashboard Quản trị), `FR-ADM-002` (Giám sát tiêu thụ Token & Quota người dùng), `FR-ADM-003` (Bảng điều khiển sức khỏe Celery Jobs & Database), `NFR-SEC-001` (Phân quyền Role `ADMIN`).
- **UI Web Tham khảo & Đối sánh:**
  - *Sản phẩm chuẩn:* **Vercel Admin Dashboard** & **Grafana Modern Cloud UI**.
  - *Nên học hỏi:* Bảng danh sách người dùng với avatar, vai trò (`ADMIN` / `STUDENT`), tổng số token đã gọi, trạng thái lộ trình; các thẻ trạng thái hệ thống xanh/đỏ (Postgres Healthy, Redis Connected, Celery Workers Active).
  - *Anti-patterns cần tránh:* Cho phép truy cập không kiểm tra quyền ở Route Guard (`adminGuard`); để lộ token hoặc thông tin nhạy cảm.

#### Bố cục Trực quan (ASCII Wireframe)
```
+-------------------------------------------------------------------------+
| [FocusFlow ADMIN PORTAL]    [Hệ thống: BÌNH THƯỜNG •]   [Admin: Thắng Vũ]|
+-------------------------------------------------------------------------+
|  +-------------------+  +-------------------+  +-------------------+    |
|  | Tổng Sinh viên    |  | Token AI tháng này|  | Celery Jobs Treo  |    |
|  | 142 Người dùng    |  | 2,450,120 Tokens  |  | 0 Tác vụ lỗi      |    |
|  | (128 Active)      |  | (~ $4.90 USD)     |  | (Tất cả ổn định)  |    |
|  +-------------------+  +-------------------+  +-------------------+    |
|                                                                         |
|  DANH SÁCH NGƯỜI DÙNG & TIÊU THỤ HẠN NGẠCH (RECENT STUDENTS):           |
|  +----+----------------------+---------+------------+----------+-------+|
|  | ID | Email                | Lộ trình| Tokens Dùng| Hạn ngạch| Role  ||
|  +----+----------------------+---------+------------+----------+-------+|
|  | #1 | thang.vu@hcmute...   | FastAPI | 145,200    | 8/10     | ADMIN ||
|  | #2 | duan.phan@student... | DevOps  | 89,400     | 4/10     | USER  ||
|  | #3 | lan.nguyen@...       | React19 | 12,000     | 1/10     | USER  ||
|  +----+----------------------+---------+------------+----------+-------+|
|  Trang: [ < ] [ 1 ] [ 2 ] [ 3 ] [ > ]     [ Xuất báo cáo kiểm toán CSV ]|
+-------------------------------------------------------------------------+
```

---

## 4. Bộ Prompt Chuẩn Google Stitch Design Cho 11 Màn Hình Web FocusFlow

> **Hướng dẫn nạp Prompt vào Google Stitch (stitch.withgoogle.com / Google Labs):**
> - **Canvas Frame:** Chọn chế độ **Desktop Web (1440 × 900px, tỉ lệ 16:9)**.
> - **Chế độ khởi tạo:** Standard Mode (Prompt-based) hoặc chọn Model **Gemini 2.5 / Flash**.
> - **Cấu trúc chuẩn mực:** Áp dụng mô hình chuẩn 5 thành phần của Stitch: **Bối cảnh (Context) ➔ Đối tượng (User) ➔ Mục tiêu (Goal) ➔ Bố cục & Thành phần (Layout & Components) ➔ Phong cách Thẩm mỹ (Style & Theme)**.

---

#### Hướng dẫn Định hình Phong cách Chung cho Toàn bộ Project trên Google Stitch
Khi bắt đầu một Project mới trên Google Stitch, hãy dán đoạn hướng dẫn phong cách tổng thể này vào ô mô tả dự án (Project Style Guide) hoặc phần ghi chú phong cách chung:

```text
Quy chuẩn Thẩm mỹ & Thiết kế Hệ thống FocusFlow (Project Style Guidelines):

- Phong cách chủ đạo: Modern Minimalist Luxury Editorial, dựa trên ảnh tham chiếu website kiến trúc/bất động sản người dùng cung cấp. Chỉ học ngôn ngữ thị giác, tuyệt đối không đưa nội dung bất động sản vào sản phẩm.
- Tinh thần: tối giản cao cấp, typography lớn có chủ đích, lưới editorial bất đối xứng nhẹ, khoảng trắng rộng nhưng có chức năng, hình ảnh được tuyển chọn, điều hướng gọn, đường phân cách mảnh.
- Màu sắc: đơn sắc đen/trắng/xám. Nền #FAFAFA hoặc #FFFFFF; vùng phụ #F1F1F1; chữ chính #111111; chữ phụ #555555; viền #DCDCDC. Màu trạng thái chỉ dùng tiết chế: xanh trầm #246B4A, tím AI #6D4C8D, cam cảnh báo #A85B18, đỏ lỗi #B42318, xanh thông tin #315F83.
- Typography: Inter / Geist / Plus Jakarta Sans. Headline marketing 64–112px trên desktop, weight 700–800, tracking âm nhẹ; tiêu đề màn hình 36–56px; heading section 24–32px; body 14–16px; metadata 11–13px nhưng phải đảm bảo dễ đọc. Không dùng headline cực lớn cho màn hình tác vụ dày dữ liệu.
- CTA: nút chính đen (#111111), chữ trắng, hình pill (border-radius: 999px), cao 44–52px. Nút phụ nền trắng, viền 1px xám, chữ đen; không dùng gradient làm CTA mặc định.
- Layout: Desktop 1440px; lưới 12 cột cho landing page, 8/4 hoặc 7/5 cho split view, khoảng cách cột rộng. Landing page có hero lớn, ảnh chủ đạo, section bất đối xứng và các đường kẻ mảnh. SaaS dashboard dùng sidebar/header tối giản, lưới nhất quán và card phẳng.
- Surface: ưu tiên nền phẳng, đường kẻ mảnh, bóng đổ gần như bằng 0. Card/panel thường vuông hoặc bo 2–4px; chỉ CTA/chip dùng pill. Tránh giao diện toàn bộ là những card bo tròn lớn.
- Hình ảnh: dùng ảnh học tập, sách, ghi chú, không gian học tập hoặc hình minh họa phù hợp FocusFlow; ảnh phải chất lượng cao, có art direction và không lặp lại như ảnh stock trang trí.
- Motion: transition 180–300ms, fade/slide nhẹ; không dùng hiệu ứng hào nhoáng hoặc animation liên tục.
- Áp dụng theo ngữ cảnh: marketing/onboarding = editorial rõ nét; dashboard = thông tin dễ quét; lịch = lưới mảnh và block có mã màu; workspace = tập trung tối đa; admin = bảng dữ liệu tương phản cao.
- Accessibility: giữ WCAG 2.2 AA, focus ring rõ, keyboard navigation, trạng thái không chỉ dựa vào màu sắc, responsive desktop/tablet/mobile.
- Tránh: pastel phủ toàn giao diện, gradient tím trang trí, glassmorphism, bóng đổ dày, quá nhiều icon, card lồng card, ảnh không liên quan, headline quá lớn trong form và dashboard.
```

---

### 4.1 Prompt Stitch: SCR-01 — Authentication & Onboarding Access
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình Đăng nhập & Đăng ký tài khoản (Desktop Web 1440x900px) cho nền tảng tự học thích ứng FocusFlow.

Đối tượng người dùng (User):
Sinh viên Đại học và người tự học mọi khối ngành (Kinh tế, Ngoại ngữ, Y Dược, Luật, Công nghệ), yêu thích không gian học tập tĩnh tâm, ngăn nắp và thanh lịch.

Mục tiêu màn hình (Goal):
Giúp người học đăng nhập nhanh chóng, tạo cảm giác nhẹ nhàng, an tâm và sẵn sàng bước vào không gian học tập kỷ luật như mở một trang sổ tay mới.

Bố cục & Thành phần chi tiết (Layout & Components):
- Bố cục trung tâm (Center Modal Container): Khung đăng nhập màu trắng tinh khôi rộng 420px được đặt căn giữa trên nền trắng trung tính ấm (#FAFAFA).
- Phía trên hộp đăng nhập: Logo biểu tượng FocusFlow tối giản (hình bông hoa sen cách điệu hoặc khối tròn đồng tâm tượng trưng cho sự tập trung) với tông màu than chì ấm và điểm nhấn xanh trầm chức năng.
- Tiêu đề: "Đăng nhập FocusFlow" (cỡ chữ 24px, in đậm, màu than chì #111111), phụ đề "Không gian quản trị và thực thi lộ trình tự học cá nhân hóa" (màu xám trung tính 14px).
- Các trường nhập liệu (Inputs):
  * Nhãn "Email học tập": Ô input nền trắng, bo góc 4px, viền 1px màu xám trung tính (#DCDCDC), placeholder "student@university.edu.vn" hoặc "learner@gmail.com".
  * Nhãn "Mật khẩu": Ô input có nút ẩn/hiển thị mật khẩu, kèm liên kết "Quên mật khẩu?" màu xám than bên phải.
- Nút bấm hành động chính (Primary CTA): Nút "Bắt đầu Không gian Học" kích thước lớn, chiều rộng 100%, màu đen (#111111), chữ trắng in đậm, dạng pill (border-radius: 999px).
- Phân cách: Một đường kẻ tóc mảnh 1px có chữ "HOẶC" nhẹ nhàng ở giữa.
- Đăng nhập một chạm: Nút "Tiếp tục với Google / Email Trường Đại học" viền 1px thanh mảnh, logo Google nhỏ gọn.
- Chân hộp: Dòng chữ liên kết "Chưa có tài khoản? Đăng ký miễn phí".
- Chân trang (Footer): Nhãn bảo mật nhỏ mờ: "Bảo vệ thông tin cá nhân theo tiêu chuẩn HttpOnly Cookie (RFC 6265)".

Phong cách Thẩm mỹ (Style & Theme):
- Phong cách Modern Minimalist Luxury Editorial.
- Nền màn hình trắng trung tính ấm (#FAFAFA), thẻ đăng nhập trắng muốt (#ffffff) viền xám 1px (#DCDCDC), hầu như không dùng bóng đổ (shadow-xs).
- Con trỏ chuột focus hiển thị viền xanh trầm chức năng dịu dàng, tạo cảm giác thư thái không áp lực.
```

---

### 4.2 Prompt Stitch: SCR-02 — Goal Setup & Baseline Context Wizard
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình Thiết lập Mục tiêu Tự học & Ngữ cảnh Nền tảng (Desktop Web 1440x900px, Step-by-step Wizard) của FocusFlow.

Đối tượng người dùng (User):
Sinh viên và người tự học đa ngành (chuẩn bị thi IELTS, luyện thi chứng chỉ nghề nghiệp CFA/PMP, học lập trình, hoặc nghiên cứu môn học chuyên ngành).

Mục tiêu màn hình (Goal):
Dẫn dắt người học qua quy trình 3 bước trực quan không gây bối rối, thu thập: Mục tiêu tự học cụ thể, Xuất phát điểm hiện tại, và Quỹ thời gian cam kết mỗi tuần.

Bố cục & Thành phần chi tiết (Layout & Components):
- Đầu trang: Thanh điều hướng trang nhã với logo FocusFlow bên trái, thanh tiến trình phân đoạn 3 bước (Segmented Progress Bar) ở giữa: "1. Mục tiêu (Đang chọn) ── 2. Nền tảng ── 3. Quỹ thời gian", bên phải có nút "Lưu nháp & Thoát".
- Thẻ nội dung chính (Card trắng trung tâm rộng 720px, bo góc 4px, viền xám 1px):
  * Tiêu đề lớn: "Bước 1/3: Bạn dự định chinh phục mục tiêu học tập nào?"
  * Ô nhập mục tiêu (TextArea rộng rãi): Khung nhập liệu nền trắng ngà nhạt (#fcfbfa) viền mảnh, có gợi ý placeholder sinh động:
    "Ví dụ: Luyện thi IELTS Academic đạt Target 7.5 trong 3 tháng, Ôn thi Chứng chỉ CFA Level 1, hoặc Master Lập trình Web Fullstack".
  * Chọn cấp độ xuất phát điểm (Baseline Level): Lưới 3 thẻ lựa chọn tương tác (Radio Cards):
    + Thẻ 1: "Mới bắt đầu (Beginner)" — Mô tả: "Chưa có nền tảng cơ bản, cần học bài bản từ khái niệm nhập môn".
    + Thẻ 2: "Đã có nền tảng (Intermediate)" (Được tích chọn, viền xanh trầm chức năng) — Mô tả: "Đã nắm lý thuyết cốt lõi, cần tập trung luyện đề, làm dự án và thực hành chuyên sâu".
    + Thẻ 3: "Nâng cao (Advanced)" — Mô tả: "Muốn tối ưu hóa kỹ năng, giải quyết các dạng đề/bài toán phức tạp".
  * Cam kết thời gian mỗi tuần: Thanh trượt số giờ học/tuần (Slider từ 3 đến 40 giờ), đang hiển thị số "10 giờ / tuần" bằng font chữ Monospace kỹ thuật to rõ ràng.
  * Chọn hạn chót (Deadline): Bộ chọn ngày thanh lịch hiển thị hạn chót cam kết: "30/11/2026 (còn 7 tuần)".
- Chân thẻ wizard: Nút "< Quay lại" viền xám mờ bên trái và nút nổi bật "Tiếp tục: Phân rã Kế hoạch bằng AI >" màu tím trầm (Muted Violet) với icon ngôi sao lấp lánh bên phải.

Phong cách Thẩm mỹ (Style & Theme):
- Phong cách Modern Minimalist Editorial: Giao diện sáng dịu, thanh lịch, thẻ trắng nổi nhẹ trên nền trắng trung tính.
- Thẻ được chọn có viền màu xanh thảo mộc (#246B4A) kèm dấu tích tròn nhỏ tinh tế.
```

---

### 4.3 Prompt Stitch: SCR-03 — AI 2-Level Proposal Streaming & Approval
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình Sinh Lộ trình AI Trực tiếp dạng Luồng SSE và Duyệt Đề xuất 2 Cấp độ (Desktop Web 1440x900px, Split-view) cho FocusFlow.

Đối tượng người dùng (User):
Sinh viên và người tự học đa ngành đang chờ AI tạo lộ trình cá nhân hóa và muốn trực tiếp tương tác, chỉnh sửa cấu trúc Mốc học tập (Milestones) và Nhiệm vụ (Tasks) trước khi áp dụng vào thời khóa biểu.

Mục tiêu màn hình (Goal):
Minh bạch hóa luồng phân tích của AI theo thời gian thực (Zero black-box AI), trao quyền cho người học duyệt Cấp 1 (Milestones) và Cấp 2 (Tasks chi tiết), tạo cảm giác hào hứng và làm chủ kế hoạch học tập.

Bố cục & Thành phần chi tiết (Layout & Components):
- Thanh trạng thái đỉnh: Thanh tiến độ sinh lộ trình: "Tiến độ AI: 65% — Đang phân rã bài học chi tiết cho Mốc 2", kèm đồng hồ đếm ngược an toàn 55s và nút "Hủy".
- Bố cục chia đôi 2 cột (Split View 40% - 60%):
  * CỘT TRÁI — NHẬT KÝ SUY LUẬN CỦA TRỢ LÝ AI (Thought Stream):
    + Khung nền trắng, đường kẻ xám mảnh và nhãn AI màu tím trầm (#6D4C8D), bên trong hiển thị các dòng log phân tích đang tự động gõ chữ (typing effect):
      "[v] Đã phân tích mục tiêu: Luyện thi IELTS 7.5 & Nền tảng 6.0 hiện tại"
      "[v] Đã cân đối quỹ thời gian 10 giờ/tuần qua 7 tuần"
      "[>] Đang phân bổ 6 phiên Pomodoro cho kỹ năng Writing Task 2..."
    + Lời giải thích từ AI: "Tôi ưu tiên xếp kỹ năng Nghe & Đọc vào các ngày trong tuần và dồn bài Viết luận vào Thứ Bảy để bạn có không gian tập trung sâu nhất."
    + Huy hiệu nhỏ: "Tốc độ: 42 tokens/s • Mô hình: FocusAI Engine".
  * CỘT PHẢI — CÂY LỘ TRÌNH ĐỀ XUẤT TƯƠNG TÁC (Interactive Hierarchy Tree):
    + Danh sách các Mốc học tập dạng Accordion có thể mở rộng/thu gọn:
      - Mốc 1 (Tuần 1-2 | 20 giờ): "Củng cố Từ vựng Học thuật & Cấu trúc Ngữ pháp Nâng cao" (Đã sinh xong, hiển thị 4 Tasks bên dưới kèm badge số Pomodoro 🍅x2).
      - Mốc 2 (Tuần 3-4 | 20 giờ): "Chiến thuật Giải đề Reading & Listening Chuyên sâu" (Đang sinh dở, viền nhấp nháy sáng nhẹ).
    + Các nút chỉnh sửa nhanh bên cạnh từng Task: Nút kéo đổi thứ tự, nút tăng/giảm số Pomodoro, nút thêm bài học thủ công.
- Thanh hành động đáy trang:
  * Bên trái: Nút "Nhờ AI tinh chỉnh lại" (mở ô chat mini prompt).
  * Bên phải: Nút viền xám "Hủy bỏ" và Nút nổi bật "Phê duyệt & Áp dụng vào Thời khóa biểu" màu xanh trầm chức năng.

Phong cách Thẩm mỹ (Style & Theme):
- Phong cách Minimalist AI Workspace: Nền trắng trung tính thanh nhã, các bề mặt trắng, đường phân cách xám mảnh, màu tím trầm (#6D4C8D) làm điểm nhấn cho AI.
- Các node bài học xuất hiện dạng hoạt ảnh fade-in nhẹ nhàng, typography phân cấp rõ nét.
```

---

### 4.4 Prompt Stitch: SCR-04 — Roadmap Management Dashboard & Timeline
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình Dashboard Quản trị Lộ trình & Dòng thời gian Tổng thể (Desktop Web 1440x900px) cho FocusFlow.

Đối tượng người dùng (User):
Sinh viên đại học và người tự học đang theo đuổi một lộ trình học tập ACTIVE, cần xem tổng thể tiến độ, biết hôm nay học bài gì và còn bao nhiêu ngày đến hạn chót.

Mục tiêu màn hình (Goal):
Cung cấp bức tranh toàn cảnh về tiến trình tự học, hỗ trợ theo dõi cả dạng danh sách bài học và dạng biểu đồ dòng thời gian (Timeline/Gantt), cho phép kích hoạt cơ chế Tạm dừng lộ trình (Domino Shift Pause).

Bố cục & Thành phần chi tiết (Layout & Components):
- Thanh điều hướng trên cùng: Logo FocusFlow, các tab trang nhã: "Lộ trình", "Lịch học tuần", "Hàng đợi Backlog", "Báo cáo tuần", góc phải là Avatar người dùng.
- Khu vực Hero Banner tiến độ (Thẻ trắng lớn viền 1px):
  * Tên lộ trình: "Chinh phục IELTS Academic Target 7.5" (Huy hiệu xanh trầm: "ĐANG HOẠT ĐỘNG").
  * Thanh tiến độ tổng quan: 48% (12/25 Tasks hoàn thành), thanh hiển thị thanh lịch với màu xanh trầm chức năng.
  * Thông số hạn chót: "Hạn chót: 30/11/2026 (Còn 32 ngày)" viết bằng font JetBrains Mono màu than chì.
  * Nút chức năng quan trọng: Nút "Tạm dừng Lộ trình (Pause)" màu cam đất ấm kèm tooltip: "Đóng băng lộ trình và tự động tịnh tiến hạn chót bằng Domino Shift khi có biến cố".
- Thanh công cụ điều khiển:
  * Chuyển chế độ xem: [Xem Dòng thời gian / Timeline] | [Xem Danh sách Cột / Kanban].
  * Bộ lọc trạng thái: [Tất cả] [Đang học] [Quá hạn] [Đã hoàn thành].
- Danh sách các Mốc học tập (Dạng thẻ trắng phẳng mở rộng):
  * Mốc 1: "Củng cố Từ vựng Học thuật (Academic Vocabulary)" — Huy hiệu xanh: "HOÀN THÀNH 100%".
  * Mốc 2: "Kỹ năng Viết Task 1 & Task 2 Chuyên sâu" — Huy hiệu cam đất: "ĐANG HỌC — TIẾN ĐỘ 45%":
    + Thẻ Task 1: "TSK-03: Luyện viết dạng biểu đồ Line Graph & Bar Chart" — Có nút nổi bật "Vào phòng học ngay (Enter)", mốc giờ: "Tối nay, 20:00 - 21:30 | 🍅x2 Pomodoro".
    + Thẻ Task 2: "TSK-04: Phân tích 5 bài mẫu Essay Band 8.0" — Trạng thái: "Dự kiến: Tối mai".
  * Mốc 3: "Luyện đề Full Test có bấm giờ" — Huy hiệu xám: "SẮP TỚI — 0%".

Phong cách Thẩm mỹ (Style & Theme):
- Phong cách Editorial Grid + Functional SaaS Dashboard: lưới gọn, chữ phân cấp rõ, bề mặt phẳng và khoảng trắng có chủ đích.
- Nền trắng trung tính dịu mát, các bề mặt trắng, đường phân cách xám mảnh, tạo cảm giác thư thái và hứng thú học tập mỗi ngày.
```

---

### 4.5 Prompt Stitch: SCR-05 — Weekly Adaptive Schedule & Hybrid Availability
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình Thời khóa biểu Tuần Thích ứng & Đồng bộ WebCal (Desktop Web 1440x900px, Time-Grid Calendar) của FocusFlow.

Đối tượng người dùng (User):
Sinh viên và người tự học cần quản lý thời gian biểu trong tuần, kết hợp giữa lịch học ở trường/công sở và các khung giờ tự học cá nhân, đồng bộ trực tiếp về điện thoại qua WebCal.

Mục tiêu màn hình (Goal):
Hiển thị thời khóa biểu tuần dạng lưới giờ tương tác như minimal calendar, trực quan hóa các slot học Pomodoro, đánh dấu bài học bị quá hạn, và cung cấp nút 1-click xuất luồng lịch iCal/WebCal.

Bố cục & Thành phần chi tiết (Layout & Components):
- Đầu trang:
  * Tiêu đề: "THỜI KHÓA BIỂU HỌC TẬP TUẦN" kèm bộ chọn tuần "Tuần 42: 14/10 - 20/10/2026".
  * Tóm tắt khung giờ rảnh: "Cấu hình rảnh: Mode A (Thứ 2, 4, 6) & Mode B (Buổi tối 20:00 - 22:30)" kèm nút chỉnh sửa.
  * Nút chức năng nổi bật: Nút "Đồng bộ Luồng WebCal (.ics)" màu xanh phiến đá trang nhã.
- Lưới thời gian tuần (Weekly 7-Day Time Grid):
  * Cột trục giờ bên trái (từ 07:00 đến 23:00) chia từng vạch 30 phút font monospace xám nhẹ.
  * 7 cột đại diện từ Thứ Hai đến Chủ Nhật, cột hôm nay có viền sáng xanh thảo mộc nhẹ ở đỉnh cột.
  * Các khối sự kiện trên lưới:
    + Khung bận cá nhân (Lịch học trường ĐH, Giờ làm việc): Khối màu xám nhạt hoa văn kẻ chéo kín đáo.
    + Khối phiên học FocusFlow (20:00 - 21:30 Thứ Hai): Khối thẻ trắng bo góc viền xanh lá thảo mộc (#246B4A), bên trong ghi: "TSK-03: Luyện viết Task 1 (🍅x2) — Đang diễn ra", có nút nhỏ "Vào học".
    + Khối phiên học bị trễ/quá hạn: Khối viền màu cam đất ấm (#d97706) có biểu tượng chấm than cảnh báo "Cần dời lịch bù".
- Modal Đồng bộ WebCal (Popup hiển thị khi bấm nút WebCal):
  * Hộp thoại màu trắng kích thước 500px, tiêu đề: "Đồng bộ Lịch học về Google Calendar & Apple Calendar".
  * Ô chứa liên kết WebCal: "webcal://focusflow.edu.vn/api/v1/calendar/feed/live_token_99.ics" kèm nút "Sao chép Link (Copy)".
  * 3 bước hướng dẫn nhanh bằng icon: Google Calendar, Apple Calendar, Outlook.
- Thanh phím tắt đáy: "[T] Hôm nay • [W] Chuyển tuần • [C] Sao chép Link WebCal • [Click] Tạo slot học mới".

Phong cách Thẩm mỹ (Style & Theme):
- Phong cách Minimalist Calendar UI với lưới mảnh và tương phản đơn sắc.
- Đường kẻ lưới mỏng sắc nét màu xám trung tính (#DCDCDC), các khối học tập màu xanh trầm và cam đất nổi bật hài hòa.
```

---

### 4.6 Prompt Stitch: SCR-06 — Backlog & Task Queue Management
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình hoặc Ngăn kéo Hàng đợi Bài học (Task Backlog Management, Desktop Web 1440x900px, Slide-over Drawer / Full View) của FocusFlow.

Đối tượng người dùng (User):
Sinh viên và người tự học đa ngành cần sắp xếp lại các bài học chưa lên lịch, xử lý các bài tập bị trễ hạn, hoặc điều chỉnh số Pomodoro cho từng bài học.

Mục tiêu màn hình (Goal):
Cung cấp danh sách bài học gọn gàng, hỗ trợ thao tác bàn phím nhanh, phân loại rõ ràng bài quá hạn cần can thiệp, và hỗ trợ kéo thả bài học vào các ngày trong tuần.

Bố cục & Thành phần chi tiết (Layout & Components):
- Thanh công cụ Backlog:
  * Ô tìm kiếm nhanh: "[ / ] Tìm kiếm bài học theo tên hoặc chủ đề...".
  * Bộ lọc nhanh (Filter Pills): [Tất cả 15] [Quá hạn 2] [Chưa xếp lịch 8] [Ưu tiên cao].
  * Nút "+ Thêm bài học mới" (Phím tắt 'N').
- Bố cục danh sách bài học phân nhóm:
  * Nhóm 1: "⚠️ BÀI TẬP QUÁ HẠN CẦN CAN THIỆP (2 Tasks)" (Khung viền cam đất ấm nhạt):
    + Dòng task 1: "TSK-03: Viết lại bài luận Essay 250 từ" — Hạn: Hôm qua — Badge: "🍅x2 Pomodoro" — Nút nhanh: "[Dời lịch bù]" và "[Hạ về Backlog]".
  * Nhóm 2: "📅 ĐÃ LÊN LỊCH TUẦN NÀY (5 Tasks)":
    + Dòng task: "TSK-04: Luyện đề Listening Section 3 & 4" — Lịch: Tối nay 20:00 — Badge: "🍅x2".
  * Nhóm 3: "📥 HÀNG ĐỢI CHƯA LÊN LỊCH (UNSCHEDULED - 8 Tasks)":
    + Dòng task: "TSK-08: Học 50 từ vựng chuyên ngành Tài chính" — Badge: "🍅x1" — Có nút "[+ Xếp vào Thứ Sáu]".
- Chi tiết tương tác trên từng dòng:
  * Checkbox tròn tinh tế bên trái.
  * Tên bài học in rõ nét, mã bài học monospace xám (#TSK-08).
  * Nhãn ước lượng Pomodoro tương tác: Bấm trực tiếp vào để tăng/giảm số quả cà chua (1, 2, 3, 4).
- Gợi ý phím tắt đáy: "[↑/↓] Điều hướng • [Space] Chọn bài • [Cmd+E] Đổi số Pomodoro • [Esc] Đóng".

Phong cách Thẩm mỹ (Style & Theme):
- Minimalist Task List kết hợp Things 3: Tối giản, nền trắng trung tính, dòng danh sách thanh thoát (chiều cao 44px/dòng), hover hiển thị nền xám trung tính nhẹ.
```

---

### 4.7 Prompt Stitch: SCR-07 — Study Workspace (Deep Focus Engine)
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình Không gian Thực thi Phiên học Tập trung Chuyên sâu (Study Workspace Zen Mode, Desktop Web 1440x900px) cho nền tảng FocusFlow.

Đối tượng người dùng (User):
Sinh viên và người tự học đang trong phiên học 25 phút Pomodoro (đọc sách, dịch tài liệu, làm bài tập, viết luận, luyện đề), cần một không gian tĩnh lặng tuyệt đối để não bộ đạt trạng thái dòng chảy nhận thức (Flow State).

Mục tiêu màn hình (Goal):
Cung cấp đồng hồ Pomodoro toàn màn hình chính xác từng giây, danh sách bước thực hiện (Checklist), vùng ghi chú nháp nhận thức (Scratchpad) tự lưu, và bảo đảm gửi tín hiệu duy trì phiên Heartbeat định kỳ 60 giây.

Bố cục & Thành phần chi tiết (Layout & Components):
- Thanh trên cùng tối giản (Zen Topbar):
  * Bên trái: Tên bài học: "TSK-03: Luyện viết biểu đồ Line Graph & Bar Chart" (Kèm chấm tròn xanh lá thảo mộc nhấp nháy báo hiệu phiên học Live).
  * Bên phải: Huy hiệu "Kết nối: Đã đồng bộ 15s trước (Live •)" và nút mờ "Tạm dừng & Thoát phòng".
- Khu vực Trung tâm (Hero Pomodoro Timer):
  * Vòng tròn đếm ngược đồ họa SVG kích thước lớn (đường kính 280px) với đường viền tiến độ xanh lá thảo mộc (#246B4A) thanh nhã trên nền trắng trung tính.
  * Giữa vòng tròn: Con số thời gian đếm ngược khổng lồ "21 : 45" bằng font chữ Monospace kỹ thuật (JetBrains Mono), kích thước chữ 64px, màu than chì sắc nét.
  * Phía trên số giờ: Dòng chữ nhỏ "HIỆP 1 TRÊN 2 — CHẾ ĐỘ FOCUS (25 PHÚT)".
  * Dưới số giờ: Nút bấm hình viên thuốc "|| Tạm dừng (Nhấn phím Space)" với viền mảnh xám trung tính.
- Khu vực 2 Widget bên dưới (Chia 2 cột cân xứng):
  * CỘT TRÁI — CHECKLIST BƯỚC HỌC TRONG PHIÊN:
    + Tiêu đề: "Các bước thực hiện" kèm thanh tiến độ mini (1/3 xong).
    + Danh sách các ô checkbox: "[v] Đọc và gạch chân số liệu nổi bật của đề bài", "[>] Viết đoạn Overview khái quát xu hướng (Đang viết)", "[ ] Viết 2 đoạn Body chi tiết".
    + Nút bấm nhỏ: "+ Thêm bước con".
  * CỘT PHẢI — BẢN NHÁP NHẬN THỨC (SCRATCHPAD):
    + Tiêu đề: "Vùng nháp nhận thức (Tự động lưu vào máy cục bộ)".
    + Khung soạn thảo văn bản không viền, nền trắng tinh khôi viền xám, hiển thị các ghi chú nhanh của người học: từ vựng mới, cấu trúc hay, ý tưởng luận điểm.
- Cửa sổ Thu hoạch Tri thức (Popup Key Takeaways Modal - Bật lên khi hết 2 hiệp Pomodoro):
  * Hộp thoại chúc mừng hoàn thành: "🎉 Xuất sắc! Bạn vừa hoàn thành 50 phút tập trung cao độ".
  * Ô nhập bắt buộc: "Đúc kết quan trọng nhất bạn học được trong phiên này là gì?" (TextArea 3 dòng).
  * Đánh giá mức độ tự tin: 5 ngôi sao tương tác.
  * Nút chính: "Lưu đúc kết & Đánh dấu Hoàn thành Bài học".

Phong cách Thẩm mỹ (Style & Theme):
- Minimalist Deep Focus Workspace.
- Tông màu nền trắng trung tính ấm áp (#FAFAFA), bề mặt trắng (#ffffff), điểm xuyết màu xanh trầm chức năng tạo cảm giác an nhiên, thư thái và kích thích tư duy sâu.
```

---

### 4.8 Prompt Stitch: SCR-08 — Adaptation & Overdue Resolution Modal/Flow
```text
Bối cảnh sản phẩm (Context):
Thiết kế Cửa sổ Điều chỉnh Kế hoạch Thích ứng khi có Bài học Quá hạn (Overdue Adaptation Modal Overlay, Desktop Web 1440x900px) của FocusFlow.

Đối tượng người dùng (User):
Sinh viên và người tự học quay lại hệ thống sau một ngày có việc đột xuất và phát hiện 2 bài học bị trễ hạn, cần phương án giải quyết thông minh mà không cảm thấy tội lỗi hay nản chí.

Mục tiêu màn hình (Goal):
Giải quyết bài toán "Đứt gãy kế hoạch khi có biến cố", đưa ra 3 phương án dứt khoát có tính toán khoa học (ưu tiên phương án Domino Shift tịnh tiến hạn chót tự động).

Bố cục & Thành phần chi tiết (Layout & Components):
- Lớp phủ nền: Toàn bộ trang web phía sau bị làm mờ nhẹ (blur 8px).
- Hộp thoại Trung tâm (Modal Window kích thước rộng 680px, màu trắng tinh khôi bo góc 4px viền xám):
  * Khung cảnh báo trên cùng: Biểu tượng tam giác cảnh báo màu cam đất ấm (#d97706), tiêu đề in đậm: "BẠN CÓ 2 BÀI HỌC BỊ TRỄ HẠN HÔM QUA ⚠️".
  * Nội dung mô tả: "Hệ thống nhận thấy bạn đã bỏ lỡ 2 phiên học ngày hôm qua. Đừng lo lắng! Hãy chọn một trong 3 phương án thích ứng bên dưới để sắp xếp lại:"
  * Lựa chọn 1 — THẺ KHUYẾN NGHỊ (DOMINO SHIFT TỰ ĐỘNG - Được viền cam đất ấm nổi bật):
    + Huy hiệu góc phải: "KHUYẾN NGHỊ TỐI ƯU CÔNG THÁI HỌC".
    + Nút radio tròn được tích chọn.
    + Tiêu đề: "Phương án 1: Domino Shift — Tịnh tiến toàn bộ lịch học".
    + Diễn giải: "Tự động đẩy lùi tất cả các bài học kế tiếp về sau 2 ngày. Bạn giữ nguyên nhịp độ học 10h/tuần mà không bị áp lực dồn ép."
    + So sánh ngày hạn chót: "Hạn chót cũ: 30/11/2026 ➔ Hạn chót mới: 02/12/2026 (+2 ngày)".
  * Lựa chọn 2 — THẺ TĂNG CƯỜNG ĐỘ (COMPACT RE-BALANCE):
    + Tiêu đề: "Phương án 2: Dồn bài học bù vào cuối tuần này".
    + Diễn giải: "Giữ nguyên hạn chót 30/11/2026. Tự động chèn 2 bài học này vào các khung thời gian rảnh Thứ Bảy và Chủ Nhật tuần này."
  * Lựa chọn 3 — THẺ HẠ VỀ HÀNG ĐỢI (DROP TO BACKLOG):
    + Tiêu đề: "Phương án 3: Chuyển 2 bài học này về Hàng đợi Backlog".
    + Diễn giải: "Giải phóng thời khóa biểu tuần này, bạn sẽ tự xếp lịch thủ công khi rảnh."
- Chân hộp thoại:
  * Nút phụ bên trái: "Để tôi tự xử lý sau (Bỏ qua)".
  * Nút chính bên phải: Nút lớn "Áp dụng Domino Shift & Cập nhật Lịch" màu cam đất ấm hoặc than chì sang trọng.

Phong cách Thẩm mỹ (Style & Theme):
- Phong cách Minimalist Insight Panel & Reclaim.ai.
- Màu cam đất ấm (#d97706) kết hợp nền trắng và chữ than chì tạo cảm giác thấu cảm, hỗ trợ người học vượt qua tâm lý trì hoãn.
```

---

### 4.9 Prompt Stitch: SCR-09 — Periodic Analytics & AI Retrospective Review
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình Báo cáo Đánh giá Tuần & Nhận xét Trí tuệ Nhân tạo (Weekly Analytics & AI Retrospective Review, Desktop Web 1440x900px) cho FocusFlow.

Đối tượng người dùng (User):
Sinh viên và người tự học đa ngành cuối mỗi tuần muốn nhìn lại hiệu suất học tập thực tế của mình, đối chiếu với cam kết ban đầu, và đọc lời khuyên cá nhân hóa từ AI để chuẩn bị cho tuần tới.

Mục tiêu màn hình (Goal):
Cung cấp bức tranh phân tích định lượng (giờ học thật, tỷ lệ hoàn thành, độ trôi lịch) kết hợp nhận xét định tính sâu sắc từ trợ lý AI, hỗ trợ xuất báo cáo PDF cho giảng viên hướng dẫn.

Bố cục & Thành phần chi tiết (Layout & Components):
- Đầu trang: Tiêu đề "BÁO CÁO HỌC TẬP TUẦN 41 (07/10 - 13/10/2026)", bên phải có bộ chọn tuần trước/sau và nút "Tải Báo cáo PDF / In ấn".
- Hàng 3 Thẻ Chỉ số KPI then chốt (Top Metrics Cards màu trắng bo góc 4px viền xám):
  * Thẻ 1: "Tổng giờ học thực tế" — Con số lớn "10.5 / 12.0 Giờ" (Đạt 87.5% chỉ tiêu) kèm thanh tiến độ mini màu xanh trầm.
  * Thẻ 2: "Tỷ lệ hoàn thành bài học" — Con số "87.5%" (7 trên 8 bài hoàn tất đúng hạn).
  * Thẻ 3: "Độ lệch kế hoạch (Schedule Drift)" — Con số "+1.2 Ngày" (Màu cam đất ấm — Đã điều chỉnh bằng Domino Shift).
- Biểu đồ phân bổ giờ học theo ngày (Weekly Hours Bar Chart):
  * Biểu đồ cột từ Thứ Hai đến Chủ Nhật, các cột ngày học tốt (Thứ 2, Thứ 4) có màu xanh trầm chức năng cao 2.5h, ngày nghỉ hiển thị mức thấp.
  * Trục thời gian và giờ dùng font monospace kỹ thuật.
- Hộp Nhận xét Trí tuệ Nhân tạo (AI Retrospective Card — Chiếm toàn bộ chiều rộng):
  * Thẻ nền trắng, viền xám mảnh, nhãn AI màu tím trầm (#6D4C8D) và biểu tượng lấp lánh (Sparkles) và tiêu đề: "NHẬN XÉT & KHUYẾN NGHỊ THÍCH ỨNG TỪ FOCUS-AI".
  * Nội dung trích dẫn nhận xét:
    "Bạn duy trì phong độ tập trung rất ấn tượng vào các buổi tối Thứ 2 và Thứ 4 (trung bình 2.5 giờ liên tục không ngắt quãng). Tuy nhiên, phiên học tối Thứ 6 bị bỏ dở do dấu hiệu quá tải sau một tuần làm việc.
    Khuyến nghị cho Tuần 42: Bạn nên giảm 1 Pomodoro vào tối Thứ 6 và chuyển 1 phiên sang sáng Thứ 7 để bảo toàn năng lượng."
  * Nút bấm tiện ích: "[Áp dụng lời khuyên này vào Lịch tuần tới]".

Phong cách Thẩm mỹ (Style & Theme):
- Phong cách Editorial Analytics với bố cục đơn sắc.
- Giao diện trực quan hóa dữ liệu sáng sủa, sạch sẽ, thẻ KPI viền mảnh 1px, đồ thị cột hiển thị thanh lịch không rối mắt.
```

---

### 4.10 Prompt Stitch: SCR-10 — Quota Management & Mock Upgrade Sandbox
```text
Bối cảnh sản phẩm (Context):
Thiết kế màn hình Quản lý Hạn ngạch & Trải nghiệm Nâng cấp Giả lập (Quota Usage & Mock Upgrade Sandbox, Desktop Web 1440x900px) cho nền tảng FocusFlow.

Đối tượng người dùng (User):
Sinh viên kiểm tra số lượt gọi AI còn lại trong tháng, hoặc Giảng viên/Hội đồng chấm thi muốn bấm thử tính năng Nâng cấp mô phỏng (Sandbox) để kiểm thử luồng nghiệp vụ không giới hạn.

Mục tiêu màn hình (Goal):
Minh bạch hóa lượng tài nguyên AI mà người dùng đã tiêu thụ, đưa ra cảnh báo hạn ngạch khi đạt 80% và 100%, đồng thời cung cấp môi trường Sandbox giả lập gói Pro phục vụ chấm điểm đồ án tốt nghiệp.

Bố cục & Thành phần chi tiết (Layout & Components):
- Tiêu đề trang: "Cài đặt Tài khoản ➔ Quản lý Hạn ngạch & Gói Trải nghiệm (Quota & Billing)".
- Hộp trạng thái sử dụng hiện tại (Current Usage Card):
  * Tiêu đề: "GÓI HIỆN TẠI: SINH VIÊN MIỄN PHÍ (FREE TIER)".
  * Đồng hồ đo hạn ngạch 1: "Lượt tạo Lộ trình chuyên sâu AI: 8 / 10 lượt" — Thanh tiến độ màu tím trầm đạt 80% (Kèm nhãn cảnh báo: "Sắp chạm ngưỡng tối đa trong tháng").
  * Đồng hồ đo hạn ngạch 2: "Lượt AI Review đánh giá tuần: 3 / 4 tuần".
  * Dòng ghi chú: "Hạn ngạch sẽ được hệ thống tự động làm mới vào ngày 01 tháng sau".
- Bảng so sánh 2 gói dịch vụ (Comparison Pricing Cards):
  * CỘT 1 — GÓI MIỄN PHÍ HIỆN TẠI (Thẻ trắng viền xám):
    + Giá: "0 đ / tháng".
    + Danh sách tính năng có dấu tích: 10 lượt tạo lộ trình AI, AI review tuần cơ bản, 1 liên kết lịch WebCal.
    + Nút: "Đang sử dụng (Disabled)".
  * CỘT 2 — GÓI PRO UNLIMITED (MÔ PHỎNG ĐỒ ÁN - viền xám mảnh và nhãn Pro màu tím trầm):
    + Giá: "99.000 đ / tháng" (Kèm nhãn: "MÔ PHỎNG TEST SANDBOX").
    + Tính năng nâng cấp: Không giới hạn lượt sinh lộ trình AI, AI Review chuyên sâu hàng ngày, Phân tích biểu đồ nhịp sinh học, Không giới hạn thiết bị WebCal.
    + Nút chính nổi bật: "Trải nghiệm Nâng cấp Giả lập (Mock Upgrade)" màu tím trầm sang trọng.
- Hộp thoại Thanh toán Mô phỏng (Mock Checkout Modal — Bật lên khi bấm nâng cấp):
  * Hộp thoại hiển thị thông báo rõ ràng: "Đây là môi trường Sandbox phục vụ nghiệm thu Đồ án Tốt nghiệp. Hệ thống không trừ tiền thật."
  * Nút "Kích hoạt Gói Pro Mô phỏng ngay (Success 200 OK)".

Phong cách Thẩm mỹ (Style & Theme):
- Stripe Customer Portal với bảng màu đơn sắc editorial.
- Thẻ gói Pro có viền xám mảnh; màu tím trầm chỉ dùng cho nhãn Pro, các thanh đo hạn ngạch hiển thị số liệu monospace chuẩn xác.
```

---

### 4.11 Prompt Stitch: SCR-11 — Platform Governance & Admin Dashboard
```text
Bối cảnh sản phẩm (Context):
Thiết kế Bảng Điều khiển Quản trị Nền tảng & Giám sát Hệ thống (Platform Governance & Admin Dashboard, Desktop Web 1440x900px) cho FocusFlow.

Đối tượng người dùng (User):
Quản trị viên hệ thống (Admin), Trưởng nhóm kỹ thuật, hoặc Giảng viên kiểm tra hạ tầng vận hành của nền tảng trong buổi bảo vệ khóa luận.

Mục tiêu màn hình (Goal):
Cung cấp cái nhìn toàn diện về số lượng người học đa ngành, tổng lượng token AI đã sử dụng, chi phí ước tính, trạng thái hàng đợi nền Celery Worker, và bảng quản lý phân quyền người dùng.

Bố cục & Thành phần chi tiết (Layout & Components):
- Đầu trang Admin: Tiêu đề "FOCUSFLOW ADMIN PORTAL", bên cạnh có đèn trạng thái hệ thống: "Hạ tầng: BÌNH THƯỜNG (All Systems Operational •)" màu xanh trầm chức năng, góc phải hiển thị thông tin Admin đăng nhập.
- Hàng 4 Thẻ Giám sát Tổng quan (System Overview Cards màu trắng bo góc 4px viền xám):
  * Thẻ 1: "Tổng số Người học" — Con số lớn "142 Người dùng" (128 đang có lộ trình Active).
  * Thẻ 2: "Tổng Token AI Tiêu thụ (Tháng này)" — "2,450,120 Tokens" (Ước tính chi phí API: $4.90 USD).
  * Thẻ 3: "Hàng đợi Celery Worker" — "0 Tác vụ lỗi / 12 tác vụ chạy ngầm" (Đèn xanh).
  * Thẻ 4: "Thời gian phản hồi API trung bình (p95)" — "185 ms".
- Bảng Quản trị Người dùng & Tiêu thụ Hạn ngạch (User Governance Table):
  * Thanh tìm kiếm người dùng theo Email/Tên và bộ lọc vai trò: [Tất cả Roles] [ADMIN] [LEARNER].
  * Bảng dữ liệu có tiêu đề cột rõ ràng:
    + Cột ID (#01, #02...)
    + Cột Email người học
    + Cột Tên lộ trình đang học (IELTS, CFA, FastAPI...)
    + Cột Token AI đã dùng (font monospace căn phải)
    + Cột Hạn ngạch tháng (ví dụ: 8/10)
    + Cột Vai trò (Badge màu xanh: ADMIN, Badge màu xám: USER)
    + Cột Thao tác: Nút bấm "[Reset Quota]" và "[Xem chi tiết]".
  * Chân bảng: Phân trang "[ < ] Trang 1 trên 15 [ > ]" và nút "Xuất file Báo cáo Kiểm toán (Export CSV)".

Phong cách Thẩm mỹ (Style & Theme):
- Phong cách Minimalist Admin Console kết hợp Grafana Cloud.
- Mật độ thông tin cao (High Density), bảng viền mỏng 1px sắc sảo, màu chữ than chì phân cấp dễ đọc, trạng thái hệ thống sử dụng đèn LED tròn trực quan.
```


