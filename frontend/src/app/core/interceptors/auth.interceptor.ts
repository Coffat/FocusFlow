import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

let isRefreshing = false;

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  // Always attach credentials for SameSite HttpOnly cookie authentication (ADR-008)
  const authReq = req.clone({
    withCredentials: true,
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
