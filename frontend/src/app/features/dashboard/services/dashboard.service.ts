import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, of } from 'rxjs';
import { DashboardSummary } from '../models/dashboard.model';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private readonly http = inject(HttpClient);

  readonly summary = signal<DashboardSummary | null>({
    activeRoadmapTitle: 'Chinh phục Lập trình Web Fullstack với FastAPI & Angular 19',
    totalMilestones: 8,
    completedMilestones: 2,
    totalStudyHours: 24.5,
    weeklyTargetHours: 15,
    streakDays: 5,
    upcomingTasks: [
      {
        id: 't-01',
        title: 'Thiết kế REST API Endpoints chuẩn OpenAPI 3.1',
        milestoneTitle: 'Chặng 2: Xây dựng Backend FastAPI',
        scheduledDate: 'Hôm nay, 14:00',
        pomodoroEstimate: 3,
        isCompleted: false
      },
      {
        id: 't-02',
        title: 'Cấu hình HttpInterceptor xoay vòng Token JWT SameSite',
        milestoneTitle: 'Chặng 3: Xây dựng Frontend Angular 19',
        scheduledDate: 'Hôm nay, 16:30',
        pomodoroEstimate: 2,
        isCompleted: false
      }
    ]
  });

  readonly isLoading = signal<boolean>(false);

  loadSummary(): Observable<DashboardSummary> {
    this.isLoading.set(true);
    return this.http.get<DashboardSummary>('/api/v1/analytics/summary').pipe(
      tap({
        next: (data) => {
          this.summary.set(data);
          this.isLoading.set(false);
        },
        error: () => {
          this.isLoading.set(false);
        }
      })
    );
  }
}
