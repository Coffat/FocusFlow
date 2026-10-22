import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ScheduleSlot, WebCalTokenInfo } from '../models/schedule.model';

@Injectable({
  providedIn: 'root'
})
export class ScheduleService {
  private readonly http = inject(HttpClient);

  readonly weeklySlots = signal<ScheduleSlot[]>([
    {
      id: 'sl-01',
      dayOfWeek: 1, // Thứ 2
      startTime: '19:00',
      endTime: '21:00',
      taskId: 't-01',
      taskTitle: 'Thiết kế REST API Endpoints chuẩn OpenAPI 3.1',
      isCompleted: true
    },
    {
      id: 'sl-02',
      dayOfWeek: 3, // Thứ 4
      startTime: '19:00',
      endTime: '21:30',
      taskId: 't-02',
      taskTitle: 'Cấu hình HttpInterceptor xoay vòng Token JWT SameSite',
      isCompleted: false
    },
    {
      id: 'sl-03',
      dayOfWeek: 5, // Thứ 6
      startTime: '19:00',
      endTime: '21:00',
      taskId: 't-03',
      taskTitle: 'Xây dựng Spartan UI Primitives và kiểm thử Vitest',
      isCompleted: false
    }
  ]);

  readonly webCalInfo = signal<WebCalTokenInfo>({
    tokenUrl: 'webcal://api.focusflow.vn/api/v1/calendar/feed/a4b8c9d0e1f2.ics',
    isActive: true,
    lastAccessedAt: '2026-10-14T08:30:00Z'
  });

  resetWebCalToken(): Observable<WebCalTokenInfo> {
    return this.http.post<WebCalTokenInfo>('/api/v1/calendar/tokens/reset', {});
  }
}
