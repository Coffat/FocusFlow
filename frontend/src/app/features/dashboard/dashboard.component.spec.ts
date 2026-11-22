import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router, ActivatedRoute } from '@angular/router';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest';
import { DashboardComponent } from './dashboard.component';
import { DashboardService, EMPTY_DASHBOARD_SUMMARY } from './services/dashboard.service';
import { AvailabilityService } from '../../core/services/availability.service';
import { CalendarIntegrationService } from '../../core/services/calendar-integration.service';
import { RoadmapWizardHostComponent } from '../roadmaps/components/dialogs/roadmap-wizard-host/roadmap-wizard-host.component';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;
  let router: Router;
  let service: DashboardService;
  let mockCalendarService: {
    connection: ReturnType<typeof signal<any>>;
    isConnected: ReturnType<typeof signal<boolean>>;
    isLoading: ReturnType<typeof signal<boolean>>;
    loadStatus: Mock<() => any>;
  };
  let mockAvailabilityService: {
    profile: ReturnType<typeof signal<any>>;
    hasConfiguredAvailability: Mock<() => boolean>;
    loadMyAvailability: Mock<(cb?: any) => void>;
    checkPrerequisites: Mock<(cb: (ready: boolean) => void) => void>;
  };

  beforeEach(async () => {
    mockCalendarService = {
      connection: signal({ connected: false, provider: 'GOOGLE', sync_status: 'IDLE' }),
      isConnected: signal(false),
      isLoading: signal(false),
      loadStatus: vi.fn().mockReturnValue(of({ connected: false, provider: 'GOOGLE', sync_status: 'IDLE' })),
    };

    mockAvailabilityService = {
      profile: signal({ id: 'avail-1', user_id: 'usr-1' }),
      hasConfiguredAvailability: vi.fn().mockReturnValue(true),
      loadMyAvailability: vi.fn((cb) => cb?.({ id: 'avail-1' })),
      checkPrerequisites: vi.fn((cb: (ready: boolean) => void) => {
        if (!mockAvailabilityService.profile()) {
          mockAvailabilityService.loadMyAvailability();
        }
        const ready = mockCalendarService.isConnected() || mockAvailabilityService.hasConfiguredAvailability();
        cb(ready);
      }),
    };

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AvailabilityService, useValue: mockAvailabilityService },
        { provide: CalendarIntegrationService, useValue: mockCalendarService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    service = TestBed.inject(DashboardService);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fixture.detectChanges();
  });

  it('khởi tạo thành công và hiển thị giao diện dashboard', () => {
    expect(component).toBeTruthy();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.dashboard-page-container')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="dashboard-create-roadmap-btn"]')).toBeTruthy();
  });

  it('hiển thị KPI grid và Weekly grid khi có lộ trình học', () => {
    service.summary.set({
      ...service.summary(),
      activeRoadmaps: [
        {
          id: 'rm-1',
          title: 'IELTS Academic',
          category: 'English',
          progressPercentage: 40,
          totalTasks: 20,
          completedTasks: 8,
          nextTaskTitle: 'Next',
          deadline: '2026-12-31',
        },
      ],
    });
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-dashboard-kpi-grid')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-weekly-grid')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-empty-state')).toBeFalsy();
  });

  it('hiển thị empty state khi ở trạng thái new-user và mở Wizard Dialog khi bấm Tạo Lộ trình Học tập Đầu tiên với AI', () => {
    service.setState('new-user');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-dashboard-empty-state')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-kpi-grid')).toBeFalsy();

    const emptyCtaBtn = compiled.querySelector(
      '[data-testid="empty-state-cta-btn"]'
    ) as HTMLButtonElement;
    expect(emptyCtaBtn).toBeTruthy();
    emptyCtaBtn.click();
    fixture.detectChanges();

    expect(component.wizardOpen()).toBe(true);
    expect(component.wizardStep()).toBe(1);
  });

  it('không mở wizard khi bấm phím C (đã loại bỏ phím tắt C theo yêu cầu UX)', () => {
    expect(component.wizardOpen()).toBe(false);
    const event = new KeyboardEvent('keydown', { key: 'c' });
    window.dispatchEvent(event);
    expect(component.wizardOpen()).toBe(false);
  });

  it('điều hướng tới /workspace khi bấm phím Space ngoài ô input', () => {
    const event = new KeyboardEvent('keydown', { code: 'Space' });
    window.dispatchEvent(event);
    expect(router.navigate).toHaveBeenCalledWith(['/workspace']);
  });

  it('bỏ qua phím tắt khi người dùng đang gõ trong ô input', () => {
    vi.clearAllMocks();
    const inputEl = document.createElement('input');
    document.body.appendChild(inputEl);
    inputEl.focus();

    const event = new KeyboardEvent('keydown', { key: 'c', bubbles: true });
    inputEl.dispatchEvent(event);

    expect(component.wizardOpen()).toBe(false);
    document.body.removeChild(inputEl);
  });

  describe('Kiểm tra tiền điều kiện Thời gian rảnh & Auto-open', () => {
    it('bật PrerequisiteAvailabilityDialogComponent khi chưa có thời gian rảnh và bấm Tạo lộ trình mới', () => {
      mockAvailabilityService.hasConfiguredAvailability.mockReturnValue(false);

      component.openCreateWizard(1);

      expect(component.prerequisiteDialogOpen()).toBe(true);
      expect(component.wizardOpen()).toBe(false);
    });

    it('bật PrerequisiteAvailabilityDialogComponent khi chưa có thời gian rảnh và chọn Starter Template', () => {
      mockAvailabilityService.hasConfiguredAvailability.mockReturnValue(false);

      component.onSelectStarterTemplate({
        id: 'tpl-1',
        title: 'Python Core',
        subtitle: 'From zero to hero',
        categoryTag: 'Backend',
        weeksCount: 8,
        tasksCount: 20,
        tags: ['Python'],
        hoursPerWeek: 10,
        knowledgeLevel: 'BEGINNER',
      });

      expect(component.prerequisiteDialogOpen()).toBe(true);
      expect(component.wizardOpen()).toBe(false);
    });

    it('gọi loadMyAvailability nếu profile() là null trước khi kiểm tra tiền điều kiện', () => {
      mockAvailabilityService.profile.set(null);
      mockAvailabilityService.hasConfiguredAvailability.mockReturnValue(false);

      component.openCreateWizard(1);

      expect(mockAvailabilityService.loadMyAvailability).toHaveBeenCalled();
      expect(component.prerequisiteDialogOpen()).toBe(true);
      expect(component.wizardOpen()).toBe(false);
    });

    it('tự động mở Wizard và dọn query param khi queryParam có autoOpen=true', () => {
      const route = TestBed.inject(ActivatedRoute);
      const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

      vi.spyOn(route.snapshot.queryParamMap, 'get').mockImplementation((k: string) => {
        if (k === 'autoOpen') return 'true';
        return null;
      });
      route.snapshot.queryParams = { autoOpen: 'true' };

      mockAvailabilityService.hasConfiguredAvailability.mockReturnValue(true);

      component.ngOnInit();

      expect(component.wizardOpen()).toBe(true);
      expect(navigateSpy).toHaveBeenCalledWith([], {
        relativeTo: route,
        queryParams: {},
        replaceUrl: true,
      });
    });

    it('khi Google Calendar isConnected === true (dù chưa có profile lịch rảnh), checkPrerequisites trả về true và mở thẳng Wizard tạo lộ trình', () => {
      mockAvailabilityService.profile.set(null);
      mockCalendarService.isConnected.set(true);
      mockAvailabilityService.hasConfiguredAvailability.mockReturnValue(false);

      component.openCreateWizard(1);

      expect(component.prerequisiteDialogOpen()).toBe(false);
      expect(component.wizardOpen()).toBe(true);
    });
  });

  describe('FE-SYNC-02: Đồng bộ Dashboard sau khi áp dụng lộ trình từ Roadmap Wizard', () => {
    it('phát roadmapApplied từ app-roadmap-wizard-host sẽ đóng wizard, chuyển trạng thái khỏi new-user và gọi loadSummary()', () => {
      service.setState('new-user');
      component.wizardOpen.set(true);
      fixture.detectChanges();

      const loadSummarySpy = vi
        .spyOn(service, 'loadSummary')
        .mockReturnValue(of(EMPTY_DASHBOARD_SUMMARY));

      const wizardDebugEl = fixture.debugElement.query(By.directive(RoadmapWizardHostComponent));
      expect(wizardDebugEl).toBeTruthy();
      const wizardHost = wizardDebugEl.componentInstance as RoadmapWizardHostComponent;

      wizardHost.roadmapApplied.emit('rm-new-1');
      fixture.detectChanges();

      expect(component.wizardOpen()).toBe(false);
      expect(component.currentState()).toBe('normal');
      expect(loadSummarySpy).toHaveBeenCalledTimes(1);
    });

    it('chỉ phát closeWizard (hủy hoặc apply thất bại) chỉ đóng wizard và KHÔNG gọi lại loadSummary()', () => {
      component.wizardOpen.set(true);
      fixture.detectChanges();

      const loadSummarySpy = vi
        .spyOn(service, 'loadSummary')
        .mockReturnValue(of(EMPTY_DASHBOARD_SUMMARY));

      const wizardDebugEl = fixture.debugElement.query(By.directive(RoadmapWizardHostComponent));
      const wizardHost = wizardDebugEl.componentInstance as RoadmapWizardHostComponent;

      wizardHost.closeWizard.emit();
      fixture.detectChanges();

      expect(component.wizardOpen()).toBe(false);
      expect(loadSummarySpy).not.toHaveBeenCalled();
    });
  });

  describe('FE-SYNC-05: Human-in-the-loop Adaptation Workflow trên Dashboard', () => {
    it('onConfirmAdaptation() gọi POST /api/v1/roadmaps/{id}/reoptimize-schedule tạo bản nháp DRAFT và điều hướng tới /roadmaps/{id}', () => {
      const httpMock = TestBed.inject(HttpTestingController);
      httpMock.match('/api/v1/auth/me').forEach((req) => req.flush({}));
      httpMock.match('/api/v1/evaluation/dashboard-summary').forEach((req) => req.flush({}));

      service.summary.set({
        ...EMPTY_DASHBOARD_SUMMARY,
        activeRoadmaps: [
          {
            id: 'rm-adapt-1',
            title: 'Lộ trình FastAPI Production',
            category: 'Backend',
            progressPercentage: 50,
            totalTasks: 10,
            completedTasks: 5,
            nextTaskTitle: 'Task 6',
            deadline: '2026-12-20',
          },
        ],
        adaptationStatus: {
          hasDominoShift: true,
          affectedTasksCount: 3,
          rescheduleReason: 'Trễ 3 phiên',
          needsAttention: true,
          alertMessage: 'Có 3 phiên cần tái phân bổ',
        },
      });
      component.openAdaptationModal();
      fixture.detectChanges();

      expect(component.adaptationContext()).toEqual({
        roadmapId: 'rm-adapt-1',
        roadmapTitle: 'Lộ trình FastAPI Production',
        missedSessionsCount: 3,
        currentDeadline: '2026-12-20',
      });

      component.onConfirmAdaptation({
        strategy: 'DOMINO_SHIFT',
        roadmapId: 'rm-adapt-1',
      });

      const req = httpMock.expectOne('/api/v1/roadmaps/rm-adapt-1/reoptimize-schedule');
      expect(req.request.method).toBe('POST');
      expect(req.request.withCredentials).toBe(true);
      req.flush({
        id: 'prop-draft-1',
        roadmap_id: 'rm-adapt-1',
        status: 'DRAFT',
        tasks: [],
        dependencies: [],
        is_valid: true,
      });

      expect(component.adaptationModalOpen()).toBe(false);
      expect(component.adaptationError()).toBeNull();
      expect(router.navigate).toHaveBeenCalledWith(['/roadmaps', 'rm-adapt-1']);
      httpMock.verify();
    });

    it('khi POST reoptimize-schedule thất bại, giữ modal mở, hiển thị lỗi và KHÔNG điều hướng', () => {
      const httpMock = TestBed.inject(HttpTestingController);
      httpMock.match('/api/v1/auth/me').forEach((req) => req.flush({}));
      httpMock.match('/api/v1/evaluation/dashboard-summary').forEach((req) => req.flush({}));
      vi.clearAllMocks();

      component.openAdaptationModal();
      component.onConfirmAdaptation({
        strategy: 'DOMINO_SHIFT',
        roadmapId: 'rm-adapt-err',
      });

      const req = httpMock.expectOne('/api/v1/roadmaps/rm-adapt-err/reoptimize-schedule');
      req.flush(
        { message: 'Không đủ khung giờ rảnh để tái tối ưu.' },
        { status: 409, statusText: 'Conflict' }
      );
      fixture.detectChanges();

      expect(component.adaptationModalOpen()).toBe(true);
      expect(component.adaptationError()).toContain('Không đủ khung giờ rảnh');
      expect(router.navigate).not.toHaveBeenCalled();

      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('[data-testid="adaptation-error-banner"]')?.textContent).toContain(
        'Không đủ khung giờ rảnh'
      );
      httpMock.verify();
    });
  });
});
