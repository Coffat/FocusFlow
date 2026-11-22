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

  it('loadQuota đặt quota về null và cập nhật quotaError khi backend báo lỗi (không dùng dữ liệu giả)', async () => {
    const promise = service.loadQuota();
    const req = httpMock.expectOne('/api/v1/account/quota');
    req.flush('Error', { status: 500, statusText: 'Server Error' });

    await promise;
    expect(service.quota()).toBeNull();
    expect(service.quotaError()).toBe('Không thể tải thông tin hạn ngạch AI. Vui lòng thử lại.');
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

  it('loadWebcalStatus tải trạng thái token WebCal thật từ backend', async () => {
    const promise = service.loadWebcalStatus();
    const req = httpMock.expectOne('/api/v1/account/calendar/webcal');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush({
      has_active_token: true,
      is_active: true,
      rotated_at: '2026-11-21T08:00:00Z',
      last_used_at: null,
    });

    await promise;
    expect(service.webcalStatus()?.has_active_token).toBe(true);
    expect(service.webcalUrl()).toBeNull();
    expect(service.webcalError()).toBeNull();
  });

  it('rotateWebcalToken gọi POST /api/v1/account/calendar/webcal/rotate và lưu URL một lần', async () => {
    const promise = service.rotateWebcalToken();
    const req = httpMock.expectOne('/api/v1/account/calendar/webcal/rotate');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush({
      webcal_url: 'webcal://localhost:8000/api/v1/feeds/real-token-abc.ics',
      feed_url: 'http://localhost:8000/api/v1/feeds/real-token-abc.ics',
      rotated_at: '2026-11-21T09:00:00Z',
    });

    const res = await promise;
    expect(res?.webcal_url).toBe('webcal://localhost:8000/api/v1/feeds/real-token-abc.ics');
    expect(service.webcalUrl()).toBe('webcal://localhost:8000/api/v1/feeds/real-token-abc.ics');
    expect(service.webcalStatus()?.has_active_token).toBe(true);
  });

  it('revokeWebcalToken gọi DELETE /api/v1/account/calendar/webcal và xóa URL khỏi state', async () => {
    service.webcalUrl.set('webcal://localhost:8000/api/v1/feeds/old.ics');
    const promise = service.revokeWebcalToken();
    const req = httpMock.expectOne('/api/v1/account/calendar/webcal');
    expect(req.request.method).toBe('DELETE');
    expect(req.request.withCredentials).toBe(true);
    req.flush({ revoked: true, is_active: false });

    const ok = await promise;
    expect(ok).toBe(true);
    expect(service.webcalUrl()).toBeNull();
    expect(service.webcalStatus()?.has_active_token).toBe(false);
  });

  it('loadWebcalStatus cập nhật webcalError khi backend lỗi', async () => {
    const promise = service.loadWebcalStatus();
    const req = httpMock.expectOne('/api/v1/account/calendar/webcal');
    req.flush('Error', { status: 500, statusText: 'Server Error' });

    await promise;
    expect(service.webcalError()).toBe('Không thể tải trạng thái liên kết WebCal. Vui lòng thử lại.');
  });

  it('FE-MOCK-03: exportAccountData gọi GET /api/v1/account/export với withCredentials và trả về snapshot thật', async () => {
    const mockSnapshot = {
      schema_version: '1.0',
      exported_at: '2026-11-21T09:30:00Z',
      user: {
        id: 'u-1',
        email: 'learner@focusflow.ai',
        full_name: 'Minh Hoàng',
        timezone: 'Asia/Ho_Chi_Minh',
        tier: 'FREE',
        role: 'LEARNER',
        created_at: '2026-01-01T00:00:00Z',
      },
      analytics_summary: {
        total_study_minutes: 120,
        current_streak_days: 3,
        longest_streak_days: 5,
      },
      study_sessions_count: 2,
      tasks_count: 4,
      roadmaps: [],
    };

    const promise = service.exportAccountData();
    expect(service.exportLoading()).toBe(true);

    const req = httpMock.expectOne('/api/v1/account/export');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush(mockSnapshot);

    const result = await promise;
    expect(result?.schema_version).toBe('1.0');
    expect(result?.user.email).toBe('learner@focusflow.ai');
    expect(service.exportLoading()).toBe(false);
    expect(service.exportError()).toBeNull();
  });

  it('FE-MOCK-03: exportAccountData trả về null và đặt exportError khi backend lỗi 500 (không fallback dữ liệu giả)', async () => {
    const promise = service.exportAccountData();
    const req = httpMock.expectOne('/api/v1/account/export');
    req.flush('Internal Server Error', { status: 500, statusText: 'Server Error' });

    const result = await promise;
    expect(result).toBeNull();
    expect(service.exportLoading()).toBe(false);
    expect(service.exportError()).toBe('Không thể xuất dữ liệu cá nhân lúc này. Vui lòng thử lại sau.');
  });
});
