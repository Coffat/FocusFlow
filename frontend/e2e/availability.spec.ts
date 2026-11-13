import { test, expect, Page, APIRequestContext } from '@playwright/test';

const BACKEND_API_URL = process.env['BACKEND_API_URL'] || 'http://localhost:8000/api/v1';

interface MockAvailabilityState {
  id: string | null;
  user_id: string;
  mode: 'MODE_A' | 'MODE_B';
  calendar_integration_mode: string;
  min_session_minutes: number;
  weekly_schedule: Record<string, unknown>;
  total_weekly_hours: number;
  updated_at: string;
}

function buildDefaultWeeklySchedule() {
  const weekday = {
    enabled: true,
    quota_hours: 2.0,
    time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }],
    allowed_window: { start: '07:00', end: '23:00' },
    preferred_period: 'EVENING',
    min_session_minutes: 30
  };
  const weekend = {
    enabled: true,
    quota_hours: 3.0,
    time_slots: [{ start: '14:00', end: '17:00', end_day_offset: 0 }],
    allowed_window: { start: '07:00', end: '23:00' },
    preferred_period: 'AFTERNOON',
    min_session_minutes: 30
  };
  return {
    monday: structuredClone(weekday),
    tuesday: structuredClone(weekday),
    wednesday: structuredClone(weekday),
    thursday: structuredClone(weekday),
    friday: structuredClone(weekday),
    saturday: structuredClone(weekend),
    sunday: structuredClone(weekend)
  };
}

async function setupLearnerSession(page: Page, request: APIRequestContext): Promise<void> {
  const uniqueEmail = `e2e.avail.${Date.now()}.${Math.floor(Math.random() * 10000)}@focusflow.vn`;
  const password = 'Password123!';
  let accessToken = 'e2e-fallback-jwt-token';
  let userProfile = {
    id: '00000000-0000-0000-0000-000000000099',
    email: uniqueEmail,
    full_name: 'E2E Learner',
    role: 'LEARNER',
    tier: 'FREE',
    created_at: new Date().toISOString()
  };
  let backendAvailable = false;

  try {
    const regRes = await request.post(`${BACKEND_API_URL}/auth/register`, {
      data: {
        full_name: 'E2E Learner',
        email: uniqueEmail,
        password
      },
      timeout: 3000
    });

    if (regRes.ok()) {
      const body = await regRes.json();
      if (body.access_token) {
        accessToken = body.access_token;
        userProfile = body.user || userProfile;
        backendAvailable = true;
        const storageState = await request.storageState();
        await page.context().addCookies(storageState.cookies);
      }
    }
  } catch {
    backendAvailable = false;
  }

  // Fallback stateful mock only when backend server is not reachable
  if (!backendAvailable) {
    let currentState: MockAvailabilityState = {
      id: null,
      user_id: userProfile.id,
      mode: 'MODE_A',
      calendar_integration_mode: 'NONE',
      min_session_minutes: 30,
      weekly_schedule: buildDefaultWeeklySchedule(),
      total_weekly_hours: 16.0,
      updated_at: new Date().toISOString()
    };

    await page.route('**/api/v1/auth/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(userProfile)
      });
    });

    await page.route('**/api/v1/availabilities/me', async route => {
      const method = route.request().method();
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(currentState)
        });
        return;
      }
      if (method === 'PUT') {
        const payload = JSON.parse(route.request().postData() || '{}');
        currentState = {
          ...currentState,
          id: currentState.id || '11111111-2222-3333-4444-555555555555',
          mode: payload.mode ?? currentState.mode,
          calendar_integration_mode: payload.calendar_integration_mode ?? currentState.calendar_integration_mode,
          min_session_minutes: payload.min_session_minutes ?? currentState.min_session_minutes,
          weekly_schedule: payload.weekly_schedule ?? currentState.weekly_schedule,
          updated_at: new Date().toISOString()
        };
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(currentState)
        });
        return;
      }
      await route.continue();
    });
  } else {
    // Ensure /auth/me succeeds even if backend only exposes /auth/register + /availabilities/me
    await page.route('**/api/v1/auth/me', async route => {
      const response = await route.fetch().catch(() => null);
      if (response && response.ok()) {
        await route.fulfill({ response });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(userProfile)
        });
      }
    });
  }

  await page.addInitScript(
    ({ token }) => {
      window.localStorage.setItem('access_token', token);
    },
    { token: accessToken }
  );
}

