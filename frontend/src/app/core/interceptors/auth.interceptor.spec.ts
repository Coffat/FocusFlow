import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpContext,
  HttpErrorResponse,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Subject, throwError } from 'rxjs';
import { AUTH_RETRY_ATTEMPTED, authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';
import { API_BASE_URL } from '../../constant/api.constant';

describe('authInterceptor (Pure HttpOnly Cookie & Concurrent 401 Queue)', () => {
  let http: HttpClient;
  let httpTesting: HttpTestingController;
  let mockAuthService: {
    refreshToken: ReturnType<typeof vi.fn>;
    handleSessionExpired: ReturnType<typeof vi.fn>;
  };
  let mockStorage: Record<string, string> = {};

  beforeAll(() => {
    const storageMock = {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, value: string) => {
        mockStorage[key] = value;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
      clear: () => {
        mockStorage = {};
      },
      key: (i: number) => Object.keys(mockStorage)[i] ?? null,
      length: 0,
    };
    Object.defineProperty(globalThis, 'localStorage', {
      value: storageMock,
      writable: true,
      configurable: true,
    });
  });

  beforeEach(() => {
    mockStorage = {};
    mockAuthService = {
      refreshToken: vi.fn(),
      handleSessionExpired: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: mockAuthService },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('gắn withCredentials: true cho API request và KHÔNG gắn header Authorization ngay cả khi localStorage có access_token', () => {
    localStorage.setItem('access_token', 'forged-or-stale-token');

    let responseBody: unknown;
    http.get('/api/v1/roadmaps').subscribe(res => {
      responseBody = res;
    });

    const req = httpTesting.expectOne(`${API_BASE_URL}/roadmaps`);
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({ items: [] });

    expect(responseBody).toEqual({ items: [] });
  });

  it('tự động refresh token và retry cả request gốc lẫn các request 401 đồng thời khi refresh thành công', () => {
    const refreshSubject = new Subject<unknown>();
    mockAuthService.refreshToken.mockReturnValue(refreshSubject.asObservable());

    let res1: unknown;
    let res2: unknown;

    http.get('/api/v1/roadmaps').subscribe(r => {
      res1 = r;
    });
    http.get('/api/v1/tasks').subscribe(r => {
      res2 = r;
    });

    const req1 = httpTesting.expectOne(`${API_BASE_URL}/roadmaps`);
    const req2 = httpTesting.expectOne(`${API_BASE_URL}/tasks`);

    // Both requests fail with 401; only ONE refreshToken() call should be triggered
    req1.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });
    req2.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(mockAuthService.refreshToken).toHaveBeenCalledTimes(1);

    // Refresh succeeds -> both queued requests retry with withCredentials and no Authorization header
    refreshSubject.next({ user: { id: 'u1' } });
    refreshSubject.complete();

    const retry1 = httpTesting.expectOne(`${API_BASE_URL}/roadmaps`);
    const retry2 = httpTesting.expectOne(`${API_BASE_URL}/tasks`);
    expect(retry1.request.withCredentials).toBe(true);
    expect(retry1.request.headers.has('Authorization')).toBe(false);
    expect(retry2.request.withCredentials).toBe(true);
    expect(retry2.request.headers.has('Authorization')).toBe(false);

    retry1.flush({ ok: 'roadmaps' });
    retry2.flush({ ok: 'tasks' });

    expect(res1).toEqual({ ok: 'roadmaps' });
    expect(res2).toEqual({ ok: 'tasks' });
    expect(mockAuthService.handleSessionExpired).not.toHaveBeenCalled();
  });

  it('trả lỗi dứt khoát cho tất cả request 401 đồng thời (không bị treo) khi refreshToken thất bại', () => {
    const refreshSubject = new Subject<unknown>();
    mockAuthService.refreshToken.mockReturnValue(refreshSubject.asObservable());

    let err1: HttpErrorResponse | null = null;
    let err2: HttpErrorResponse | null = null;

    http.get('/api/v1/roadmaps').subscribe({
      error: (err: HttpErrorResponse) => {
        err1 = err;
      },
    });
    http.get('/api/v1/tasks').subscribe({
      error: (err: HttpErrorResponse) => {
        err2 = err;
      },
    });

    const req1 = httpTesting.expectOne(`${API_BASE_URL}/roadmaps`);
    const req2 = httpTesting.expectOne(`${API_BASE_URL}/tasks`);

    req1.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });
    req2.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(mockAuthService.refreshToken).toHaveBeenCalledTimes(1);

    const refreshError = new HttpErrorResponse({
      status: 401,
      statusText: 'Refresh Expired',
    });
    refreshSubject.error(refreshError);

    expect(err1).toBeTruthy();
    expect(err2).toBeTruthy();
    expect(mockAuthService.handleSessionExpired).toHaveBeenCalledTimes(1);
    httpTesting.expectNone(`${API_BASE_URL}/roadmaps`);
    httpTesting.expectNone(`${API_BASE_URL}/tasks`);
  });

  it('không gọi refreshToken cho các endpoint /auth/refresh, /auth/login, /auth/me, /auth/logout khi trả 401', () => {
    mockAuthService.refreshToken.mockReturnValue(throwError(() => new Error('Should not run')));

    let caughtError: HttpErrorResponse | null = null;
    http.get('/api/v1/auth/me').subscribe({
      error: (err: HttpErrorResponse) => {
        caughtError = err;
      },
    });

    const req = httpTesting.expectOne(`${API_BASE_URL}/auth/me`);
    req.flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(caughtError).toBeTruthy();
    expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
  });

  it('áp dụng retry-once guard (AUTH_RETRY_ATTEMPTED) để không lặp vô hạn khi request retry vẫn trả 401', () => {
    const refreshSubject = new Subject<unknown>();
    mockAuthService.refreshToken.mockReturnValue(refreshSubject.asObservable());

    const errors: HttpErrorResponse[] = [];
    http.get('/api/v1/roadmaps').subscribe({
      error: (err: HttpErrorResponse) => {
        errors.push(err);
      },
    });

    const firstReq = httpTesting.expectOne(`${API_BASE_URL}/roadmaps`);
    firstReq.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(mockAuthService.refreshToken).toHaveBeenCalledTimes(1);

    refreshSubject.next({ user: { id: 'u1' } });
    refreshSubject.complete();

    const retryReq = httpTesting.expectOne(`${API_BASE_URL}/roadmaps`);
    expect(retryReq.request.context.get(AUTH_RETRY_ATTEMPTED)).toBe(true);
    retryReq.flush({ detail: 'Still Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(errors).toHaveLength(1);
    expect(errors[0].status).toBe(401);
    expect(mockAuthService.refreshToken).toHaveBeenCalledTimes(1);
  });

  it('không gọi refreshToken nếu request đã mang cờ AUTH_RETRY_ATTEMPTED', () => {
    const errors: HttpErrorResponse[] = [];
    http
      .get('/api/v1/roadmaps', {
        context: new HttpContext().set(AUTH_RETRY_ATTEMPTED, true),
      })
      .subscribe({
        error: (err: HttpErrorResponse) => {
          errors.push(err);
        },
      });

    const req = httpTesting.expectOne(`${API_BASE_URL}/roadmaps`);
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(errors).toHaveLength(1);
    expect(errors[0].status).toBe(401);
    expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
  });

  it('giải phóng cờ isRefreshing và giải thoát request đang chờ nếu subscriber khởi phát hủy đăng ký giữa chừng', () => {
    const refreshSubject = new Subject<unknown>();
    mockAuthService.refreshToken.mockReturnValue(refreshSubject.asObservable());

    const errors2: HttpErrorResponse[] = [];
    const sub1 = http.get('/api/v1/roadmaps').subscribe({ error: () => undefined });
    http.get('/api/v1/tasks').subscribe({
      error: (err: HttpErrorResponse) => {
        errors2.push(err);
      },
    });

    const req1 = httpTesting.expectOne(`${API_BASE_URL}/roadmaps`);
    const req2 = httpTesting.expectOne(`${API_BASE_URL}/tasks`);

    req1.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });
    req2.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(mockAuthService.refreshToken).toHaveBeenCalledTimes(1);

    // Initiating caller unsubscribes before refresh settles
    sub1.unsubscribe();

    expect(errors2).toHaveLength(1);
    expect(errors2[0].status).toBe(401);
  });
});
