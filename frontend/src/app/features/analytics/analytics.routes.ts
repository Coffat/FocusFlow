import { Routes } from '@angular/router';

export const ANALYTICS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./components/analytics-page.component').then(m => m.AnalyticsPageComponent)
  }
];
