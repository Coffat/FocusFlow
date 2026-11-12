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
});
