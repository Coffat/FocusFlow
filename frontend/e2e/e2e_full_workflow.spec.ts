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

  test('Full E2E Flow: Auth -> Availability (Mode A/B) -> Roadmaps AI (Milestones SSE -> Proposal SSE -> Soft Overflow -> Apply) -> Direct Navigation', async ({
    page,
    request
  }) => {
    test.setTimeout(90_000);

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

    // Verify user is NOT kicked back to sign-in
    expect(page.url()).toContain('/availability');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '03_availability_direct_nav.png'), fullPage: true });

    // =========================================================================
    // STEP 4: Configure Hybrid Availability (Mode A & Mode B)
    // =========================================================================
    // Ensure Mode A tab is active
    const modeATab = page.locator('[data-testid="mode-a-tab"]');
    await modeATab.click();

    // Adjust Monday Quota
    const mondayQuota = page.locator('[data-testid="quota-slider-monday"]');
    if (await mondayQuota.isVisible()) {
      await mondayQuota.fill('2.5');
    }

    // Click Save
    const saveAvailBtn = page.locator('[data-testid="save-availability-btn"]');
    await saveAvailBtn.click();
    await page.waitForSelector('[data-testid="save-success-banner"]', { state: 'visible', timeout: 5000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '04_availability_mode_a_saved.png'), fullPage: true });

    // Switch to Mode B (Fixed Slots)
    const modeBTab = page.locator('[data-testid="mode-b-tab"]');
    await modeBTab.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '05_availability_mode_b_slots.png'), fullPage: true });

    // Save Mode B
    await saveAvailBtn.click();
    await page.waitForSelector('[data-testid="save-success-banner"]', { state: 'visible', timeout: 5000 });

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
    await page.fill('[data-testid="new-goal-start-date-input"]', startDateStr);
    await page.fill('[data-testid="new-goal-target-date-input"]', targetDateStr);

    await page.screenshot({ path: path.join(EVIDENCE_DIR, '07_goal_form_filled.png'), fullPage: true });

    // Submit Goal creation
    await page.click('[data-testid="submit-create-roadmap-btn"]');
    await page.waitForSelector('[data-testid="generate-milestones-ai-btn"]', { state: 'visible', timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '08_goal_created_step1.png'), fullPage: true });

    // =========================================================================
    // STEP 6: Generate Milestones with AI via 2-Stage SSE (UC-07)
    // =========================================================================
    await page.click('[data-testid="generate-milestones-ai-btn"]');

    // Wait for SSE streaming completion (milestones list populated)
    await page.waitForSelector('[data-testid="milestone-item-0"]', { state: 'visible', timeout: 20000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '09_milestones_generated_sse.png'), fullPage: true });

    // =========================================================================
    // STEP 7: Approve Milestones (FR-PLAN-001 Approval Gate)
    // =========================================================================
    const approveMilestonesBtn = page.locator('[data-testid="approve-milestones-btn"]');
    await approveMilestonesBtn.click();

    // Verify approval badge appears
    await page.waitForSelector('text=APPROVED', { state: 'visible', timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '10_milestones_approved.png'), fullPage: true });

    // =========================================================================
    // STEP 8: Step 2 — Generate AI Schedule Proposal (UC-08)
    // =========================================================================
    await page.click('[data-testid="step-tab-2"]');
    await page.waitForSelector('[data-testid="step-2-panel"]', { state: 'visible' });

    // Click Generate Schedule Proposal
    const genProposalBtn = page.locator('[data-testid="generate-proposal-ai-btn"]');
    await genProposalBtn.click();

    // Wait for SSE proposal generation to complete (draft proposal tasks appear)
    await page.waitForSelector('[data-testid="proposal-task-row-0"]', { state: 'visible', timeout: 25000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '11_proposal_generated_draft.png'), fullPage: true });

    // =========================================================================
    // STEP 9: Check Validation, Diff Summary & Soft Overflow Gate (BUSR-04, UC-12)
    // =========================================================================
    const softOverflowCheckbox = page.locator('[data-testid="confirm-soft-overflow-checkbox"]');
    if (await softOverflowCheckbox.isVisible()) {
      await softOverflowCheckbox.check();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, '12_soft_overflow_confirmed.png'), fullPage: true });
    } else {
      await page.screenshot({ path: path.join(EVIDENCE_DIR, '12_proposal_verified_valid.png'), fullPage: true });
    }

    // =========================================================================
    // STEP 10: Apply Schedule Proposal to Official Schedule
    // =========================================================================
    const applyBtn = page.locator('[data-testid="apply-proposal-btn"]');
    await expect(applyBtn).toBeEnabled({ timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '13_apply_button_ready.png'), fullPage: true });
    await applyBtn.click();

    // Wait for Step 3 to activate
    await page.waitForSelector('[data-testid="step-3-panel"]', { state: 'visible', timeout: 15000 });
    await page.waitForSelector('[data-testid="official-roadmap-status"]', { state: 'visible' });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '14_official_schedule_active.png'), fullPage: true });

    // =========================================================================
    // STEP 11: Direct URL Navigation to /settings (Verify System Settings & Link)
    // =========================================================================
    await page.goto('/settings');
    await page.waitForURL('**/settings');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/settings');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '15_settings_page_direct_nav.png'), fullPage: true });
  });
});
