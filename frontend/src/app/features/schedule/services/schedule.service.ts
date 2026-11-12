import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ScheduleSlot, WebCalTokenInfo } from '../models/schedule.model';

@Injectable({
  providedIn: 'root'
})
export class ScheduleService {
  private readonly http = inject(HttpClient);

  readonly weeklySlots = signal<ScheduleSlot[]>([]);

  readonly webCalInfo = signal<WebCalTokenInfo>({
    tokenUrl: '',
    isActive: false,
    lastAccessedAt: null
  });

  resetWebCalToken(): Observable<WebCalTokenInfo> {
    return this.http.post<WebCalTokenInfo>('/api/v1/calendar/tokens/reset', {});
  }
}
