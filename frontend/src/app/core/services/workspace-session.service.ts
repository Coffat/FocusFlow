import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  Observable,
  Subject,
  Subscription,
  catchError,
  debounceTime,
  distinctUntilChanged,
  finalize,
  forkJoin,
  interval,
  map,
  of,
  switchMap,
  tap,
  throwError,
} from 'rxjs';
import { components } from '../api/schema';
import { API_ENDPOINTS } from '../constants/api-endpoints';
import { parseHttpErrorMessage } from '../utils/error-parser.util';
import type {
  MilestoneContextSummary,
  SessionLifecycleState,
} from '../../features/workspace/models/workspace.model';

export type TodayFocusResponse = components['schemas']['TodayFocusResponse'];
export type StudySessionResponse = components['schemas']['StudySessionResponse'];
export type TaskResponse = components['schemas']['TaskResponse'];
export type RoadmapDetailResponse = components['schemas']['RoadmapDetailResponse'];
export type StartSessionRequest = components['schemas']['StartSessionRequest'];
export type HeartbeatSessionRequest = components['schemas']['HeartbeatSessionRequest'];
export type FinalizeSessionRequest = components['schemas']['FinalizeSessionRequest'];
export type ResolveTakeawayRequest = components['schemas']['ResolveTakeawayRequest'];
export type SessionMode = StartSessionRequest['session_mode'];
export type TimeSufficiency = NonNullable<FinalizeSessionRequest['checkin_time_sufficiency']>;

export interface ExecutionApiError {
  code: string | null;
  message: string;
  isOffline: boolean;
}

export interface TodayProgressSummary {
  completedCount: number;
  totalCount: number;
  percentage: number;
  totalPlannedMinutes: number;
  totalStudiedMinutes: number;
}

export interface LocalTakeawayCheck {
  charCount: number;
  distinctWordCount: number;
  hasMinChars: boolean;
  hasMinWords: boolean;
  hasAlpha: boolean;
  hasNoRepeatedChars: boolean;
  isValid: boolean;
}

export function extractExecutionError(
  err: unknown,
  fallback = 'Đã có lỗi xảy ra. Vui lòng thử lại.'
): ExecutionApiError {
  if (err instanceof HttpErrorResponse) {
    const isOffline = err.status === 0;
    const rawBody =
      err.error && typeof err.error === 'object'
        ? (err.error as Record<string, unknown>)
        : null;
    const code = rawBody && typeof rawBody['code'] === 'string' ? rawBody['code'] : null;
    const message = parseHttpErrorMessage(err, fallback);
    return { code, message, isOffline };
  }
  return { code: null, message: fallback, isOffline: false };
}

export function evaluateTakeawayCheck(takeaway: string): LocalTakeawayCheck {
  const normalized = (takeaway || '').trim().replace(/\s+/g, ' ');
  const charCount = normalized.length;
  const words = (normalized.toLowerCase().match(/[0-9a-zA-ZÀ-ỹ]+/gu) ?? []);
  const distinctWords = new Set(words);
  const distinctWordCount = distinctWords.size;
  const hasMinChars = charCount >= 30;
  const hasMinWords = distinctWordCount >= 6;
  const hasAlpha = /[A-Za-zÀ-ỹ]/u.test(normalized);
  const hasNoRepeatedChars = !/(.)\1{5,}/i.test(normalized);

  return {
    charCount,
    distinctWordCount,
    hasMinChars,
    hasMinWords,
    hasAlpha,
    hasNoRepeatedChars,
    isValid: hasMinChars && hasMinWords && hasAlpha && hasNoRepeatedChars,
  };
}

