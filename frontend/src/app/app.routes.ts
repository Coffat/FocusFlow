import { Routes } from '@angular/router';
import { AuthLayoutComponent } from './layout/auth-layout/auth-layout.component';
import { MainLayoutComponent } from './layout/main-layout/main-layout.component';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    component: AuthLayoutComponent,
    children: [
      {
        path: '',
        redirectTo: 'sign-in',
        pathMatch: 'full'
      },
      {
        path: 'sign-in',
        loadComponent: () => import('./features/auth/sign-in/sign-in.component').then(m => m.SignInComponent)
      },
      {
        path: 'sign-up',
        loadComponent: () => import('./features/auth/sign-up/sign-up.component').then(m => m.SignUpComponent)
      },
      {
        path: 'forgot-password',
        loadComponent: () => import('./features/auth/forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent)
      },
      {
        path: 'verify-otp',
        loadComponent: () => import('./features/auth/otp-validation/otp-validation.component').then(m => m.OtpValidationComponent)
      },
      {
        path: 'otp-validation',
        redirectTo: 'verify-otp'
      }
    ]
  },
  {
    path: 'auth',
    component: AuthLayoutComponent,
    children: [
      {
        path: '',
        redirectTo: 'sign-in',
        pathMatch: 'full'
      },
      {
        path: 'login',
        redirectTo: 'sign-in'
      },
      {
        path: 'sign-in',
        loadComponent: () => import('./features/auth/sign-in/sign-in.component').then(m => m.SignInComponent)
      },
      {
        path: 'sign-up',
        loadComponent: () => import('./features/auth/sign-up/sign-up.component').then(m => m.SignUpComponent)
      },
      {
        path: 'forgot-password',
        loadComponent: () => import('./features/auth/forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent)
      },
      {
        path: 'verify-otp',
        loadComponent: () => import('./features/auth/otp-validation/otp-validation.component').then(m => m.OtpValidationComponent)
      }
    ]
  },
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent)
      },
      {
        path: 'roadmaps',
        loadChildren: () => import('./features/roadmaps/roadmaps.routes').then(m => m.ROADMAPS_ROUTES)
      },
      {
        path: 'workspace',
        loadChildren: () => import('./features/workspace/workspace.routes').then(m => m.WORKSPACE_ROUTES)
      },
      {
        path: 'schedule',
        loadChildren: () => import('./features/schedule/schedule.routes').then(m => m.SCHEDULE_ROUTES)
      },
      {
        path: 'availability',
        loadComponent: () => import('./features/settings/components/availability-config/availability-config.component').then(m => m.AvailabilityConfigComponent)
      },
      {
        path: 'tasks',
        loadChildren: () => import('./features/tasks/tasks.routes').then(m => m.TASKS_ROUTES)
      },
      {
        path: 'analytics',
        loadChildren: () => import('./features/analytics/analytics.routes').then(m => m.ANALYTICS_ROUTES)
      },
      {
        path: 'settings',
        loadChildren: () => import('./features/settings/settings.routes').then(m => m.SETTINGS_ROUTES)
      },
      {
        path: 'admin',
        loadChildren: () => import('./features/admin/admin.routes').then(m => m.ADMIN_ROUTES)
      }
    ]
  },
  {
    path: 'login',
    redirectTo: 'sign-in'
  },
  {
    path: 'register',
    redirectTo: 'sign-up'
  },
  {
    path: 'forgot-pass',
    redirectTo: 'forgot-password'
  },
  {
    path: '**',
    redirectTo: 'sign-in'
  }
];
