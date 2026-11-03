import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { BacklogTask } from '../models/task.model';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  private readonly http = inject(HttpClient);

  readonly tasks = signal<BacklogTask[]>([
    {
      id: 't-01',
      roadmapId: 'rd-01',
      milestoneId: 'ms-02',
      title: 'Thiết kế REST API Endpoints chuẩn OpenAPI 3.1',
      description: 'Sử dụng FastAPI Router và Pydantic v2 schemas',
      pomodoroEstimate: 3,
      pomodorosCompleted: 3,
      priority: 'HIGH',
      status: 'COMPLETED'
    },
    {
      id: 't-02',
      roadmapId: 'rd-01',
      milestoneId: 'ms-03',
      title: 'Cấu hình HttpInterceptor xoay vòng Token JWT SameSite',
      description: 'Bảo mật cookie HttpOnly SameSite=Lax (ADR-008)',
      pomodoroEstimate: 2,
      pomodorosCompleted: 1,
      priority: 'HIGH',
      status: 'IN_PROGRESS'
    },
    {
      id: 't-03',
      roadmapId: 'rd-01',
      milestoneId: 'ms-03',
      title: 'Xây dựng Spartan UI Primitives và kiểm thử Vitest',
      description: 'Đảm bảo đạt điểm số Google Lighthouse Accessibility >= 90',
      pomodoroEstimate: 4,
      pomodorosCompleted: 0,
      priority: 'MEDIUM',
      status: 'SCHEDULED'
    }
  ]);

  updateTaskStatus(taskId: string, status: BacklogTask['status']): void {
    this.tasks.update((list) =>
      list.map((t) => (t.id === taskId ? { ...t, status } : t))
    );
  }
}
