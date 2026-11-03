# ADR-003: Lựa chọn Nền tảng Công nghệ Frontend: Angular 21+ (Zoneless & Signals), Tailwind CSS v4, PrimeNG v21 & `openapi-typescript`

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật Kiến trúc v2.0)
* **Ngày quyết định:** 29/09/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1, TC2.3 & TC2.7 (Mức 5)
* **Yêu cầu liên quan:** `ASR-03`, `FR-PLAN-003`, `FR-SESSION-001`, `FR-SESSION-002`, `UC-01` đến `UC-19`, `NFR-UX-001`, `NFR-UX-002`, `EVAL-04`, `EVAL-05`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Giao diện người dùng của FocusFlow phục vụ toàn bộ 19 Use Cases trải dài từ người học (`Learner`) đến quản trị viên (`Administrator`), với các đặc thù kỹ thuật khắt khe:
1. **Không gian Thực thi Tập trung Thời gian thực (Pomodoro Study Workspace - `UC-10`, `UC-11`):** Đồng hồ đếm ngược Pomodoro/Stopwatch cập nhật mỗi giây, kết hợp trình soạn thảo ghi chú Markdown (Scratchpad), danh sách nhiệm vụ và cơ chế gửi Heartbeat định kỳ 60 giây.
2. **Luồng Tương tác AI Streaming 2 Chặng (`UC-06`, `UC-07`, `ASR-03`):** Hiển thị tiến trình sinh Milestones và Schedule Proposal theo thời gian thực qua Server-Sent Events (`EventSource`) với thời gian hiển thị token đầu tiên $\le 2.5\text{s}$, kết hợp giao diện kéo-thả / duyệt lịch trực quan.
3. **Biểu đồ Phân tích Học tập, Thanh toán & Quản trị Hệ thống (`UC-05`, `UC-14`, `UC-18`, `UC-19`):** Đòi hỏi bộ thành phần UI giàu tính năng (Data Table phân trang/lọc cho Admin, Timeline/Calendar, Dialog, Toast, Chart, Stepper) đạt chuẩn tiếp cận **Lighthouse Accessibility $\ge 90$** (`NFR-UX-002`).

Trong bản thiết kế sơ bộ v1.0, việc dự kiến dùng Angular 19 kèm thư viện Spartan UI bộc lộ hạn chế khi hệ thống mở rộng sang các màn hình phức tạp như bảng lịch học đa chế độ, bảng quản trị người dùng (`UC-18`), giám sát hệ thống (`UC-19`) và cổng thanh toán nâng cấp gói (`UC-05`), do Spartan UI thiếu các component doanh nghiệp hoàn chỉnh. Đồng thời, cần loại bỏ hoàn toàn `zone.js` để tối ưu hóa hiệu năng render cho bộ đếm Pomodoro.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: React SPA thuần (Vite + React + Redux Toolkit)
* *Ưu điểm:* Hệ sinh thái phổ biến.
* *Nhược điểm:* Thiếu tính chuẩn hóa nguyên bản về Dependency Injection, Router Guards dạng hàm, Reactive Forms và cấu trúc phân hệ chặt chẽ như Angular.

### Phương án B: Angular 19 (Zone.js) + Spartan UI + NgRx Store (Kiến trúc cũ v1.0)
* *Ưu điểm:* Spartan UI nhẹ dựa trên Angular CDK.
* *Nhược điểm:* `zone.js` kích hoạt kiểm tra thay đổi dư thừa mỗi khi bộ đếm `setInterval` 1s chạy; Spartan UI thiếu các component phức tạp sẵn có (DatePicker nâng cao, DataTable quản trị, Tree/Timeline, Chart) khiến nhóm tốn nhiều công sức tự chế tạo lại UI primitives; NgRx Store tạo quá nhiều boilerplate.

