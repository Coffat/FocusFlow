import { test, expect, Page } from '@playwright/test';

const ROADMAP_ID = '018f0000-0000-7000-8000-00000000f170';
const GOAL_ID = '018f0000-0000-7000-8000-00000000g170';
const USER_ID = '018f0000-0000-7000-8000-00000000u170';
const PROPOSAL_ID = '018f0000-0000-7000-8000-00000000p170';
const SCHEDULE_ID = '018f0000-0000-7000-8000-00000000s170';

function buildWeeklySchedule() {
  const day = {
    enabled: true,
    quota_hours: 2.0,
    time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }],
    allowed_window: { start: '07:00', end: '23:00' },
    preferred_period: 'EVENING',
    min_session_minutes: 30,
  };
  return {
    monday: day,
    tuesday: day,
    wednesday: day,
    thursday: day,
    friday: day,
    saturday: { ...day, quota_hours: 0, enabled: false, time_slots: [] },
    sunday: { ...day, quota_hours: 0, enabled: false, time_slots: [] },
  };
}

interface MockWorkflowState {
  roadmapCreated: boolean;
  fitCapacityApproved: boolean;
  proposalGenerated: boolean;
  proposalApplied: boolean;
  scopeVersion: number;
  approveAttempts: number;
}

async function setupDeterministicFitCapacityRoutes(page: Page, state: MockWorkflowState): Promise<void> {
  const milestonesBase = [
    {
      id: 'ms-fit-1',
      roadmap_id: ROADMAP_ID,
      sequence_order: 1,
      title: 'Chặng 1: FastAPI & Domain Core',
      description: 'Xây dựng nền tảng REST & Hexagonal',
      estimated_effort_minutes: 180,
      status: 'PENDING',
      created_at: '2026-11-17T08:00:00Z',
      updated_at: '2026-11-17T08:00:00Z',
    },
    {
      id: 'ms-fit-2',
      roadmap_id: ROADMAP_ID,
      sequence_order: 2,
      title: 'Chặng 2: Distributed Caching & Observability (Hoãn)',
      description: 'Nội dung nâng cao vượt quỹ giờ hiện tại',
      estimated_effort_minutes: 240,
      status: 'PENDING',
      created_at: '2026-11-17T08:00:00Z',
      updated_at: '2026-11-17T08:00:00Z',
    },
  ];

  const buildPrelim = () => ({
    status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
    scope_proposal_version: state.scopeVersion,
    scope_proposal_hash: `hash-v${state.scopeVersion}`,
    requires_learner_approval: true,
    scope_approval_status: state.fitCapacityApproved ? 'APPROVED_BY_LEARNER' : 'PENDING_LEARNER_APPROVAL',
    approved_scope_version: state.fitCapacityApproved ? state.scopeVersion : null,
    hard_packable_capacity_minutes: 240,
    soft_target_capacity_minutes: 204,
    estimated_total_minutes: 420,
    normalized_planned_total_minutes: 180,
    kept_scope: [
      {
        sequence_order: 1,
        milestone_id: 'ms-fit-1',
        title: 'Chặng 1: FastAPI & Domain Core',
        estimated_effort_minutes: 180,
        normalized_planned_effort_minutes: 180,
        expected_outcomes: ['M1-O1: Triển khai API & Domain Entity chuẩn Hexagonal'],
      },
    ],
    deferred_scope: [
      {
        sequence_order: 2,
        milestone_id: 'ms-fit-2',
        title: 'Chặng 2: Distributed Caching & Observability (Hoãn)',
        estimated_effort_minutes: 240,
        learning_outcomes: ['M2-O1: Redis Cluster & OpenTelemetry'],
      },
    ],
    feasibility_reasons: [],
  });

  const buildMilestones = () =>
    milestonesBase.map((m, idx) => ({
      ...m,
      // Deferred milestone #2 remains PENDING even after FIT_CAPACITY approval!
      status: state.fitCapacityApproved && idx === 0 ? 'APPROVED' : 'PENDING',
    }));

  const buildProposal = () => ({
    id: PROPOSAL_ID,
    roadmap_id: ROADMAP_ID,
    user_id: USER_ID,
    status: state.proposalApplied ? 'APPLIED' : 'DRAFT',
    is_valid: true,
    has_soft_overflow: false,
    judge_status: 'PASSED',
    is_partial_schedule: false,
    feasibility_verdict: 'VERIFIED_FEASIBLE',
    schedule_completeness_status: 'FULL',
    scheduled_tasks_count: 1,
    unscheduled_tasks_count: 0,
    unscheduled_tasks: [],
    feasibility: {
      status: 'FEASIBLE',
      required_minutes: 180,
      available_minutes: 240,
      scheduled_minutes: 180,
      schedulable_ratio: 1.0,
      unscheduled_minutes: 0,
      reason_codes: [],
      recommended_actions: [],
    },
    tasks: [
      {
        task_id: 'task-fit-1',
        milestone_id: 'ms-fit-1',
        milestone_sequence_order: 1,
        title: 'Thực hành Domain Aggregate & Port/Adapter',
        description: 'Hoàn thiện module planning',
        task_type: 'PRACTICE',
        learning_objective: 'Tách biệt domain thuần Python',
        completion_criteria: 'Unit test đạt 100%',
        estimated_minutes: 90,
        scheduled_date: '2026-11-18',
        scheduled_start: '2026-11-18T19:30:00Z',
        scheduled_end: '2026-11-18T21:00:00Z',
        learning_resources: [
          {
            title: 'FastAPI Official Docs',
            url: 'https://fastapi.tiangolo.com/',
            type: 'DOCS',
          },
        ],
      },
    ],
    dependencies: [],
    violations: [],
    soft_overflow_warnings: [],
    advisory_warnings: [],
    diff_summary: {
      preserved_completed_tasks_count: 0,
      replaced_tasks_count: 0,
      inserted_tasks_count: 1,
    },
    proposal_data: {},
    applied_at: state.proposalApplied ? '2026-11-17T08:15:00Z' : null,
    created_at: '2026-11-17T08:10:00Z',
    updated_at: '2026-11-17T08:10:00Z',
  });

  const buildRoadmapBase = () => ({
    id: ROADMAP_ID,
    user_id: USER_ID,
    goal_id: GOAL_ID,
    title: 'Lộ trình FastAPI FIT_CAPACITY',
    description: 'Kiểm thử luồng thu gọn phạm vi FIT_CAPACITY',
    status: state.proposalApplied ? 'ACTIVE' : 'INITIALIZED',
    start_date: '2026-11-17',
    target_date: '2026-11-24',
    created_at: '2026-11-17T08:00:00Z',
    updated_at: '2026-11-17T08:00:00Z',
    goal: {
      id: GOAL_ID,
      user_id: USER_ID,
      title: 'Lộ trình FastAPI FIT_CAPACITY',
      raw_description: 'Kiểm thử luồng thu gọn phạm vi FIT_CAPACITY',
      target_date: '2026-11-24',
      status: 'ACTIVE',
      prior_knowledge_level: 'INTERMEDIATE',
      clarification_context: null,
      created_at: '2026-11-17T08:00:00Z',
      updated_at: '2026-11-17T08:00:00Z',
    },
    preliminary_feasibility: buildPrelim(),
  });

  const buildOfficialSchedule = () => ({
    id: SCHEDULE_ID,
    roadmap_id: ROADMAP_ID,
    total_sessions: 1,
    total_planned_minutes: 90,
    buffer_minutes_per_week: 30,
    recovery_window_days: 7,
    daily_workload_cap_minutes: 180,
    stability_weight: 0.8,
    activated_at: '2026-11-17T08:15:00Z',
    created_at: '2026-11-17T08:15:00Z',
    updated_at: '2026-11-17T08:15:00Z',
  });

  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    const method = request.method();

    const jsonOk = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(body),
      });

    if (pathname === '/api/v1/auth/me') {
      return jsonOk({
        id: USER_ID,
        email: 'learner.fitcapacity@focusflow.vn',
        full_name: 'Nguyễn Học Viên',
        role: 'LEARNER',
        tier: 'FREE',
        timezone: 'Asia/Ho_Chi_Minh',
        created_at: '2026-11-01T00:00:00Z',
      });
    }

    if (pathname === '/api/v1/users/profile') {
      return jsonOk({
        id: USER_ID,
        email: 'learner.fitcapacity@focusflow.vn',
        full_name: 'Nguyễn Học Viên',
        timezone: 'Asia/Ho_Chi_Minh',
        role: 'LEARNER',
        tier: 'FREE',
        created_at: '2026-11-01T00:00:00Z',
      });
    }

    if (pathname === '/api/v1/users/quota') {
      return jsonOk({ remaining_quota: 20, daily_limit: 20, tier: 'FREE' });
    }

    if (pathname.startsWith('/api/v1/calendar/')) {
      return jsonOk({ connected: false, provider: 'GOOGLE', sync_status: 'NOT_CONNECTED' });
    }

    if (pathname === '/api/v1/availabilities/me') {
      return jsonOk({
        id: 'avail-fit-1',
        user_id: USER_ID,
        mode: 'MODE_A',
        calendar_integration_mode: 'NONE',
        min_session_minutes: 30,
        weekly_schedule: buildWeeklySchedule(),
        total_weekly_hours: 10.0,
        updated_at: '2026-11-17T08:00:00Z',
      });
    }

    if (pathname === '/api/v1/roadmaps' && method === 'GET') {
      return jsonOk(state.roadmapCreated ? [buildRoadmapBase()] : []);
    }

    if (pathname === '/api/v1/roadmaps' && method === 'POST') {
      state.roadmapCreated = true;
      return jsonOk(buildRoadmapBase(), 201);
    }

    if (pathname === `/api/v1/roadmaps/goals/${GOAL_ID}/clarify-questions` && method === 'POST') {
      return jsonOk({
        session_id: 'clarify-sess-1',
        round: 1,
        status: 'WAITING_ANSWER',
        questions: [
          {
            question_id: 'q1',
            text: 'Kinh nghiệm của bạn với FastAPI?',
            question_type: 'single_choice',
            options: [{ id: 'basic', label: 'Đã biết cơ bản' }],
          },
        ],
        information_gaps: [],
        next_turn_quota_cost: 0,
      });
    }

    if (pathname === `/api/v1/roadmaps/goals/${GOAL_ID}/clarify-skip` && method === 'POST') {
      return jsonOk({
        goal_id: GOAL_ID,
        session_id: 'clarify-sess-1',
        round: 1,
        status: 'SKIPPED',
        clarification_context: 'Đã bỏ qua phỏng vấn để tạo lộ trình nhanh.',
        questions: [],
        information_gaps: [],
        next_turn_quota_cost: 0,
      });
    }

    if (pathname === `/api/v1/roadmaps/${ROADMAP_ID}/milestones/generate-jobs` && method === 'POST') {
      return jsonOk({
        job_id: 'job-ms-fit-1',
        reservation_id: 'res-ms-fit-1',
        roadmap_id: ROADMAP_ID,
        job_type: 'MILESTONE_GEN',
        status: 'RESERVED',
        stream_url: '/api/v1/roadmaps/jobs/job-ms-fit-1/stream',
      });
    }

    if (pathname === '/api/v1/roadmaps/jobs/job-ms-fit-1/stream' && method === 'GET') {
      const completedPayload = {
        stage: 'COMPLETED',
        progress: 100,
        deltaText: 'Hoàn tất phân rã cột mốc',
        payload: {
          roadmap_id: ROADMAP_ID,
          milestones: buildMilestones(),
          preliminary_feasibility: buildPrelim(),
        },
      };
      const sseBody = [
        `event: stage\ndata: ${JSON.stringify({ stage: 'STREAMING', progress: 50, deltaText: 'Đang cân đối thời lượng...' })}\n\n`,
        `event: completed\ndata: ${JSON.stringify(completedPayload)}\n\n`,
      ].join('');
      return route.fulfill({
        status: 200,
        contentType: 'text/event-stream; charset=utf-8',
        headers: { 'Cache-Control': 'no-cache' },
        body: sseBody,
      });
    }

    if (pathname === `/api/v1/roadmaps/${ROADMAP_ID}/milestones/approve` && method === 'POST') {
      state.approveAttempts += 1;
      const reqBody = request.postDataJSON() as {
        confirmed_scope_proposal_version?: number | null;
        accept_fit_capacity?: boolean;
      };

      if (!reqBody.accept_fit_capacity || reqBody.confirmed_scope_proposal_version !== state.scopeVersion) {
        return jsonOk(
          {
            code: 'SCOPE_APPROVAL_REQUIRED',
            message: `Lộ trình vượt quá quỹ thời gian hiện tại và cần xác nhận thu gọn phạm vi FIT_CAPACITY phiên bản v${state.scopeVersion}.`,
            detail: `Lộ trình vượt quá quỹ thời gian hiện tại và cần xác nhận thu gọn phạm vi FIT_CAPACITY phiên bản v${state.scopeVersion}.`,
            scope_proposal_version: state.scopeVersion,
            scope_proposal_hash: `hash-v${state.scopeVersion}`,
            preliminary_feasibility: buildPrelim(),
          },
          409
        );
      }

      state.fitCapacityApproved = true;
      return jsonOk({
        roadmap_id: ROADMAP_ID,
        milestones: buildMilestones(),
        preliminary_feasibility: buildPrelim(),
      });
    }

    if (pathname === `/api/v1/roadmaps/${ROADMAP_ID}/proposals/generate-jobs` && method === 'POST') {
      return jsonOk({
        job_id: 'job-prop-fit-1',
        reservation_id: 'res-prop-fit-1',
        roadmap_id: ROADMAP_ID,
        job_type: 'SCHEDULE_PROPOSAL_GEN',
        status: 'RESERVED',
        stream_url: '/api/v1/roadmaps/jobs/job-prop-fit-1/stream',
      });
    }

    if (pathname === '/api/v1/roadmaps/jobs/job-prop-fit-1/stream' && method === 'GET') {
      state.proposalGenerated = true;
      const completedPayload = {
        stage: 'COMPLETED',
        progress: 100,
        deltaText: 'Hoàn tất sinh đề xuất lịch học',
        payload: { proposal_id: PROPOSAL_ID },
      };
      const sseBody = [
        `event: stage\ndata: ${JSON.stringify({ stage: 'VALIDATING_TIER_1_2_3', progress: 80, deltaText: 'Đang kiểm định 3 tầng...' })}\n\n`,
        `event: completed\ndata: ${JSON.stringify(completedPayload)}\n\n`,
      ].join('');
      return route.fulfill({
        status: 200,
        contentType: 'text/event-stream; charset=utf-8',
        headers: { 'Cache-Control': 'no-cache' },
        body: sseBody,
      });
    }

    if (pathname === `/api/v1/roadmaps/${ROADMAP_ID}/proposals/current` && method === 'GET') {
      return jsonOk(buildProposal());
    }

    if (pathname === `/api/v1/roadmaps/${ROADMAP_ID}/proposals/${PROPOSAL_ID}/apply` && method === 'POST') {
      state.proposalApplied = true;
      return jsonOk({
        roadmap_id: ROADMAP_ID,
        roadmap_status: 'ACTIVE',
        official_schedule_id: SCHEDULE_ID,
        proposal_id: PROPOSAL_ID,
        proposal_status: 'APPLIED',
        total_sessions: 1,
        total_planned_minutes: 90,
        preserved_completed_tasks_count: 0,
        replaced_tasks_count: 0,
        inserted_tasks_count: 1,
        affected_tasks_count: 1,
        total_shifted_minutes: 0,
        trigger_type: 'INITIAL_APPLY',
        calendar_sync_status: 'NOT_CONNECTED',
        backlog_unscheduled_tasks_count: 0,
        official_schedule: buildOfficialSchedule(),
      });
    }

    if (pathname === `/api/v1/roadmaps/${ROADMAP_ID}` && method === 'GET') {
      return jsonOk({
        ...buildRoadmapBase(),
        milestones: buildMilestones(),
        official_schedule: state.proposalApplied ? buildOfficialSchedule() : null,
        scheduled_tasks: state.proposalApplied
          ? [
              {
                id: 'sched-task-1',
                roadmap_id: ROADMAP_ID,
                milestone_id: 'ms-fit-1',
                title: 'Thực hành Domain Aggregate & Port/Adapter',
                task_type: 'PRACTICE',
                estimated_minutes: 90,
                scheduled_date: '2026-11-18',
                scheduled_start: '2026-11-18T19:30:00Z',
                scheduled_end: '2026-11-18T21:00:00Z',
                status: 'SCHEDULED',
              },
            ]
          : [],
        current_draft_proposal: state.proposalGenerated && !state.proposalApplied ? buildProposal() : null,
      });
    }

    return jsonOk({});
  });
}

