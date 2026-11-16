import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AiSseService, AiStreamChunkEvent } from './ai-sse.service';

class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;

  readonly CONNECTING = FakeEventSource.CONNECTING;
  readonly OPEN = FakeEventSource.OPEN;
  readonly CLOSED = FakeEventSource.CLOSED;
  readyState = FakeEventSource.CONNECTING;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  closed = false;
  private readonly listeners = new Map<string, (event: Event) => void>();

  constructor(
    readonly url: string,
    readonly eventSourceInitDict?: EventSourceInit
  ) {
    fakeEventSource = this;
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject): void {
    if (typeof listener === 'function') {
      this.listeners.set(type, listener);
    }
  }

  close(): void {
    this.closed = true;
    this.readyState = FakeEventSource.CLOSED;
  }

  emit(type: string, data: object): void {
    this.listeners.get(type)?.(new MessageEvent(type, { data: JSON.stringify(data) }));
  }
}

let fakeEventSource: FakeEventSource;

describe('AiSseService', () => {
  let service: AiSseService;

  beforeEach(() => {
    vi.stubGlobal('EventSource', FakeEventSource);
    TestBed.configureTestingModule({ providers: [AiSseService, provideHttpClient()] });
    service = TestBed.inject(AiSseService);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('chuẩn hóa payload lỗi backend và hoàn tất luồng mà không báo mất kết nối', () => {
    const received: AiStreamChunkEvent[] = [];
    let completed = false;
    let transportError: unknown;

    service.observeJobStream('/api/v1/roadmaps/jobs/job-1/stream').subscribe({
      next: event => received.push(event),
      error: error => (transportError = error),
      complete: () => (completed = true),
    });

    fakeEventSource.emit('failed', {
      stage: 'FAILED',
      progress: 100,
      code: 'AI_GATEWAY_TIMEOUT',
      message: 'AI mất quá nhiều thời gian phản hồi. Vui lòng thử lại.',
    });
    fakeEventSource.onerror?.(new Event('error'));

    expect(received[0].error_code).toBe('AI_GATEWAY_TIMEOUT');
    expect(received[0].error).toBe('AI mất quá nhiều thời gian phản hồi. Vui lòng thử lại.');
    expect(completed).toBe(true);
    expect(transportError).toBeUndefined();
  });

  it('giữ kết nối để EventSource tự nối lại khi lỗi mạng chỉ là tạm thời', () => {
    let transportError: unknown;
    service
      .observeJobStream('/api/v1/roadmaps/jobs/job-2/stream')
      .subscribe({ error: error => (transportError = error) });

    fakeEventSource.readyState = FakeEventSource.CONNECTING;
    fakeEventSource.onerror?.(new Event('error'));

    expect(fakeEventSource.closed).toBe(false);
    expect(transportError).toBeUndefined();
  });
});
