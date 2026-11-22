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
  const email = `e2e.p2b2a.${tag}.${uniqueSuffix}@focusflow.vn`;
  const password = 'Password123!';

  const regRes = await registerUserWithOtp(request, {
    fullName: `E2E P2B2A Learner ${tag}`,
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
): Promise<{ roadmapId: string }> {
  const todayStr = formatLocalIsoDate(new Date());

  const createRoadmapRes = await request.post(`${BACKEND_API_URL}/roadmaps`, {
    headers: E2E_CSRF_HEADERS,
    data: {
      title: `P2B2A Roadmap ${tag}`,
      description: 'E2E roadmap for Prove Mode and WebCal functional completeness verification',
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
            title: `Chặng 1: Nền tảng cốt lõi ${tag}`,
            description: 'Nắm vững kiến thức nền tảng và kiểm chứng qua Prove Mode',
            estimated_effort_minutes: 60,
          },
        ],
        tasks: [
          {
            milestone_sequence_order: 1,
            title: `Nhiệm vụ học sâu ${tag}`,
            description: 'Thực hành bài tập nền tảng và ôn tập kiến thức',
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

  return { roadmapId: roadmapBody.id };
}

function extractFeedToken(webcalUrl: string): string {
  const match = webcalUrl.match(/\/feeds\/([^/?#]+)\.ics/);
  expect(match, `Unexpected WebCal URL format: ${webcalUrl}`).toBeTruthy();
  return match![1];
}

test.describe('P2B2A Functional Completeness (Real Backend + PostgreSQL)', () => {
  test('FE-FUNC-01: Prove Mode tạo 3 câu hỏi, chấm điểm thật và giữ bền vững sau F5 reload', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'prove');
    const { roadmapId } = await seedAppliedRoadmap(request, 'prove');

    await page.goto(`/roadmaps/${roadmapId}`, { waitUntil: 'domcontentloaded' });

    const openProveBtn = page.getByTestId('open-prove-mode-btn').first();
    await expect(openProveBtn).toBeVisible({ timeout: 15_000 });
    await openProveBtn.click();

    await expect(page.getByTestId('prove-mode-dialog')).toBeVisible();
    const generateBtn = page.getByTestId('prove-generate-btn');
    await expect(generateBtn).toBeVisible({ timeout: 10_000 });
    await generateBtn.click();

    // Expect 3 real recall questions generated by backend
    await expect(page.getByTestId('prove-question-card-0')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('prove-question-card-1')).toBeVisible();
    await expect(page.getByTestId('prove-question-card-2')).toBeVisible();

    await page
      .getByTestId('prove-answer-input-0')
      .fill(
        'Khái niệm cốt lõi giúp tổ chức kiến thức mạch lạc, phân tách rõ trách nhiệm và dễ dàng kiểm chứng bằng ví dụ thực tế.'
      );
    await page
      .getByTestId('prove-answer-input-1')
      .fill(
        'Khi áp dụng vào dự án thực tế cần xác định đầu vào, quy tắc kiểm tra tất định và tiêu chí hoàn thành rõ ràng.'
      );
    await page
      .getByTestId('prove-answer-input-2')
      .fill(
        'Lỗi phổ biến là bỏ qua bước kiểm thử biên; cách khắc phục là viết unit test và đối chiếu kết quả định kỳ.'
      );

    await page.getByTestId('prove-confidence-slider').fill('75');
    await page.getByTestId('prove-submit-btn').click();

    const resultPanel = page.getByTestId('prove-result-panel');
    await expect(resultPanel).toBeVisible({ timeout: 20_000 });

    const scoreText = (await page.getByTestId('prove-result-score').textContent())?.trim() ?? '';
    const statusText = (await page.getByTestId('prove-result-status').textContent())?.trim() ?? '';
    expect(scoreText).toMatch(/\d+\s*\/\s*100/);
    expect(statusText).toMatch(/PASSED|NEEDS_REVIEW/);

    // Reload browser (F5) and reopen dialog -> verify persisted proof restored from PostgreSQL
    await page.reload({ waitUntil: 'domcontentloaded' });
    const reopenBtn = page.getByTestId('open-prove-mode-btn').first();
    await expect(reopenBtn).toBeVisible({ timeout: 15_000 });
    await reopenBtn.click();

    await expect(page.getByTestId('prove-result-panel')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('prove-result-score')).toHaveText(scoreText);
    await expect(page.getByTestId('prove-result-status')).toHaveText(statusText);
  });

  test('FE-MOCK-02: WebCal thật — tạo, tải feed .ics hợp lệ, xoay vòng vô hiệu hóa token cũ và thu hồi', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'webcal');
    await seedAppliedRoadmap(request, 'webcal');

    await page.goto('/settings?tab=calendar', { waitUntil: 'domcontentloaded' });

    await expect(page.getByTestId('webcal-inactive-status')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('body')).not.toContainText('ff_live_sec_789123');

    // 1. Create initial WebCal token
    await page.getByTestId('webcal-create-btn').click();
    const urlInput1 = page.getByTestId('webcal-url-input');
    await expect(urlInput1).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId('webcal-onetime-warning')).toBeVisible();

    const webcalUrl1 = await urlInput1.inputValue();
    const token1 = extractFeedToken(webcalUrl1);

    // 2. Fetch real .ics feed via token1
    const feedRes1 = await request.get(`${BACKEND_API_URL}/feeds/${token1}.ics`);
    expect(feedRes1.status()).toBe(200);
    expect(feedRes1.headers()['content-type'] ?? '').toContain('text/calendar');
    const icsBody1 = await feedRes1.text();
    expect(icsBody1).toContain('BEGIN:VCALENDAR');
    expect(icsBody1).toContain('VEVENT');
    expect(icsBody1).toContain('X-WR-TIMEZONE');

    // 3. Reload -> verify token is NOT re-exposed (only SHA-256 active status)
    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('webcal-active-status')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('webcal-url-input')).toHaveCount(0);

    // 4. Rotate token -> confirm dialog -> old token 404, new token 200
    await page.getByTestId('webcal-rotate-btn').click();
    await page
      .getByRole('alertdialog', { name: 'Đặt lại WebCal Token' })
      .getByRole('button', { name: 'Xác nhận tạo mới' })
      .click();

    const urlInput2 = page.getByTestId('webcal-url-input');
    await expect(urlInput2).toBeVisible({ timeout: 10_000 });
    const webcalUrl2 = await urlInput2.inputValue();
    const token2 = extractFeedToken(webcalUrl2);
    expect(token2).not.toBe(token1);

    const oldFeedRes = await request.get(`${BACKEND_API_URL}/feeds/${token1}.ics`);
    expect(oldFeedRes.status()).toBe(404);

    const newFeedRes = await request.get(`${BACKEND_API_URL}/feeds/${token2}.ics`);
    expect(newFeedRes.status()).toBe(200);
    expect(await newFeedRes.text()).toContain('BEGIN:VCALENDAR');

    // 5. Revoke token -> confirm dialog -> token2 returns 404
    await page.getByTestId('webcal-revoke-btn').click();
    await page
      .getByRole('alertdialog', { name: 'Thu hồi liên kết WebCal' })
      .getByRole('button', { name: 'Thu hồi liên kết' })
      .click();

    await expect(page.getByTestId('webcal-inactive-status')).toBeVisible({ timeout: 10_000 });
    const revokedFeedRes = await request.get(`${BACKEND_API_URL}/feeds/${token2}.ics`);
    expect(revokedFeedRes.status()).toBe(404);

    // 6. Random nonexistent token -> 404
    const randomFeedRes = await request.get(
      `${BACKEND_API_URL}/feeds/nonexistent_random_token_${Date.now()}.ics`
    );
    expect(randomFeedRes.status()).toBe(404);
  });

  test('FE-MOCK-06: Người học (LEARNER) bị chặn khỏi /admin -> chuyển về /dashboard và API trả 403', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'admin-gate');

    await page.goto('/admin', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });

    const adminStatusRes = await request.get(`${BACKEND_API_URL}/account/admin/status`);
    expect(adminStatusRes.status()).toBe(403);
  });
});
