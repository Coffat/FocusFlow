import * as fs from 'node:fs';
import { test, expect, Page, APIRequestContext } from '@playwright/test';
import { E2E_CSRF_HEADERS, registerUserWithOtp } from './helpers/otp-auth.helper';

const BACKEND_API_URL = process.env['BACKEND_API_URL'] || 'http://127.0.0.1:3000/api/v1';

function formatLocalIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function addLocalDays(base: Date, deltaDays: number): Date {
  return new Date(base.getFullYear(), base.getMonth(), base.getDate() + deltaDays);
}

function buildLocalIsoDateTime(dateStr: string, timeStr: string): string {
  const [y, m, d] = dateStr.split('-').map(Number);
  const [hh, mm] = timeStr.split(':').map(Number);
  return new Date(y, (m || 1) - 1, d || 1, hh || 0, mm || 0, 0).toISOString();
}

function buildUniformEveningWeeklySchedule() {
  const dayConfig = {
    enabled: true,
    quota_hours: 3.0,
    time_slots: [{ start: '19:00', end: '22:00', end_day_offset: 0 }],
    allowed_window: { start: '07:00', end: '23:00' },
    preferred_period: 'EVENING',
    min_session_minutes: 30,
  };
  return {
    monday: structuredClone(dayConfig),
    tuesday: structuredClone(dayConfig),
    wednesday: structuredClone(dayConfig),
    thursday: structuredClone(dayConfig),
    friday: structuredClone(dayConfig),
    saturday: structuredClone(dayConfig),
    sunday: structuredClone(dayConfig),
  };
}

async function registerAndSetupLearner(
  page: Page,
  request: APIRequestContext,
  tag: string
): Promise<{ email: string }> {
  const uniqueSuffix = `${Date.now()}.${Math.floor(Math.random() * 100000)}`;
  const email = `e2e.p2b2b.${tag}.${uniqueSuffix}@focusflow.vn`;
  const password = 'Password123!';

  const regRes = await registerUserWithOtp(request, {
    fullName: `E2E P2B2B Learner ${tag}`,
    email,
    password,
    backendApiUrl: BACKEND_API_URL,
  });
  expect(regRes.ok(), `Register failed (${regRes.status()}): ${await regRes.text()}`).toBeTruthy();

  const availRes = await request.put(`${BACKEND_API_URL}/availabilities/me`, {
    headers: E2E_CSRF_HEADERS,
    data: {
      mode: 'MODE_A',
      calendar_integration_mode: 'NONE',
      min_session_minutes: 30,
      weekly_schedule: buildUniformEveningWeeklySchedule(),
    },
  });
  expect(
    availRes.ok(),
    `Availability setup failed (${availRes.status()}): ${await availRes.text()}`
  ).toBeTruthy();

  const storageState = await request.storageState();
  await page.context().addCookies(storageState.cookies);

  return { email };
}

async function seedAppliedRoadmap(
  request: APIRequestContext,
  tag: string
): Promise<{ roadmapId: string; title: string }> {
  const todayStr = formatLocalIsoDate(new Date());
  const title = `P2B2B Roadmap ${tag}`;

  const createRoadmapRes = await request.post(`${BACKEND_API_URL}/roadmaps`, {
    headers: E2E_CSRF_HEADERS,
    data: {
      title,
      description: 'E2E roadmap for P2B2B GDPR export and persistent notification verification',
      prior_knowledge_level: 'BEGINNER',
      start_date: todayStr,
      target_date: formatLocalIsoDate(addLocalDays(new Date(), 14)),
    },
  });
  expect(
    createRoadmapRes.status(),
    `POST /roadmaps failed: ${await createRoadmapRes.text()}`
  ).toBe(201);
  const roadmapBody = (await createRoadmapRes.json()) as { id: string };

  const manualProposalRes = await request.post(
    `${BACKEND_API_URL}/roadmaps/${roadmapBody.id}/proposals/manual`,
    {
      headers: E2E_CSRF_HEADERS,
      data: {
        milestones: [
          {
            sequence_order: 1,
            title: `Chặng 1: Nền tảng ${tag}`,
            description: 'Nắm vững kiến thức nền tảng',
            estimated_effort_minutes: 60,
          },
        ],
        tasks: [
          {
            milestone_sequence_order: 1,
            title: `Nhiệm vụ học sâu ${tag}`,
            description: 'Thực hành bài tập nền tảng',
            task_type: 'PRACTICE',
            estimated_minutes: 60,
            scheduled_date: todayStr,
            scheduled_start: buildLocalIsoDateTime(todayStr, '19:00'),
            scheduled_end: buildLocalIsoDateTime(todayStr, '20:00'),
          },
        ],
        dependencies: [],
      },
    }
  );
  expect(
    manualProposalRes.status(),
    `POST /proposals/manual failed: ${await manualProposalRes.text()}`
  ).toBe(201);
  const proposalBody = (await manualProposalRes.json()) as { id: string };

  const applyRes = await request.post(
    `${BACKEND_API_URL}/roadmaps/${roadmapBody.id}/proposals/${proposalBody.id}/apply`,
    {
      headers: E2E_CSRF_HEADERS,
      data: {
        confirm_soft_overflow: true,
        confirm_warnings: true,
        confirm_partial_schedule: true,
      },
    }
  );
  expect(applyRes.status(), `POST /apply failed: ${await applyRes.text()}`).toBe(200);

  return { roadmapId: roadmapBody.id, title };
}

