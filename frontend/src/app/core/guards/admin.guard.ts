import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const adminGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return authService.currentUser()?.role?.toLowerCase() === 'admin'
      ? true
      : router.createUrlTree(['/dashboard']);
  }

  return authService.checkSession().pipe(
    map((isAuthed) => {
      if (!isAuthed) {
        return router.createUrlTree(['/sign-in']);
      }
      return authService.currentUser()?.role?.toLowerCase() === 'admin'
        ? true
        : router.createUrlTree(['/dashboard']);
    })
  );
};
