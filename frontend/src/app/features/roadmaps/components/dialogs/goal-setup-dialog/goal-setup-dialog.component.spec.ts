import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { GoalSetupDialogComponent } from './goal-setup-dialog.component';

describe('GoalSetupDialogComponent', () => {
  let component: GoalSetupDialogComponent;
  let fixture: ComponentFixture<GoalSetupDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GoalSetupDialogComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(GoalSetupDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('hiển thị lỗi kiểm tra khi bấm Tiếp tục mà chưa nhập mục tiêu học tập', () => {
    const submitSpy = vi.fn();
    component.submitGoal.subscribe(submitSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const submitBtn = compiled.querySelector('[data-testid="goal-submit-btn"]') as HTMLButtonElement;
    submitBtn.click();
    fixture.detectChanges();

    expect(submitSpy).not.toHaveBeenCalled();
    const errorEl = compiled.querySelector('[data-testid="goal-validation-error"]');
    expect(errorEl).toBeTruthy();
  });

  it('điền nhanh mục tiêu khi bấm vào Quick Suggestion Chip và cập nhật ước tính AI', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const chip0 = compiled.querySelector('[data-testid="goal-suggestion-chip-0"]') as HTMLButtonElement;
    expect(chip0).toBeTruthy();
    chip0.click();
    fixture.detectChanges();

    expect(component.goalTitle()).toBe('Chứng chỉ AWS Solutions Architect');
    const estimateBox = compiled.querySelector('[data-testid="ai-cognitive-estimate-box"]');
    expect(estimateBox?.textContent).toContain('giờ học');
    expect(estimateBox?.textContent).toContain('phiên Pomodoro');
  });

  it('phát sự kiện submitGoal với đầy đủ thông tin khi hợp lệ', () => {
    const submitSpy = vi.fn();
    component.submitGoal.subscribe(submitSpy);

    component.selectSuggestion('Luyện thi IELTS 7.5 Academic');
    component.selectLevel('INTERMEDIATE');
    component.onWeeklyHoursChange(15);
    fixture.detectChanges();

    component.onSubmit();

    expect(submitSpy).toHaveBeenCalledTimes(1);
    const payload = submitSpy.mock.calls[0][0];
    expect(payload.title).toBe('Luyện thi IELTS 7.5 Academic');
    expect(payload.prior_knowledge_level).toBe('INTERMEDIATE');
  });
});
