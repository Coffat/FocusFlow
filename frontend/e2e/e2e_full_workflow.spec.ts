import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const EVIDENCE_DIR = path.resolve(__dirname, '../../docs/evidence/e2e_screenshots');

test.describe('FocusFlow End-to-End Visual Evidence Suite', () => {
  test.beforeAll(() => {
    if (!fs.existsSync(EVIDENCE_DIR)) {
      fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
    }
  });

  test('Full E2E Flow: Auth -> Availability (Mode A/B) -> Roadmaps AI (Clarification -> Milestones SSE -> Proposal SSE -> Soft Overflow -> Apply) -> Workspace', async ({
    page,
    request
  }) => {
    test.setTimeout(120_000);

    const timestamp = Date.now();
    const testEmail = `evidence.${timestamp}@gmail.com`;
    const testPassword = 'Password123!';
    const testFullName = 'Thắng Vũ (E2E Test)';

    // =========================================================================
    // STEP 1: Registration / Sign In via Backend API and open Sign-In page
    // =========================================================================
    const regRes = await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        full_name: testFullName,
        email: testEmail,
        password: testPassword
      }
    });
    expect(regRes.ok()).toBeTruthy();

    await page.goto('/sign-in');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '01_sign_in_page.png'), fullPage: true });

    // Fill Sign-in form
    await page.fill('input[formControlName="email"]', testEmail);
    await page.fill('input[formControlName="password"]', testPassword);
    await page.click('button[type="submit"]');

    // =========================================================================
    // STEP 2: Verify Dashboard After Login
    // =========================================================================
    await page.waitForURL('**/dashboard');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '02_dashboard_logged_in.png'), fullPage: true });

    // =========================================================================
    // STEP 3: Direct URL Navigation to /availability (Session Restoration check)
    // =========================================================================
    await page.goto('/availability');
    await page.waitForURL('**/availability');
    await page.waitForLoadState('networkidle');

    expect(page.url()).toContain('/availability');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '03_availability_direct_nav.png'), fullPage: true });

    // =========================================================================
    // STEP 4: Configure Hybrid Availability (Mode A & Mode B)
    // =========================================================================
    const modeATab = page.locator('[data-testid="mode-a-tab"]');
    await modeATab.click();

    // Select preset Busy Pro to configure a solid starting schedule (13.5h/week)
    const presetBusyProBtn = page.locator('[data-testid="preset-busy-pro"]');
    if (await presetBusyProBtn.isVisible()) {
      await presetBusyProBtn.click();
    }

    // Save Mode A
    const saveAvailBtn = page.locator('[data-testid="save-availability-btn"]');
    await expect(saveAvailBtn).toBeEnabled({ timeout: 5000 });
    await saveAvailBtn.click();
    await expect(page.locator('[data-testid="save-success-banner"]')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '04_availability_mode_a_saved.png'), fullPage: true });

    // Switch to Mode B (Fixed Slots)
    const modeBTab = page.locator('[data-testid="mode-b-tab"]');
    await modeBTab.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '05_availability_mode_b_slots.png'), fullPage: true });

    // Save Mode B
    await expect(saveAvailBtn).toBeEnabled({ timeout: 5000 });
    await saveAvailBtn.click();
    await expect(page.locator('[data-testid="save-success-banner"]')).toBeVisible({ timeout: 10000 });

    // =========================================================================
    // STEP 5: Navigate to /roadmaps & Create New Goal
    // =========================================================================
    await page.goto('/roadmaps');
    await page.waitForURL('**/roadmaps');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '06_roadmaps_initial_page.png'), fullPage: true });

    // If create form is collapsed, open it
    const toggleFormBtn = page.locator('[data-testid="toggle-create-roadmap-btn"]');
    if (await toggleFormBtn.isVisible()) {
      const titleInput = page.locator('[data-testid="new-goal-title-input"]');
      if (!(await titleInput.isVisible())) {
        await toggleFormBtn.click();
      }
    }

    const today = new Date();
    const startDateStr = today.toISOString().split('T')[0];
    const targetDate = new Date(today.getTime() + 28 * 24 * 3600 * 1000);
    const targetDateStr = targetDate.toISOString().split('T')[0];

    await page.fill('[data-testid="new-goal-title-input"]', 'Luyện thi AWS Solutions Architect Associate (SAA-C03)');
    await page.fill(
      '[data-testid="new-goal-description-input"]',
      'Học chuyên sâu kiến trúc đám mây AWS, làm bài lab thực hành và giải đề thi trong 4 tuần.'
    );

    // Select prior knowledge level: INTERMEDIATE (FR-GOAL-002)
    const intermediateLvlBtn = page.locator('[data-testid="knowledge-level-INTERMEDIATE"]');
    if (await intermediateLvlBtn.isVisible()) {
      await intermediateLvlBtn.click();
    }

    await page.fill('[data-testid="new-goal-start-date-input"]', startDateStr);
    await page.fill('[data-testid="new-goal-target-date-input"]', targetDateStr);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '07_goal_form_filled.png'), fullPage: true });

    // Submit Goal creation
    await page.click('[data-testid="submit-create-roadmap-btn"]');

    // =========================================================================
    // STEP 6: AI Diagnostic Clarification Questions (FR-GOAL-002)
    // =========================================================================
    const clarifyCard = page.locator('[data-testid="clarification-questionnaire-card"]');
    await expect(clarifyCard).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '08_goal_clarification_questions.png'), fullPage: true });

    // Select options or answers for questions
    const firstOpt = page.locator('[data-testid="question-0-opt-0"]');
    if (await firstOpt.isVisible()) {
      await firstOpt.click();
    }
    const secondOpt = page.locator('[data-testid="question-1-opt-0"]');
    if (await secondOpt.isVisible()) {
      await secondOpt.click();
    }

    // Submit clarification answers
    await page.click('[data-testid="submit-clarification-btn"]');

    // Submitting answers automatically moves to Step 2 with milestones generator ready
    const genMilestonesBtn = page.locator('[data-testid="generate-milestones-ai-btn"]');
    await expect(genMilestonesBtn).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '09_clarification_submitted_step2_ready.png'), fullPage: true });

    // Verify diagnosed context can also be viewed on Step 1
    await page.click('[data-testid="step-tab-1"]');
    await expect(page.locator('[data-testid="clarification-context-card"]')).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '10_clarification_context_saved.png'), fullPage: true });

    // Switch back to Step 2
    await page.click('[data-testid="step-tab-2"]');
    await expect(genMilestonesBtn).toBeVisible({ timeout: 5000 });

    // =========================================================================
    // STEP 7: Generate Milestones with AI via 2-Stage SSE (UC-07)
    // =========================================================================
    await page.click('[data-testid="generate-milestones-ai-btn"]');

    // Wait for SSE streaming completion (milestones list populated)
    await page.waitForSelector('[data-testid="milestone-item-0"]', { state: 'visible', timeout: 30000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '11_milestones_generated_sse.png'), fullPage: true });

    // =========================================================================
    // STEP 8: Approve Milestones (FR-PLAN-001 Approval Gate) & Go to Step 3
    // =========================================================================
    const approveMilestonesBtn = page.locator('[data-testid="approve-milestones-btn"]');
    await approveMilestonesBtn.click();

    // Verify approval badge appears
    await page.waitForSelector('text=APPROVED', { state: 'visible', timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '12_milestones_approved.png'), fullPage: true });

    // Click "Sang Bước 3: Sinh Nhiệm vụ chi tiết & Nguồn học" button
    const goToStep3Btn = page.locator('[data-testid="go-to-step-3-btn"]');
    if (await goToStep3Btn.isVisible()) {
      await goToStep3Btn.click();
    } else {
      await page.click('[data-testid="step-tab-3"]');
    }

    // =========================================================================
    // STEP 9: Step 3 — Task Decomposition by Milestone & Learning Resources (UC-08 / UC-12)
    // =========================================================================
    await page.waitForSelector('[data-testid="step-3-panel"]', { state: 'visible' });

    // Click Generate Tasks & Knowledge Decomposition
    const genTasksBtn = page.locator('[data-testid="generate-tasks-ai-btn"]');
    if (await genTasksBtn.isVisible()) {
      await genTasksBtn.click();
    } else {
      await page.click('[data-testid="generate-proposal-ai-btn"]');
    }

    // Wait for SSE proposal generation to complete (milestone task groups appear)
    await page.waitForSelector('[data-testid="milestone-task-group-0"]', { state: 'visible', timeout: 45000 });
    await page.waitForSelector('[data-testid="task-learning-resources"]', { state: 'visible', timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '13_step3_tasks_and_learning_resources.png'), fullPage: true });

    // Click "Chốt danh sách nhiệm vụ & Sang Bước 4: Xếp Thời khóa biểu"
    const confirmTasksBtn = page.locator('[data-testid="confirm-tasks-to-step-4-btn"]').first();
    await expect(confirmTasksBtn).toBeVisible({ timeout: 5000 });
    await confirmTasksBtn.click();

    // =========================================================================
    // STEP 10: Step 4 — SpatioTemporal Timetable, Diff Summary & Soft Overflow Gate
    // =========================================================================
    await page.waitForSelector('[data-testid="step-4-panel"]', { state: 'visible', timeout: 15000 });
    await page.waitForSelector('[data-testid="spatiotemporal-schedule-panel"]', { state: 'visible', timeout: 15000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '14_step4_spatiotemporal_timetable.png'), fullPage: true });

    const softOverflowCheckbox = page.locator('[data-testid="confirm-soft-overflow-checkbox"]');
    if (await softOverflowCheckbox.isVisible()) {
      await softOverflowCheckbox.check();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, '15_soft_overflow_confirmed.png'), fullPage: true });
    }

    // =========================================================================
    // STEP 11: Apply Schedule Proposal to Official Schedule & Enter Workspace
    // =========================================================================
    const applyBtn = page.locator('[data-testid="apply-proposal-btn"]');
    await expect(applyBtn).toBeEnabled({ timeout: 10000 });
    await applyBtn.click();

    // Wait for OfficialSchedule active status
    await page.waitForSelector('[data-testid="official-roadmap-status"]', { state: 'visible', timeout: 20000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '16_official_schedule_active.png'), fullPage: true });

    // Click "Bắt đầu phiên học đầu tiên tại Study Workspace"
    const goToWorkspaceBtn = page.locator('[data-testid="go-to-workspace-btn"]');
    await expect(goToWorkspaceBtn).toBeVisible({ timeout: 10000 });
    await goToWorkspaceBtn.click();

    // =========================================================================
    // STEP 12: Verify Transition to /workspace (Active Pomodoro Session Ready)
    // =========================================================================
    await page.waitForURL('**/workspace');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/workspace');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '17_workspace_pomodoro_session.png'), fullPage: true });
  });

  test('Onboarding Modal & Skip Clarification Flow (FR-GOAL-002 Skip + Presets)', async ({
    page,
    request
  }) => {
    test.setTimeout(90_000);

    const timestamp = Date.now();
    const testEmail = `onboard.${timestamp}@gmail.com`;
    const testPassword = 'Password123!';
    const testFullName = 'Learner Onboard';

    // Register user via API
    const regRes = await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        full_name: testFullName,
        email: testEmail,
        password: testPassword
      }
    });
    expect(regRes.ok()).toBeTruthy();

    // Login via UI
    await page.goto('/sign-in');
    await page.waitForLoadState('networkidle');
    await page.fill('input[formControlName="email"]', testEmail);
    await page.fill('input[formControlName="password"]', testPassword);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard');
    await page.waitForLoadState('networkidle');

    // Go directly to /roadmaps WITHOUT configuring availability in /availability
    await page.goto('/roadmaps');
    await page.waitForURL('**/roadmaps');
    await page.waitForLoadState('networkidle');

    // Click "+ Tạo Mục tiêu & Lộ trình mới"
    const toggleFormBtn = page.locator('[data-testid="toggle-create-roadmap-btn"]');
    await toggleFormBtn.click();

    // Verify Onboarding Modal is displayed!
    const onboardingModal = page.locator('[data-testid="availability-onboarding-modal"]');
    await expect(onboardingModal).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '18_onboarding_modal_opened.png'), fullPage: true });

    // Click Busy Pro Preset chip
    const busyProBtn = page.locator('[data-testid="onboard-preset-busy-pro"]');
    await expect(busyProBtn).toBeVisible();
    await busyProBtn.click();

    // Verify modal is closed and form is opened
    await expect(onboardingModal).toBeHidden({ timeout: 10000 });
    const titleInput = page.locator('[data-testid="new-goal-title-input"]');
    await expect(titleInput).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '19_onboarding_preset_applied_form_opened.png'), fullPage: true });

    // Fill Goal details
    await titleInput.fill('Chuyên gia Thiết kế Hệ thống Phân tán & Cloud-Native');
    await page.fill('[data-testid="new-goal-description-input"]', 'Nghiên cứu microservices, event-driven và distributed tracing');

    const today = new Date();
    const startDateStr = today.toISOString().split('T')[0];
    const targetDate = new Date(today.getTime() + 30 * 24 * 3600 * 1000);
    const targetDateStr = targetDate.toISOString().split('T')[0];
    await page.fill('[data-testid="new-goal-start-date-input"]', startDateStr);
    await page.fill('[data-testid="new-goal-target-date-input"]', targetDateStr);

    // Submit Goal
    await page.click('[data-testid="submit-create-roadmap-btn"]');

    // Verify Clarification Questions appear
    const clarifyCard = page.locator('[data-testid="clarification-questionnaire-card"]');
    await expect(clarifyCard).toBeVisible({ timeout: 15000 });

    // Click "Bỏ qua phỏng vấn (Skip)"
    const skipBtn = page.locator('[data-testid="skip-clarification-btn"]');
    await expect(skipBtn).toBeVisible();
    await skipBtn.click();

    // Verify user is immediately transitioned to Step 2 with Milestone generation button ready!
    const genMilestonesBtn = page.locator('[data-testid="generate-milestones-ai-btn"]');
    await expect(genMilestonesBtn).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '20_skip_clarification_step2_ready.png'), fullPage: true });
  });
});
