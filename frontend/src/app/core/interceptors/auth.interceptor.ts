import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { API_BASE_URL } from '../../constant/api.constant';

let isRefreshing = false;

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
      // Avoid infinite loop if refresh endpoint itself returns 401
      if (error.status === 401 && !req.url.includes('/api/v1/auth/refresh') && !req.url.includes('/api/v1/auth/login')) {
        if (!isRefreshing) {
          isRefreshing = true;
          return authService.refreshToken().pipe(
            switchMap(() => {
              isRefreshing = false;
              // Retry original request with credentials
              return next(authReq);
            }),
            catchError((refreshErr) => {
              isRefreshing = false;
              authService.handleSessionExpired();
              return throwError(() => refreshErr);
            })
          );
        }
      }
      return throwError(() => error);
    })
  );
};