@Injectable({
  providedIn: 'root',
})
export class WorkspaceSessionService {
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);

  // Server state signals
  private readonly _todayFocus = signal<TodayFocusResponse | null>(null);
  readonly todayFocus = this._todayFocus.asReadonly();

  private readonly _activeSession = signal<StudySessionResponse | null>(null);
  readonly activeSession = this._activeSession.asReadonly();

  private readonly _pendingTakeawaySession = signal<StudySessionResponse | null>(null);
  readonly pendingTakeawaySession = this._pendingTakeawaySession.asReadonly();

  private readonly _todayQueue = signal<TaskResponse[]>([]);
  readonly todayQueue = this._todayQueue.asReadonly();

  private readonly _focusTask = signal<TaskResponse | null>(null);
  readonly focusTask = this._focusTask.asReadonly();

  private readonly _preselectedTask = signal<TaskResponse | null>(null);
  readonly preselectedTask = this._preselectedTask.asReadonly();

  private readonly _isLoading = signal<boolean>(false);
  readonly isLoading = this._isLoading.asReadonly();

  private readonly _isSubmitting = signal<boolean>(false);
  readonly isSubmitting = this._isSubmitting.asReadonly();

  private readonly _errorState = signal<ExecutionApiError | null>(null);
  readonly errorState = this._errorState.asReadonly();

  private readonly _heartbeatStatus = signal<'idle' | 'syncing' | 'synced' | 'offline' | 'error'>('idle');
  readonly heartbeatStatus = this._heartbeatStatus.asReadonly();

  private readonly _lastHeartbeatAt = signal<string | null>(null);
  readonly lastHeartbeatAt = this._lastHeartbeatAt.asReadonly();

  private readonly _lastFinalizedSession = signal<StudySessionResponse | null>(null);
  readonly lastFinalizedSession = this._lastFinalizedSession.asReadonly();

  // Timer & session reactive signals (timestamp-based, zoneless-safe)
  readonly sessionId = computed<string | null>(() => this._activeSession()?.id ?? null);
  readonly taskId = computed<string | null>(
    () => this._activeSession()?.session_tasks?.[0]?.task_id ?? null
  );
  readonly activeTaskIds = computed<string[]>(
    () => this._activeSession()?.session_tasks?.map((t) => t.task_id) ?? []
  );
  readonly sessionMode = computed<SessionMode>(() =>
    this._activeSession()?.session_mode === 'MVS' ? 'MVS' : 'STANDARD'
  );
  readonly mode = signal<'pomodoro' | 'stopwatch'>('pomodoro');
  readonly durationMinutes = signal<number>(25);
  readonly remainingSeconds = signal<number>(25 * 60);
  readonly elapsedSeconds = signal<number>(0);
  readonly isRunning = signal<boolean>(false);

  private readonly _timerCompletedTick = signal<number>(0);
  readonly timerCompletedTick = this._timerCompletedTick.asReadonly();

  // Local break timer signals (never calls backend session APIs)
  private readonly _activeBreakType = signal<'short' | 'long' | null>(null);
  readonly activeBreakType = this._activeBreakType.asReadonly();

  private readonly _breakDurationMinutes = signal<number>(5);
  readonly breakDurationMinutes = this._breakDurationMinutes.asReadonly();

  private readonly _breakRemainingSeconds = signal<number>(300);
  readonly breakRemainingSeconds = this._breakRemainingSeconds.asReadonly();

  private readonly _isBreakRunning = signal<boolean>(false);
  readonly isBreakRunning = this._isBreakRunning.asReadonly();

  private readonly _localPomodorosToday = signal<number>(this.loadPomodorosToday());
  private readonly _localPomodoroDelta = signal<number>(0);
  readonly completedPomodorosToday = computed<number>(() => {
    const tf = this._todayFocus();
    if (tf && typeof tf.completed_sessions_today === 'number') {
      return tf.completed_sessions_today + this._localPomodoroDelta();
    }
    return this._localPomodorosToday();
  });

  private readonly _scratchpadNote = signal<string>('');
  readonly scratchpadNote = this._scratchpadNote.asReadonly();

  readonly activeFocusTaskId = signal<string | null>(null);
  readonly milestoneContext = signal<MilestoneContextSummary | null>(null);

  readonly lifecycleState = computed<SessionLifecycleState>(() => {
    if (this._isBreakRunning() || this._activeBreakType() !== null) {
      return 'BREAK';
    }
    if (this._activeSession()?.status === 'IN_PROGRESS') {
      return this.isRunning() ? 'FOCUSING' : 'PAUSED';
    }
    if (this._lastFinalizedSession() !== null) {
      return 'COMPLETED';
    }
    return 'READY';
  });

  // Deduplicated tasks available to show in workspace
  readonly availableTasks = computed<TaskResponse[]>(() => {
    const mapById = new Map<string, TaskResponse>();
    const focus = this._focusTask();
    if (focus) {
      mapById.set(focus.id, focus);
    }
    for (const item of this._todayQueue()) {
      mapById.set(item.id, item);
    }
    const preselected = this._preselectedTask();
    if (preselected && !mapById.has(preselected.id)) {
      mapById.set(preselected.id, preselected);
    }
    return Array.from(mapById.values());
  });

  readonly activeSessionTasks = computed<TaskResponse[]>(() => {
    const ids = new Set(this.activeTaskIds());
    return this.availableTasks().filter((t) => ids.has(t.id));
  });

  readonly activeFocusTask = computed<TaskResponse | null>(() => {
    const inSession = this._activeSession()?.status === 'IN_PROGRESS';
    const selectedId = this.activeFocusTaskId();

    if (inSession) {
      const sessionTasks = this.activeSessionTasks();
      if (selectedId) {
        const match = sessionTasks.find((t) => t.id === selectedId);
        if (match) {
          return match;
        }
      }
      return sessionTasks[0] ?? null;
    }

    const available = this.availableTasks();
    if (selectedId) {
      const match = available.find((t) => t.id === selectedId);
      if (match) {
        return match;
      }
    }
    return this._focusTask() ?? available[0] ?? null;
  });

  readonly displaySeconds = computed(() =>
    this.mode() === 'stopwatch' ? this.elapsedSeconds() : this.remainingSeconds()
  );

  readonly formattedTime = computed(() => {
    if (this.mode() === 'stopwatch') {
      const totalSec = this.elapsedSeconds();
      const hours = Math.floor(totalSec / 3600);
      const minutes = Math.floor((totalSec % 3600) / 60);
      const seconds = totalSec % 60;
      if (hours > 0) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      }
      return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    const totalSec = this.remainingSeconds();
    const minutes = Math.floor(totalSec / 60);
    const seconds = totalSec % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  });

  readonly progressPercentage = computed(() => {
    if (this.mode() === 'stopwatch') {
      const targetSec = Math.max(1, this.durationMinutes() * 60);
      return Math.min(100, Math.max(0, Math.round((this.elapsedSeconds() / targetSec) * 100)));
    }

    const total = this.durationMinutes() * 60;
    if (total === 0) return 0;
    const elapsed = total - this.remainingSeconds();
    return Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));
  });

  readonly elapsedMinutes = computed(() => Math.max(0, Math.floor(this.elapsedSeconds() / 60)));

  readonly breakFormattedTime = computed(() => {
    const totalSec = this._breakRemainingSeconds();
    const minutes = Math.floor(totalSec / 60);
    const seconds = totalSec % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  });

  readonly breakProgressPercentage = computed(() => {
    const total = this._breakDurationMinutes() * 60;
    if (total <= 0) return 0;
    const elapsed = total - this._breakRemainingSeconds();
    return Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));
  });

  readonly todayProgress = computed<TodayProgressSummary>(() => {
    const tasks = this.availableTasks().filter((t) => t.status !== 'CANCELLED');
    const totalCount = tasks.length;
    const completedCount = tasks.filter((t) => t.status === 'COMPLETED').length;
    const percentage = totalCount === 0 ? 0 : Math.round((completedCount / totalCount) * 100);
    const totalPlannedMinutes = tasks.reduce((sum, t) => sum + (t.estimated_minutes || 0), 0);
    const tf = this._todayFocus();
    const serverStudiedMinutes =
      tf && typeof tf.studied_minutes_today === 'number' ? tf.studied_minutes_today : 0;
    const totalStudiedMinutes = serverStudiedMinutes + this.elapsedMinutes();
    return {
      completedCount,
      totalCount,
      percentage,
      totalPlannedMinutes,
      totalStudiedMinutes,
    };
  });

  private startedAt: number | null = null;
  private pausedMs = 0;
  private pauseTimestamp: number | null = null;
  private pomodoroCountedForCurrentSession = false;
  private timerSubscription: Subscription | null = null;
  private heartbeatSubscription: Subscription | null = null;

  private breakStartedAt: number | null = null;
  private breakPausedMs = 0;
  private breakPauseTimestamp: number | null = null;
  private breakTimerSubscription: Subscription | null = null;

  private readonly scratchpadSave$ = new Subject<string>();
  private readonly roadmapCache = new Map<string, RoadmapDetailResponse>();

  private readonly visibilityHandler = (): void => {
    if (typeof document === 'undefined' || document.hidden) return;
    if (this.isRunning() && this.startedAt) {
      this.recalculateRemainingTime();
    }
    if (this._isBreakRunning() && this.breakStartedAt) {
      this.recalculateBreakRemainingTime();
    }
  };

  constructor() {
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', this.visibilityHandler);
    }

    // Debounced scratchpad auto-save via heartbeat when a session is active
    this.scratchpadSave$
      .pipe(
        debounceTime(1500),
        distinctUntilChanged(),
        switchMap(() => {
          if (!this.sessionId()) {
            return of(null);
          }
          return this.sendHeartbeat().pipe(catchError(() => of(null)));
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe();

    this.destroyRef.onDestroy(() => {
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', this.visibilityHandler);
      }
      this.stopTimersAndHeartbeat();
      this.stopBreakInterval();
    });
  }

  clearError(): void {
    this._errorState.set(null);
  }

  clearFinalizedBanner(): void {
    this._lastFinalizedSession.set(null);
  }

  setScratchpadNote(note: string): void {
    this._scratchpadNote.set(note);
    if (this.sessionId()) {
      this.scratchpadSave$.next(note);
    }
  }

  setActiveFocusTask(taskId: string): boolean {
    if (this.sessionId() !== null && !this.activeTaskIds().includes(taskId)) {
      return false;
    }
    this.activeFocusTaskId.set(taskId);
    return true;
  }

  hasInlineMilestoneContext(task: TaskResponse | null): boolean {
    if (!task || !task.milestone_id) {
      return false;
    }
    const hasTitle =
      typeof task.milestone_title === 'string' && task.milestone_title.trim().length > 0;
    const hasOutcomes =
      Array.isArray(task.learning_outcomes) && task.learning_outcomes.length > 0;
    const hasCriteria =
      typeof task.completion_criteria === 'string' && task.completion_criteria.trim().length > 0;
    return hasTitle || hasOutcomes || hasCriteria;
  }

  applyInlineMilestoneContext(task: TaskResponse | null): boolean {
    if (!task || !task.roadmap_id || !task.milestone_id || !this.hasInlineMilestoneContext(task)) {
      return false;
    }
    this.milestoneContext.set({
      roadmapId: task.roadmap_id,
      milestoneId: task.milestone_id,
      milestoneTitle: task.milestone_title ?? null,
      learningOutcomes: task.learning_outcomes ?? [],
      completionCriteria: task.completion_criteria ?? null,
    });
    return true;
  }

  loadMilestoneContext(roadmapId: string, milestoneId: string): void {
    if (!roadmapId || !milestoneId) {
      this.milestoneContext.set(null);
      return;
    }

    const focusTask = this.activeFocusTask();
    if (
      focusTask &&
      focusTask.roadmap_id === roadmapId &&
      focusTask.milestone_id === milestoneId &&
      this.applyInlineMilestoneContext(focusTask)
    ) {
      return;
    }

    const cached = this.roadmapCache.get(roadmapId);
    if (cached) {
      this.applyMilestoneFromRoadmap(cached, roadmapId, milestoneId);
      return;
    }

    this.http
      .get<RoadmapDetailResponse>(API_ENDPOINTS.ROADMAPS.DETAIL(roadmapId), {
        withCredentials: true,
      })
      .pipe(
        catchError(() => of(null)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((detail) => {
        if (!detail) {
          return;
        }
        this.roadmapCache.set(roadmapId, detail);
        this.applyMilestoneFromRoadmap(detail, roadmapId, milestoneId);
      });
  }

  private applyMilestoneFromRoadmap(
    detail: RoadmapDetailResponse,
    roadmapId: string,
    milestoneId: string
  ): void {
    const milestone = detail.milestones?.find((m) => m.id === milestoneId);
    if (!milestone) {
      this.milestoneContext.set(null);
      return;
    }
    this.milestoneContext.set({
      roadmapId,
      milestoneId,
      learningOutcomes: milestone.learning_outcomes ?? [],
      completionCriteria: milestone.completion_criteria ?? null,
    });
  }

  loadWorkspace(preferredTaskId?: string | null): Observable<TodayFocusResponse | null> {
    this._isLoading.set(true);
    this._errorState.set(null);

    return forkJoin({
      todayFocus: this.http.get<TodayFocusResponse>(API_ENDPOINTS.SESSIONS.TODAY_FOCUS, {
        withCredentials: true,
      }),
      active: this.http
        .get<StudySessionResponse | null>(API_ENDPOINTS.SESSIONS.ACTIVE, {
          withCredentials: true,
        })
        .pipe(catchError(() => of(null))),
    }).pipe(
      switchMap(({ todayFocus, active }) => {
        const inQueue =
          !!preferredTaskId &&
          (todayFocus.focus_task?.id === preferredTaskId ||
            (todayFocus.today_queue ?? []).some((t) => t.id === preferredTaskId));

        if (preferredTaskId && !inQueue) {
          return this.http
            .get<TaskResponse[]>(API_ENDPOINTS.TASKS.LIST, { withCredentials: true })
            .pipe(
              map((tasks) => ({
                todayFocus,
                active,
                extraTask: tasks.find((t) => t.id === preferredTaskId) ?? null,
              })),
              catchError(() => of({ todayFocus, active, extraTask: null }))
            );
        }
        return of({ todayFocus, active, extraTask: null });
      }),
      tap(({ todayFocus, active, extraTask }) => {
        this._todayFocus.set(todayFocus);
        this._localPomodoroDelta.set(0);
        this._todayQueue.set(todayFocus.today_queue ?? []);
        this._focusTask.set(todayFocus.focus_task ?? null);
        this._preselectedTask.set(extraTask);
        this._pendingTakeawaySession.set(todayFocus.pending_takeaway_session ?? null);

        const resolvedActive = active ?? todayFocus.active_session ?? null;
        if (resolvedActive && resolvedActive.status === 'IN_PROGRESS') {
          this.hydrateActiveSession(resolvedActive);
        } else {
          this.resetLocalSessionState();
        }

        const currentFocus = this.activeFocusTask();
        if (!this.applyInlineMilestoneContext(currentFocus)) {
          if (!currentFocus?.roadmap_id || !currentFocus?.milestone_id) {
            this.milestoneContext.set(null);
          }
        }
      }),
      map(({ todayFocus }) => todayFocus),
      catchError((err: unknown) => {
        this._errorState.set(
          extractExecutionError(err, 'Không thể tải không gian học tập. Vui lòng thử lại.')
        );
        return of(null);
      }),
      finalize(() => {
        this._isLoading.set(false);
      })
    );
  }

  beginSession(request: StartSessionRequest): Observable<StudySessionResponse> {
    this._isSubmitting.set(true);
    this._errorState.set(null);

    return this.http
      .post<StudySessionResponse>(API_ENDPOINTS.SESSIONS.START, request, {
        withCredentials: true,
      })
      .pipe(
        tap((session) => {
          this._lastFinalizedSession.set(null);
          this.hydrateActiveSession(session, true);
        }),
        catchError((err: unknown) => {
          const parsed = extractExecutionError(
            err,
            'Không thể bắt đầu phiên học. Vui lòng kiểm tra lại.'
          );
          this._errorState.set(parsed);
          return throwError(() => err);
        }),
        finalize(() => {
          this._isSubmitting.set(false);
        })
      );
  }

  pauseSession(): void {
    if (!this.isRunning()) return;
    this.isRunning.set(false);
    this.pauseTimestamp = Date.now();
    this.stopCountdownTimer();
  }

  resumeSession(): void {
    if (this.isRunning() || !this.sessionId()) return;
    if (this.pauseTimestamp) {
      this.pausedMs += Date.now() - this.pauseTimestamp;
      this.pauseTimestamp = null;
    }
    this.isRunning.set(true);
    this.startCountdownTimer();
  }

  sendHeartbeat(): Observable<StudySessionResponse | null> {
    const id = this.sessionId();
    if (!id) {
      return of(null);
    }

    this._heartbeatStatus.set('syncing');
    const payload: HeartbeatSessionRequest = {
      actual_minutes: this.elapsedMinutes(),
      scratchpad_content: this._scratchpadNote(),
    };

    return this.http
      .post<StudySessionResponse>(API_ENDPOINTS.SESSIONS.HEARTBEAT(id), payload, {
        withCredentials: true,
      })
      .pipe(
        tap((updated) => {
          this._activeSession.set(updated);
          this._heartbeatStatus.set('synced');
          this._lastHeartbeatAt.set(updated.last_heartbeat_at);
        }),
        catchError((err: unknown) => {
          const parsed = extractExecutionError(err, 'Mất kết nối nhịp tim phiên học.');
          this._heartbeatStatus.set(parsed.isOffline ? 'offline' : 'error');
          return of(null);
        })
      );
  }

  finalizeSession(request: FinalizeSessionRequest): Observable<StudySessionResponse> {
    const id = this.sessionId();
    if (!id) {
      return throwError(() => new Error('Không có phiên học đang hoạt động.'));
    }

    this._isSubmitting.set(true);
    this._errorState.set(null);

    const payload: FinalizeSessionRequest = {
      ...request,
      scratchpad_content: request.scratchpad_content ?? this._scratchpadNote(),
      actual_minutes: request.actual_minutes ?? Math.max(1, this.elapsedMinutes()),
    };

    return this.http
      .post<StudySessionResponse>(API_ENDPOINTS.SESSIONS.FINALIZE(id), payload, {
        withCredentials: true,
      })
      .pipe(
        tap((finalized) => {
          if (this.mode() === 'pomodoro' && !this.pomodoroCountedForCurrentSession) {
            this.incrementCompletedPomodorosToday();
            this.pomodoroCountedForCurrentSession = true;
          }
          this.stopTimersAndHeartbeat();
          this.resetLocalSessionState();
          this._lastFinalizedSession.set(finalized);
        }),
        catchError((err: unknown) => {
          const parsed = extractExecutionError(
            err,
            'Không thể hoàn tất phiên học. Vui lòng kiểm tra lại Key Takeaway.'
          );
          this._errorState.set(parsed);
          return throwError(() => err);
        }),
        finalize(() => {
          this._isSubmitting.set(false);
        })
      );
  }

  resolvePendingTakeaway(
    sessionId: string,
    request: ResolveTakeawayRequest
  ): Observable<StudySessionResponse> {
    this._isSubmitting.set(true);
    this._errorState.set(null);

    return this.http
      .post<StudySessionResponse>(API_ENDPOINTS.SESSIONS.RESOLVE_TAKEAWAY(sessionId), request, {
        withCredentials: true,
      })
      .pipe(
        tap(() => {
          this._pendingTakeawaySession.set(null);
        }),
        catchError((err: unknown) => {
          const parsed = extractExecutionError(
            err,
            'Key Takeaway chưa đạt yêu cầu chất lượng. Vui lòng bổ sung.'
          );
          this._errorState.set(parsed);
          return throwError(() => err);
        }),
        finalize(() => {
          this._isSubmitting.set(false);
        })
      );
  }

  toggleTaskCompletion(task: TaskResponse): Observable<TaskResponse | null> {
    const isCompleted = task.status === 'COMPLETED';
    const prevQueue = this._todayQueue();
    const prevFocus = this._focusTask();
    const prevPreselected = this._preselectedTask();

    const optimisticTask: TaskResponse = {
      ...task,
      status: isCompleted ? 'PENDING' : 'COMPLETED',
      completed_at: isCompleted ? null : new Date().toISOString(),
    };

    this.replaceTaskInSignals(optimisticTask);

    const url = isCompleted
      ? API_ENDPOINTS.TASKS.REOPEN(task.id)
      : API_ENDPOINTS.TASKS.COMPLETE(task.id);

    return this.http.post<TaskResponse>(url, null, { withCredentials: true }).pipe(
      tap((updated) => {
        this.replaceTaskInSignals(updated);
      }),
      catchError((err: unknown) => {
        this._todayQueue.set(prevQueue);
        this._focusTask.set(prevFocus);
        this._preselectedTask.set(prevPreselected);
        this._errorState.set(
          extractExecutionError(err, 'Không thể cập nhật trạng thái nhiệm vụ. Vui lòng thử lại.')
        );
        return of(null);
      })
    );
  }

  startBreak(type: 'short' | 'long', minutes: number): void {
    const safeMinutes = Math.max(1, minutes);
    const totalSec = Math.round(safeMinutes * 60);

    this.stopBreakInterval();
    this._activeBreakType.set(type);
    this._breakDurationMinutes.set(safeMinutes);
    this._breakRemainingSeconds.set(totalSec);
    this.breakStartedAt = Date.now();
    this.breakPausedMs = 0;
    this.breakPauseTimestamp = null;
    this._isBreakRunning.set(true);
    this.startBreakInterval();
  }

  pauseBreak(): void {
    if (!this._isBreakRunning()) return;
    this._isBreakRunning.set(false);
    this.breakPauseTimestamp = Date.now();
    this.stopBreakInterval();
  }

  resumeBreak(): void {
    if (this._isBreakRunning() || !this._activeBreakType() || this.breakStartedAt === null) {
      return;
    }
    if (this.breakPauseTimestamp) {
      this.breakPausedMs += Date.now() - this.breakPauseTimestamp;
      this.breakPauseTimestamp = null;
    }
    this._isBreakRunning.set(true);
    this.recalculateBreakRemainingTime();
    this.startBreakInterval();
  }

  stopBreak(): void {
    this.stopBreakInterval();
    this.breakStartedAt = null;
    this.breakPausedMs = 0;
    this.breakPauseTimestamp = null;
    this._isBreakRunning.set(false);
    this._activeBreakType.set(null);
    this._breakDurationMinutes.set(5);
    this._breakRemainingSeconds.set(300);
  }

  /**
   * Hydrate local timer state from a StudySessionResponse (for active session recovery or start).
   */
  hydrateActiveSession(session: StudySessionResponse, freshStart = false): void {
    this._activeSession.set(session);
    const sessionTaskIds = (session.session_tasks ?? []).map((t) => t.task_id);
    const currentFocusId = this.activeFocusTaskId();
    if (!currentFocusId || !sessionTaskIds.includes(currentFocusId)) {
      this.activeFocusTaskId.set(sessionTaskIds[0] ?? null);
    }
    const planned = Math.max(1, session.planned_minutes || 25);
    this.durationMinutes.set(planned);

    if (session.scratchpad_content !== undefined && session.scratchpad_content !== null) {
      this._scratchpadNote.set(session.scratchpad_content);
    }

    const parsedStart = Date.parse(session.started_at);
    this.startedAt = freshStart || Number.isNaN(parsedStart) ? Date.now() : parsedStart;
    this.pausedMs = 0;
    this.pauseTimestamp = null;
    this.pomodoroCountedForCurrentSession = false;
    this._lastHeartbeatAt.set(session.last_heartbeat_at ?? null);
    this._heartbeatStatus.set('synced');

    this.recalculateRemainingTime();
    this.isRunning.set(true);
    this.startCountdownTimer();
    this.startHeartbeat(session.id);
  }

  private resetLocalSessionState(): void {
    this.stopTimersAndHeartbeat();
    this._activeSession.set(null);
    this.startedAt = null;
    this.pausedMs = 0;
    this.pauseTimestamp = null;
    this.pomodoroCountedForCurrentSession = false;
    this.isRunning.set(false);
    this.durationMinutes.set(25);
    this.remainingSeconds.set(25 * 60);
    this.elapsedSeconds.set(0);
    this._scratchpadNote.set('');
    this._heartbeatStatus.set('idle');
    this._lastHeartbeatAt.set(null);
  }

  private replaceTaskInSignals(updated: TaskResponse): void {
    this._todayQueue.update((list) =>
      list.map((item) => (item.id === updated.id ? updated : item))
    );
    if (this._focusTask()?.id === updated.id) {
      this._focusTask.set(updated);
    }
    if (this._preselectedTask()?.id === updated.id) {
      this._preselectedTask.set(updated);
    }
  }

  private startCountdownTimer(): void {
    this.stopCountdownTimer();
    this.timerSubscription = interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.recalculateRemainingTime();
      });
  }

  private stopCountdownTimer(): void {
    if (this.timerSubscription) {
      this.timerSubscription.unsubscribe();
      this.timerSubscription = null;
    }
  }

  private recalculateRemainingTime(): void {
    if (!this.startedAt) return;
    const now = Date.now();
    const currentPausedMs = this.pauseTimestamp
      ? this.pausedMs + (now - this.pauseTimestamp)
      : this.pausedMs;
    const elapsedSec = Math.max(0, Math.floor((now - this.startedAt - currentPausedMs) / 1000));

    this.elapsedSeconds.set(elapsedSec);

    if (this.mode() === 'stopwatch') {
      this.remainingSeconds.set(0);
      return;
    }

    const totalSec = this.durationMinutes() * 60;
    const remaining = Math.max(0, totalSec - elapsedSec);
    this.remainingSeconds.set(remaining);

    if (remaining === 0 && this.isRunning()) {
      this._timerCompletedTick.update((n) => n + 1);
      if (!this.pomodoroCountedForCurrentSession) {
        this.incrementCompletedPomodorosToday();
        this.pomodoroCountedForCurrentSession = true;
      }
      this.pauseSession();
    }
  }

  private startBreakInterval(): void {
    this.stopBreakInterval();
    this.breakTimerSubscription = interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.recalculateBreakRemainingTime();
      });
  }

  private stopBreakInterval(): void {
    if (this.breakTimerSubscription) {
      this.breakTimerSubscription.unsubscribe();
      this.breakTimerSubscription = null;
    }
  }

  private recalculateBreakRemainingTime(): void {
    if (this.breakStartedAt === null) return;
    const now = Date.now();
    const currentPausedMs = this.breakPauseTimestamp
      ? this.breakPausedMs + (now - this.breakPauseTimestamp)
      : this.breakPausedMs;
    const elapsedSec = Math.max(
      0,
      Math.floor((now - this.breakStartedAt - currentPausedMs) / 1000)
    );
    const totalSec = Math.round(this._breakDurationMinutes() * 60);
    const remaining = Math.max(0, totalSec - elapsedSec);

    this._breakRemainingSeconds.set(remaining);

    if (remaining === 0 && this._isBreakRunning()) {
      this._timerCompletedTick.update((n) => n + 1);
      this.stopBreak();
    }
  }

  private getLocalDateString(): string {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private loadPomodorosToday(): number {
    if (typeof localStorage === 'undefined' || typeof localStorage?.getItem !== 'function') {
      return 0;
    }
    try {
      const raw = localStorage.getItem('focusflow_pomodoros_today_v1');
      if (!raw) return 0;
      const parsed = JSON.parse(raw) as { date?: unknown; count?: unknown };
      if (parsed.date === this.getLocalDateString() && typeof parsed.count === 'number') {
        return Math.max(0, Math.floor(parsed.count));
      }
    } catch {
      return 0;
    }
    return 0;
  }

  private incrementCompletedPomodorosToday(): void {
    const today = this.getLocalDateString();
    const hasStorage =
      typeof localStorage !== 'undefined' &&
      typeof localStorage?.getItem === 'function' &&
      typeof localStorage?.setItem === 'function';

    let current = 0;
    if (hasStorage) {
      try {
        const raw = localStorage.getItem('focusflow_pomodoros_today_v1');
        if (raw) {
          const parsed = JSON.parse(raw) as { date?: unknown; count?: unknown };
          if (parsed.date === today && typeof parsed.count === 'number') {
            current = Math.max(0, Math.floor(parsed.count));
          }
        }
      } catch {
        current = this._localPomodorosToday();
      }
    } else {
      current = this._localPomodorosToday();
    }

    const nextCount = current + 1;
    this._localPomodorosToday.set(nextCount);
    this._localPomodoroDelta.update((delta) => delta + 1);

    if (hasStorage) {
      try {
        localStorage.setItem(
          'focusflow_pomodoros_today_v1',
          JSON.stringify({ date: today, count: nextCount })
        );
      } catch {
        // Ignore storage quota errors
      }
    }
  }

  private startHeartbeat(sessionId: string): void {
    this.stopHeartbeat();
    // Send heartbeat every 60 seconds (ADR-004, BUSR-09)
    this.heartbeatSubscription = interval(60000)
      .pipe(
        switchMap(() => {
          if (!this.isRunning() || this.sessionId() !== sessionId) {
            return of(null);
          }
          return this.sendHeartbeat();
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe();
  }

  private stopHeartbeat(): void {
    if (this.heartbeatSubscription) {
      this.heartbeatSubscription.unsubscribe();
      this.heartbeatSubscription = null;
    }
  }

  private stopTimersAndHeartbeat(): void {
    this.stopCountdownTimer();
    this.stopHeartbeat();
  }
}