### Phương án C: Angular 21+ (Standalone, Zoneless, OnPush) + Tailwind CSS v4 + PrimeNG v21 + Native Signals Store (Được chọn)
* Nâng cấp lên **Angular 21+** với `standalone: true` mặc định, kích hoạt **`provideZonelessChangeDetection()`** (loại bỏ hoàn toàn `zone.js`) và áp dụng **`ChangeDetectionStrategy.OnPush`** trên 100% components.
* Sử dụng **Tailwind CSS v4** kết hợp bộ thư viện component doanh nghiệp **PrimeNG v21** (cấu hình theo kiến trúc Design Token / Semantic CSS Variables `var(--p-primary-color)`) và bộ biểu tượng **Lucide Icons**.
* Quản lý trạng thái bằng **Native Angular Signals (`signal`, `computed`, `linkedSignal`, `rxResource`)** trong các `@Injectable` Feature Store Services kết hợp RxJS cho luồng sự kiện SSE.
* Đồng bộ hợp đồng kiểu dữ liệu tự động từ FastAPI OpenAPI 3.1 bằng **`openapi-typescript`**.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C với 5 trụ cột kiến trúc Frontend v2.0:**

### 3.1. Nền tảng Angular 21+ Zoneless & OnPush
* Toàn bộ ứng dụng khởi chạy với `provideZonelessChangeDetection()`, loại bỏ hoàn toàn gói `zone.js` khỏi bundle.
* 100% components là **Standalone Components** (`standalone: true`), sử dụng `ChangeDetectionStrategy.OnPush`, cú pháp Control Flow hiện đại (`@if`, `@for`, `@switch`, `@defer`) và Signal Inputs/Outputs (`input()`, `output()`, `model()`).
* Khi bộ đếm Pomodoro cập nhật mỗi 1 giây, Angular chỉ cập nhật đúng text node chứa giá trị Signal mà không quét lại cây component cha.

### 3.2. Hệ thống Thiết kế: Tailwind CSS v4 + PrimeNG v21 + Lucide Icons & Auth Styling Chuyên biệt
* **PrimeNG v21 (Styled Mode với Semantic CSS Variables):** Cung cấp đầy đủ các thành phần phức tạp đạt chuẩn WAI-ARIA (Table, Dialog, Drawer, Select, DatePicker, Timeline, ProgressBar, Toast, ConfirmPopup) được tùy biến đồng bộ qua hệ thống biến CSS ngữ nghĩa (`--p-primary-color`, `--p-surface-*`) hỗ trợ cả Light Mode và Dark Mode tập trung.
* **Tailwind CSS v4:** Sử dụng cho bố cục (Flexbox/Grid), khoảng cách (Spacing), Typography và hiệu ứng vi tương tác (Micro-interactions) trên các phân hệ nội bộ.
* **Lucide Icons (`lucide-angular`):** Bộ icon vector tối giản, sắc nét và đồng nhất.
* **Thiết kế Chuyên biệt cho Phân hệ Xác thực (Auth Feature Slice — `UC-01`, `UC-02`):** Giao diện Auth áp dụng hệ thống thiết kế UI & SCSS chuyên biệt của Duẩn: Bộ màu Brand Tokens (`assets/color/palette.json`, `light.json`), hệ thống đa ngôn ngữ song ngữ (`assets/i18n/{vi,en}.json` qua `TranslationService` & `TranslatePipe`), và SCSS Component Styling cho 4 luồng (`sign-in`, `sign-up`, `forgot-password`, `otp-validation`). Thiết kế này tối ưu hóa tối đa trải nghiệm người dùng đầu tiên (First Impression) với hiệu ứng động mượt mà, phân tích độ mạnh mật khẩu theo entropy, và lưới nhập mã OTP 6 ô độc lập.

### 3.3. Quản lý Trạng thái bằng Native Angular Signals & Cầu nối RxJS SSE
* **Feature Store Services với Native Signals:** Mỗi phân hệ sở hữu các `@Injectable` Store Service quản lý trạng thái bằng `signal()`, `computed()`, `linkedSignal()` và `rxResource()` (không dùng NgRx cồng kềnh).
* **Cầu nối Streaming & Bất đồng bộ (RxJS $\to$ Signals):** Các luồng sự kiện thời gian thực như **2-Stage SSE (`EventSource`)** khi AI sinh lộ trình hoặc luồng timer được bọc trong RxJS `Observable`, chuyển đổi sang Signal bằng **`toSignal()`** và tự động dọn dẹp bộ nhớ qua **`takeUntilDestroyed()`**.

