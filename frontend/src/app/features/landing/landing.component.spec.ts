import { ComponentFixture, DeferBlockBehavior, DeferBlockState, TestBed } from '@angular/core/testing';
import { signal, WritableSignal } from '@angular/core';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { LandingComponent } from './landing.component';
import { AuthService } from '../../core/services/auth.service';
import { InteractiveWorkspaceComponent } from '../../shared/components/interactive-workspace/interactive-workspace.component';
import { StudyScenariosComponent } from '../../shared/components/study-scenarios/study-scenarios.component';

interface GlobalWithObserver {
  IntersectionObserver?: unknown;
}

describe('LandingComponent', () => {
  let component: LandingComponent;
  let fixture: ComponentFixture<LandingComponent>;
  let mockIsAuthenticated: WritableSignal<boolean>;

  beforeAll(() => {
    const globalRef = globalThis as unknown as GlobalWithObserver;
    if (typeof globalRef.IntersectionObserver === 'undefined') {
      globalRef.IntersectionObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
      };
    }
  });

  beforeEach(async () => {
    mockIsAuthenticated = signal(false);

    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      deferBlockBehavior: DeferBlockBehavior.Playthrough,
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

    // Render all defer blocks so below-the-fold content is populated in tests
    const deferBlocks = await fixture.getDeferBlocks();
    for (const deferBlock of deferBlocks) {
      await deferBlock.render(DeferBlockState.Complete);
    }
  });

  it('should initialize component with default state', () => {
    expect(component).toBeTruthy();
    expect(component.activeWorkspaceTab()).toBe('dag');
    expect(component.activeScenario()).toBe('thesis');
    expect(component.mobileMenuOpen()).toBe(false);
  });

  describe('Architecture Strip, Bento Grid & Methodology Copy', () => {
    it('should render real FocusFlow architecture & integrations strip without fake partners', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('KIẾN TRÚC ĐIỀU PHỐI & TÍCH HỢP THỰC TẾ CỦA FOCUSFLOW');
      expect(compiled.textContent).toContain('Chu trình 6 bước SRL');
      expect(compiled.textContent).toContain('3-Tier Validation Gate');
      expect(compiled.textContent).toContain('RAG Grounding (pgvector)');
      expect(compiled.textContent).toContain('2-Stage SSE Streaming');
      expect(compiled.textContent).toContain('Google Calendar OAuth2');
      expect(compiled.textContent).toContain('WebCal (.ics RFC 5545)');

      expect(compiled.textContent).not.toContain('ĐH BÁCH KHOA');
      expect(compiled.textContent).not.toContain('Coursera API');
      expect(compiled.textContent).not.toContain('LeetCode Sync');
    });

    it('should render SRS v1.3 Bento capabilities including Human-in-the-Loop Apply', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('Phân rã Lộ trình & Đồ thị DAG có Kiểm chứng RAG');
      expect(compiled.textContent).toContain('DagCycleValidator');
      expect(compiled.textContent).toContain('Xếp lịch Tất định Mode A/B & Duyệt Bản nháp (Human-in-the-Loop)');
      expect(compiled.textContent).toContain('ScheduleProposal (DRAFT)');
      expect(compiled.textContent).toContain('Áp dụng (Apply)');
      expect(compiled.textContent).toContain('Phiên học Pomodoro, MVS & TakeawayGuard (OS-01)');
      expect(compiled.textContent).toContain('Minimum Viable Session (5–15 phút)');
      expect(compiled.textContent).toContain('Hồ sơ Người học 4×3 & Báo cáo Tự điều hòa (Weekly Review)');
      expect(compiled.textContent).toContain('STALLED');
    });

    it('should render 3 separated core entities in Methodology and honest Bottom CTA', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('Roadmap (Học gì & Thứ tự nào)');
      expect(compiled.textContent).toContain('Schedule (Học khi nào — Mode A & Mode B)');
      expect(compiled.textContent).toContain('Learner Model 4×3 (Học như thế nào)');
      expect(compiled.textContent).toContain('Prove Mode');

      expect(compiled.textContent).toContain('30 lượt điều phối AI miễn phí mỗi tháng');
      expect(compiled.textContent).not.toContain('12,000 học giả');
      expect(compiled.textContent).not.toContain('Ebbinghaus');
    });
  });

  describe('Workspace Tab Switching (activeWorkspaceTab)', () => {
    it('should switch between dag, schedule, and pomodoro tabs and sync child component', async () => {
      const workspaceDe = fixture.debugElement.query(By.directive(InteractiveWorkspaceComponent));
      const workspaceCmp = workspaceDe.componentInstance as InteractiveWorkspaceComponent;

      component.setWorkspaceTab('schedule');
      fixture.detectChanges();
      await fixture.whenStable();
      expect(component.activeWorkspaceTab()).toBe('schedule');
      expect(workspaceCmp.activeTab()).toBe('schedule');

      component.setWorkspaceTab('pomodoro');
      fixture.detectChanges();
      await fixture.whenStable();
      expect(component.activeWorkspaceTab()).toBe('pomodoro');
      expect(workspaceCmp.activeTab()).toBe('pomodoro');

      component.setWorkspaceTab('dag');
      fixture.detectChanges();
      await fixture.whenStable();
      expect(component.activeWorkspaceTab()).toBe('dag');
      expect(workspaceCmp.activeTab()).toBe('dag');
    });
  });

  describe('Scenario Switching (activeScenario)', () => {
    it('should switch between thesis, aws, and ai scenarios and reflect in StudyScenariosComponent', async () => {
      const scenariosDe = fixture.debugElement.query(By.directive(StudyScenariosComponent));
      const scenariosCmp = scenariosDe.componentInstance as StudyScenariosComponent;

      component.setScenario('aws');
      fixture.detectChanges();
      await fixture.whenStable();
      expect(component.activeScenario()).toBe('aws');
      expect(scenariosCmp.activeScenario()).toBe('aws');
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('Chinh phục chứng chỉ AWS SAA-C03');
      expect(compiled.textContent).toContain('IAM, VPC & Mạng Đám Mây Toàn Diện');

      component.setScenario('ai');
      fixture.detectChanges();
      await fixture.whenStable();
      expect(component.activeScenario()).toBe('ai');
      expect(scenariosCmp.activeScenario()).toBe('ai');
      expect(compiled.textContent).toContain('Chuyển dịch năng lực AI Engineer');

      component.setScenario('thesis');
      fixture.detectChanges();
      await fixture.whenStable();
      expect(component.activeScenario()).toBe('thesis');
      expect(scenariosCmp.activeScenario()).toBe('thesis');
      expect(compiled.textContent).toContain('SRS & Đặc tả Kiến trúc');
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
