import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { WorkspaceComponent } from './workspace.component';
import { StudySessionResponse, TaskResponse, TodayFocusResponse } from './models/workspace.model';

const sampleTask: TaskResponse = {
  id: 'task-1',
  roadmap_id: 'rm-1',
  milestone_id: 'ms-1',
  title: 'Thực hành DDD Aggregate',
  description: 'Xây dựng Aggregate Root',
  estimated_minutes: 30,
  learning_resources: [{ title: 'DDD Reference', url: 'https://example.com/ddd' }],
  scheduled_date: '2026-11-18',
  status: 'TODO',
  reschedule_count: 0,
  is_overdue: false,
  is_blocked: false,
  is_stalled: false,
  predecessor_ids: [],
  roadmap_title: 'Backend Mastery',
  created_at: '2026-11-18T00:00:00Z',
  updated_at: '2026-11-18T00:00:00Z',
};

describe('WorkspaceComponent', () => {
  let component: WorkspaceComponent;
  let fixture: ComponentFixture<WorkspaceComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WorkspaceComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(WorkspaceComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    component.sessionService.pauseSession();
    httpMock.verify();
  });

  function flushInitialLoad(todayFocus: TodayFocusResponse, active: StudySessionResponse | null = null) {
    fixture.detectChanges();
    const tfReq = httpMock.expectOne('/api/v1/sessions/today-focus');
    tfReq.flush(todayFocus);
    const activeReq = httpMock.expectOne('/api/v1/sessions/active');
    activeReq.flush(active);
    fixture.detectChanges();
  }

  it('hiển thị empty state khi chưa có nhiệm vụ hôm nay', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: null,
      today_queue: [],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="workspace-empty-state"]')).toBeTruthy();
    expect(el.textContent).toContain('Chưa có nhiệm vụ nào cho hôm nay');
  });

  it('hiển thị banner xử lý Takeaway Debt khi tồn tại pending_takeaway_session', () => {
    const debtSession: StudySessionResponse = {
      id: 'sess-debt-1',
      user_id: 'u-1',
      roadmap_id: 'rm-1',
      started_at: '2026-11-18T01:00:00Z',
      planned_minutes: 25,
      actual_minutes: 20,
      status: 'AUTO_CLOSED',
      last_heartbeat_at: '2026-11-18T01:20:00Z',
      session_mode: 'STANDARD',
      pending_takeaway: true,
      scratchpad_content: '',
      session_tasks: [],
      notes: [],
      created_at: '2026-11-18T01:00:00Z',
      updated_at: '2026-11-18T01:20:00Z',
    };

    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: debtSession,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="pending-takeaway-card"]')).toBeTruthy();
    const startBtn = el.querySelector('[data-testid="start-session-btn"]') as HTMLButtonElement;
    expect(startBtn.disabled).toBe(true);
  });

  it('cho phép bắt đầu phiên học và mở hộp thoại hoàn tất phiên học', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    component.selectMode('MVS');
    expect(component.plannedMinutes()).toBe(15);

    component.startStudySession();
    const startReq = httpMock.expectOne('/api/v1/sessions/start');
    expect(startReq.request.body).toEqual({
      task_ids: ['task-1'],
      session_mode: 'MVS',
      planned_minutes: 15,
    });
    startReq.flush({
      id: 'sess-active-1',
      user_id: 'u-1',
      roadmap_id: 'rm-1',
      started_at: new Date().toISOString(),
      planned_minutes: 15,
      actual_minutes: 0,
      status: 'IN_PROGRESS',
      last_heartbeat_at: new Date().toISOString(),
      session_mode: 'MVS',
      pending_takeaway: false,
      scratchpad_content: '',
      session_tasks: [
        {
          id: 'st-1',
          session_id: 'sess-active-1',
          task_id: 'task-1',
          allocated_minutes: 15,
          actual_minutes: 0,
          status_after_session: 'IN_PROGRESS',
        },
      ],
      notes: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="workspace-timer-display"]')).toBeTruthy();

    component.openFinalizeModal(false);
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="finalize-session-dialog"]')).toBeTruthy();
  });
});