test.describe('P2B2B Functional Integration (Real Backend + PostgreSQL)', () => {
  test('FE-MOCK-03: GDPR Export tải snapshot JSON thật không chứa secret và báo lỗi trung thực khi HTTP 500', async ({
    page,
    request,
  }) => {
    const { email } = await registerAndSetupLearner(page, request, 'gdpr');
    const { title } = await seedAppliedRoadmap(request, 'gdpr');

    await page.goto('/settings?tab=security', { waitUntil: 'networkidle' });

    const exportBtn = page.getByTestId('gdpr-export-btn');
    await expect(exportBtn).toBeVisible({ timeout: 15_000 });

    const [exportResponse, download] = await Promise.all([
      page.waitForResponse(
        (res) => res.url().includes('/api/v1/account/export') && res.request().method() === 'GET'
      ),
      page.waitForEvent('download'),
      exportBtn.click(),
    ]);

    expect(exportResponse.status()).toBe(200);
    const downloadedPath = await download.path();
    expect(downloadedPath).toBeTruthy();

    const rawJson = fs.readFileSync(downloadedPath!, 'utf-8');
    const payload = JSON.parse(rawJson) as {
      schema_version: string;
      user: { email: string };
      roadmaps?: Array<{ title: string }>;
    };

    expect(payload.schema_version).toBe('1.0');
    expect(payload.user.email).toBe(email);
    expect(Array.isArray(payload.roadmaps)).toBe(true);
    expect(payload.roadmaps?.some((r) => r.title === title)).toBe(true);

    // Must never leak password_hash or auth secrets
    expect(rawJson).not.toContain('password_hash');
    expect(rawJson).not.toContain('hashed_password');
    expect(rawJson).not.toContain('refresh_token');
    expect(rawJson).not.toContain('access_token');

    // Error state: intercept with HTTP 500 and ensure honest error UI with no fake download
    await page.route('**/api/v1/account/export', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      });
    });

    let unexpectedDownload = false;
    const onDownload = () => {
      unexpectedDownload = true;
    };
    page.on('download', onDownload);

    await exportBtn.click();
    await expect(page.getByTestId('gdpr-export-error')).toBeVisible({ timeout: 10_000 });
    expect(unexpectedDownload).toBe(false);
    page.off('download', onDownload);
  });

  test('FE-MOCK-08: Trung tâm thông báo hiển thị thông báo thật từ DB và lưu bền vững trạng thái đã đọc sau F5', async ({
    page,
    request,
  }) => {
    // Outbox relay cron runs every 60s on Taskiq scheduler; allow up to 90s for full E2E round-trip
    test.setTimeout(90_000);
    await registerAndSetupLearner(page, request, 'notif');
    await seedAppliedRoadmap(request, 'notif');

    // Wait for outbox relay/event handler to persist the real notification in PostgreSQL
    let persistedNotifId: string | null = null;
    await expect
      .poll(
        async () => {
          const res = await request.get(`${BACKEND_API_URL}/account/notifications`);
          if (!res.ok()) return 0;
          const body = (await res.json()) as {
            items?: Array<{ id: string; is_read: boolean }>;
            unread_count: number;
          };
          if (body.items && body.items.length > 0) {
            persistedNotifId = body.items[0].id;
          }
          return body.unread_count;
        },
        {
          timeout: 70_000,
          intervals: [1000, 2000, 2500],
          message: 'Expected real notification to be persisted after applying official schedule',
        }
      )
      .toBeGreaterThan(0);

    expect(persistedNotifId).toBeTruthy();

    await page.goto('/dashboard', { waitUntil: 'networkidle' });

    const bellBtn = page.getByTestId('notification-bell-btn');
    await expect(bellBtn).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('notification-unread-badge')).toBeVisible({ timeout: 10_000 });

    await bellBtn.click();
    const popover = page.getByTestId('notification-popover');
    await expect(popover).toBeVisible();

    const firstItem = page.locator('[data-testid="notification-item"]').first();
    await expect(firstItem).toBeVisible();
    await expect(firstItem).toHaveAttribute('data-unread', 'true');

    const [markReadRes] = await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes('/api/v1/account/notifications/') &&
          res.url().endsWith('/read') &&
          res.request().method() === 'POST'
      ),
      firstItem.click(),
    ]);
    expect(markReadRes.status()).toBe(200);

    // Reload page (F5) and confirm read state persists in PostgreSQL
    await page.reload({ waitUntil: 'networkidle' });
    await expect(page.getByTestId('notification-bell-btn')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('notification-unread-badge')).toHaveCount(0);

    await page.getByTestId('notification-bell-btn').click();
    await expect(page.getByTestId('notification-popover')).toBeVisible();
    await expect(page.locator('[data-testid="notification-item"]').first()).toHaveAttribute(
      'data-unread',
      'false'
    );
  });

  test('FE-API-05: Trang /pricing phản ánh đúng release_mode (FREE_BETA chặn nâng cấp hoặc PAID_ENABLED checkout thật)', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'billing');

    const configRes = await request.get(`${BACKEND_API_URL}/account/billing/config`);
    expect(configRes.ok(), `GET /account/billing/config failed (${configRes.status()})`).toBeTruthy();
    const billingConfig = (await configRes.json()) as {
      release_mode: 'FREE_BETA' | 'PAID_ENABLED';
      checkout_enabled: boolean;
      mock_confirm_enabled: boolean;
      status_message: string;
    };

    await page.goto('/pricing', { waitUntil: 'networkidle' });

    const premiumBtn = page.getByTestId('pricing-select-premium-btn');
    await expect(premiumBtn).toBeVisible({ timeout: 15_000 });

    if (billingConfig.release_mode === 'FREE_BETA' || !billingConfig.checkout_enabled) {
      const betaBanner = page.getByTestId('billing-free-beta-banner');
      await expect(betaBanner).toBeVisible();
      await expect(betaBanner).toContainText(billingConfig.status_message);
      await expect(premiumBtn).toBeDisabled();
      await expect(page.getByTestId('billing-checkout-modal')).toHaveCount(0);

      // Verify backend security enforcement directly
      const checkoutRes = await request.post(`${BACKEND_API_URL}/account/billing/checkout`, {
        headers: E2E_CSRF_HEADERS,
        data: { plan_code: 'PREMIUM_MONTHLY' },
      });
      expect(checkoutRes.status()).toBe(503);
      expect(await checkoutRes.text()).toContain('BILLING_FREE_BETA_DISABLED');

      const mockConfirmRes = await request.post(
        `${BACKEND_API_URL}/account/billing/mock-confirm/00000000-0000-0000-0000-000000000000`,
        { headers: E2E_CSRF_HEADERS }
      );
      expect(mockConfirmRes.status()).toBe(403);

      const meRes = await request.get(`${BACKEND_API_URL}/auth/me`);
      expect(meRes.ok()).toBeTruthy();
      const meBody = (await meRes.json()) as { tier?: string };
      expect((meBody.tier || '').toUpperCase()).toBe('FREE');
      return;
    }

    const [checkoutRes] = await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes('/api/v1/account/billing/checkout') &&
          res.request().method() === 'POST'
      ),
      premiumBtn.click(),
    ]);

    const modal = page.getByTestId('billing-checkout-modal');
    await expect(modal).toBeVisible();

    if (checkoutRes.status() === 200) {
      await expect(page.getByTestId('billing-checkout-details')).toBeVisible();
      const mockConfirmBtn = page.getByTestId('billing-mock-confirm-btn');
      if (await mockConfirmBtn.isVisible()) {
        const [confirmRes] = await Promise.all([
          page.waitForResponse(
            (res) =>
              res.url().includes('/api/v1/account/billing/mock-confirm/') &&
              res.request().method() === 'POST'
          ),
          mockConfirmBtn.click(),
        ]);
        expect(confirmRes.status()).toBe(200);
        await expect(page.getByTestId('billing-mock-success-banner')).toBeVisible();

        const meRes = await request.get(`${BACKEND_API_URL}/auth/me`);
        expect(meRes.ok()).toBeTruthy();
        const meBody = (await meRes.json()) as { tier?: string };
        expect((meBody.tier || '').toUpperCase()).toBe('PREMIUM');
      }
    } else {
      expect(checkoutRes.status()).toBe(503);
      await expect(page.getByTestId('billing-error-banner')).toBeVisible();
      await expect(page.getByTestId('billing-mock-success-banner')).toHaveCount(0);
    }
  });

  test('Scope 0: Dashboard KPI Card 4 hiển thị đúng nhãn "Phiên học hoàn tất" (không còn "Pomodoro hoàn tất")', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'kpi');
    await seedAppliedRoadmap(request, 'kpi');
    await page.goto('/dashboard', { waitUntil: 'networkidle' });

    await expect(page.getByText('Phiên học hoàn tất')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Trong tháng')).toBeVisible();
    await expect(page.getByText('Pomodoro hoàn tất')).toHaveCount(0);
  });
});
