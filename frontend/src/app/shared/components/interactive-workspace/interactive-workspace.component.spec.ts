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

  it('should initialize with default "dag" tab and render DAG panel', () => {
    expect(component).toBeTruthy();
    expect(component.activeTab()).toBe('dag');
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Giai đoạn 1: Nền tảng Backend & Clean Architecture');
  });

  it('should switch tabs when setTab is called', async () => {
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
    expect(el.textContent).toContain('18:42');
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
