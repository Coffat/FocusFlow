import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router, ActivatedRoute } from '@angular/router';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ConfirmationService, MessageService } from 'primeng/api';
import { RoadmapsHubComponent } from './roadmaps-hub.component';
import { RoadmapService } from '../../services/roadmap.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AvailabilityService } from '../../../../core/services/availability.service';
import { CalendarIntegrationService } from '../../../../core/services/calendar-integration.service';
import { RoadmapResponse } from '../../models/roadmap.model';
import { RoadmapWizardHostComponent } from '../dialogs/roadmap-wizard-host/roadmap-wizard-host.component';

describe('RoadmapsHubComponent', () => {
  let component: RoadmapsHubComponent;
  let fixture: ComponentFixture<RoadmapsHubComponent>;
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
  let mockRoadmapService: {
    roadmaps: ReturnType<typeof signal<RoadmapResponse[]>>;
    loading: ReturnType<typeof signal<boolean>>;
    loadRoadmaps: ReturnType<typeof vi.fn>;
    pauseRoadmap: ReturnType<typeof vi.fn>;
    resumeRoadmap: ReturnType<typeof vi.fn>;
    archiveRoadmap: ReturnType<typeof vi.fn>;
  };

  const mockRoadmaps: RoadmapResponse[] = [
    {
      id: 'rm-1',
      user_id: 'usr-1',
      goal_id: 'goal-1',
      title: 'Master FastAPI & Hexagonal Architecture',
      description: 'Chinh phục kiến trúc phân lớp Ports & Adapters.',
      status: 'ACTIVE',
      start_date: '2026-10-01',
      target_date: '2026-12-31',
      created_at: '2026-10-01T00:00:00Z',
      updated_at: '2026-10-15T00:00:00Z',
    },
    {
      id: 'rm-2',
      user_id: 'usr-1',
      goal_id: 'goal-2',
      title: 'AWS Certified Solutions Architect',
      description: 'Nắm vững VPC, IAM, EC2, S3, RDS.',
      status: 'PAUSED',
      start_date: '2026-08-01',
      target_date: '2026-11-30',
      created_at: '2026-08-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
    },
    {
      id: 'rm-3',
      user_id: 'usr-1',
      goal_id: 'goal-3',
      title: 'Frontend Modernization với Angular 19',
      description: 'Xây dựng Single Page App với Standalone.',
      status: 'COMPLETED',
      start_date: '2026-06-01',
      target_date: '2026-09-10',
      created_at: '2026-06-01T00:00:00Z',
      updated_at: '2026-09-10T00:00:00Z',
    },
  ];

  let roadmapsSignal: ReturnType<typeof signal<RoadmapResponse[]>>;
  let loadingSignal: ReturnType<typeof signal<boolean>>;

  beforeEach(async () => {
    roadmapsSignal = signal<RoadmapResponse[]>(mockRoadmaps);
    loadingSignal = signal<boolean>(false);

    mockRoadmapService = {
      roadmaps: roadmapsSignal,
      loading: loadingSignal,
      loadRoadmaps: vi.fn(),
      pauseRoadmap: vi.fn().mockReturnValue(of({ id: 'rm-1', status: 'PAUSED' })),
      resumeRoadmap: vi.fn().mockReturnValue(of({ id: 'rm-2', status: 'ACTIVE' })),
      archiveRoadmap: vi.fn(),
    };

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

    const mockAuthService = {
      currentUser: signal({
        id: 'usr-1',
        email: 'hoang@focusflow.ai',
        fullName: 'Minh Hoàng',
        role: 'Sinh viên SE',
        tier: 'PRO',
        createdAt: '2026-01-01',
      }),
    };

    await TestBed.configureTestingModule({
      imports: [RoadmapsHubComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        ConfirmationService,
        MessageService,
        { provide: RoadmapService, useValue: mockRoadmapService },
        { provide: AuthService, useValue: mockAuthService },
        { provide: AvailabilityService, useValue: mockAvailabilityService },
        { provide: CalendarIntegrationService, useValue: mockCalendarService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RoadmapsHubComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('nên khởi tạo thành công component', () => {
    expect(component).toBeTruthy();
    expect(component.totalCount()).toBe(3);
    expect(component.activeCount()).toBe(1);
    expect(component.pausedCount()).toBe(1);
    expect(component.completedCount()).toBe(1);
  });

  it('nên tính toán chữ cái đầu của người dùng chính xác', () => {
    expect(component.userInitials()).toBe('MH');
  });

  it('nên lọc lộ trình theo trạng thái đúng', () => {
    component.setFilter('ACTIVE');
    fixture.detectChanges();
    expect(component.filteredRoadmaps().length).toBe(1);
    expect(component.filteredRoadmaps()[0].id).toBe('rm-1');

    component.setFilter('PAUSED');
    fixture.detectChanges();
    expect(component.filteredRoadmaps().length).toBe(1);
    expect(component.filteredRoadmaps()[0].id).toBe('rm-2');

    component.setFilter('COMPLETED');
    fixture.detectChanges();
    expect(component.filteredRoadmaps().length).toBe(1);
    expect(component.filteredRoadmaps()[0].id).toBe('rm-3');

    component.setFilter('ALL');
    fixture.detectChanges();
    expect(component.filteredRoadmaps().length).toBe(3);
  });

  it('nên lọc theo từ khóa tìm kiếm chính xác', () => {
    component.onSearchChange('FastAPI');
    fixture.detectChanges();
    expect(component.filteredRoadmaps().length).toBe(1);
    expect(component.filteredRoadmaps()[0].title).toContain('FastAPI');

    component.onSearchChange('Không tồn tại');
    fixture.detectChanges();
    expect(component.filteredRoadmaps().length).toBe(0);
  });

  it('nên chuyển đổi giữa dạng Grid và List', () => {
    expect(component.viewMode()).toBe('grid');
    component.setViewMode('list');
    expect(component.viewMode()).toBe('list');
  });

  it('nên hiển thị Empty State cùng 3 starter templates khi không có lộ trình nào', () => {
    roadmapsSignal.set([]);
    fixture.detectChanges();

    expect(component.totalCount()).toBe(0);
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Chưa có lộ trình học tập nào');
    expect(compiled.textContent).toContain('FastAPI & Microservices');
    expect(compiled.textContent).toContain('AWS Solutions Architect');
    expect(compiled.textContent).toContain('IELTS Academic Band 7.5');
  });

  it('nên mở RoadmapWizardHostComponent ở Bước 1 khi bấm nút Khởi tạo Lộ trình Mới với AI', () => {
    expect(component.wizardOpen()).toBe(false);
    component.openCreateWizard(1);
    expect(component.wizardOpen()).toBe(true);
    expect(component.wizardStep()).toBe(1);
  });

  it('nên mở RoadmapWizardHostComponent điền sẵn dữ liệu khi chọn Starter Template', () => {
    component.onSelectTemplate({
      id: 'aws-solutions-architect',
      title: 'AWS Solutions Architect',
      subtitle: 'Cloud',
      categoryTag: 'Cloud Arch',
      weeksCount: 8,
      tasksCount: 56,
      knowledgeLevel: 'BEGINNER',
      hoursPerWeek: 8,
      tags: ['AWS'],
    });

    expect(component.wizardOpen()).toBe(true);
    expect(component.wizardInitialTitle()).toBe('AWS Solutions Architect');
    expect(component.wizardInitialLevel()).toBe('BEGINNER');
    expect(component.wizardInitialWeeklyHours()).toBe(8);
  });

  it('nên trích xuất tags phù hợp từ tiêu đề lộ trình', () => {
    const tags = component.getTags(mockRoadmaps[0]);
    expect(tags).toContain('Backend');
    expect(tags).toContain('Python');
  });

  it('nên kích hoạt ConfirmationService khi tạm dừng lộ trình', () => {
    const confirmationService = TestBed.inject(ConfirmationService);
    const confirmSpy = vi.spyOn(confirmationService, 'confirm');
    component.onPauseRoadmap('rm-1');
    expect(confirmSpy).toHaveBeenCalled();
  });

  it('nên mở AdaptationModalDialogComponent (SCR-08) khi bấm kích hoạt lại / tái cân bằng Domino Shift', () => {
    expect(component.adaptationModalOpen()).toBe(false);
    component.onResumeRoadmap('rm-2');
    expect(component.adaptationModalOpen()).toBe(true);
    expect(component.adaptationRoadmapId()).toBe('rm-2');
    expect(component.adaptationRoadmapTitle()).toBe('AWS Certified Solutions Architect');
  });

  it('nên kích hoạt ConfirmationService khi lưu trữ lộ trình', () => {
    const confirmationService = TestBed.inject(ConfirmationService);
    const confirmSpy = vi.spyOn(confirmationService, 'confirm');
    component.onArchiveRoadmap('rm-1');
    expect(confirmSpy).toHaveBeenCalled();
  });

  describe('Kiểm tra tiền điều kiện Thời gian rảnh & Auto-open', () => {
    it('bật PrerequisiteAvailabilityDialogComponent khi chưa có thời gian rảnh và bấm Tạo lộ trình mới', () => {
      mockAvailabilityService.hasConfiguredAvailability.mockReturnValue(false);

      component.openCreateWizard(1);
      fixture.detectChanges();

      expect(component.prerequisiteDialogOpen()).toBe(true);
      expect(component.wizardOpen()).toBe(false);
    });

    it('bật PrerequisiteAvailabilityDialogComponent khi chưa có thời gian rảnh và chọn Starter Template', () => {
      mockAvailabilityService.hasConfiguredAvailability.mockReturnValue(false);

      component.onSelectTemplate({
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
      fixture.detectChanges();

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

    it('mở Wizard trực tiếp khi đã cấu hình thời gian rảnh hợp lệ', () => {
      mockAvailabilityService.profile.set({ id: 'avail-1' });
      mockAvailabilityService.hasConfiguredAvailability.mockReturnValue(true);

      component.openCreateWizard(1);

      expect(component.prerequisiteDialogOpen()).toBe(false);
      expect(component.wizardOpen()).toBe(true);
      expect(component.wizardStep()).toBe(1);
    });

    it('tự động mở Wizard và dọn query param khi queryParam có autoOpen=true', () => {
      const route = TestBed.inject(ActivatedRoute);
      const router = TestBed.inject(Router);
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
      fixture.detectChanges();

      expect(component.prerequisiteDialogOpen()).toBe(false);
      expect(component.wizardOpen()).toBe(true);
      expect(component.wizardStep()).toBe(1);
    });
  });

  describe('FE-API-03: Xử lý lỗi HTTP trung thực cho Resume, Pause và Archive', () => {
    it('executeResume gặp lỗi HTTP -> giữ nguyên trạng thái PAUSED, hiện toast lỗi và không hiện toast thành công', () => {
      const messageService = TestBed.inject(MessageService);
      const addSpy = vi.spyOn(messageService, 'add');

      mockRoadmapService.resumeRoadmap.mockReturnValue(
        throwError(
          () =>
            new HttpErrorResponse({
              status: 500,
              statusText: 'Internal Server Error',
              error: { message: 'Lỗi máy chủ khi kích hoạt lại lộ trình.' },
            })
        )
      );

      component.onConfirmAdaptation({
        roadmapId: 'rm-2',
        strategy: 'DOMINO_SHIFT',
      });

      const target = roadmapsSignal().find(r => r.id === 'rm-2');
      expect(target?.status).toBe('PAUSED');
      expect(addSpy).toHaveBeenCalledTimes(1);
      expect(addSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 'error',
          summary: 'Kích hoạt lại thất bại',
          detail: 'Lỗi máy chủ khi kích hoạt lại lộ trình.',
        })
      );
      expect(addSpy).not.toHaveBeenCalledWith(
        expect.objectContaining({ severity: 'success' })
      );
    });

    it('executePause gặp lỗi HTTP -> giữ nguyên trạng thái ACTIVE, hiện toast lỗi và không hiện toast thành công/cảnh báo', () => {
      const confirmationService = TestBed.inject(ConfirmationService);
      const messageService = TestBed.inject(MessageService);
      const addSpy = vi.spyOn(messageService, 'add');

      vi.spyOn(confirmationService, 'confirm').mockImplementation(cfg => {
        cfg.accept?.();
        return confirmationService;
      });
      mockRoadmapService.pauseRoadmap.mockReturnValue(
        throwError(
          () =>
            new HttpErrorResponse({
              status: 409,
              statusText: 'Conflict',
              error: { detail: 'Không thể tạm dừng lộ trình lúc này.' },
            })
        )
      );

      component.onPauseRoadmap('rm-1');

      const target = roadmapsSignal().find(r => r.id === 'rm-1');
      expect(target?.status).toBe('ACTIVE');
      expect(addSpy).toHaveBeenCalledTimes(1);
      expect(addSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 'error',
          summary: 'Tạm dừng thất bại',
          detail: 'Không thể tạm dừng lộ trình lúc này.',
        })
      );
      expect(addSpy).not.toHaveBeenCalledWith(
        expect.objectContaining({ severity: 'warn' })
      );
      expect(addSpy).not.toHaveBeenCalledWith(
        expect.objectContaining({ severity: 'success' })
      );
    });

    it('onArchiveRoadmap gặp lỗi HTTP -> giữ nguyên trạng thái, hiện toast lỗi và không hiện toast Đã lưu trữ', () => {
      const confirmationService = TestBed.inject(ConfirmationService);
      const messageService = TestBed.inject(MessageService);
      const addSpy = vi.spyOn(messageService, 'add');

      vi.spyOn(confirmationService, 'confirm').mockImplementation(cfg => {
        cfg.accept?.();
        return confirmationService;
      });
      mockRoadmapService.archiveRoadmap.mockImplementation(
        (
          _id: string,
          callbacks?: {
            onSuccess?: (archived: RoadmapResponse) => void;
            onError?: (msg: string) => void;
          }
        ) => {
          callbacks?.onError?.('Không thể lưu trữ lộ trình học tập.');
        }
      );

      component.onArchiveRoadmap('rm-1');

      const target = roadmapsSignal().find(r => r.id === 'rm-1');
      expect(target?.status).toBe('ACTIVE');
      expect(addSpy).toHaveBeenCalledTimes(1);
      expect(addSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 'error',
          summary: 'Lưu trữ thất bại',
          detail: 'Không thể lưu trữ lộ trình học tập.',
        })
      );
      expect(addSpy).not.toHaveBeenCalledWith(
        expect.objectContaining({ summary: 'Đã lưu trữ' })
      );
    });
  });

  describe('FE-SYNC-02: Đồng bộ RoadmapsHub sau khi áp dụng lộ trình từ Wizard', () => {
    it('phát roadmapApplied đóng wizard, đặt lại bộ lọc về ALL, hiện toast thành công và KHÔNG gọi trùng loadRoadmaps() khi loading() === true', () => {
      const messageService = TestBed.inject(MessageService);
      const addSpy = vi.spyOn(messageService, 'add');

      component.setFilter('PAUSED');
      component.wizardOpen.set(true);
      loadingSignal.set(true);
      mockRoadmapService.loadRoadmaps.mockClear();
      fixture.detectChanges();

      const wizardDebugEl = fixture.debugElement.query(By.directive(RoadmapWizardHostComponent));
      expect(wizardDebugEl).toBeTruthy();
      const wizardHost = wizardDebugEl.componentInstance as RoadmapWizardHostComponent;

      wizardHost.roadmapApplied.emit('rm-new-1');
      fixture.detectChanges();

      expect(component.wizardOpen()).toBe(false);
      expect(component.activeFilter()).toBe('ALL');
      expect(addSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 'success',
        })
      );
      expect(mockRoadmapService.loadRoadmaps).not.toHaveBeenCalled();
    });

    it('phát roadmapApplied gọi loadRoadmaps() khi loading() === false', () => {
      component.wizardOpen.set(true);
      loadingSignal.set(false);
      mockRoadmapService.loadRoadmaps.mockClear();
      fixture.detectChanges();

      const wizardDebugEl = fixture.debugElement.query(By.directive(RoadmapWizardHostComponent));
      const wizardHost = wizardDebugEl.componentInstance as RoadmapWizardHostComponent;

      wizardHost.roadmapApplied.emit('rm-new-2');
      fixture.detectChanges();

      expect(component.wizardOpen()).toBe(false);
      expect(mockRoadmapService.loadRoadmaps).toHaveBeenCalledTimes(1);
    });
  });
});
