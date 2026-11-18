import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, catchError, finalize, map, of, tap, throwError } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import {
  AddTaskDependencyRequest,
  CompleteTaskRequest,
  CreateTaskRequest,
  MilestoneResponse,
  RescheduleTaskRequest,
  RoadmapDetailResponse,
  RoadmapResponse,
  TaskDependencyResponse,
  TaskResponse,
  UpdateTaskRequest,
} from '../models/task.model';

export interface TaskApiError {
  code: string | null;
  message: string;
  details?: Record<string, unknown> | null;
  isOffline: boolean;
}

export function parseTaskApiError(
  err: unknown,
  fallback = 'Không thể thực hiện thao tác trên nhiệm vụ.'
): TaskApiError {
  if (err instanceof HttpErrorResponse) {
    const body =
      err.error && typeof err.error === 'object' ? (err.error as Record<string, unknown>) : null;
    const code = body && typeof body['code'] === 'string' ? body['code'] : null;
    const details =
      body && body['details'] && typeof body['details'] === 'object'
        ? (body['details'] as Record<string, unknown>)
        : null;
    return {
      code,
      message: parseHttpErrorMessage(err, fallback),
      details,
      isOffline: err.status === 0,
    };
  }
  return { code: null, message: fallback, isOffline: false };
}

@Injectable({
  providedIn: 'root',
})
export class TaskService {
  private readonly http = inject(HttpClient);

  readonly tasks = signal<TaskResponse[]>([]);
  readonly backlogTasks = signal<TaskResponse[]>([]);
  readonly roadmaps = signal<RoadmapResponse[]>([]);
  readonly milestonesByRoadmap = signal<Record<string, MilestoneResponse[]>>({});

  readonly isLoading = signal<boolean>(false);
  readonly isSubmitting = signal<boolean>(false);
  readonly errorState = signal<TaskApiError | null>(null);

  clearError(): void {
    this.errorState.set(null);
  }

