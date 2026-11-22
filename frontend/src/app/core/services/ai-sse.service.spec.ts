import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { API_ENDPOINTS } from '../constants/api-endpoints';
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
    createdEventSources.push(this);
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
let createdEventSources: FakeEventSource[] = [];

describe('AiSseService', () => {
  let service: AiSseService;
  let httpTesting: HttpTestingController;
  let mockSessionStore: Record<string, string> = {};

  beforeEach(() => {
    createdEventSources = [];
    mockSessionStore = {};
    vi.stubGlobal('EventSource', FakeEventSource);
    vi.stubGlobal('sessionStorage', {
      getItem: (key: string) => mockSessionStore[key] ?? null,
      setItem: (key: string, value: string) => {
        mockSessionStore[key] = value;
      },
      removeItem: (key: string) => {
        delete mockSessionStore[key];
      },
      clear: () => {
        mockSessionStore = {};
      },
      key: (index: number) => Object.keys(mockSessionStore)[index] ?? null,
      get length() {
        return Object.keys(mockSessionStore).length;
      },
    });
    TestBed.configureTestingModule({
      providers: [AiSseService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AiSseService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
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

  it('thử refresh phiên một lần khi EventSource đóng đột ngột (401) và nối lại luồng thành công', () => {
    const received: AiStreamChunkEvent[] = [];
    let completed = false;
    let transportError: unknown;

    service.observeJobStream('/api/v1/roadmaps/jobs/job-401/stream').subscribe({
      next: event => received.push(event),
      error: error => (transportError = error),
      complete: () => (completed = true),
    });

    expect(createdEventSources).toHaveLength(1);
    const firstSource = createdEventSources[0];
    firstSource.readyState = FakeEventSource.CLOSED;
    firstSource.onerror?.(new Event('error'));

    const refreshReq = httpTesting.expectOne(API_ENDPOINTS.AUTH.REFRESH);
    expect(refreshReq.request.method).toBe('POST');
    expect(refreshReq.request.withCredentials).toBe(true);
    refreshReq.flush({ ok: true });

    expect(createdEventSources).toHaveLength(2);
    const reopenedSource = createdEventSources[1];
    reopenedSource.emit('completed', { stage: 'COMPLETED', progress: 100 });

    expect(received).toHaveLength(1);
    expect(received[0].stage).toBe('COMPLETED');
    expect(completed).toBe(true);
    expect(transportError).toBeUndefined();
  });

  it('phát lỗi SSE_CONNECTION_LOST khi refresh phiên thất bại sau khi EventSource đóng đột ngột', () => {
    let transportError: unknown;
    service.observeJobStream('/api/v1/roadmaps/jobs/job-401-fail/stream').subscribe({
      error: error => (transportError = error),
    });

    fakeEventSource.readyState = FakeEventSource.CLOSED;
    fakeEventSource.onerror?.(new Event('error'));

    const refreshReq = httpTesting.expectOne(API_ENDPOINTS.AUTH.REFRESH);
    refreshReq.flush({ detail: 'Refresh expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(createdEventSources).toHaveLength(1);
    expect(transportError).toBeInstanceOf(SseStreamError);
    expect((transportError as SseStreamError).code).toBe('SSE_CONNECTION_LOST');
  });

  it('không lặp refresh lần thứ hai nếu EventSource sau khi nối lại tiếp tục bị CLOSED', () => {
    let transportError: unknown;
    service.observeJobStream('/api/v1/roadmaps/jobs/job-401-twice/stream').subscribe({
      error: error => (transportError = error),
    });

    createdEventSources[0].readyState = FakeEventSource.CLOSED;
    createdEventSources[0].onerror?.(new Event('error'));

    const refreshReq = httpTesting.expectOne(API_ENDPOINTS.AUTH.REFRESH);
    refreshReq.flush({ ok: true });

    expect(createdEventSources).toHaveLength(2);
    createdEventSources[1].readyState = FakeEventSource.CLOSED;
    createdEventSources[1].onerror?.(new Event('error'));

    httpTesting.expectNone(API_ENDPOINTS.AUTH.REFRESH);
    expect(transportError).toBeInstanceOf(SseStreamError);
    expect((transportError as SseStreamError).code).toBe('SSE_CONNECTION_LOST');
  });

  it('lưu, đọc, xóa active job theo roadmapId + stage trong sessionStorage và tự hủy bản ghi quá hạn', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-22T10:00:00Z'));

    service.saveActiveJob('rm-1', 'MILESTONES', {
      jobId: 'job-m1',
      streamUrl: '/api/v1/roadmaps/jobs/job-m1/stream',
    });
    service.saveActiveJob('rm-1', 'PROPOSAL', {
      jobId: 'job-p1',
      streamUrl: '/api/v1/roadmaps/jobs/job-p1/stream',
    });

    const milestoneJob = service.getActiveJob('rm-1', 'MILESTONES');
    expect(milestoneJob?.jobId).toBe('job-m1');
    expect(milestoneJob?.streamUrl).toBe('/api/v1/roadmaps/jobs/job-m1/stream');
    expect(service.getActiveJob('rm-1', 'PROPOSAL')?.jobId).toBe('job-p1');
    expect(service.getActiveJob('rm-2', 'MILESTONES')).toBeNull();

    service.clearActiveJob('rm-1', 'MILESTONES');
    expect(service.getActiveJob('rm-1', 'MILESTONES')).toBeNull();
    expect(service.getActiveJob('rm-1', 'PROPOSAL')?.jobId).toBe('job-p1');

    // Advance past 10m TTL -> expired record is auto-cleared
    vi.advanceTimersByTime(11 * 60_000);
    expect(service.getActiveJob('rm-1', 'PROPOSAL')).toBeNull();
  });
});
