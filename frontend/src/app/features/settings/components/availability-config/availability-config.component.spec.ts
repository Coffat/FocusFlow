import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AvailabilityConfigComponent } from './availability-config.component';
import { AvailabilityService } from '../../../../core/services/availability.service';

describe('AvailabilityConfigComponent', () => {
  let component: AvailabilityConfigComponent;
  let fixture: ComponentFixture<AvailabilityConfigComponent>;
  let service: AvailabilityService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AvailabilityConfigComponent],
      providers: [
        AvailabilityService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AvailabilityConfigComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(AvailabilityService);
    fixture.detectChanges();
  });

  it('khởi tạo component thành công và tải dữ liệu', () => {
    expect(component).toBeTruthy();
    expect(service.activeMode()).toBe('MODE_A');
    expect(service.totalWeeklyHours()).toBe(16.0);
  });

  it('hiển thị trạng thái loading có aria-busy="true" khi service.loading() === true', () => {
    service.loading.set(true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const loadingEl = compiled.querySelector('[aria-busy="true"]');
    expect(loadingEl).toBeTruthy();
  });

  it('cung cấp đầy đủ thuộc tính A11y (tablist, tab, switch, aria-pressed) và ô chọn allowed_window', () => {
    service.loading.set(false);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[role="tablist"]')).toBeTruthy();
    const modeATab = compiled.querySelector('[data-testid="mode-a-tab"]');
    expect(modeATab?.getAttribute('role')).toBe('tab');
    expect(modeATab?.getAttribute('aria-selected')).toBe('true');

    const mondaySwitch = compiled.querySelector('[data-testid="toggle-day-monday"]');
    expect(mondaySwitch?.getAttribute('role')).toBe('switch');
    expect(mondaySwitch?.getAttribute('aria-checked')).toBe('true');

    const awStart = compiled.querySelector('#allowed-window-start') as HTMLInputElement | null;
    const awEnd = compiled.querySelector('#allowed-window-end') as HTMLInputElement | null;
    expect(awStart).toBeTruthy();
    expect(awEnd).toBeTruthy();
  });

  it('chuyển đổi tab giữa Mode A và Mode B', () => {
    component.setMode('MODE_B');
    fixture.detectChanges();
    expect(service.activeMode()).toBe('MODE_B');

    component.setMode('MODE_A');
    fixture.detectChanges();
    expect(service.activeMode()).toBe('MODE_A');
  });

  it('áp dụng preset khi người dùng chọn nút preset', () => {
    service.applyPreset('BUSY_PRO');
    fixture.detectChanges();
    expect(service.totalWeeklyHours()).toBe(13.5);

    service.applyPreset('BOOTCAMPER');
    fixture.detectChanges();
    expect(service.totalWeeklyHours()).toBe(36.0);
  });

  it('sao chép Thứ 2 sang T3-T6 khi bấm nút sao chép', () => {
    service.updateDayQuota('monday', 4.5);
    service.copyMondayToWeekdays();
    fixture.detectChanges();

    expect(service.weeklySchedule().tuesday.quota_hours).toBe(4.5);
    expect(service.weeklySchedule().friday.quota_hours).toBe(4.5);
  });

  it('nút Lưu bị vô hiệu hóa khi tổng giờ tuần < 1.0h', () => {
    // Tắt các ngày để tổng giờ < 1.0h
    for (const d of ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] as const) {
      service.toggleDayEnabled(d);
    }
    service.updateDayQuota('monday', 0.5);
    fixture.detectChanges();

    expect(service.totalWeeklyHours()).toBe(0.5);
    expect(service.isWeeklyValid()).toBe(false);

    const compiled = fixture.nativeElement as HTMLElement;
    const saveButton = compiled.querySelector('button[size="lg"]') as HTMLButtonElement | null;
    expect(saveButton?.disabled).toBe(true);
  });

  it('gọi service.saveMyAvailability khi nhấn nút Lưu', () => {
    const saveSpy = vi.spyOn(service, 'saveMyAvailability');

    // Đảm bảo hợp lệ
    service.applyPreset('BUSY_PRO');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const buttons = compiled.querySelectorAll('button');
    const saveButton = Array.from(buttons).find(b => b.textContent?.includes('Lưu cấu hình thời gian rảnh'));

    expect(saveButton).toBeTruthy();
    saveButton?.click();

    expect(saveSpy).toHaveBeenCalled();
  });
});
