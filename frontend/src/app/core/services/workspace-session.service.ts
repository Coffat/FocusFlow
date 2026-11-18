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

export type TodayFocusResponse = components['schemas']['TodayFocusResponse'];
export type StudySessionResponse = components['schemas']['StudySessionResponse'];
export type TaskResponse = components['schemas']['TaskResponse'];
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

  private readonly _scratchpadNote = signal<string>('');
  readonly scratchpadNote = this._scratchpadNote.asReadonly();

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

  readonly formattedTime = computed(() => {
    const totalSec = this.remainingSeconds();
    const minutes = Math.floor(totalSec / 60);
    const seconds = totalSec % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  });

  readonly progressPercentage = computed(() => {
    const total = this.durationMinutes() * 60;
    if (total === 0) return 0;
    const elapsed = total - this.remainingSeconds();
    return Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));
  });

  readonly elapsedMinutes = computed(() => Math.max(0, Math.floor(this.elapsedSeconds() / 60)));

  private startedAt: number | null = null;
  private pausedMs = 0;
  private pauseTimestamp: number | null = null;
  private timerSubscription: Subscription | null = null;
  private heartbeatSubscription: Subscription | null = null;
  private readonly scratchpadSave$ = new Subject<string>();

  private readonly visibilityHandler = (): void => {
    if (typeof document !== 'undefined' && !document.hidden && this.isRunning() && this.startedAt) {
      this.recalculateRemainingTime();
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

  /**
   * Hydrate local timer state from a StudySessionResponse (for active session recovery or start).
   */
  hydrateActiveSession(session: StudySessionResponse, freshStart = false): void {
    this._activeSession.set(session);
    const planned = Math.max(1, session.planned_minutes || 25);
    this.durationMinutes.set(planned);

    if (session.scratchpad_content !== undefined && session.scratchpad_content !== null) {
      this._scratchpadNote.set(session.scratchpad_content);
    }

    const parsedStart = Date.parse(session.started_at);
    this.startedAt = freshStart || Number.isNaN(parsedStart) ? Date.now() : parsedStart;
    this.pausedMs = 0;
    this.pauseTimestamp = null;
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
    this.isRunning.set(false);
    this.durationMinutes.set(25);
    this.remainingSeconds.set(25 * 60);
    this.elapsedSeconds.set(0);
    this._scratchpadNote.set('');
    this._heartbeatStatus.set('idle');
    this._lastHeartbeatAt.set(null);
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
    const totalSec = this.durationMinutes() * 60;
    const remaining = Math.max(0, totalSec - elapsedSec);

    this.elapsedSeconds.set(elapsedSec);
    this.remainingSeconds.set(remaining);

    if (remaining === 0 && this.isRunning()) {
      this.pauseSession();
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
