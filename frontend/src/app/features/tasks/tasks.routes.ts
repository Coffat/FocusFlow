import { Routes } from '@angular/router';

export const TASKS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./components/tasks-page.component').then(m => m.TasksPageComponent)
  }
];
