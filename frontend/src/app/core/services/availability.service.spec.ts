import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import {
  AvailabilityService,
   DAYS_OF_WEEK,
  calculateDurationMinutes,
  createDefaultSchedule
} from './availability.service';
import { API_ENDPOINTS } from '../constants/api-endpoints';
import { AvailabilityResponseDTO } from '../models/availability.model';

describe('calculateDurationMinutes', () => {
  it('tính đúng số phút giữa hai mốc giờ trong ngày', () => {
    expect(calculateDurationMinutes('19:30', '21:30')).toBe(120);
    expect(calculateDurationMinutes('08:30', '11:00')).toBe(150);
  });

  it('xử lý đúng khung giờ qua đêm với end_day_offset = 1', () => {
    expect(calculateDurationMinutes('23:00', '01:00', 1)).toBe(120);
    expect(calculateDurationMinutes('22:30', '02:00', 1)).toBe(210);
  });

  it('trả về 0 nếu giờ bắt đầu sau giờ kết thúc mà không có offset', () => {
    expect(calculateDurationMinutes('22:00', '20:00', 0)).toBe(0);
  });
});

describe('AvailabilityService', () => {
  let service: AvailabilityService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        AvailabilityService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });

    service = TestBed.inject(AvailabilityService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('khởi tạo với cấu hình mặc định hợp lệ khớp 100% với Backend (19:30-21:30 T2-T6, 14:00-17:00 T7-CN)', () => {
    expect(service.activeMode()).toBe('MODE_A');
    expect(service.totalWeeklyHours()).toBe(16.0);
    expect(service.isWeeklyValid()).toBe(true);
    expect(service.dailyErrors().monday.length).toBe(0);
    expect(service.weeklySchedule().monday.time_slots[0]).toEqual({
      start: '19:30',
      end: '21:30',
      end_day_offset: 0
    });
    expect(service.weeklySchedule().saturday.time_slots[0]).toEqual({
      start: '14:00',
      end: '17:00',
      end_day_offset: 0
    });
  });

  it('tính đúng tổng thời gian rảnh khi chuyển sang Mode B', () => {
    service.setMode('MODE_B');
    // Default schedule có: T2-T6: 2h/ngày, T7-CN: 3h/ngày = 16.0h
    expect(service.totalWeeklyHours()).toBe(16.0);
    expect(service.isWeeklyValid()).toBe(true);
  });

  it('addTimeSlot() trên ngày mặc định (19:30-21:30) tạo slot mới không chồng lấn', () => {
    service.setMode('MODE_B');
    service.addTimeSlot('monday');

    const slots = service.weeklySchedule().monday.time_slots;
    expect(slots.length).toBe(2);
    expect(slots[0]).toEqual({ start: '19:30', end: '21:30', end_day_offset: 0 });
    expect(slots[1]).toEqual({ start: '21:30', end: '23:00', end_day_offset: 0 });
    expect(service.dailyErrors().monday).toEqual([]);
    expect(service.isWeeklyValid()).toBe(true);
  });

  it('áp dụng thành công Preset 1: BUSY_PRO (13.5h)', () => {
    service.applyPreset('BUSY_PRO');

    service.setMode('MODE_A');
    expect(service.totalWeeklyHours()).toBe(13.5);
    expect(service.isWeeklyValid()).toBe(true);

    service.setMode('MODE_B');
    expect(service.totalWeeklyHours()).toBe(13.5);
    expect(service.isWeeklyValid()).toBe(true);
  });

  it('áp dụng thành công Preset 2: UNI_STUDENT (15.5h) và bật lại ngày nghỉ tuesday không gây lỗi validation', () => {
    service.applyPreset('UNI_STUDENT');

    service.setMode('MODE_A');
    expect(service.totalWeeklyHours()).toBe(15.5);
    expect(service.weeklySchedule().tuesday.enabled).toBe(false);
    expect(service.weeklySchedule().thursday.enabled).toBe(false);
    expect(service.isWeeklyValid()).toBe(true);

    // Bật lại ngày nghỉ tuesday ở cả Mode A và Mode B đều có sẵn cấu hình hợp lệ
    service.toggleDayEnabled('tuesday');
    expect(service.weeklySchedule().tuesday.enabled).toBe(true);
    expect(service.weeklySchedule().tuesday.quota_hours).toBe(2.0);
    expect(service.dailyErrors().tuesday).toEqual([]);
    expect(service.isWeeklyValid()).toBe(true);

    service.setMode('MODE_B');
    expect(service.dailyErrors().tuesday).toEqual([]);
    expect(service.isWeeklyValid()).toBe(true);
  });

  it('áp dụng thành công Preset 3: BOOTCAMPER (36.0h) và bật lại ngày nghỉ sunday không gây lỗi validation', () => {
    service.applyPreset('BOOTCAMPER');

    service.setMode('MODE_A');
    expect(service.totalWeeklyHours()).toBe(36.0);
    expect(service.weeklySchedule().sunday.enabled).toBe(false);
    expect(service.isWeeklyValid()).toBe(true);

    service.toggleDayEnabled('sunday');
    expect(service.dailyErrors().sunday).toEqual([]);
    expect(service.isWeeklyValid()).toBe(true);

    service.setMode('MODE_B');
    expect(service.dailyErrors().sunday).toEqual([]);
    expect(service.isWeeklyValid()).toBe(true);
  });

  it('setAllowedWindow và setMinSessionMinutes đồng bộ xuống cả 7 ngày trong weeklySchedule()', () => {
    service.setAllowedWindow('06:30', '22:30');
    service.setMinSessionMinutes(45);

    expect(service.allowedWindow()).toEqual({ start: '06:30', end: '22:30' });
    expect(service.minSessionMinutes()).toBe(45);

    const sched = service.weeklySchedule();
    for (const day of DAYS_OF_WEEK) {
      expect(sched[day].allowed_window).toEqual({ start: '06:30', end: '22:30' });
      expect(sched[day].min_session_minutes).toBe(45);
    }
  });

  it('sao chép Thứ 2 sang T3-T6 chuẩn xác với copyMondayToWeekdays', () => {
    service.updateDayQuota('monday', 5.0);
    service.updateDayPeriod('monday', 'MORNING');

    service.copyMondayToWeekdays();

    const sched = service.weeklySchedule();
    expect(sched.tuesday.quota_hours).toBe(5.0);
    expect(sched.tuesday.preferred_period).toBe('MORNING');
    expect(sched.wednesday.quota_hours).toBe(5.0);
    expect(sched.thursday.quota_hours).toBe(5.0);
    expect(sched.friday.quota_hours).toBe(5.0);
  });

  it('bắt lỗi Mode A khi quota < 0.5h, > 14.0h hoặc allowed_window không hợp lệ', () => {
    service.setMode('MODE_A');

    // Vi phạm cận dưới < 0.5h
    service.updateDayQuota('monday', 0.4);
    expect(service.dailyErrors().monday.length).toBeGreaterThan(0);
    expect(service.isWeeklyValid()).toBe(false);

    // Hợp lệ cận dưới 0.5h
    service.updateDayQuota('monday', 0.5);
    expect(service.dailyErrors().monday.length).toBe(0);

    // Vi phạm cận trên > 14.0h
    service.updateDayQuota('monday', 14.5);
    expect(service.dailyErrors().monday.length).toBeGreaterThan(0);
    expect(service.isWeeklyValid()).toBe(false);

    // Khôi phục quota hợp lệ, kiểm tra lỗi allowed_window end <= start
    service.updateDayQuota('monday', 2.0);
    service.setAllowedWindow('22:00', '08:00');
    expect(service.dailyErrors().monday.length).toBeGreaterThan(0);
    expect(service.isWeeklyValid()).toBe(false);

    // Khôi phục allowed_window hợp lệ
    service.setAllowedWindow('07:00', '23:00');
    expect(service.dailyErrors().monday.length).toBe(0);

    // Tắt ngày -> không báo lỗi
    service.updateDayQuota('monday', 14.5);
    service.toggleDayEnabled('monday');
    expect(service.dailyErrors().monday.length).toBe(0);
  });

  it('bắt lỗi Mode B khi slot < 30 phút hoặc 2 slot chồng lấn', () => {
    service.setMode('MODE_B');

    // Slot < 30m
    service.updateTimeSlot('monday', 0, 'start', '20:00');
    service.updateTimeSlot('monday', 0, 'end', '20:20');
    expect(service.dailyErrors().monday.length).toBeGreaterThan(0);
    expect(service.isWeeklyValid()).toBe(false);

    // Sửa thành hợp lệ
    service.updateTimeSlot('monday', 0, 'end', '21:00');
    expect(service.dailyErrors().monday.length).toBe(0);

    // Thêm slot thứ 2 chồng lấn [20:30 - 22:00] chồng lên [20:00 - 21:00]
    service.addTimeSlot('monday');
    const lastIndex = service.weeklySchedule().monday.time_slots.length - 1;
    service.updateTimeSlot('monday', lastIndex, 'start', '20:30');
    service.updateTimeSlot('monday', lastIndex, 'end', '22:00');

    expect(service.dailyErrors().monday).toContain('Có khung giờ bị chồng lấn nhau trong ngày.');
    expect(service.isWeeklyValid()).toBe(false);
  });

  it('bắt lỗi khi tổng giờ rảnh cả tuần < 1.0h', () => {
    service.setMode('MODE_A');
    // Tắt tất cả các ngày trừ Monday 0.5h
    for (const d of ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] as const) {
      service.toggleDayEnabled(d);
    }
    service.updateDayQuota('monday', 0.5);

    expect(service.totalWeeklyHours()).toBe(0.5);
    expect(service.isWeeklyValid()).toBe(false);
  });

  it('gọi API GET loadMyAvailability và cập nhật state', () => {
    const mockRes: AvailabilityResponseDTO = {
      id: 'avail-123',
      user_id: 'user-456',
      mode: 'MODE_B',
      calendar_integration_mode: 'CONNECTED',
      min_session_minutes: 45,
      weekly_schedule: createDefaultSchedule(),
      total_weekly_hours: 16.0,
      updated_at: '2026-10-28T00:00:00Z'
    };

    service.loadMyAvailability();

    const req = httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY);
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);

    req.flush(mockRes);

    expect(service.profile()?.id).toBe('avail-123');
    expect(service.activeMode()).toBe('MODE_B');
    expect(service.calendarIntegrationMode()).toBe('CONNECTED');
    expect(service.minSessionMinutes()).toBe(45);
  });

  it('gọi API PUT saveMyAvailability thành công', () => {
    const mockRes: AvailabilityResponseDTO = {
      id: 'avail-123',
      user_id: 'user-456',
      mode: 'MODE_A',
      calendar_integration_mode: 'NONE',
      min_session_minutes: 30,
      weekly_schedule: service.weeklySchedule(),
      total_weekly_hours: 16.0,
      updated_at: '2026-10-28T00:00:00Z'
    };

    service.saveMyAvailability();

    const req = httpTesting.expectOne(API_ENDPOINTS.SETTINGS.AVAILABILITY);
    expect(req.request.method).toBe('PUT');
    expect(req.request.withCredentials).toBe(true);

    req.flush(mockRes);

    expect(service.saveSuccessMessage()).toBe('Đã lưu cấu hình thời gian rảnh thành công!');
    expect(service.saving()).toBe(false);
  });
});
