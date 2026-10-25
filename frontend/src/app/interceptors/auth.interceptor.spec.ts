import { TestBed } from '@angular/core/testing';
import { HttpRequest, HttpHandlerFn, HttpResponse } from '@angular/common/http';
import { of } from 'rxjs';
import { authInterceptor } from './auth.interceptor';
import { API_BASE_URL } from '../constant/api.constant';

describe('authInterceptor', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should set withCredentials=true and Authorization header for API requests when token exists', () => {
    localStorage.setItem('access_token', 'sample-jwt-token');

    const req = new HttpRequest('GET', `${API_BASE_URL}/auth/me`);
    const next: HttpHandlerFn = vi.fn((clonedReq) => of(new HttpResponse({ status: 200 })));

    TestBed.runInInjectionContext(() => {
      authInterceptor(req, next);
    });

    expect(next).toHaveBeenCalled();
    const calledReq = (next as ReturnType<typeof vi.fn>).mock.calls[0][0] as HttpRequest<unknown>;
    expect(calledReq.withCredentials).toBe(true);
    expect(calledReq.headers.get('Authorization')).toBe('Bearer sample-jwt-token');
  });

  it('should set withCredentials=true but no Authorization header when token is empty for API request', () => {
    localStorage.removeItem('access_token');

    const req = new HttpRequest('POST', `${API_BASE_URL}/auth/login`, {});
    const next: HttpHandlerFn = vi.fn((clonedReq) => of(new HttpResponse({ status: 200 })));

    TestBed.runInInjectionContext(() => {
      authInterceptor(req, next);
    });

    expect(next).toHaveBeenCalled();
    const calledReq = (next as ReturnType<typeof vi.fn>).mock.calls[0][0] as HttpRequest<unknown>;
    expect(calledReq.withCredentials).toBe(true);
    expect(calledReq.headers.has('Authorization')).toBe(false);
  });

  it('should set withCredentials=false for non-API requests (e.g. assets)', () => {
    const req = new HttpRequest('GET', '/assets/i18n/vi.json');
    const next: HttpHandlerFn = vi.fn((clonedReq) => of(new HttpResponse({ status: 200 })));

    TestBed.runInInjectionContext(() => {
      authInterceptor(req, next);
    });

    expect(next).toHaveBeenCalled();
    const calledReq = (next as ReturnType<typeof vi.fn>).mock.calls[0][0] as HttpRequest<unknown>;
    expect(calledReq.withCredentials).toBe(false);
  });
});
