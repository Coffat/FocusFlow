import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./components/admin-dashboard-page.component').then(
        m => m.AdminDashboardPageComponent
      )
  }
];
