import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, catchError, finalize, forkJoin, of, tap, throwError } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import {
  RescheduleTaskRequest,
  RoadmapResponse,
  ScheduleDayGroup,
  ScheduleProposalResponse,
  TaskResponse,
  WeeklyScheduleItemResponse,
  WeeklyScheduleResponse,
} from '../models/schedule.model';

export interface ScheduleApiError {
  code: string | null;
  message: string;
  violations: string[];
  isOffline: boolean;
}

export function formatLocalDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function getLocalMondayIso(offsetWeeks = 0): string {
  const now = new Date();
  const day = now.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + diffToMonday + offsetWeeks * 7
  );
  return formatLocalDateKey(monday);
}

export function extractLocalDateFromItem(item: WeeklyScheduleItemResponse): string {
  if (item.start_time) {
    const dt = new Date(item.start_time);
    if (!Number.isNaN(dt.getTime())) {
      return formatLocalDateKey(dt);
    }
  }
  return item.block_date;
}

export function formatLocalTimeRange(startIso: string, endIso: string): string {
  const fmt = (iso: string): string => {
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) return iso;
    return dt.toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  };
  return `${fmt(startIso)} – ${fmt(endIso)}`;
}

export function parseScheduleApiError(
  err: unknown,
  fallback = 'Không thể thực hiện thao tác lịch học.'
): ScheduleApiError {
  if (err instanceof HttpErrorResponse) {
    const body =
      err.error && typeof err.error === 'object' ? (err.error as Record<string, unknown>) : null;
    const code = body && typeof body['code'] === 'string' ? body['code'] : null;
    const details =
      body && body['details'] && typeof body['details'] === 'object'
        ? (body['details'] as Record<string, unknown>)
        : null;

    const violations: string[] = [];
    if (details && Array.isArray(details['violations'])) {
      for (const v of details['violations']) {
        if (typeof v === 'string') {
          violations.push(v);
        } else if (v && typeof v === 'object') {
          const rec = v as Record<string, unknown>;
          const msg = rec['message'] ?? rec['suggested_fix'] ?? rec['rule_code'];
          if (typeof msg === 'string' && msg.trim()) {
            violations.push(msg.trim());
          }
        }
      }
    }
    if (details && Array.isArray(details['calendar_conflicts'])) {
      for (const c of details['calendar_conflicts']) {
        if (typeof c === 'string') {
          violations.push(c);
        } else if (c && typeof c === 'object') {
          const rec = c as Record<string, unknown>;
          if (typeof rec['summary'] === 'string') {
            violations.push(`Xung đột lịch ngoài: ${rec['summary']}`);
          }
        }
      }
    }

    return {
      code,
      message: parseHttpErrorMessage(err, fallback),
      violations,
      isOffline: err.status === 0,
    };
  }
  return { code: null, message: fallback, violations: [], isOffline: false };
}

const WEEKDAY_NAMES_VI = [
  'Chủ Nhật',
  'Thứ Hai',
  'Thứ Ba',
  'Thứ Tư',
  'Thứ Năm',
  'Thứ Sáu',
  'Thứ Bảy',
];

@Injectable({
  providedIn: 'root',
})
export class ScheduleService {
  private readonly http = inject(HttpClient);

  readonly weeklySchedule = signal<WeeklyScheduleResponse | null>(null);
  readonly roadmaps = signal<RoadmapResponse[]>([]);
  readonly weekOffset = signal<number>(0);

  readonly isLoading = signal<boolean>(false);
  readonly isSubmitting = signal<boolean>(false);
  readonly errorState = signal<ScheduleApiError | null>(null);

  readonly items = computed<WeeklyScheduleItemResponse[]>(
    () => this.weeklySchedule()?.items ?? []
  );

  readonly dayGroups = computed<ScheduleDayGroup[]>(() => {
    const items = this.items();
    if (items.length === 0) return [];

    const todayKey = formatLocalDateKey(new Date());
    const grouped = new Map<string, WeeklyScheduleItemResponse[]>();

    for (const item of items) {
      const dateKey = extractLocalDateFromItem(item);
      const list = grouped.get(dateKey) ?? [];
      list.push(item);
      grouped.set(dateKey, list);
    }

    const sortedKeys = Array.from(grouped.keys()).sort();
    return sortedKeys.map((dateKey) => {
      const dayItems = (grouped.get(dateKey) ?? []).slice().sort((a, b) =>
        a.start_time.localeCompare(b.start_time)
      );
      const [y, m, d] = dateKey.split('-').map(Number);
      const dt = new Date(y, (m || 1) - 1, d || 1);
      const weekday = WEEKDAY_NAMES_VI[dt.getDay()] ?? '';
      const formattedDate = `${String(d || 1).padStart(2, '0')}/${String(m || 1).padStart(2, '0')}/${y}`;
      return {
        localDate: dateKey,
        dayLabel: `${weekday}, ${formattedDate}`,
        isToday: dateKey === todayKey,
        items: dayItems,
      };
    });
  });

