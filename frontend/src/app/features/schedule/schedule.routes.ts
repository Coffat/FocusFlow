import { Routes } from '@angular/router';

export const SCHEDULE_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./components/schedule-page.component').then(m => m.SchedulePageComponent)
  }
];
