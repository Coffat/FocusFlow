import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MilestoneApprovalDialogComponent } from './milestone-approval-dialog.component';
import { RoadmapService } from '../../../services/roadmap.service';

describe('MilestoneApprovalDialogComponent', () => {
  let component: MilestoneApprovalDialogComponent;
  let fixture: ComponentFixture<MilestoneApprovalDialogComponent>;
  let roadmapService: RoadmapService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MilestoneApprovalDialogComponent],
      providers: [RoadmapService, provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(MilestoneApprovalDialogComponent);
    component = fixture.componentInstance;
    roadmapService = TestBed.inject(RoadmapService);
    fixture.detectChanges();
  });

  it('cho phép thêm cột mốc mới, chỉnh sửa và xóa cột mốc', () => {
    expect(roadmapService.editableMilestones().length).toBe(0);

    const compiled = fixture.nativeElement as HTMLElement;
    const addBtn = compiled.querySelector('[data-testid="add-milestone-btn"]') as HTMLButtonElement;
    addBtn.click();
    fixture.detectChanges();

    expect(roadmapService.editableMilestones().length).toBe(1);
    expect(compiled.querySelector('[data-testid="editable-milestone-card-0"]')).toBeTruthy();

    component.onTitleChange(0, 'Chặng 1: Kiến trúc Hexagonal');
    fixture.detectChanges();
    expect(roadmapService.editableMilestones()[0].title).toBe('Chặng 1: Kiến trúc Hexagonal');

    component.onRemoveMilestone(0);
    fixture.detectChanges();
    expect(roadmapService.editableMilestones().length).toBe(0);
  });

  it('phát sự kiện generateMilestones và approveMilestones khi người dùng bấm nút', () => {
    const genSpy = vi.fn();
    const approveSpy = vi.fn();
    component.generateMilestones.subscribe(genSpy);
    component.approveMilestones.subscribe(approveSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const genBtn = compiled.querySelector('[data-testid="generate-milestones-btn"]') as HTMLButtonElement;
    genBtn.click();
    expect(genSpy).toHaveBeenCalled();

    const approveBtn = compiled.querySelector('[data-testid="approve-milestones-btn"]') as HTMLButtonElement;
    approveBtn.click();
    expect(approveSpy).toHaveBeenCalled();
  });

  it('hiển thị màn hình loading tối giản và thanh tiến trình khi AI đang stream 2-Stage SSE', () => {
    roadmapService.sseProgress.set({
      stage: 'STREAMING',
      progress: 35,
      message: 'Đang trích xuất cây khái niệm từ Knowledge Graph...',
      retryCount: 0,
      isStreaming: true,
    });
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const streamContainer = compiled.querySelector('[data-testid="milestones-stream-generating-state"]');
    expect(streamContainer).toBeTruthy();

    const stageBadge = compiled.querySelector('[data-testid="stream-stage-hero-badge"]');
    const statusMessage = compiled.querySelector('[data-testid="stream-status-message"]');
    expect(stageBadge?.textContent).toContain('Giai đoạn 1/2: Thiết kế cột mốc');
    expect(streamContainer?.textContent).toContain('Đang kiến trúc chuỗi cột mốc học tập...');
    expect(statusMessage?.textContent).toContain('Đang trích xuất cây khái niệm từ Knowledge Graph...');

    // Vô hiệu hóa nút Lưu & Phê duyệt khi đang stream, nhưng giữ nút Quay lại Bước 2 hoạt động
    const backBtn = compiled.querySelector('[data-testid="milestone-back-btn"]') as HTMLButtonElement;
    const saveBtn = compiled.querySelector('[data-testid="save-milestones-btn"]') as HTMLButtonElement;
    const approveBtn = compiled.querySelector('[data-testid="approve-milestones-btn"]') as HTMLButtonElement;
    expect(backBtn.disabled).toBe(false);
    expect(saveBtn.disabled).toBe(true);
    expect(approveBtn.disabled).toBe(true);

    // Đã loại bỏ hoàn toàn các skeleton card nhấp nháy giả tạo và hộp đen terminal
    const skeletonCards = streamContainer?.querySelectorAll('.animate-pulse');
    expect(skeletonCards?.length).toBe(0);

    // Chuyển sang Giai đoạn 2 và kiểm tra fallback khi message rỗng
    roadmapService.sseProgress.set({
      stage: 'VALIDATING_TIER_1_2_3',
      progress: 75,
      message: '',
      retryCount: 0,
      isStreaming: true,
    });
    fixture.detectChanges();

    expect(stageBadge?.textContent).toContain('Giai đoạn 2/2: Cân đối thời lượng');
    expect(statusMessage?.textContent).toContain(
      'Hệ thống đang cấu trúc hóa các chuyên đề và cân đối thời lượng học tập tối ưu.'
    );
  });

  it('cho phép mở rộng và nhập ngữ cảnh bổ sung cho AI', () => {
    expect(component.isContextExpanded()).toBe(false);

    const compiled = fixture.nativeElement as HTMLElement;
    const toggleBtn = compiled.querySelector('[data-testid="toggle-context-btn"]') as HTMLButtonElement;
    toggleBtn.click();
    fixture.detectChanges();

    expect(component.isContextExpanded()).toBe(true);

    const contextInput = compiled.querySelector(
      '[data-testid="milestone-additional-context-input"]'
    ) as HTMLTextAreaElement;
    expect(contextInput).toBeTruthy();

    component.additionalContext.set('Tập trung các bài tập thực hành FastAPI');
    fixture.detectChanges();

    const genSpy = vi.fn();
    component.generateMilestones.subscribe(genSpy);

    const genBtn = compiled.querySelector('[data-testid="generate-milestones-btn"]') as HTMLButtonElement;
    genBtn.click();

    expect(genSpy).toHaveBeenCalledWith('Tập trung các bài tập thực hành FastAPI');
  });

  it('đọc estimated_effort_minutes từ milestone thay vì fallback cứng 24h', () => {
    roadmapService.editableMilestones.set([
      {
        id: 'ms-1',
        milestone_id: 'ms-1',
        sequence_order: 1,
        title: 'Chặng 1',
        description: 'Mô tả',
        estimated_effort_minutes: 180,
      },
      {
        id: 'ms-2',
        milestone_id: 'ms-2',
        sequence_order: 2,
        title: 'Chặng 2',
        description: 'Mô tả',
        estimated_effort_minutes: 300,
      },
    ]);
    fixture.detectChanges();

    expect(component.getMilestoneHours(0)).toBe(3);
    expect(component.getMilestoneHours(1)).toBe(5);
    expect(component.totalEstimatedHours()).toBe(8);

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="total-estimated-hours-badge"]')?.textContent).toContain('8h');
  });

  it('hiển thị FIT_CAPACITY scope panel và phát approveFitCapacity & regenerateFitCapacity trong dialog', () => {
    roadmapService.editableMilestones.set([
      {
        id: 'ms-1',
        milestone_id: 'ms-1',
        sequence_order: 1,
        title: 'Chặng 1: Giữ lại',
        description: 'Core',
        estimated_effort_minutes: 180,
      },
      {
        id: 'ms-2',
        milestone_id: 'ms-2',
        sequence_order: 2,
        title: 'Chặng 2: Hoãn lại',
        description: 'Deferred',
        estimated_effort_minutes: 240,
      },
    ]);
    roadmapService.preliminaryFeasibility.set({
      status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
      scope_proposal_version: 2,
      requires_learner_approval: true,
      scope_approval_status: 'PENDING_LEARNER_APPROVAL',
      hard_packable_capacity_minutes: 240,
      estimated_total_minutes: 420,
      normalized_planned_total_minutes: 180,
      kept_scope: [
        { sequence_order: 1, milestone_id: 'ms-1', title: 'Chặng 1: Giữ lại', estimated_effort_minutes: 180 },
      ],
      deferred_scope: [
        { sequence_order: 2, milestone_id: 'ms-2', title: 'Chặng 2: Hoãn lại', estimated_effort_minutes: 240 },
      ],
      feasibility_reasons: [],
    });
    fixture.detectChanges();

    const approveFitSpy = vi.fn();
    const regenFitSpy = vi.fn();
    component.approveFitCapacity.subscribe(approveFitSpy);
    component.regenerateFitCapacity.subscribe(regenFitSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="fit-capacity-scope-panel"]')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="scope-proposal-version-badge"]')?.textContent).toContain('v2');
    expect(compiled.querySelector('[data-testid="dialog-milestone-scope-badge-0"]')?.textContent).toContain('Giữ lại');
    expect(compiled.querySelector('[data-testid="dialog-milestone-scope-badge-1"]')?.textContent).toContain('Hoãn lại (PENDING)');

    const checkbox = compiled.querySelector('[data-testid="confirm-fit-capacity-checkbox"]') as HTMLInputElement;
    checkbox.click();
    fixture.detectChanges();

    (compiled.querySelector('[data-testid="confirm-fit-capacity-approve-btn"]') as HTMLButtonElement).click();
    expect(approveFitSpy).toHaveBeenCalledWith(2);

    (compiled.querySelector('[data-testid="regenerate-fit-capacity-btn"]') as HTMLButtonElement).click();
    expect(regenFitSpy).toHaveBeenCalledOnce();
  });

  it('hiển thị cảnh báo PRELIMINARY_UNSCHEDULABLE và khóa nút phê duyệt trong dialog', () => {
    roadmapService.preliminaryFeasibility.set({
      status: 'PRELIMINARY_UNSCHEDULABLE',
      scope_proposal_version: 0,
      requires_learner_approval: false,
      scope_approval_status: 'NOT_REQUIRED',
      hard_packable_capacity_minutes: 30,
      kept_scope: [],
      deferred_scope: [],
      feasibility_reasons: [
        { code: 'PRELIMINARY_UNSCHEDULABLE', message: 'Không đủ quỹ giờ cho cột mốc 1.' },
      ],
    });
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="preliminary-unschedulable-alert"]')).toBeTruthy();
    expect((compiled.querySelector('[data-testid="approve-milestones-btn"]') as HTMLButtonElement).disabled).toBe(true);
  });
});
