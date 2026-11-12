import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AdaptationModalDialogComponent } from './adaptation-modal-dialog.component';

describe('AdaptationModalDialogComponent', () => {
  let component: AdaptationModalDialogComponent;
  let fixture: ComponentFixture<AdaptationModalDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdaptationModalDialogComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(AdaptationModalDialogComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('open', true);
    fixture.componentRef.setInput('roadmapId', 'rm-2');
    fixture.detectChanges();
  });

  it('hiển thị đầy đủ 3 phương án thích ứng và chọn mặc định DOMINO_SHIFT', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[role="dialog"]')).toBeTruthy();
    expect(compiled.textContent).toContain('Tái cân bằng lộ trình học tập');
    expect(compiled.textContent).toContain('Chuỗi học tập (Streak) của bạn vẫn được bảo toàn');
    expect(component.selectedStrategy()).toBe('DOMINO_SHIFT');
  });

  it('cho phép chọn phương án COMPACT_REBALANCE và phát sự kiện confirmAdaptation', () => {
    const confirmSpy = vi.fn();
    component.confirmAdaptation.subscribe(confirmSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const compactCard = compiled.querySelector(
      '[data-testid="strategy-card-COMPACT_REBALANCE"]'
    ) as HTMLButtonElement;
    compactCard.click();
    fixture.detectChanges();

    expect(component.selectedStrategy()).toBe('COMPACT_REBALANCE');

    const confirmBtn = compiled.querySelector(
      '[data-testid="adaptation-confirm-btn"]'
    ) as HTMLButtonElement;
    confirmBtn.click();

    expect(confirmSpy).toHaveBeenCalledWith({
      strategy: 'COMPACT_REBALANCE',
      roadmapId: 'rm-2',
    });
  });

  it('đóng hộp thoại khi bấm phím Escape', () => {
    const closeSpy = vi.fn();
    component.closeModal.subscribe(closeSpy);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(closeSpy).toHaveBeenCalled();
  });
});
