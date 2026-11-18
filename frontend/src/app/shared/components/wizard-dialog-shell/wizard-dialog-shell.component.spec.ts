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
    expect(compiled.textContent).toContain('Tạo lộ trình học tập');
    expect(compiled.querySelector('[data-testid="wizard-step-btn-5"]')).toBeNull();

    const step3Btn = compiled.querySelector('[data-testid="wizard-step-btn-3"]') as HTMLButtonElement;
    expect(step3Btn).toBeTruthy();
    step3Btn.click();
    expect(stepSpy).toHaveBeenCalledWith(3);

    const step4Btn = compiled.querySelector('[data-testid="wizard-step-btn-4"]') as HTMLButtonElement;
    expect(step4Btn).toBeTruthy();
    expect(step4Btn.textContent).toContain('4. Lịch học');
    step4Btn.click();
    expect(stepSpy).toHaveBeenCalledWith(4);
  });

  it('hiển thị banner lỗi role="alert" khi có errorMessage', () => {
    fixture.componentRef.setInput('errorMessage', 'Không thể kết nối tới máy chủ AI.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const alertBox = compiled.querySelector('[role="alert"]');
    expect(alertBox).toBeTruthy();
    expect(alertBox?.textContent).toContain('Không thể kết nối tới máy chủ AI.');
  });

  it('chỉ hiển thị nút đóng và phát sự kiện closeDialog khi bấm nút đóng hoặc Escape', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="wizard-sse-banner"]')).toBeNull();
    expect(compiled.querySelector('[data-testid="wizard-save-draft-btn"]')).toBeNull();

    const closeBtn = compiled.querySelector('[data-testid="wizard-close-btn"]') as HTMLButtonElement;
    expect(closeBtn).toBeTruthy();

    const closeSpy = vi.fn();
    component.closeDialog.subscribe(closeSpy);

    closeBtn.click();
    expect(closeSpy).toHaveBeenCalledTimes(1);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(closeSpy).toHaveBeenCalledTimes(2);
  });
});