test.describe('PR-B FIT_CAPACITY End-to-End Scope Approval (DEF-05)', () => {
  test('Goal -> Milestones -> 409 FIT_CAPACITY -> Confirm version -> Step 3 unlocked -> Generate Proposal -> Apply (Desktop & 375px Mobile)', async ({
    page,
  }) => {
    const state: MockWorkflowState = {
      roadmapCreated: false,
      fitCapacityApproved: false,
      proposalGenerated: false,
      proposalApplied: false,
      scopeVersion: 1,
      approveAttempts: 0,
    };

    await setupDeterministicFitCapacityRoutes(page, state);

    // 1. Navigate to /roadmaps/new and open Goal & Roadmap creation form
    await page.goto('/roadmaps/new');
    const titleInput = page.locator('[data-testid="new-goal-title-input"]');
    const toggleCreateBtn = page.locator('[data-testid="toggle-create-roadmap-btn"]');
    await expect(toggleCreateBtn).toBeVisible({ timeout: 15_000 });
    if (!(await titleInput.isVisible())) {
      await toggleCreateBtn.click();
    }
    await expect(titleInput).toBeVisible({ timeout: 10_000 });

    await page.fill('[data-testid="new-goal-title-input"]', 'Lộ trình FastAPI FIT_CAPACITY');
    await page.fill('[data-testid="new-goal-description-input"]', 'Kiểm thử luồng thu gọn phạm vi FIT_CAPACITY');
    await page.click('[data-testid="knowledge-level-INTERMEDIATE"]');
    await page.fill('[data-testid="new-goal-start-date-input"]', '2026-11-17');
    await page.fill('[data-testid="new-goal-target-date-input"]', '2026-11-24');
    await page.click('[data-testid="submit-create-roadmap-btn"]');

    // 2. Skip clarification to enter Step 2 (Milestone Review)
    await expect(page.locator('[data-testid="clarification-questionnaire-card"]')).toBeVisible({ timeout: 10_000 });
    await page.click('[data-testid="skip-clarification-btn"]');
    await expect(page.locator('[data-testid="step-2-panel"]')).toBeVisible({ timeout: 10_000 });

    // 3. Generate milestones via 2-Stage SSE
    await page.click('[data-testid="generate-milestones-ai-btn"]');
    await expect(page.locator('[data-testid="milestone-item-0"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="milestone-item-1"]')).toBeVisible();

    // 4. Attempt direct approval -> backend returns 409 SCOPE_APPROVAL_REQUIRED -> stays on Step 2
    await page.click('[data-testid="approve-milestones-btn"]');
    await expect(page.locator('[data-testid="roadmap-error-alert"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="step-2-panel"]')).toBeVisible();
    expect(state.approveAttempts).toBe(1);

    // 5. Verify FIT_CAPACITY scope panel renders version, kept_scope, deferred_scope, and milestone badges
    const panel = page.locator('[data-testid="fit-capacity-scope-panel"]');
    await expect(panel).toBeVisible();
    await expect(page.locator('[data-testid="scope-proposal-version-badge"]')).toContainText('v1');
    await expect(page.locator('[data-testid="kept-scope-list"]')).toContainText('Chặng 1: FastAPI & Domain Core');
    await expect(page.locator('[data-testid="deferred-scope-list"]')).toContainText('Chặng 2: Distributed Caching & Observability (Hoãn)');
    await expect(page.locator('[data-testid="milestone-scope-badge-0"]')).toContainText('Trong phạm vi giữ lại');
    await expect(page.locator('[data-testid="milestone-scope-badge-1"]')).toContainText('Hoãn lại (PENDING)');

    // Confirm button must remain disabled until checkbox is checked
    const confirmApproveBtn = page.locator('[data-testid="confirm-fit-capacity-approve-btn"]');
    await expect(confirmApproveBtn).toBeDisabled();

    // Verify mobile responsiveness (375px) on the planning workspace & FIT_CAPACITY panel
    await page.setViewportSize({ width: 375, height: 812 });
    const mobileFit = await page.evaluate(() => {
      const workspace = document.querySelector('.roadmap-workspace');
      const scopePanel = document.querySelector('[data-testid="fit-capacity-scope-panel"]');
      return {
        workspaceOverflow: workspace ? workspace.scrollWidth > workspace.clientWidth : true,
        panelRight: scopePanel ? Math.round(scopePanel.getBoundingClientRect().right) : 999,
        vw: window.innerWidth,
      };
    });
    expect(mobileFit.workspaceOverflow).toBe(false);
    expect(mobileFit.panelRight).toBeLessThanOrEqual(mobileFit.vw);
    await page.setViewportSize({ width: 1280, height: 800 });

    // Keyboard accessibility: focus checkbox and toggle via Space
    const confirmCheckbox = page.locator('[data-testid="confirm-fit-capacity-checkbox"]');
    await confirmCheckbox.focus();
    await page.keyboard.press('Space');
    await expect(confirmCheckbox).toBeChecked();
    await expect(confirmApproveBtn).toBeEnabled();

    // 6. Confirm FIT_CAPACITY v1 -> 200 OK -> Step 3 unlocked even though deferred milestone #2 is PENDING
    await confirmApproveBtn.click();
    await expect(page.locator('[data-testid="step-3-panel"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="unapproved-milestones-guard"]')).toHaveCount(0);
    expect(state.fitCapacityApproved).toBe(true);

    // 7. Generate Schedule Proposal (Step 3) -> Confirm Tasks -> Apply Official Schedule (Step 4)
    const genTasksBtn = page.locator('[data-testid="generate-tasks-ai-btn"]');
    await expect(genTasksBtn).toBeEnabled();
    await genTasksBtn.click();

    await expect(
      page.getByRole('textbox', { name: 'Tiêu đề nhiệm vụ *' }).first()
    ).toHaveValue('Thực hành Domain Aggregate & Port/Adapter', { timeout: 10_000 });
    await page.locator('[data-testid="confirm-tasks-to-step-4-btn"]').first().click();

    await expect(page.locator('[data-testid="step-4-panel"]')).toBeVisible({ timeout: 10_000 });
    const applyBtn = page.locator('[data-testid="apply-proposal-btn"]');
    await expect(applyBtn).toBeEnabled();
    await applyBtn.click();

    await expect(page.locator('[data-testid="official-schedule-card"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="roadmap-success-banner"]')).toContainText('Đã áp dụng lịch học chính thức');
    expect(state.proposalApplied).toBe(true);
  });
});
