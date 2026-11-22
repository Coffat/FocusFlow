import { test, expect, Page, APIRequestContext, Cookie } from '@playwright/test';
import { E2E_CSRF_HEADERS, registerUserWithOtp } from './helpers/otp-auth.helper';

const BACKEND_API_URL = process.env['BACKEND_API_URL'] || 'http://127.0.0.1:3000/api/v1';

interface ApiRoadmapRecord {
  id: string;
  title: string;
  status: string;
}

interface ApiTaskRecord {
  id: string;
  title: string;
  status: string;
  roadmap_id: string;
  scheduled_date?: string | null;
  scheduled_start?: string | null;
  scheduled_end?: string | null;
}

interface ApiScheduleWeekResponse {
  week_start: string;
  week_end: string;
  items: Array<{
    block_id: string;
    task_id: string | null;
    roadmap_id: string;
    roadmap_title: string;
    start_time: string;
    end_time: string;
    block_status: string;
    task?: {
      id: string;
      title: string;
      status: string;
    } | null;
  }>;
}

interface ApiDashboardSummaryRecord {
  kpi?: {
    completed_pomodoro_count?: number;
    monthly_hours?: number;
  };
  active_roadmaps?: Array<{
    id: string;
    title: string;
    completed_tasks?: number;
    total_tasks?: number;
  }>;
  weekly_schedule?: Array<{
    id?: string;
    task_id?: string | null;
    title?: string;
    scheduled_date?: string;
  }>;
}

interface ApiAnalyticsSummaryRecord {
  total_focused_hours: number;
  weekly_study_hours: number;
  completed_tasks_count: number;
  total_tasks_count: number;
  task_completion_rate: number;
}

interface ApiProposalRecord {
  id: string;
  status: string;
  version: number;
}

function formatLocalIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function addLocalDays(base: Date, deltaDays: number): Date {
  const dt = new Date(base.getFullYear(), base.getMonth(), base.getDate() + deltaDays);
  return dt;
}

function getLocalMondayIso(offsetWeeks = 0): string {
  const now = new Date();
  const day = now.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + diffToMonday + offsetWeeks * 7
  );
  return formatLocalIsoDate(monday);
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

/**
 * Registers a fresh isolated learner via the real backend API, configures valid
 * availability so scheduling prerequisites pass, and transfers the real HttpOnly
 * session cookies into the Playwright browser context.
 */
