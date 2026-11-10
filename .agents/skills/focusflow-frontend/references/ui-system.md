# Hệ thống thiết kế: Tailwind CSS v4 + PrimeNG v21 + Lucide

Mục lục: 1. Phân vai · 2. Theme & token · 3. Dark mode · 4. Layout & responsive · 5. A11y · 6. Pattern UI chuẩn · 7. Hiệu năng

## 1. Phân vai
- **PrimeNG v21 (Styled mode)**: component phức tạp đạt WAI-ARIA — Table, Dialog, Drawer, Select/MultiSelect, DatePicker, Timeline, Stepper, ProgressBar, Toast, ConfirmPopup/ConfirmDialog, Tabs, Chart, Tree. Dùng trước khi nghĩ tới tự chế.
- **Tailwind v4**: bố cục (flex/grid), khoảng cách, typography, trạng thái/hiệu ứng nhỏ. Không dùng Tailwind để "vẽ lại" component PrimeNG; tuỳ biến qua token/`pt` (pass-through) khi cần.
- **Lucide (`lucide-angular`)**: icon. Chỉ import icon dùng tới (tree-shaking). Icon trang trí `aria-hidden="true"`; nút chỉ có icon phải có `aria-label`/`pTooltip` + tên accessible.

## 2. Theme & token
- Cấu hình `providePrimeNG` với preset tuỳ biến; semantic tokens (`--p-primary-color`, `--p-surface-*`, `--p-text-color`...). Màu thương hiệu định nghĩa **một lần** trong preset/`@theme` của Tailwind, ánh xạ sang token ngữ nghĩa (primary, success, warn, danger, info).
- Thứ tự CSS layer: `theme, base, primeng` (hoặc theo hướng dẫn chính thức của PrimeNG cho Tailwind v4: `tailwindcss-primeui`), để utility Tailwind ghi đè được khi cần mà không chiến tranh specificity. **Khi cấu hình nghi ngờ, đọc tài liệu chính thức của đúng phiên bản trong `package.json`** — API theme thay đổi giữa các bản.
- Trạng thái nghiệp vụ → màu + **icon + nhãn chữ**: `OVERDUE` (danger), `STALLED` (warn, icon riêng), `BLOCKED` (surface mờ + icon khóa), `COMPLETED` (success), `DRAFT` (info, "Bản nháp"), `PAUSED` (surface). Không bao giờ chỉ dùng màu.
- Typography: một thang chữ nhất quán (tiêu đề/nội dung/số liệu); số liệu (đồng hồ, thống kê) dùng chữ số đều chiều rộng (`tabular-nums`) để không nhảy layout khi cập nhật mỗi giây.

## 3. Dark mode
Chuyển bằng class gốc (`.app-dark`) gắn trên `<html>`; lưu lựa chọn người dùng (preference không nhạy cảm, có thể `localStorage` — token thì không) và mặc định theo `prefers-color-scheme`. Kiểm tra tương phản ở **cả hai** chế độ; biểu đồ lấy màu từ CSS variable để đổi theo theme.

## 4. Layout & responsive
- Shell: sidebar/drawer (collapse trên mobile), topbar có quota AI + gói + menu người dùng. Điều hướng chính hiện diện đủ trên 375px (bottom nav hoặc Drawer).
- Breakpoint kiểm tra: 375, 768, 1024, 1440. Không overflow ngang; bảng dữ liệu cuộn ngang trong **container riêng** hoặc chuyển dạng thẻ trên mobile; Dialog trở thành full-screen/drawer trên mobile.
- Calendar: tuần/tháng desktop, danh sách theo ngày trên mobile.
- Study Workspace: ưu tiên timer + checklist ở mobile; Scratchpad ở tab/ngăn kéo.
- Target chạm ≥ 44×44px cho điều khiển chính.

## 5. A11y checklist (mục tiêu Lighthouse ≥ 90, nhưng đừng chỉ chạy theo điểm)
- Cấu trúc: landmark (`header/nav/main`), một `h1`/trang, thứ tự heading hợp lý, `lang="vi"`.
- Form: `label` gắn control, lỗi liên kết bằng `aria-describedby`, `aria-invalid`; focus chuyển tới lỗi đầu tiên khi submit lỗi.
- Dialog: giữ focus trap (PrimeNG đã hỗ trợ), trả focus về nút gọi, đóng bằng Esc; `header` rõ ràng.
- Live region: kết quả AI đang stream (`aria-live="polite"`, cập nhật theo câu/đoạn chứ không từng token), toast, kết quả lưu.
- Bàn phím: mọi hành động dùng được không cần chuột (kể cả kéo-thả lịch — cung cấp thay thế: nút "Dời tới…" mở DatePicker).
- Tương phản ≥ 4.5:1 (chữ), ≥ 3:1 (UI); focus ring nhìn thấy; tôn trọng `prefers-reduced-motion` (tắt animation không thiết yếu, kể cả hiệu ứng stream).
- Biểu đồ: có `aria-label` + bảng dữ liệu/tóm tắt thay thế.

## 6. Pattern UI chuẩn
- **Skeleton** cho tải; **empty state** có hành động; **error state** có Thử lại + mã tham chiếu.
- **Toast** cho kết quả ngắn; **Dialog/ConfirmPopup** cho quyết định; **Inline banner** cho trạng thái bền (offline, hết quota, chế độ mock).
- **Diff Proposal**: hai cột (hiện tại | đề xuất) hoặc danh sách thay đổi theo ngày; ngày vi phạm tô viền/icon cảnh báo + văn bản.
- Hành động rủi ro: nút danger tách riêng, mô tả hệ quả, không đặt cạnh nút chính.
- Ngôn ngữ UI tiếng Việt, ngắn gọn, nói việc cần làm kế tiếp; giọng điệu hỗ trợ (đặc biệt ở overdue/STALLED — không đổ lỗi).

## 7. Hiệu năng
- Bundle: lazy theo slice; `@defer` cho chart/calendar nặng; import PrimeNG theo component; ảnh/icon tối ưu.
- Render: `@for` có `track` ổn định (id), danh sách dài dùng `p-table` virtual scroll/phân trang; `computed` thay vì hàm trong template.
- Timer: chỉ signal `label()` đổi mỗi giây; tránh để cả danh sách phụ thuộc vào `now` signal.
- SSE: nối chuỗi chunk bằng `signal.update`; tránh render lại markdown đầy đủ mỗi token nếu nặng (gộp theo animation frame/đoạn).
- Mục tiêu: REST tương tác ≤500ms thị giác; TTFT hiển thị ≤2.5s.