### 3.4. Đồng bộ Hợp đồng API Tự động qua `openapi-typescript`
* Thiết lập script sinh tự động tệp định nghĩa kiểu `frontend/src/app/core/api/schema.d.ts` trực tiếp từ đặc tả `openapi.json` (OpenAPI 3.1) của FastAPI Backend bằng công cụ **`openapi-typescript`**.
* Đảm bảo **100% Compile-Time Type Safety** giữa Pydantic v2 DTOs ở Backend và TypeScript Services ở Frontend; bất kỳ thay đổi tên trường nào từ Backend đều được phát hiện ngay lúc biên dịch Frontend.

### 3.5. Cấu trúc 9 Feature Slices & Kiểm thử Tự động (Vitest + Playwright)
Tổ chức thư mục `frontend/src/app/features/` thành **9 Feature Slices** độc lập (nạp lười qua `loadComponent` / `loadChildren`), bao phủ trọn vẹn 19 Use Cases:
1. `auth/`: Đăng ký, đăng nhập, quên mật khẩu, khởi tạo Onboarding (`UC-01`, `UC-02`).
2. `dashboard/`: Tổng quan tiến độ hôm nay, mục `Needs Attention` cảnh báo quá hạn (kèm nút `AI Reschedule`), hạn ngạch AI, truy cập nhanh phiên học.
3. `planning/` (tương ứng `roadmaps/` — `UC-06..UC-09`): Thiết lập mục tiêu, AI sinh & duyệt Milestones, sinh & duyệt Schedule Proposal.
4. `workspace/` (`UC-11`, `UC-12`): Không gian học tập Pomodoro/Stopwatch, ghi chú Markdown (`StudyNote`), Heartbeat 60s.
5. `calendar/` (tương ứng `schedule/` — `UC-10`, `UC-13`): Lịch học chính thức dạng Calendar/Timeline, đồng bộ Google Calendar OAuth2 & WebCal `.ics`.
6. `tasks/` (`UC-09`, `UC-17`): Quản lý danh sách công việc, đồ thị phụ thuộc DAG và xử lý cảnh báo chống lặp quá hạn (`STALLED` intervention dialog).
7. `analytics/` (`UC-14..UC-16`): Biểu đồ thống kê định lượng (Adherence, Velocity), báo cáo đánh giá AI định kỳ SRL và tạm dừng/tiếp tục lộ trình.
8. `settings/` (`UC-03..UC-05`, bao gồm `billing`): Thiết lập lịch rảnh Mode A/B & hồ sơ năng lực SRL (`UC-03`), nâng cấp gói Premium (`UC-04`), và **thanh toán QR (`UC-05` — `billing`)**.
9. `admin/` (`UC-18`, `UC-19`): Cổng quản trị người dùng, hạn ngạch (`UC-18`) và bảng giám sát sức khỏe hệ thống, nhật ký AI (`UC-19`).

* **Công cụ Kiểm thử:** Sử dụng **Vitest** tốc độ cao cho Unit Test (Signal Stores, Components, Pipes) và **Playwright** cho kiểm thử tích hợp đầu-cuối (E2E User Flows).

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Hiệu năng Tuyệt đối với Zoneless Signals (`ASR-03`):** Loại bỏ `zone.js` giúp giảm kích thước bundle, tăng tốc độ khởi động ứng dụng và đảm bảo bộ đếm Pomodoro cùng luồng stream token AI đạt 60 FPS mượt mà.
* **Tăng tốc Phát triển & Đảm bảo Chuẩn Tiếp cận (`NFR-UX-002`):** Kết hợp PrimeNG v21 và Tailwind CSS v4 giúp nhóm có ngay các thành phần giao diện chuẩn WAI-ARIA cho cả 9 Feature Slices mà vẫn giữ quyền kiểm soát thẩm mỹ học thuật hiện đại.
* **Không bao giờ Lệch Hợp đồng API:** `openapi-typescript` xóa bỏ hoàn toàn rủi ro viết tay interface TypeScript sai lệch so với Pydantic schema của Backend.

---

## 5. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Kiến trúc Frontend hiện đại, đồng bộ hoàn toàn với 19 Use Cases (bao gồm `admin` và `billing`); dễ dàng đóng gói thành SPA tĩnh chạy trên Nginx Alpine.
* **Kiểm chứng Tự động:** Chạy kiểm tra kiểu `ng build --configuration production`, chạy unit test bằng `vitest run` và E2E test bằng `playwright test`.
