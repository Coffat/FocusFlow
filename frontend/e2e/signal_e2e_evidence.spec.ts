import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const EVIDENCE_DIR = path.resolve(__dirname, '../../docs/evidence/e2e_screenshots');

test.describe('Angular 21 Signals & OnPush Multi-Level Verification Suite', () => {
  test.beforeAll(() => {
    if (!fs.existsSync(EVIDENCE_DIR)) {
      fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
    }
  });

  test('Comprehensive End-to-End Visual Evidence: Auth Signals -> Dashboard -> Workspace Timer & Scratchpad -> Availability Mode A/B -> Roadmaps AI SSE -> Tasks & Analytics OnPush -> Settings', async ({
    page,
    request
  }) => {
    test.setTimeout(120_000);

    const timestamp = Date.now();
    const testEmail = `learner.signals.${timestamp}@example.com`;
    const testPassword = 'Password123!';
    const testFullName = 'Lê Minh Tuấn (Angular 21 Signals)';

    // =========================================================================
    // BƯỚC 1: Đăng ký user test qua Backend API
    // =========================================================================
    const regRes = await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        full_name: testFullName,
        email: testEmail,
        password: testPassword
      }
    });
    expect(regRes.ok()).toBeTruthy();
    const regData = await regRes.json();
    const authToken = regData.access_token;

    // Thiết lập sẵn availability cơ bản cho user mới để luồng Roadmaps hoạt động trơn tru
    await request.put('http://localhost:8000/api/v1/availabilities/me', {
      headers: {
        Authorization: `Bearer ${authToken}`
      },
      data: {
        mode: 'MODE_A',
        calendar_integration_mode: 'NONE',
        min_session_minutes: 30,
        weekly_schedule: {
          monday: { enabled: true, quota_hours: 2.0, time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }], allowed_window: { start: '07:00', end: '23:00' }, preferred_period: 'EVENING', min_session_minutes: 30 },
          tuesday: { enabled: true, quota_hours: 2.0, time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }], allowed_window: { start: '07:00', end: '23:00' }, preferred_period: 'EVENING', min_session_minutes: 30 },
          wednesday: { enabled: true, quota_hours: 2.0, time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }], allowed_window: { start: '07:00', end: '23:00' }, preferred_period: 'EVENING', min_session_minutes: 30 },
          thursday: { enabled: true, quota_hours: 2.0, time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }], allowed_window: { start: '07:00', end: '23:00' }, preferred_period: 'EVENING', min_session_minutes: 30 },
          friday: { enabled: true, quota_hours: 2.0, time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }], allowed_window: { start: '07:00', end: '23:00' }, preferred_period: 'EVENING', min_session_minutes: 30 },
          saturday: { enabled: true, quota_hours: 3.0, time_slots: [{ start: '14:00', end: '17:00', end_day_offset: 0 }], allowed_window: { start: '07:00', end: '23:00' }, preferred_period: 'AFTERNOON', min_session_minutes: 30 },
          sunday: { enabled: true, quota_hours: 3.0, time_slots: [{ start: '14:00', end: '17:00', end_day_offset: 0 }], allowed_window: { start: '07:00', end: '23:00' }, preferred_period: 'AFTERNOON', min_session_minutes: 30 }
        }
      }
    });

    // =========================================================================
    // BƯỚC 2: Điều hướng /sign-in, test nút toggle mật khẩu (Signal isPasswordVisible)
    // =========================================================================
    await page.goto('/sign-in');
    await page.waitForLoadState('networkidle');

    const passwordInput = page.locator('#password');
    const togglePasswordBtn = page.locator('.trailing-toggle-button');

    // Kiểm tra trạng thái mặc định: password field là 'password'
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Click toggle: Signal isPasswordVisible chuyển sang true -> input type đổi thành 'text'
    await togglePasswordBtn.click();
    await expect(passwordInput).toHaveAttribute('type', 'text');

    // Click toggle lần nữa: Signal isPasswordVisible chuyển về false -> input type đổi về 'password'
    await togglePasswordBtn.click();
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Nhập thông tin đăng nhập
    await page.fill('#work-email', testEmail);
    await page.fill('#password', testPassword);

    // Chụp ảnh minh chứng Bước 2: 01_signin_signals.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '01_signin_signals.png'), fullPage: true });

    // Submit form đăng nhập
    await page.click('button[type="submit"]');

    // =========================================================================
    // BƯỚC 3: Đợi chuyển hướng vào /dashboard, xác minh Signal currentUser()
    // =========================================================================
    await page.waitForURL('**/dashboard');
    await page.waitForLoadState('networkidle');

    // Xác minh Navbar hiển thị đúng tên người dùng từ currentUser() signal
    const navbarUserName = page.locator('.user-name');
    await expect(navbarUserName).toContainText(testFullName);

    // Xác minh Card chào mừng hiển thị đúng tên người dùng từ currentUser() signal
    const welcomeHeader = page.locator('h1');
    await expect(welcomeHeader).toContainText(`Xin chào, ${testFullName}`);

    // Chụp ảnh minh chứng Bước 3: 02_dashboard_user_signal.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '02_dashboard_user_signal.png'), fullPage: true });

    // =========================================================================
    // BƯỚC 4: Điều hướng /workspace, test Pomodoro Signal & Scratchpad
    // =========================================================================
    await page.goto('/workspace');
    await page.waitForURL('**/workspace');
    await page.waitForLoadState('networkidle');

    // Xác minh đồng hồ hiển thị giá trị mặc định từ computed formattedTime() (25:00)
    const clockFace = page.locator('.text-7xl');
    await expect(clockFace).toHaveText('25:00');

    // Bấm nút "Bắt đầu / Tiếp tục"
    const startResumeBtn = page.getByRole('button', { name: 'Bắt đầu / Tiếp tục' });
    await startResumeBtn.click();

    // Xác minh trạng thái isRunning chuyển thành true (badge hiển thị running)
    await expect(page.locator('text=Đang chạy (Heartbeat 60s active)')).toBeVisible();

    // Chờ 2.5 giây để đồng hồ Signal đếm lùi và thanh tiến độ cập nhật
    await page.waitForTimeout(2500);
    const runningTime = await clockFace.textContent();
    expect(runningTime?.trim()).not.toBe('25:00');

    // Chụp ảnh minh chứng Bước 4a: 03_workspace_pomodoro_running.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '03_workspace_pomodoro_running.png'), fullPage: true });

    // Nhập ghi chú vào ô Scratchpad và xác minh Signal scratchpadNote phản ứng
    const scratchpad = page.locator('textarea');
    const testNote = 'Ghi chú kiến trúc Angular 21 Signals: Zoneless OnPush reactivity và Pomodoro Timer bảo toàn nhịp tim hoạt động mượt mà!';
    await scratchpad.fill(testNote);
    await expect(scratchpad).toHaveValue(testNote);

    // Chụp ảnh minh chứng Bước 4b: 04_workspace_scratchpad_saved.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '04_workspace_scratchpad_saved.png'), fullPage: true });

    // =========================================================================
    // BƯỚC 5: Điều hướng /availability, test chuyển tab Mode A / Mode B
    // =========================================================================
    await page.goto('/availability');
    await page.waitForURL('**/availability');
    await page.waitForLoadState('networkidle');

    // Kiểm tra Mode A tab được chọn
    const modeATab = page.locator('[data-testid="mode-a-tab"]');
    await expect(modeATab).toHaveAttribute('aria-selected', 'true');

    // Chụp ảnh minh chứng Bước 5a: 05_availability_mode_a.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '05_availability_mode_a.png'), fullPage: true });

    // Chuyển sang Mode B (Khung giờ cố định)
    const modeBTab = page.locator('[data-testid="mode-b-tab"]');
    await modeBTab.click();
    await expect(modeBTab).toHaveAttribute('aria-selected', 'true');
    await page.waitForTimeout(500);

    // Chụp ảnh minh chứng Bước 5b: 06_availability_mode_b.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '06_availability_mode_b.png'), fullPage: true });

    // =========================================================================
    // BƯỚC 6: Điều hướng /roadmaps, tạo mục tiêu, sinh cột mốc SSE & phê duyệt lịch
    // =========================================================================
    await page.goto('/roadmaps');
    await page.waitForURL('**/roadmaps');
    await page.waitForLoadState('networkidle');

    // Kiểm tra modal onboarding nếu có
    const onboardingModal = page.locator('[data-testid="availability-onboarding-modal"]');
    if (await onboardingModal.isVisible()) {
      const busyProBtn = page.locator('[data-testid="onboard-preset-busy-pro"]');
      if (await busyProBtn.isVisible()) {
        await busyProBtn.click();
        await page.waitForTimeout(500);
      }
    }

    // Mở form tạo mục tiêu nếu chưa mở
    const toggleFormBtn = page.locator('[data-testid="toggle-create-roadmap-btn"]');
    if (await toggleFormBtn.isVisible()) {
      const titleInput = page.locator('[data-testid="new-goal-title-input"]');
      if (!(await titleInput.isVisible())) {
        await toggleFormBtn.click();
      }
    }

    const today = new Date();
    const startDateStr = today.toISOString().split('T')[0];
    const targetDate = new Date(today.getTime() + 30 * 24 * 3600 * 1000);
    const targetDateStr = targetDate.toISOString().split('T')[0];

    await page.fill('[data-testid="new-goal-title-input"]', 'Mastering Angular 21 Signals & Hexagonal Monolith');
    await page.fill(
      '[data-testid="new-goal-description-input"]',
      'Học chuyên sâu kiến trúc Angular 21 Zoneless, Signals, PrimeNG v21 và thiết kế Hexagonal Modular Monolith.'
    );
    await page.fill('[data-testid="new-goal-start-date-input"]', startDateStr);
    await page.fill('[data-testid="new-goal-target-date-input"]', targetDateStr);

    // Submit tạo mục tiêu
    await page.click('[data-testid="submit-create-roadmap-btn"]');

    // Chuyển sang Step 2 (Cột mốc kiến thức — Milestones)
    const skipToMilestonesBtn = page.locator('[data-testid="skip-to-milestones-btn"]');
    if (await skipToMilestonesBtn.isVisible({ timeout: 10000 })) {
      await skipToMilestonesBtn.click();
    } else {
      await page.click('[data-testid="step-tab-2"]');
    }

    await page.waitForSelector('[data-testid="generate-milestones-ai-btn"]', { state: 'visible', timeout: 15000 });

    // Sinh cột mốc AI qua 2-Stage SSE (UC-07)
    await page.click('[data-testid="generate-milestones-ai-btn"]');

    // Chờ các cột mốc hiển thị từ SSE stream
    await page.waitForSelector('[data-testid="milestone-item-0"]', { state: 'visible', timeout: 25000 });

    // Chụp ảnh minh chứng Bước 6a: 07_roadmaps_milestones_sse.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '07_roadmaps_milestones_sse.png'), fullPage: true });

    // Phê duyệt cột mốc (FR-PLAN-001 Approval Gate)
    const approveMilestonesBtn = page.locator('[data-testid="approve-milestones-btn"]');
    await approveMilestonesBtn.click();
    await page.waitForSelector('text=APPROVED', { state: 'visible', timeout: 10000 });

    // Chuyển sang Step 3: Đề xuất lịch học chi tiết (Proposal — UC-08)
    await page.click('[data-testid="step-tab-3"]');
    await page.waitForSelector('[data-testid="step-3-panel"]', { state: 'visible' });

    const genProposalBtn = page.locator('[data-testid="generate-proposal-ai-btn"]');
    await genProposalBtn.click();

    // Chờ danh sách task đề xuất xuất hiện
    await page.waitForSelector('[data-testid="proposal-task-row-0"]', { state: 'visible', timeout: 25000 });

    // Xác nhận Soft Overflow nếu xuất hiện
    const softOverflowCheckbox = page.locator('[data-testid="confirm-soft-overflow-checkbox"]');
    if (await softOverflowCheckbox.isVisible()) {
      await softOverflowCheckbox.check();
    }

    // Phê duyệt & Áp dụng lịch chính thức (Official Schedule)
    const applyBtn = page.locator('[data-testid="apply-proposal-btn"]');
    await expect(applyBtn).toBeEnabled({ timeout: 10000 });
    await applyBtn.click();

    // Chờ chuyển sang Step 4 và xác minh lịch chính thức đã kích hoạt
    await page.waitForSelector('[data-testid="step-4-panel"]', { state: 'visible', timeout: 20000 });
    await page.waitForSelector('[data-testid="official-roadmap-status"]', { state: 'visible' });

    // Chụp ảnh minh chứng Bước 6b: 08_proposal_official_schedule.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '08_proposal_official_schedule.png'), fullPage: true });

    // =========================================================================
    // BƯỚC 7: Điều hướng /tasks và /analytics kiểm tra OnPush components
    // =========================================================================
    // Kiểm tra /tasks
    await page.goto('/tasks');
    await page.waitForURL('**/tasks');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Hàng Đợi Công Việc');

    // Chụp ảnh minh chứng Bước 7a: 09_tasks_page_onpush.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '09_tasks_page_onpush.png'), fullPage: true });

    // Kiểm tra /analytics
    await page.goto('/analytics');
    await page.waitForURL('**/analytics');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Báo Cáo & Phân Tích Hiệu Suất');

    // Chụp ảnh minh chứng Bước 7b: 10_analytics_page_onpush.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '10_analytics_page_onpush.png'), fullPage: true });

    // =========================================================================
    // BƯỚC 8: Điều hướng /settings kiểm tra OnPush Settings Page
    // =========================================================================
    await page.goto('/settings');
    await page.waitForURL('**/settings');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: 'Cài Đặt Hệ Thống' })).toBeVisible();

    // Chụp ảnh minh chứng Bước 8: 11_settings_page_onpush.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '11_settings_page_onpush.png'), fullPage: true });
  });
});
