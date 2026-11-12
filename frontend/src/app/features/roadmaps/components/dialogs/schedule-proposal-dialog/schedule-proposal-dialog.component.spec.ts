import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ScheduleProposalDialogComponent } from './schedule-proposal-dialog.component';
import { RoadmapService } from '../../../services/roadmap.service';

describe('ScheduleProposalDialogComponent', () => {
  let component: ScheduleProposalDialogComponent;
  let fixture: ComponentFixture<ScheduleProposalDialogComponent>;
  let roadmapService: RoadmapService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScheduleProposalDialogComponent],
      providers: [RoadmapService, provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(ScheduleProposalDialogComponent);
    component = fixture.componentInstance;
    roadmapService = TestBed.inject(RoadmapService);
    fixture.detectChanges();
  });

  it('hiển thị huy hiệu 0 vi phạm ràng buộc cứng mặc định và cho phép thêm phiên học mới', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="zero-hard-violations-badge"]')).toBeTruthy();

    const addBtn = compiled.querySelector('[data-testid="add-task-btn"]') as HTMLButtonElement;
    addBtn.click();
    fixture.detectChanges();

    expect(roadmapService.editableTasks().length).toBe(1);
    expect(compiled.querySelector('[data-testid="proposed-task-card-0"]')).toBeTruthy();
  });

  it('yêu cầu tích chọn xác nhận Soft Overflow trước khi cho phép bấm Apply Schedule', () => {
    roadmapService.currentProposal.set({
      id: 'prop-1',
      roadmap_id: 'rm-1',
      user_id: 'usr-1',
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: true,
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
});
