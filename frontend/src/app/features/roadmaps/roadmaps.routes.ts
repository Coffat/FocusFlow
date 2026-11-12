import { Routes } from '@angular/router';

export const ROADMAPS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./components/roadmaps-hub/roadmaps-hub.component').then(m => m.RoadmapsHubComponent),
  },
  {
    path: 'new',
    loadComponent: () =>
      import('./components/roadmap-page/roadmap-page.component').then(m => m.RoadmapPageComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./components/roadmap-page/roadmap-page.component').then(m => m.RoadmapPageComponent),
  },
];
