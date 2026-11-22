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
import { adminGuard } from './admin.guard';
import { AuthService, User } from '../services/auth.service';

describe('adminGuard (FE-MOCK-06 RBAC Route Gate)', () => {
  let router: Router;
  let isAuthenticatedSignal: ReturnType<typeof signal<boolean>>;
  let currentUserSignal: ReturnType<typeof signal<User | null>>;
  let mockAuthService: {
    isAuthenticated: ReturnType<typeof signal<boolean>>;
    currentUser: ReturnType<typeof signal<User | null>>;
    checkSession: ReturnType<typeof vi.fn>;
  };

  const dummyRoute = {} as ActivatedRouteSnapshot;
  const dummyState = { url: '/admin' } as RouterStateSnapshot;

  beforeEach(() => {
    isAuthenticatedSignal = signal<boolean>(false);
    currentUserSignal = signal<User | null>(null);
    mockAuthService = {
      isAuthenticated: isAuthenticatedSignal,
      currentUser: currentUserSignal,
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

  it('cho phép truy cập /admin khi người dùng hiện tại có role ADMIN', () => {
    isAuthenticatedSignal.set(true);
    currentUserSignal.set({
      id: 'admin-1',
      email: 'admin@focusflow.ai',
      fullName: 'Admin',
      role: 'admin',
      tier: 'PRO',
      createdAt: '2026-01-01T00:00:00Z',
    });

    const result = TestBed.runInInjectionContext(() => adminGuard(dummyRoute, dummyState));
    expect(result).toBe(true);
  });

  it('chuyển hướng người học (LEARNER) về /dashboard khi truy cập /admin', () => {
    isAuthenticatedSignal.set(true);
    currentUserSignal.set({
      id: 'learner-1',
      email: 'learner@focusflow.ai',
      fullName: 'Learner',
      role: 'learner',
      tier: 'FREE',
      createdAt: '2026-01-01T00:00:00Z',
    });

    const result = TestBed.runInInjectionContext(() => adminGuard(dummyRoute, dummyState));
    expect(result).toBeInstanceOf(UrlTree);
    expect(router.serializeUrl(result as UrlTree)).toBe('/dashboard');
  });

  it('gọi checkSession khi chưa xác thực và chuyển hướng về /dashboard nếu là learner', async () => {
    isAuthenticatedSignal.set(false);
    mockAuthService.checkSession.mockImplementation(() => {
      currentUserSignal.set({
        id: 'learner-2',
        email: 'learner2@focusflow.ai',
        fullName: 'Learner 2',
        role: 'learner',
        tier: 'FREE',
        createdAt: '2026-01-01T00:00:00Z',
      });
      return of(true);
    });

    const result$ = TestBed.runInInjectionContext(() =>
      adminGuard(dummyRoute, dummyState)
    ) as Observable<boolean | UrlTree>;

    const decision = await firstValueFrom(result$);
    expect(decision).toBeInstanceOf(UrlTree);
    expect(router.serializeUrl(decision as UrlTree)).toBe('/dashboard');
  });

  it('chuyển hướng về /sign-in nếu chưa đăng nhập và checkSession trả về false', async () => {
    isAuthenticatedSignal.set(false);
    mockAuthService.checkSession.mockReturnValue(of(false));

    const result$ = TestBed.runInInjectionContext(() =>
      adminGuard(dummyRoute, dummyState)
    ) as Observable<boolean | UrlTree>;

    const decision = await firstValueFrom(result$);
    expect(decision).toBeInstanceOf(UrlTree);
    expect(router.serializeUrl(decision as UrlTree)).toBe('/sign-in');
  });
});
