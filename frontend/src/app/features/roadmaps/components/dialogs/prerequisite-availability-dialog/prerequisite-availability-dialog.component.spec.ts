import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { ComponentRef } from '@angular/core';
import { PrerequisiteAvailabilityDialogComponent } from './prerequisite-availability-dialog.component';

describe('PrerequisiteAvailabilityDialogComponent', () => {
  let component: PrerequisiteAvailabilityDialogComponent;
  let componentRef: ComponentRef<PrerequisiteAvailabilityDialogComponent>;
  let fixture: ComponentFixture<PrerequisiteAvailabilityDialogComponent>;
  let mockRouter: {
    navigate: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    mockRouter = {
      navigate: vi.fn().mockResolvedValue(true),
    };

    await TestBed.configureTestingModule({
      imports: [PrerequisiteAvailabilityDialogComponent],
      providers: [
        { provide: Router, useValue: mockRouter },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PrerequisiteAvailabilityDialogComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it('không hiển thị dialog khi open() === false', () => {
    componentRef.setInput('open', false);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="prerequisite-dialog-container"]')).toBeFalsy();
  });

  it('hiển thị đầy đủ dialog và cấu trúc A11y khi open() === true', () => {
    componentRef.setInput('open', true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const dialogBackdrop = compiled.querySelector('[data-testid="prerequisite-dialog-backdrop"]');
    expect(dialogBackdrop).toBeTruthy();
    expect(dialogBackdrop?.getAttribute('role')).toBe('dialog');
    expect(dialogBackdrop?.getAttribute('aria-modal')).toBe('true');
    expect(dialogBackdrop?.getAttribute('aria-labelledby')).toBe('prerequisite-dialog-title');
    expect(dialogBackdrop?.getAttribute('aria-describedby')).toBe('prerequisite-dialog-desc');

    const title = compiled.querySelector('#prerequisite-dialog-title');
    expect(title?.textContent).toContain('Cần thiết lập Nguồn Thời gian Rảnh cho AI');

    const hybridCard = compiled.querySelector('[data-testid="option-card-hybrid"]');
    expect(hybridCard).toBeTruthy();
    expect(hybridCard?.getAttribute('role')).toBe('radio');
    expect(hybridCard?.getAttribute('aria-checked')).toBe('true');

    const calendarCard = compiled.querySelector('[data-testid="option-card-calendar"]');
    expect(calendarCard).toBeTruthy();
    expect(calendarCard?.getAttribute('role')).toBe('radio');
    expect(calendarCard?.getAttribute('aria-checked')).toBe('false');
  });

  it('cho phép chọn giữa 2 phương thức (Lịch lai vs Google Calendar)', () => {
    componentRef.setInput('open', true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const calendarCard = compiled.querySelector('[data-testid="option-card-calendar"]') as HTMLElement;
    calendarCard.click();
    fixture.detectChanges();

    expect(component.selectedOption()).toBe('calendar');
    expect(calendarCard.getAttribute('aria-checked')).toBe('true');

    const hybridCard = compiled.querySelector('[data-testid="option-card-hybrid"]') as HTMLElement;
    hybridCard.click();
    fixture.detectChanges();

    expect(component.selectedOption()).toBe('hybrid');
    expect(hybridCard.getAttribute('aria-checked')).toBe('true');
  });

  it('đóng dialog khi nhấn nút Đóng (X) hoặc nút Để sau', () => {
    componentRef.setInput('open', true);
    fixture.detectChanges();

    const closeSpy = vi.fn();
    component.closeDialog.subscribe(closeSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const closeBtn = compiled.querySelector('[data-testid="prerequisite-close-btn"]') as HTMLButtonElement;
    closeBtn.click();
    expect(closeSpy).toHaveBeenCalledTimes(1);

    const cancelBtn = compiled.querySelector('[data-testid="prerequisite-cancel-btn"]') as HTMLButtonElement;
    cancelBtn.click();
    expect(closeSpy).toHaveBeenCalledTimes(2);
  });

  it('đóng dialog khi nhấn phím Escape', () => {
    componentRef.setInput('open', true);
    fixture.detectChanges();

    const closeSpy = vi.fn();
    component.closeDialog.subscribe(closeSpy);

    component.onEscapeKey();
    expect(closeSpy).toHaveBeenCalledTimes(1);
  });

  it('đóng dialog khi click ra backdrop ngoài vùng container', () => {
    componentRef.setInput('open', true);
    fixture.detectChanges();

    const closeSpy = vi.fn();
    component.closeDialog.subscribe(closeSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const backdrop = compiled.querySelector('[data-testid="prerequisite-dialog-backdrop"]') as HTMLElement;
    backdrop.click();

    expect(closeSpy).toHaveBeenCalledTimes(1);
  });

  it('điều hướng sang /availability với query params khi chọn Lịch lai và bấm Tiến hành thiết lập', () => {
    componentRef.setInput('open', true);
    componentRef.setInput('returnUrl', '/roadmaps');
    fixture.detectChanges();

    const actionSpy = vi.fn();
    const closeSpy = vi.fn();
    component.setupOptionSelected.subscribe(actionSpy);
    component.closeDialog.subscribe(closeSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const proceedBtn = compiled.querySelector('[data-testid="prerequisite-proceed-btn"]') as HTMLButtonElement;
    proceedBtn.click();

    expect(actionSpy).toHaveBeenCalledWith('hybrid');
    expect(closeSpy).toHaveBeenCalled();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/availability'], {
      queryParams: {
        returnUrl: '/roadmaps',
        autoOpen: 'true',
      },
    });
  });

  it('điều hướng sang /availability với query params và focus=calendar khi chọn Google Calendar và bấm Tiến hành thiết lập', () => {
    componentRef.setInput('open', true);
    componentRef.setInput('returnUrl', '/dashboard');
    component.selectOption('calendar');
    fixture.detectChanges();

    const actionSpy = vi.fn();
    component.setupOptionSelected.subscribe(actionSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const proceedBtn = compiled.querySelector('[data-testid="prerequisite-proceed-btn"]') as HTMLButtonElement;
    proceedBtn.click();

    expect(actionSpy).toHaveBeenCalledWith('calendar');
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/availability'], {
      queryParams: {
        focus: 'calendar',
        returnUrl: '/dashboard',
        autoOpen: 'true',
      },
    });
  });

  it('hỗ trợ bấm nút trực tiếp trên từng thẻ để điều hướng nhanh', () => {
    componentRef.setInput('open', true);
    componentRef.setInput('returnUrl', '/roadmaps');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;

    // Bấm nút trực tiếp trên thẻ Google Calendar
    const directCalendarBtn = compiled.querySelector('[data-testid="direct-calendar-btn"]') as HTMLButtonElement;
    directCalendarBtn.click();

    expect(mockRouter.navigate).toHaveBeenCalledWith(['/availability'], {
      queryParams: {
        focus: 'calendar',
        returnUrl: '/roadmaps',
        autoOpen: 'true',
      },
    });

    // Bấm nút trực tiếp trên thẻ Lịch lai
    const directHybridBtn = compiled.querySelector('[data-testid="direct-hybrid-btn"]') as HTMLButtonElement;
    directHybridBtn.click();

    expect(mockRouter.navigate).toHaveBeenCalledWith(['/availability'], {
      queryParams: {
        returnUrl: '/roadmaps',
        autoOpen: 'true',
      },
    });
  });
});
