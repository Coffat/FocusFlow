import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ScheduleProposalDialogComponent } from './schedule-proposal-dialog.component';
import { RoadmapService } from '../../../services/roadmap.service';
import {
  CalendarConnectionResponseDTO,
  CalendarIntegrationService,
} from '../../../../../core/services/calendar-integration.service';
import { AvailabilityService } from '../../../../../core/services/availability.service';
import { components } from '../../../../../core/api/schema';

type AvailabilityResponseDTO = components['schemas']['AvailabilityResponseDTO'];

describe('ScheduleProposalDialogComponent', () => {
  let component: ScheduleProposalDialogComponent;
  let fixture: ComponentFixture<ScheduleProposalDialogComponent>;
  let roadmapService: RoadmapService;
  let mockCalendarService: {
    isConnected: ReturnType<typeof signal<boolean>>;
    connection: ReturnType<typeof signal<CalendarConnectionResponseDTO | null>>;
    loadStatus: ReturnType<typeof vi.fn>;
  };
  let mockAvailabilityService: {
    profile: ReturnType<typeof signal<AvailabilityResponseDTO | null>>;
  };

  beforeEach(async () => {
    mockCalendarService = {
      isConnected: signal(false),
      connection: signal<CalendarConnectionResponseDTO | null>({
        connected: false,
        provider: 'GOOGLE',
        sync_status: 'NOT_CONNECTED',
      }),
      loadStatus: vi.fn(() =>
        of({
          connected: false,
          provider: 'GOOGLE',
          sync_status: 'NOT_CONNECTED',
        })
      ),
    };
    mockAvailabilityService = {
      profile: signal<AvailabilityResponseDTO | null>(null),
    };

    await TestBed.configureTestingModule({
      imports: [ScheduleProposalDialogComponent],
      providers: [
        RoadmapService,
        { provide: CalendarIntegrationService, useValue: mockCalendarService },
        { provide: AvailabilityService, useValue: mockAvailabilityService },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ScheduleProposalDialogComponent);
    component = fixture.componentInstance;
    roadmapService = TestBed.inject(RoadmapService);
    fixture.detectChanges();
  });

  it('hiển thị bố cục 1 cột tối giản mặc định và cho phép thêm phiên học mới', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="zero-hard-violations-badge"]')).toBeNull();
    expect(compiled.querySelector('[data-testid="schedule-diff-summary"]')).toBeNull();

    const addBtn = compiled.querySelector('[data-testid="add-task-btn"]') as HTMLButtonElement;
    addBtn.click();
    fixture.detectChanges();

    expect(roadmapService.editableTasks().length).toBe(1);
    expect(compiled.querySelector('[data-testid="proposed-task-card-0"]')).toBeTruthy();
  });

  it('hiển thị trạng thái đang tạo lịch nền và trạng thái khôi phục khi gặp lỗi', () => {
    roadmapService.sseProgress.set({
      stage: 'STREAMING',
      progress: 45,
      message: 'Đang kiểm định tính khả thi và xếp khung giờ rảnh...',
      retryCount: 0,
      isStreaming: true,
    });
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const liveBox = compiled.querySelector('[data-testid="step4-live-progress-box"]');
    expect(liveBox).toBeTruthy();
    expect(liveBox?.textContent).toContain('45%');
    expect(liveBox?.textContent).toContain('1. Phân rã bài học');
    expect(liveBox?.textContent).toContain('4. Hoàn thiện đề xuất');

    roadmapService.sseProgress.set({
      stage: 'FAILED',
      progress: 0,
      message: 'Quá thời gian xử lý.',
      retryCount: 0,
      isStreaming: false,
    });
    fixture.detectChanges();

    expect(compiled.querySelector('[data-testid="step4-error-recovery-box"]')).toBeTruthy();
    const retrySpy = vi.fn();
    const manualSpy = vi.fn();
    component.generateProposal.subscribe(retrySpy);
    component.manualScheduleFallback.subscribe(manualSpy);

    (compiled.querySelector('[data-testid="step4-retry-btn"]') as HTMLButtonElement).click();
    expect(retrySpy).toHaveBeenCalledOnce();

    (compiled.querySelector('[data-testid="step4-manual-fallback-btn"]') as HTMLButtonElement).click();
    expect(manualSpy).toHaveBeenCalledOnce();
  });

  it('yêu cầu tích chọn xác nhận Soft Overflow trước khi cho phép bấm Apply Schedule', () => {
    roadmapService.currentProposal.set({
      id: 'prop-1',
      roadmap_id: 'rm-1',
      user_id: 'usr-1',
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: true,
      judge_status: 'PASSED',
      is_partial_schedule: false,
      scheduled_tasks_count: 0,
      unscheduled_tasks_count: 0,
      tasks: [],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [
        {
          task_index: 0,
          task_title: 'Phiên học tối',
          scheduled_date: '2026-11-15',
          overflow_minutes: 15,
          message: 'Tràn 15 phút cuối ngày',
        },
      ],
      advisory_warnings: [],
      diff_summary: {
        preserved_completed_tasks_count: 2,
        replaced_tasks_count: 1,
        inserted_tasks_count: 3,
      },
      proposal_data: {},
      applied_at: null,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    roadmapService.setConfirmSoftOverflow(false);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="soft-overflow-warning-box"]')).toBeTruthy();

    const applyBtn = compiled.querySelector('[data-testid="apply-proposal-btn"]') as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(true);

    component.onToggleSoftOverflow(true);
    fixture.detectChanges();
    expect(applyBtn.disabled).toBe(false);

    const applySpy = vi.fn();
    component.applyProposal.subscribe(applySpy);
    applyBtn.click();
    expect(applySpy).toHaveBeenCalledWith(true);
  });

  it('hỗ trợ chuyển đổi giữa chế độ Danh sách (TIMELINE) và Lịch Tuần (CALENDAR), hiển thị tài liệu đính kèm và nguồn lịch', () => {
    roadmapService.currentProposal.set({
      id: 'prop-cal-1',
      roadmap_id: 'rm-1',
      user_id: 'usr-1',
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: false,
      judge_status: 'PASSED',
      is_partial_schedule: false,
      scheduled_tasks_count: 0,
      unscheduled_tasks_count: 0,
      availability_source_metadata: {
        source_type: 'GOOGLE_CALENDAR',
        calendar_connected: true,
        busy_intervals_count: 4,
      },
      tasks: [],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [],
      advisory_warnings: [],
      diff_summary: {},
      proposal_data: {},
      applied_at: null,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    roadmapService.editableTasks.set([
      {
        task_id: 't-1',
        milestone_id: 'ms-1',
        milestone_sequence_order: 1,
        title: 'Thiết kế Aggregate Root',
        estimated_minutes: 60,
        scheduled_date: '2026-11-16',
        scheduled_start: '19:00',
        scheduled_end: '20:00',
        task_type: 'PRACTICE',
        resources: [
          {
            title: 'DDD Reference Guide',
            url: 'https://domainlanguage.com/ddd/',
            type: 'DOCS',
          },
        ],
      },
    ]);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="availability-source-badge"]')?.textContent).toContain(
      'Google Calendar (đã trừ 4 khoảng bận)'
    );
    expect(compiled.querySelector('[data-testid="task-resources-list-0"]')?.textContent).toContain(
      'DDD Reference Guide'
    );

    const calBtn = compiled.querySelector('[data-testid="view-mode-calendar-btn"]') as HTMLButtonElement;
    calBtn.click();
    fixture.detectChanges();

    expect(component.viewMode()).toBe('CALENDAR');
    expect(compiled.querySelector('[data-testid="schedule-calendar-weekly-view"]')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="weekly-schedule-group-1"]')?.textContent).toContain(
      'Thiết kế Aggregate Root'
    );
  });

  it('hiển thị hộp cảnh báo unscheduled_tasks (AC-07) và yêu cầu xác nhận khi judge_status là REVIEW_PENDING hoặc NEEDS_REVIEW', () => {
    roadmapService.currentProposal.set({
      id: 'prop-partial-1',
      roadmap_id: 'rm-1',
      user_id: 'usr-1',
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: false,
      judge_status: 'REVIEW_PENDING',
      is_partial_schedule: true,
      scheduled_tasks_count: 1,
      unscheduled_tasks_count: 1,
      unscheduled_tasks: [
        {
          task_id: 't-unsched-1',
          title: 'Bài tập nâng cao bị tràn deadline',
          task_type: 'PRACTICE',
          estimated_minutes: 90,
          unscheduled_reason: 'OVER_CAPACITY',
        },
      ],
      feasibility: {
        status: 'PARTIAL',
        required_minutes: 150,
        available_minutes: 60,
        scheduled_minutes: 60,
        schedulable_ratio: 0.4,
        unscheduled_minutes: 90,
        reason_codes: ['DEADLINE_CAPACITY_EXCEEDED'],
        recommended_actions: ['KEEP_BACKLOG'],
      },
      tasks: [],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [],
      advisory_warnings: ['Mật độ kiến thức tuần cuối khá cao.'],
      diff_summary: {},
      proposal_data: {},
      applied_at: null,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    roadmapService.editableTasks.set([
      {
        task_id: 't-sched-1',
        title: 'Bài học đã xếp lịch',
        task_type: 'PRACTICE',
        estimated_minutes: 60,
        scheduled_date: '2026-11-16',
        scheduled_start: '19:00',
        scheduled_end: '20:00',
      },
    ]);
    roadmapService.setConfirmWarnings(false);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const unschedBox = compiled.querySelector('[data-testid="unscheduled-tasks-warning-box"]');
    expect(unschedBox).toBeTruthy();
    expect(unschedBox?.textContent).toContain('Bài tập nâng cao bị tràn deadline');
    expect(unschedBox?.textContent).toContain('Backlog');

    const pendingBadge = compiled.querySelector('[data-testid="judge-status-review-pending-badge"]');
    expect(pendingBadge).toBeTruthy();
    expect(pendingBadge?.textContent).toContain('Chưa hoàn tất kiểm tra sư phạm tự động');
    expect(compiled.querySelector('[data-testid="judge-status-passed-badge"]')).toBeNull();

    const applyBtn = compiled.querySelector('[data-testid="apply-proposal-btn"]') as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(true);

    component.onToggleConfirmWarnings(true);
    component.onToggleConfirmPartialSchedule(true);
    fixture.detectChanges();
    expect(applyBtn.disabled).toBe(false);
  });

  it('chặn Apply khi INFEASIBLE và cho phép yêu cầu AI tạo lại Roadmap theo quỹ giờ', () => {
    roadmapService.currentProposal.set({
      id: 'prop-infeasible-1',
      roadmap_id: 'rm-1',
      user_id: 'usr-1',
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: false,
      judge_status: 'PASSED',
      is_partial_schedule: false,
      scheduled_tasks_count: 0,
      unscheduled_tasks_count: 1,
      feasibility: {
        status: 'INFEASIBLE',
        required_minutes: 600,
        available_minutes: 120,
        scheduled_minutes: 120,
        schedulable_ratio: 0.2,
        unscheduled_minutes: 480,
        reason_codes: ['SCHEDULABLE_RATIO_BELOW_25_PERCENT'],
        recommended_actions: ['REGENERATE_ROADMAP_FIT_CAPACITY'],
      },
      tasks: [],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [],
      advisory_warnings: [],
      diff_summary: {},
      proposal_data: {},
      applied_at: null,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    const regenerateSpy = vi.fn();
    component.regenerateRoadmapFitCapacity.subscribe(regenerateSpy);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="infeasible-plan-alert"]')).toBeTruthy();
    expect((compiled.querySelector('[data-testid="apply-proposal-btn"]') as HTMLButtonElement).disabled).toBe(true);

    (compiled.querySelector('[data-testid="fit-capacity-regenerate-btn"]') as HTMLButtonElement).click();
    expect(regenerateSpy).toHaveBeenCalledOnce();
  });

  it('hiển thị đúng nhãn nguồn giờ rảnh cho Google Calendar (0 khoảng bận), gián đoạn, và giờ rảnh cá nhân', () => {
    const baseProposal = {
      id: 'prop-src-1',
      roadmap_id: 'rm-1',
      user_id: 'usr-1',
      status: 'DRAFT' as const,
      is_valid: true,
      has_soft_overflow: false,
      judge_status: 'PASSED' as const,
      is_partial_schedule: false,
      scheduled_tasks_count: 0,
      unscheduled_tasks_count: 0,
      tasks: [],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [],
      advisory_warnings: [],
      diff_summary: {},
      proposal_data: {},
      applied_at: null,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    };

    roadmapService.currentProposal.set({
      ...baseProposal,
      availability_source_metadata: {
        source_type: 'GOOGLE_CALENDAR',
        calendar_connected: true,
        busy_intervals_count: 0,
      },
    });
    fixture.detectChanges();
    expect(component.availabilitySourceLabel()).toBe('Google Calendar (đã đồng bộ)');

    roadmapService.currentProposal.set({
      ...baseProposal,
      availability_source_metadata: {
        source_type: 'MANUAL',
        calendar_connected: false,
        google_sync_status: 'FAILED_OR_EXPIRED',
      },
    });
    fixture.detectChanges();
    expect(component.availabilitySourceLabel()).toBe(
      'Google Calendar gián đoạn (đang dùng giờ rảnh dự phòng)'
    );

    roadmapService.currentProposal.set({
      ...baseProposal,
      availability_source_metadata: {
        source_type: 'MANUAL',
        calendar_connected: false,
      },
    });
    fixture.detectChanges();
    expect(component.availabilitySourceLabel()).toBe('Giờ rảnh cá nhân');
  });

  it('ưu tiên kiểm tra CalendarIntegrationService.isConnected() khi currentProposal là null hoặc thiếu availability_source_metadata', () => {
    roadmapService.currentProposal.set(null);
    mockCalendarService.isConnected.set(true);
    fixture.detectChanges();

    expect(component.isGoogleCalendarSource()).toBe(true);
    expect(component.availabilitySourceLabel()).toBe('Google Calendar (đã đồng bộ)');

    roadmapService.currentProposal.set({
      id: 'prop-no-meta-1',
      roadmap_id: 'rm-1',
      user_id: 'usr-1',
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: false,
      judge_status: 'PASSED',
      is_partial_schedule: false,
      scheduled_tasks_count: 0,
      unscheduled_tasks_count: 0,
      tasks: [],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [],
      advisory_warnings: [],
      diff_summary: {},
      proposal_data: {},
      applied_at: null,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });
    fixture.detectChanges();

    expect(component.isGoogleCalendarSource()).toBe(true);
    expect(component.availabilitySourceLabel()).toBe('Google Calendar (đã đồng bộ)');
  });
});
