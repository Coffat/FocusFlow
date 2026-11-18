import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Subject } from 'rxjs';
import { mapRawTasksToProposedItems, RoadmapService } from './services/roadmap.service';
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
  it('khởi tạo nhiệm vụ mới không kèm học liệu giả', () => {
    service.addEditableTask({ title: 'Học kiến trúc' });
    expect(service.editableTasks()[0].learning_resources).toEqual([]);
    expect(service.proposalDirty()).toBe(true);
  });

  it('không tạo nguồn học liệu giả khi phản hồi AI thiếu URL', () => {
    const tasks = mapRawTasksToProposedItems([{
      task_id: 'task-1',
      title: 'Học kiến trúc',
      estimated_minutes: 60,
      learning_resources: [{ title: 'Nguồn không hợp lệ' }],
    }]);
    expect(tasks[0].learning_resources).toEqual([]);
    expect(tasks[0].scheduled_date).toBeNull();
  });

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
          options: [
            { id: 'none', label: 'Chưa từng' },
            { id: 'basic', label: 'Đã học cơ bản' },
            { id: 'advanced', label: 'Thành thạo' },
          ],
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
    expect(service.activeStep()).toBe(1);
    expect(service.clarificationStatus()).toBe('ERROR');
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
    expect(postReq.request.body.generation_strategy).toBe('FULL_SCOPE');

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
        estimated_effort_minutes: 60,
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
        estimated_effort_minutes: 60,
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
        estimated_effort_minutes: 60,
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

  it('hiển thị lỗi timeout thực từ server thay vì báo mất kết nối SSE', () => {
    const stream$ = new Subject<AiStreamChunkEvent<unknown>>();
    vi.spyOn(aiSseService, 'observeJobStream').mockReturnValue(stream$.asObservable());

    service.generateMilestonesWithAi(mockRoadmap.id);
    httpTesting
      .expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS(mockRoadmap.id))
      .flush({
        job_id: 'job-timeout-1',
        reservation_id: 'reservation-timeout-1',
        roadmap_id: mockRoadmap.id,
        job_type: 'MILESTONE_GEN',
        status: 'RESERVED',
        stream_url: '/api/v1/roadmaps/jobs/job-timeout-1/stream',
        jobId: 'job-timeout-1',
        reservationId: 'reservation-timeout-1',
        streamUrl: '/api/v1/roadmaps/jobs/job-timeout-1/stream',
      } satisfies SseJobTicketResponse);

    stream$.next({
      eventType: 'failed',
      stage: 'FAILED',
      progress: 100,
      code: 'AI_GATEWAY_TIMEOUT',
      message: 'AI mất quá nhiều thời gian phản hồi. Vui lòng thử lại.',
    });
    stream$.complete();

    expect(service.errorMessage()).toBe(
      'AI mất quá nhiều thời gian phản hồi. Vui lòng thử lại.'
    );
    expect(service.sseProgress().isStreaming).toBe(false);
    expect(service.sseProgress().stage).toBe('FAILED');
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
      judge_status: 'PASSED',
      is_partial_schedule: false,
      feasibility_verdict: 'VERIFIED_FEASIBLE',
      schedule_completeness_status: 'FULL',
      scheduled_tasks_count: 1,
      unscheduled_tasks_count: 0,
      tasks: [
        {
          task_id: 't-1',
          milestone_id: 'ms-1',
          title: 'Xây dựng Validation Gate',
          task_type: 'PRACTICE',
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
          title: 'Thực hành Spatio-Temporal Engine',
          task_type: 'PRACTICE',
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
          estimated_effort_minutes: 60,
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
    expect(applyReq.request.body).toEqual({
      confirm_soft_overflow: true,
      confirm_warnings: false,
      confirm_partial_schedule: false,
    });

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
      calendar_sync_status: 'NOT_CONNECTED',
      backlog_unscheduled_tasks_count: 0,
      official_schedule: {
        id: 'sched-001',
        roadmap_id: mockRoadmap.id,
        total_sessions: 1,
        total_planned_minutes: 90,
        buffer_minutes_per_week: 60,
        recovery_window_days: 7,
        daily_workload_cap_minutes: 180,
        stability_weight: 0.8,
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
      judge_status: 'PASSED',
      is_partial_schedule: false,
      feasibility_verdict: 'VERIFIED_FEASIBLE',
      schedule_completeness_status: 'FULL',
      scheduled_tasks_count: 1,
      unscheduled_tasks_count: 0,
      tasks: [
        {
          task_id: 'task-manual-1',
          milestone_id: 'ms-1',
          title: 'Tự đọc chương 1',
          task_type: 'PRACTICE',
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

  it('xử lý 409 SCOPE_APPROVAL_REQUIRED -> xác nhận FIT_CAPACITY đúng phiên bản -> 200 OK và areMilestonesApproved() === true dù cột mốc hoãn vẫn PENDING', () => {
    const msList = [
      {
        id: 'ms-1',
        roadmap_id: mockRoadmap.id,
        sequence_order: 1,
        title: 'Chặng 1: Nền tảng cốt lõi',
        description: 'Trong phạm vi',
        estimated_effort_minutes: 180,
        status: 'PENDING',
        created_at: '2026-10-30T08:00:00Z',
        updated_at: '2026-10-30T08:00:00Z',
      },
      {
        id: 'ms-2',
        roadmap_id: mockRoadmap.id,
        sequence_order: 2,
        title: 'Chặng 2: Mở rộng nâng cao',
        description: 'Hoãn lại',
        estimated_effort_minutes: 240,
        status: 'PENDING',
        created_at: '2026-10-30T08:00:00Z',
        updated_at: '2026-10-30T08:00:00Z',
      },
    ];
    service.selectedRoadmapDetail.set({
      ...mockRoadmap,
      milestones: msList,
      official_schedule: null,
      scheduled_tasks: [],
      current_draft_proposal: null,
    });
    service.milestones.set(msList);
    service.activeStep.set(2);

    const conflictPrelim = {
      status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
      scope_proposal_version: 1,
      scope_proposal_hash: 'hash-v1',
      requires_learner_approval: true,
      scope_approval_status: 'PENDING_LEARNER_APPROVAL',
      hard_packable_capacity_minutes: 240,
      soft_target_capacity_minutes: 204,
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
          title: 'Chặng 2: Mở rộng nâng cao',
          estimated_effort_minutes: 240,
        },
      ],
      feasibility_reasons: [],
    };

    service.approveMilestones(mockRoadmap.id);
    const firstReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockRoadmap.id));
    expect(firstReq.request.body).toEqual({
      confirmed_scope_proposal_version: null,
      accept_fit_capacity: false,
    });
    firstReq.flush(
      {
        code: 'SCOPE_APPROVAL_REQUIRED',
        message: 'Cần xác nhận phạm vi FIT_CAPACITY phiên bản v1.',
        detail: 'Cần xác nhận phạm vi FIT_CAPACITY phiên bản v1.',
        scope_proposal_version: 1,
        scope_proposal_hash: 'hash-v1',
        preliminary_feasibility: conflictPrelim,
      },
      { status: 409, statusText: 'Conflict' }
    );

    expect(service.activeStep()).toBe(2);
    expect(service.requiresScopeApproval()).toBe(true);
    expect(service.scopeProposalVersion()).toBe(1);
    expect(service.keptScope().length).toBe(1);
    expect(service.deferredScope().length).toBe(1);
    expect(service.areMilestonesApproved()).toBe(false);
    expect(service.scopeApprovalConflict()?.code).toBe('SCOPE_APPROVAL_REQUIRED');

    // Confirm FIT_CAPACITY v1
    service.approveMilestones(mockRoadmap.id, undefined, {
      confirmedScopeProposalVersion: 1,
      acceptFitCapacity: true,
    });
    const confirmReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockRoadmap.id));
    expect(confirmReq.request.body).toEqual({
      confirmed_scope_proposal_version: 1,
      accept_fit_capacity: true,
    });
    confirmReq.flush({
      roadmap_id: mockRoadmap.id,
      milestones: [
        { ...msList[0], status: 'APPROVED' },
        { ...msList[1], status: 'PENDING' },
      ],
      // Omit scope_approval_status to also verify local fallback update
      preliminary_feasibility: {
        ...conflictPrelim,
      },
    } satisfies MilestoneListResponse);

    expect(service.scopeApprovalConflict()).toBeNull();
    expect(service.isFitCapacityApproved()).toBe(true);
    expect(service.requiresScopeApproval()).toBe(false);
    expect(service.areMilestonesApproved()).toBe(true);
    expect(service.activeStep()).toBe(3);
  });

  it('mở lại lộ trình đã phê duyệt FIT_CAPACITY sẽ điều hướng thẳng sang Bước 3 và chặn double-submit khi đang phê duyệt', () => {
    const detail: RoadmapDetailResponse = {
      ...mockRoadmap,
      milestones: [
        {
          id: 'ms-1',
          roadmap_id: mockRoadmap.id,
          sequence_order: 1,
          title: 'Chặng 1',
          description: null,
          estimated_effort_minutes: 180,
          status: 'APPROVED',
          created_at: '2026-10-30T08:00:00Z',
          updated_at: '2026-10-30T08:00:00Z',
        },
        {
          id: 'ms-2',
          roadmap_id: mockRoadmap.id,
          sequence_order: 2,
          title: 'Chặng 2 (hoãn)',
          description: null,
          estimated_effort_minutes: 240,
          status: 'PENDING',
          created_at: '2026-10-30T08:00:00Z',
          updated_at: '2026-10-30T08:00:00Z',
        },
      ],
      official_schedule: null,
      scheduled_tasks: [],
      current_draft_proposal: null,
      preliminary_feasibility: {
        status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
        scope_proposal_version: 2,
        requires_learner_approval: true,
        scope_approval_status: 'APPROVED_BY_LEARNER',
        approved_scope_version: 2,
        kept_scope: [{ sequence_order: 1, milestone_id: 'ms-1', title: 'Chặng 1', estimated_effort_minutes: 180 }],
        deferred_scope: [{ sequence_order: 2, milestone_id: 'ms-2', title: 'Chặng 2 (hoãn)', estimated_effort_minutes: 240 }],
        feasibility_reasons: [],
      },
    };

    service.loadRoadmapDetail(mockRoadmap.id);
    httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockRoadmap.id)).flush(detail);

    expect(service.isFitCapacityApproved()).toBe(true);
    expect(service.areMilestonesApproved()).toBe(true);
    expect(service.activeStep()).toBe(3);

    // Double-submit guard
    service.approveMilestones(mockRoadmap.id);
    service.approveMilestones(mockRoadmap.id);
    const reqs = httpTesting.match(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockRoadmap.id));
    expect(reqs.length).toBe(1);
    reqs[0].flush(
      {
        code: 'SCOPE_APPROVAL_REQUIRED',
        message: 'Phiên bản phạm vi đã thay đổi sang v3.',
        detail: 'Phiên bản phạm vi đã thay đổi sang v3.',
        scope_proposal_version: 3,
        preliminary_feasibility: {
          status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
          scope_proposal_version: 3,
          requires_learner_approval: true,
          scope_approval_status: 'PENDING_LEARNER_APPROVAL',
          kept_scope: [],
          deferred_scope: [],
          feasibility_reasons: [],
        },
      },
      { status: 409, statusText: 'Conflict' }
    );

    expect(service.scopeProposalVersion()).toBe(3);
    expect(service.isApprovingMilestones()).toBe(false);
    expect(service.requiresScopeApproval()).toBe(true);
  });

  it('xử lý 409 PRELIMINARY_UNSCHEDULABLE khi sinh proposal bằng AI', () => {
    service.generateScheduleProposalWithAi(mockRoadmap.id);
    const req = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSALS_GENERATE_JOBS(mockRoadmap.id)
    );
    req.flush(
      {
        code: 'PRELIMINARY_UNSCHEDULABLE',
        message: 'Quỹ giờ rảnh không đủ cho cột mốc nền tảng đầu tiên.',
        detail: 'Quỹ giờ rảnh không đủ cho cột mốc nền tảng đầu tiên.',
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
              message: 'Quỹ thời gian khả dụng (60 phút) không đủ cho cột mốc đầu tiên (tối thiểu 180 phút).',
            },
          ],
          adjustment_options: {
            is_approximate: true,
            estimated_earliest_target_date_range: { min_date: '2026-12-10', max_date: '2026-12-20' },
            recommended_additional_weekly_minutes: 120,
          },
        },
      },
      { status: 409, statusText: 'Conflict' }
    );

    expect(service.isPreliminaryUnschedulable()).toBe(true);
    expect(service.areMilestonesApproved()).toBe(false);
    expect(service.scopeApprovalConflict()?.code).toBe('PRELIMINARY_UNSCHEDULABLE');
    expect(service.sseProgress().stage).toBe('FAILED');
  });

  it('không nuốt thông báo lỗi khi SSE failed gửi error rỗng "" và ghi nhận lastErrorCode + lastFailedStage để thử lại', () => {
    const stream$ = new Subject<AiStreamChunkEvent<unknown>>();
    vi.spyOn(aiSseService, 'observeJobStream').mockReturnValue(stream$.asObservable());

    service.generateMilestonesWithAi(mockRoadmap.id);
    httpTesting
      .expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS(mockRoadmap.id))
      .flush({
        job_id: 'job-empty-err-1',
        reservation_id: 'res-empty-err-1',
        roadmap_id: mockRoadmap.id,
        job_type: 'MILESTONE_GEN',
        status: 'RESERVED',
        stream_url: '/api/v1/roadmaps/jobs/job-empty-err-1/stream',
        jobId: 'job-empty-err-1',
        reservationId: 'res-empty-err-1',
        streamUrl: '/api/v1/roadmaps/jobs/job-empty-err-1/stream',
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

    expect(service.errorMessage()).toBe(
      'Tiến trình sinh lộ trình bằng AI thất bại. Vui lòng thử lại hoặc lập kế hoạch thủ công.'
    );
    expect(service.sseProgress().isStreaming).toBe(false);
    expect(service.sseProgress().stage).toBe('FAILED');
    expect(service.sseProgress().message).toBe('Tiến trình AI gặp lỗi.');
    expect(service.lastErrorCode()).toBe('AI_EXECUTION_ERROR');
    expect(service.lastFailedStage()).toBe('MILESTONES');

    const retrySpy = vi.spyOn(service, 'generateMilestonesWithAi');
    service.retryFailedAiGeneration();
    expect(retrySpy).toHaveBeenCalledWith(mockRoadmap.id);
    httpTesting
      .expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS(mockRoadmap.id))
      .flush({
        job_id: 'job-retry-2',
        reservation_id: 'res-retry-2',
        roadmap_id: mockRoadmap.id,
        job_type: 'MILESTONE_GEN',
        status: 'RESERVED',
        stream_url: '/api/v1/roadmaps/jobs/job-retry-2/stream',
        jobId: 'job-retry-2',
        reservationId: 'res-retry-2',
        streamUrl: '/api/v1/roadmaps/jobs/job-retry-2/stream',
      } satisfies SseJobTicketResponse);
    service.closeActiveStream();
  });

  it('gửi Idempotency-Key khi applyProposal, giữ nguyên key khi thử lại cùng đề xuất và xử lý đủ các mã xung đột 409', () => {
    const baseProposal: ScheduleProposalResponse = {
      id: 'prop-409-1',
      roadmap_id: mockRoadmap.id,
      user_id: mockRoadmap.user_id,
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: false,
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
          title: 'Học kiểm thử',
          task_type: 'PRACTICE',
          estimated_minutes: 60,
          scheduled_date: '2026-11-02',
          scheduled_start: '19:30',
          scheduled_end: '20:30',
        },
      ],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [],
      advisory_warnings: [],
      diff_summary: {},
      proposal_data: {},
      applied_at: null,
      created_at: '2026-10-30T08:00:00Z',
      updated_at: '2026-10-30T08:00:00Z',
    };

    service.currentProposal.set(baseProposal);
    service.editableTasks.set([
      {
        task_id: 'task-1',
        milestone_id: 'ms-1',
        milestone_sequence_order: 1,
        title: 'Học kiểm thử',
        task_type: 'PRACTICE',
        estimated_minutes: 60,
        scheduled_date: '2026-11-02',
        scheduled_start: '19:30',
        scheduled_end: '20:30',
        learning_resources: [],
        prerequisite_ids: [],
      },
    ]);

    // 1. Network/500 failure then retry reuses exact same Idempotency-Key
    service.applyProposal(mockRoadmap.id, baseProposal.id);
    const attempt1 = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(mockRoadmap.id, baseProposal.id)
    );
    const key1 = attempt1.request.headers.get('Idempotency-Key');
    expect(key1).toBeTruthy();
    attempt1.flush({ message: '' }, { status: 503, statusText: 'Service Unavailable' });
    expect(service.errorMessage()).toBe('Không thể áp dụng đề xuất lịch học vào Lịch học Chính thức.');

    service.applyProposal(mockRoadmap.id, baseProposal.id);
    const attempt2 = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(mockRoadmap.id, baseProposal.id)
    );
    expect(attempt2.request.headers.get('Idempotency-Key')).toBe(key1);
    attempt2.flush(
      {
        code: 'JUDGE_REVIEW_CONFIRMATION_REQUIRED',
        message: 'Cần xác nhận lưu ý sư phạm trước khi áp dụng.',
        judge_status: 'NEEDS_REVIEW',
        advisory_warnings: ['Mật độ buổi cuối tuần cao.'],
      },
      { status: 409, statusText: 'Conflict' }
    );

    expect(service.lastErrorCode()).toBe('JUDGE_REVIEW_CONFIRMATION_REQUIRED');
    expect(service.needsJudgeConfirmation()).toBe(true);
    expect(service.canApplyProposal()).toBe(false);
    service.setConfirmWarnings(true);
    expect(service.canApplyProposal()).toBe(true);

    // 2. 409 PARTIAL_SCHEDULE_CONFIRMATION_REQUIRED
    service.applyProposal(mockRoadmap.id, baseProposal.id);
    const attempt3 = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(mockRoadmap.id, baseProposal.id)
    );
    attempt3.flush(
      {
        code: 'PARTIAL_SCHEDULE_CONFIRMATION_REQUIRED',
        message: 'Cần xác nhận giữ phần chưa xếp lịch trong Backlog.',
      },
      { status: 409, statusText: 'Conflict' }
    );
    expect(service.lastErrorCode()).toBe('PARTIAL_SCHEDULE_CONFIRMATION_REQUIRED');
    expect(service.isPartialSchedule()).toBe(true);
    expect(service.canApplyProposal()).toBe(false);
    service.setConfirmPartialSchedule(true);
    expect(service.canApplyProposal()).toBe(true);

    // 3. 409 FRESH_CALENDAR_CONFLICT_DETECTED
    service.applyProposal(mockRoadmap.id, baseProposal.id);
    const attempt4 = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(mockRoadmap.id, baseProposal.id)
    );
    attempt4.flush(
      {
        code: 'FRESH_CALENDAR_CONFLICT_DETECTED',
        message: 'Phát hiện xung đột mới với Google Calendar.',
        conflicts: [{ task_id: 'task-1', conflict_source: 'GOOGLE_CALENDAR_BUSY' }],
      },
      { status: 409, statusText: 'Conflict' }
    );
    expect(service.lastErrorCode()).toBe('FRESH_CALENDAR_CONFLICT_DETECTED');
    expect(service.freshCalendarConflicts().length).toBe(1);

    // 4. 409 PROPOSAL_SUPERSEDED
    service.applyProposal(mockRoadmap.id, baseProposal.id);
    const attempt5 = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(mockRoadmap.id, baseProposal.id)
    );
    attempt5.flush(
      {
        code: 'PROPOSAL_SUPERSEDED',
        message: 'Bản nháp đã bị thay thế.',
      },
      { status: 409, statusText: 'Conflict' }
    );
    expect(service.lastErrorCode()).toBe('PROPOSAL_SUPERSEDED');
    expect(service.currentProposal()?.status).toBe('SUPERSEDED');
    expect(service.canApplyProposal()).toBe(false);
  });

  it('hiển thị thông báo Vòng 2 và giữ nguyên Bước 1 khi submitClarificationAnswers trả về WAITING_FOLLOW_UP', () => {
    service.setActiveStep(1);
    service.clarificationQuestions.set([
      {
        question_id: 'q1',
        id: 'q1',
        text: 'Mục tiêu ưu tiên của bạn là gì?',
        question: 'Mục tiêu ưu tiên của bạn là gì?',
        placeholder: '',
        question_type: 'text',
        options: [],
        question_purpose: 'Xác định trọng tâm',
        expected_answer_format: 'text',
        diagnostic_dimension: 'GOAL',
      },
    ]);

    service.submitClarificationAnswers(mockRoadmap.goal_id, [
      { question_id: 'q1', question_text: 'Mục tiêu ưu tiên của bạn là gì?', answer: 'Backend API' },
    ]);

    const ansReq = httpTesting.expectOne(
      API_ENDPOINTS.ROADMAPS.CLARIFY_ANSWERS(mockRoadmap.goal_id)
    );
    ansReq.flush({
      goal_id: mockRoadmap.goal_id,
      session_id: 'sess-round-2',
      round: 2,
      status: 'WAITING_FOLLOW_UP',
      clarification_context: 'Đã ghi nhận ưu tiên Backend API.',
      questions: [
        {
          question_id: 'q2',
          text: 'Bạn đã từng dùng PostgreSQL chưa?',
          question_type: 'single_choice',
          options: [{ id: 'yes', label: 'Rồi' }],
        },
      ],
      message: 'Follow-up needed',
    });

    expect(service.activeStep()).toBe(1);
    expect(service.clarificationRound()).toBe(2);
    expect(service.clarificationStatus()).toBe('WAITING_FOLLOW_UP');
    expect(service.successMessage()).toBe(
      'Đã ghi nhận vòng 1. Vui lòng trả lời câu hỏi làm rõ bổ sung (Vòng 2) bên dưới.'
    );
    expect(service.clarificationQuestions().length).toBe(1);
  });
});
