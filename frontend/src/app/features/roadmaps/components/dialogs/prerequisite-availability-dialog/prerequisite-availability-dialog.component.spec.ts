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

    const desc = compiled.querySelector('#prerequisite-dialog-desc');
    expect(desc?.textContent).toContain('Để AI có thể phân bổ lộ trình học tập chính xác');

    const contentText = compiled.textContent;
    expect(contentText).toContain('Lập lịch biểu thích ứng');
    expect(contentText).toContain('Khuyên dùng');
    expect(contentText).toContain('Tự động 2 chiều');

    const hybridCard = compiled.querySelector('[data-testid="option-card-hybrid"]');
    expect(hybridCard).toBeTruthy();
    expect(hybridCard?.getAttribute('role')).toBe('radio');
    expect(hybridCard?.getAttribute('aria-checked')).toBe('true');

    const calendarCard = compiled.querySelector('[data-testid="option-card-calendar"]');
    expect(calendarCard).toBeTruthy();
    expect(calendarCard?.getAttribute('role')).toBe('radio');
    expect(calendarCard?.getAttribute('aria-checked')).toBe('false');
  });

  it('tuân thủ 100% token thiết kế Architectural Focus từ docs/design.md', () => {
    componentRef.setInput('open', true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;

    // 1. Container & Backdrop styling
    const container = compiled.querySelector('[data-testid="prerequisite-dialog-container"]') as HTMLElement;
    expect(container).toBeTruthy();
    expect(container.className).toContain('rounded-xl');
    expect(container.className).toContain('bg-[#FFFFFF]');
    expect(container.className).toContain('border-[#DCDCDC]');
    expect(container.className).toContain('text-[#111111]');

    // 2. Micro-indicator header pill
    const microIndicator = container.querySelector('span.rounded-full[class*="border-[#246B4A]/20"]') as HTMLElement;
    expect(microIndicator).toBeTruthy();
    expect(microIndicator.className).toContain('bg-[#EBF3EE]');
    expect(microIndicator.className).toContain('text-[#246B4A]');
    expect(microIndicator.textContent).toContain('Lập lịch biểu thích ứng');
    const dotGlyph = microIndicator.querySelector('span.rounded-full[class*="bg-[#246B4A]"]');
    expect(dotGlyph).toBeTruthy();

    // 3. Title typography
    const title = compiled.querySelector('#prerequisite-dialog-title') as HTMLElement;
    expect(title.className).toContain('font-serif');
    expect(title.className).toContain('font-medium');
    expect(title.className).toContain('tracking-tight');
    expect(title.className).toContain('text-[#111111]');

    // 4. Action Cards & Radio tokens
    const hybridCard = compiled.querySelector('[data-testid="option-card-hybrid"]') as HTMLElement;
    const calendarCard = compiled.querySelector('[data-testid="option-card-calendar"]') as HTMLElement;

    expect(hybridCard.className).toContain('rounded-xl');
    expect(hybridCard.className).toContain('border-[#246B4A]');
    expect(hybridCard.className).toContain('bg-[#EBF3EE]/40');

    expect(calendarCard.className).toContain('rounded-xl');
    expect(calendarCard.className).toContain('border-[#DCDCDC]');
    expect(calendarCard.className).toContain('bg-[#FFFFFF]');

    // Card 1 Icon box & Badge
    const hybridIcon = hybridCard.querySelector('.rounded-lg') as HTMLElement;
    expect(hybridIcon.className).toContain('bg-[#EBF3EE]');
    expect(hybridIcon.className).toContain('text-[#246B4A]');

    const hybridBadge = hybridCard.querySelector('span.rounded-full.uppercase') as HTMLElement;
    expect(hybridBadge.className).toContain('bg-[#EBF3EE]');
    expect(hybridBadge.className).toContain('text-[#246B4A]');
    expect(hybridBadge.textContent).toContain('Khuyên dùng');

    // Card 2 Icon box & Badge (Slate Blue #315F83 semantics)
    const calendarIcon = calendarCard.querySelector('.rounded-lg') as HTMLElement;
    expect(calendarIcon.className).toContain('bg-[#F0F4F8]');
    expect(calendarIcon.className).toContain('text-[#315F83]');

    const calendarBadge = calendarCard.querySelector('span.rounded-full.uppercase') as HTMLElement;
    expect(calendarBadge.className).toContain('bg-[#F0F4F8]');
    expect(calendarBadge.className).toContain('text-[#315F83]');
    expect(calendarBadge.textContent).toContain('Tự động 2 chiều');

    // 5. Radio Checkmark active vs inactive
    const activeCheckmark = hybridCard.querySelector('.rounded-full[class*="bg-[#246B4A]"]') as HTMLElement;
    expect(activeCheckmark).toBeTruthy();
    expect(activeCheckmark.textContent).toContain('✓');

    const inactiveCheckmark = calendarCard.querySelector('.rounded-full[class*="border-[#DCDCDC]"]') as HTMLElement;
    expect(inactiveCheckmark).toBeTruthy();

    // 6. Primary and Secondary CTA Buttons
    const proceedBtn = compiled.querySelector('[data-testid="prerequisite-proceed-btn"]') as HTMLButtonElement;
    expect(proceedBtn.className).toContain('rounded-full');
    expect(proceedBtn.className).toContain('bg-[#246B4A]');
    expect(proceedBtn.className).toContain('hover:bg-[#1B5338]');
    expect(proceedBtn.className).toContain('text-white');

    const cancelBtn = compiled.querySelector('[data-testid="prerequisite-cancel-btn"]') as HTMLButtonElement;
    expect(cancelBtn.className).toContain('rounded-full');
    expect(cancelBtn.className).toContain('border-[#DCDCDC]');
    expect(cancelBtn.className).toContain('text-[#555555]');
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

    // When calendar selected, calendar gets active radio checkmark
    const activeCheckmark = calendarCard.querySelector('.rounded-full[class*="bg-[#246B4A]"]') as HTMLElement;
    expect(activeCheckmark).toBeTruthy();
    expect(activeCheckmark.textContent).toContain('✓');

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

  it('điều hướng sang /settings với query params và tab=calendar, focus=calendar khi chọn Google Calendar và bấm Tiến hành thiết lập', () => {
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
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/settings'], {
      queryParams: {
        tab: 'calendar',
        focus: 'calendar',
        returnUrl: '/dashboard',
        autoOpen: 'true',
      },
    });
  });

  it('hỗ trợ gọi directNavigate trực tiếp theo phương thức', () => {
    componentRef.setInput('open', true);
    componentRef.setInput('returnUrl', '/roadmaps');
    fixture.detectChanges();

    const actionSpy = vi.fn();
    const closeSpy = vi.fn();
    component.setupOptionSelected.subscribe(actionSpy);
    component.closeDialog.subscribe(closeSpy);

    component.directNavigate('calendar');

    expect(actionSpy).toHaveBeenCalledWith('calendar');
    expect(closeSpy).toHaveBeenCalled();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/settings'], {
      queryParams: {
        tab: 'calendar',
        focus: 'calendar',
        returnUrl: '/roadmaps',
        autoOpen: 'true',
      },
    });
  });

  it('hỗ trợ chọn option bằng bàn phím (Enter và Space)', () => {
    componentRef.setInput('open', true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const calendarCard = compiled.querySelector('[data-testid="option-card-calendar"]') as HTMLElement;

    calendarCard.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    fixture.detectChanges();
    expect(component.selectedOption()).toBe('calendar');

    const hybridCard = compiled.querySelector('[data-testid="option-card-hybrid"]') as HTMLElement;
    hybridCard.dispatchEvent(new KeyboardEvent('keydown', { key: ' ' }));
    fixture.detectChanges();
    expect(component.selectedOption()).toBe('hybrid');
  });
});
