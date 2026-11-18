import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { WorkspaceComponent } from './workspace.component';
import {
  StickyNoteResponse,
  StudySessionResponse,
  TaskResponse,
  TodayFocusResponse,
  WorkspaceStudioConfigResponse,
} from './models/workspace.model';

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
    if (typeof localStorage !== 'undefined' && typeof localStorage.removeItem === 'function') {
      localStorage.removeItem('focusflow_workspace_studio_v1');
    }

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
    component.studioStore.resetSessionDistractions();
    component.studioStore.closeToolPopover();
    component.studioStore.setFocusMode(false);
    component.studioStore.setLeftPanelCollapsed(false);
    component.studioStore.setNotesPanelOpen(false);
    component.studioStore.setClockStyle('editorial');
    component.studioStore.setScene('lofi-night');
    httpMock.verify();
  });

  function flushInitialLoad(
    todayFocusInput: Omit<
      TodayFocusResponse,
      'completed_sessions_today' | 'studied_minutes_today'
    > &
      Partial<Pick<TodayFocusResponse, 'completed_sessions_today' | 'studied_minutes_today'>>,
    active: StudySessionResponse | null = null,
    serverNotes: StickyNoteResponse[] = [],
    serverStudioConfig: WorkspaceStudioConfigResponse = {
      scene: 'lofi-night',
      clock_style: 'ring',
      clock_size: 'lg',
      show_seconds: true,
      show_in_tab_title: true,
      tab_guard_enabled: true,
      zen_lock_enabled: false,
      blocklist: ['facebook.com', 'youtube.com', 'tiktok.com'],
      parking_lot: [],
      updated_at: null,
    }
  ) {
    const todayFocus: TodayFocusResponse = {
      completed_sessions_today: 0,
      studied_minutes_today: 0,
      ...todayFocusInput,
    };
    fixture.detectChanges();
    const notesReq = httpMock.expectOne('/api/v1/sessions/notes');
    notesReq.flush(serverNotes);
    const configReq = httpMock.expectOne('/api/v1/sessions/studio-config');
    configReq.flush(serverStudioConfig);
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

    httpMock.match('/api/v1/roadmaps/rm-1').forEach((req) =>
      req.flush({ id: 'rm-1', milestones: [] })
    );
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="workspace-timer-display"]')).toBeTruthy();

    component.openFinalizeModal(false);
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="finalize-session-dialog"]')).toBeTruthy();
  });

  it('cho phép bật tắt bảng ghi chú nhanh bên phải', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('ff-workspace-sticky-notes-panel')).toBeNull();

    const toggleBtn = el.querySelector('button[aria-label="Ghi chú nhanh"]') as HTMLButtonElement;
    toggleBtn.click();
    fixture.detectChanges();

    expect(component.studioStore.notesPanelOpen()).toBe(true);
    expect(el.querySelector('ff-workspace-sticky-notes-panel')).toBeTruthy();

    toggleBtn.click();
    fixture.detectChanges();

    expect(component.studioStore.notesPanelOpen()).toBe(false);
    expect(el.querySelector('ff-workspace-sticky-notes-panel')).toBeNull();
  });

  it('hiển thị Focus Shield Return Banner khi ghi nhận sao nhãng và cho phép đóng', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="focus-return-banner"]')).toBeNull();

    component.studioStore.recordDistraction();
    fixture.detectChanges();

    const banner = el.querySelector('[data-testid="focus-return-banner"]');
    expect(banner).toBeTruthy();
    expect(banner?.textContent).toContain('1 lần sao nhãng');

    const dismissBtn = el.querySelector('[data-testid="dismiss-return-banner-btn"]') as HTMLButtonElement;
    dismissBtn.click();
    fixture.detectChanges();

    expect(el.querySelector('[data-testid="focus-return-banner"]')).toBeNull();
  });

  it('cho phép chuyển đổi kiểu hiển thị đồng hồ (clockStyle)', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="workspace-timer-display"] svg')).toBeTruthy();

    component.studioStore.setClockStyle('editorial');
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="workspace-timer-display"] svg')).toBeNull();

    component.studioStore.setClockStyle('flip');
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="workspace-timer-display"] .flip-card')).toBeTruthy();
  });

  it('cho phép thu gọn và mở rộng bảng nhiệm vụ bên trái', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="workspace-left-region"]')).toBeTruthy();

    const collapseBtn = el.querySelector('button[aria-label="Thu gọn bảng điều khiển"]') as HTMLButtonElement;
    collapseBtn.click();
    fixture.detectChanges();

    expect(component.studioStore.leftPanelCollapsed()).toBe(true);
    expect(el.querySelector('[data-testid="workspace-left-region"]')).toBeNull();

    const openBtn = el.querySelector('[data-testid="open-left-panel-btn"]') as HTMLButtonElement;
    expect(openBtn).toBeTruthy();
    openBtn.click();
    fixture.detectChanges();

    expect(component.studioStore.leftPanelCollapsed()).toBe(false);
    expect(el.querySelector('[data-testid="workspace-left-region"]')).toBeTruthy();
  });

  it('cho phép mở và đóng bảng công cụ Âm thanh ngay trong bảng điều khiển bên trái', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('section[aria-label="Âm thanh & Nhạc nền"]')).toBeNull();
    expect(el.querySelector('nav[aria-label="Lưới công cụ không gian học"]')).toBeTruthy();

    const audioBtn = el.querySelector('button[aria-label*="Âm thanh"]') as HTMLButtonElement;
    audioBtn.click();
    fixture.detectChanges();

    expect(component.studioStore.activeToolPopover()).toBe('audio');
    expect(el.querySelector('section[aria-label*="Âm thanh"]')).toBeTruthy();

    const closeToolBtn = el.querySelector('button[aria-label="Quay lại bảng công cụ"]') as HTMLButtonElement;
    closeToolBtn.click();
    fixture.detectChanges();

    expect(component.studioStore.activeToolPopover()).toBeNull();
    expect(el.querySelector('section[aria-label="Âm thanh & Nhạc nền"]')).toBeNull();
  });

  it('cập nhật thuộc tính data-ws-contrast theo bối cảnh sáng/tối', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    const studioRoot = el.querySelector('.workspace-studio') as HTMLElement;
    expect(studioRoot).toBeTruthy();

    component.studioStore.setScene('lofi-night');
    fixture.detectChanges();
    expect(studioRoot.getAttribute('data-ws-contrast')).toBe('dark');

    component.studioStore.setScene('architectural');
    fixture.detectChanges();
    expect(studioRoot.getAttribute('data-ws-contrast')).toBe('light');
  });

  it('cho phép bật Focus Mode và thoát bằng phím Escape mà không dừng phiên học', () => {
    const activeSession: StudySessionResponse = {
      id: 'sess-focus-1',
      user_id: 'u-1',
      roadmap_id: 'rm-1',
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
          id: 'st-1',
          session_id: 'sess-focus-1',
          task_id: 'task-1',
          allocated_minutes: 25,
          actual_minutes: 0,
          status_after_session: 'IN_PROGRESS',
        },
      ],
      notes: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    flushInitialLoad(
      {
        local_date: '2026-11-18',
        active_session: activeSession,
        pending_takeaway_session: null,
        focus_task: sampleTask,
        today_queue: [sampleTask],
        overdue_tasks_count: 0,
      },
      activeSession
    );

    httpMock.match('/api/v1/roadmaps/rm-1').forEach((req) =>
      req.flush({ id: 'rm-1', milestones: [] })
    );
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const focusBtn = el.querySelector('button[aria-label="Chế độ tập trung"]') as HTMLButtonElement;
    focusBtn.click();
    fixture.detectChanges();

    expect(component.studioStore.focusMode()).toBe(true);
    expect(el.querySelector('[data-testid="workspace-focus-mode-region"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="workspace-left-region"]')).toBeNull();
    expect(el.querySelector('[data-testid="exit-focus-mode-btn"]')).toBeTruthy();
    expect(component.sessionService.isRunning()).toBe(true);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    fixture.detectChanges();

    expect(component.studioStore.focusMode()).toBe(false);
    expect(el.querySelector('[data-testid="workspace-left-region"]')).toBeTruthy();
    expect(component.sessionService.isRunning()).toBe(true);
  });

  it('ghim ghi chú mới khi nhấn Enter trong 1 Note Composer và giữ ghi chú hiển thị sau khi đóng composer', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const el = fixture.nativeElement as HTMLElement;
    const toggleBtn = el.querySelector('button[aria-label="Ghi chú nhanh"]') as HTMLButtonElement;
    toggleBtn.click();
    fixture.detectChanges();

    const titleInput = el.querySelector('[data-testid="scratchpad-title-input"]') as HTMLInputElement;
    const textarea = el.querySelector('[data-testid="scratchpad-textarea"]') as HTMLTextAreaElement;
    expect(titleInput).toBeTruthy();
    expect(textarea).toBeTruthy();

    titleInput.value = '  Tài liệu DDD  ';
    titleInput.dispatchEvent(new Event('input'));
    textarea.value = 'Công thức DDD Aggregate Root https://youtu.be/dQw4w9WgXcQ';
    textarea.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', cancelable: true }));
    fixture.detectChanges();

    const createNoteReq = httpMock.expectOne('/api/v1/sessions/notes');
    expect(createNoteReq.request.method).toBe('POST');
    createNoteReq.flush({
      id: '01933c2a-1111-7000-8000-000000000010',
      task_id: null,
      title: 'Tài liệu DDD',
      body: 'Công thức DDD Aggregate Root https://youtu.be/dQw4w9WgXcQ',
      color: 'cream',
      pinned: true,
      pos_x: null,
      pos_y: null,
      z_index: 1,
      origin_session_id: null,
      created_at: '2026-11-18T10:00:00Z',
      updated_at: '2026-11-18T10:00:00Z',
    });
    fixture.detectChanges();

    expect(component.studioStore.visiblePinnedNotes().length).toBe(1);
    expect(component.studioStore.visiblePinnedNotes()[0].title).toBe('Tài liệu DDD');
    expect(component.studioStore.visiblePinnedNotes()[0].content).toBe(
      'Công thức DDD Aggregate Root https://youtu.be/dQw4w9WgXcQ'
    );
    expect(titleInput.value).toBe('');
    expect(textarea.value).toBe('');

    const closeComposerBtn = el.querySelector(
      'button[aria-label="Đóng khung soạn ghi chú"]'
    ) as HTMLButtonElement;
    closeComposerBtn.click();
    fixture.detectChanges();

    expect(component.studioStore.notesPanelOpen()).toBe(false);
    expect(el.querySelector('ff-workspace-sticky-notes-panel')).toBeTruthy();
    expect(el.querySelector('[data-testid="scratchpad-textarea"]')).toBeNull();
    expect(el.textContent).toContain('Công thức DDD Aggregate Root');
    const pinnedTitleInput = el.querySelector('[data-testid="pinned-note-title-input"]') as HTMLInputElement;
    expect(pinnedTitleInput?.value).toBe('Tài liệu DDD');
    const ytThumb = el.querySelector('[data-testid="note-media-previews"] img') as HTMLImageElement;
    expect(ytThumb?.getAttribute('src')).toBe('https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg');
  });

  it('hiển thị cảnh báo khi bấm vào nhiệm vụ ngoài phiên đang học', () => {
    const outsideTask: TaskResponse = {
      ...sampleTask,
      id: 'task-2',
      title: 'Viết Unit Test cho Outbox',
    };
    const activeSession: StudySessionResponse = {
      id: 'sess-active-2',
      user_id: 'u-1',
      roadmap_id: 'rm-1',
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
          id: 'st-1',
          session_id: 'sess-active-2',
          task_id: 'task-1',
          allocated_minutes: 25,
          actual_minutes: 0,
          status_after_session: 'IN_PROGRESS',
        },
      ],
      notes: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    flushInitialLoad(
      {
        local_date: '2026-11-18',
        active_session: activeSession,
        pending_takeaway_session: null,
        focus_task: sampleTask,
        today_queue: [sampleTask, outsideTask],
        overdue_tasks_count: 0,
      },
      activeSession
    );

    httpMock.match('/api/v1/roadmaps/rm-1').forEach((req) =>
      req.flush({ id: 'rm-1', milestones: [] })
    );
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const outsideRow = el.querySelector(
      `[aria-label="Nhiệm vụ ngoài phiên: ${outsideTask.title}"]`
    ) as HTMLElement;
    expect(outsideRow).toBeTruthy();
    outsideRow.click();
    fixture.detectChanges();

    const warningBanner = el.querySelector('[data-testid="switch-task-warning-banner"]');
    expect(warningBanner).toBeTruthy();
    expect(warningBanner?.textContent).toContain(
      'Cần hoàn tất hoặc dừng sớm phiên hiện tại trước khi chuyển sang nhiệm vụ khác'
    );
    expect(el.querySelector('[data-testid="switch-task-end-session-btn"]')).toBeTruthy();
  });

  it('cập nhật tọa độ và zIndex của ghi chú nổi trên Desktop khi kéo hoặc điều hướng bằng phím mũi tên', () => {
    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: sampleTask,
      today_queue: [sampleTask],
      overdue_tasks_count: 0,
    });

    const note1 = component.studioStore.pinNewNoteFromComposer(
      'Ghi chú di chuyển',
      'cream',
      null,
      null,
      'Note 1'
    );
    const note2 = component.studioStore.pinNewNoteFromComposer(
      'Ghi chú thứ hai',
      'sage',
      null,
      null,
      'Note 2'
    );
    expect(note1).not.toBeNull();
    expect(note2).not.toBeNull();
    const postReqs = httpMock.match('/api/v1/sessions/notes');
    expect(postReqs.length).toBe(2);
    postReqs[0].flush({
      id: '01933c2a-1111-7000-8000-000000000021',
      task_id: null,
      title: 'Note 1',
      body: 'Ghi chú di chuyển',
      color: 'cream',
      pinned: true,
      pos_x: null,
      pos_y: null,
      z_index: 1,
      origin_session_id: null,
      created_at: '2026-11-18T10:00:00Z',
      updated_at: '2026-11-18T10:00:00Z',
    });
    postReqs[1].flush({
      id: '01933c2a-1111-7000-8000-000000000022',
      task_id: null,
      title: 'Note 2',
      body: 'Ghi chú thứ hai',
      color: 'sage',
      pinned: true,
      pos_x: null,
      pos_y: null,
      z_index: 2,
      origin_session_id: null,
      created_at: '2026-11-18T10:00:00Z',
      updated_at: '2026-11-18T10:00:00Z',
    });
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const floatingLayer = el.querySelector('[data-testid="desktop-floating-notes-layer"]') as HTMLElement;
    expect(floatingLayer).toBeTruthy();

    const card1 = floatingLayer.querySelector(
      '[data-note-id="01933c2a-1111-7000-8000-000000000021"]'
    ) as HTMLElement;
    expect(card1).toBeTruthy();

    // Drag via pointer events
    card1.dispatchEvent(
      new PointerEvent('pointerdown', {
        bubbles: true,
        clientX: 100,
        clientY: 100,
        button: 0,
        pointerType: 'mouse',
      })
    );
    window.dispatchEvent(
      new PointerEvent('pointermove', {
        bubbles: true,
        clientX: 140,
        clientY: 130,
      })
    );
    window.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
    fixture.detectChanges();

    const movedNote = component.studioStore
      .notes()
      .find((n) => n.id === '01933c2a-1111-7000-8000-000000000021');
    expect(movedNote?.posX).toBeDefined();
    expect(movedNote?.posY).toBeDefined();
    expect(movedNote?.zIndex).toBe(3);

    const prevX = movedNote!.posX!;
    const prevY = movedNote!.posY!;

    // Keyboard nudge via drag handle
    const dragHandle = card1.querySelector('div[aria-label="Kéo để di chuyển ghi chú"]') as HTMLElement;
    expect(dragHandle).toBeTruthy();
    dragHandle.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true, cancelable: true })
    );
    fixture.detectChanges();

    const nudgedNote = component.studioStore
      .notes()
      .find((n) => n.id === '01933c2a-1111-7000-8000-000000000021');
    expect(nudgedNote?.posX).toBe(Math.max(12, prevX - 16));
    expect(nudgedNote?.posY).toBe(prevY);
  });

  it('hiển thị milestone context (milestone_title, learning_outcomes, completion_criteria) từ TodayFocusResponse mà không gọi /api/v1/roadmaps/{id}', () => {
    const enrichedTask: TaskResponse = {
      ...sampleTask,
      milestone_sequence: 1,
      milestone_title: 'Nền tảng Domain-Driven Design',
      learning_outcomes: ['Phân biệt Entity và Value Object', 'Thiết kế Aggregate Root'],
      completion_criteria: 'Hoàn thành module Domain thuần Python',
    };

    flushInitialLoad({
      local_date: '2026-11-18',
      active_session: null,
      pending_takeaway_session: null,
      focus_task: enrichedTask,
      today_queue: [enrichedTask],
      overdue_tasks_count: 0,
    });

    httpMock.expectNone('/api/v1/roadmaps/rm-1');

    const el = fixture.nativeElement as HTMLElement;
    const contextEl = el.querySelector('[data-testid="active-task-context"]') as HTMLElement;
    expect(contextEl).toBeTruthy();
    expect(contextEl.textContent).toContain('Mốc #1: Nền tảng Domain-Driven Design');

    const toggleBtn = contextEl.querySelector(
      '[data-testid="toggle-objective-btn"]'
    ) as HTMLButtonElement;
    expect(toggleBtn).toBeTruthy();
    toggleBtn.click();
    fixture.detectChanges();

    const detailsPanel = contextEl.querySelector(
      '[data-testid="objective-details-panel"]'
    ) as HTMLElement;
    expect(detailsPanel).toBeTruthy();
    expect(detailsPanel.textContent).toContain('Phân biệt Entity và Value Object');
    expect(detailsPanel.textContent).toContain('Hoàn thành module Domain thuần Python');
  });

  it('tự động đồng bộ ghi chú và cấu hình Studio từ server khi khởi tạo WorkspaceComponent', () => {
    flushInitialLoad(
      {
        local_date: '2026-11-18',
        active_session: null,
        pending_takeaway_session: null,
        focus_task: sampleTask,
        today_queue: [sampleTask],
        overdue_tasks_count: 0,
        completed_sessions_today: 2,
        studied_minutes_today: 50,
      },
      null,
      [
        {
          id: '01933c2a-1111-7000-8000-000000000088',
          task_id: null,
          title: 'Ghi chú đồng bộ',
          body: 'Nội dung từ backend',
          color: 'lavender',
          pinned: true,
          pos_x: 100,
          pos_y: 120,
          z_index: 2,
          origin_session_id: null,
          created_at: '2026-11-18T10:00:00Z',
          updated_at: '2026-11-18T10:05:00Z',
        },
      ],
      {
        scene: 'library',
        clock_style: 'flip',
        clock_size: 'md',
        show_seconds: false,
        show_in_tab_title: false,
        tab_guard_enabled: false,
        zen_lock_enabled: true,
        blocklist: ['example.com'],
        parking_lot: [],
        updated_at: '2026-11-18T10:00:00Z',
      }
    );

    expect(component.studioStore.scene()).toBe('library');
    expect(component.studioStore.clockStyle()).toBe('flip');
    expect(component.studioStore.clockSize()).toBe('md');
    expect(component.studioStore.showSeconds()).toBe(false);
    expect(component.studioStore.notes().length).toBe(1);
    expect(component.studioStore.notes()[0].title).toBe('Ghi chú đồng bộ');
    expect(component.sessionService.completedPomodorosToday()).toBe(2);
    expect(component.sessionService.todayProgress().totalStudiedMinutes).toBe(50);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="workspace-timer-display"] .flip-card')).toBeTruthy();
  });
});
