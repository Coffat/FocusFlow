import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AiSseService, AiStreamChunkEvent, SseStreamError } from './ai-sse.service';

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
    vi.useRealTimers();
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

  it('không để chuỗi error rỗng nuốt mất message khi chuẩn hóa sự kiện failed', () => {
    const received: AiStreamChunkEvent[] = [];
    service.observeJobStream('/api/v1/roadmaps/jobs/job-empty/stream').subscribe({
      next: event => received.push(event),
    });

    fakeEventSource.emit('failed', {
      stage: 'FAILED',
      progress: 100,
      error: '',
      message: 'Thông báo lỗi từ message.',
    });

    expect(received[0].error).toBe('Thông báo lỗi từ message.');
  });

  it('giữ metadata tiến độ logical subjob theo milestone', () => {
    const received: AiStreamChunkEvent[] = [];
    service.observeJobStream('/api/v1/roadmaps/jobs/job-progress/stream').subscribe({
      next: event => received.push(event),
    });

    fakeEventSource.emit('chunk', {
      stage: 'DECOMPOSING_MILESTONES',
      progress: 71,
      milestone_sequence: 4,
      completed_count: 2,
      total_count: 6,
      from_checkpoint: true,
    });

    expect(received[0].stage).toBe('DECOMPOSING_MILESTONES');
    expect(received[0].milestone_sequence).toBe(4);
    expect(received[0].completed_count).toBe(2);
    expect(received[0].total_count).toBe(6);
    expect(received[0].from_checkpoint).toBe(true);
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

  it('đóng EventSource và phát lỗi có kiểm soát khi vòng lặp onerror vượt quá ngưỡng thử lại', () => {
    let transportError: unknown;
    service
      .observeJobStream('/api/v1/roadmaps/jobs/job-loop/stream', { maxReconnectAttempts: 2 })
      .subscribe({ error: error => (transportError = error) });

    fakeEventSource.readyState = FakeEventSource.CONNECTING;
    fakeEventSource.onerror?.(new Event('error'));
    fakeEventSource.onerror?.(new Event('error'));
    expect(fakeEventSource.closed).toBe(false);
    expect(transportError).toBeUndefined();

    // 3rd consecutive error exceeds maxReconnectAttempts (2)
    fakeEventSource.onerror?.(new Event('error'));
    expect(fakeEventSource.closed).toBe(true);
    expect(transportError).toBeInstanceOf(SseStreamError);
    expect((transportError as SseStreamError).code).toBe('SSE_RECONNECT_EXHAUSTED');
  });

  it('đóng EventSource và phát lỗi SSE_TIMEOUT khi luồng im lặng quá thời gian chờ watchdog', () => {
    vi.useFakeTimers();
    let transportError: unknown;
    service
      .observeJobStream('/api/v1/roadmaps/jobs/job-silent/stream', { inactivityTimeoutMs: 5000 })
      .subscribe({ error: error => (transportError = error) });

    // Receive an event at 3s -> resets watchdog
    vi.advanceTimersByTime(3000);
    fakeEventSource.emit('stage', { stage: 'STREAMING', progress: 40 });
    expect(fakeEventSource.closed).toBe(false);

    // 4s after event (total 7s) -> still alive
    vi.advanceTimersByTime(4000);
    expect(fakeEventSource.closed).toBe(false);
    expect(transportError).toBeUndefined();

    // Another 1.1s without events -> watchdog trips
    vi.advanceTimersByTime(1100);
    expect(fakeEventSource.closed).toBe(true);
    expect(transportError).toBeInstanceOf(SseStreamError);
    expect((transportError as SseStreamError).code).toBe('SSE_TIMEOUT');
  });
});
