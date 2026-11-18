import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { RoadmapWizardHostComponent } from './roadmap-wizard-host.component';
import { RoadmapService } from '../../../services/roadmap.service';
import { API_ENDPOINTS } from '../../../../../core/constants/api-endpoints';
import { CalendarIntegrationService } from '../../../../../core/services/calendar-integration.service';

describe('RoadmapWizardHostComponent', () => {
  let component: RoadmapWizardHostComponent;
  let fixture: ComponentFixture<RoadmapWizardHostComponent>;
  let roadmapService: RoadmapService;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoadmapWizardHostComponent],
      providers: [
        RoadmapService,
        {
          provide: CalendarIntegrationService,
          useValue: {
            isConnected: signal(false),
            connection: signal({
              connected: false,
              provider: 'GOOGLE',
              sync_status: 'NOT_CONNECTED',
            }),
            loadStatus: vi.fn(() =>
              of({
                connected: false,
                provider: 'GOOGLE',
                sync_status: 'NOT_CONNECTED',
              })
            ),
          },
        },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RoadmapWizardHostComponent);
    component = fixture.componentInstance;
    roadmapService = TestBed.inject(RoadmapService);
    httpTesting = TestBed.inject(HttpTestingController);
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('không tự ý chuyển sang Bước 2 nếu API createRoadmap trả lỗi (giữ nguyên Bước 1 và hiển thị banner lỗi)', () => {
    expect(component.currentStep()).toBe(1);

    component.onGoalSubmit({
      title: 'AWS Solutions Architect',
      description: 'Test',
      goal_title: 'AWS Solutions Architect',
      goal_description: 'Test',
      prior_knowledge_level: 'BEGINNER',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
    });

    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    req.flush(
      { message: 'Máy chủ AI hiện không khả dụng.' },
      { status: 503, statusText: 'Service Unavailable' }
    );
    fixture.detectChanges();

    expect(component.currentStep()).toBe(1);
    expect(roadmapService.errorMessage()).toBe('Máy chủ AI hiện không khả dụng.');

    const compiled = fixture.nativeElement as HTMLElement;
    const alertBanner = compiled.querySelector('[data-testid="wizard-error-banner"]');
    expect(alertBanner).toBeTruthy();
    expect(alertBanner?.textContent).toContain('Máy chủ AI hiện không khả dụng.');
  });

  it('tự động chuyển sang Bước 2 khi API createRoadmap thành công', () => {
    component.onGoalSubmit({
      title: 'IELTS 7.5 Academic',
      description: 'Test',
      goal_title: 'IELTS 7.5 Academic',
      goal_description: 'Test',
      prior_knowledge_level: 'INTERMEDIATE',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
    });

    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    req.flush({
      id: 'rm-100',
      user_id: 'usr-1',
      goal_id: 'goal-100',
      title: 'IELTS 7.5 Academic',
      description: 'Test',
      status: 'INITIALIZED',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });

    const clarifyReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.CLARIFY_QUESTIONS('goal-100'));
    clarifyReq.flush({ questions: [] });
    fixture.detectChanges();

    expect(component.currentStep()).toBe(2);
  });

  it('cho phép người dùng click trực tiếp vào 4-Step Stepper trên Header để kiểm tra giao diện từng bước', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const step3Btn = compiled.querySelector('[data-testid="wizard-step-btn-3"]') as HTMLButtonElement;
    step3Btn.click();
    fixture.detectChanges();
    expect(component.currentStep()).toBe(3);

    const step4Btn = compiled.querySelector('[data-testid="wizard-step-btn-4"]') as HTMLButtonElement;
    step4Btn.click();
    fixture.detectChanges();
    expect(component.currentStep()).toBe(4);
    expect(compiled.querySelector('app-schedule-proposal-dialog')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="wizard-step-btn-5"]')).toBeNull();
  });

  it('giữ shellMaxWidthClass đồng nhất ở max-w-[1040px] trên cả 4 bước', () => {
    for (const step of [1, 2, 3, 4] as const) {
      component.onStepChange(step);
      fixture.detectChanges();
      expect(component.shellMaxWidthClass()).toBe('max-w-[1040px]');
    }
  });

  it('tự động chuyển sang Bước 4, gọi ngay onGenerateProposal khi phê duyệt Cột mốc ở Bước 3, và giữ ở Bước 4 khi SSE hoàn tất', () => {
    roadmapService.selectedRoadmapDetail.set({
      id: 'rm-100',
      user_id: 'usr-1',
      goal_id: 'goal-100',
      title: 'Học Rust',
      description: 'Systems programming',
      status: 'INITIALIZED',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    component.currentStep.set(3);
    fixture.detectChanges();

    const genProposalSpy = vi.spyOn(component, 'onGenerateProposal');

    component.onApproveMilestones();

    const approveReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE('rm-100'));
    approveReq.flush({
      roadmap_id: 'rm-100',
      milestones: [
        {
          id: 'ms-1',
          roadmap_id: 'rm-100',
          sequence_order: 1,
          title: 'Ownership & Borrowing',
          description: 'Core Rust concepts',
          status: 'APPROVED',
          created_at: '2026-11-12T00:00:00Z',
          updated_at: '2026-11-12T00:00:00Z',
        },
      ],
    });
    fixture.detectChanges();

    expect(component.currentStep()).toBe(4);
    expect(genProposalSpy).toHaveBeenCalledTimes(1);

    const jobReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.PROPOSALS_GENERATE_JOBS('rm-100'));
    jobReq.flush({ job_id: 'job-prop-100', status: 'RESERVED' });

    // Khi SSE hoàn tất sinh đề xuất, giữ ở Bước 4 để ScheduleProposalDialog hiển thị lịch
    roadmapService.proposalCompletedCount.update(c => c + 1);
    fixture.detectChanges();
    expect(component.currentStep()).toBe(4);
  });

  it('hiển thị nút Thử lại và Lập lịch thủ công khi Bước 4 gặp lỗi', () => {
    component.currentStep.set(4);
    roadmapService.errorMessage.set('Lỗi kết nối AI khi phân rã nhiệm vụ.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="step4-error-recovery-box"]')).toBeTruthy();

    const manualBtn = compiled.querySelector('[data-testid="step4-manual-fallback-btn"]') as HTMLButtonElement;
    expect(manualBtn).toBeTruthy();
    manualBtn.click();
    fixture.detectChanges();

    expect(component.currentStep()).toBe(4);
    expect(roadmapService.manualPlanningMode()).toBe(true);
  });

  it('tự động chuyển sang Bước 3 và kích hoạt onGenerateMilestones khi submit câu trả lời Bước 2', () => {
    roadmapService.selectedRoadmapDetail.set({
      id: 'rm-100',
      user_id: 'usr-1',
      goal_id: 'goal-100',
      title: 'Học Go',
      description: 'Lập trình backend Go',
      status: 'INITIALIZED',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    component.currentStep.set(2);
    fixture.detectChanges();

    const genMilestonesSpy = vi.spyOn(component, 'onGenerateMilestones');

    component.onSubmitInterviewAnswers([
      {
        question_id: 'q1',
        question_text: 'Kinh nghiệm?',
        answer: 'Mới bắt đầu',
      },
    ]);

    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.CLARIFY_ANSWERS('goal-100'));
    req.flush({
      id: 'goal-100',
      user_id: 'usr-1',
      title: 'Học Go',
      status: 'ACTIVE',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    fixture.detectChanges();

    expect(component.currentStep()).toBe(3);
    expect(genMilestonesSpy).toHaveBeenCalledTimes(1);

    const jobReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS('rm-100'));
    jobReq.flush({ job_id: 'job-100', status: 'PENDING' });
  });

  it('tự động chuyển sang Bước 3 và kích hoạt onGenerateMilestones khi bỏ qua phỏng vấn Bước 2', () => {
    roadmapService.selectedRoadmapDetail.set({
      id: 'rm-100',
      user_id: 'usr-1',
      goal_id: 'goal-100',
      title: 'Học Go',
      description: 'Lập trình backend Go',
      status: 'INITIALIZED',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    component.currentStep.set(2);
    fixture.detectChanges();

    const genMilestonesSpy = vi.spyOn(component, 'onGenerateMilestones');

    component.onSkipInterview();

    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.CLARIFY_SKIP('goal-100'));
    req.flush({
      id: 'goal-100',
      user_id: 'usr-1',
      title: 'Học Go',
      status: 'ACTIVE',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    fixture.detectChanges();

    expect(component.currentStep()).toBe(3);
    expect(genMilestonesSpy).toHaveBeenCalledTimes(1);

    const jobReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS('rm-100'));
    jobReq.flush({ job_id: 'job-100', status: 'PENDING' });
  });

  it('hiển thị hộp trạng thái live progress và làm nổi bật giai đoạn tương ứng ở Bước 4 khi SSE đạt progress 60', () => {
    component.currentStep.set(4);
    roadmapService.sseProgress.set({
      isStreaming: true,
      stage: 'VALIDATING_TIER_1_2_3',
      progress: 60,
      message: 'Đang phân rã nhiệm vụ bằng AI và chạy cổng kiểm định 3 tầng...',
      retryCount: 0,
    });
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const liveBox = compiled.querySelector('[data-testid="step4-live-progress-box"]');
    expect(liveBox).toBeTruthy();
    expect(liveBox?.textContent).toContain('60%');
    expect(liveBox?.textContent).toContain('Đang phân rã nhiệm vụ bằng AI');

    const stage2 = compiled.querySelector('[data-testid="step4-inline-stage-2"]');
    expect(stage2).toBeTruthy();
    expect(stage2?.className).toContain('text-[#246B4A]');
  });

  it('giữ nguyên Bước 3 khi 409 SCOPE_APPROVAL_REQUIRED và chuyển Bước 4 sau khi xác nhận FIT_CAPACITY', () => {
    const msList = [
      {
        id: 'ms-1',
        roadmap_id: 'rm-100',
        sequence_order: 1,
        title: 'Chặng 1',
        description: 'Core',
        estimated_effort_minutes: 180,
        status: 'PENDING',
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
      },
      {
        id: 'ms-2',
        roadmap_id: 'rm-100',
        sequence_order: 2,
        title: 'Chặng 2',
        description: 'Deferred',
        estimated_effort_minutes: 240,
        status: 'PENDING',
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
      },
    ];
    roadmapService.selectedRoadmapDetail.set({
      id: 'rm-100',
      user_id: 'usr-1',
      goal_id: 'goal-100',
      title: 'Học Rust',
      description: 'Systems programming',
      status: 'INITIALIZED',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
      milestones: msList,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    roadmapService.milestones.set(msList);
    roadmapService.editableMilestones.set(
      msList.map(m => ({
        id: m.id,
        milestone_id: m.id,
        sequence_order: m.sequence_order,
        title: m.title,
        description: m.description,
        estimated_effort_minutes: m.estimated_effort_minutes,
      }))
    );
    component.currentStep.set(3);
    fixture.detectChanges();

    component.onApproveMilestones();
    const conflictReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE('rm-100'));
    conflictReq.flush(
      {
        code: 'SCOPE_APPROVAL_REQUIRED',
        message: 'Cần xác nhận phạm vi FIT_CAPACITY v1.',
        detail: 'Cần xác nhận phạm vi FIT_CAPACITY v1.',
        scope_proposal_version: 1,
        preliminary_feasibility: {
          status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
          scope_proposal_version: 1,
          requires_learner_approval: true,
          scope_approval_status: 'PENDING_LEARNER_APPROVAL',
          kept_scope: [{ sequence_order: 1, milestone_id: 'ms-1', title: 'Chặng 1', estimated_effort_minutes: 180 }],
          deferred_scope: [{ sequence_order: 2, milestone_id: 'ms-2', title: 'Chặng 2', estimated_effort_minutes: 240 }],
          feasibility_reasons: [],
        },
      },
      { status: 409, statusText: 'Conflict' }
    );
    fixture.detectChanges();

    expect(component.currentStep()).toBe(3);

    const compiled = fixture.nativeElement as HTMLElement;
    const checkbox = compiled.querySelector('[data-testid="confirm-fit-capacity-checkbox"]') as HTMLInputElement;
    expect(checkbox).toBeTruthy();
    checkbox.click();
    fixture.detectChanges();

    const genProposalSpy = vi.spyOn(component, 'onGenerateProposal');
    (compiled.querySelector('[data-testid="confirm-fit-capacity-approve-btn"]') as HTMLButtonElement).click();

    const approveReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE('rm-100'));
    expect(approveReq.request.body).toEqual({
      confirmed_scope_proposal_version: 1,
      accept_fit_capacity: true,
    });
    approveReq.flush({
      roadmap_id: 'rm-100',
      milestones: [
        { ...msList[0], status: 'APPROVED' },
        { ...msList[1], status: 'PENDING' },
      ],
      preliminary_feasibility: {
        status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
        scope_proposal_version: 1,
        requires_learner_approval: true,
        scope_approval_status: 'APPROVED_BY_LEARNER',
        approved_scope_version: 1,
        kept_scope: [{ sequence_order: 1, milestone_id: 'ms-1', title: 'Chặng 1', estimated_effort_minutes: 180 }],
        deferred_scope: [{ sequence_order: 2, milestone_id: 'ms-2', title: 'Chặng 2', estimated_effort_minutes: 240 }],
        feasibility_reasons: [],
      },
    });
    fixture.detectChanges();

    expect(component.currentStep()).toBe(4);
    expect(genProposalSpy).toHaveBeenCalledTimes(1);

    httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.PROPOSALS_GENERATE_JOBS('rm-100')).flush({
      job_id: 'job-prop-101',
      status: 'RESERVED',
    });
  });
});
