import { Routes } from '@angular/router';

export const ROADMAPS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./components/roadmap-page.component').then(m => m.RoadmapPageComponent)
  }
];
