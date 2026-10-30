import { inject } from '@angular/core';
import { Router, CanActivateFn, UrlTree } from '@angular/router';
import { map, Observable, of } from 'rxjs';
import { AuthService } from '../core/services/auth.service';

export const authGuard: CanActivateFn = (_route, _state): boolean | UrlTree | Observable<boolean | UrlTree> => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const token = localStorage.getItem('access_token') || '';

  if (
    authService.isAuthenticatedSubject?.value ||
    (typeof authService.isAuthenticated === 'function' && authService.isAuthenticated()) ||
    (typeof authService.currentUser === 'function' && authService.currentUser() !== null) ||
    token.length > 0
  ) {
    return true;
  }

  if (typeof authService.checkSession === 'function') {
    return authService.checkSession().pipe(
      map((isAuthenticated) => {
        if (isAuthenticated) {
          return true;
        }
        router.navigate(['/sign-in']);
        return false;
      })
    );
  }

  router.navigate(['/sign-in']);
  return false;
};
