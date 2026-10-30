import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { RoadmapPageComponent } from './roadmap-page.component';
import { RoadmapService } from '../../services/roadmap.service';
import { API_ENDPOINTS } from '../../../../core/constants/api-endpoints';
import { RoadmapDetailResponse, ScheduleProposalResponse } from '../../models/roadmap.model';

describe('RoadmapPageComponent (WBS 6.3 3-Step AI Planning & Approval Workspace)', () => {
  let component: RoadmapPageComponent;
  let fixture: ComponentFixture<RoadmapPageComponent>;
  let service: RoadmapService;
  let httpTesting: HttpTestingController;

  const mockDetail: RoadmapDetailResponse = {
    id: '018f0000-0000-7000-8000-000000000001',
    user_id: '018f0000-0000-7000-8000-000000000099',
    goal_id: '018f0000-0000-7000-8000-000000000010',
    title: 'Lộ trình Kiến trúc Lục giác & AI Planning',
    description: 'Tuần 9 WBS 6.1 - 6.3',
    status: 'INITIALIZED',
    start_date: '2026-11-02',
    target_date: '2026-12-30',
    created_at: '2026-10-30T08:00:00Z',
    updated_at: '2026-10-30T08:00:00Z',
    goal: {
      id: '018f0000-0000-7000-8000-000000000010',
      user_id: '018f0000-0000-7000-8000-000000000099',
      title: 'Lộ trình Kiến trúc Lục giác & AI Planning',
      raw_description: 'Tuần 9 WBS 6.1 - 6.3',
      target_date: '2026-12-30',
      status: 'ACTIVE',
      created_at: '2026-10-30T08:00:00Z',
      updated_at: '2026-10-30T08:00:00Z',
    },
    milestones: [
      {
        id: 'ms-1',
        roadmap_id: '018f0000-0000-7000-8000-000000000001',
        sequence_order: 1,
        title: 'Chặng 1: Cổng kiểm định 3 tầng',
        description: 'Tier 1, Tier 2, Tier 3',
        status: 'PENDING',
        created_at: '2026-10-30T08:00:00Z',
        updated_at: '2026-10-30T08:00:00Z',
      },
    ],
    official_schedule: null,
    scheduled_tasks: [],
    current_draft_proposal: null,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoadmapPageComponent],
      providers: [
        RoadmapService,
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RoadmapPageComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(RoadmapService);
    httpTesting = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    // Flush initial loadRoadmaps() on ngOnInit
    const listReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    listReq.flush([mockDetail]);
    const detailReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.DETAIL(mockDetail.id));
    detailReq.flush(mockDetail);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('hiển thị đầy đủ 3 tab bước lập kế hoạch với thuộc tính A11y chuẩn', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const tablist = compiled.querySelector('[role="tablist"]');
    expect(tablist).toBeTruthy();

    const step1Tab = compiled.querySelector('[data-testid="step-tab-1"]');
    expect(step1Tab?.getAttribute('aria-selected')).toBe('true');

    const step1Panel = compiled.querySelector('[data-testid="step-1-panel"]');
    expect(step1Panel).toBeTruthy();
  });

  it('cho phép tạo mới Goal & Roadmap trực tiếp từ form ở Bước 1', () => {
    const createSpy = vi.spyOn(service, 'createRoadmap');
    component.toggleCreateForm();
    component.newGoalTitle.set('Chinh phục AI Evaluation Harness');
    component.newGoalDescription.set('Kiểm thử 5 Golden Datasets');
    component.newTargetDate.set('2026-12-15');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const submitBtn = compiled.querySelector(
      '[data-testid="submit-create-roadmap-btn"]'
    ) as HTMLButtonElement;
    submitBtn.click();

    expect(createSpy).toHaveBeenCalledWith({
      title: 'Chinh phục AI Evaluation Harness',
      description: 'Kiểm thử 5 Golden Datasets',
      goal_title: 'Chinh phục AI Evaluation Harness',
      goal_description: 'Kiểm thử 5 Golden Datasets',
      start_date: '2026-11-02',
      target_date: '2026-12-15',
    });

    const postReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    postReq.flush({
      ...mockDetail,
      id: 'rm-new-2',
      title: 'Chinh phục AI Evaluation Harness',
    });
  });

  it('cho phép thêm/sửa cột mốc và bấm Phê duyệt Cột mốc ở Bước 1', () => {
    const approveSpy = vi.spyOn(service, 'approveMilestones');
    const compiled = fixture.nativeElement as HTMLElement;

    const addBtn = compiled.querySelector('[data-testid="add-milestone-btn"]') as HTMLButtonElement;
    addBtn.click();
    fixture.detectChanges();

    expect(service.editableMilestones().length).toBe(2);

    const approveBtn = compiled.querySelector(
      '[data-testid="approve-milestones-btn"]'
    ) as HTMLButtonElement;
    approveBtn.click();

    expect(approveSpy).toHaveBeenCalledWith(mockDetail.id);
    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(mockDetail.id));
    req.flush({
      roadmap_id: mockDetail.id,
      milestones: [
        {
          ...mockDetail.milestones![0],
          status: 'APPROVED',
        },
      ],
    });
    fixture.detectChanges();

    expect(service.activeStep()).toBe(2);
  });

  it('hiển thị cảnh báo Soft Overflow ở Bước 2 và khóa nút Apply cho đến khi người học tích xác nhận', () => {
    const draftProposal: ScheduleProposalResponse = {
      id: 'prop-soft-1',
      roadmap_id: mockDetail.id,
      user_id: mockDetail.user_id,
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: true,
      tasks: [
        {
          task_id: 'task-1',
          milestone_id: 'ms-1',
          title: 'Ôn tập chuyên sâu Mode B',
          estimated_minutes: 90,
          scheduled_date: '2026-11-02',
          scheduled_start: '20:20',
          scheduled_end: '21:50',
        },
      ],
      dependencies: [],
      violations: [],
      soft_overflow_warnings: [
        {
          task_index: 0,
          task_title: 'Ôn tập chuyên sâu Mode B',
          scheduled_date: '2026-11-02',
          overflow_minutes: 20,
          message: 'Tràn 20 phút cuối ngày.',
        },
      ],
      advisory_warnings: [],
      diff_summary: {
        preserved_completed_tasks_count: 3,
        replaced_tasks_count: 1,
        inserted_tasks_count: 1,
      },
      proposal_data: {},
      applied_at: null,
      created_at: '2026-10-30T08:00:00Z',
      updated_at: '2026-10-30T08:00:00Z',
    };

    service.milestones.set([
      {
        ...mockDetail.milestones![0],
        status: 'APPROVED',
      },
    ]);
    service.currentProposal.set(draftProposal);
    service.editableTasks.set([
      {
        task_id: 'task-1',
        milestone_id: 'ms-1',
        milestone_sequence_order: 1,
        title: 'Ôn tập chuyên sâu Mode B',
        description: null,
        estimated_minutes: 90,
        scheduled_date: '2026-11-02',
        scheduled_start: '20:20',
        scheduled_end: '21:50',
        prerequisite_ids: [],
      },
    ]);
    service.setActiveStep(2);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const warningPanel = compiled.querySelector('[data-testid="soft-overflow-warning-panel"]');
    expect(warningPanel).toBeTruthy();

    const applyBtn = compiled.querySelector('[data-testid="apply-proposal-btn"]') as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(true);

    // Check confirmation checkbox
    const checkbox = compiled.querySelector(
      '[data-testid="confirm-soft-overflow-checkbox"]'
    ) as HTMLInputElement;
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(service.confirmSoftOverflow()).toBe(true);
    expect(applyBtn.disabled).toBe(false);
  });

  it('hiển thị Lịch học Chính thức (OfficialSchedule) theo từng Cột mốc ở Bước 3 và đóng SSE khi destroy', () => {
    const closeSpy = vi.spyOn(service, 'closeActiveStream');

    service.selectedRoadmapDetail.set({
      ...mockDetail,
      status: 'ACTIVE',
      official_schedule: {
        id: 'off-1',
        roadmap_id: mockDetail.id,
        total_sessions: 1,
        total_planned_minutes: 60,
        activated_at: '2026-10-30T10:00:00Z',
        created_at: '2026-10-30T10:00:00Z',
        updated_at: '2026-10-30T10:00:00Z',
      },
      scheduled_tasks: [
        {
          task_id: 'task-off-1',
          roadmap_id: mockDetail.id,
          milestone_id: 'ms-1',
          title: 'Phiên học chính thức #1',
          estimated_minutes: 60,
          scheduled_date: '2026-11-02',
          scheduled_start: '2026-11-02T19:30:00Z',
          scheduled_end: '2026-11-02T20:30:00Z',
          status: 'PENDING',
          roadmap_target_date: '2026-12-30',
        },
      ],
    });
    service.setActiveStep(3);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="official-total-sessions"]')?.textContent).toContain(
      '1 phiên học'
    );
    expect(
      compiled.querySelector('[data-testid="official-task-item-task-off-1"]')?.textContent
    ).toContain('Phiên học chính thức #1');

    fixture.destroy();
    expect(closeSpy).toHaveBeenCalled();
  });
});
