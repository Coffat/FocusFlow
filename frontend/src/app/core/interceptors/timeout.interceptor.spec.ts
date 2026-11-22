import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpContext,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TimeoutError } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  DEFAULT_HTTP_TIMEOUT_MS,
  HTTP_TIMEOUT_MS,
  SKIP_HTTP_TIMEOUT,
  timeoutInterceptor,
} from './timeout.interceptor';

describe('timeoutInterceptor', () => {
  let http: HttpClient;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    vi.useFakeTimers();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([timeoutInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    vi.useRealTimers();
  });

  it('cho phép request hoàn thành bình thường trong thời gian chờ mặc định', () => {
    let result: unknown;
    http.get('/api/v1/roadmaps').subscribe((res) => {
      result = res;
    });

    const req = httpTesting.expectOne('/api/v1/roadmaps');
    vi.advanceTimersByTime(DEFAULT_HTTP_TIMEOUT_MS - 100);
    req.flush({ ok: true });

    expect(result).toEqual({ ok: true });
  });

  it('ném TimeoutError khi request vượt quá DEFAULT_HTTP_TIMEOUT_MS (30s)', () => {
    let caughtError: unknown;
    http.get('/api/v1/roadmaps').subscribe({
      error: (err) => {
        caughtError = err;
      },
    });

    const req = httpTesting.expectOne('/api/v1/roadmaps');
    vi.advanceTimersByTime(DEFAULT_HTTP_TIMEOUT_MS);

    expect(caughtError).toBeInstanceOf(TimeoutError);
    expect(req.cancelled).toBe(true);
  });

  it('tôn trọng giá trị HTTP_TIMEOUT_MS tùy chỉnh trên HttpContext', () => {
    let caughtError: unknown;
    http
      .get('/api/v1/slow-endpoint', {
        context: new HttpContext().set(HTTP_TIMEOUT_MS, 5_000),
      })
      .subscribe({
        error: (err) => {
          caughtError = err;
        },
      });

    const req = httpTesting.expectOne('/api/v1/slow-endpoint');
    vi.advanceTimersByTime(4_900);
    expect(caughtError).toBeUndefined();

    vi.advanceTimersByTime(100);
    expect(caughtError).toBeInstanceOf(TimeoutError);
    expect(req.cancelled).toBe(true);
  });

  it('bỏ qua timeout khi request đặt SKIP_HTTP_TIMEOUT = true', () => {
    let result: unknown;
    let caughtError: unknown;
    http
      .get('/api/v1/export', {
        context: new HttpContext().set(SKIP_HTTP_TIMEOUT, true),
      })
      .subscribe({
        next: (res) => {
          result = res;
        },
        error: (err) => {
          caughtError = err;
        },
      });

    const req = httpTesting.expectOne('/api/v1/export');
    vi.advanceTimersByTime(DEFAULT_HTTP_TIMEOUT_MS * 3);
    expect(caughtError).toBeUndefined();
    expect(req.cancelled).toBe(false);

    req.flush({ exported: true });
    expect(result).toEqual({ exported: true });
  });
});
