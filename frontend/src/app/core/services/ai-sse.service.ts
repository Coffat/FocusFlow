import { DestroyRef, Injectable, Signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { Observable, Subscription } from 'rxjs';
import { API_BASE_URL } from '../../constant/api.constant';
import { API_ENDPOINTS } from '../constants/api-endpoints';
import type { components } from '../api/schema';

export type SseJobTicketResponse = components['schemas']['SseJobTicketResponse'];

export type SseEventType =
  | 'stage'
  | 'chunk'
  | 'validation_retry'
  | 'completed'
  | 'failed'
  | 'message';

export interface AiStreamChunkEvent<T = unknown> {
  readonly eventType?: SseEventType;
  readonly stage:
    | 'RESERVED'
    | 'STREAMING'
    | 'DECOMPOSING_MILESTONES'
    | 'VALIDATING_TIER_1_2_3'
    | 'COMPLETED'
    | 'FAILED';
  readonly progress: number;
  readonly deltaText?: string;
  readonly delta_text?: string;
  readonly milestone_sequence?: number;
  readonly completed_count?: number;
  readonly total_count?: number;
  readonly from_checkpoint?: boolean;
  readonly retry_attempt?: number;
  readonly violations?: components['schemas']['ConstraintViolationSchema'][];
  readonly payload?: T;
  readonly error?: string;
  readonly error_code?: string;
  readonly message?: string;
  readonly code?: string;
}

export type SseStreamErrorCode =
  | 'SSE_TIMEOUT'
  | 'SSE_CONNECTION_LOST'
  | 'SSE_RECONNECT_EXHAUSTED'
  | 'SSE_PARSE_ERROR';

export class SseStreamError extends Error {
  constructor(
    message: string,
    readonly code: SseStreamErrorCode
  ) {
    super(message);
    this.name = 'SseStreamError';
  }
}

export interface SseStreamWatchdogOptions {
  readonly inactivityTimeoutMs?: number;
  readonly maxReconnectAttempts?: number;
}

export type ActiveSseJobStage = 'MILESTONES' | 'PROPOSAL';

export interface ActiveSseJobRecord {
  readonly jobId: string;
  readonly streamUrl: string;
  readonly roadmapId: string;
  readonly stage: ActiveSseJobStage;
  readonly startedAt: number;
}

const DEFAULT_INACTIVITY_TIMEOUT_MS = 90_000;
const DEFAULT_MAX_RECONNECT_ATTEMPTS = 3;
const ACTIVE_JOB_STORAGE_PREFIX = 'focusflow:sse:active';
const ACTIVE_JOB_MAX_AGE_MS = 10 * 60_000;

function pickNonEmpty(...candidates: Array<string | null | undefined>): string | undefined {
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim().length > 0) {
      return candidate.trim();
    }
  }
  return undefined;
}

/**
 * Uniform 2-Stage SSE Streaming Service (ADR-005).
 * Stage 1: POST request reserves ACID AI Quota & returns jobId + streamUrl.
 * Stage 2: Native EventSource wrapped in RxJS Observable -> Angular Signal via toSignal().
 */
