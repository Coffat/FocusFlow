import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../core/services/auth.service';

export const authGuard: CanActivateFn = (_route, _state) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const token = localStorage.getItem('access_token') || '';

  if (authService.isAuthenticatedSubject.value || token.length > 0) {
    return true;
  }

  router.navigate(['/sign-in']);
  return false;
};
