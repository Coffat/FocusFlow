import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SettingsService } from './settings.service';
import type { AIQuotaResponseDTO } from '../models/settings.model';

let mockStore: Record<string, string> = {};

const storageMock = {
  getItem: (key: string) => mockStore[key] ?? null,
  setItem: (key: string, value: string) => {
    mockStore[key] = value;
  },
  removeItem: (key: string) => {
    delete mockStore[key];
  },
  clear: () => {
    mockStore = {};
  },
  key: (index: number) => Object.keys(mockStore)[index] ?? null,
  length: 0,
};

describe('SettingsService', () => {
  let service: SettingsService;
  let httpMock: HttpTestingController;

  beforeAll(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: storageMock,
      writable: true,
      configurable: true,
    });
  });

  beforeEach(() => {
    storageMock.clear();
    TestBed.configureTestingModule({
      providers: [
        SettingsService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(SettingsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    storageMock.clear();
  });

  it('khởi tạo thành công SettingsService với cấu hình mặc định', () => {
    expect(service).toBeTruthy();
    expect(service.preferences().defaultPomodoroDuration).toBe(25);
    expect(service.preferences().shortBreakDuration).toBe(5);
    expect(service.preferences().longBreakDuration).toBe(15);
    expect(service.preferences().soundEnabled).toBe(true);
    expect(service.preferences().theme).toBe('light');
    expect(service.quota()).toBeNull();
  });

  it('savePreferences cập nhật signal và lưu trữ vào localStorage', () => {
    service.savePreferences({
      defaultPomodoroDuration: 45,
      soundEnabled: false,
    });

    expect(service.preferences().defaultPomodoroDuration).toBe(45);
    expect(service.preferences().soundEnabled).toBe(false);

    const stored = JSON.parse(storageMock.getItem('focusflow_user_preferences') || '{}');
    expect(stored.defaultPomodoroDuration).toBe(45);
    expect(stored.soundEnabled).toBe(false);
  });

  it('loadQuota tải thông tin quota AI từ backend thành công', async () => {
    const mockQuota: AIQuotaResponseDTO = {
      monthly_limit: 50,
      used_calls: 10,
      reserved_calls: 1,
      remaining_calls: 39,
      tokens_consumed: 12500,
      cycle_start: '2026-01-01T00:00:00Z',
      cycle_end: '2026-01-31T23:59:59Z',
    };

    const promise = service.loadQuota();
    const req = httpMock.expectOne('/api/v1/account/quota');
    expect(req.request.method).toBe('GET');
    req.flush(mockQuota);

    await promise;
    expect(service.quota()).toEqual(mockQuota);
    expect(service.quotaLoading()).toBe(false);
  });

  it('loadQuota dùng fallback an toàn khi backend báo lỗi', async () => {
    const promise = service.loadQuota();
    const req = httpMock.expectOne('/api/v1/account/quota');
    req.flush('Error', { status: 500, statusText: 'Server Error' });

    await promise;
    expect(service.quota()).toBeTruthy();
    expect(service.quota()?.monthly_limit).toBe(10);
    expect(service.quotaLoading()).toBe(false);
  });

  it('changePassword gửi POST /api/v1/account/change-password với credentials', async () => {
    const promise = service.changePassword({
      current_password: 'OldPassword123!',
      new_password: 'NewPassword456@',
    });

    const req = httpMock.expectOne('/api/v1/account/change-password');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      current_password: 'OldPassword123!',
      new_password: 'NewPassword456@',
    });
    req.flush({ message: 'Password updated successfully' });

    const result = await promise;
    expect(result.message).toBe('Password updated successfully');
  });

  it('resetWebCalToken trả về URL webcal mới', async () => {
    const res = await service.resetWebCalToken();
    expect(res.webcal_url).toContain('webcal://focusflow.app/api/v1/calendar/feed.ics?token=');
  });
});
