import { DestroyRef, Injectable, Signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { Observable } from 'rxjs';

export interface SseJobTicketResponse {
  readonly jobId: string;
  readonly reservationId: string;
  readonly streamUrl: string;
}

export interface AiStreamChunkEvent<T = unknown> {
  readonly stage: 'RESERVED' | 'STREAMING' | 'VALIDATING_TIER_1_2_3' | 'COMPLETED' | 'FAILED';
  readonly progress: number;
  readonly deltaText?: string;
  readonly payload?: T;
  readonly error?: string;
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

  initiateStreamJob<TRequest>(endpoint: string, body: TRequest): Observable<SseJobTicketResponse> {
    return this.http.post<SseJobTicketResponse>(endpoint, body);
  }

  observeJobStream<TPayload = unknown>(streamUrl: string): Observable<AiStreamChunkEvent<TPayload>> {
    return new Observable<AiStreamChunkEvent<TPayload>>(subscriber => {
      const eventSource = new EventSource(streamUrl, { withCredentials: true });

      eventSource.onmessage = (event: MessageEvent<string>) => {
        try {
          const parsed = JSON.parse(event.data) as AiStreamChunkEvent<TPayload>;
          subscriber.next(parsed);
          if (parsed.stage === 'COMPLETED' || parsed.stage === 'FAILED') {
            eventSource.close();
            subscriber.complete();
          }
        } catch (err) {
          subscriber.error(err);
        }
      };

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
          progress: 0
        }
      }
    );
  }
}
