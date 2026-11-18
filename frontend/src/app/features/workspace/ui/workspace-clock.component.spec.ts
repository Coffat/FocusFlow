import { ComponentFixture, TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { STUDY_QUOTES, WorkspaceClockComponent } from './workspace-clock.component';
import {
  ClockStyleId,
  MilestoneContextSummary,
  StudySessionResponse,
  TaskResponse,
  TimerTabMode,
} from '../models/workspace.model';

function createActiveSession(
  overrides: Partial<StudySessionResponse> = {}
): StudySessionResponse {
  return {
    id: 'session-1',
    user_id: 'user-1',
    roadmap_id: 'roadmap-1',
    started_at: '2026-11-18T10:00:00Z',
    ended_at: null,
    planned_minutes: 25,
    actual_minutes: 0,
    status: 'IN_PROGRESS',
    last_heartbeat_at: '2026-11-18T10:01:00Z',
    session_mode: 'STANDARD',
    pending_takeaway: false,
    scratchpad_content: '',
    created_at: '2026-11-18T10:00:00Z',
    updated_at: '2026-11-18T10:01:00Z',
    ...overrides,
  };
}

function createTask(overrides: Partial<TaskResponse> = {}): TaskResponse {
  return {
    id: 'task-1',
    roadmap_id: 'roadmap-1',
    milestone_id: 'milestone-1',
    title: 'Ôn tập SQL Indexing & Query Plan',
    description: 'Phân tích EXPLAIN ANALYZE cho bảng lớn.',
    estimated_minutes: 45,
    learning_resources: [{ title: 'PostgreSQL Docs', url: 'https://www.postgresql.org/docs/' }],
    status: 'TODO',
    reschedule_count: 0,
    is_overdue: false,
    is_blocked: false,
    is_stalled: false,
    roadmap_title: 'Lộ trình Backend PostgreSQL',
    milestone_sequence: 2,
    created_at: '2026-11-18T08:00:00Z',
    updated_at: '2026-11-18T08:00:00Z',
    ...overrides,
  };
}

function createMilestoneContext(
  overrides: Partial<MilestoneContextSummary> = {}
): MilestoneContextSummary {
  return {
    roadmapId: 'roadmap-1',
    milestoneId: 'milestone-1',
    learningOutcomes: ['Hiểu B-Tree index', 'Đọc được EXPLAIN ANALYZE'],
    completionCriteria: 'Tối ưu 3 câu truy vấn chậm dưới 50ms.',
    ...overrides,
  };
}

describe('WorkspaceClockComponent', () => {
  let fixture: ComponentFixture<WorkspaceClockComponent>;
  let component: WorkspaceClockComponent;

  function setRequiredInputs(overrides: Record<string, unknown> = {}): void {
    const defaults: Record<string, unknown> = {
      activeTabMode: 'pomodoro',
      clockStyle: 'ring',
      clockSize: 'lg',
      showSeconds: true,
      activeSession: null,
      isRunning: false,
      isSubmitting: false,
      plannedMinutes: 25,
      elapsedSeconds: 0,
      remainingSeconds: 1500,
      progressPercentage: 0,
      heartbeatStatus: 'idle',
      canStartSession: true,
    };

    const merged = { ...defaults, ...overrides };
    for (const [key, value] of Object.entries(merged)) {
      fixture.componentRef.setInput(key, value);
    }
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WorkspaceClockComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(WorkspaceClockComponent);
    component = fixture.componentInstance;
  });

  it('phát sự kiện selectTabMode khi chuyển qua lại cả 4 tab chế độ', () => {
    setRequiredInputs();
    const emitted: TimerTabMode[] = [];
    const sub = component.selectTabMode.subscribe((mode) => emitted.push(mode));

    const tabOrder: Array<{ testId: string; expected: TimerTabMode }> = [
      { testId: 'mode-mvs-btn', expected: 'mvs' },
      { testId: 'mode-stopwatch-btn', expected: 'stopwatch' },
      { testId: 'mode-break-btn', expected: 'break' },
      { testId: 'mode-standard-btn', expected: 'pomodoro' },
    ];

    for (const item of tabOrder) {
      const btn = fixture.nativeElement.querySelector(
        `[data-testid="${item.testId}"]`
      ) as HTMLButtonElement;
      expect(btn).toBeTruthy();
      btn.click();
    }

    expect(emitted).toEqual(['mvs', 'stopwatch', 'break', 'pomodoro']);
    sub.unsubscribe();
  });

  it('render cả 4 kiểu đồng hồ (ring mặc định, editorial, flip, minimal) và đặt nút điều khiển đúng vị trí ở ring', () => {
    const styles: ClockStyleId[] = ['ring', 'editorial', 'flip', 'minimal'];

    for (const style of styles) {
      setRequiredInputs({
        clockStyle: style,
        plannedMinutes: 25,
        completedPomodorosToday: 1,
      });
      const display = fixture.nativeElement.querySelector(
        '[data-testid="workspace-timer-display"]'
      ) as HTMLElement;
      expect(display).toBeTruthy();
      expect(display.textContent).toContain('25');

      if (style === 'ring') {
        const svg = display.querySelector('svg');
        expect(svg).toBeTruthy();
        expect(svg?.getAttribute('viewBox')).toBe('0 0 260 260');
        expect(display.textContent).toContain('Sẵn sàng');
        expect(display.textContent).toContain('Phiên tập trung 2 / 4');
        expect(
          display.querySelector('[data-testid="start-session-btn"]')
        ).toBeTruthy();
      }
      if (style === 'flip') {
        expect(display.querySelectorAll('.flip-card').length).toBe(2);
      }
    }

    // Ring active session: pause & finalize inside ring, early-stop outside ring SVG container
    setRequiredInputs({
      clockStyle: 'ring',
      activeSession: createActiveSession(),
      isRunning: true,
      heartbeatStatus: 'synced',
    });

    const display = fixture.nativeElement.querySelector(
      '[data-testid="workspace-timer-display"]'
    ) as HTMLElement;
    const ringOverlay = display.querySelector('.relative') as HTMLElement;
    const pauseBtn = display.querySelector(
      '[data-testid="pause-session-btn"]'
    ) as HTMLButtonElement;
    const finalizeBtn = display.querySelector(
      '[data-testid="open-finalize-btn"]'
    ) as HTMLButtonElement;
    const earlyStopBtn = display.querySelector(
      '[data-testid="open-early-stop-btn"]'
    ) as HTMLButtonElement;

    expect(display.textContent).toContain('Đang học');
    expect(ringOverlay.contains(pauseBtn)).toBe(true);
    expect(ringOverlay.contains(finalizeBtn)).toBe(true);
    expect(earlyStopBtn).toBeTruthy();
    expect(ringOverlay.contains(earlyStopBtn)).toBe(false);

    // Paused state inside ring
    setRequiredInputs({
      clockStyle: 'ring',
      activeSession: createActiveSession(),
      isRunning: false,
      heartbeatStatus: 'synced',
    });
    expect(display.textContent).toContain('Tạm dừng');
    expect(
      display.querySelector('[data-testid="resume-session-btn"]')
    ).toBeTruthy();
  });

  it('ẩn phần giây khi showSeconds = false', () => {
    setRequiredInputs({
      clockStyle: 'editorial',
      showSeconds: false,
      plannedMinutes: 25,
    });

    const editorialDisplay = fixture.nativeElement.querySelector(
      '[data-testid="workspace-timer-display"]'
    ) as HTMLElement;
    expect(editorialDisplay.textContent).toContain('25 phút');
    expect(editorialDisplay.textContent).not.toContain('25:00');

    setRequiredInputs({
      clockStyle: 'flip',
      showSeconds: false,
      plannedMinutes: 25,
    });

    const flipDisplay = fixture.nativeElement.querySelector(
      '[data-testid="workspace-timer-display"]'
    ) as HTMLElement;
    expect(flipDisplay.querySelectorAll('.flip-card').length).toBe(1);
    expect(flipDisplay.textContent).toContain('25');
    expect(flipDisplay.textContent).not.toContain(':00');

    setRequiredInputs({
      clockStyle: 'ring',
      showSeconds: false,
      plannedMinutes: 25,
    });

    const ringDisplay = fixture.nativeElement.querySelector(
      '[data-testid="workspace-timer-display"]'
    ) as HTMLElement;
    expect(ringDisplay.textContent).toContain('25 phút');
    expect(ringDisplay.textContent).not.toContain('25:00');
  });

  it('khóa tab break và mvs khi phiên STANDARD đang IN_PROGRESS nhưng vẫn cho chuyển giữa pomodoro và stopwatch', () => {
    setRequiredInputs({
      activeTabMode: 'pomodoro',
      activeSession: createActiveSession({
        session_mode: 'STANDARD',
        status: 'IN_PROGRESS',
      }),
      isRunning: true,
      heartbeatStatus: 'synced',
    });

    const emitSpy = vi.fn();
    const sub = component.selectTabMode.subscribe(emitSpy);

    const pomodoroBtn = fixture.nativeElement.querySelector(
      '[data-testid="mode-standard-btn"]'
    ) as HTMLButtonElement;
    const mvsBtn = fixture.nativeElement.querySelector(
      '[data-testid="mode-mvs-btn"]'
    ) as HTMLButtonElement;
    const stopwatchBtn = fixture.nativeElement.querySelector(
      '[data-testid="mode-stopwatch-btn"]'
    ) as HTMLButtonElement;
    const breakBtn = fixture.nativeElement.querySelector(
      '[data-testid="mode-break-btn"]'
    ) as HTMLButtonElement;

    expect(pomodoroBtn.disabled).toBe(false);
    expect(stopwatchBtn.disabled).toBe(false);
    expect(mvsBtn.disabled).toBe(true);
    expect(breakBtn.disabled).toBe(true);
    expect(mvsBtn.getAttribute('title')).toBe('Đang trong phiên học');
    expect(breakBtn.getAttribute('title')).toBe('Đang trong phiên học');

    mvsBtn.click();
    breakBtn.click();
    expect(emitSpy).not.toHaveBeenCalled();

    stopwatchBtn.click();
    expect(emitSpy).toHaveBeenCalledWith('stopwatch');
    sub.unsubscribe();
  });

  it('hiển thị Active Task Context với tên lộ trình, mốc, tiêu đề, link tài liệu an toàn và toggle mục tiêu', () => {
    setRequiredInputs({
      activeTask: createTask(),
      milestoneContext: createMilestoneContext(),
    });

    const contextEl = fixture.nativeElement.querySelector(
      '[data-testid="active-task-context"]'
    ) as HTMLElement;
    expect(contextEl).toBeTruthy();
    expect(contextEl.textContent).toContain('Lộ trình Backend PostgreSQL');
    expect(contextEl.textContent).toContain('Mốc #2');
    expect(contextEl.textContent).toContain('Ôn tập SQL Indexing & Query Plan');
    expect(contextEl.textContent).toContain('Ước lượng 45p');

    const link = contextEl.querySelector(
      '[data-testid="active-task-resource-link"]'
    ) as HTMLAnchorElement;
    expect(link).toBeTruthy();
    expect(link.getAttribute('href')).toBe('https://www.postgresql.org/docs/');
    expect(link.getAttribute('target')).toBe('_blank');
    expect(link.getAttribute('rel')).toBe('noopener noreferrer');

    const toggleBtn = contextEl.querySelector(
      '[data-testid="toggle-objective-btn"]'
    ) as HTMLButtonElement;
    expect(toggleBtn).toBeTruthy();
    expect(
      contextEl.querySelector('[data-testid="objective-details-panel"]')
    ).toBeNull();

    toggleBtn.click();
    fixture.detectChanges();

    const detailsPanel = contextEl.querySelector(
      '[data-testid="objective-details-panel"]'
    ) as HTMLElement;
    expect(detailsPanel).toBeTruthy();
    expect(detailsPanel.textContent).toContain('Hiểu B-Tree index');
    expect(detailsPanel.textContent).toContain(
      'Tối ưu 3 câu truy vấn chậm dưới 50ms.'
    );

    // Unsafe URLs must not render resource link
    setRequiredInputs({
      activeTask: createTask({
        learning_resources: [{ url: 'javascript:alert(1)' }],
      }),
    });
    expect(
      fixture.nativeElement.querySelector(
        '[data-testid="active-task-resource-link"]'
      )
    ).toBeNull();
  });

  it('ẩn câu động viên và hiển thị nút thoát chế độ tập trung khi focusMode = true', () => {
    setRequiredInputs({ focusMode: false });
    expect(
      fixture.nativeElement.querySelector(
        '[data-testid="encouraging-quote-pill"]'
      )
    ).toBeTruthy();
    expect(
      fixture.nativeElement.querySelector('[data-testid="exit-focus-mode-btn"]')
    ).toBeNull();

    setRequiredInputs({ focusMode: true });
    expect(
      fixture.nativeElement.querySelector(
        '[data-testid="encouraging-quote-pill"]'
      )
    ).toBeNull();

    const exitBtn = fixture.nativeElement.querySelector(
      '[data-testid="exit-focus-mode-btn"]'
    ) as HTMLButtonElement;
    expect(exitBtn).toBeTruthy();
    expect(exitBtn.textContent).toContain('Thoát chế độ tập trung (Esc)');

    const exitSpy = vi.fn();
    const sub = component.exitFocusMode.subscribe(exitSpy);
    exitBtn.click();
    expect(exitSpy).toHaveBeenCalledTimes(1);
    sub.unsubscribe();
  });

  it('hiển thị trích dẫn học tập kèm tác giả và đổi sang câu khác khi nhấn vào nút quote', () => {
    setRequiredInputs({ focusMode: false });

    const quoteBtn = fixture.nativeElement.querySelector(
      '[data-testid="encouraging-quote-pill"]'
    ) as HTMLButtonElement;
    expect(quoteBtn).toBeTruthy();
    expect(quoteBtn.tagName).toBe('BUTTON');
    expect(quoteBtn.getAttribute('aria-label')).toBe('Đổi câu truyền cảm hứng khác');

    const initialIndex = component.currentQuoteIndex();
    const initialQuote = STUDY_QUOTES[initialIndex];
    expect(quoteBtn.textContent).toContain(initialQuote.quote);
    expect(quoteBtn.textContent).toContain(`— ${initialQuote.author}`);

    quoteBtn.click();
    fixture.detectChanges();

    const nextIndex = component.currentQuoteIndex();
    const nextQuote = STUDY_QUOTES[nextIndex];
    expect(nextIndex).not.toBe(initialIndex);
    expect(quoteBtn.textContent).toContain(nextQuote.quote);
    expect(quoteBtn.textContent).toContain(`— ${nextQuote.author}`);
  });
});