  loadTasks(roadmapId?: string | null, status?: string | null): Observable<TaskResponse[]> {
    this.isLoading.set(true);
    this.errorState.set(null);

    let params = new HttpParams();
    if (roadmapId) {
      params = params.set('roadmap_id', roadmapId);
    }
    if (status) {
      params = params.set('status', status);
    }

    return this.http
      .get<TaskResponse[]>(API_ENDPOINTS.TASKS.LIST, {
        params,
        withCredentials: true,
      })
      .pipe(
        tap((list) => {
          this.tasks.set(list);
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseTaskApiError(err, 'Không thể tải danh sách nhiệm vụ.'));
          return of([]);
        }),
        finalize(() => {
          this.isLoading.set(false);
        })
      );
  }

  loadBacklogTasks(roadmapId?: string | null): Observable<TaskResponse[]> {
    let params = new HttpParams();
    if (roadmapId) {
      params = params.set('roadmap_id', roadmapId);
    }

    return this.http
      .get<TaskResponse[]>(API_ENDPOINTS.TASKS.BACKLOG, {
        params,
        withCredentials: true,
      })
      .pipe(
        tap((list) => {
          this.backlogTasks.set(list);
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseTaskApiError(err, 'Không thể tải hàng đợi phục hồi Backlog.'));
          return of([]);
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

  loadRoadmapMilestones(roadmapId: string): Observable<MilestoneResponse[]> {
    const cached = this.milestonesByRoadmap()[roadmapId];
    if (cached && cached.length > 0) {
      return of(cached);
    }

    return this.http
      .get<RoadmapDetailResponse>(API_ENDPOINTS.ROADMAPS.DETAIL(roadmapId), {
        withCredentials: true,
      })
      .pipe(
        map((detail) => detail.milestones ?? []),
        tap((milestones) => {
          this.milestonesByRoadmap.update((current) => ({
            ...current,
            [roadmapId]: milestones,
          }));
        }),
        catchError(() => of([]))
      );
  }

  createTask(payload: CreateTaskRequest): Observable<TaskResponse> {
    this.isSubmitting.set(true);
    this.errorState.set(null);

    return this.http
      .post<TaskResponse>(API_ENDPOINTS.TASKS.CREATE, payload, { withCredentials: true })
      .pipe(
        tap((created) => {
          this.tasks.update((list) => [created, ...list]);
          if (!created.scheduled_date) {
            this.backlogTasks.update((list) => [created, ...list]);
          }
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseTaskApiError(err, 'Không thể tạo nhiệm vụ mới.'));
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
      );
  }

  updateTask(taskId: string, payload: UpdateTaskRequest): Observable<TaskResponse> {
    this.isSubmitting.set(true);
    this.errorState.set(null);

    return this.http
      .patch<TaskResponse>(API_ENDPOINTS.TASKS.UPDATE(taskId), payload, {
        withCredentials: true,
      })
      .pipe(
        tap((updated) => {
          this.replaceTaskInSignals(updated);
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseTaskApiError(err, 'Không thể cập nhật nhiệm vụ.'));
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
      );
  }

  completeTask(taskId: string, payload?: CompleteTaskRequest | null): Observable<TaskResponse> {
    this.isSubmitting.set(true);
    this.errorState.set(null);

    return this.http
      .post<TaskResponse>(API_ENDPOINTS.TASKS.COMPLETE(taskId), payload ?? null, {
        withCredentials: true,
      })
      .pipe(
        tap((updated) => {
          this.replaceTaskInSignals(updated);
          this.backlogTasks.update((list) => list.filter((t) => t.id !== updated.id));
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseTaskApiError(err, 'Không thể hoàn thành nhiệm vụ.'));
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
      );
  }

  reopenTask(taskId: string): Observable<TaskResponse> {
    this.isSubmitting.set(true);
    this.errorState.set(null);

    return this.http
      .post<TaskResponse>(API_ENDPOINTS.TASKS.REOPEN(taskId), {}, { withCredentials: true })
      .pipe(
        tap((updated) => {
          this.replaceTaskInSignals(updated);
          if (!updated.scheduled_date) {
            this.backlogTasks.update((list) => [updated, ...list.filter((t) => t.id !== updated.id)]);
          }
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseTaskApiError(err, 'Không thể mở lại nhiệm vụ.'));
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
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
        tap((updated) => {
          this.replaceTaskInSignals(updated);
          if (!updated.scheduled_date) {
            this.backlogTasks.update((list) => [updated, ...list.filter((t) => t.id !== updated.id)]);
          } else {
            this.backlogTasks.update((list) => list.filter((t) => t.id !== updated.id));
          }
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseTaskApiError(err, 'Không thể dời lịch nhiệm vụ.'));
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
      );
  }

  deleteTask(taskId: string): Observable<TaskResponse> {
    this.isSubmitting.set(true);
    this.errorState.set(null);

    return this.http
      .delete<TaskResponse>(API_ENDPOINTS.TASKS.DELETE(taskId), { withCredentials: true })
      .pipe(
        tap((cancelled) => {
          this.replaceTaskInSignals(cancelled);
          this.backlogTasks.update((list) => list.filter((t) => t.id !== taskId));
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseTaskApiError(err, 'Không thể hủy nhiệm vụ.'));
          return throwError(() => err);
        }),
        finalize(() => {
          this.isSubmitting.set(false);
        })
      );
  }

  addDependency(
    taskId: string,
    payload: AddTaskDependencyRequest
  ): Observable<TaskDependencyResponse> {
    return this.http.post<TaskDependencyResponse>(
      API_ENDPOINTS.TASKS.ADD_DEPENDENCY(taskId),
      payload,
      { withCredentials: true }
    );
  }

  removeDependency(taskId: string, predecessorId: string): Observable<void> {
    return this.http.delete<void>(API_ENDPOINTS.TASKS.REMOVE_DEPENDENCY(taskId, predecessorId), {
      withCredentials: true,
    });
  }

  private replaceTaskInSignals(updated: TaskResponse): void {
    this.tasks.update((list) => {
      const exists = list.some((t) => t.id === updated.id);
      if (!exists) return [updated, ...list];
      return list.map((t) => (t.id === updated.id ? updated : t));
    });
  }
}
