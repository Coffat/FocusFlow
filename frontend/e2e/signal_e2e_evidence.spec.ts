import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { E2E_CSRF_HEADERS, registerUserWithOtp } from './helpers/otp-auth.helper';

const BACKEND_API_URL = process.env['BACKEND_API_URL'] || 'http://127.0.0.1:3000/api/v1';
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
    test.setTimeout(240_000);

    const timestamp = Date.now();
    const testEmail = `learner.signals.${timestamp}@example.com`;
    const testPassword = 'Password123!';
    const testFullName = 'Lê Minh Tuấn (Angular 21 Signals)';

    // =========================================================================
    // BƯỚC 1: Đăng ký user test qua Backend API
    // =========================================================================
    const regRes = await registerUserWithOtp(request, {
      fullName: testFullName,
      email: testEmail,
      password: testPassword,
      backendApiUrl: BACKEND_API_URL
    });
    expect(regRes.ok()).toBeTruthy();

    // Thiết lập sẵn availability cơ bản cho user mới để luồng Roadmaps hoạt động trơn tru
    const availRes = await request.put(`${BACKEND_API_URL}/availabilities/me`, {
      headers: E2E_CSRF_HEADERS,
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
    expect(availRes.ok(), `Availability setup failed (${availRes.status()}): ${await availRes.text()}`).toBeTruthy();

    // Seed 1 active roadmap + today's task via real Backend API so Workspace has a real selectable task
    const now = new Date();
    const todayLocal = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const targetLocalDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 14);
    const targetLocal = `${targetLocalDate.getFullYear()}-${String(targetLocalDate.getMonth() + 1).padStart(2, '0')}-${String(targetLocalDate.getDate()).padStart(2, '0')}`;
    const seedTaskTitle = `Signal Pomodoro Task ${timestamp}`;

    const seedRoadmapRes = await request.post(`${BACKEND_API_URL}/roadmaps`, {
      headers: E2E_CSRF_HEADERS,
      data: {
        title: `Signal Workspace Seed ${timestamp}`,
        description: 'Seeded active roadmap for Workspace Pomodoro signal verification',
        prior_knowledge_level: 'INTERMEDIATE',
        start_date: todayLocal,
        target_date: targetLocal
      }
    });
    expect(seedRoadmapRes.status(), `POST /roadmaps failed: ${await seedRoadmapRes.text()}`).toBe(201);
    const seedRoadmap = (await seedRoadmapRes.json()) as { id: string };

    const seedProposalRes = await request.post(
      `${BACKEND_API_URL}/roadmaps/${seedRoadmap.id}/proposals/manual`,
      {
        headers: E2E_CSRF_HEADERS,
        data: {
          milestones: [
            {
              sequence_order: 1,
              title: 'Cột mốc 1: Angular Signals Core',
              description: 'Thực hành Signals và Zoneless reactivity',
              estimated_effort_minutes: 60
            }
          ],
          tasks: [
            {
              milestone_sequence_order: 1,
              title: seedTaskTitle,
              description: 'Nhiệm vụ phiên học kiểm thử đồng hồ Pomodoro Signal',
              task_type: 'PRACTICE',
              estimated_minutes: 60,
              scheduled_date: todayLocal,
              scheduled_start: new Date(now.getFullYear(), now.getMonth(), now.getDate(), 19, 30, 0).toISOString(),
              scheduled_end: new Date(now.getFullYear(), now.getMonth(), now.getDate(), 20, 30, 0).toISOString()
            }
          ],
          dependencies: []
        }
      }
    );
    expect(seedProposalRes.status(), `POST /proposals/manual failed: ${await seedProposalRes.text()}`).toBe(201);
    const seedProposal = (await seedProposalRes.json()) as { id: string };

    const seedApplyRes = await request.post(
      `${BACKEND_API_URL}/roadmaps/${seedRoadmap.id}/proposals/${seedProposal.id}/apply`,
      {
        headers: E2E_CSRF_HEADERS,
        data: {
          confirm_soft_overflow: true,
          confirm_warnings: true,
          confirm_partial_schedule: true
        }
      }
    );
    expect(seedApplyRes.status(), `POST /apply failed: ${await seedApplyRes.text()}`).toBe(200);

    // =========================================================================
    // BƯỚC 2: Điều hướng /sign-in, test nút toggle mật khẩu (Signal isPasswordVisible)
    // =========================================================================
    await page.goto('/sign-in');
    await page.waitForLoadState('networkidle');

    const passwordInput = page.locator('#password');
    const togglePasswordBtn = page.getByRole('button', {
      name: /Ẩn\/Hiện mật khẩu|Toggle password visibility/i
    });

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
    const userMenuBtn = page.getByRole('button', { name: 'Menu tài khoản người dùng' });
    await expect(userMenuBtn).toBeVisible();
    await userMenuBtn.click();
    const userDropdown = page.locator('.user-dropdown-panel');
    await expect(userDropdown).toBeVisible();
    await expect(userDropdown).toContainText(testFullName);
    await expect(userDropdown).toContainText(testEmail);
    await userMenuBtn.click();
    await expect(userDropdown).toBeHidden();

    // Xác minh Dashboard heading hiển thị đúng
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();

    // Chụp ảnh minh chứng Bước 3: 02_dashboard_user_signal.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '02_dashboard_user_signal.png'), fullPage: true });

    // =========================================================================
    // BƯỚC 4: Điều hướng /workspace, test Pomodoro Signal & Scratchpad
    // =========================================================================
    await page.goto('/workspace');
    await page.waitForURL('**/workspace');
    await page.waitForLoadState('networkidle');

    // Xác minh đồng hồ hiển thị đúng thời lượng 60:00 từ computed formattedPrimaryTime() của nhiệm vụ 60 phút
    const clockFace = page.getByTestId('workspace-timer-display');
    await expect(clockFace).toBeVisible();
    await expect(clockFace).toContainText('60:00');

    // Chọn nhiệm vụ hôm nay vào phiên học để kích hoạt nút Bắt đầu
    const taskCheckbox = page.getByRole('checkbox', {
      name: `Chọn nhiệm vụ vào phiên học: ${seedTaskTitle}`
    });
    await expect(taskCheckbox).toBeVisible();
    if (!(await taskCheckbox.isChecked())) {
      await taskCheckbox.check();
    }

    // Bấm nút bắt đầu phiên học & đợi API /sessions/start phản hồi
    const startSessionPromise = page.waitForResponse(
      (res) => res.url().includes('/api/v1/sessions/start') && res.request().method() === 'POST'
    );
    const startSessionBtn = page.getByTestId('start-session-btn');
    await expect(startSessionBtn).toBeEnabled();
    await startSessionBtn.click();
    expect((await startSessionPromise).ok()).toBeTruthy();

    // Xác minh đồng hồ Signal đếm lùi tự động (zoneless OnPush reactivity)
    await expect(clockFace).not.toContainText('60:00', { timeout: 6000 });

    // Chụp ảnh minh chứng Bước 4a: 03_workspace_pomodoro_running.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '03_workspace_pomodoro_running.png'), fullPage: true });

    // Mở bảng Ghi chú nhanh (Scratchpad) và xác minh Signal scratchpad phản ứng
    const toggleNotesBtn = page.getByRole('button', { name: 'Ghi chú nhanh' });
    await expect(toggleNotesBtn).toBeVisible();
    await toggleNotesBtn.click();
    const scratchpad = page.getByTestId('scratchpad-textarea');
    await expect(scratchpad).toBeVisible();
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

    // Chụp ảnh minh chứng Bước 5b: 06_availability_mode_b.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '06_availability_mode_b.png'), fullPage: true });

    // =========================================================================
    // BƯỚC 6: Điều hướng /roadmaps/new, tạo mục tiêu, sinh cột mốc SSE & phê duyệt lịch
    // =========================================================================
    await page.goto('/roadmaps/new');
    await page.waitForURL('**/roadmaps/new');
    await page.waitForLoadState('networkidle');

    // Kiểm tra modal onboarding nếu có
    const onboardingModal = page.locator('[data-testid="availability-onboarding-modal"]');
    if (await onboardingModal.isVisible()) {
      const busyProBtn = page.locator('[data-testid="onboard-preset-busy-pro"]');
      if (await busyProBtn.isVisible()) {
        await busyProBtn.click();
        await expect(onboardingModal).toBeHidden({ timeout: 10000 });
      }
    }

    // Chuyển về Step 1 (vì user đã có sẵn 1 roadmap ACTIVE nên loadRoadmaps() tự chọn Step 4)
    const step1Tab = page.locator('[data-testid="step-tab-1"]');
    if (await step1Tab.isVisible()) {
      await step1Tab.click();
    }

    // Mở form tạo mục tiêu nếu chưa mở
    const titleInput = page.locator('[data-testid="new-goal-title-input"]');
    if (!(await titleInput.isVisible())) {
      const toggleFormBtn = page.locator('[data-testid="toggle-create-roadmap-btn"]');
      await expect(toggleFormBtn).toBeVisible();
      await toggleFormBtn.click();
    }
    await expect(titleInput).toBeVisible({ timeout: 10000 });

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

    // Chờ bộ câu hỏi phỏng vấn (FR-GOAL-002) và chuyển sang Step 2 (Cột mốc kiến thức — Milestones)
    const skipClarifyBtn = page.locator('[data-testid="skip-clarification-btn"]');
    const skipToMilestonesBtn = page.locator('[data-testid="skip-to-milestones-btn"]');
    const genMilestonesBtn = page.locator('[data-testid="generate-milestones-ai-btn"]');

    await expect(skipClarifyBtn.or(skipToMilestonesBtn).or(genMilestonesBtn)).toBeVisible({
      timeout: 45000
    });

    if (await skipClarifyBtn.isVisible()) {
      await skipClarifyBtn.click();
    } else if (await skipToMilestonesBtn.isVisible()) {
      await skipToMilestonesBtn.click();
    }

    await expect(genMilestonesBtn).toBeVisible({ timeout: 15000 });

    // Sinh cột mốc AI qua 2-Stage SSE (UC-07)
    await genMilestonesBtn.click();

    // Chờ các cột mốc hiển thị từ SSE stream
    await page.waitForSelector('[data-testid="milestone-item-0"]', { state: 'visible', timeout: 60000 });

    // Chụp ảnh minh chứng Bước 6a: 07_roadmaps_milestones_sse.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '07_roadmaps_milestones_sse.png'), fullPage: true });

    // Phê duyệt cột mốc (FR-PLAN-001 Approval Gate)
    const approveMilestonesBtn = page.locator('[data-testid="approve-milestones-btn"]');
    await approveMilestonesBtn.click();
    await page.waitForSelector('text=APPROVED', { state: 'visible', timeout: 10000 });

    // Chuyển sang Step 3: Đề xuất lịch học chi tiết (Proposal — UC-08)
    const goToStep3Btn = page.locator('[data-testid="go-to-step-3-btn"]');
    if (await goToStep3Btn.isVisible()) {
      await goToStep3Btn.click();
    } else {
      await page.click('[data-testid="step-tab-3"]');
    }
    await page.waitForSelector('[data-testid="step-3-panel"]', { state: 'visible' });

    const genTasksBtn = page.locator('[data-testid="generate-tasks-ai-btn"]');
    if (await genTasksBtn.isVisible()) {
      await genTasksBtn.click();
    } else {
      await page.click('[data-testid="generate-proposal-ai-btn"]');
    }

    // Chờ danh sách task đề xuất xuất hiện từ SSE
    await page.waitForSelector('[data-testid="milestone-task-group-0"]', { state: 'visible', timeout: 90000 });

    // Chốt danh sách nhiệm vụ & chuyển sang Step 4: Thời khóa biểu đề xuất
    const confirmTasksBtn = page.locator('[data-testid="confirm-tasks-to-step-4-btn"]').first();
    await expect(confirmTasksBtn).toBeVisible({ timeout: 5000 });
    await confirmTasksBtn.click();
    await page.waitForSelector('[data-testid="step-4-panel"]', { state: 'visible', timeout: 15000 });

    // Xác nhận Soft Overflow nếu xuất hiện
    const softOverflowCheckbox = page.locator('[data-testid="confirm-soft-overflow-checkbox"]');
    if (await softOverflowCheckbox.isVisible()) {
      await softOverflowCheckbox.check();
    }

    // Phê duyệt & Áp dụng lịch chính thức (Official Schedule)
    const applyBtn = page.locator('[data-testid="apply-proposal-btn"]');
    await expect(applyBtn).toBeEnabled({ timeout: 10000 });
    await applyBtn.click();

    // Xác minh lịch chính thức đã kích hoạt
    await page.waitForSelector('[data-testid="official-roadmap-status"]', { state: 'visible', timeout: 20000 });

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
    await expect(page.getByRole('heading', { name: 'Cài Đặt FocusFlow' })).toBeVisible();

    // Chụp ảnh minh chứng Bước 8: 11_settings_page_onpush.png
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '11_settings_page_onpush.png'), fullPage: true });
  });
});
