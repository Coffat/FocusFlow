import { test, expect, Page, APIRequestContext } from '@playwright/test';
import { E2E_CSRF_HEADERS, registerUserWithOtp } from './helpers/otp-auth.helper';

const BACKEND_API_URL = process.env['BACKEND_API_URL'] || 'http://127.0.0.1:3000/api/v1';

interface ApiRoadmapRecord {
  id: string;
  title: string;
  status: string;
}

interface ApiDashboardSummaryRecord {
  active_roadmaps?: Array<{
    id: string;
    title: string;
  }>;
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

/**
 * Registers a fresh isolated learner via the real backend API, configures valid
 * availability so scheduling prerequisites pass, and transfers the real HttpOnly
 * session cookies into the Playwright browser context.
 */
async function registerAndSetupLearner(
  page: Page,
  request: APIRequestContext,
  tag: string
): Promise<{ email: string }> {
  const uniqueSuffix = `${Date.now()}.${Math.floor(Math.random() * 100000)}`;
  const email = `e2e.sync.${tag}.${uniqueSuffix}@focusflow.vn`;
  const password = 'Password123!';

  const regRes = await registerUserWithOtp(request, {
    fullName: `E2E Sync Learner ${tag}`,
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

async function fetchBackendRoadmaps(request: APIRequestContext): Promise<ApiRoadmapRecord[]> {
  const res = await request.get(`${BACKEND_API_URL}/roadmaps`);
  expect(res.ok(), `GET /roadmaps failed (${res.status()})`).toBeTruthy();
  return (await res.json()) as ApiRoadmapRecord[];
}

async function fetchBackendDashboardSummary(
  request: APIRequestContext
): Promise<ApiDashboardSummaryRecord> {
  const res = await request.get(`${BACKEND_API_URL}/evaluation/dashboard-summary`);
  expect(res.ok(), `GET /evaluation/dashboard-summary failed (${res.status()})`).toBeTruthy();
  return (await res.json()) as ApiDashboardSummaryRecord;
}

/**
 * Drives the real Roadmap Wizard UI through Step 1 (real POST /roadmaps),
 * Step 3 (add manual milestone), and Step 4 (add task + save manual plan via
 * real POST /roadmaps/{id}/proposals/manual), stopping right before clicking Apply.
 */
async function createManualDraftInWizard(
  page: Page,
  roadmapTitle: string
): Promise<{ roadmapId: string }> {
  await expect(page.getByTestId('wizard-dialog-container')).toBeVisible();

  // Step 1: Fill goal title & submit to real POST /api/v1/roadmaps
  const titleInput = page.getByTestId('goal-title-textarea');
  await expect(titleInput).toBeVisible();
  await titleInput.fill(roadmapTitle);

  const createResponsePromise = page.waitForResponse(
    res =>
      res.url().includes('/api/v1/roadmaps') &&
      res.request().method() === 'POST' &&
      !res.url().includes('/proposals') &&
      !res.url().includes('/milestones')
  );
  await page.getByTestId('goal-submit-btn').click();
  const createRes = await createResponsePromise;
  expect(createRes.status(), `POST /roadmaps failed: ${await createRes.text()}`).toBe(201);
  const createdBody = (await createRes.json()) as { id: string };
  expect(createdBody.id).toBeTruthy();

  // Step 3: Navigate to Milestones step via wizard stepper & add a manual milestone
  await page.getByTestId('wizard-step-btn-3').click();
  await expect(page.getByTestId('add-milestone-btn')).toBeVisible();
  await page.getByTestId('add-milestone-btn').click();
  await expect(page.getByTestId('milestone-title-input-0')).toBeVisible();
  await page.getByTestId('milestone-title-input-0').fill('Cột mốc 1: Nền tảng & Thực hành');

  // Step 4: Navigate to Schedule Proposal step, add a task, and save manual draft
  await page.getByTestId('wizard-step-btn-4').click();

  const manualFallbackBtn = page.getByTestId('step4-manual-fallback-btn');
  const addTaskBtn = page.getByTestId('add-task-btn');
  if (await manualFallbackBtn.isVisible().catch(() => false)) {
    await manualFallbackBtn.click();
  } else {
    await expect(addTaskBtn).toBeVisible();
    await addTaskBtn.click();
  }

  await expect(page.getByTestId('proposed-task-card-0')).toBeVisible();

  const manualProposalPromise = page.waitForResponse(
    res =>
      res.url().includes(`/api/v1/roadmaps/${createdBody.id}/proposals/manual`) &&
      res.request().method() === 'POST'
  );
  await page.getByTestId('update-proposal-btn').click();
  const manualProposalRes = await manualProposalPromise;
  expect(
    manualProposalRes.status(),
    `POST /proposals/manual failed: ${await manualProposalRes.text()}`
  ).toBe(201);

  await expect(page.getByTestId('apply-proposal-btn')).toBeEnabled();

  return { roadmapId: createdBody.id };
}

test.describe('Phase 3 Cross-Page E2E — Roadmap & Dashboard Real-Backend Sync', () => {
  test('Workflow 1: Create Roadmap -> Apply Proposal -> Dashboard updates immediately without reload', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf1');
    const roadmapTitle = `E2E Dashboard Sync ${Date.now()}`;

    // Navigate to /dashboard and confirm initial empty state for new user
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();
    await expect(page.getByText('Chưa có lộ trình học tập nào')).toBeVisible();

    // Open Roadmap Wizard from Dashboard & create manual proposal draft
    await page.getByTestId('dashboard-create-roadmap-btn').click();
    const { roadmapId } = await createManualDraftInWizard(page, roadmapTitle);

    // Apply Proposal via UI -> real POST /apply + automatic dashboard-summary reload
    const applyResPromise = page.waitForResponse(
      res =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/proposals/`) &&
        res.url().endsWith('/apply') &&
        res.request().method() === 'POST'
    );
    const summaryRefreshPromise = page.waitForResponse(
      res =>
        res.url().includes('/api/v1/evaluation/dashboard-summary') &&
        res.request().method() === 'GET'
    );

    await page.getByTestId('apply-proposal-btn').click();
    const applyRes = await applyResPromise;
    expect(applyRes.status(), `POST /apply failed: ${await applyRes.text()}`).toBe(200);

    const summaryRes = await summaryRefreshPromise;
    expect(summaryRes.ok()).toBeTruthy();

    // Verify wizard closes & Dashboard updates WITHOUT page reload
    await expect(page.getByTestId('wizard-dialog-container')).toBeHidden();
    await expect(page.getByText('Chưa có lộ trình học tập nào')).toBeHidden();
    await expect(page.getByRole('heading', { name: 'Lộ trình Đang theo đuổi' })).toBeVisible();
    await expect(
      page.locator('app-dashboard-active-roadmaps').getByText(roadmapTitle)
    ).toBeVisible();

    // Cross-check against real backend PostgreSQL state
    const backendSummary = await fetchBackendDashboardSummary(request);
    expect(backendSummary.active_roadmaps?.some(r => r.id === roadmapId && r.title === roadmapTitle)).toBeTruthy();

    const backendRoadmaps = await fetchBackendRoadmaps(request);
    const persisted = backendRoadmaps.find(r => r.id === roadmapId);
    expect(persisted).toBeDefined();
    expect(persisted?.status).toBe('ACTIVE');
  });

  test('Workflow 2: Apply Roadmap -> Roadmaps Hub displays ACTIVE status matching DB', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf2');
    const roadmapTitle = `E2E Hub Active ${Date.now()}`;

    await page.goto('/roadmaps');
    await expect(page.getByRole('heading', { name: 'Roadmap Hub' })).toBeVisible();
    await expect(page.getByText('Chưa có lộ trình học tập nào')).toBeVisible();

    // Open Wizard directly from Roadmaps Hub & create + apply
    await page.getByTestId('hub-create-roadmap-btn').click();
    const { roadmapId } = await createManualDraftInWizard(page, roadmapTitle);

    const applyResPromise = page.waitForResponse(
      res =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/proposals/`) &&
        res.url().endsWith('/apply') &&
        res.request().method() === 'POST'
    );
    await page.getByTestId('apply-proposal-btn').click();
    const applyRes = await applyResPromise;
    expect(applyRes.status()).toBe(200);

    await expect(page.getByTestId('wizard-dialog-container')).toBeHidden();

    // Verify Roadmaps Hub displays the applied roadmap with ACTIVE status
    const card = page.locator('app-roadmap-card').filter({ hasText: roadmapTitle });
    await expect(card).toBeVisible();
    await expect(card).toContainText('ĐANG KÍCH HOẠT');
    await expect(page.getByRole('button', { name: /Đang kích hoạt \(1\)/ })).toBeVisible();

    // Cross-check against real backend DB
    const backendRoadmaps = await fetchBackendRoadmaps(request);
    const persisted = backendRoadmaps.find(r => r.id === roadmapId);
    expect(persisted?.status).toBe('ACTIVE');
  });

  test('Workflow 3: Pause / Resume Roadmap -> UI and Database stay consistent across F5 reload', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf3');
    const roadmapTitle = `E2E Pause Resume ${Date.now()}`;

    await page.goto('/roadmaps');
    await expect(page.getByRole('heading', { name: 'Roadmap Hub' })).toBeVisible();

    await page.getByTestId('hub-create-roadmap-btn').click();
    const { roadmapId } = await createManualDraftInWizard(page, roadmapTitle);

    const applyResPromise = page.waitForResponse(
      res =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/proposals/`) &&
        res.url().endsWith('/apply') &&
        res.request().method() === 'POST'
    );
    await page.getByTestId('apply-proposal-btn').click();
    expect((await applyResPromise).status()).toBe(200);
    await expect(page.getByTestId('wizard-dialog-container')).toBeHidden();

    const card = page.locator('app-roadmap-card').filter({ hasText: roadmapTitle });
    await expect(card).toContainText('ĐANG KÍCH HOẠT');

    // Trigger Pause via 3-dot dropdown menu + ConfirmDialog
    await card.getByRole('button', { name: 'Tác vụ lộ trình' }).click();
    await card.getByRole('button', { name: /Tạm dừng lộ trình/ }).click();

    const pauseResPromise = page.waitForResponse(
      res =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/pause`) &&
        res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Tạm dừng', exact: true }).click();
    const pauseRes = await pauseResPromise;
    expect(pauseRes.ok(), `POST /pause failed: ${await pauseRes.text()}`).toBeTruthy();

    // Verify UI reflects PAUSED
    await expect(card).toContainText('TẠM DỪNG (DOMINO SHIFT)');
    await expect(page.getByRole('button', { name: /Tạm dừng \(1\)/ })).toBeVisible();

    // Verify real DB status is PAUSED
    let backendRoadmaps = await fetchBackendRoadmaps(request);
    expect(backendRoadmaps.find(r => r.id === roadmapId)?.status).toBe('PAUSED');

    // Reload page (F5) -> confirm still PAUSED
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Roadmap Hub' })).toBeVisible();
    const reloadedCard = page.locator('app-roadmap-card').filter({ hasText: roadmapTitle });
    await expect(reloadedCard).toContainText('TẠM DỪNG (DOMINO SHIFT)');
    await expect(page.getByRole('button', { name: /Tạm dừng \(1\)/ })).toBeVisible();

    // Trigger Resume via UI -> Adaptation Modal -> Confirm
    await reloadedCard.getByRole('button', { name: /Kích hoạt lại lộ trình/ }).click();
    await expect(page.getByTestId('adaptation-modal-container')).toBeVisible();

    const resumeResPromise = page.waitForResponse(
      res =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/resume`) &&
        res.request().method() === 'POST'
    );
    await page.getByTestId('adaptation-confirm-btn').click();
    const resumeRes = await resumeResPromise;
    expect(resumeRes.ok(), `POST /resume failed: ${await resumeRes.text()}`).toBeTruthy();

    await expect(page.getByTestId('adaptation-modal-container')).toBeHidden();
    await expect(reloadedCard).toContainText('ĐANG KÍCH HOẠT');
    await expect(page.getByRole('button', { name: /Đang kích hoạt \(1\)/ })).toBeVisible();

    // Verify real DB status is ACTIVE again
    backendRoadmaps = await fetchBackendRoadmaps(request);
    expect(backendRoadmaps.find(r => r.id === roadmapId)?.status).toBe('ACTIVE');
  });

  test('Workflow 4: API Apply fails (HTTP 500) -> wizard stays open, shows error, no false-success or ACTIVE DB state', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf4');
    const roadmapTitle = `E2E Apply Failure ${Date.now()}`;

    await page.goto('/dashboard');
    await expect(page.getByText('Chưa có lộ trình học tập nào')).toBeVisible();

    await page.getByTestId('dashboard-create-roadmap-btn').click();
    const { roadmapId } = await createManualDraftInWizard(page, roadmapTitle);

    // Intercept ONLY the apply POST with HTTP 500 for this negative test
    await page.route('**/api/v1/roadmaps/*/proposals/*/apply', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Simulated apply failure' }),
        });
        return;
      }
      await route.continue();
    });

    await page.getByTestId('apply-proposal-btn').click();

    // Wizard MUST remain open and display error banner
    await expect(page.getByTestId('wizard-dialog-container')).toBeVisible();
    await expect(page.getByTestId('wizard-error-banner')).toBeVisible();
    await expect(page.getByTestId('wizard-error-banner')).toContainText('Simulated apply failure');

    // Close wizard manually and verify Dashboard did NOT optimistically show active roadmap
    await page.getByTestId('wizard-close-btn').click();
    await expect(page.getByTestId('wizard-dialog-container')).toBeHidden();
    await expect(page.getByText('Chưa có lộ trình học tập nào')).toBeVisible();

    // Real backend DB must NOT have this roadmap as ACTIVE
    const backendRoadmaps = await fetchBackendRoadmaps(request);
    const persisted = backendRoadmaps.find(r => r.id === roadmapId);
    expect(persisted).toBeDefined();
    expect(persisted?.status).not.toBe('ACTIVE');
  });

  test('Workflow 5: Page Reload & Route Navigation (/dashboard <-> /roadmaps) -> data remains consistent', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf5');
    const roadmapTitle = `E2E Cross Route ${Date.now()}`;

    // Create & apply roadmap from /dashboard
    await page.goto('/dashboard');
    await expect(page.getByText('Chưa có lộ trình học tập nào')).toBeVisible();

    await page.getByTestId('dashboard-create-roadmap-btn').click();
    const { roadmapId } = await createManualDraftInWizard(page, roadmapTitle);

    const applyResPromise = page.waitForResponse(
      res =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/proposals/`) &&
        res.url().endsWith('/apply') &&
        res.request().method() === 'POST'
    );
    await page.getByTestId('apply-proposal-btn').click();
    expect((await applyResPromise).status()).toBe(200);
    await expect(page.getByTestId('wizard-dialog-container')).toBeHidden();

    // 1. Verify /dashboard matches backend summary
    await expect(
      page.locator('app-dashboard-active-roadmaps').getByText(roadmapTitle)
    ).toBeVisible();
    let summary = await fetchBackendDashboardSummary(request);
    expect(summary.active_roadmaps?.some(r => r.id === roadmapId)).toBeTruthy();

    // 2. Navigate /dashboard -> /roadmaps and verify against backend /roadmaps
    await page.goto('/roadmaps');
    await expect(page.getByRole('heading', { name: 'Roadmap Hub' })).toBeVisible();
    const hubCard = page.locator('app-roadmap-card').filter({ hasText: roadmapTitle });
    await expect(hubCard).toBeVisible();
    await expect(hubCard).toContainText('ĐANG KÍCH HOẠT');
    let roadmaps = await fetchBackendRoadmaps(request);
    expect(roadmaps.find(r => r.id === roadmapId)?.status).toBe('ACTIVE');

    // 3. Navigate /roadmaps -> /dashboard and verify consistency
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();
    await expect(
      page.locator('app-dashboard-active-roadmaps').getByText(roadmapTitle)
    ).toBeVisible();

    // 4. Reload /dashboard (F5) and verify consistency against backend summary
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();
    await expect(
      page.locator('app-dashboard-active-roadmaps').getByText(roadmapTitle)
    ).toBeVisible();
    summary = await fetchBackendDashboardSummary(request);
    expect(summary.active_roadmaps?.some(r => r.id === roadmapId)).toBeTruthy();

    // 5. Navigate to /roadmaps & reload (F5) and verify consistency against backend /roadmaps
    await page.goto('/roadmaps');
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Roadmap Hub' })).toBeVisible();
    await expect(
      page.locator('app-roadmap-card').filter({ hasText: roadmapTitle })
    ).toContainText('ĐANG KÍCH HOẠT');
    roadmaps = await fetchBackendRoadmaps(request);
    expect(roadmaps.find(r => r.id === roadmapId)?.status).toBe('ACTIVE');
  });
});
