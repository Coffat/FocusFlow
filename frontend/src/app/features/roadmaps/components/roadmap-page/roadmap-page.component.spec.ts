import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { RoadmapPageComponent } from './roadmap-page.component';
import { RoadmapService } from '../../services/roadmap.service';
import { API_ENDPOINTS } from '../../../../core/constants/api-endpoints';
import { RoadmapDetailResponse, ScheduleProposalResponse } from '../../models/roadmap.model';
import { createDefaultSchedule } from '../../../../core/services/availability.service';

describe('RoadmapPageComponent (WBS 6.3 3-Step AI Planning & Approval Workspace)', () => {
  let component: RoadmapPageComponent;
  let fixture: ComponentFixture<RoadmapPageComponent>;
  let service: RoadmapService;
  let httpTesting: HttpTestingController;

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
    await TestBed.configureTestingModule({
      imports: [RoadmapPageComponent],
      providers: [
        RoadmapService,
        provideRouter([{ path: 'availability', component: RoadmapPageComponent }]),
        provideHttpClient(),
        provideHttpClientTesting(),
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
          options: ['Chưa rõ', 'Cơ bản', 'Chuyên sâu'],
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
        options: ['Chưa từng', 'Đã biết khái niệm', 'Đã triển khai thực tế'],
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
        options: ['A', 'B'],
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

    it('hiển thị link tùy chỉnh dẫn sang /availability và đóng modal khi click', () => {
      component.toggleCreateForm();
      fixture.detectChanges();

      const compiled = fixture.nativeElement as HTMLElement;
      const customLink = compiled.querySelector(
        '[data-testid="onboard-custom-config-link"]'
      ) as HTMLAnchorElement;
      expect(customLink).toBeTruthy();
      expect(customLink.getAttribute('routerLink') || customLink.getAttribute('href')).toContain('/availability');

      customLink.click();
      fixture.detectChanges();
      expect(component.showOnboardingModal()).toBe(false);
    });
  });
});
