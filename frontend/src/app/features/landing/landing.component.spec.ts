import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal, WritableSignal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { LandingComponent } from './landing.component';
import { AuthService } from '../../core/services/auth.service';

describe('LandingComponent', () => {
  let component: LandingComponent;
  let fixture: ComponentFixture<LandingComponent>;
  let mockIsAuthenticated: WritableSignal<boolean>;

  beforeEach(async () => {
    mockIsAuthenticated = signal(false);

    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            isAuthenticated: mockIsAuthenticated,
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LandingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should initialize component with default state', () => {
    expect(component).toBeTruthy();
    expect(component.activeWorkspaceTab()).toBe('dag');
    expect(component.activeScenario()).toBe('thesis');
    expect(component.mobileMenuOpen()).toBe(false);
    expect(component.currentScenario().id).toBe('thesis');
  });

  describe('Workspace Tab Switching (activeWorkspaceTab)', () => {
    it('should switch between dag, schedule, and pomodoro tabs', () => {
      component.setWorkspaceTab('schedule');
      expect(component.activeWorkspaceTab()).toBe('schedule');

      component.setWorkspaceTab('pomodoro');
      expect(component.activeWorkspaceTab()).toBe('pomodoro');

      component.setWorkspaceTab('dag');
      expect(component.activeWorkspaceTab()).toBe('dag');
    });

    it('should update DOM when workspace tab changes', async () => {
      component.setWorkspaceTab('schedule');
      fixture.detectChanges();
      await fixture.whenStable();

      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('Lịch Trình Thích Ứng (Mode B)');

      component.setWorkspaceTab('pomodoro');
      fixture.detectChanges();
      await fixture.whenStable();

      expect(compiled.textContent).toContain('Không Gian Học Sâu Pomodoro Zen');
      expect(compiled.textContent).toContain('18:42');

      component.setWorkspaceTab('dag');
      fixture.detectChanges();
      await fixture.whenStable();

      expect(compiled.textContent).toContain('Giai đoạn 1: Nền tảng Backend & Clean Architecture');
    });
  });

  describe('Scenario Switching (activeScenario)', () => {
    it('should switch between thesis, aws, and ai scenarios', () => {
      component.setScenario('aws');
      expect(component.activeScenario()).toBe('aws');
      expect(component.currentScenario().title).toContain('AWS SAA-C03');

      component.setScenario('ai');
      expect(component.activeScenario()).toBe('ai');
      expect(component.currentScenario().title).toContain('AI Engineer');

      component.setScenario('thesis');
      expect(component.activeScenario()).toBe('thesis');
      expect(component.currentScenario().title).toContain('Khóa luận');
    });

    it('should reflect active scenario milestones in DOM', async () => {
      component.setScenario('aws');
      fixture.detectChanges();
      await fixture.whenStable();

      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('Chinh phục chứng chỉ AWS SAA-C03');
      expect(compiled.textContent).toContain('IAM, VPC & Mạng Đám Mây Toàn Diện');
    });
  });

  describe('CTA Buttons & Authentication State', () => {
    it('should show "Đăng nhập" and "Bắt đầu ngay" when unauthenticated', async () => {
      mockIsAuthenticated.set(false);
      fixture.detectChanges();
      await fixture.whenStable();

      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('Đăng nhập');
      expect(compiled.textContent).toContain('Bắt đầu ngay');
      expect(compiled.textContent).toContain('Tạo lộ trình ngay — Hoàn toàn miễn phí');
      expect(compiled.textContent).not.toContain('Vào Dashboard của bạn');
    });

    it('should show "Vào Dashboard" when authenticated', async () => {
      mockIsAuthenticated.set(true);
      fixture.detectChanges();
      await fixture.whenStable();

      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('Vào Dashboard');
      expect(compiled.textContent).toContain('Vào Dashboard của bạn');
      expect(compiled.textContent).not.toContain('Tạo lộ trình ngay — Hoàn toàn miễn phí');
    });
  });

  describe('Mobile Menu & Navigation', () => {
    it('should toggle and close mobile menu', () => {
      expect(component.mobileMenuOpen()).toBe(false);

      component.toggleMobileMenu();
      expect(component.mobileMenuOpen()).toBe(true);

      component.closeMobileMenu();
      expect(component.mobileMenuOpen()).toBe(false);
    });

    it('should handle scrollTo and close mobile menu', () => {
      const scrollSpy = vi.fn();
      Element.prototype.scrollIntoView = scrollSpy;

      component.toggleMobileMenu();
      expect(component.mobileMenuOpen()).toBe(true);

      const fakeEvent = new Event('click');
      const preventDefaultSpy = vi.spyOn(fakeEvent, 'preventDefault');

      component.scrollTo('capabilities', fakeEvent);

      expect(preventDefaultSpy).toHaveBeenCalled();
      expect(component.mobileMenuOpen()).toBe(false);
      expect(scrollSpy).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });
    });
  });
});
