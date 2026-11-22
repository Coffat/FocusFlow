import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService, User } from './auth.service';
import { AUTH_ENDPOINTS } from '../../constant/api.constant';

describe('AuthService (Angular 21 Signals & HttpOnly Cookie Auth)', () => {
  let service: AuthService;
  let httpTesting: HttpTestingController;
  let mockRouter: { url: string; navigate: ReturnType<typeof vi.fn> };
  let mockStorage: Record<string, string> = {};

  const mockUser: User = {
    id: 'user-uuid-1234',
    email: 'test@focusflow.io',
    fullName: 'Test User',
    role: 'learner',
    tier: 'free',
    createdAt: '2026-11-01T00:00:00Z'
  };

  const mockBackendAuthResponse = {
    access_token: 'server-issued-jwt',
    token_type: 'bearer',
    expires_in: 900,
    user: {
      id: 'user-login-1',
      email: 'test@focusflow.io',
      full_name: 'Logged In User',
      role: 'learner',
      tier: 'free',
      created_at: '2026-11-01T00:00:00Z'
    }
  };

  beforeAll(() => {
    const storageMock = {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, value: string) => { mockStorage[key] = value; },
      removeItem: (key: string) => { delete mockStorage[key]; },
      clear: () => { mockStorage = {}; },
      key: (i: number) => Object.keys(mockStorage)[i] ?? null,
      length: 0
    };
    Object.defineProperty(globalThis, 'localStorage', {
      value: storageMock,
      writable: true,
      configurable: true
    });
  });

  beforeEach(() => {
    TestBed.resetTestingModule();
    mockStorage = {};
    mockRouter = {
      url: '/dashboard',
      navigate: vi.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: mockRouter }
      ]
    });

    service = TestBed.inject(AuthService);
    httpTesting = TestBed.inject(HttpTestingController);

    // Consume the initial checkSession call triggered by constructor's initAuth
    const initialReq = httpTesting.expectOne(AUTH_ENDPOINTS.ME);
    initialReq.flush(null, { status: 401, statusText: 'Unauthorized' });
  });

  afterEach(() => {
    httpTesting.verify();
    TestBed.resetTestingModule();
  });

  it('khởi tạo với trạng thái ban đầu: currentUser là null, isAuthenticated là false, isLoading là false', () => {
    expect(service.currentUser()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(service.isLoading()).toBe(false);
  });

  it('setUser() cập nhật signal currentUser, kích hoạt isAuthenticated và KHÔNG lưu access_token vào localStorage', () => {
    service.setUser(mockUser);

    expect(service.currentUser()).toEqual(mockUser);
    expect(service.isAuthenticated()).toBe(true);
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('clearUser() đưa currentUser về null và isAuthenticated chuyển sang false', () => {
    service.setUser(mockUser);
    expect(service.isAuthenticated()).toBe(true);

    service.clearUser();

    expect(service.currentUser()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('checkSession() trả về true ngay lập tức mà không gọi HTTP nếu currentUser đã có dữ liệu', () => {
    service.setUser(mockUser);

    let sessionResult: boolean | undefined;
    service.checkSession().subscribe(res => {
      sessionResult = res;
    });

    expect(sessionResult).toBe(true);
    httpTesting.expectNone(AUTH_ENDPOINTS.ME);
  });

  it('checkSession() gộp nhiều subscriber đồng thời thành 1 HTTP GET /auth/me duy nhất (shareReplay) và reset sau finalize', () => {
    let sub1Result: boolean | undefined;
    let sub2Result: boolean | undefined;

    service.checkSession().subscribe(res => {
      sub1Result = res;
    });
    service.checkSession().subscribe(res => {
      sub2Result = res;
    });

    // Only ONE HTTP request must be issued for concurrent callers (e.g. initAuth + authGuard)
    const req = httpTesting.expectOne(AUTH_ENDPOINTS.ME);
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);

    req.flush({
      id: 'session-user-999',
      email: 'session@focusflow.io',
      full_name: 'Session User',
      role: 'learner',
      tier: 'pro',
      created_at: '2026-11-02T10:00:00Z'
    });

    expect(sub1Result).toBe(true);
    expect(sub2Result).toBe(true);
    expect(service.currentUser()).toEqual({
      id: 'session-user-999',
      email: 'session@focusflow.io',
      fullName: 'Session User',
      role: 'learner',
      tier: 'pro',
      createdAt: '2026-11-02T10:00:00Z'
    });
    expect(service.isAuthenticated()).toBe(true);

    // After clearing user, a subsequent checkSession() issues a fresh GET /auth/me (finalize cleared cache)
    service.clearUser();
    let sub3Result: boolean | undefined;
    service.checkSession().subscribe(res => {
      sub3Result = res;
    });

    const secondReq = httpTesting.expectOne(AUTH_ENDPOINTS.ME);
    secondReq.flush(null, { status: 401, statusText: 'Unauthorized' });
    expect(sub3Result).toBe(false);
  });

  it('checkSession() xử lý lỗi 401/500, xoá session và trả về false', () => {
    let sessionResult: boolean | undefined;
    service.checkSession().subscribe(res => {
      sessionResult = res;
    });

    const req = httpTesting.expectOne(AUTH_ENDPOINTS.ME);
    req.flush({ detail: 'Token expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(sessionResult).toBe(false);
    expect(service.currentUser()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('login() / signIn() dùng withCredentials và không lưu access_token vào localStorage', () => {
    expect(service.isLoading()).toBe(false);

    service.login({ email: 'test@focusflow.io', password: 'password123' }).subscribe();
    expect(service.isLoading()).toBe(true);

    const loginReq = httpTesting.expectOne(AUTH_ENDPOINTS.LOGIN);
    expect(loginReq.request.method).toBe('POST');
    expect(loginReq.request.withCredentials).toBe(true);
    loginReq.flush(mockBackendAuthResponse);

    expect(service.isLoading()).toBe(false);
    expect(service.currentUser()?.fullName).toBe('Logged In User');
    expect(service.isAuthenticated()).toBe(true);
    expect(localStorage.getItem('access_token')).toBeNull();

    service.signIn({ email: 'test@focusflow.io', password: 'password123', rememberMe: true }).subscribe();
    const signInReq = httpTesting.expectOne(AUTH_ENDPOINTS.LOGIN);
    expect(signInReq.request.withCredentials).toBe(true);
    signInReq.flush(mockBackendAuthResponse);
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('signUp(), refreshToken(), signOut() dùng withCredentials và không ghi access_token vào localStorage', () => {
    service.signUp({ fullName: 'Test User', email: 'test@focusflow.io', password: 'Password123!' }).subscribe();
    const regReq = httpTesting.expectOne(AUTH_ENDPOINTS.REGISTER);
    expect(regReq.request.withCredentials).toBe(true);
    regReq.flush(mockBackendAuthResponse);
    expect(service.isAuthenticated()).toBe(true);
    expect(localStorage.getItem('access_token')).toBeNull();

    service.refreshToken().subscribe();
    const refreshReq = httpTesting.expectOne(AUTH_ENDPOINTS.REFRESH_TOKEN);
    expect(refreshReq.request.withCredentials).toBe(true);
    refreshReq.flush(mockBackendAuthResponse);
    expect(service.isAuthenticated()).toBe(true);
    expect(localStorage.getItem('access_token')).toBeNull();

    service.signOut();
    const logoutReq = httpTesting.expectOne(AUTH_ENDPOINTS.LOGOUT);
    expect(logoutReq.request.withCredentials).toBe(true);
    logoutReq.flush({});
    expect(service.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('handleSessionExpired() điều hướng người dùng về trang /sign-in với query param expired=1 khi đang ở trang được bảo vệ', () => {
    mockRouter.url = '/dashboard';
    service.setUser(mockUser);
    service.handleSessionExpired();

    expect(service.currentUser()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/sign-in'], {
      queryParams: { expired: '1' }
    });
  });

  it('handleSessionExpired() chỉ clearSession mà không điều hướng khi đang ở trang công khai (/features, /, /auth/*)', () => {
    for (const publicUrl of ['/', '/features?tab=1', '/how-it-works#top', '/pricing', '/faq', '/auth/sign-in']) {
      mockRouter.navigate.mockClear();
      mockRouter.url = publicUrl;
      service.setUser(mockUser);

      service.handleSessionExpired();

      expect(service.currentUser()).toBeNull();
      expect(service.isAuthenticated()).toBe(false);
      expect(mockRouter.navigate).not.toHaveBeenCalled();
    }
  });
});