  clearError(): void {
    this.errorState.set(null);
  }

  loadWeeklySchedule(weekStart?: string | null): Observable<WeeklyScheduleResponse | null> {
    this.isLoading.set(true);
    this.errorState.set(null);

    let params = new HttpParams();
    if (weekStart) {
      params = params.set('week_start', weekStart);
    }

    return this.http
      .get<WeeklyScheduleResponse>(API_ENDPOINTS.TASKS.SCHEDULE_WEEK, {
        params,
        withCredentials: true,
      })
      .pipe(
        tap((res) => {
          this.weeklySchedule.set(res);
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseScheduleApiError(err, 'Không thể tải thời khóa biểu tuần.'));
          return of(null);
        }),
        finalize(() => {
          this.isLoading.set(false);
        })
      );
  }

  loadRoadmaps(): Observable<RoadmapResponse[]> {
    return this.http
      .get<RoadmapResponse[]>(API_ENDPOINTS.ROADMAPS.BASE, { withCredentials: true })
      .pipe(
        tap((list) => {
          this.roadmaps.set(list);
        }),
        catchError(() => of([]))
      );
  }

  rescheduleTask(taskId: string, payload: RescheduleTaskRequest): Observable<TaskResponse> {
    this.isSubmitting.set(true);
    this.errorState.set(null);

    return this.http
      .post<TaskResponse>(API_ENDPOINTS.TASKS.RESCHEDULE(taskId), payload, {
        withCredentials: true,
      })
      .pipe(
        catchError((err: unknown) => {
          this.errorState.set(parseScheduleApiError(err, 'Không thể dời lịch nhiệm vụ.'));
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
      );
  }

  moveTasksToBacklog(taskIds: string[], reason?: string | null): Observable<TaskResponse[]> {
    const uniqueIds = Array.from(new Set(taskIds.filter((id) => !!id)));
    if (uniqueIds.length === 0) {
      return of([]);
    }

    this.isSubmitting.set(true);
    this.errorState.set(null);

    const requests = uniqueIds.map((id) =>
      this.http.post<TaskResponse>(
        API_ENDPOINTS.TASKS.RESCHEDULE(id),
        {
          scheduled_date: null,
          scheduled_start: null,
          scheduled_end: null,
          reason: reason || 'Chuyển nhiệm vụ chưa xong hôm nay về Backlog',
          allow_stalled_commitment: false,
          confirm_soft_overflow: false,
        } satisfies RescheduleTaskRequest,
        { withCredentials: true }
      )
    );

    return forkJoin(requests).pipe(
      catchError((err: unknown) => {
        this.errorState.set(
          parseScheduleApiError(err, 'Không thể chuyển một số nhiệm vụ về Backlog.')
        );
        return throwError(() => err);
      }),
      finalize(() => {
        this.isSubmitting.set(false);
      })
    );
  }

  reoptimizeRoadmapSchedule(roadmapId: string): Observable<ScheduleProposalResponse> {
    this.isSubmitting.set(true);
    this.errorState.set(null);

    return this.http
      .post<ScheduleProposalResponse>(
        API_ENDPOINTS.ROADMAPS.REOPTIMIZE_SCHEDULE(roadmapId),
        {},
        { withCredentials: true }
      )
      .pipe(
        catchError((err: unknown) => {
          this.errorState.set(
            parseScheduleApiError(err, 'Không thể tạo đề xuất tái tối ưu lịch trình.')
          );
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
      );
  }

  pauseRoadmap(roadmapId: string): Observable<RoadmapResponse> {
    this.isSubmitting.set(true);
    this.errorState.set(null);

    return this.http
      .post<RoadmapResponse>(API_ENDPOINTS.ROADMAPS.PAUSE(roadmapId), {}, { withCredentials: true })
      .pipe(
        catchError((err: unknown) => {
          this.errorState.set(parseScheduleApiError(err, 'Không thể tạm dừng lộ trình.'));
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
      );
  }
}
