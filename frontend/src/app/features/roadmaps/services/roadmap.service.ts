import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Roadmap, GenerateRoadmapPayload } from '../models/roadmap.model';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';

@Injectable({
  providedIn: 'root'
})
export class RoadmapService {
  private readonly http = inject(HttpClient);

  readonly currentRoadmap = signal<Roadmap | null>({
    id: 'rd-01',
    userId: 'usr-01',
    title: 'Chinh phục Lập trình Web Fullstack với FastAPI & Angular 19',
    targetGoal: 'Hoàn thành Khóa luận Tốt nghiệp Đạt Xuất sắc tại HCMUTE',
    status: 'ACTIVE',
    hoursPerWeek: 15,
    createdAt: '2026-10-01T08:00:00Z',
    milestones: [
      {
        id: 'ms-01',
        roadmapId: 'rd-01',
        title: 'Chặng 1: Nền tảng Kiến trúc Lục giác & SRS ISO 29148',
        orderIndex: 1,
        description: 'Hoàn thiện hồ sơ yêu cầu phần mềm và ma trận truy vết',
        totalPomodoros: 20,
        completedPomodoros: 20,
        tasksCount: 6
      },
      {
        id: 'ms-02',
        roadmapId: 'rd-01',
        title: 'Chặng 2: Xây dựng Backend FastAPI & CSDL PostgreSQL 16',
        orderIndex: 2,
        description: 'Triển khai Domain Entities, Use Cases và Repository Adapters',
        totalPomodoros: 35,
        completedPomodoros: 15,
        tasksCount: 10
      },
      {
        id: 'ms-03',
        roadmapId: 'rd-01',
        title: 'Chặng 3: Xây dựng Frontend Angular 19 Standalone & Spartan UI',
        orderIndex: 3,
        description: 'Hiện thực giao diện người dùng theo chuẩn WCAG 2.2 AA',
        totalPomodoros: 40,
        completedPomodoros: 5,
        tasksCount: 12
      }
    ]
  });

  readonly isGeneratingStream = signal<boolean>(false);

  pauseRoadmap(id: string): Observable<Roadmap> {
    return this.http.post<Roadmap>(API_ENDPOINTS.ROADMAPS.PAUSE(id), {}).pipe(
      tap((updated) => this.currentRoadmap.set(updated))
    );
  }

  resumeRoadmap(id: string): Observable<Roadmap> {
    return this.http.post<Roadmap>(API_ENDPOINTS.ROADMAPS.RESUME(id), {}).pipe(
      tap((updated) => this.currentRoadmap.set(updated))
    );
  }
}
