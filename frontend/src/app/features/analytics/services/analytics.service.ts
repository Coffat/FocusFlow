import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AnalyticsSummary } from '../models/analytics.model';

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private readonly http = inject(HttpClient);

  readonly analyticsData = signal<AnalyticsSummary>({
    weeklyStudyHours: 0,
    taskCompletionRate: 0,
    averageFocusScore: 0,
    dailyMetrics: []
  });
}
