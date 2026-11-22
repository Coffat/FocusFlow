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

  it('không render dữ liệu giả định mặc định như Master FastAPI, +2 ngày hay 30/11/2026', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent ?? '';
    expect(text).not.toContain('Master FastAPI');
    expect(text).not.toContain('+2 ngày');
    expect(text).not.toContain('30/11/2026');
    expect(text).not.toContain('02/12/2026');
  });

  it('hiển thị banner lỗi khi có errorMessage và vô hiệu hóa nút xác nhận khi submitting', () => {
    fixture.componentRef.setInput('errorMessage', 'Không thể tái tối ưu lịch học.');
    fixture.componentRef.setInput('submitting', true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const errorBanner = compiled.querySelector('[data-testid="adaptation-error-banner"]');
    const confirmBtn = compiled.querySelector(
      '[data-testid="adaptation-confirm-btn"]'
    ) as HTMLButtonElement;

    expect(errorBanner?.textContent).toContain('Không thể tái tối ưu lịch học.');
    expect(confirmBtn.disabled).toBe(true);
  });
});
