import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { ConfirmationService, MessageService } from 'primeng/api';
import { RoadmapsHubComponent } from './roadmaps-hub.component';
import { RoadmapService } from '../../services/roadmap.service';
import { AuthService } from '../../../../core/services/auth.service';
import { RoadmapResponse } from '../../models/roadmap.model';

describe('RoadmapsHubComponent', () => {
  let component: RoadmapsHubComponent;
  let fixture: ComponentFixture<RoadmapsHubComponent>;
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
});
