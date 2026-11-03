import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Subject } from 'rxjs';
import { RoadmapService } from './services/roadmap.service';
import { AiSseService, AiStreamChunkEvent } from '../../core/services/ai-sse.service';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints';
import {
  ApplyScheduleProposalResponse,
  MilestoneListResponse,
  RoadmapDetailResponse,
  RoadmapResponse,
  ScheduleProposalResponse,
  SseJobTicketResponse,
} from './models/roadmap.model';

describe('RoadmapService (WBS 6.3 AI Planning & Approval Store)', () => {
  let service: RoadmapService;
  let httpTesting: HttpTestingController;
  let aiSseService: AiSseService;

  const mockRoadmap: RoadmapResponse = {
    id: '018f0000-0000-7000-8000-000000000001',
    user_id: '018f0000-0000-7000-8000-000000000099',
    goal_id: '018f0000-0000-7000-8000-000000000010',
    title: 'Lộ trình FastAPI & Angular 21',
    description: 'Xây dựng hệ thống Modular Monolith',
    status: 'INITIALIZED',
    start_date: '2026-11-02',
    target_date: '2026-12-30',
    created_at: '2026-10-30T08:00:00Z',
    updated_at: '2026-10-30T08:00:00Z',
    goal: {
      id: '018f0000-0000-7000-8000-000000000010',
      user_id: '018f0000-0000-7000-8000-000000000099',
      title: 'Lộ trình FastAPI & Angular 21',
      raw_description: 'Xây dựng hệ thống Modular Monolith',
      target_date: '2026-12-30',
      status: 'ACTIVE',
      prior_knowledge_level: 'BEGINNER',
      clarification_context: null,
      created_at: '2026-10-30T08:00:00Z',
      updated_at: '2026-10-30T08:00:00Z',
    },
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        RoadmapService,
        AiSseService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(RoadmapService);
    httpTesting = TestBed.inject(HttpTestingController);
    aiSseService = TestBed.inject(AiSseService);
  });

  afterEach(() => {
    service.closeActiveStream();
    httpTesting.verify();
  });

  it('tạo mới Goal & Roadmap (UC-07) và kích hoạt phỏng vấn chẩn đoán AI (FR-GOAL-002)', () => {
    service.createRoadmap({
      title: 'Lộ trình FastAPI & Angular 21',
      description: 'Xây dựng hệ thống Modular Monolith',
      goal_title: 'Lộ trình FastAPI & Angular 21',
      goal_description: 'Xây dựng hệ thống Modular Monolith',
      prior_knowledge_level: 'BEGINNER',
      start_date: '2026-11-02',
      target_date: '2026-12-30',
    });

    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.body.prior_knowledge_level).toBe('BEGINNER');
    req.flush(mockRoadmap);

    const clarifyReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.CLARIFY_QUESTIONS(mockRoadmap.goal_id)
    );
    expect(clarifyReq.request.method).toBe('POST');
    clarifyReq.flush({
      questions: [
        {
          question_id: 'q1',
          text: 'Bạn đã từng học lập trình Python trước đây chưa?',
          question_type: 'single_choice',
          options: ['Chưa từng', 'Đã học cơ bản', 'Thành thạo'],
        },
      ],
    });

    expect(service.roadmaps().length).toBe(1);
    expect(service.selectedRoadmapDetail()?.id).toBe(mockRoadmap.id);
    expect(service.activeStep()).toBe(1);
    expect(service.clarificationQuestions().length).toBe(1);
    expect(service.successMessage()).toContain('Đã khởi tạo');
  });

  it('hỗ trợ trả lời phỏng vấn chẩn đoán hoặc bỏ qua (FR-GOAL-002)', () => {
    service.submitClarificationAnswers(mockRoadmap.goal_id, [
      { question_id: 'q1', question_text: 'Python?', answer: 'Đã học cơ bản' },
    ]);
    expect(service.isSubmittingAnswers()).toBe(true);

    const ansReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.CLARIFY_ANSWERS(mockRoadmap.goal_id)
    );
    expect(ansReq.request.method).toBe('POST');
    expect(ansReq.request.body.answers[0].answer).toBe('Đã học cơ bản');
    ansReq.flush({
      goal_id: mockRoadmap.goal_id,
      clarification_context: 'Học viên đã có nền tảng Python cơ bản.',
      message: 'Updated',
    });

    expect(service.isSubmittingAnswers()).toBe(false);
    expect(service.clarificationContext()).toBe('Học viên đã có nền tảng Python cơ bản.');
    expect(service.activeStep()).toBe(2);

    // Test skip clarification
    service.setActiveStep(1);
    service.skipClarification();
    expect(service.activeStep()).toBe(2);
  });

  it('sinh Cột mốc bằng AI qua 2-Stage SSE, theo dõi retry và phê duyệt Cột mốc (FR-PLAN-001)', () => {
    const stream$ = new Subject<AiStreamChunkEvent<unknown>>();
    vi.spyOn(aiSseService, 'observeJobStream').mockReturnValue(stream$.asObservable());

    service.selectedRoadmapDetail.set({
      ...mockRoadmap,
      milestones: [],
      official_schedule: null,
      scheduled_tasks: [],
      current_draft_proposal: null,
    });

    service.generateMilestonesWithAi(mockRoadmap.id);

    const postReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS(mockRoadmap.id)
    );
    expect(postReq.request.method).toBe('POST');
    expect(postReq.request.headers.has('Idempotency-Key')).toBe(true);

    const ticket: SseJobTicketResponse = {
      job_id: '018f0000-0000-7000-8000-000000000111',
      reservation_id: '018f0000-0000-7000-8000-000000000222',
      roadmap_id: mockRoadmap.id,
      job_type: 'MILESTONE_GEN',
      status: 'RESERVED',
      stream_url: '/api/v1/roadmaps/jobs/018f0000-0000-7000-8000-000000000111/stream',
      jobId: '018f0000-0000-7000-8000-000000000111',
      reservationId: '018f0000-0000-7000-8000-000000000222',
      streamUrl: '/api/v1/roadmaps/jobs/018f0000-0000-7000-8000-000000000111/stream',
    };
    postReq.flush(ticket);

    // Emit stage -> validation_retry -> completed
    stream$.next({
      eventType: 'stage',
      stage: 'STREAMING',
      progress: 35,
      deltaText: 'Đang phân rã cột mốc...',
    });
    expect(service.sseProgress().isStreaming).toBe(true);
    expect(service.sseProgress().progress).toBe(35);

    stream$.next({
      eventType: 'validation_retry',
      stage: 'VALIDATING_TIER_1_2_3',
      progress: 65,
      retry_attempt: 1,
      deltaText: 'Tự động điều chỉnh cấu trúc cột mốc #1',
    });
    expect(service.sseProgress().retryCount).toBe(1);

    const generatedMilestones = [
      {
        id: 'ms-1',
        roadmap_id: mockRoadmap.id,
        sequence_order: 1,
        title: 'Chặng 1: Domain Model',
        description: 'Thiết kế Aggregate',
        status: 'PENDING',
        created_at: '2026-10-30T08:00:00Z',
        updated_at: '2026-10-30T08:00:00Z',
      },
      {
        id: 'ms-2',
        roadmap_id: mockRoadmap.id,
        sequence_order: 2,
        title: 'Chặng 2: Use Cases & Ports',
        description: 'Xây dựng tầng Application',
        status: 'PENDING',
        created_at: '2026-10-30T08:00:00Z',
        updated_at: '2026-10-30T08:00:00Z',
      },
      {
        id: 'ms-3',
        roadmap_id: mockRoadmap.id,
        sequence_order: 3,
        title: 'Chặng 3: Presentation & UI',
        description: 'Kết nối OpenAPI & Angular 21',
        status: 'PENDING',
        created_at: '2026-10-30T08:00:00Z',
        updated_at: '2026-10-30T08:00:00Z',
      },
    ];

    stream$.next({
      eventType: 'completed',
      stage: 'COMPLETED',
      progress: 100,
      payload: {
        roadmap_id: mockRoadmap.id,
        milestones: generatedMilestones,
      },
    });
    stream$.complete();

    const detailReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockRoadmap.id));
    detailReq.flush({
      ...mockRoadmap,
      milestones: generatedMilestones,
      official_schedule: null,
      scheduled_tasks: [],
      current_draft_proposal: null,
    } satisfies RoadmapDetailResponse);

    expect(service.sseProgress().isStreaming).toBe(false);
    expect(service.milestones().length).toBe(3);
    expect(service.areMilestonesApproved()).toBe(false);

    // Reorder milestone and approve
    service.moveEditableMilestone(1, 'UP');
    expect(service.editableMilestones()[0].title).toBe('Chặng 2: Use Cases & Ports');
    expect(service.editableMilestones()[0].sequence_order).toBe(1);

    service.approveMilestones(mockRoadmap.id);
    const approveReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockRoadmap.id)
    );
    expect(approveReq.request.method).toBe('POST');

    const approvedList: MilestoneListResponse = {
      roadmap_id: mockRoadmap.id,
      milestones: generatedMilestones.map(m => ({ ...m, status: 'APPROVED' })),
    };
    approveReq.flush(approvedList);

    expect(service.areMilestonesApproved()).toBe(true);
    expect(service.activeStep()).toBe(3);
  });

  it('sinh Đề xuất Lịch học AI (UC-08) qua 2-Stage SSE và chỉnh sửa nhiệm vụ với updateProposal (UC-12)', () => {
    const stream$ = new Subject<AiStreamChunkEvent<unknown>>();
    vi.spyOn(aiSseService, 'observeJobStream').mockReturnValue(stream$.asObservable());

    service.generateScheduleProposalWithAi(mockRoadmap.id);

    const postReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSALS_GENERATE_JOBS(mockRoadmap.id)
    );
    expect(postReq.request.method).toBe('POST');
    expect(postReq.request.headers.has('Idempotency-Key')).toBe(true);

    postReq.flush({
      job_id: 'job-prop-1',
      reservation_id: 'res-prop-1',
      roadmap_id: mockRoadmap.id,
      job_type: 'SCHEDULE_PROPOSAL_GEN',
      status: 'RESERVED',
      stream_url: '/api/v1/roadmaps/jobs/job-prop-1/stream',
      jobId: 'job-prop-1',
      reservationId: 'res-prop-1',
      streamUrl: '/api/v1/roadmaps/jobs/job-prop-1/stream',
    } satisfies SseJobTicketResponse);

    const mockProposal: ScheduleProposalResponse = {
      id: 'prop-ai-1',
      roadmap_id: mockRoadmap.id,
      user_id: mockRoadmap.user_id,
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: false,
      tasks: [
        {
          task_id: 't-1',
          milestone_id: 'ms-1',
          title: 'Xây dựng Validation Gate',
          estimated_minutes: 60,
          scheduled_date: '2026-11-02',
          scheduled_start: '2026-11-02T19:30:00Z',
          scheduled_end: '2026-11-02T20:30:00Z',
        },
      ],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [],
      advisory_warnings: [],
      diff_summary: {
        preserved_completed_tasks_count: 1,
        replaced_tasks_count: 0,
        inserted_tasks_count: 1,
      },
      proposal_data: {},
      applied_at: null,
      created_at: '2026-10-30T08:00:00Z',
      updated_at: '2026-10-30T08:00:00Z',
    };

    stream$.next({
      eventType: 'completed',
      stage: 'COMPLETED',
      progress: 100,
      payload: { proposal_id: mockProposal.id },
    });
    stream$.complete();

    httpTesting
      .expectOne(API_ENDPOINTS.ROADMAPS.PROPOSALS_CURRENT(mockRoadmap.id))
      .flush(mockProposal);
    httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockRoadmap.id)).flush({
      ...mockRoadmap,
      milestones: [],
      official_schedule: null,
      scheduled_tasks: [],
      current_draft_proposal: mockProposal,
    });

    expect(service.currentProposal()?.id).toBe('prop-ai-1');
    expect(service.editableTasks().length).toBe(1);
    expect(service.editableTasks()[0].scheduled_start).toBe('19:30');

    // Edit task duration to 90 minutes and save via updateProposal
    service.updateEditableTask(0, { estimated_minutes: 90 });
    service.updateProposal(mockRoadmap.id, mockProposal.id);

    const putReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSAL_UPDATE(mockRoadmap.id, mockProposal.id)
    );
    expect(putReq.request.method).toBe('PUT');
    expect(putReq.request.body.tasks[0].estimated_minutes).toBe(90);

    putReq.flush({
      ...mockProposal,
      tasks: [
        {
          ...mockProposal.tasks![0],
          estimated_minutes: 90,
        },
      ],
    });

    expect(service.editableTasks()[0].estimated_minutes).toBe(90);
    expect(service.successMessage()).toContain('UC-12');
  });

  it('kiểm soát chặt chẽ cổng Soft Overflow (BUSR-04) trước khi cho phép Apply ScheduleProposal', () => {
    const proposalWithSoftOverflow: ScheduleProposalResponse = {
      id: 'prop-001',
      roadmap_id: mockRoadmap.id,
      user_id: mockRoadmap.user_id,
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: true,
      tasks: [
        {
          task_id: 'task-1',
          milestone_id: 'ms-1',
          title: 'Thực hành Spatio-Temporal Engine',
          estimated_minutes: 90,
          scheduled_date: '2026-11-02',
          scheduled_start: '20:15',
          scheduled_end: '21:45',
        },
      ],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [
        {
          task_index: 0,
          task_title: 'Thực hành Spatio-Temporal Engine',
          scheduled_date: '2026-11-02',
          overflow_minutes: 15,
          message: 'Nhiệm vụ cuối ngày vượt khung giờ 15 phút (≤ 30 phút cho phép).',
        },
      ],
      advisory_warnings: [],
      diff_summary: {
        preserved_completed_tasks_count: 2,
        replaced_tasks_count: 1,
        inserted_tasks_count: 1,
      },
      proposal_data: {},
      applied_at: null,
      created_at: '2026-10-30T08:00:00Z',
      updated_at: '2026-10-30T08:00:00Z',
    };

    service.selectedRoadmapDetail.set({
      ...mockRoadmap,
      milestones: [
        {
          id: 'ms-1',
          roadmap_id: mockRoadmap.id,
          sequence_order: 1,
          title: 'Chặng 1',
          description: null,
          status: 'APPROVED',
          created_at: '2026-10-30T08:00:00Z',
          updated_at: '2026-10-30T08:00:00Z',
        },
      ],
      official_schedule: null,
      scheduled_tasks: [],
      current_draft_proposal: proposalWithSoftOverflow,
    });

    service.loadCurrentProposal(mockRoadmap.id);
    const getPropReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSALS_CURRENT(mockRoadmap.id)
    );
    getPropReq.flush(proposalWithSoftOverflow);

    expect(service.hasSoftOverflow()).toBe(true);
    expect(service.confirmSoftOverflow()).toBe(false);
    // Gate must block Apply until checkbox is confirmed
    expect(service.canApplyProposal()).toBe(false);

    service.setConfirmSoftOverflow(true);
    expect(service.canApplyProposal()).toBe(true);

    // Apply proposal with confirm_soft_overflow = true
    service.applyProposal(mockRoadmap.id, proposalWithSoftOverflow.id);
    const applyReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(mockRoadmap.id, proposalWithSoftOverflow.id)
    );
    expect(applyReq.request.method).toBe('POST');
    expect(applyReq.request.body).toEqual({ confirm_soft_overflow: true });

    const applyResponse: ApplyScheduleProposalResponse = {
      roadmap_id: mockRoadmap.id,
      roadmap_status: 'ACTIVE',
      official_schedule_id: 'sched-001',
      proposal_id: proposalWithSoftOverflow.id,
      proposal_status: 'APPLIED',
      total_sessions: 1,
      total_planned_minutes: 90,
      preserved_completed_tasks_count: 2,
      replaced_tasks_count: 1,
      inserted_tasks_count: 1,
      affected_tasks_count: 1,
      total_shifted_minutes: 90,
      trigger_type: 'INITIAL_APPLY',
      official_schedule: {
        id: 'sched-001',
        roadmap_id: mockRoadmap.id,
        total_sessions: 1,
        total_planned_minutes: 90,
        activated_at: '2026-10-30T08:30:00Z',
        created_at: '2026-10-30T08:30:00Z',
        updated_at: '2026-10-30T08:30:00Z',
      },
    };
    applyReq.flush(applyResponse);

    httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockRoadmap.id)).flush({
      ...mockRoadmap,
      status: 'ACTIVE',
      milestones: [],
      official_schedule: applyResponse.official_schedule,
      scheduled_tasks: [],
      current_draft_proposal: null,
    });
    httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE).flush([
      { ...mockRoadmap, status: 'ACTIVE' },
    ]);

    expect(service.activeStep()).toBe(4);
    expect(service.lastApplyResult()?.roadmap_status).toBe('ACTIVE');
  });

  it('hỗ trợ Lập kế hoạch thủ công (UC-09) và Lưu trữ lộ trình (UC-10)', () => {
    service.selectedRoadmapDetail.set({
      ...mockRoadmap,
      milestones: [],
      official_schedule: null,
      scheduled_tasks: [],
      current_draft_proposal: null,
    });

    service.addEditableMilestone('Chặng thủ công 1', 'Tự học');
    service.enableManualPlanningMode();
    expect(service.manualPlanningMode()).toBe(true);
    expect(service.activeStep()).toBe(3);
    expect(service.editableTasks().length).toBe(1);

    service.updateEditableTask(0, {
      title: 'Tự đọc chương 1',
      estimated_minutes: 75,
    });

    service.saveManualPlan(mockRoadmap.id);

    const manualReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSALS_MANUAL(mockRoadmap.id)
    );
    expect(manualReq.request.method).toBe('POST');
    expect(manualReq.request.body.tasks[0].title).toBe('Tự đọc chương 1');
    expect(manualReq.request.body.tasks[0].estimated_minutes).toBe(75);

    const savedManualProposal: ScheduleProposalResponse = {
      id: 'prop-manual-1',
      roadmap_id: mockRoadmap.id,
      user_id: mockRoadmap.user_id,
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: false,
      tasks: [
        {
          task_id: 'task-manual-1',
          milestone_id: 'ms-1',
          title: 'Tự đọc chương 1',
          estimated_minutes: 75,
          scheduled_date: '2026-11-02',
          scheduled_start: '19:30',
          scheduled_end: '20:45',
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
      applied_at: null,
      created_at: '2026-10-30T09:00:00Z',
      updated_at: '2026-10-30T09:00:00Z',
    };
    manualReq.flush(savedManualProposal);

    httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockRoadmap.id)).flush({
      ...mockRoadmap,
      milestones: [],
      official_schedule: null,
      scheduled_tasks: [],
      current_draft_proposal: savedManualProposal,
    });

    expect(service.currentProposal()?.id).toBe('prop-manual-1');
    expect(service.successMessage()).toContain('UC-09');

    // Archive roadmap (UC-10)
    service.archiveRoadmap(mockRoadmap.id);
    const archiveReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.ARCHIVE(mockRoadmap.id));
    expect(archiveReq.request.method).toBe('POST');
    archiveReq.flush({ ...mockRoadmap, status: 'ARCHIVED' });

    expect(service.selectedRoadmapDetail()?.status).toBe('ARCHIVED');
    expect(service.isReadOnlyRoadmap()).toBe(true);
  });
});