@Injectable({ providedIn: 'root' })
export class AiSseService {
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);

  initiateStreamJob<TRequest>(
    endpoint: string,
    body: TRequest,
    idempotencyKey?: string
  ): Observable<SseJobTicketResponse> {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    return this.http.post<SseJobTicketResponse>(endpoint, body, {
      withCredentials: true,
      headers,
    });
  }

  private getActiveJobStorageKey(roadmapId: string, stage: ActiveSseJobStage): string {
    return `${ACTIVE_JOB_STORAGE_PREFIX}:${roadmapId}:${stage}`;
  }

  saveActiveJob(
    roadmapId: string,
    stage: ActiveSseJobStage,
    job: { jobId: string; streamUrl: string }
  ): void {
    if (typeof sessionStorage === 'undefined' || !roadmapId || !job.streamUrl) {
      return;
    }
    const record: ActiveSseJobRecord = {
      jobId: job.jobId,
      streamUrl: job.streamUrl,
      roadmapId,
      stage,
      startedAt: Date.now(),
    };
    try {
      sessionStorage.setItem(this.getActiveJobStorageKey(roadmapId, stage), JSON.stringify(record));
    } catch {
      // Ignore storage quota or privacy-mode errors
    }
  }

  getActiveJob(roadmapId: string, stage: ActiveSseJobStage): ActiveSseJobRecord | null {
    if (typeof sessionStorage === 'undefined' || !roadmapId) {
      return null;
    }
    const key = this.getActiveJobStorageKey(roadmapId, stage);
    try {
      const raw = sessionStorage.getItem(key);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw) as Partial<ActiveSseJobRecord>;
      if (
        typeof parsed.jobId !== 'string' ||
        typeof parsed.streamUrl !== 'string' ||
        parsed.streamUrl.trim().length === 0 ||
        typeof parsed.startedAt !== 'number'
      ) {
        sessionStorage.removeItem(key);
        return null;
      }
      if (Date.now() - parsed.startedAt > ACTIVE_JOB_MAX_AGE_MS) {
        sessionStorage.removeItem(key);
        return null;
      }
      return {
        jobId: parsed.jobId,
        streamUrl: parsed.streamUrl,
        roadmapId,
        stage,
        startedAt: parsed.startedAt,
      };
    } catch {
      return null;
    }
  }

  clearActiveJob(roadmapId: string, stage: ActiveSseJobStage): void {
    if (typeof sessionStorage === 'undefined' || !roadmapId) {
      return;
    }
    try {
      sessionStorage.removeItem(this.getActiveJobStorageKey(roadmapId, stage));
    } catch {
      // Ignore storage access errors
    }
  }

  observeJobStream<TPayload = unknown>(
    streamUrl: string,
    options?: SseStreamWatchdogOptions
  ): Observable<AiStreamChunkEvent<TPayload>> {
    return new Observable<AiStreamChunkEvent<TPayload>>(subscriber => {
      let resolvedUrl = streamUrl;
      if (streamUrl.startsWith('/api/v1')) {
        resolvedUrl = `${API_BASE_URL}${streamUrl.slice('/api/v1'.length)}`;
      }
      const inactivityTimeoutMs = options?.inactivityTimeoutMs ?? DEFAULT_INACTIVITY_TIMEOUT_MS;
      const maxReconnectAttempts = options?.maxReconnectAttempts ?? DEFAULT_MAX_RECONNECT_ATTEMPTS;

      let currentEventSource: EventSource | null = null;
      let refreshSubscription: Subscription | null = null;
      let terminalReceived = false;
      let reconnectAttempts = 0;
      let authRefreshAttempted = false;
      let authRefreshInProgress = false;
      let inactivityTimer: ReturnType<typeof setTimeout> | null = null;

      const clearWatchdog = () => {
        if (inactivityTimer !== null) {
          clearTimeout(inactivityTimer);
          inactivityTimer = null;
        }
      };

      const failAndClose = (message: string, code: SseStreamErrorCode) => {
        if (terminalReceived || subscriber.closed) {
          return;
        }
        terminalReceived = true;
        clearWatchdog();
        refreshSubscription?.unsubscribe();
        refreshSubscription = null;
        currentEventSource?.close();
        subscriber.error(new SseStreamError(message, code));
      };

      const resetWatchdog = () => {
        clearWatchdog();
        if (terminalReceived || subscriber.closed || inactivityTimeoutMs <= 0) {
          return;
        }
        inactivityTimer = setTimeout(() => {
          failAndClose(
            'Luồng AI không phản hồi quá thời gian chờ. Vui lòng thử lại.',
            'SSE_TIMEOUT'
          );
        }, inactivityTimeoutMs);
      };

      const handleEvent = (rawEvent: MessageEvent<string>, eventType: SseEventType) => {
        if (terminalReceived || subscriber.closed) {
          return;
        }
        reconnectAttempts = 0;
        resetWatchdog();
        try {
          const parsed = JSON.parse(rawEvent.data) as AiStreamChunkEvent<TPayload>;
          const isTerminal =
            parsed.stage === 'COMPLETED' ||
            parsed.stage === 'FAILED' ||
            eventType === 'completed' ||
            eventType === 'failed';
          terminalReceived = isTerminal;
          const normalized: AiStreamChunkEvent<TPayload> = {
            ...parsed,
            eventType,
            deltaText: parsed.deltaText ?? parsed.delta_text,
            error: pickNonEmpty(parsed.error, parsed.message),
            error_code: pickNonEmpty(parsed.error_code, parsed.code),
          };
          subscriber.next(normalized);
          if (isTerminal) {
            clearWatchdog();
            currentEventSource?.close();
            subscriber.complete();
          }
        } catch {
          failAndClose('Dữ liệu phản hồi từ luồng SSE không hợp lệ.', 'SSE_PARSE_ERROR');
        }
      };

      const namedEvents: readonly SseEventType[] = [
        'stage',
        'chunk',
        'validation_retry',
        'completed',
        'failed',
      ];

      const openEventSource = () => {
        const es = new EventSource(resolvedUrl, { withCredentials: true });
        currentEventSource = es;

        es.onopen = () => {
          reconnectAttempts = 0;
          resetWatchdog();
        };

        es.onmessage = (event: MessageEvent<string>) => {
          handleEvent(event, 'message');
        };

        for (const evtName of namedEvents) {
          if (typeof es.addEventListener === 'function') {
            es.addEventListener(evtName, (event: Event) => {
              handleEvent(event as MessageEvent<string>, evtName);
            });
          }
        }

        es.onerror = () => {
          if (terminalReceived || subscriber.closed || authRefreshInProgress) {
            return;
          }
          if (es.readyState === EventSource.CLOSED) {
            // EventSource closes immediately on HTTP 401; attempt a single cookie refresh
            // before giving up so an expired 15m access token mid-stream recovers cleanly.
            if (!authRefreshAttempted) {
              authRefreshAttempted = true;
              authRefreshInProgress = true;
              clearWatchdog();
              es.close();

              refreshSubscription = this.http
                .post(API_ENDPOINTS.AUTH.REFRESH, {}, { withCredentials: true })
                .subscribe({
                  next: () => {
                    authRefreshInProgress = false;
                    refreshSubscription = null;
                    if (terminalReceived || subscriber.closed) {
                      return;
                    }
                    reconnectAttempts = 0;
                    resetWatchdog();
                    openEventSource();
                  },
                  error: () => {
                    authRefreshInProgress = false;
                    refreshSubscription = null;
                    failAndClose('Kết nối luồng SSE đã bị đóng đột ngột.', 'SSE_CONNECTION_LOST');
                  },
                });
              return;
            }
            failAndClose('Kết nối luồng SSE đã bị đóng đột ngột.', 'SSE_CONNECTION_LOST');
            return;
          }
          // A transient network interruption moves EventSource to CONNECTING;
          // allow bounded reconnect attempts with Last-Event-ID, then abort cleanly.
          reconnectAttempts += 1;
          if (reconnectAttempts > maxReconnectAttempts) {
            failAndClose(
              'Mất kết nối luồng SSE sau nhiều lần thử kết nối lại. Vui lòng thử lại.',
              'SSE_RECONNECT_EXHAUSTED'
            );
          }
        };
      };

      resetWatchdog();
      openEventSource();

      return () => {
        clearWatchdog();
        refreshSubscription?.unsubscribe();
        refreshSubscription = null;
        currentEventSource?.close();
      };
    });
  }

  connectStreamAsSignal<TPayload = unknown>(
    streamUrl: string
  ): Signal<AiStreamChunkEvent<TPayload>> {
    return toSignal(
      this.observeJobStream<TPayload>(streamUrl).pipe(takeUntilDestroyed(this.destroyRef)),
      {
        initialValue: {
          stage: 'RESERVED',
          progress: 0,
        },
      }
    );
  }
}
