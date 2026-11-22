import { test, expect, Page, APIRequestContext, Cookie } from '@playwright/test';
import { E2E_CSRF_HEADERS, registerUserWithOtp } from './helpers/otp-auth.helper';

const BACKEND_API_URL = process.env['BACKEND_API_URL'] || 'http://127.0.0.1:3000/api/v1';

interface ApiTaskRecord {
  id: string;
  title: string;
  status: string;
  roadmap_id: string;
}

interface ApiTodayFocusRecord {
  local_date: string;
  completed_sessions_today: number;
  studied_minutes_today: number;
  focus_task?: { id: string; title: string } | null;
  today_queue?: Array<{ id: string; title: string }>;
}

interface ApiStudySessionRecord {
  id: string;
  status: string;
  actual_minutes: number;
}

interface ApiDashboardSummaryRecord {
  kpi?: {
    completed_pomodoro_count?: number;
    monthly_hours?: number;
  };
}

interface ApiProfileRecord {
  id: string;
  email: string;
  full_name: string;
  srl_profile?: {
    total_completed_sessions: number;
    is_cold_start: boolean;
    min_sessions_required: number;
    optimal_focus_duration_mins?: number | null;
    estimation_bias_factor?: number | null;
    peak_productivity_slots?: string[];
  } | null;
}

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
): Promise<{ email: string; password: string; cookies: Cookie[] }> {
  const uniqueSuffix = `${Date.now()}.${Math.floor(Math.random() * 100000)}`;
  const email = `e2e.p2b1.${tag}.${uniqueSuffix}@focusflow.vn`;
  const password = 'Password123!';

  const regRes = await registerUserWithOtp(request, {
    fullName: `E2E P2B1 Learner ${tag}`,
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

  return { email, password, cookies: storageState.cookies };
}

async function seedTwoTaskRoadmapViaApi(
  request: APIRequestContext,
  tag: string
): Promise<{ roadmapId: string; task1Id: string; task2Id: string }> {
  const todayStr = formatLocalIsoDate(new Date());
  const task1Title = `P2B1 Task 1 — Deep Focus ${tag}`;
  const task2Title = `P2B1 Task 2 — Abandon Check ${tag}`;

  const createRoadmapRes = await request.post(`${BACKEND_API_URL}/roadmaps`, {
    headers: E2E_CSRF_HEADERS,
    data: {
      title: `P2B1 Roadmap ${tag}`,
      description: 'E2E seeded roadmap for P2B1 study data integrity verification',
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
            title: 'Cột mốc 1: Kiểm chứng toàn vẹn dữ liệu học tập',
            description: 'Thực hành Pomodoro và kiểm tra SRL profile',
            estimated_effort_minutes: 120,
          },
        ],
        tasks: [
          {
            milestone_sequence_order: 1,
            title: task1Title,
            description: 'Nhiệm vụ 1 để hoàn thành phiên học hợp lệ',
            task_type: 'PRACTICE',
            estimated_minutes: 60,
            scheduled_date: todayStr,
            scheduled_start: buildLocalIsoDateTime(todayStr, '19:00'),
            scheduled_end: buildLocalIsoDateTime(todayStr, '20:00'),
          },
          {
            milestone_sequence_order: 1,
            title: task2Title,
            description: 'Nhiệm vụ 2 để kiểm tra phiên bị hủy không tăng số phiên hoàn thành',
            task_type: 'PRACTICE',
            estimated_minutes: 60,
            scheduled_date: todayStr,
            scheduled_start: buildLocalIsoDateTime(todayStr, '20:00'),
            scheduled_end: buildLocalIsoDateTime(todayStr, '21:00'),
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

  const tasksRes = await request.get(`${BACKEND_API_URL}/tasks`);
  expect(tasksRes.ok()).toBeTruthy();
  const tasks = (await tasksRes.json()) as ApiTaskRecord[];

  const task1 = tasks.find((t) => t.roadmap_id === roadmapBody.id && t.title === task1Title);
  const task2 = tasks.find((t) => t.roadmap_id === roadmapBody.id && t.title === task2Title);
  expect(task1, 'Seeded task 1 must exist').toBeDefined();
  expect(task2, 'Seeded task 2 must exist').toBeDefined();

  return {
    roadmapId: roadmapBody.id,
    task1Id: task1!.id,
    task2Id: task2!.id,
  };
}

async function fetchTodayFocus(request: APIRequestContext): Promise<ApiTodayFocusRecord> {
  const res = await request.get(`${BACKEND_API_URL}/sessions/today-focus`);
  expect(res.ok(), `GET /sessions/today-focus failed (${res.status()})`).toBeTruthy();
  return (await res.json()) as ApiTodayFocusRecord;
}

test.describe('P2B1 — Study Data Integrity (Canonical Pomodoro & Real SRL Profile)', () => {
  test('Workflows 1–3: Pomodoro server persistence, multi-device consistency, and Profile SRL cold-start state', async ({
    page,
    request,
    browser,
  }) => {
    const tag = 'integrity';
    const { email, password } = await registerAndSetupLearner(page, request, tag);
    const { task1Id, task2Id } = await seedTwoTaskRoadmapViaApi(request, tag);

    // =========================================================================
    // WORKFLOW 1: Pomodoro Server Persistence & No LocalStorage Spoofing
    // =========================================================================

    // Inject spoofed localStorage value BEFORE navigating to /workspace
    await page.addInitScript(() => {
      window.localStorage.setItem(
        'focusflow_pomodoros_today_v1',
        JSON.stringify({ date: '2099-01-01', count: 99 })
      );
    });

    const initialTodayFocus = await fetchTodayFocus(request);
    expect(initialTodayFocus.completed_sessions_today).toBe(0);

    await page.goto('/workspace', { waitUntil: 'networkidle' });
    await expect(page.getByText('0 / 4 phiên')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('99 / 4 phiên')).toHaveCount(0);

    // Start & finalize a session with CANCELLED (abandon: early_stop + 1 min + no takeaway)
    const startCancelRes = await request.post(`${BACKEND_API_URL}/sessions/start`, {
      headers: E2E_CSRF_HEADERS,
      data: {
        task_ids: [task2Id],
        session_mode: 'STANDARD',
        planned_minutes: 25,
      },
    });
    expect(
      startCancelRes.status(),
      `Start cancel session failed: ${await startCancelRes.text()}`
    ).toBe(201);
    const cancelSession = (await startCancelRes.json()) as ApiStudySessionRecord;

    const finalizeCancelRes = await request.post(
      `${BACKEND_API_URL}/sessions/${cancelSession.id}/finalize`,
      {
        headers: E2E_CSRF_HEADERS,
        data: {
          early_stop: true,
          completed_task_ids: [],
          takeaway: null,
          actual_minutes: 1,
        },
      }
    );
    expect(
      finalizeCancelRes.ok(),
      `Finalize cancel session failed: ${await finalizeCancelRes.text()}`
    ).toBeTruthy();
    const cancelledBody = (await finalizeCancelRes.json()) as ApiStudySessionRecord;
    expect(cancelledBody.status).toBe('CANCELLED');

    const afterCancelFocus = await fetchTodayFocus(request);
    expect(afterCancelFocus.completed_sessions_today).toBe(0);

    await page.reload({ waitUntil: 'networkidle' });
    await expect(page.getByText('0 / 4 phiên')).toBeVisible({ timeout: 15000 });

    // Start & finalize a session with COMPLETED
    const startCompleteRes = await request.post(`${BACKEND_API_URL}/sessions/start`, {
      headers: E2E_CSRF_HEADERS,
      data: {
        task_ids: [task1Id],
        session_mode: 'STANDARD',
        planned_minutes: 25,
      },
    });
    expect(
      startCompleteRes.status(),
      `Start complete session failed: ${await startCompleteRes.text()}`
    ).toBe(201);
    const completeSession = (await startCompleteRes.json()) as ApiStudySessionRecord;

    const finalizeCompleteRes = await request.post(
      `${BACKEND_API_URL}/sessions/${completeSession.id}/finalize`,
      {
        headers: E2E_CSRF_HEADERS,
        data: {
          early_stop: false,
          completed_task_ids: [task1Id],
          takeaway:
            'Đã nắm vững quy trình đồng bộ phiên học Pomodoro từ máy chủ xuống giao diện người dùng mà không dựa vào bộ nhớ cục bộ.',
          self_confidence: 4,
          actual_minutes: 25,
          checkin_time_sufficiency: 'JUST_RIGHT',
          checkin_perceived_difficulty: 3,
          checkin_focus_level: 5,
        },
      }
    );
    expect(
      finalizeCompleteRes.ok(),
      `Finalize complete session failed: ${await finalizeCompleteRes.text()}`
    ).toBeTruthy();
    const completedBody = (await finalizeCompleteRes.json()) as ApiStudySessionRecord;
    expect(completedBody.status).toBe('COMPLETED');

    const afterCompleteFocus = await fetchTodayFocus(request);
    expect(afterCompleteFocus.completed_sessions_today).toBe(1);

    // Reload Workspace (F5) and verify server-persisted 1 / 4 phiên
    await page.reload({ waitUntil: 'networkidle' });
    await expect(page.getByText('1 / 4 phiên')).toBeVisible({ timeout: 15000 });

    // Verify Dashboard KPI matches persisted DB state
    const dashSummaryRes = await request.get(`${BACKEND_API_URL}/evaluation/dashboard-summary`);
    expect(dashSummaryRes.ok()).toBeTruthy();
    const dashSummary = (await dashSummaryRes.json()) as ApiDashboardSummaryRecord;
    expect(dashSummary.kpi?.completed_pomodoro_count).toBe(1);

    await page.goto('/dashboard', { waitUntil: 'networkidle' });
    await expect(page.getByText('1 phiên').first()).toBeVisible({ timeout: 15000 });

    // =========================================================================
    // WORKFLOW 2: Multi-Device Consistency After Refresh (Independent Client B)
    // =========================================================================
    const clientBContext = await browser.newContext();
    try {
      const clientBLoginRes = await clientBContext.request.post(`${BACKEND_API_URL}/auth/login`, {
        data: { email, password },
      });
      expect(
        clientBLoginRes.ok(),
        `Client B login failed (${clientBLoginRes.status()}): ${await clientBLoginRes.text()}`
      ).toBeTruthy();

      const clientBPage = await clientBContext.newPage();

      // Verify Client B has zero spoofed localStorage
      await clientBPage.goto('/workspace', { waitUntil: 'networkidle' });
      const clientBStorageVal = await clientBPage.evaluate(() =>
        window.localStorage.getItem('focusflow_pomodoros_today_v1')
      );
      expect(clientBStorageVal).toBeNull();

      // Client B immediately shows exact server-persisted count = 1
      await expect(clientBPage.getByText('1 / 4 phiên')).toBeVisible({ timeout: 15000 });

      await clientBPage.goto('/dashboard', { waitUntil: 'networkidle' });
      await expect(clientBPage.getByText('1 phiên').first()).toBeVisible({ timeout: 15000 });
    } finally {
      await clientBContext.close();
    }

    // =========================================================================
    // WORKFLOW 3: Profile Insufficient-Data SRL State (< 3 completed sessions)
    // =========================================================================
    const profileRes = await request.get(`${BACKEND_API_URL}/account/profile`);
    expect(profileRes.ok()).toBeTruthy();
    const profileBody = (await profileRes.json()) as ApiProfileRecord;
    expect(profileBody.srl_profile?.is_cold_start).toBe(true);
    const completedSessions = profileBody.srl_profile?.total_completed_sessions ?? 0;
    const minRequired = profileBody.srl_profile?.min_sessions_required ?? 3;
    expect(completedSessions).toBeLessThan(minRequired);

    await page.goto('/profile', { waitUntil: 'networkidle' });

    const banner = page.getByTestId('srl-insufficient-data-banner');
    await expect(banner).toBeVisible({ timeout: 15000 });
    await expect(banner).toContainText(
      `Chưa đủ dữ liệu học tập (${completedSessions}/${minRequired} phiên hoàn thành)`
    );

    const badge = page.getByTestId('srl-state-badge');
    await expect(badge).toContainText('SRL: Chưa đủ dữ liệu');

    await expect(page.getByTestId('srl-optimal-focus')).toHaveText('—');
    await expect(page.getByTestId('srl-estimation-bias')).toHaveText('—');
    await expect(page.getByTestId('srl-peak-slots')).toHaveText('—');

    // Zero hardcoded fake strings anywhere on the page
    const pageBodyText = await page.locator('body').innerText();
    expect(pageBodyText).not.toContain('Sequential Deep Work');
    expect(pageBodyText).not.toContain('1.05x');
    expect(pageBodyText).not.toContain('45 phút / phiên');
  });
});
