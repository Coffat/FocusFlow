import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full'
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES)
  },
  {
    path: 'dashboard',
    loadChildren: () => import('./features/dashboard/dashboard.routes').then(m => m.DASHBOARD_ROUTES)
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
    path: '**',
    redirectTo: 'dashboard'
  }
];