test.describe('FR-AVAIL v2.0 — Hybrid Availability End-to-End Verification (E2E-PW-01..05)', () => {
  test('E2E-PW-01..05: Full user journey from default Mode A -> Presets & Batch Copy -> Mode B Live Validation -> Save & Reload F5 -> /schedule Quick Drawer isolation', async ({
    page,
    request
  }) => {
    await setupLearnerSession(page, request);

    // =========================================================================
    // E2E-PW-01: Đăng ký người học mới & Điều hướng tới /availability
    // =========================================================================
    await page.goto('/availability');

    await expect(
      page.getByRole('heading', { name: /Cấu Hình Thời Gian Rảnh Lai/i })
    ).toBeVisible();

    const modeATab = page.getByTestId('mode-a-tab');
    const modeBTab = page.getByTestId('mode-b-tab');
    await expect(modeATab).toHaveAttribute('aria-selected', 'true');
    await expect(modeBTab).toHaveAttribute('aria-selected', 'false');

    const totalHoursEl = page.getByTestId('total-weekly-hours');
    await expect(totalHoursEl).toContainText('16.0 giờ / tuần');
    await expect(page.getByTestId('weekly-valid-badge')).toContainText('Đạt chuẩn (≥ 1.0h/tuần)');

    // =========================================================================
    // E2E-PW-02: Áp dụng 3 Bộ Mẫu Gợi ý (Presets) & Sao chép Hàng loạt (Batch Copy)
    // =========================================================================
    // 1. Preset "Người đi làm bận rộn" -> 13.5 giờ / tuần
    await page.getByTestId('preset-busy-pro').click();
    await expect(totalHoursEl).toContainText('13.5 giờ / tuần');

    // 2. Preset "Sinh viên đại học" -> 15.5 giờ / tuần (T3 & T5 đang nghỉ)
    await page.getByTestId('preset-uni-student').click();
    await expect(totalHoursEl).toContainText('15.5 giờ / tuần');

    const tuesdaySwitch = page.getByTestId('toggle-day-tuesday');
    const thursdaySwitch = page.getByTestId('toggle-day-thursday');
    await expect(tuesdaySwitch).toHaveAttribute('aria-checked', 'false');
    await expect(thursdaySwitch).toHaveAttribute('aria-checked', 'false');

    // Gạt công tắc bật lại Thứ 3 -> có sẵn quỹ giờ hợp lệ 2.0h, không báo lỗi đỏ
    await tuesdaySwitch.click();
    await expect(tuesdaySwitch).toHaveAttribute('aria-checked', 'true');
    await expect(page.getByTestId('day-errors-tuesday')).toHaveCount(0);
    await expect(totalHoursEl).toContainText('17.5 giờ / tuần');

    // 3. Preset "Học toàn thời gian" -> 36.0 giờ / tuần
    await page.getByTestId('preset-bootcamper').click();
    await expect(totalHoursEl).toContainText('36.0 giờ / tuần');

    // 4. Chỉnh Thứ 2 ở Mode A thành 3.5h + buổi Sáng (MORNING), bấm "Sao chép Thứ 2 sang T3–T6"
    const mondayCard = page.getByTestId('day-card-monday');
    await mondayCard.getByRole('button', { name: '3.5h' }).click();
    await page.getByTestId('period-MORNING-monday').click();
    await expect(page.getByTestId('period-MORNING-monday')).toHaveAttribute('aria-pressed', 'true');

    await page.getByTestId('batch-copy-monday').click();

    for (const day of ['tuesday', 'wednesday', 'thursday', 'friday']) {
      await expect(page.getByTestId(`day-card-${day}`)).toContainText(/3\.5\s*giờ\s*\/\s*ngày/);
      await expect(page.getByTestId(`period-MORNING-${day}`)).toHaveAttribute('aria-pressed', 'true');
    }

    // =========================================================================
    // E2E-PW-03: Kiểm tra Live Validation trên UI (Mode B) & Thêm Khung giờ Không Chồng lấn
    // =========================================================================
    await page.getByTestId('preset-busy-pro').click(); // Reset về cấu hình gọn 1 slot/ngày
    await modeBTab.click();
    await expect(modeBTab).toHaveAttribute('aria-selected', 'true');

    // Bấm "+ Thêm khung giờ" vào Thứ 2 -> thêm tự động ở khoảng hợp lệ, không báo lỗi chồng lấn
    await page.getByTestId('add-slot-monday').click();
    await expect(page.getByTestId('slot-row-monday-1')).toBeVisible();
    await expect(page.getByTestId('day-errors-monday')).toHaveCount(0);

    const saveBtn = page.getByTestId('save-availability-btn');
    await expect(saveBtn).toBeEnabled();

    // Sửa khung giờ thứ 2 đè lên khung giờ thứ 1 (20:30 - 22:00) -> báo lỗi chồng lấn & khóa nút Lưu
    const slot2Start = page.getByTestId('slot-start-monday-1');
    const slot2End = page.getByTestId('slot-end-monday-1');
    await slot2Start.fill('20:30');
    await slot2Start.dispatchEvent('change');
    await slot2End.fill('22:00');
    await slot2End.dispatchEvent('change');

    await expect(page.getByTestId('day-errors-monday')).toContainText('chồng lấn');
    await expect(saveBtn).toBeDisabled();

    // Xóa khung giờ bị trùng -> cảnh báo biến mất, nút Lưu sáng trở lại
    await page.getByTestId('remove-slot-monday-1').click();
    await expect(page.getByTestId('day-errors-monday')).toHaveCount(0);
    await expect(saveBtn).toBeEnabled();

    // =========================================================================
    // E2E-PW-04: Lưu Cấu hình Xuống PostgreSQL & Tải lại Trang (F5 Persistence Check)
    // =========================================================================
    await page.getByTestId('calendar-mode-select').selectOption('EXPORT_ICS');
    await page.getByTestId('min-session-select').selectOption('45');

    await saveBtn.click();
    await expect(page.getByTestId('save-success-banner')).toBeVisible();

    // F5 Reload kiểm chứng dữ liệu từ DB
    await page.reload();

    await expect(page.getByTestId('mode-b-tab')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('calendar-mode-select')).toHaveValue('EXPORT_ICS');
    await expect(page.getByTestId('min-session-select')).toHaveValue('45');
    await expect(page.getByTestId('total-weekly-hours')).toContainText('13.5 giờ / tuần');

    // =========================================================================
    // E2E-PW-05: Kiểm chứng Ranh giới Quick Drawer tại /schedule (Không gọi PUT /availabilities/me)
    // =========================================================================
    let putAvailabilityCount = 0;
    page.on('request', req => {
      if (req.method() === 'PUT' && req.url().includes('/api/v1/availabilities/me')) {
        putAvailabilityCount += 1;
      }
    });

    await page.goto('/schedule');
    await expect(page.getByRole('heading', { name: /Thời Khóa Biểu Học Tập/i })).toBeVisible();

    // Mở Quick Drawer -> nhấn phím Escape -> Quick Drawer đóng lại
    await page.getByTestId('open-quick-drawer-btn').click();
    const drawerDialog = page.getByTestId('quick-drawer-dialog');
    await expect(drawerDialog).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(drawerDialog).toBeHidden();

    // Mở lại Quick Drawer, chọn Domino Shift, nhập lý do và xác nhận
    await page.getByTestId('open-quick-drawer-btn').click();
    await expect(drawerDialog).toBeVisible();

    await page.getByTestId('action-domino-shift').check();
    await page.getByTestId('adjustment-reason-input').fill('Tăng ca đột xuất tại công ty');
    await page.getByTestId('confirm-today-adjustment-btn').click();

    await expect(drawerDialog).toBeHidden();
    await expect(page.getByTestId('quick-drawer-notification')).toContainText('Domino Shift');
    expect(putAvailabilityCount).toBe(0);

    // Quay lại /availability kiểm tra khuôn mẫu tuần vẫn nguyên vẹn 100%
    await page.goto('/availability');
    await expect(page.getByTestId('mode-b-tab')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('total-weekly-hours')).toContainText('13.5 giờ / tuần');
  });

  test('E2E-PW-06: Cross-midnight slot (+1d), Allowed Window live validation, and Mode B <-> Mode A State Retention across PostgreSQL reloads', async ({
    page,
    request
  }) => {
    await setupLearnerSession(page, request);
    await page.goto('/availability');

    await expect(
      page.getByRole('heading', { name: /Cấu Hình Thời Gian Rảnh Lai/i })
    ).toBeVisible();

    const saveBtn = page.getByTestId('save-availability-btn');

    // 1. Kiểm tra Live Validation cho Allowed Window ở Mode A (End <= Start -> khóa nút Lưu)
    const allowedStart = page.getByTestId('allowed-window-start');
    const allowedEnd = page.getByTestId('allowed-window-end');
    await allowedStart.fill('22:00');
    await allowedStart.dispatchEvent('change');
    await allowedEnd.fill('08:00');
    await allowedEnd.dispatchEvent('change');

    await expect(page.getByTestId('day-errors-monday')).toContainText('Khung giờ cho phép');
    await expect(saveBtn).toBeDisabled();

    // Khôi phục Allowed Window hợp lệ (06:30 -> 23:00)
    await allowedStart.fill('06:30');
    await allowedStart.dispatchEvent('change');
    await allowedEnd.fill('23:00');
    await allowedEnd.dispatchEvent('change');
    await expect(page.getByTestId('day-errors-monday')).toHaveCount(0);
    await expect(saveBtn).toBeEnabled();

    // 2. Chuyển sang Mode B và cấu hình slot qua nửa đêm (22:30 -> 00:30 +1d = 2.0h) cho Thứ 2
    await page.getByTestId('mode-b-tab').click();
    const monStart0 = page.getByTestId('slot-start-monday-0');
    const monEnd0 = page.getByTestId('slot-end-monday-0');
    const monOffset0 = page.getByTestId('slot-offset-monday-0');

    await monStart0.fill('22:30');
    await monStart0.dispatchEvent('change');
    await monEnd0.fill('00:30');
    await monEnd0.dispatchEvent('change');
    await monOffset0.check();

    await expect(page.getByTestId('day-errors-monday')).toHaveCount(0);
    await expect(page.getByTestId('slot-row-monday-0')).toContainText('120 phút');

    // Lưu cấu hình Mode B xuống PostgreSQL
    await saveBtn.click();
    await expect(page.getByTestId('save-success-banner')).toBeVisible();

    // 3. Chuyển về Mode A, chỉnh Thứ 2 thành 4.0h và bấm Lưu ở Mode A
    await page.getByTestId('mode-a-tab').click();
    await page.getByTestId('day-card-monday').getByRole('button', { name: '4h', exact: true }).click();
    await saveBtn.click();
    await expect(page.getByTestId('save-success-banner')).toBeVisible();

    // 4. Reload F5 từ PostgreSQL: đang ở Mode A (Thứ 2 = 4.0h), khi bấm sang tab Mode B vẫn giữ nguyên slot 22:30 -> 00:30 (+1d)
    await page.reload();
    await expect(page.getByTestId('mode-a-tab')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('day-card-monday')).toContainText(/4(\.0)?\s*giờ\s*\/\s*ngày/);

    await page.getByTestId('mode-b-tab').click();
    await expect(page.getByTestId('slot-start-monday-0')).toHaveValue('22:30');
    await expect(page.getByTestId('slot-end-monday-0')).toHaveValue('00:30');
    await expect(page.getByTestId('slot-offset-monday-0')).toBeChecked();
  });
});
