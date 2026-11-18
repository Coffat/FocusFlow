import { ComponentFixture, TestBed } from '@angular/core/testing';
import { InteractiveWorkspaceComponent } from './interactive-workspace.component';

describe('InteractiveWorkspaceComponent', () => {
  let component: InteractiveWorkspaceComponent;
  let fixture: ComponentFixture<InteractiveWorkspaceComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InteractiveWorkspaceComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(InteractiveWorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    component.pauseTimer();
  });

  it('should initialize with default "dag" tab and render DAG panel', () => {
    expect(component).toBeTruthy();
    expect(component.activeTab()).toBe('dag');
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Giai đoạn 1: Nền tảng Backend & Clean Architecture');
  });

  it('should switch tabs when setTab is called and render Pomodoro with 25:00 timer', async () => {
    component.setTab('schedule');
    fixture.detectChanges();
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(component.activeTab()).toBe('schedule');
    expect(el.textContent).toContain('Lịch Trình Thích Ứng (Mode B)');

    component.setTab('pomodoro');
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.activeTab()).toBe('pomodoro');
    expect(el.textContent).toContain('Không Gian Học Sâu Pomodoro Zen');
    expect(el.textContent).toContain('25:00');
  });

  it('should start, pause, and reset countdown timer', () => {
    vi.useFakeTimers();
    expect(component.isTimerRunning()).toBe(false);
    expect(component.formattedTime()).toBe('25:00');

    component.toggleTimer();
    expect(component.isTimerRunning()).toBe(true);

    vi.advanceTimersByTime(3000);
    expect(component.timerSeconds()).toBe(1497);
    expect(component.formattedTime()).toBe('24:57');

    component.toggleTimer();
    expect(component.isTimerRunning()).toBe(false);

    vi.advanceTimersByTime(2000);
    expect(component.timerSeconds()).toBe(1497);

    component.resetTimer();
    expect(component.isTimerRunning()).toBe(false);
    expect(component.timerSeconds()).toBe(1500);
    expect(component.formattedTime()).toBe('25:00');

    vi.useRealTimers();
  });

  it('should update scratchpad notes on input', () => {
    component.setTab('pomodoro');
    fixture.detectChanges();

    const customText = 'Nghiên cứu lại Transaction Isolation Level trong PostgreSQL';
    const fakeEvent = {
      target: { value: customText },
    } as unknown as Event;

    component.onScratchpadInput(fakeEvent);
    expect(component.scratchpadNote()).toBe(customText);
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
