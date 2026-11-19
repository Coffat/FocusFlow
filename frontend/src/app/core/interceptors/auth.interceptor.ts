import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { BehaviorSubject, catchError, filter, switchMap, take, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { API_BASE_URL } from '../../constant/api.constant';

let isRefreshing = false;
const refreshTokenSubject = new BehaviorSubject<string | null>(null);

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  const isRelativeApi = req.url.startsWith('/api/v1');
  const isApiRequest =
    isRelativeApi ||
    req.url.startsWith(API_BASE_URL) ||
    req.url.startsWith('http://localhost:8000') ||
    req.url.startsWith('http://127.0.0.1:8000');

  const token = localStorage.getItem('access_token') || '';
  const headers: Record<string, string> = {};

  if (token.length > 0 && isApiRequest) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const targetUrl = isRelativeApi ? `${API_BASE_URL}${req.url.slice('/api/v1'.length)}` : req.url;

  // Always attach credentials for SameSite HttpOnly cookie authentication (ADR-008)
  const authReq = req.clone({
    url: targetUrl,
    withCredentials: isApiRequest,
    setHeaders: headers,
  });

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Avoid infinite loop or public session-probe redirect when refresh/login/me/logout returns 401
      if (
        error.status === 401 &&
        !req.url.includes('/api/v1/auth/refresh') &&
        !req.url.includes('/api/v1/auth/login') &&
        !req.url.includes('/api/v1/auth/me') &&
        !req.url.includes('/api/v1/auth/logout')
      ) {
        if (!isRefreshing) {
          isRefreshing = true;
          refreshTokenSubject.next(null);

          return authService.refreshToken().pipe(
            switchMap((response) => {
              isRefreshing = false;
              const newToken = response?.accessToken || localStorage.getItem('access_token') || '';
              refreshTokenSubject.next(newToken);

              const retryHeaders: Record<string, string> = {};
              if (newToken.length > 0) {
                retryHeaders['Authorization'] = `Bearer ${newToken}`;
              }
              const retriedReq = authReq.clone({ setHeaders: retryHeaders });
              return next(retriedReq);
            }),
            catchError((refreshErr) => {
              isRefreshing = false;
              refreshTokenSubject.next(null);
              authService.handleSessionExpired();
              return throwError(() => refreshErr);
            })
          );
        } else {
          // Concurrent request: wait for ongoing refresh to complete then retry with new token
          return refreshTokenSubject.pipe(
            filter((newToken) => newToken !== null),
            take(1),
            switchMap((newToken) => {
              const retryHeaders: Record<string, string> = {};
              if (newToken && newToken.length > 0) {
                retryHeaders['Authorization'] = `Bearer ${newToken}`;
              }
              const retriedReq = authReq.clone({ setHeaders: retryHeaders });
              return next(retriedReq);
            })
          );
        }
      }
      return throwError(() => error);
    })
  );
};