async function registerAndSetupLearner(
  page: Page,
  request: APIRequestContext,
  tag: string
): Promise<{ email: string; cookies: Cookie[] }> {
  const uniqueSuffix = `${Date.now()}.${Math.floor(Math.random() * 100000)}`;
  const email = `e2e.p2a.${tag}.${uniqueSuffix}@focusflow.vn`;
  const password = 'Password123!';

  const regRes = await registerUserWithOtp(request, {
    fullName: `E2E P2A Learner ${tag}`,
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

  return { email, cookies: storageState.cookies };
}

async function fetchBackendRoadmaps(request: APIRequestContext): Promise<ApiRoadmapRecord[]> {
  const res = await request.get(`${BACKEND_API_URL}/roadmaps`);
  expect(res.ok(), `GET /roadmaps failed (${res.status()})`).toBeTruthy();
  return (await res.json()) as ApiRoadmapRecord[];
}

async function fetchBackendTasks(request: APIRequestContext): Promise<ApiTaskRecord[]> {
  const res = await request.get(`${BACKEND_API_URL}/tasks`);
  expect(res.ok(), `GET /tasks failed (${res.status()})`).toBeTruthy();
  return (await res.json()) as ApiTaskRecord[];
}

async function fetchBackendScheduleWeek(
  request: APIRequestContext,
  weekStart: string
): Promise<ApiScheduleWeekResponse> {
  const res = await request.get(
    `${BACKEND_API_URL}/tasks/schedule/week?week_start=${encodeURIComponent(weekStart)}`
  );
  expect(res.ok(), `GET /tasks/schedule/week failed (${res.status()})`).toBeTruthy();
  return (await res.json()) as ApiScheduleWeekResponse;
}

async function fetchBackendDashboardSummary(
  request: APIRequestContext
): Promise<ApiDashboardSummaryRecord> {
  const res = await request.get(`${BACKEND_API_URL}/evaluation/dashboard-summary`);
  expect(res.ok(), `GET /evaluation/dashboard-summary failed (${res.status()})`).toBeTruthy();
  return (await res.json()) as ApiDashboardSummaryRecord;
}

async function fetchBackendAnalyticsSummary(
  request: APIRequestContext
): Promise<ApiAnalyticsSummaryRecord> {
  const res = await request.get(`${BACKEND_API_URL}/analytics/summary`);
  expect(res.ok(), `GET /analytics/summary failed (${res.status()})`).toBeTruthy();
  return (await res.json()) as ApiAnalyticsSummaryRecord;
}

/**
 * Seeds a real ACTIVE roadmap with a single scheduled task via real backend APIs
 * (zero mocks) so cross-feature workflows can focus on their target mutations.
 */
async function seedActiveRoadmapWithTaskViaApi(
  request: APIRequestContext,
  opts: {
    roadmapTitle: string;
    taskTitle: string;
    secondTaskTitle?: string;
    scheduledDate?: string;
    startTime?: string;
    endTime?: string;
  }
): Promise<{ roadmapId: string; taskId: string; proposalId: string; scheduledDate: string }> {
  const scheduledDate = opts.scheduledDate ?? formatLocalIsoDate(new Date());
  const startTime = opts.startTime ?? '19:00';
  const endTime = opts.endTime ?? '20:00';

  const createRoadmapRes = await request.post(`${BACKEND_API_URL}/roadmaps`, {
    headers: E2E_CSRF_HEADERS,
    data: {
      title: opts.roadmapTitle,
      description: 'E2E seeded roadmap for P2A data consistency verification',
      prior_knowledge_level: 'BEGINNER',
      start_date: scheduledDate,
      target_date: formatLocalIsoDate(addLocalDays(new Date(), 14)),
    },
  });
  expect(
    createRoadmapRes.status(),
    `POST /roadmaps failed: ${await createRoadmapRes.text()}`
  ).toBe(201);
  const roadmapBody = (await createRoadmapRes.json()) as { id: string };

  const seededTasks = [
    {
      milestone_sequence_order: 1,
      title: opts.taskTitle,
      description: 'Nhiệm vụ học tập kiểm thử đồng bộ dữ liệu P2A',
      task_type: 'PRACTICE',
      estimated_minutes: 60,
      scheduled_date: scheduledDate,
      scheduled_start: buildLocalIsoDateTime(scheduledDate, startTime),
      scheduled_end: buildLocalIsoDateTime(scheduledDate, endTime),
    },
  ];
  if (opts.secondTaskTitle) {
    seededTasks.push({
      milestone_sequence_order: 1,
      title: opts.secondTaskTitle,
      description: 'Nhiệm vụ thứ hai giữ lộ trình ở trạng thái ACTIVE sau khi hoàn thành task 1',
      task_type: 'PRACTICE',
      estimated_minutes: 60,
      scheduled_date: scheduledDate,
      scheduled_start: buildLocalIsoDateTime(scheduledDate, '20:00'),
      scheduled_end: buildLocalIsoDateTime(scheduledDate, '21:00'),
    });
  }

  const manualProposalRes = await request.post(
    `${BACKEND_API_URL}/roadmaps/${roadmapBody.id}/proposals/manual`,
    {
      headers: E2E_CSRF_HEADERS,
      data: {
        milestones: [
          {
            sequence_order: 1,
            title: 'Cột mốc 1: Thực hành cốt lõi',
            description: 'Nắm vững kiến thức nền tảng',
            estimated_effort_minutes: opts.secondTaskTitle ? 120 : 60,
          },
        ],
        tasks: seededTasks,
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

  const tasks = await fetchBackendTasks(request);
  const createdTask = tasks.find(
    (t) => t.roadmap_id === roadmapBody.id && t.title === opts.taskTitle
  );
  expect(createdTask, 'Seeded task must exist in GET /api/v1/tasks').toBeDefined();

  return {
    roadmapId: roadmapBody.id,
    taskId: createdTask!.id,
    proposalId: proposalBody.id,
    scheduledDate,
  };
}

/**
 * Drives the real Roadmap Wizard UI through Step 1 (POST /roadmaps),
 * Step 3 (add manual milestone), and Step 4 (add task + save manual plan via
 * POST /roadmaps/{id}/proposals/manual), stopping right before clicking Apply.
 */
async function createManualDraftInWizard(
  page: Page,
  roadmapTitle: string
): Promise<{ roadmapId: string }> {
  await expect(page.getByTestId('wizard-dialog-container')).toBeVisible();

  const titleInput = page.getByTestId('goal-title-textarea');
  await expect(titleInput).toBeVisible();
  await titleInput.fill(roadmapTitle);

  const createResponsePromise = page.waitForResponse(
    (res) =>
      res.url().includes('/api/v1/roadmaps') &&
      res.request().method() === 'POST' &&
      !res.url().includes('/proposals') &&
      !res.url().includes('/milestones')
  );
  await page.getByTestId('goal-submit-btn').click();
  const createRes = await createResponsePromise;
  expect(createRes.status(), `POST /roadmaps failed: ${await createRes.text()}`).toBe(201);
  const createdBody = (await createRes.json()) as { id: string };

  await page.getByTestId('wizard-step-btn-3').click();
  await expect(page.getByTestId('add-milestone-btn')).toBeVisible();
  await page.getByTestId('add-milestone-btn').click();
  await expect(page.getByTestId('milestone-title-input-0')).toBeVisible();
  await page.getByTestId('milestone-title-input-0').fill('Cột mốc 1: Nền tảng & Thực hành');

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
    (res) =>
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

async function clickNavbarLink(page: Page, label: string): Promise<void> {
  await page.locator('header.app-navbar nav').getByRole('link', { name: label }).click();
}

test.describe('P2A Cross-Feature Data Consistency E2E (Real Backend + PostgreSQL)', () => {
  test.describe.configure({ timeout: 90_000 });

  test('Workflow 1: Create Roadmap -> Apply -> Dashboard updates immediately without reload', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf1');
    const roadmapTitle = `P2A WF1 Roadmap ${Date.now()}`;

    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();
    await expect(page.getByText('Chưa có lộ trình học tập nào')).toBeVisible();

    await page.getByTestId('dashboard-create-roadmap-btn').click();
    const { roadmapId } = await createManualDraftInWizard(page, roadmapTitle);

    const applyResPromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/proposals/`) &&
        res.url().endsWith('/apply') &&
        res.request().method() === 'POST'
    );
    const summaryRefreshPromise = page.waitForResponse(
      (res) =>
        res.url().includes('/api/v1/evaluation/dashboard-summary') &&
        res.request().method() === 'GET'
    );

    await page.getByTestId('apply-proposal-btn').click();
    expect((await applyResPromise).status()).toBe(200);
    expect((await summaryRefreshPromise).ok()).toBeTruthy();

    await expect(page.getByTestId('wizard-dialog-container')).toBeHidden();
    await expect(page.getByText('Chưa có lộ trình học tập nào')).toBeHidden();
    await expect(
      page.locator('app-dashboard-active-roadmaps').getByText(roadmapTitle)
    ).toBeVisible();

    // Real backend DB readback
    const backendSummary = await fetchBackendDashboardSummary(request);
    expect(
      backendSummary.active_roadmaps?.some((r) => r.id === roadmapId && r.title === roadmapTitle)
    ).toBeTruthy();

    const backendRoadmaps = await fetchBackendRoadmaps(request);
    expect(backendRoadmaps.find((r) => r.id === roadmapId)?.status).toBe('ACTIVE');
  });

  test('Workflow 2: Pause / Resume Roadmap -> Tasks & Schedule stay consistent with DB', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf2');
    const roadmapTitle = `P2A WF2 PauseResume ${Date.now()}`;
    const taskTitle = `Task WF2 ${Date.now()}`;
    const { roadmapId } = await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
    });

    await page.goto('/roadmaps');
    await expect(page.getByRole('heading', { name: 'Roadmap Hub' })).toBeVisible();

    const card = page.locator('app-roadmap-card').filter({ hasText: roadmapTitle });
    await expect(card).toContainText('ĐANG KÍCH HOẠT');

    // Pause active roadmap via UI
    await card.getByRole('button', { name: 'Tác vụ lộ trình' }).click();
    await card.getByRole('button', { name: /Tạm dừng lộ trình/ }).click();

    const pauseResPromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/pause`) &&
        res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Tạm dừng', exact: true }).click();
    expect((await pauseResPromise).ok()).toBeTruthy();

    await expect(card).toContainText('TẠM DỪNG (DOMINO SHIFT)');
    let backendRoadmaps = await fetchBackendRoadmaps(request);
    expect(backendRoadmaps.find((r) => r.id === roadmapId)?.status).toBe('PAUSED');

    // Navigate via SPA to /tasks -> confirm roadmap list & tasks reflect persisted state
    await clickNavbarLink(page, 'Hàng đợi Task');
    await expect(page.getByRole('heading', { name: /Hàng Đợi Công Việc/ })).toBeVisible();
    await expect(page.locator('#roadmap-filter-select')).toContainText(roadmapTitle);

    // Navigate via SPA to /schedule -> confirm RoadmapStore reflects PAUSED (no stale ACTIVE)
    await clickNavbarLink(page, 'Thời khóa biểu');
    await expect(page.getByRole('heading', { name: 'Thời Khóa Biểu Học Tập' })).toBeVisible();
    await page.getByTestId('open-quick-drawer-btn').click();
    await page.getByTestId('action-reoptimize').check();
    await expect(page.locator('#drawer-roadmap-select')).toContainText(`${roadmapTitle} (PAUSED)`);
    await page.getByRole('button', { name: 'Hủy bỏ' }).click();

    // Navigate back to /roadmaps & Resume roadmap
    await clickNavbarLink(page, 'Roadmap Hub');
    const pausedCard = page.locator('app-roadmap-card').filter({ hasText: roadmapTitle });
    await expect(pausedCard).toContainText('TẠM DỪNG (DOMINO SHIFT)');
    await pausedCard.getByRole('button', { name: /Kích hoạt lại lộ trình/ }).click();
    await expect(page.getByTestId('adaptation-modal-container')).toBeVisible();

    const resumeResPromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/resume`) &&
        res.request().method() === 'POST'
    );
    await page.getByTestId('adaptation-confirm-btn').click();
    expect((await resumeResPromise).ok()).toBeTruthy();

    await expect(page.getByTestId('adaptation-modal-container')).toBeHidden();
    await expect(pausedCard).toContainText('ĐANG KÍCH HOẠT');

    backendRoadmaps = await fetchBackendRoadmaps(request);
    expect(backendRoadmaps.find((r) => r.id === roadmapId)?.status).toBe('ACTIVE');

    // Re-check /tasks and /schedule after Resume
    await clickNavbarLink(page, 'Hàng đợi Task');
    await expect(page.getByTestId('task-card').filter({ hasText: taskTitle })).toBeVisible();

    await clickNavbarLink(page, 'Thời khóa biểu');
    await page.getByTestId('open-quick-drawer-btn').click();
    await page.getByTestId('action-reoptimize').check();
    await expect(page.locator('#drawer-roadmap-select')).toContainText(`${roadmapTitle} (ACTIVE)`);
  });

  test('Workflow 3: Complete Task in Workspace -> Tasks Page reflects COMPLETED immediately', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf3');
    const roadmapTitle = `P2A WF3 WorkspaceTask ${Date.now()}`;
    const taskTitle = `Task WF3 Complete ${Date.now()}`;
    const { taskId } = await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
    });

    await page.goto('/workspace');
    await expect(page.getByTestId('workspace-left-region')).toBeVisible();
    await expect(
      page.getByRole('region', { name: 'Danh sách việc cần làm' }).getByText(taskTitle)
    ).toBeVisible();

    // Complete task directly in Workspace left panel
    const completePromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/tasks/${taskId}/complete`) && res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: `Hoàn thành nhanh nhiệm vụ: ${taskTitle}` }).click();
    expect((await completePromise).ok()).toBeTruthy();

    // Verify backend DB readback
    const backendTasks = await fetchBackendTasks(request);
    expect(backendTasks.find((t) => t.id === taskId)?.status).toBe('COMPLETED');

    // Navigate via SPA navbar to /tasks and verify immediately shown as COMPLETED
    await clickNavbarLink(page, 'Hàng đợi Task');
    await expect(page.getByRole('heading', { name: /Hàng Đợi Công Việc/ })).toBeVisible();
    await page.getByTestId('tab-completed').click();

    const completedCard = page.getByTestId('task-card').filter({ hasText: taskTitle });
    await expect(completedCard).toBeVisible();
    await expect(completedCard).toContainText('Hoàn thành');
  });

  test('Workflow 4: Complete Study Session -> Dashboard & Analytics reflect persisted DB state', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf4');
    const roadmapTitle = `P2A WF4 Session ${Date.now()}`;
    const taskTitle = `Task WF4 Study ${Date.now()}`;
    const { taskId } = await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
      secondTaskTitle: `Task WF4 Remaining ${Date.now()}`,
    });

    await page.goto('/workspace');
    await expect(
      page.getByRole('region', { name: 'Danh sách việc cần làm' }).getByText(taskTitle)
    ).toBeVisible();

    // Select task into study session if not already checked
    const taskCheckbox = page.getByRole('checkbox', {
      name: `Chọn nhiệm vụ vào phiên học: ${taskTitle}`,
    });
    if (!(await taskCheckbox.isChecked())) {
      await taskCheckbox.check();
    }

    // Start real study session
    const startSessionPromise = page.waitForResponse(
      (res) => res.url().includes('/api/v1/sessions/start') && res.request().method() === 'POST'
    );
    await page.getByTestId('start-session-btn').click();
    const startRes = await startSessionPromise;
    expect(startRes.ok(), `POST /sessions/start failed: ${await startRes.text()}`).toBeTruthy();
    const startedSession = (await startRes.json()) as { id: string };

    // Open early-stop finalize modal & submit valid takeaway + completed task
    await page.getByTestId('open-early-stop-btn').click();
    await expect(page.getByTestId('finalize-session-dialog')).toBeVisible();

    await page.getByTestId('confirm-early-stop-checkbox').check();
    const finalizeTaskCheckbox = page
      .getByTestId('finalize-session-dialog')
      .locator('label')
      .filter({ hasText: taskTitle })
      .locator('input[type="checkbox"]');
    if (!(await finalizeTaskCheckbox.isChecked())) {
      await finalizeTaskCheckbox.check();
    }

    await page
      .getByTestId('finalize-takeaway-textarea')
      .fill(
        'Đã hoàn thành bài học về đồng bộ trạng thái xuyên suốt kiến trúc Hexagonal và Outbox Pattern.'
      );

    const finalizePromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/sessions/${startedSession.id}/finalize`) &&
        res.request().method() === 'POST'
    );
    await page.getByTestId('submit-finalize-btn').click();
    const finalizeRes = await finalizePromise;
    expect(
      finalizeRes.ok(),
      `POST /sessions/finalize failed: ${await finalizeRes.text()}`
    ).toBeTruthy();

    await expect(page.getByTestId('session-finalized-banner')).toBeVisible();

    // Verify real backend DB readback
    const backendTasks = await fetchBackendTasks(request);
    expect(backendTasks.find((t) => t.id === taskId)?.status).toBe('COMPLETED');

    const backendDashboard = await fetchBackendDashboardSummary(request);
    const backendAnalytics = await fetchBackendAnalyticsSummary(request);
    expect(backendAnalytics.completed_tasks_count).toBeGreaterThanOrEqual(1);
    expect(backendDashboard.active_roadmaps?.[0]?.completed_tasks ?? 0).toBeGreaterThanOrEqual(1);

    // Navigate via SPA to /dashboard & verify UI reflects completed task / session progress
    await clickNavbarLink(page, 'Tổng quan');
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();
    await expect(
      page.locator('app-dashboard-active-roadmaps').getByText(roadmapTitle)
    ).toBeVisible();

    // Navigate via SPA to /analytics & verify KPI matches backend summary
    await clickNavbarLink(page, 'Báo cáo');
    await expect(page.getByRole('heading', { name: /Báo Cáo & Phân Tích Hiệu Suất/ })).toBeVisible();
    await expect(
      page.getByText(
        `${backendAnalytics.completed_tasks_count} / ${backendAnalytics.total_tasks_count} nhiệm vụ hoàn thành`
      )
    ).toBeVisible();
  });

  test('Workflow 5: Reschedule Task -> Schedule & Dashboard match real backend week schedule', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf5');
    const roadmapTitle = `P2A WF5 Reschedule ${Date.now()}`;
    const taskTitle = `Task WF5 Move ${Date.now()}`;

    // Schedule on Monday of current week, reschedule to Tuesday of current week (guaranteed same week)
    const mondayIso = getLocalMondayIso(0);
    const [y, m, d] = mondayIso.split('-').map(Number);
    const tuesdayIso = formatLocalIsoDate(new Date(y, (m || 1) - 1, (d || 1) + 1));

    const { taskId } = await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
      scheduledDate: mondayIso,
      startTime: '19:00',
      endTime: '20:00',
    });

    await page.goto('/schedule');
    await expect(page.getByRole('heading', { name: 'Thời Khóa Biểu Học Tập' })).toBeVisible();

    const blockItem = page.getByTestId('schedule-block-item').filter({ hasText: taskTitle });
    await expect(blockItem).toBeVisible();
    await expect(blockItem).toContainText('19:00');

    // Open reschedule modal and move to Tuesday 20:00 - 21:00
    await blockItem.getByRole('button', { name: 'Dời lịch' }).click();
    await expect(page.getByTestId('schedule-reschedule-dialog')).toBeVisible();

    await page.locator('#sched-reschedule-date').fill(tuesdayIso);
    await page.locator('#sched-reschedule-start').fill('20:00');
    await page.locator('#sched-reschedule-end').fill('21:00');

    const reschedulePromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/tasks/${taskId}/reschedule`) &&
        res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Xác nhận dời' }).click();
    const rescheduleRes = await reschedulePromise;
    expect(
      rescheduleRes.ok(),
      `POST /tasks/reschedule failed: ${await rescheduleRes.text()}`
    ).toBeTruthy();

    await expect(page.getByTestId('schedule-reschedule-dialog')).toBeHidden();
    const movedBlock = page.getByTestId('schedule-block-item').filter({ hasText: taskTitle });
    await expect(movedBlock).toBeVisible();
    await expect(movedBlock).toContainText('20:00');

    // Cross-check real backend /tasks/schedule/week
    const backendWeek = await fetchBackendScheduleWeek(request, mondayIso);
    const persistedBlock = backendWeek.items.find((item) => item.task_id === taskId);
    expect(persistedBlock).toBeDefined();
    expect(formatLocalIsoDate(new Date(persistedBlock!.start_time))).toBe(tuesdayIso);

    // Navigate via SPA to /dashboard & verify summary matches backend
    await clickNavbarLink(page, 'Tổng quan');
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();
    const backendSummary = await fetchBackendDashboardSummary(request);
    expect(backendSummary.active_roadmaps?.some((r) => r.title === roadmapTitle)).toBeTruthy();
    await expect(
      page.locator('app-dashboard-active-roadmaps').getByText(roadmapTitle)
    ).toBeVisible();
  });

  test('Workflow 6: Adaptation -> Proposal Review (DRAFT) -> Apply (Human-in-the-loop)', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf6');
    const roadmapTitle = `P2A WF6 Adaptation ${Date.now()}`;
    const taskTitle = `Task WF6 Reopt ${Date.now()}`;
    const { roadmapId } = await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
    });

    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();

    // Trigger Adaptation Modal from Dashboard AI Insights banner
    const adaptTriggerBtn = page
      .locator('app-dashboard-ai-insights')
      .getByRole('button', { name: /Tái cân bằng Domino Shift/ });
    await expect(adaptTriggerBtn).toBeVisible();
    await adaptTriggerBtn.click();
    await expect(page.getByTestId('adaptation-modal-container')).toBeVisible();

    // Confirm adaptation -> real POST /roadmaps/{id}/reoptimize-schedule (creates DRAFT, NOT auto-applied)
    const reoptPromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/reoptimize-schedule`) &&
        res.request().method() === 'POST'
    );
    await page.getByTestId('adaptation-confirm-btn').click();
    const reoptRes = await reoptPromise;
    expect(
      reoptRes.ok(),
      `POST /reoptimize-schedule failed: ${await reoptRes.text()}`
    ).toBeTruthy();

    // User lands on /roadmaps/:id to review the DRAFT proposal
    await expect(page).toHaveURL(new RegExp(`/roadmaps/${roadmapId}`));

    // Verify human-in-the-loop: OfficialSchedule NOT auto-applied; current proposal is DRAFT
    const currentPropRes = await request.get(
      `${BACKEND_API_URL}/roadmaps/${roadmapId}/proposals/current`
    );
    expect(currentPropRes.ok()).toBeTruthy();
    const draftProposal = (await currentPropRes.json()) as ApiProposalRecord;
    expect(draftProposal.status).toBe('DRAFT');

    // Wait explicitly for roadmap detail hydration to settle before switching to Step 4.
    // RoadmapService.loadRoadmapDetail() sets activeStep(3) when current_draft_proposal exists
    // and hydrates selectedDetail().official_schedule (rendering the ACTIVE badge on step-tab-4).
    const step4Tab = page.getByTestId('step-tab-4');
    await expect(step4Tab).toBeVisible();
    await expect(step4Tab).toContainText('ACTIVE');
    await expect(page.getByTestId('step-3-panel')).toBeVisible();

    // Open Step 4 (Schedule Proposal Review & Apply) after hydration settles so activeStep is not overwritten
    await step4Tab.click();
    await expect(step4Tab).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('step-4-panel')).toBeVisible();

    // Confirm any optional warning checkboxes if present
    for (const checkboxId of [
      'confirm-soft-overflow-checkbox',
      'confirm-warnings-checkbox',
      'confirm-partial-schedule-checkbox',
    ]) {
      const cb = page.getByTestId(checkboxId);
      if (await cb.isVisible().catch(() => false)) {
        await cb.check();
      }
    }

    const applyBtn = page.getByTestId('apply-proposal-btn');
    await expect(applyBtn).toBeEnabled();

    const applyPromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/proposals/${draftProposal.id}/apply`) &&
        res.request().method() === 'POST'
    );
    await applyBtn.click();
    expect((await applyPromise).status()).toBe(200);

    await expect(page.getByTestId('official-schedule-card')).toBeVisible();

    // Verify DB reflects applied proposal (ACTIVE roadmap & proposal status APPLIED)
    const afterPropRes = await request.get(
      `${BACKEND_API_URL}/roadmaps/${roadmapId}/proposals/current`
    );
    if (afterPropRes.ok()) {
      const appliedProp = (await afterPropRes.json()) as ApiProposalRecord;
      expect(appliedProp.status).not.toBe('DRAFT');
    }
    const backendRoadmaps = await fetchBackendRoadmaps(request);
    expect(backendRoadmaps.find((r) => r.id === roadmapId)?.status).toBe('ACTIVE');
  });

  test('Workflow 7: API failure (HTTP 500) -> UI error & rollback, DB unchanged', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf7');
    const roadmapTitle = `P2A WF7 ErrorRollback ${Date.now()}`;
    const taskTitle = `Task WF7 FailComplete ${Date.now()}`;
    const { taskId } = await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
    });

    await page.goto('/tasks');
    const taskCard = page.getByTestId('task-card').filter({ hasText: taskTitle });
    await expect(taskCard).toBeVisible();

    // Intercept ONLY the target mutation endpoint with HTTP 500
    await page.route(`**/api/v1/tasks/${taskId}/complete`, async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Simulated task complete failure' }),
        });
        return;
      }
      await route.continue();
    });

    await taskCard.getByRole('button', { name: 'Hoàn thành' }).click();
    const dialog = page.getByTestId('complete-task-dialog');
    await expect(dialog).toBeVisible();

    await page.getByTestId('submit-complete-task-btn').click();

    // Error alert MUST be displayed inside dialog & dialog stays open
    await expect(dialog.getByRole('alert')).toBeVisible();
    await expect(dialog.getByRole('alert')).toContainText('Simulated task complete failure');

    // Close modal & verify task was NOT falsely marked completed
    await dialog.getByRole('button', { name: 'Hủy' }).click();
    await expect(dialog).toBeHidden();
    await expect(taskCard).toBeVisible();
    await expect(taskCard).not.toContainText('Mở lại');

    // Real backend DB confirms unchanged state
    const backendTasks = await fetchBackendTasks(request);
    expect(backendTasks.find((t) => t.id === taskId)?.status).not.toBe('COMPLETED');
  });

  test('Workflow 8: Browser refresh (F5) -> State restored from backend PostgreSQL', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf8');
    const roadmapTitle = `P2A WF8 Reload ${Date.now()}`;
    const taskTitle = `Task WF8 Persist ${Date.now()}`;
    const { roadmapId, taskId } = await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
      secondTaskTitle: `Task WF8 Remaining ${Date.now()}`,
    });

    // Mutation 1: Complete task on /tasks
    await page.goto('/tasks');
    const taskCard = page.getByTestId('task-card').filter({ hasText: taskTitle });
    await expect(taskCard).toBeVisible();
    await taskCard.getByRole('button', { name: 'Hoàn thành' }).click();

    const completePromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/tasks/${taskId}/complete`) && res.request().method() === 'POST'
    );
    await page.getByTestId('submit-complete-task-btn').click();
    expect((await completePromise).ok()).toBeTruthy();

    // Mutation 2: Pause roadmap on /roadmaps
    await clickNavbarLink(page, 'Roadmap Hub');
    const card = page.locator('app-roadmap-card').filter({ hasText: roadmapTitle });
    await expect(card).toContainText('ĐANG KÍCH HOẠT');
    await card.getByRole('button', { name: 'Tác vụ lộ trình' }).click();
    await card.getByRole('button', { name: /Tạm dừng lộ trình/ }).click();

    const pausePromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/roadmaps/${roadmapId}/pause`) &&
        res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Tạm dừng', exact: true }).click();
    expect((await pausePromise).ok()).toBeTruthy();

    // Browser refresh (F5) on /roadmaps -> state restored from PostgreSQL
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Roadmap Hub' })).toBeVisible();
    await expect(
      page.locator('app-roadmap-card').filter({ hasText: roadmapTitle })
    ).toContainText('TẠM DỪNG (DOMINO SHIFT)');

    // Navigate to /tasks and execute Browser refresh (F5) -> state restored from PostgreSQL
    await page.goto('/tasks');
    await page.reload();
    await expect(page.getByRole('heading', { name: /Hàng Đợi Công Việc/ })).toBeVisible();
    await page.getByTestId('tab-completed').click();
    await expect(page.getByTestId('task-card').filter({ hasText: taskTitle })).toContainText(
      'Hoàn thành'
    );

    // Cross-check DB
    const backendTasks = await fetchBackendTasks(request);
    expect(backendTasks.find((t) => t.id === taskId)?.status).toBe('COMPLETED');
    const backendRoadmaps = await fetchBackendRoadmaps(request);
    expect(backendRoadmaps.find((r) => r.id === roadmapId)?.status).toBe('PAUSED');
  });

  test('Workflow 9: Rapid navigation & rapid week switching -> Zero console errors or stale overwrites', async ({
    page,
    request,
  }) => {
    await registerAndSetupLearner(page, request, 'wf9');
    const roadmapTitle = `P2A WF9 RapidNav ${Date.now()}`;
    const taskTitle = `Task WF9 Rapid ${Date.now()}`;
    await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
      scheduledDate: getLocalMondayIso(0),
    });

    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const unexpectedHttpErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Browser logs a 404 resource message when a fresh learner has no weekly review yet
        if (!text.includes('status of 404')) {
          consoleErrors.push(text);
        }
      }
    });
    page.on('pageerror', (err) => {
      pageErrors.push(err.message);
    });
    page.on('response', (res) => {
      const status = res.status();
      if (status >= 500 || (status === 404 && !res.url().includes('/weekly-reviews/latest'))) {
        unexpectedHttpErrors.push(`${status} ${res.url()}`);
      }
    });

    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();

    // Rapid cross-feature SPA navigation
    await clickNavbarLink(page, 'Roadmap Hub');
    await clickNavbarLink(page, 'Hàng đợi Task');
    await clickNavbarLink(page, 'Thời khóa biểu');
    await clickNavbarLink(page, 'Báo cáo');
    await clickNavbarLink(page, 'Tổng quan');

    // Final dashboard view must match real backend summary
    await expect(page.getByRole('heading', { name: 'Tổng quan học tập' })).toBeVisible();
    await expect(
      page.locator('app-dashboard-active-roadmaps').getByText(roadmapTitle)
    ).toBeVisible();

    // Rapid week switching on /schedule (+2 weeks then -2 weeks back to current week)
    await clickNavbarLink(page, 'Thời khóa biểu');
    await expect(page.getByRole('heading', { name: 'Thời Khóa Biểu Học Tập' })).toBeVisible();

    await page.getByTestId('next-week-btn').click();
    await page.getByTestId('next-week-btn').click();
    await page.getByTestId('prev-week-btn').click();

    const currentMonday = getLocalMondayIso(0);
    const finalWeekPromise = page.waitForResponse(
      (res) =>
        res.url().includes('/api/v1/tasks/schedule/week') &&
        res.url().includes(`week_start=${currentMonday}`) &&
        res.request().method() === 'GET'
    );
    await page.getByTestId('prev-week-btn').click();
    expect((await finalWeekPromise).ok()).toBeTruthy();

    // Final rendered week must match current week's backend schedule (no stale future-week overwrite)
    const backendWeek = await fetchBackendScheduleWeek(request, currentMonday);
    await expect(page.getByTestId('week-range-label')).toContainText(backendWeek.week_start);
    await expect(
      page.getByTestId('schedule-block-item').filter({ hasText: taskTitle })
    ).toBeVisible();

    expect(consoleErrors, `Unexpected console errors: ${consoleErrors.join('; ')}`).toEqual([]);
    expect(pageErrors, `Unexpected page errors: ${pageErrors.join('; ')}`).toEqual([]);
    expect(
      unexpectedHttpErrors,
      `Unexpected HTTP errors: ${unexpectedHttpErrors.join('; ')}`
    ).toEqual([]);
  });

  test('Workflow 10: Two independent authenticated clients -> Consistent persisted state after refresh', async ({
    browser,
    page,
    request,
  }) => {
    const { cookies } = await registerAndSetupLearner(page, request, 'wf10');
    const roadmapTitle = `P2A WF10 MultiClient ${Date.now()}`;
    const taskTitle = `Task WF10 Sync ${Date.now()}`;
    const { roadmapId, taskId } = await seedActiveRoadmapWithTaskViaApi(request, {
      roadmapTitle,
      taskTitle,
      secondTaskTitle: `Task WF10 Remaining ${Date.now()}`,
    });

    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    try {
      await contextA.addCookies(cookies);
      await contextB.addCookies(cookies);

      const pageA = await contextA.newPage();
      const pageB = await contextB.newPage();

      // Client B loads initial ACTIVE roadmap before Client A mutates
      await pageB.goto('/roadmaps');
      await expect(
        pageB.locator('app-roadmap-card').filter({ hasText: roadmapTitle })
      ).toContainText('ĐANG KÍCH HOẠT');

      // Client A completes task on /tasks
      await pageA.goto('/tasks');
      const taskCardA = pageA.getByTestId('task-card').filter({ hasText: taskTitle });
      await expect(taskCardA).toBeVisible();
      await taskCardA.getByRole('button', { name: 'Hoàn thành' }).click();

      const completePromiseA = pageA.waitForResponse(
        (res) =>
          res.url().includes(`/api/v1/tasks/${taskId}/complete`) &&
          res.request().method() === 'POST'
      );
      await pageA.getByTestId('submit-complete-task-btn').click();
      expect((await completePromiseA).ok()).toBeTruthy();

      // Client A pauses roadmap on /roadmaps
      await pageA.goto('/roadmaps');
      const cardA = pageA.locator('app-roadmap-card').filter({ hasText: roadmapTitle });
      await expect(cardA).toContainText('ĐANG KÍCH HOẠT');
      await cardA.getByRole('button', { name: 'Tác vụ lộ trình' }).click();
      await cardA.getByRole('button', { name: /Tạm dừng lộ trình/ }).click();

      const pausePromiseA = pageA.waitForResponse(
        (res) =>
          res.url().includes(`/api/v1/roadmaps/${roadmapId}/pause`) &&
          res.request().method() === 'POST'
      );
      await pageA.getByRole('button', { name: 'Tạm dừng', exact: true }).click();
      expect((await pausePromiseA).ok()).toBeTruthy();

      // Client B refreshes /roadmaps -> sees exact PAUSED state persisted by Client A
      await pageB.reload();
      await expect(
        pageB.locator('app-roadmap-card').filter({ hasText: roadmapTitle })
      ).toContainText('TẠM DỪNG (DOMINO SHIFT)');

      // Client B navigates to /tasks -> sees exact COMPLETED task persisted by Client A
      await pageB.goto('/tasks');
      await pageB.getByTestId('tab-completed').click();
      await expect(pageB.getByTestId('task-card').filter({ hasText: taskTitle })).toContainText(
        'Hoàn thành'
      );

      // Final real DB readback
      const backendTasks = await fetchBackendTasks(request);
      expect(backendTasks.find((t) => t.id === taskId)?.status).toBe('COMPLETED');
      const backendRoadmaps = await fetchBackendRoadmaps(request);
      expect(backendRoadmaps.find((r) => r.id === roadmapId)?.status).toBe('PAUSED');
    } finally {
      await contextA.close();
      await contextB.close();
    }
  });
});
