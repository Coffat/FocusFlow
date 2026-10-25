import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { authGuard } from './auth.guard';
import { AuthService } from '../core/services/auth.service';

describe('authGuard', () => {
  let mockAuthService: { isAuthenticatedSubject: BehaviorSubject<boolean> };
  let mockRouter: { navigate: ReturnType<typeof vi.fn> };

  const dummyRoute = {} as ActivatedRouteSnapshot;
  const dummyState = {} as RouterStateSnapshot;

  beforeEach(() => {
    localStorage.clear();
    mockAuthService = {
      isAuthenticatedSubject: new BehaviorSubject<boolean>(false)
    };
    mockRouter = {
      navigate: vi.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: mockAuthService },
        { provide: Router, useValue: mockRouter }
      ]
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should allow activation when user is authenticated via authService', () => {
    mockAuthService.isAuthenticatedSubject.next(true);

    const result = TestBed.runInInjectionContext(() => authGuard(dummyRoute, dummyState));

    expect(result).toBe(true);
    expect(mockRouter.navigate).not.toHaveBeenCalled();
  });

  it('should allow activation when token exists in localStorage', () => {
    localStorage.setItem('access_token', 'valid-mock-jwt-token');

    const result = TestBed.runInInjectionContext(() => authGuard(dummyRoute, dummyState));

    expect(result).toBe(true);
    expect(mockRouter.navigate).not.toHaveBeenCalled();
  });

  it('should redirect to /sign-in and block activation when unauthenticated and no token', () => {
    mockAuthService.isAuthenticatedSubject.next(false);
    localStorage.removeItem('access_token');

    const result = TestBed.runInInjectionContext(() => authGuard(dummyRoute, dummyState));

    expect(result).toBe(false);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/sign-in']);
  });
});
