# Kiểm thử Frontend (Vitest + Playwright)

Chạy unit/component qua `pnpm exec ng test --watch=false` để Angular TestBed được khởi tạo; `vitest run` trực tiếp quét cả Playwright và thiếu môi trường Angular. Chạy `pnpm exec ng lint`, production build và `bash scripts/check-api-contract.sh` theo `docs/engineering/harness-quality.md`. E2E cần backend mock cùng PostgreSQL/Redis; chưa coi CI E2E là đã xác minh trước khi workflow chạy thực tế.

## 1. Vitest (unit/component)
- **Store**: test state machine bằng signals: trạng thái ban đầu → hành động → trạng thái mong đợi; `computed` dẫn xuất (overdue, stalled, remaining); rollback optimistic khi API lỗi; không bấm đúp khi đang `starting/streaming`.
- **SSE store**: mock `EventSource` (class giả có `addEventListener`, `close`, `readyState`); kiểm chuỗi `stage→chunk*→completed`, `validation_retry` tăng bộ đếm, `failed` map ra `ApiError`, `close()` được gọi khi `completed`/hủy/destroy, reconnect (CONNECTING) không tạo job mới.
- **Timer**: dùng fake timers + `Date` giả; kiểm elapsed/remaining chính xác sau "tab nền" (nhảy thời gian lớn).
- **Component**: render theo input signal, phát output đúng; trạng thái loading/empty/error; a11y cơ bản (role, aria-label, focus). Truy vấn theo role/label, không theo class CSS.
- **Pipe/util**: định dạng ngày theo timezone (UTC+7, UTC−8, ranh giới nửa đêm/DST), format mm:ss, mapper lỗi `code → thông điệp`.
- **Validator form**: Mode A (0.5–14h; biên 0.49/0.5/14/14.01), Mode B (start<end, vắt nửa đêm, overlap), thời lượng task 15–240.
- Dùng HTTP testing (`provideHttpClientTesting`) cho API service; assert URL/method/header (`Idempotency-Key`, `withCredentials`).
- Test zoneless: sau thay đổi signal, `await fixture.whenStable()`; không dựa `fixture.detectChanges()` kiểu zone cũ khi không cần.

## 2. Playwright (E2E, backend `LLM_PROVIDER=mock`, `PAYMENT_PROVIDER=local_mock`, `CALENDAR_PROVIDER=local_mock`)
Luồng bắt buộc có test:
1. Đăng ký → onboarding → đăng nhập; phiên hết hạn → refresh → tiếp tục.
2. Goal → AI Milestones (SSE) → Approve → AI Proposal (SSE) → xem diff → Apply (lịch chính thức xuất hiện).
3. Lỗi AI: kịch bản mock timeout / schema hỏng → hiện lỗi, nút Thử lại + Thủ công; quota không giảm.
4. Hết quota → nút Nâng cấp; thanh toán QR giả lập → gói Premium + quota tăng.
5. Study Workspace: start → timer → tick task → dừng sớm → tóm tắt; mất mạng (offline) → banner → khôi phục.
6. Overdue: dữ liệu quá hạn → Needs Attention theo roadmap → AI Reschedule → Proposal → Apply; `reschedule_count` chạm 3 → dialog STALLED.
7. Pause/Resume roadmap; Domino Shift phản ánh trên lịch.
8. RBAC: LEARNER vào `/admin` bị chặn; ADMIN thao tác quota.
9. Mobile viewport 375px chạy lại các luồng 1, 2, 5.
- Chạy được **khi ngắt mạng ngoài** (chế độ Offline Defense) — đây là tiêu chí smoke test của ADR-006.
- Chọn phần tử bằng `getByRole`/`getByLabel`; không phụ thuộc timeout cứng (dùng auto-wait/`expect.poll`).
- Seed dữ liệu qua API/fixture của backend, không qua UI dài dòng.

## 3. Kiểm định chất lượng khác
- **Lighthouse a11y ≥ 90** trên Onboarding, Study Workspace, Calendar, Analytics (CI hoặc script thủ công, ghi điểm vào PR).
- **axe** (jest-axe/@axe-core/playwright) trong E2E cho các trang trên: 0 lỗi nghiêm trọng.
- **Responsive**: ảnh chụp/kiểm overflow ở 375, 768, 1024.
- **Hợp đồng API**: `npm run api:gen` rồi `ng build` — lỗi type nghĩa là FE lệch BE; sửa FE hoặc báo BE.
- **Bundle**: theo dõi kích thước initial bundle; SPA Nginx image nhẹ (<25MB theo ADR-006).

## 4. Quy ước
- Test cạnh file (`*.spec.ts`); tên mô tả hành vi: `shows STALLED dialog when reschedule_count reaches 3`.
- Không `sleep`; không phụ thuộc giờ thật.
- Bug mới ⇒ viết test tái hiện trước khi sửa.
