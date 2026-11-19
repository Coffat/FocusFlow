import { ComponentFixture, TestBed } from '@angular/core/testing';
import { InteractiveWorkspaceComponent } from './interactive-workspace.component';

describe('InteractiveWorkspaceComponent', () => {
  let component: InteractiveWorkspaceComponent;
  let fixture: ComponentFixture<InteractiveWorkspaceComponent>;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-18T12:00:00Z'));

    await TestBed.configureTestingModule({
      imports: [InteractiveWorkspaceComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(InteractiveWorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    component.pauseTimer();
    fixture.destroy();
    vi.useRealTimers();
  });

  it('should initialize with default "dag" tab, real FocusFlow Topbar/Footer chrome, and fixed-height viewport', () => {
    expect(component).toBeTruthy();
    expect(component.activeTab()).toBe('dag');

    const el = fixture.nativeElement as HTMLElement;
    const text = el.textContent ?? '';
    expect(text).toContain('Plan Smarter • Do Better');
    expect(text).toContain('Roadmap Hub');
    expect(text).toContain('Thời khóa biểu');
    expect(text).toContain('Vào học');
    expect(text).toContain('AI Quota: 24/30 lượt');
    expect(text).toContain('3-Tier Gate: Passed');
    expect(text).toContain('Giai đoạn 1: Nền tảng Modular Monolith & Domain');
    expect(text).toContain('FocusFlow AI Harness • 2-Stage SSE');
    expect(text).toContain('WCAG 2.2 AA');
    expect(text).not.toContain('Attio');
    expect(el.querySelector('aside')).toBeNull();
    expect(el.querySelector('.lg\\:h-\\[468px\\]')).toBeTruthy();

    component.setTab('schedule');
    fixture.detectChanges();
    expect(el.querySelector('.lg\\:h-\\[468px\\]')).toBeTruthy();

    component.setTab('pomodoro');
    fixture.detectChanges();
    expect(el.querySelector('.lg\\:h-\\[468px\\]')).toBeTruthy();
  });

  it('should select DAG nodes and update effort, DagCycleValidator, RAG source, and 3-Tier Gate details', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(component.selectedDagNodeId()).toBe('hexagonal');
    expect(el.textContent).toContain('Architecture ADR-002 & Clean Architecture Notes');

    component.selectDagNode('indexing');
    fixture.detectChanges();
    expect(component.selectedDagNodeId()).toBe('indexing');
    expect(el.textContent).toContain('estimated_effort: 60 phút');
    expect(el.textContent).toContain('rag_chunk #104');

    component.selectDagNode('outbox');
    fixture.detectChanges();
    expect(component.selectedDagNodeId()).toBe('outbox');
    expect(el.textContent).toContain('Taskiq Outbox & Idempotent Consumer');
    expect(el.textContent).toContain('rag_chunk #309');
    expect(el.textContent).toContain('BLOCKED');
  });

  it('should switch to "schedule" tab, show Soft Overflow notice, and apply/reset proposal explicitly', () => {
    component.setTab('schedule');
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(component.activeTab()).toBe('schedule');
    expect(component.proposalApplied()).toBe(false);
    expect(el.textContent).toContain('Đề xuất Lịch học (Mode B)');
    expect(el.textContent).toContain('T2–T6: 19:30–21:30 • T7: 09:00–11:30');
    expect(el.textContent).toContain('ScheduleProposal (DRAFT)');
    expect(el.textContent).toContain('Soft Overflow: +15 phút ở block cuối ngày');
    expect(el.textContent).toContain('BUSR-04');

    component.applyProposal();
    fixture.detectChanges();

    expect(component.proposalApplied()).toBe(true);
    expect(el.textContent).toContain('OfficialSchedule (Đã áp dụng)');

    component.resetProposal();
    fixture.detectChanges();

    expect(component.proposalApplied()).toBe(false);
    expect(el.textContent).toContain('ScheduleProposal (DRAFT)');
  });

  it('should switch to "pomodoro" tab and toggle between Pomodoro 25:00 and MVS 15:00 modes', () => {
    component.setTab('pomodoro');
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(component.activeTab()).toBe('pomodoro');
    expect(component.isMvsMode()).toBe(false);
    expect(component.formattedTime()).toBe('25:00');
    expect(el.textContent).toContain('Phiên học Focus & TakeawayGuard');
    expect(el.textContent).toContain('25:00');

    component.setMvsMode(true);
    fixture.detectChanges();
    expect(component.isMvsMode()).toBe(true);
    expect(component.formattedTime()).toBe('15:00');
    expect(el.textContent).toContain('15:00');

    component.setMvsMode(false);
    fixture.detectChanges();
    expect(component.isMvsMode()).toBe(false);
    expect(component.formattedTime()).toBe('25:00');
  });

  it('should run timestamp-based countdown using Date.now() on start, pause, and reset', () => {
    component.setTab('pomodoro');
    fixture.detectChanges();

    expect(component.isTimerRunning()).toBe(false);
    expect(component.formattedTime()).toBe('25:00');

    component.toggleTimer();
    expect(component.isTimerRunning()).toBe(true);

    // Advance fake timers by 3 seconds
    vi.advanceTimersByTime(3000);
    expect(component.timerSeconds()).toBe(1497);
    expect(component.formattedTime()).toBe('24:57');

    // Simulate background tab throttling where wall-clock jumps forward by 60s before next poll
    vi.setSystemTime(Date.now() + 60_000);
    vi.advanceTimersByTime(250);
    expect(component.timerSeconds()).toBe(1437);
    expect(component.formattedTime()).toBe('23:57');

    component.toggleTimer();
    expect(component.isTimerRunning()).toBe(false);

    vi.advanceTimersByTime(5000);
    expect(component.timerSeconds()).toBe(1437);

    component.resetTimer();
    expect(component.isTimerRunning()).toBe(false);
    expect(component.timerSeconds()).toBe(1500);
    expect(component.formattedTime()).toBe('25:00');
  });

  it('should enforce TakeawayGuard OS-01 (< 20 vs >= 20 chars) before completing a session', () => {
    component.setTab('pomodoro');
    fixture.detectChanges();

    const shortNote = 'Ghi chú quá ngắn';
    component.onScratchpadInput({ target: { value: shortNote } } as unknown as Event);
    fixture.detectChanges();

    expect(component.takeawayLength()).toBe(shortNote.length);
    expect(component.takeawayLength()).toBeLessThan(20);
    expect(component.canCompleteSession()).toBe(false);

    const completeBtn = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('button')
    ).find((btn) => btn.textContent?.includes('Hoàn thành phiên học'));
    expect(completeBtn?.disabled).toBe(true);

    component.completeSession();
    expect(component.sessionCompleted()).toBe(false);

    const validNote = 'Nghiên cứu lại Transaction Isolation Level trong PostgreSQL 16';
    component.onScratchpadInput({ target: { value: validNote } } as unknown as Event);
    fixture.detectChanges();

    expect(component.takeawayLength()).toBe(validNote.length);
    expect(component.canCompleteSession()).toBe(true);
    expect(completeBtn?.disabled).toBe(false);

    component.completeSession();
    fixture.detectChanges();

    expect(component.sessionCompleted()).toBe(true);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'Phiên học đã hoàn thành & lưu Key Takeaways!'
    );
  });

  it('should auto-play tabs every 6000ms and pause when setTab is called manually', () => {
    expect(component.activeTab()).toBe('dag');
    expect(component.isAutoPlayPaused()).toBe(false);

    vi.advanceTimersByTime(6000);
    fixture.detectChanges();
    expect(component.activeTab()).toBe('schedule');

    vi.advanceTimersByTime(6000);
    fixture.detectChanges();
    expect(component.activeTab()).toBe('pomodoro');

    vi.advanceTimersByTime(6000);
    fixture.detectChanges();
    expect(component.activeTab()).toBe('dag');

    // Manual setTab pauses auto-play
    component.setTab('schedule');
    fixture.detectChanges();
    expect(component.activeTab()).toBe('schedule');
    expect(component.isAutoPlayPaused()).toBe(true);

    vi.advanceTimersByTime(12000);
    fixture.detectChanges();
    expect(component.activeTab()).toBe('schedule');

    // Toggle auto-play back on
    component.toggleAutoPlay();
    expect(component.isAutoPlayPaused()).toBe(false);

    vi.advanceTimersByTime(6000);
    fixture.detectChanges();
    expect(component.activeTab()).toBe('pomodoro');
  });

  it('should pause auto-play while hovering and resume on mouseleave if not manually paused', () => {
    expect(component.activeTab()).toBe('dag');

    component.onShellMouseEnter();
    expect(component.isEffectiveAutoPlayPaused()).toBe(true);

    vi.advanceTimersByTime(6000);
    expect(component.activeTab()).toBe('dag');

    component.onShellMouseLeave();
    expect(component.isEffectiveAutoPlayPaused()).toBe(false);

    vi.advanceTimersByTime(6000);
    expect(component.activeTab()).toBe('schedule');
  });

  it('should trigger smooth scroll on anchor links', () => {
    const scrollSpy = vi.fn();
    Element.prototype.scrollIntoView = scrollSpy;

    const fakeEvent = new Event('click');
    const preventSpy = vi.spyOn(fakeEvent, 'preventDefault');

    component.scrollTo('capabilities', fakeEvent);

    expect(preventSpy).toHaveBeenCalled();
  });
});
