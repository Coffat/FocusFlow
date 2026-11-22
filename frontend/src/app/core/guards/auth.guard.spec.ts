import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  Router,
  RouterStateSnapshot,
  UrlTree,
  provideRouter,
} from '@angular/router';
import { Observable, firstValueFrom, of } from 'rxjs';
import { signal } from '@angular/core';
import { authGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

describe('authGuard (HttpOnly Cookie Session Verification)', () => {
  let router: Router;
  let isAuthenticatedSignal: ReturnType<typeof signal<boolean>>;
  let mockAuthService: {
    isAuthenticated: ReturnType<typeof signal<boolean>>;
    checkSession: ReturnType<typeof vi.fn>;
  };
  let mockStorage: Record<string, string> = {};

  const dummyRoute = {} as ActivatedRouteSnapshot;
  const dummyState = { url: '/dashboard' } as RouterStateSnapshot;

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
    isAuthenticatedSignal = signal<boolean>(false);
    mockAuthService = {
      isAuthenticated: isAuthenticatedSignal,
      checkSession: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: mockAuthService },
      ],
    });

    router = TestBed.inject(Router);
  });

  it('cho phép truy cập ngay lập tức khi isAuthenticated() là true mà không gọi checkSession()', () => {
    isAuthenticatedSignal.set(true);

    const result = TestBed.runInInjectionContext(() => authGuard(dummyRoute, dummyState));

    expect(result).toBe(true);
    expect(mockAuthService.checkSession).not.toHaveBeenCalled();
  });

  it('cho phép truy cập khi cold reload có cookie hợp lệ (checkSession trả về true)', async () => {
    isAuthenticatedSignal.set(false);
    mockAuthService.checkSession.mockReturnValue(of(true));

    const result$ = TestBed.runInInjectionContext(() =>
      authGuard(dummyRoute, dummyState)
    ) as Observable<boolean | UrlTree>;

    const allowed = await firstValueFrom(result$);
    expect(allowed).toBe(true);
    expect(mockAuthService.checkSession).toHaveBeenCalledTimes(1);
  });

  it('chuyển hướng về /sign-in khi phiên hết hạn NGAY CẢ KHI localStorage có access_token giả mạo', async () => {
    localStorage.setItem('access_token', 'forged');
    isAuthenticatedSignal.set(false);
    mockAuthService.checkSession.mockReturnValue(of(false));

    const result$ = TestBed.runInInjectionContext(() =>
      authGuard(dummyRoute, dummyState)
    ) as Observable<boolean | UrlTree>;

    const decision = await firstValueFrom(result$);
    expect(decision).toBeInstanceOf(UrlTree);
    expect(router.serializeUrl(decision as UrlTree)).toBe('/sign-in');
    expect(mockAuthService.checkSession).toHaveBeenCalledTimes(1);
  });
});
