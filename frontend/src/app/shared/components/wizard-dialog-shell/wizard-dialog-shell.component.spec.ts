import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { WizardDialogShellComponent } from './wizard-dialog-shell.component';

describe('WizardDialogShellComponent', () => {
  let component: WizardDialogShellComponent;
  let fixture: ComponentFixture<WizardDialogShellComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WizardDialogShellComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(WizardDialogShellComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
  });

  it('hiển thị hộp thoại với role="dialog" và aria-modal="true" khi open=true', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const dialog = compiled.querySelector('[role="dialog"]');
    expect(dialog).toBeTruthy();
    expect(dialog?.getAttribute('aria-modal')).toBe('true');
  });

  it('phát sự kiện stepChange khi bấm vào các nút trên thanh 4-Step Stepper', () => {
    const stepSpy = vi.fn();
    component.stepChange.subscribe(stepSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const step3Btn = compiled.querySelector('[data-testid="wizard-step-btn-3"]') as HTMLButtonElement;
    expect(step3Btn).toBeTruthy();
    step3Btn.click();

    expect(stepSpy).toHaveBeenCalledWith(3);
  });

  it('hiển thị banner lỗi role="alert" khi có errorMessage', () => {
    fixture.componentRef.setInput('errorMessage', 'Không thể kết nối tới máy chủ AI.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const alertBox = compiled.querySelector('[role="alert"]');
    expect(alertBox).toBeTruthy();
    expect(alertBox?.textContent).toContain('Không thể kết nối tới máy chủ AI.');
  });

  it('hiển thị 2-Stage SSE Telemetry banner khi sseProgress đang PROCESSING', () => {
    fixture.componentRef.setInput('sseProgress', {
      status: 'PROCESSING',
      progressPercent: 68,
      message: 'Đang phân rã cột mốc kiến thức...',
      stage: 'STREAMING',
    });
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const sseBanner = compiled.querySelector('[data-testid="wizard-sse-banner"]');
    expect(sseBanner).toBeTruthy();
    expect(sseBanner?.textContent).toContain('68%');
    expect(sseBanner?.textContent).toContain('Đang phân rã cột mốc kiến thức...');
  });

  it('phát sự kiện closeDialog khi bấm phím Escape', () => {
    const closeSpy = vi.fn();
    component.closeDialog.subscribe(closeSpy);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(closeSpy).toHaveBeenCalled();
  });
});
