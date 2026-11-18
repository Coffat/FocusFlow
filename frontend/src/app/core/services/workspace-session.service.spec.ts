import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import {
  StudySessionResponse,
  TaskResponse,
  TodayFocusResponse,
  WorkspaceSessionService,
  evaluateTakeawayCheck,
} from './workspace-session.service';

const makeTask = (overrides: Partial<TaskResponse> = {}): TaskResponse => ({
  id: 'task-01',
  roadmap_id: 'rm-01',
  milestone_id: 'ms-01',
  title: 'Học kiến trúc Hexagonal',
  description: 'Tách domain và infrastructure',
  estimated_minutes: 45,
  learning_resources: [],
  scheduled_date: '2026-11-18',
  status: 'TODO',
  reschedule_count: 0,
  is_overdue: false,
  is_blocked: false,
  is_stalled: false,
  predecessor_ids: [],
  created_at: '2026-11-18T00:00:00Z',
  updated_at: '2026-11-18T00:00:00Z',
  ...overrides,
});

const makeSession = (overrides: Partial<StudySessionResponse> = {}): StudySessionResponse => ({
  id: 'sess-01',
  user_id: 'usr-01',
  roadmap_id: 'rm-01',
  started_at: new Date().toISOString(),
  planned_minutes: 25,
  actual_minutes: 0,
  status: 'IN_PROGRESS',
  last_heartbeat_at: new Date().toISOString(),
  session_mode: 'STANDARD',
  pending_takeaway: false,
  scratchpad_content: '',
  session_tasks: [
    {
      id: 'st-01',
      session_id: 'sess-01',
      task_id: 'task-01',
      allocated_minutes: 25,
      actual_minutes: 0,
      status_after_session: 'IN_PROGRESS',
    },
  ],
  notes: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
});

