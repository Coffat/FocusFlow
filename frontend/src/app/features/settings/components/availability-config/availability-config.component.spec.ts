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

  it('bật và tắt ca học 1-Click trong Mode B', () => {
    component.setMode('MODE_B');
    fixture.detectChanges();

    // Ban đầu thứ 2 chưa có ca sáng 08:00 - 11:30
    expect(component.isShiftActive('monday', '08:00', '11:30')).toBe(false);

    // Bấm chọn ca sáng 08:00 - 11:30
    component.toggleShift('monday', '08:00', '11:30');
    fixture.detectChanges();
    expect(component.isShiftActive('monday', '08:00', '11:30')).toBe(true);

    // Bấm lại ca sáng 08:00 - 11:30 -> gỡ bỏ
    component.toggleShift('monday', '08:00', '11:30');
    fixture.detectChanges();
    expect(component.isShiftActive('monday', '08:00', '11:30')).toBe(false);
  });

  it('điều chỉnh quỹ giờ linh hoạt với adjustDayQuota (+1h / -1h)', () => {
    const current = service.weeklySchedule().monday.quota_hours;
    component.adjustDayQuota('monday', 1.0);
    expect(service.weeklySchedule().monday.quota_hours).toBe(current + 1.0);

    component.adjustDayQuota('monday', -1.0);
    expect(service.weeklySchedule().monday.quota_hours).toBe(current);
  });

  it('khôi phục cài đặt mặc định với resetToDefault', () => {
    component.setMode('MODE_B');
    component.updateDayQuota('monday', 8.0);
    expect(service.activeMode()).toBe('MODE_B');

    component.resetToDefault();
    fixture.detectChanges();
    expect(service.activeMode()).toBe('MODE_A');
    expect(service.weeklySchedule().monday.quota_hours).toBe(2.0);
  });

  it('thay thế khung giờ chồng lấn khi chọn Ca Tối 1-Click (19:00 - 22:00) thay vì gây lỗi overlap', () => {
    component.setMode('MODE_B');
    fixture.detectChanges();

    // Ban đầu Monday có slot mặc định 19:30 - 21:30
    const initialSlots = service.weeklySchedule().monday.time_slots;
    expect(initialSlots.some(s => s.start === '19:30' && s.end === '21:30')).toBe(true);

    // Bấm chọn Ca Tối (19:00 - 22:00)
    component.toggleShift('monday', '19:00', '22:00');
    fixture.detectChanges();

    const updatedSlots = service.weeklySchedule().monday.time_slots;
    expect(component.isShiftActive('monday', '19:00', '22:00')).toBe(true);
    // Khung 19:30 - 21:30 chồng lấn đã được dọn sạch
    expect(updatedSlots.some(s => s.start === '19:30' && s.end === '21:30')).toBe(false);
    expect(service.dailyErrors().monday.length).toBe(0);
  });

  it('kích hoạt đồng thời cả 3 ca Sáng, Chiều, Tối trong Mode B đạt đúng 10.0h và không có lỗi', () => {
    component.setMode('MODE_B');
    fixture.detectChanges();

    component.toggleShift('monday', '08:00', '11:30'); // Sáng: 3.5h
    component.toggleShift('monday', '13:30', '17:00'); // Chiều: 3.5h
    component.toggleShift('monday', '19:00', '22:00'); // Tối: 3.0h (thay thế 19:30-21:30)
    fixture.detectChanges();

    const slots = service.weeklySchedule().monday.time_slots;
    expect(slots.length).toBe(3);
    expect(component.getDaySlotHours(slots)).toBe(10.0);
    expect(service.dailyErrors().monday.length).toBe(0);
  });

  it('kiểm tra trạng thái vô hiệu hóa của nút stepper +1h / +0.5h / -1h / -0.5h tại các biên', () => {
    // Đặt quota = 13.5h
    component.updateDayQuota('monday', 13.5);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const plusHalfBtn = compiled.querySelector('[data-testid="adjust-plus-half-monday"]') as HTMLButtonElement;
    const plus1hBtn = compiled.querySelector('[data-testid="adjust-plus-1h-monday"]') as HTMLButtonElement;

    // Tại 13.5h, +0.5h vẫn bấm được để lên 14.0h, nhưng +1h bị disable
    expect(plusHalfBtn.disabled).toBe(false);
    expect(plus1hBtn.disabled).toBe(true);

    // Tăng lên 14.0h
    component.adjustDayQuota('monday', 0.5);
    fixture.detectChanges();
    expect(plusHalfBtn.disabled).toBe(true);
    expect(plus1hBtn.disabled).toBe(true);

    // Đặt quota = 1.0h
    component.updateDayQuota('monday', 1.0);
    fixture.detectChanges();
    const minusHalfBtn = compiled.querySelector('[data-testid="adjust-minus-half-monday"]') as HTMLButtonElement;
    const minus1hBtn = compiled.querySelector('[data-testid="adjust-minus-1h-monday"]') as HTMLButtonElement;

    // Tại 1.0h, -0.5h bấm được để về 0.5h, nhưng -1h bị disable
    expect(minusHalfBtn.disabled).toBe(false);
    expect(minus1hBtn.disabled).toBe(true);

    // Giảm về 0.5h
    component.adjustDayQuota('monday', -0.5);
    fixture.detectChanges();
    expect(minusHalfBtn.disabled).toBe(true);
  });

  it('hỗ trợ điều hướng phím mũi tên giữa tab Mode A và Mode B (A11y)', () => {
    const eventRight = new KeyboardEvent('keydown', { key: 'ArrowRight' });
    component.onModeKeydown(eventRight, 'MODE_A');
    expect(service.activeMode()).toBe('MODE_B');

    const eventLeft = new KeyboardEvent('keydown', { key: 'ArrowLeft' });
    component.onModeKeydown(eventLeft, 'MODE_B');
    expect(service.activeMode()).toBe('MODE_A');
  });
});
