import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { vi } from 'vitest';
import {
  StudySessionResponse,
  TaskResponse,
  TodayFocusResponse,
  WorkspaceSessionService,
  evaluateTakeawayCheck,
} from './workspace-session.service';
import { EntityInvalidationService } from './entity-invalidation.service';

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

const makeTodayFocus = (overrides: Partial<TodayFocusResponse> = {}): TodayFocusResponse => ({
  local_date: '2026-11-18',
  active_session: null,
  pending_takeaway_session: null,
  focus_task: null,
  today_queue: [],
  overdue_tasks_count: 0,
  completed_sessions_today: 0,
  studied_minutes_today: 0,
  ...overrides,
});

describe('WorkspaceSessionService', () => {
  let service: WorkspaceSessionService;
  let httpMock: HttpTestingController;

  let storageMap: Map<string, string>;
  let getItemSpy: ReturnType<typeof vi.fn>;
  let setItemSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    storageMap = new Map<string, string>([
      ['focusflow_pomodoros_today_v1', JSON.stringify({ date: '2099-01-01', count: 99 })],
    ]);
    getItemSpy = vi.fn((key: string) => storageMap.get(key) ?? null);
    setItemSpy = vi.fn((key: string, value: string) => {
      storageMap.set(key, value);
    });
    vi.stubGlobal('localStorage', {
      getItem: getItemSpy,
      setItem: setItemSpy,
      removeItem: (key: string) => {
        storageMap.delete(key);
      },
      clear: () => {
        storageMap.clear();
      },
    });
    TestBed.configureTestingModule({
      providers: [WorkspaceSessionService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(WorkspaceSessionService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    service?.pauseSession();
    service?.stopBreak();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    httpMock?.verify();
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
    const todayFocus = makeTodayFocus({
      pending_takeaway_session: pendingSession,
      focus_task: task,
      today_queue: [task],
      overdue_tasks_count: 1,
    });

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

  it('stopwatch mode đếm tiến liên tục không tự tạm dừng khi vượt duration và định dạng HH:MM:SS khi >= 3600s', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-18T10:00:00Z'));

    service.mode.set('stopwatch');
    service.hydrateActiveSession(makeSession({ planned_minutes: 1 }), true);

    expect(service.isRunning()).toBe(true);
    expect(service.displaySeconds()).toBe(0);
    expect(service.formattedTime()).toBe('00:00');

    // Tiến 90 giây (vượt quá 1 phút planned_minutes)
    vi.advanceTimersByTime(90 * 1000);
    expect(service.isRunning()).toBe(true);
    expect(service.elapsedSeconds()).toBe(90);
    expect(service.remainingSeconds()).toBe(0);
    expect(service.displaySeconds()).toBe(90);
    expect(service.formattedTime()).toBe('01:30');
    expect(service.progressPercentage()).toBe(100);

    // Tiến thêm 3600 giây -> tổng 3690 giây = 01:01:30
    vi.advanceTimersByTime(3600 * 1000);
    expect(service.isRunning()).toBe(true);
    expect(service.elapsedSeconds()).toBe(3690);
    expect(service.formattedTime()).toBe('01:01:30');

    // Dọn dẹp các heartbeat request định kỳ 60s phát sinh trong lúc stopwatch chạy
    const hbReqs = httpMock.match('/api/v1/sessions/sess-01/heartbeat');
    expect(hbReqs.length).toBeGreaterThan(0);
    for (const req of hbReqs) {
      if (!req.cancelled) {
        req.flush(makeSession({ id: 'sess-01' }));
      }
    }
  });

  it('pomodoro mode tự tạm dừng và tăng timerCompletedTick khi về 0 nhưng KHÔNG tăng completedPomodorosToday trước khi finalize thành công', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-18T10:00:00Z'));

    service.mode.set('pomodoro');
    service.hydrateActiveSession(makeSession({ id: 'sess-pomo', planned_minutes: 1 }), true);

    expect(service.timerCompletedTick()).toBe(0);
    expect(service.completedPomodorosToday()).toBe(0);

    vi.advanceTimersByTime(60 * 1000);

    expect(service.remainingSeconds()).toBe(0);
    expect(service.isRunning()).toBe(false);
    expect(service.timerCompletedTick()).toBe(1);
    // Phải vẫn là 0 cho đến khi backend finalize trả về COMPLETED / PARTIAL_COMPLETED
    expect(service.completedPomodorosToday()).toBe(0);
    expect(getItemSpy).not.toHaveBeenCalledWith('focusflow_pomodoros_today_v1');
    expect(setItemSpy).not.toHaveBeenCalledWith('focusflow_pomodoros_today_v1', expect.anything());

    // Finalize thành công với COMPLETED -> tăng delta lên 1 mà không đụng localStorage
    service
      .finalizeSession({
        early_stop: false,
        takeaway: 'Hoàn thành trọn vẹn phiên học 1 phút theo chuẩn Pomodoro và chốt kết quả.',
        checkin_time_sufficiency: 'JUST_RIGHT',
      })
      .subscribe();
    httpMock
      .expectOne('/api/v1/sessions/sess-pomo/finalize')
      .flush(makeSession({ id: 'sess-pomo', status: 'COMPLETED' }));

    expect(service.completedPomodorosToday()).toBe(1);
    expect(getItemSpy).not.toHaveBeenCalledWith('focusflow_pomodoros_today_v1');
    expect(setItemSpy).not.toHaveBeenCalledWith('focusflow_pomodoros_today_v1', expect.anything());
  });

  it('KHÔNG tăng completedPomodorosToday khi finalize trả về CANCELLED hoặc lỗi HTTP, và không đếm lặp khi gọi double finalize', () => {
    // 1. CANCELLED -> giữ nguyên 0
    service.hydrateActiveSession(makeSession({ id: 'sess-cancel' }), true);
    service
      .finalizeSession({
        early_stop: true,
        takeaway: '',
      })
      .subscribe();
    httpMock
      .expectOne('/api/v1/sessions/sess-cancel/finalize')
      .flush(makeSession({ id: 'sess-cancel', status: 'CANCELLED' }));

    expect(service.completedPomodorosToday()).toBe(0);

    // 2. HTTP error -> giữ nguyên 0
    service.hydrateActiveSession(makeSession({ id: 'sess-err' }), true);
    let errCaught = false;
    service
      .finalizeSession({
        early_stop: false,
        takeaway: 'Kiểm thử lỗi mạng khi chốt phiên học trên máy chủ backend.',
      })
      .subscribe({
        error: () => {
          errCaught = true;
        },
      });
    httpMock
      .expectOne('/api/v1/sessions/sess-err/finalize')
      .flush({ message: 'Server error' }, { status: 500, statusText: 'Server Error' });

    expect(errCaught).toBe(true);
    expect(service.completedPomodorosToday()).toBe(0);

    // 3. Double finalize trên cùng một session đang active -> lần 2 bị chặn do sessionId đã null sau lần 1, không đếm lặp
    service.finalizeSession({
      early_stop: false,
      takeaway: 'Chốt phiên hợp lệ sau khi khôi phục kết nối máy chủ thành công.',
    }).subscribe();
    httpMock
      .expectOne('/api/v1/sessions/sess-err/finalize')
      .flush(makeSession({ id: 'sess-err', status: 'PARTIAL_COMPLETED' }));

    expect(service.completedPomodorosToday()).toBe(1);

    let secondFinalizeErrored = false;
    service
      .finalizeSession({
        early_stop: false,
        takeaway: 'Gọi finalize lần hai phải bị từ chối và không tăng bộ đếm.',
      })
      .subscribe({
        error: () => {
          secondFinalizeErrored = true;
        },
      });
    expect(secondFinalizeErrored).toBe(true);
    expect(service.completedPomodorosToday()).toBe(1);
    expect(getItemSpy).not.toHaveBeenCalledWith('focusflow_pomodoros_today_v1');
    expect(setItemSpy).not.toHaveBeenCalledWith('focusflow_pomodoros_today_v1', expect.anything());
  });

  it('local break timer hỗ trợ startBreak, pauseBreak, resumeBreak, stopBreak và tự dừng khi hết giờ mà không gọi API', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-18T10:00:00Z'));

    service.startBreak('short', 1);
    expect(service.activeBreakType()).toBe('short');
    expect(service.breakDurationMinutes()).toBe(1);
    expect(service.breakRemainingSeconds()).toBe(60);
    expect(service.isBreakRunning()).toBe(true);
    expect(service.breakFormattedTime()).toBe('01:00');
    expect(service.breakProgressPercentage()).toBe(0);

    vi.advanceTimersByTime(15 * 1000);
    expect(service.breakRemainingSeconds()).toBe(45);
    expect(service.breakFormattedTime()).toBe('00:45');
    expect(service.breakProgressPercentage()).toBe(25);

    service.pauseBreak();
    expect(service.isBreakRunning()).toBe(false);
    vi.advanceTimersByTime(10 * 1000);
    expect(service.breakRemainingSeconds()).toBe(45);

    service.resumeBreak();
    expect(service.isBreakRunning()).toBe(true);
    vi.advanceTimersByTime(15 * 1000);
    expect(service.breakRemainingSeconds()).toBe(30);
    expect(service.breakProgressPercentage()).toBe(50);

    // Kết thúc khi chạy hết 30s còn lại
    const prevTick = service.timerCompletedTick();
    vi.advanceTimersByTime(30 * 1000);
    expect(service.timerCompletedTick()).toBe(prevTick + 1);
    expect(service.isBreakRunning()).toBe(false);
    expect(service.activeBreakType()).toBeNull();

    // Kiểm tra stopBreak thủ công
    service.startBreak('long', 15);
    expect(service.activeBreakType()).toBe('long');
    expect(service.isBreakRunning()).toBe(true);
    service.stopBreak();
    expect(service.activeBreakType()).toBeNull();
    expect(service.isBreakRunning()).toBe(false);
    expect(service.breakRemainingSeconds()).toBe(300);
  });

  it('toggleTaskCompletion() cập nhật lạc quan và rollback khi HTTP lỗi', () => {
    const task1 = makeTask({ id: 'task-01', status: 'TODO' });
    const todayFocus = makeTodayFocus({
      focus_task: task1,
      today_queue: [task1],
    });

    service.loadWorkspace().subscribe();
    httpMock.expectOne('/api/v1/sessions/today-focus').flush(todayFocus);
    httpMock.expectOne('/api/v1/sessions/active').flush(null);

    // 1. Thành công: TODO -> COMPLETED
    let result: TaskResponse | null = null;
    service.toggleTaskCompletion(task1).subscribe((res) => {
      result = res;
    });

    // Optimistic state ngay lập tức
    expect(service.todayQueue()[0].status).toBe('COMPLETED');
    expect(service.focusTask()?.status).toBe('COMPLETED');

    const completeReq = httpMock.expectOne('/api/v1/tasks/task-01/complete');
    expect(completeReq.request.method).toBe('POST');
    expect(completeReq.request.withCredentials).toBe(true);
    expect(completeReq.request.body).toBeNull();
    const serverCompleted = makeTask({
      id: 'task-01',
      status: 'COMPLETED',
      completed_at: '2026-11-18T10:05:00Z',
    });
    completeReq.flush(serverCompleted);
    expect(result).toEqual(serverCompleted);
    expect(service.todayQueue()[0].completed_at).toBe('2026-11-18T10:05:00Z');

    // 2. Lỗi HTTP khi reopen: COMPLETED -> optimistic PENDING -> rollback COMPLETED
    let errorResult: TaskResponse | null | undefined;
    service.toggleTaskCompletion(serverCompleted).subscribe((res) => {
      errorResult = res;
    });

    expect(service.todayQueue()[0].status).toBe('PENDING');

    const reopenReq = httpMock.expectOne('/api/v1/tasks/task-01/reopen');
    expect(reopenReq.request.method).toBe('POST');
    expect(reopenReq.request.withCredentials).toBe(true);
    reopenReq.flush({ detail: 'Server error' }, { status: 500, statusText: 'Server Error' });

    expect(errorResult).toBeNull();
    expect(service.todayQueue()[0].status).toBe('COMPLETED');
    expect(service.focusTask()?.status).toBe('COMPLETED');
    expect(service.errorState()).not.toBeNull();
  });

  it('todayProgress tính toán đúng số task hoàn thành, phần trăm, tổng phút dự kiến và đã học', () => {
    const task1 = makeTask({ id: 't1', status: 'COMPLETED', estimated_minutes: 30 });
    const task2 = makeTask({ id: 't2', status: 'TODO', estimated_minutes: 45 });
    const taskCancelled = makeTask({ id: 't3', status: 'CANCELLED', estimated_minutes: 60 });

    const todayFocus = makeTodayFocus({
      focus_task: task1,
      today_queue: [task1, task2, taskCancelled],
    });

    service.loadWorkspace().subscribe();
    httpMock.expectOne('/api/v1/sessions/today-focus').flush(todayFocus);
    httpMock.expectOne('/api/v1/sessions/active').flush(null);

    service.elapsedSeconds.set(185); // 3 phút

    expect(service.todayProgress()).toEqual({
      completedCount: 1,
      totalCount: 2,
      percentage: 50,
      totalPlannedMinutes: 75,
      totalStudiedMinutes: 3,
    });
  });

  it('lifecycleState phản ánh đúng READY, FOCUSING, PAUSED, BREAK, COMPLETED', () => {
    expect(service.lifecycleState()).toBe('READY');

    const session = makeSession({ status: 'IN_PROGRESS' });
    service.hydrateActiveSession(session, true);
    expect(service.lifecycleState()).toBe('FOCUSING');

    service.pauseSession();
    expect(service.lifecycleState()).toBe('PAUSED');

    service.startBreak('short', 5);
    expect(service.lifecycleState()).toBe('BREAK');

    service.stopBreak();
    expect(service.lifecycleState()).toBe('PAUSED');

    service.finalizeSession({
      early_stop: false,
      takeaway: 'Hoàn thành kiến trúc Hexagonal với đầy đủ port và adapter.',
      checkin_time_sufficiency: 'JUST_RIGHT',
    }).subscribe();
    httpMock
      .expectOne(`/api/v1/sessions/${session.id}/finalize`)
      .flush(makeSession({ ...session, status: 'COMPLETED' }));

    expect(service.lifecycleState()).toBe('COMPLETED');
  });

  it('activeFocusTask và setActiveFocusTask cho phép chuyển task trong phiên và chặn task ngoài phiên', () => {
    const task1 = makeTask({ id: 't1', title: 'Task 1' });
    const task2 = makeTask({ id: 't2', title: 'Task 2' });
    const taskOutside = makeTask({ id: 't3', title: 'Task 3' });

    const todayFocus = makeTodayFocus({
      focus_task: task1,
      today_queue: [task1, task2, taskOutside],
    });

    service.loadWorkspace().subscribe();
    httpMock.expectOne('/api/v1/sessions/today-focus').flush(todayFocus);
    httpMock.expectOne('/api/v1/sessions/active').flush(null);

    expect(service.activeFocusTask()?.id).toBe('t1');
    expect(service.setActiveFocusTask('t3')).toBe(true);
    expect(service.activeFocusTask()?.id).toBe('t3');

    const session = makeSession({
      session_tasks: [
        {
          id: 'st-1',
          session_id: 'sess-01',
          task_id: 't1',
          allocated_minutes: 25,
          actual_minutes: 0,
          status_after_session: 'IN_PROGRESS',
        },
        {
          id: 'st-2',
          session_id: 'sess-01',
          task_id: 't2',
          allocated_minutes: 25,
          actual_minutes: 0,
          status_after_session: 'IN_PROGRESS',
        },
      ],
    });
    service.hydrateActiveSession(session, true);

    expect(service.activeFocusTask()?.id).toBe('t1');
    expect(service.setActiveFocusTask('t3')).toBe(false);
    expect(service.activeFocusTask()?.id).toBe('t1');

    expect(service.setActiveFocusTask('t2')).toBe(true);
    expect(service.activeFocusTask()?.id).toBe('t2');
  });

  it('loadMilestoneContext dùng cache theo roadmapId và bỏ qua lỗi một cách an toàn', () => {
    service.loadMilestoneContext('rm-01', 'ms-01');
    const req = httpMock.expectOne('/api/v1/roadmaps/rm-01');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush({
      id: 'rm-01',
      user_id: 'usr-01',
      goal_id: 'goal-01',
      title: 'Roadmap 1',
      status: 'ACTIVE',
      created_at: '2026-11-18T00:00:00Z',
      updated_at: '2026-11-18T00:00:00Z',
      milestones: [
        {
          id: 'ms-01',
          roadmap_id: 'rm-01',
          title: 'Milestone 1',
          order_index: 0,
          status: 'IN_PROGRESS',
          learning_outcomes: ['Hiểu Hexagonal'],
          completion_criteria: 'Pass unit test',
          created_at: '2026-11-18T00:00:00Z',
          updated_at: '2026-11-18T00:00:00Z',
        },
        {
          id: 'ms-02',
          roadmap_id: 'rm-01',
          title: 'Milestone 2',
          order_index: 1,
          status: 'PENDING',
          learning_outcomes: ['Triển khai SSE'],
          completion_criteria: null,
          created_at: '2026-11-18T00:00:00Z',
          updated_at: '2026-11-18T00:00:00Z',
        },
      ],
    });

    expect(service.milestoneContext()).toEqual({
      roadmapId: 'rm-01',
      milestoneId: 'ms-01',
      learningOutcomes: ['Hiểu Hexagonal'],
      completionCriteria: 'Pass unit test',
    });

    // Cache hit for same roadmapId
    service.loadMilestoneContext('rm-01', 'ms-02');
    httpMock.expectNone('/api/v1/roadmaps/rm-01');
    expect(service.milestoneContext()).toEqual({
      roadmapId: 'rm-01',
      milestoneId: 'ms-02',
      learningOutcomes: ['Triển khai SSE'],
      completionCriteria: null,
    });

    // Silent error handling for failing roadmap fetch
    service.loadMilestoneContext('rm-err', 'ms-err');
    httpMock
      .expectOne('/api/v1/roadmaps/rm-err')
      .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
    expect(service.errorState()).toBeNull();
  });

  it('ưu tiên completed_sessions_today (+ delta sau finalize) và studied_minutes_today (+ elapsedMinutes) từ TodayFocusResponse, bỏ qua localStorage', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-18T10:00:00Z'));

    const task = makeTask();
    const todayFocus = makeTodayFocus({
      focus_task: task,
      today_queue: [task],
      completed_sessions_today: 3,
      studied_minutes_today: 75,
    });

    service.loadWorkspace().subscribe();
    httpMock.expectOne('/api/v1/sessions/today-focus').flush(todayFocus);
    httpMock.expectOne('/api/v1/sessions/active').flush(null);

    expect(service.completedPomodorosToday()).toBe(3);
    expect(service.todayProgress().totalStudiedMinutes).toBe(75);

    service.mode.set('pomodoro');
    service.hydrateActiveSession(makeSession({ id: 'sess-sync', planned_minutes: 1 }), true);

    vi.advanceTimersByTime(60 * 1000);
    // Hết giờ nhưng chưa finalize -> vẫn là 3
    expect(service.completedPomodorosToday()).toBe(3);
    expect(service.todayProgress().totalStudiedMinutes).toBe(76);

    service
      .finalizeSession({
        early_stop: false,
        takeaway: 'Hoàn tất phiên học và đồng bộ với bộ đếm chuẩn từ server.',
      })
      .subscribe();
    httpMock
      .expectOne('/api/v1/sessions/sess-sync/finalize')
      .flush(makeSession({ id: 'sess-sync', status: 'COMPLETED' }));
    expect(service.completedPomodorosToday()).toBe(4);

    // Sau khi loadWorkspace lại với giá trị server mới, delta cục bộ được reset tránh đếm lặp
    service.loadWorkspace().subscribe();
    httpMock.expectOne('/api/v1/sessions/today-focus').flush(
      makeTodayFocus({
        focus_task: task,
        today_queue: [task],
        completed_sessions_today: 4,
        studied_minutes_today: 76,
      })
    );
    httpMock.expectOne('/api/v1/sessions/active').flush(null);
    expect(service.completedPomodorosToday()).toBe(4);
    expect(service.todayProgress().totalStudiedMinutes).toBe(76);

    // Khi TodayFocusResponse không có completed_sessions_today -> mặc định 0 (không đọc localStorage)
    service.loadWorkspace().subscribe();
    httpMock.expectOne('/api/v1/sessions/today-focus').flush({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: task,
      today_queue: [task],
      overdue_tasks_count: 0,
    } as unknown as TodayFocusResponse);
    httpMock.expectOne('/api/v1/sessions/active').flush(null);
    expect(service.completedPomodorosToday()).toBe(0);
    expect(service.todayProgress().totalStudiedMinutes).toBe(0);
    expect(getItemSpy).not.toHaveBeenCalledWith('focusflow_pomodoros_today_v1');
    expect(setItemSpy).not.toHaveBeenCalledWith('focusflow_pomodoros_today_v1', expect.anything());
  });

  it('suy diễn milestoneContext trực tiếp từ activeFocusTask mà không gọi GET /api/v1/roadmaps/{id}', () => {
    const enrichedTask = makeTask({
      roadmap_id: 'rm-inline',
      milestone_id: 'ms-inline',
      milestone_title: 'Giai đoạn 1: Domain Modeling',
      learning_outcomes: ['Hiểu Aggregate Root', 'Thiết kế Value Object'],
      completion_criteria: 'Hoàn thành bài tập Aggregate',
    });

    service.loadWorkspace().subscribe();
    httpMock.expectOne('/api/v1/sessions/today-focus').flush(
      makeTodayFocus({
        focus_task: enrichedTask,
        today_queue: [enrichedTask],
      })
    );
    httpMock.expectOne('/api/v1/sessions/active').flush(null);

    expect(service.milestoneContext()).toEqual({
      roadmapId: 'rm-inline',
      milestoneId: 'ms-inline',
      milestoneTitle: 'Giai đoạn 1: Domain Modeling',
      learningOutcomes: ['Hiểu Aggregate Root', 'Thiết kế Value Object'],
      completionCriteria: 'Hoàn thành bài tập Aggregate',
    });

    service.loadMilestoneContext('rm-inline', 'ms-inline');
    httpMock.expectNone('/api/v1/roadmaps/rm-inline');
  });

  it('toggleTaskCompletion() lỗi rollback và KHÔNG phát invalidation, trong khi thành công phát invalidation đầy đủ', () => {
    const invalidation = TestBed.inject(EntityInvalidationService);
    invalidation.resetForTests();

    const task = makeTask({ id: 'task-err', status: 'TODO' });
    service.loadWorkspace().subscribe();
    httpMock.expectOne('/api/v1/sessions/today-focus').flush(
      makeTodayFocus({ focus_task: task, today_queue: [task] })
    );
    httpMock.expectOne('/api/v1/sessions/active').flush(null);

    // Lỗi HTTP -> rollback & không invalidate
    service.toggleTaskCompletion(task).subscribe();
    httpMock
      .expectOne('/api/v1/tasks/task-err/complete')
      .flush({ message: 'Server error' }, { status: 500, statusText: 'Server Error' });

    expect(service.todayQueue()[0].status).toBe('TODO');
    expect(invalidation.versionFor('tasks')()).toBe(0);
    expect(invalidation.versionFor('dashboard')()).toBe(0);
    expect(invalidation.lastTaskMutation()).toBeNull();

    // Thành công -> phát notifyTaskMutated + invalidate 4 domain
    service.toggleTaskCompletion(task).subscribe();
    httpMock
      .expectOne('/api/v1/tasks/task-err/complete')
      .flush(makeTask({ id: 'task-err', status: 'COMPLETED' }));

    expect(invalidation.lastTaskMutation()?.id).toBe('task-err');
    expect(invalidation.versionFor('tasks')()).toBe(1);
    expect(invalidation.versionFor('schedule')()).toBe(1);
    expect(invalidation.versionFor('dashboard')()).toBe(1);
    expect(invalidation.versionFor('analytics')()).toBe(1);
  });
});