describe('WorkspaceSessionService', () => {
  let service: WorkspaceSessionService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [WorkspaceSessionService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(WorkspaceSessionService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    service.pauseSession();
    httpMock.verify();
  });

  it('khởi tạo giá trị mặc định cho Signal và Computed', () => {
    expect(service.sessionId()).toBeNull();
    expect(service.taskId()).toBeNull();
    expect(service.durationMinutes()).toBe(25);
    expect(service.remainingSeconds()).toBe(1500);
    expect(service.isRunning()).toBe(false);
    expect(service.scratchpadNote()).toBe('');
    expect(service.formattedTime()).toBe('25:00');
    expect(service.progressPercentage()).toBe(0);
  });

  it('setScratchpadNote() cập nhật signal scratchpadNote', () => {
    service.setScratchpadNote('Ghi chú ôn tập kiến trúc Hexagonal');
    expect(service.scratchpadNote()).toBe('Ghi chú ôn tập kiến trúc Hexagonal');
  });

  it('loadWorkspace() gọi /api/v1/sessions/today-focus và /api/v1/sessions/active với withCredentials', () => {
    const task = makeTask();
    const pendingSession = makeSession({
      id: 'sess-debt',
      status: 'AUTO_CLOSED',
      pending_takeaway: true,
    });
    const todayFocus: TodayFocusResponse = {
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: pendingSession,
      focus_task: task,
      today_queue: [task],
      overdue_tasks_count: 1,
    };

    service.loadWorkspace().subscribe((res) => {
      expect(res?.local_date).toBe('2026-11-18');
    });

    const tfReq = httpMock.expectOne('/api/v1/sessions/today-focus');
    expect(tfReq.request.method).toBe('GET');
    expect(tfReq.request.withCredentials).toBe(true);
    tfReq.flush(todayFocus);

    const activeReq = httpMock.expectOne('/api/v1/sessions/active');
    expect(activeReq.request.method).toBe('GET');
    expect(activeReq.request.withCredentials).toBe(true);
    activeReq.flush(null);

    expect(service.todayQueue()).toHaveLength(1);
    expect(service.pendingTakeawaySession()?.id).toBe('sess-debt');
  });

  it('beginSession() gửi POST /api/v1/sessions/start và kích hoạt đồng hồ', () => {
    const created = makeSession({ id: 'sess-live', planned_minutes: 30 });

    service
      .beginSession({ task_ids: ['task-01'], session_mode: 'STANDARD', planned_minutes: 30 })
      .subscribe((res) => {
        expect(res.id).toBe('sess-live');
      });

    const req = httpMock.expectOne('/api/v1/sessions/start');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.body).toEqual({
      task_ids: ['task-01'],
      session_mode: 'STANDARD',
      planned_minutes: 30,
    });
    req.flush(created);

    expect(service.sessionId()).toBe('sess-live');
    expect(service.taskId()).toBe('task-01');
    expect(service.durationMinutes()).toBe(30);
    expect(service.isRunning()).toBe(true);
  });

  it('pauseSession() và resumeSession() chuyển đổi trạng thái isRunning', () => {
    service.hydrateActiveSession(makeSession(), true);
    expect(service.isRunning()).toBe(true);

    service.pauseSession();
    expect(service.isRunning()).toBe(false);

    service.resumeSession();
    expect(service.isRunning()).toBe(true);
  });

  it('sendHeartbeat() gửi actual_minutes và scratchpad_content tới /api/v1/sessions/{id}/heartbeat', () => {
    service.hydrateActiveSession(makeSession({ id: 'sess-hb' }), true);
    service.setScratchpadNote('Đang học Port & Adapter');

    service.sendHeartbeat().subscribe();

    const req = httpMock.expectOne('/api/v1/sessions/sess-hb/heartbeat');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.body.scratchpad_content).toBe('Đang học Port & Adapter');
    req.flush(makeSession({ id: 'sess-hb', scratchpad_content: 'Đang học Port & Adapter' }));

    expect(service.heartbeatStatus()).toBe('synced');
  });

  it('finalizeSession() gửi POST /api/v1/sessions/{id}/finalize và xóa activeSession', () => {
    service.hydrateActiveSession(makeSession({ id: 'sess-fin' }), true);

    service
      .finalizeSession({
        early_stop: false,
        completed_task_ids: ['task-01'],
        takeaway: 'Đã hiểu rõ cách thiết kế Port và Adapter trong kiến trúc Hexagonal.',
        self_confidence: 4,
        checkin_time_sufficiency: 'JUST_RIGHT',
        checkin_perceived_difficulty: 3,
        checkin_focus_level: 5,
      })
      .subscribe();

    const req = httpMock.expectOne('/api/v1/sessions/sess-fin/finalize');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush(makeSession({ id: 'sess-fin', status: 'COMPLETED' }));

    expect(service.activeSession()).toBeNull();
    expect(service.isRunning()).toBe(false);
    expect(service.lastFinalizedSession()?.status).toBe('COMPLETED');
  });

  it('resolvePendingTakeaway() gửi POST /api/v1/sessions/{id}/resolve-takeaway', () => {
    service
      .resolvePendingTakeaway('sess-debt', {
        takeaway: 'Tóm tắt lại kiến thức về Dependency Inversion và tách module độc lập.',
        self_confidence: 4,
      })
      .subscribe();

    const req = httpMock.expectOne('/api/v1/sessions/sess-debt/resolve-takeaway');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush(makeSession({ id: 'sess-debt', pending_takeaway: false }));

    expect(service.pendingTakeawaySession()).toBeNull();
  });

  it('formattedTime và progressPercentage tính toán chính xác', () => {
    service.durationMinutes.set(20);
    service.remainingSeconds.set(1200);
    expect(service.formattedTime()).toBe('20:00');
    expect(service.progressPercentage()).toBe(0);

    service.remainingSeconds.set(600);
    expect(service.formattedTime()).toBe('10:00');
    expect(service.progressPercentage()).toBe(50);

    service.remainingSeconds.set(9);
    expect(service.formattedTime()).toBe('00:09');
  });

  it('evaluateTakeawayCheck() kiểm tra tối thiểu 30 ký tự và 6 từ phân biệt', () => {
    expect(evaluateTakeawayCheck('Quá ngắn').isValid).toBe(false);
    expect(
      evaluateTakeawayCheck('Em đã hiểu cách tách Use Case và Repository Port trong Python.')
        .isValid
    ).toBe(true);
  });
});
