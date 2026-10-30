import { DestroyRef, Injectable, Signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { Observable } from 'rxjs';
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
  readonly stage: 'RESERVED' | 'STREAMING' | 'VALIDATING_TIER_1_2_3' | 'COMPLETED' | 'FAILED';
  readonly progress: number;
  readonly deltaText?: string;
  readonly delta_text?: string;
  readonly retry_attempt?: number;
  readonly violations?: components['schemas']['ConstraintViolationSchema'][];
  readonly payload?: T;
  readonly error?: string;
  readonly error_code?: string;
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

  observeJobStream<TPayload = unknown>(streamUrl: string): Observable<AiStreamChunkEvent<TPayload>> {
    return new Observable<AiStreamChunkEvent<TPayload>>(subscriber => {
      const eventSource = new EventSource(streamUrl, { withCredentials: true });

      const handleEvent = (rawEvent: MessageEvent<string>, eventType: SseEventType) => {
        try {
          const parsed = JSON.parse(rawEvent.data) as AiStreamChunkEvent<TPayload>;
          const normalized: AiStreamChunkEvent<TPayload> = {
            ...parsed,
            eventType,
            deltaText: parsed.deltaText ?? parsed.delta_text,
          };
          subscriber.next(normalized);
          if (
            normalized.stage === 'COMPLETED' ||
            normalized.stage === 'FAILED' ||
            eventType === 'completed' ||
            eventType === 'failed'
          ) {
            eventSource.close();
            subscriber.complete();
          }
        } catch (err) {
          subscriber.error(err);
        }
      };

      eventSource.onmessage = (event: MessageEvent<string>) => {
        handleEvent(event, 'message');
      };

      const namedEvents: readonly SseEventType[] = [
        'stage',
        'chunk',
        'validation_retry',
        'completed',
        'failed',
      ];
      for (const evtName of namedEvents) {
        if (typeof eventSource.addEventListener === 'function') {
          eventSource.addEventListener(evtName, (event: Event) => {
            handleEvent(event as MessageEvent<string>, evtName);
          });
        }
      }

      eventSource.onerror = (error: Event) => {
        eventSource.close();
        subscriber.error(error);
      };

      return () => {
        eventSource.close();
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
