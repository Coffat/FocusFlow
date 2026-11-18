import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router, ActivatedRoute } from '@angular/router';
import { signal } from '@angular/core';
import { of, Subject } from 'rxjs';
import { RoadmapPageComponent } from './roadmap-page.component';
import { RoadmapService } from '../../services/roadmap.service';
import { AiSseService, AiStreamChunkEvent } from '../../../../core/services/ai-sse.service';
import { API_ENDPOINTS } from '../../../../core/constants/api-endpoints';
import {
  RoadmapDetailResponse,
  ScheduleProposalResponse,
  SseJobTicketResponse,
} from '../../models/roadmap.model';
import { createDefaultSchedule } from '../../../../core/services/availability.service';
import { CalendarIntegrationService } from '../../../../core/services/calendar-integration.service';

describe('RoadmapPageComponent (WBS 6.3 3-Step AI Planning & Approval Workspace)', () => {
  let component: RoadmapPageComponent;
  let fixture: ComponentFixture<RoadmapPageComponent>;
  let service: RoadmapService;
  let httpTesting: HttpTestingController;
  let mockCalendarService: {
    connection: ReturnType<typeof signal<any>>;
    isConnected: ReturnType<typeof signal<boolean>>;
    isLoading: ReturnType<typeof signal<boolean>>;
    loadStatus: ReturnType<typeof vi.fn>;
    connectGoogleCalendar: ReturnType<typeof vi.fn>;
    disconnectGoogleCalendar: ReturnType<typeof vi.fn>;
    checkUrlCallback: ReturnType<typeof vi.fn>;
  };

  const mockDetail: RoadmapDetailResponse = {
    id: '018f0000-0000-7000-8000-000000000001',
    user_id: '018f0000-0000-7000-8000-000000000099',
    goal_id: '018f0000-0000-7000-8000-000000000010',
    title: 'Lộ trình Kiến trúc Lục giác & AI Planning',
    description: 'Tuần 9 WBS 6.1 - 6.3',
    status: 'INITIALIZED',
    start_date: '2026-11-02',
    target_date: '2026-12-30',
    created_at: '2026-10-30T08:00:00Z',
    updated_at: '2026-10-30T08:00:00Z',
    goal: {
      id: '018f0000-0000-7000-8000-000000000010',
      user_id: '018f0000-0000-7000-8000-000000000099',
      title: 'Lộ trình Kiến trúc Lục giác & AI Planning',
      raw_description: 'Tuần 9 WBS 6.1 - 6.3',
      target_date: '2026-12-30',
      status: 'ACTIVE',
      prior_knowledge_level: 'BEGINNER',
      clarification_context: null,
      created_at: '2026-10-30T08:00:00Z',
      updated_at: '2026-10-30T08:00:00Z',
    },
    milestones: [
      {
        id: 'ms-1',
        roadmap_id: '018f0000-0000-7000-8000-000000000001',
        sequence_order: 1,
        title: 'Chặng 1: Cổng kiểm định 3 tầng',
        description: 'Tier 1, Tier 2, Tier 3',
        estimated_effort_minutes: 60,
        status: 'PENDING',
        created_at: '2026-10-30T08:00:00Z',
        updated_at: '2026-10-30T08:00:00Z',
      },
    ],
    official_schedule: null,
    scheduled_tasks: [],
    current_draft_proposal: null,
  };

  beforeEach(async () => {
    mockCalendarService = {
      connection: signal({ connected: false, provider: 'GOOGLE', sync_status: 'IDLE' }),
      isConnected: signal(false),
      isLoading: signal(false),
      loadStatus: vi.fn().mockReturnValue(of({ connected: false, provider: 'GOOGLE', sync_status: 'IDLE' })),
      connectGoogleCalendar: vi.fn(),
      disconnectGoogleCalendar: vi.fn(),
      checkUrlCallback: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [RoadmapPageComponent],
      providers: [
        RoadmapService,
        provideRouter([{ path: 'availability', component: RoadmapPageComponent }]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: CalendarIntegrationService, useValue: mockCalendarService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RoadmapPageComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(RoadmapService);
    httpTesting = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    // Flush initial loadRoadmaps() on ngOnInit
    const listReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    listReq.flush([mockDetail]);
    const detailReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockDetail.id));
    detailReq.flush(mockDetail);
    const availReq = httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY);
    availReq.flush({
      id: '018f0000-0000-7000-8000-000000000055',
      user_id: mockDetail.user_id,
      mode: 'MODE_A',
      calendar_integration_mode: 'NONE',
      min_session_minutes: 30,
      weekly_schedule: createDefaultSchedule(),
      total_weekly_hours: 16.0,
      updated_at: '2026-10-30T08:00:00Z',
    });
    fixture.detectChanges();
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('hiển thị đầy đủ 4 tab bước lập kế hoạch với thuộc tính A11y chuẩn', () => {
    service.setActiveStep(1);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const tablist = compiled.querySelector('[role="tablist"]');
    expect(tablist).toBeTruthy();

    const step1Tab = compiled.querySelector('[data-testid="step-tab-1"]');
    expect(step1Tab?.getAttribute('aria-selected')).toBe('true');
    expect(compiled.querySelector('[data-testid="step-tab-2"]')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="step-tab-3"]')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="step-tab-4"]')).toBeTruthy();

    const step1Panel = compiled.querySelector('[data-testid="step-1-panel"]');
    expect(step1Panel).toBeTruthy();
  });

  it('cho phép chọn prior_knowledge_level và tạo mới Goal & Roadmap trực tiếp từ form ở Bước 1', () => {
    service.setActiveStep(1);
    fixture.detectChanges();

    const createSpy = vi.spyOn(service, 'createRoadmap');
    component.toggleCreateForm();
    fixture.detectChanges();

    component.newGoalTitle.set('Chinh phục AI Evaluation Harness');
    component.newGoalDescription.set('Kiểm thử 5 Golden Datasets');
    component.newStartDate.set('2026-11-02');
    component.newTargetDate.set('2026-12-15');

    const compiled = fixture.nativeElement as HTMLElement;
    const intermediateBtn = compiled.querySelector(
      '[data-testid="knowledge-level-INTERMEDIATE"]'
    ) as HTMLButtonElement;
    expect(intermediateBtn).toBeTruthy();
    intermediateBtn.click();
    fixture.detectChanges();

    expect(component.newPriorKnowledgeLevel()).toBe('INTERMEDIATE');

    const submitBtn = compiled.querySelector(
      '[data-testid="submit-create-roadmap-btn"]'
    ) as HTMLButtonElement;
    submitBtn.click();

    expect(createSpy).toHaveBeenCalledWith({
      title: 'Chinh phục AI Evaluation Harness',
      description: 'Kiểm thử 5 Golden Datasets',
      goal_title: 'Chinh phục AI Evaluation Harness',
      goal_description: 'Kiểm thử 5 Golden Datasets',
      prior_knowledge_level: 'INTERMEDIATE',
      start_date: '2026-11-02',
      target_date: '2026-12-15',
    });

    const postReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    postReq.flush({
      ...mockDetail,
      id: 'rm-new-2',
      goal_id: 'g-new-2',
      title: 'Chinh phục AI Evaluation Harness',
    });

    const clarifyReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.CLARIFY_QUESTIONS('g-new-2')
    );
    clarifyReq.flush({
      questions: [
        {
          question_id: 'q1',
          text: 'Mức độ nắm vững Pydantic v2 của bạn?',
          question_type: 'single_choice',
          options: [
            { id: 'unknown', label: 'Chưa rõ' },
            { id: 'basic', label: 'Cơ bản' },
            { id: 'deep', label: 'Chuyên sâu' },
          ],
        },
      ],
    });
    fixture.detectChanges();

    expect(compiled.querySelector('[data-testid="clarification-questionnaire-card"]')).toBeTruthy();
  });

  it('cho phép trả lời phỏng vấn chẩn đoán và chuyển sang Bước 2', () => {
    service.setActiveStep(1);
    service.clarificationQuestions.set([
      {
        question_id: 'q-test-1',
        id: 'q-test-1',
        text: 'Bạn đã quen thuộc với Hexagonal Architecture chưa?',
        question: 'Bạn đã quen thuộc với Hexagonal Architecture chưa?',
        placeholder: 'Chọn một đáp án',
        question_type: 'single_choice',
        options: [
          { id: 'none', label: 'Chưa từng' },
          { id: 'concept', label: 'Đã biết khái niệm' },
          { id: 'production', label: 'Đã triển khai thực tế' },
        ],
        question_purpose: 'Đánh giá kinh nghiệm kiến trúc',
        expected_answer_format: 'text',
        diagnostic_dimension: 'EXPERIENCE',
      },
    ]);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const optBtn = compiled.querySelector(
      '[data-testid="question-0-opt-1"]'
    ) as HTMLButtonElement;
    expect(optBtn).toBeTruthy();
    optBtn.click();
    fixture.detectChanges();

    expect(component.userAnswers()['q-test-1']).toBe('Đã biết khái niệm');

    const submitClarifyBtn = compiled.querySelector(
      '[data-testid="submit-clarification-btn"]'
    ) as HTMLButtonElement;
    expect(submitClarifyBtn).toBeTruthy();
    submitClarifyBtn.click();

    const ansReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.CLARIFY_ANSWERS(mockDetail.goal_id)
    );
    expect(ansReq.request.method).toBe('POST');
    expect(ansReq.request.body.answers[0].answer).toBe('Đã biết khái niệm');
    ansReq.flush({
      goal_id: mockDetail.goal_id,
      clarification_context: 'Học viên đã biết khái niệm Hexagonal Architecture.',
      message: 'Updated',
    });
    fixture.detectChanges();

    expect(service.activeStep()).toBe(2);
  });

  it('cho phép bấm Bỏ qua phỏng vấn (Skip) để lưu trạng thái SKIPPED qua API và chuyển thẳng sang Bước 2', () => {
    service.setActiveStep(1);
    service.clarificationQuestions.set([
      {
        question_id: 'q-skip-1',
        id: 'q-skip-1',
        text: 'Câu hỏi tùy chọn?',
        question: 'Câu hỏi tùy chọn?',
        placeholder: 'Chọn đáp án',
        question_type: 'single_choice',
        options: [
          { id: 'a', label: 'A' },
          { id: 'b', label: 'B' },
        ],
        question_purpose: 'Thăm dò sở thích',
        expected_answer_format: 'text',
        diagnostic_dimension: 'PREFERENCE',
      },
    ]);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const skipBtn = compiled.querySelector(
      '[data-testid="skip-clarification-btn"]'
    ) as HTMLButtonElement;
    expect(skipBtn).toBeTruthy();
    skipBtn.click();

    const skipReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.CLARIFY_SKIP(mockDetail.goal_id)
    );
    expect(skipReq.request.method).toBe('POST');
    expect(skipReq.request.body).toEqual({
      session_id: null,
      skipped_question_ids: ['q-skip-1'],
    });
    skipReq.flush({
      goal_id: mockDetail.goal_id,
      status: 'SKIPPED',
      clarification_context: '{"status":"SKIPPED"}',
      unresolved_assumptions: ['Giả định trình độ BEGINNER'],
      message: 'Clarification survey skipped and assumptions recorded',
    });
    fixture.detectChanges();

    expect(service.activeStep()).toBe(2);
  });

  it('cho phép thêm/sửa cột mốc và bấm Phê duyệt Cột mốc ở Bước 2', () => {
    service.setActiveStep(2);
    fixture.detectChanges();

    const approveSpy = vi.spyOn(service, 'approveMilestones');
    const compiled = fixture.nativeElement as HTMLElement;

    const addBtn = compiled.querySelector('[data-testid="add-milestone-btn"]') as HTMLButtonElement;
    addBtn.click();
    fixture.detectChanges();

    expect(service.editableMilestones().length).toBe(2);

    const approveBtn = compiled.querySelector(
      '[data-testid="approve-milestones-btn"]'
    ) as HTMLButtonElement;
    approveBtn.click();

    expect(approveSpy).toHaveBeenCalledWith(mockDetail.id);
    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockDetail.id));
    req.flush({
      roadmap_id: mockDetail.id,
      milestones: [
        {
          ...mockDetail.milestones![0],
          status: 'APPROVED',
        },
      ],
    });
    fixture.detectChanges();

    expect(service.activeStep()).toBe(3);
  });

  it('hiển thị danh sách nhiệm vụ theo Cột mốc và tài liệu học ở Bước 3, chuyển sang Bước 4 khi bấm xác nhận', () => {
    service.milestones.set([
      {
        ...mockDetail.milestones![0],
        status: 'APPROVED',
      },
    ]);
    service.editableTasks.set([
      {
        task_id: 'task-step3-1',
        milestone_id: mockDetail.milestones![0].id,
        milestone_sequence_order: 1,
        title: 'Nhiệm vụ Bước 3',
        description: 'Chi tiết nhiệm vụ',
        task_type: 'PRACTICE',
        learning_objective: 'Nắm vững kiến thức thực hành',
        completion_criteria: 'Viết unit test pass 100%',
        learning_resources: [
          {
            title: 'Tài liệu kiến trúc Clean Architecture',
            url: 'https://example.com/clean-arch',
            type: 'ARTICLE',
            description: 'Đọc chương 1-3',
          },
        ],
        estimated_minutes: 60,
        scheduled_date: '2026-11-02',
        scheduled_start: '19:00',
        scheduled_end: '20:00',
        prerequisite_ids: [],
      },
    ]);
    service.setActiveStep(3);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="milestone-task-group-0"]')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="task-learning-resources"]')).toBeTruthy();

    const confirmBtn = compiled.querySelector(
      '[data-testid="confirm-tasks-to-step-4-btn"]'
    ) as HTMLButtonElement;
    expect(confirmBtn).toBeTruthy();
    confirmBtn.click();
    fixture.detectChanges();

    expect(service.activeStep()).toBe(4);
  });

  it('hiển thị cảnh báo Soft Overflow ở Bước 4 và khóa nút Apply cho đến khi người học tích xác nhận', () => {
    const draftProposal: ScheduleProposalResponse = {
      id: 'prop-soft-1',
      roadmap_id: mockDetail.id,
      user_id: mockDetail.user_id,
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: true,
      judge_status: 'PASSED',
      is_partial_schedule: false,
      feasibility_verdict: 'VERIFIED_FEASIBLE',
      schedule_completeness_status: 'FULL',
      scheduled_tasks_count: 1,
      unscheduled_tasks_count: 0,
      tasks: [
        {
          task_id: 'task-1',
          milestone_id: 'ms-1',
          title: 'Ôn tập chuyên sâu Mode B',
          estimated_minutes: 90,
          scheduled_date: '2026-11-02',
          scheduled_start: '20:20',
          scheduled_end: '21:50',
          task_type: 'PRACTICE',
          learning_objective: 'Ôn tập',
          completion_criteria: 'Hoàn thành bài ôn',
          learning_resources: [],
        },
      ],
      schedule_blocks: [
        {
          task_id: 'task-1',
          sequence_in_task: 1,
          block_date: '2026-11-02',
          scheduled_start: '2026-11-02T20:20:00Z',
          scheduled_end: '2026-11-02T21:05:00Z',
          scheduled_duration_minutes: 45,
        },
        {
          task_id: 'task-1',
          sequence_in_task: 2,
          block_date: '2026-11-03',
          scheduled_start: '2026-11-03T20:20:00Z',
          scheduled_end: '2026-11-03T21:05:00Z',
          scheduled_duration_minutes: 45,
        },
      ],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [
        {
          task_index: 0,
          task_title: 'Ôn tập chuyên sâu Mode B',
          scheduled_date: '2026-11-02',
          overflow_minutes: 20,
          message: 'Tràn 20 phút cuối ngày.',
        },
      ],
      advisory_warnings: [],
      diff_summary: {
        preserved_completed_tasks_count: 3,
        replaced_tasks_count: 1,
        inserted_tasks_count: 1,
      },
      proposal_data: {},
      applied_at: null,
      created_at: '2026-10-30T08:00:00Z',
      updated_at: '2026-10-30T08:00:00Z',
    };

    service.milestones.set([
      {
        ...mockDetail.milestones![0],
        status: 'APPROVED',
      },
    ]);
    service.currentProposal.set(draftProposal);
    service.editableTasks.set([
      {
        task_id: 'task-1',
        milestone_id: 'ms-1',
        milestone_sequence_order: 1,
        title: 'Ôn tập chuyên sâu Mode B',
        description: null,
        task_type: 'PRACTICE',
        learning_objective: 'Ôn tập chuyên sâu',
        completion_criteria: 'Xong bài kiểm tra',
        learning_resources: [],
        estimated_minutes: 90,
        scheduled_date: '2026-11-02',
        scheduled_start: '20:20',
        scheduled_end: '21:50',
        prerequisite_ids: [],
      },
    ]);
    service.setActiveStep(4);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const warningPanel = compiled.querySelector('[data-testid="soft-overflow-warning-panel"]');
    expect(warningPanel).toBeTruthy();
    expect(compiled.querySelectorAll('[data-testid="proposal-schedule-blocks"] tbody tr').length).toBe(2);

    const applyBtn = compiled.querySelector('[data-testid="apply-proposal-btn"]') as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(true);

    // Check confirmation checkbox
    const checkbox = compiled.querySelector(
      '[data-testid="confirm-soft-overflow-checkbox"]'
    ) as HTMLInputElement;
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(service.confirmSoftOverflow()).toBe(true);
    expect(applyBtn.disabled).toBe(false);
  });

  it('hiển thị Lịch học Chính thức (OfficialSchedule) theo từng Cột mốc ở Bước 4 và đóng SSE khi destroy', () => {
    const closeSpy = vi.spyOn(service, 'closeActiveStream');

    service.selectedRoadmapDetail.set({
      ...mockDetail,
      status: 'ACTIVE',
      official_schedule: {
        id: 'off-1',
        roadmap_id: mockDetail.id,
        total_sessions: 1,
        total_planned_minutes: 60,
        buffer_minutes_per_week: 60,
        recovery_window_days: 7,
        daily_workload_cap_minutes: 180,
        stability_weight: 0.8,
        activated_at: '2026-10-30T10:00:00Z',
        created_at: '2026-10-30T10:00:00Z',
        updated_at: '2026-10-30T10:00:00Z',
      },
      scheduled_tasks: [
        {
          task_id: 'task-off-1',
          roadmap_id: mockDetail.id,
          milestone_id: 'ms-1',
          title: 'Phiên học chính thức #1',
          estimated_minutes: 60,
          scheduled_date: '2026-11-02',
          scheduled_start: '2026-11-02T19:30:00Z',
          scheduled_end: '2026-11-02T20:30:00Z',
          status: 'PENDING',
          roadmap_target_date: '2026-12-30',
        },
      ],
    });
    service.setActiveStep(4);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="official-total-sessions"]')?.textContent).toContain(
      '1 phiên học'
    );
    expect(
      compiled.querySelector('[data-testid="official-task-item-task-off-1"]')?.textContent
    ).toContain('Phiên học chính thức #1');

    fixture.destroy();
    expect(closeSpy).toHaveBeenCalled();
  });

  describe('Onboarding Modal Cấu hình Rảnh lai (FR-PLAN-001)', () => {
    beforeEach(() => {
      // Simulate unconfigured user profile (id is null, not saved yet)
      component.availabilityService.profile.set({
        id: null,
        user_id: mockDetail.user_id,
        mode: 'MODE_A',
        calendar_integration_mode: 'NONE',
        min_session_minutes: 30,
        weekly_schedule: createDefaultSchedule(),
        total_weekly_hours: 16.0,
        updated_at: '2026-10-30T08:00:00Z',
      });
      fixture.detectChanges();
    });

    it('mở Onboarding Modal khi người dùng chưa có cấu hình rảnh và click "+ Tạo Mục tiêu & Lộ trình mới"', () => {
      component.toggleCreateForm();
      fixture.detectChanges();

      expect(component.showOnboardingModal()).toBe(true);
      expect(component.showCreateForm()).toBe(false);

      const compiled = fixture.nativeElement as HTMLElement;
      const modal = compiled.querySelector('[data-testid="availability-onboarding-modal"]');
      expect(modal).toBeTruthy();

      const modalTitle = modal?.querySelector('#onboarding-modal-title');
      expect(modalTitle?.textContent).toContain('Thiết lập Nguồn Thời gian Rảnh cho AI');

      // Close modal
      const closeBtn = modal?.querySelector('[data-testid="close-onboarding-modal-btn"]') as HTMLButtonElement;
      expect(closeBtn).toBeTruthy();
      closeBtn.click();
      fixture.detectChanges();

      expect(component.showOnboardingModal()).toBe(false);
    });

    it('liên kết Google Calendar: đổi mode sang CONNECTED, gọi PUT API, đóng modal và mở form tạo lộ trình', () => {
      component.toggleCreateForm();
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const connectBtn = compiled.querySelector(
        '[data-testid="onboard-connect-google-btn"]'
      ) as HTMLButtonElement;
      expect(connectBtn).toBeTruthy();

      connectBtn.click();

      const putReq = httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY);
      expect(putReq.request.method).toBe('PUT');
      expect(putReq.request.body.calendar_integration_mode).toBe('CONNECTED');

      putReq.flush({
        id: 'avail-connected-id',
        user_id: mockDetail.user_id,
        mode: 'MODE_A',
        calendar_integration_mode: 'CONNECTED',
        min_session_minutes: 30,
        weekly_schedule: createDefaultSchedule(),
        total_weekly_hours: 16.0,
        updated_at: '2026-10-30T08:00:00Z',
      });
      fixture.detectChanges();

      expect(component.showOnboardingModal()).toBe(false);
      expect(component.showCreateForm()).toBe(true);
      expect(component.roadmapService.successMessage()).toBe('Đã liên kết Google Calendar thành công!');
    });

    it('chọn Preset Busy Pro: áp dụng 13.5h, gọi PUT API, đóng modal và mở form tạo lộ trình', () => {
      component.toggleCreateForm();
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const presetBtn = compiled.querySelector(
        '[data-testid="onboard-preset-busy-pro"]'
      ) as HTMLButtonElement;
      expect(presetBtn).toBeTruthy();

      presetBtn.click();

      const putReq = httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY);
      expect(putReq.request.method).toBe('PUT');

      putReq.flush({
        id: 'avail-busy-pro-id',
        user_id: mockDetail.user_id,
        mode: 'MODE_A',
        calendar_integration_mode: 'NONE',
        min_session_minutes: 30,
        weekly_schedule: component.availabilityService.weeklySchedule(),
        total_weekly_hours: 13.5,
        updated_at: '2026-10-30T08:00:00Z',
      });
      fixture.detectChanges();

      expect(component.availabilityService.totalWeeklyHours()).toBe(13.5);
      expect(component.showOnboardingModal()).toBe(false);
      expect(component.showCreateForm()).toBe(true);
      expect(component.roadmapService.successMessage()).toBe('Đã áp dụng mẫu quỹ giờ rảnh thành công!');
    });

    it('chọn Preset Uni Student: áp dụng 15.5h, gọi PUT API, đóng modal và mở form tạo lộ trình', () => {
      component.toggleCreateForm();
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const presetBtn = compiled.querySelector(
        '[data-testid="onboard-preset-uni-student"]'
      ) as HTMLButtonElement;
      expect(presetBtn).toBeTruthy();

      presetBtn.click();

      const putReq = httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY);
      expect(putReq.request.method).toBe('PUT');

      putReq.flush({
        id: 'avail-student-id',
        user_id: mockDetail.user_id,
        mode: 'MODE_A',
        calendar_integration_mode: 'NONE',
        min_session_minutes: 30,
        weekly_schedule: component.availabilityService.weeklySchedule(),
        total_weekly_hours: 15.5,
        updated_at: '2026-10-30T08:00:00Z',
      });
      fixture.detectChanges();

      expect(component.availabilityService.totalWeeklyHours()).toBe(15.5);
      expect(component.showOnboardingModal()).toBe(false);
      expect(component.showCreateForm()).toBe(true);
    });

    it('chọn Preset Bootcamper: áp dụng 36.0h, gọi PUT API, đóng modal và mở form tạo lộ trình', () => {
      component.toggleCreateForm();
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const presetBtn = compiled.querySelector(
        '[data-testid="onboard-preset-bootcamper"]'
      ) as HTMLButtonElement;
      expect(presetBtn).toBeTruthy();

      presetBtn.click();

      const putReq = httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY);
      expect(putReq.request.method).toBe('PUT');

      putReq.flush({
        id: 'avail-bootcamp-id',
        user_id: mockDetail.user_id,
        mode: 'MODE_A',
        calendar_integration_mode: 'NONE',
        min_session_minutes: 30,
        weekly_schedule: component.availabilityService.weeklySchedule(),
        total_weekly_hours: 36.0,
        updated_at: '2026-10-30T08:00:00Z',
      });
      fixture.detectChanges();

      expect(component.availabilityService.totalWeeklyHours()).toBe(36.0);
      expect(component.showOnboardingModal()).toBe(false);
      expect(component.showCreateForm()).toBe(true);
    });

    it('hiển thị nút quay lại Danh mục Lộ trình (/roadmaps)', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const backBtn = compiled.querySelector('[data-testid="back-to-roadmaps-hub"]') as HTMLAnchorElement;
      expect(backBtn).toBeTruthy();
      expect(backBtn.getAttribute('routerLink') || backBtn.getAttribute('href')).toContain('/roadmaps');
      expect(backBtn.textContent).toContain('Danh mục Lộ trình');
    });

    it('tự động mở form tạo lộ trình và dọn query param khi queryParam có autoOpen=true', () => {
      const route = TestBed.inject(ActivatedRoute);
      const router = TestBed.inject(Router);
      const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

      vi.spyOn(route.snapshot.queryParamMap, 'get').mockImplementation((k: string) => {
        if (k === 'autoOpen') return 'true';
        return null;
      });
      route.snapshot.queryParams = { autoOpen: 'true' };

      vi.spyOn(component.availabilityService, 'hasConfiguredAvailability').mockReturnValue(true);

      component.ngOnInit();

      httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE).flush([mockDetail]);
      httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY).flush({
        id: '018f0000-0000-7000-8000-000000000055',
        user_id: mockDetail.user_id,
        mode: 'MODE_A',
        calendar_integration_mode: 'NONE',
        min_session_minutes: 30,
        weekly_schedule: createDefaultSchedule(),
        total_weekly_hours: 16.0,
        updated_at: '2026-10-30T08:00:00Z',
      });

      expect(component.showCreateForm()).toBe(true);
      expect(navigateSpy).toHaveBeenCalledWith([], {
        relativeTo: route,
        queryParams: {},
        replaceUrl: true,
      });
    });

    it('khi Google Calendar isConnected === true (dù chưa có profile lịch rảnh), hasConfiguredAvailability và checkPrerequisites trả về true và mở form tạo lộ trình', () => {
      component.availabilityService.profile.set(null);
      mockCalendarService.isConnected.set(true);

      expect(component.availabilityService.hasConfiguredAvailability()).toBe(true);

      component.toggleCreateForm();

      const req = httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY);
      req.flush(null);
      fixture.detectChanges();

      expect(component.showOnboardingModal()).toBe(false);
      expect(component.showCreateForm()).toBe(true);
    });
  });

  describe('FIT_CAPACITY & PRELIMINARY_UNSCHEDULABLE (DEF-05)', () => {
    it('hiển thị FIT_CAPACITY scope panel khi 409 SCOPE_APPROVAL_REQUIRED -> xác nhận checkbox -> 200 OK -> mở khóa Bước 3 dù cột mốc hoãn vẫn PENDING', () => {
      const twoMilestones = [
        {
          id: 'ms-1',
          roadmap_id: mockDetail.id,
          sequence_order: 1,
          title: 'Chặng 1: Nền tảng cốt lõi',
          description: 'Core',
          estimated_effort_minutes: 180,
          status: 'PENDING',
          created_at: '2026-10-30T08:00:00Z',
          updated_at: '2026-10-30T08:00:00Z',
        },
        {
          id: 'ms-2',
          roadmap_id: mockDetail.id,
          sequence_order: 2,
          title: 'Chặng 2: Mở rộng chuyên sâu',
          description: 'Deferred',
          estimated_effort_minutes: 240,
          status: 'PENDING',
          created_at: '2026-10-30T08:00:00Z',
          updated_at: '2026-10-30T08:00:00Z',
        },
      ];
      service.loadRoadmapDetail(mockDetail.id);
      httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockDetail.id)).flush({
        ...mockDetail,
        milestones: twoMilestones,
      });
      fixture.detectChanges();

      expect(service.activeStep()).toBe(2);

      const compiled = fixture.nativeElement as HTMLElement;
      const approveBtn = compiled.querySelector('[data-testid="approve-milestones-btn"]') as HTMLButtonElement;
      approveBtn.click();

      const conflictPrelim = {
        status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
        scope_proposal_version: 1,
        scope_proposal_hash: 'hash-v1',
        requires_learner_approval: true,
        scope_approval_status: 'PENDING_LEARNER_APPROVAL',
        hard_packable_capacity_minutes: 240,
        estimated_total_minutes: 420,
        normalized_planned_total_minutes: 180,
        kept_scope: [
          {
            sequence_order: 1,
            milestone_id: 'ms-1',
            title: 'Chặng 1: Nền tảng cốt lõi',
            estimated_effort_minutes: 180,
            normalized_planned_effort_minutes: 180,
          },
        ],
        deferred_scope: [
          {
            sequence_order: 2,
            milestone_id: 'ms-2',
            title: 'Chặng 2: Mở rộng chuyên sâu',
            estimated_effort_minutes: 240,
          },
        ],
        feasibility_reasons: [],
      };

      const firstReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockDetail.id));
      firstReq.flush(
        {
          code: 'SCOPE_APPROVAL_REQUIRED',
          message: 'Cần xác nhận thu gọn phạm vi FIT_CAPACITY phiên bản v1.',
          detail: 'Cần xác nhận thu gọn phạm vi FIT_CAPACITY phiên bản v1.',
          scope_proposal_version: 1,
          preliminary_feasibility: conflictPrelim,
        },
        { status: 409, statusText: 'Conflict' }
      );
      fixture.detectChanges();

      // Still on Step 2, FIT_CAPACITY panel is rendered with kept/deferred/version
      expect(service.activeStep()).toBe(2);
      expect(compiled.querySelector('[data-testid="fit-capacity-scope-panel"]')).toBeTruthy();
      expect(compiled.querySelector('[data-testid="scope-proposal-version-badge"]')?.textContent).toContain('v1');
      expect(compiled.querySelector('[data-testid="kept-scope-list"]')?.textContent).toContain('Chặng 1: Nền tảng cốt lõi');
      expect(compiled.querySelector('[data-testid="deferred-scope-list"]')?.textContent).toContain('Chặng 2: Mở rộng chuyên sâu');
      expect(compiled.querySelector('[data-testid="milestone-scope-badge-0"]')?.textContent).toContain('Trong phạm vi giữ lại');
      expect(compiled.querySelector('[data-testid="milestone-scope-badge-1"]')?.textContent).toContain('Hoãn lại (PENDING)');

      const confirmApproveBtn = compiled.querySelector(
        '[data-testid="confirm-fit-capacity-approve-btn"]'
      ) as HTMLButtonElement;
      expect(confirmApproveBtn.disabled).toBe(true);

      const checkbox = compiled.querySelector('[data-testid="confirm-fit-capacity-checkbox"]') as HTMLInputElement;
      checkbox.click();
      fixture.detectChanges();
      expect(confirmApproveBtn.disabled).toBe(false);

      // Simulate stale version mismatch 409 bumping v1 -> v2
      confirmApproveBtn.click();
      const staleReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockDetail.id));
      staleReq.flush(
        {
          code: 'SCOPE_APPROVAL_REQUIRED',
          message: 'Phiên bản phạm vi đã cập nhật lên v2.',
          detail: 'Phiên bản phạm vi đã cập nhật lên v2.',
          scope_proposal_version: 2,
          preliminary_feasibility: {
            ...conflictPrelim,
            scope_proposal_version: 2,
          },
        },
        { status: 409, statusText: 'Conflict' }
      );
      fixture.detectChanges();

      expect(compiled.querySelector('[data-testid="scope-proposal-version-badge"]')?.textContent).toContain('v2');
      const checkboxAfterStale = compiled.querySelector('[data-testid="confirm-fit-capacity-checkbox"]') as HTMLInputElement;
      expect(checkboxAfterStale.checked).toBe(false);
      expect(confirmApproveBtn.disabled).toBe(true);

      // Re-confirm v2 and succeed 200 OK
      checkboxAfterStale.click();
      fixture.detectChanges();
      confirmApproveBtn.click();

      const okReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockDetail.id));
      expect(okReq.request.body).toEqual({
        confirmed_scope_proposal_version: 2,
        accept_fit_capacity: true,
      });
      okReq.flush({
        roadmap_id: mockDetail.id,
        milestones: [
          { ...twoMilestones[0], status: 'APPROVED' },
          { ...twoMilestones[1], status: 'PENDING' },
        ],
        preliminary_feasibility: {
          ...conflictPrelim,
          scope_proposal_version: 2,
          scope_approval_status: 'APPROVED_BY_LEARNER',
          approved_scope_version: 2,
        },
      });
      fixture.detectChanges();

      expect(service.areMilestonesApproved()).toBe(true);
      expect(service.activeStep()).toBe(3);
      expect(compiled.querySelector('[data-testid="step-3-panel"]')).toBeTruthy();
      expect(compiled.querySelector('[data-testid="unapproved-milestones-guard"]')).toBeNull();
    });

    it('hiển thị PRELIMINARY_UNSCHEDULABLE alert với lý do & gợi ý điều chỉnh và khóa nút phê duyệt', () => {
      service.setActiveStep(2);
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const approveBtn = compiled.querySelector('[data-testid="approve-milestones-btn"]') as HTMLButtonElement;
      approveBtn.click();

      const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockDetail.id));
      req.flush(
        {
          code: 'PRELIMINARY_UNSCHEDULABLE',
          message: 'Quỹ thời gian khả dụng không đủ cho cột mốc nền tảng đầu tiên.',
          detail: 'Quỹ thời gian khả dụng không đủ cho cột mốc nền tảng đầu tiên.',
          hard_packable_capacity_minutes: 60,
          preliminary_feasibility: {
            status: 'PRELIMINARY_UNSCHEDULABLE',
            scope_proposal_version: 0,
            requires_learner_approval: false,
            scope_approval_status: 'NOT_REQUIRED',
            hard_packable_capacity_minutes: 60,
            kept_scope: [],
            deferred_scope: [],
            feasibility_reasons: [
              {
                code: 'PRELIMINARY_UNSCHEDULABLE',
                message: 'Quỹ thời gian khả dụng (60 phút) không đủ cho cột mốc đầu tiên (180 phút).',
              },
            ],
            adjustment_options: {
              is_approximate: true,
              estimated_earliest_target_date_range: { min_date: '2026-12-20', max_date: '2027-01-05' },
              recommended_additional_weekly_minutes: 150,
            },
          },
        },
        { status: 409, statusText: 'Conflict' }
      );
      fixture.detectChanges();

      const alert = compiled.querySelector('[data-testid="preliminary-unschedulable-alert"]');
      expect(alert).toBeTruthy();
      expect(alert?.textContent).toContain('Quỹ thời gian khả dụng (60 phút) không đủ');
      expect(alert?.textContent).toContain('2026-12-20');
      expect(approveBtn.disabled).toBe(true);
    });
  });

  describe('PR-1: SSE Error UX, Retry/Resume CTA & Apply Checkboxes/Idempotency', () => {
    it('hiển thị banner lỗi fallback tiếng Việt và nút Thử lại khi SSE failed gửi error rỗng "", bấm Thử lại kích hoạt sinh lại đúng stage', () => {
      const aiSseService = TestBed.inject(AiSseService);
      const stream$ = new Subject<AiStreamChunkEvent<unknown>>();
      vi.spyOn(aiSseService, 'observeJobStream').mockReturnValue(stream$.asObservable());

      service.setActiveStep(2);
      fixture.detectChanges();

      service.generateMilestonesWithAi(mockDetail.id);
      httpTesting
        .expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS(mockDetail.id))
        .flush({
          job_id: 'job-err-ui-1',
          reservation_id: 'res-err-ui-1',
          roadmap_id: mockDetail.id,
          job_type: 'MILESTONE_GEN',
          status: 'RESERVED',
          stream_url: '/api/v1/roadmaps/jobs/job-err-ui-1/stream',
          jobId: 'job-err-ui-1',
          reservationId: 'res-err-ui-1',
          streamUrl: '/api/v1/roadmaps/jobs/job-err-ui-1/stream',
        } satisfies SseJobTicketResponse);

      stream$.next({
        eventType: 'failed',
        stage: 'FAILED',
        progress: 100,
        code: 'AI_EXECUTION_ERROR',
        error: '',
        message: '',
      });
      stream$.complete();
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const errorAlert = compiled.querySelector('[data-testid="roadmap-error-alert"]');
      expect(errorAlert).toBeTruthy();
      expect(errorAlert?.textContent).toContain('Tiến trình sinh lộ trình bằng AI thất bại');

      const retryBtn = compiled.querySelector(
        '[data-testid="roadmap-retry-ai-btn"]'
      ) as HTMLButtonElement;
      expect(retryBtn).toBeTruthy();
      expect(retryBtn.textContent).toContain('Thử lại');

      const generateSpy = vi.spyOn(service, 'generateMilestonesWithAi');
      retryBtn.click();
      fixture.detectChanges();

      expect(generateSpy).toHaveBeenCalledWith(mockDetail.id);
      httpTesting
        .expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS(mockDetail.id))
        .flush({
          job_id: 'job-err-ui-2',
          reservation_id: 'res-err-ui-2',
          roadmap_id: mockDetail.id,
          job_type: 'MILESTONE_GEN',
          status: 'RESERVED',
          stream_url: '/api/v1/roadmaps/jobs/job-err-ui-2/stream',
          jobId: 'job-err-ui-2',
          reservationId: 'res-err-ui-2',
          streamUrl: '/api/v1/roadmaps/jobs/job-err-ui-2/stream',
        } satisfies SseJobTicketResponse);
      service.closeActiveStream();
    });

    it('hiển thị nút Thử lại trên Bước 3/4 khi sinh đề xuất lịch học SSE thất bại và kích hoạt generateScheduleProposalWithAi', () => {
      const aiSseService = TestBed.inject(AiSseService);
      const stream$ = new Subject<AiStreamChunkEvent<unknown>>();
      vi.spyOn(aiSseService, 'observeJobStream').mockReturnValue(stream$.asObservable());

      service.milestones.set([{ ...mockDetail.milestones![0], status: 'APPROVED' }]);
      service.setActiveStep(3);
      fixture.detectChanges();

      service.generateScheduleProposalWithAi(mockDetail.id);
      httpTesting
        .expectOne(API_ENDPOINTS.ROADMAPS.PROPOSALS_GENERATE_JOBS(mockDetail.id))
        .flush({
          job_id: 'job-prop-err-1',
          reservation_id: 'res-prop-err-1',
          roadmap_id: mockDetail.id,
          job_type: 'SCHEDULE_PROPOSAL_GEN',
          status: 'RESERVED',
          stream_url: '/api/v1/roadmaps/jobs/job-prop-err-1/stream',
          jobId: 'job-prop-err-1',
          reservationId: 'res-prop-err-1',
          streamUrl: '/api/v1/roadmaps/jobs/job-prop-err-1/stream',
        } satisfies SseJobTicketResponse);

      stream$.next({
        eventType: 'failed',
        stage: 'FAILED',
        progress: 100,
        error: '',
      });
      stream$.complete();
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('[data-testid="roadmap-error-alert"]')?.textContent).toContain(
        'Tiến trình sinh lộ trình bằng AI thất bại'
      );
      const retryBtn = compiled.querySelector(
        '[data-testid="roadmap-retry-ai-btn"]'
      ) as HTMLButtonElement;
      expect(retryBtn).toBeTruthy();

      const retrySpy = vi.spyOn(service, 'generateScheduleProposalWithAi');
      retryBtn.click();
      expect(retrySpy).toHaveBeenCalledWith(mockDetail.id);
      httpTesting
        .expectOne(API_ENDPOINTS.ROADMAPS.PROPOSALS_GENERATE_JOBS(mockDetail.id))
        .flush({
          job_id: 'job-prop-err-2',
          reservation_id: 'res-prop-err-2',
          roadmap_id: mockDetail.id,
          job_type: 'SCHEDULE_PROPOSAL_GEN',
          status: 'RESERVED',
          stream_url: '/api/v1/roadmaps/jobs/job-prop-err-2/stream',
          jobId: 'job-prop-err-2',
          reservationId: 'res-prop-err-2',
          streamUrl: '/api/v1/roadmaps/jobs/job-prop-err-2/stream',
        } satisfies SseJobTicketResponse);
      service.closeActiveStream();
    });

    it('hiển thị checkbox xác nhận Judge Review & Partial Schedule trên Bước 4 và đính kèm Idempotency-Key khi bấm Apply', () => {
      const proposal: ScheduleProposalResponse = {
        id: 'prop-confirm-1',
        roadmap_id: mockDetail.id,
        user_id: mockDetail.user_id,
        status: 'DRAFT',
        is_valid: true,
        has_soft_overflow: false,
        judge_status: 'NEEDS_REVIEW',
        is_partial_schedule: true,
        feasibility_verdict: 'PARTIAL_OVER_CAPACITY',
        schedule_completeness_status: 'PARTIAL',
        scheduled_tasks_count: 1,
        unscheduled_tasks_count: 1,
        unscheduled_tasks: [
          {
            task_id: 't-backlog-1',
            title: 'Nhiệm vụ đưa vào Backlog',
            task_type: 'PRACTICE',
            estimated_minutes: 60,
            unscheduled_reason: 'OVER_CAPACITY',
          },
        ],
        tasks: [
          {
            task_id: 'task-1',
            milestone_id: 'ms-1',
            title: 'Nhiệm vụ chính',
            estimated_minutes: 60,
            scheduled_date: '2026-11-02',
            scheduled_start: '19:30',
            scheduled_end: '20:30',
            task_type: 'PRACTICE',
          },
        ],
        dependencies: [],
        violations: [],
        soft_overflow_warnings: [],
        advisory_warnings: ['Cần xem lại mật độ học cuối tuần.'],
        diff_summary: {},
        proposal_data: {},
        applied_at: null,
        created_at: '2026-10-30T08:00:00Z',
        updated_at: '2026-10-30T08:00:00Z',
      };

      service.milestones.set([{ ...mockDetail.milestones![0], status: 'APPROVED' }]);
      service.currentProposal.set(proposal);
      service.editableTasks.set([
        {
          task_id: 'task-1',
          milestone_id: 'ms-1',
          milestone_sequence_order: 1,
          title: 'Nhiệm vụ chính',
          task_type: 'PRACTICE',
          estimated_minutes: 60,
          scheduled_date: '2026-11-02',
          scheduled_start: '19:30',
          scheduled_end: '20:30',
          learning_resources: [],
          prerequisite_ids: [],
        },
      ]);
      service.setActiveStep(4);
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const applyBtn = compiled.querySelector('[data-testid="apply-proposal-btn"]') as HTMLButtonElement;
      expect(applyBtn.disabled).toBe(true);

      const judgeCheckbox = compiled.querySelector(
        '[data-testid="confirm-warnings-checkbox"]'
      ) as HTMLInputElement;
      const partialCheckbox = compiled.querySelector(
        '[data-testid="confirm-partial-schedule-checkbox"]'
      ) as HTMLInputElement;
      expect(judgeCheckbox).toBeTruthy();
      expect(partialCheckbox).toBeTruthy();

      judgeCheckbox.checked = true;
      judgeCheckbox.dispatchEvent(new Event('change'));
      fixture.detectChanges();
      expect(applyBtn.disabled).toBe(true);

      partialCheckbox.checked = true;
      partialCheckbox.dispatchEvent(new Event('change'));
      fixture.detectChanges();
      expect(applyBtn.disabled).toBe(false);

      applyBtn.click();

      const applyReq = httpTesting.expectOne(
        API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(mockDetail.id, proposal.id)
      );
      expect(applyReq.request.headers.get('Idempotency-Key')).toBeTruthy();
      expect(applyReq.request.body).toEqual({
        confirm_soft_overflow: false,
        confirm_warnings: true,
        confirm_partial_schedule: true,
      });
      applyReq.flush({
        roadmap_id: mockDetail.id,
        roadmap_status: 'ACTIVE',
        official_schedule_id: 'sched-1',
        proposal_id: proposal.id,
        proposal_status: 'APPLIED',
        total_sessions: 1,
        total_planned_minutes: 60,
        preserved_completed_tasks_count: 0,
        replaced_tasks_count: 0,
        inserted_tasks_count: 1,
        affected_tasks_count: 1,
        total_shifted_minutes: 60,
        trigger_type: 'INITIAL_APPLY',
        calendar_sync_status: 'NOT_CONNECTED',
        backlog_unscheduled_tasks_count: 1,
        official_schedule: {
          id: 'sched-1',
          roadmap_id: mockDetail.id,
          total_sessions: 1,
          total_planned_minutes: 60,
          buffer_minutes_per_week: 60,
          recovery_window_days: 7,
          daily_workload_cap_minutes: 180,
          stability_weight: 0.8,
          activated_at: '2026-10-30T10:00:00Z',
          created_at: '2026-10-30T10:00:00Z',
          updated_at: '2026-10-30T10:00:00Z',
        },
      });
      httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockDetail.id)).flush(mockDetail);
      httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE).flush([mockDetail]);
    });

    it('hiển thị nhãn Gửi câu trả lời ở Vòng 1 và banner/nút Vòng 2 khi status là WAITING_FOLLOW_UP (BUG-12)', () => {
      service.setActiveStep(1);
      service.clarificationRound.set(1);
      service.clarificationStatus.set('WAITING_ANSWER');
      service.clarificationQuestions.set([
        {
          question_id: 'q-r1',
          id: 'q-r1',
          text: 'Mục tiêu chính của bạn?',
          question: 'Mục tiêu chính của bạn?',
          placeholder: '',
          question_type: 'text',
          options: [],
          question_purpose: '',
          expected_answer_format: 'text',
          diagnostic_dimension: 'GOAL',
        },
      ]);
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const submitBtn = compiled.querySelector('[data-testid="submit-clarification-btn"]');
      expect(submitBtn?.textContent).toContain('Gửi câu trả lời');
      expect(compiled.querySelector('[data-testid="clarification-round-2-banner"]')).toBeNull();

      service.clarificationRound.set(2);
      service.clarificationStatus.set('WAITING_FOLLOW_UP');
      fixture.detectChanges();

      expect(compiled.querySelector('[data-testid="clarification-round-2-badge"]')?.textContent).toContain('Vòng 2');
      expect(compiled.querySelector('[data-testid="clarification-round-2-banner"]')?.textContent).toContain('Vòng 2');
      expect(submitBtn?.textContent).toContain('Xác nhận & Hoàn tất chẩn đoán');
    });

    it('áp dụng đầy đủ cấu trúc chống tràn ngang 375px cho hero, portfolio-select và SSE pipeline steps (BUG-10)', () => {
      service.sseProgress.set({
        stage: 'STREAMING',
        progress: 45,
        message: 'Đang sinh lộ trình...',
        retryCount: 0,
        isStreaming: true,
      });
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('.roadmap-workspace')).toBeTruthy();
      expect(compiled.querySelector('.header-content')).toBeTruthy();
      expect(compiled.querySelector('.header-toolbar')).toBeTruthy();
      expect(compiled.querySelector('.portfolio-select')).toBeTruthy();

      const pipeline = compiled.querySelector('.sse-pipeline-steps');
      expect(pipeline).toBeTruthy();
      const dividers = pipeline?.querySelectorAll('.hidden.sm\\:block');
      expect(dividers?.length).toBe(3);
    });
  });
});
