import { HttpContextToken, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Subject, catchError, finalize, switchMap, take, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { API_BASE_URL } from '../../constant/api.constant';

/**
 * Retry-once guard so a request that already retried after a refresh
 * never triggers a second refresh cycle if it still receives 401.
 */
export const AUTH_RETRY_ATTEMPTED = new HttpContextToken<boolean>(() => false);

let isRefreshing = false;
const refreshResultSubject = new Subject<boolean>();

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  const isRelativeApi = req.url.startsWith('/api/v1');
  const isApiRequest =
    isRelativeApi ||
    req.url.startsWith(API_BASE_URL) ||
    req.url.startsWith('http://localhost:8000') ||
    req.url.startsWith('http://127.0.0.1:8000');

  const targetUrl = isRelativeApi ? `${API_BASE_URL}${req.url.slice('/api/v1'.length)}` : req.url;

  // Always rely on SameSite HttpOnly cookies for API authentication (ADR-008)
  const authReq = req.clone({
    url: targetUrl,
    withCredentials: isApiRequest,
  });

  const buildRetryReq = () =>
    authReq.clone({
      context: authReq.context.set(AUTH_RETRY_ATTEMPTED, true),
    });

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Avoid infinite loop or public session-probe redirect when refresh/login/me/logout returns 401
      if (
        error.status === 401 &&
        !req.context.get(AUTH_RETRY_ATTEMPTED) &&
        !req.url.includes('/api/v1/auth/refresh') &&
        !req.url.includes('/api/v1/auth/login') &&
        !req.url.includes('/api/v1/auth/me') &&
        !req.url.includes('/api/v1/auth/logout')
      ) {
        if (!isRefreshing) {
          isRefreshing = true;
          let settled = false;

          return authService.refreshToken().pipe(
            switchMap(() => {
              settled = true;
              isRefreshing = false;
              refreshResultSubject.next(true);
              return next(buildRetryReq());
            }),
            catchError((refreshErr) => {
              settled = true;
              isRefreshing = false;
              refreshResultSubject.next(false);
              authService.handleSessionExpired();
              return throwError(() => refreshErr);
            }),
            finalize(() => {
              if (!settled && isRefreshing) {
                isRefreshing = false;
                refreshResultSubject.next(false);
              }
            })
          );
        } else {
          // Concurrent request: wait for ongoing refresh result, then retry once or fail cleanly
          return refreshResultSubject.pipe(
            take(1),
            switchMap((refreshed) => (refreshed ? next(buildRetryReq()) : throwError(() => error)))
          );
        }
      }
      return throwError(() => error);
    })
  );
};
