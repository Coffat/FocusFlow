import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService, User } from './auth.service';
import { AUTH_ENDPOINTS } from '../../constant/api.constant';

describe('AuthService (Angular 21 Signals & State Reactivity)', () => {
  let service: AuthService;
  let httpTesting: HttpTestingController;
  let mockRouter: { navigate: ReturnType<typeof vi.fn> };
  let mockStorage: Record<string, string> = {};

  const mockUser: User = {
    id: 'user-uuid-1234',
    email: 'test@focusflow.io',
    fullName: 'Test User',
    role: 'learner',
    tier: 'free',
    createdAt: '2026-11-01T00:00:00Z'
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

  it('setUser() cập nhật signal currentUser và kích hoạt computed isAuthenticated chuyển sang true', () => {
    service.setUser(mockUser, 'test-access-token');

    expect(service.currentUser()).toEqual(mockUser);
    expect(service.isAuthenticated()).toBe(true);
    expect(localStorage.getItem('access_token')).toBe('test-access-token');
  });

  it('clearUser() đưa currentUser về null và isAuthenticated chuyển sang false, xoá token khỏi localStorage', () => {
    service.setUser(mockUser, 'test-access-token');
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

  it('checkSession() gọi HTTP GET /auth/me và cập nhật signals khi backend trả về session hợp lệ', () => {
    let sessionResult: boolean | undefined;
    service.checkSession().subscribe(res => {
      sessionResult = res;
    });

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

    expect(sessionResult).toBe(true);
    expect(service.currentUser()).toEqual({
      id: 'session-user-999',
      email: 'session@focusflow.io',
      fullName: 'Session User',
      role: 'learner',
      tier: 'pro',
      createdAt: '2026-11-02T10:00:00Z'
    });
    expect(service.isAuthenticated()).toBe(true);
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

  it('login() cập nhật signal isLoading trong suốt vòng đời request và cập nhật currentUser khi thành công', () => {
    expect(service.isLoading()).toBe(false);

    service.login({ email: 'test@focusflow.io', password: 'password123' }).subscribe();
    expect(service.isLoading()).toBe(true);

    const req = httpTesting.expectOne(AUTH_ENDPOINTS.LOGIN);
    expect(req.request.method).toBe('POST');
    req.flush({
      access_token: 'fake-jwt',
      token_type: 'bearer',
      user: {
        id: 'user-login-1',
        email: 'test@focusflow.io',
        full_name: 'Logged In User',
        role: 'learner',
        tier: 'free',
        created_at: '2026-11-01T00:00:00Z'
      }
    });

    expect(service.isLoading()).toBe(false);
    expect(service.currentUser()?.fullName).toBe('Logged In User');
    expect(service.isAuthenticated()).toBe(true);
    expect(localStorage.getItem('access_token')).toBe('fake-jwt');
  });

  it('handleSessionExpired() điều hướng người dùng về trang /sign-in với query param expired=1', () => {
    service.setUser(mockUser);
    service.handleSessionExpired();

    expect(service.currentUser()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/sign-in'], {
      queryParams: { expired: '1' }
    });
  });
});
