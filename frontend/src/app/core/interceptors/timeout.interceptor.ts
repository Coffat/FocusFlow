import { HttpContextToken, HttpInterceptorFn } from '@angular/common/http';
import { timeout } from 'rxjs';

/** Default timeout for standard HTTP requests (30 seconds). */
export const DEFAULT_HTTP_TIMEOUT_MS = 30_000;

/** Per-request timeout override in milliseconds. */
export const HTTP_TIMEOUT_MS = new HttpContextToken<number>(() => DEFAULT_HTTP_TIMEOUT_MS);

/** Opt-out token for long-running requests that manage their own timeout. */
export const SKIP_HTTP_TIMEOUT = new HttpContextToken<boolean>(() => false);

export const timeoutInterceptor: HttpInterceptorFn = (req, next) => {
  if (req.context.get(SKIP_HTTP_TIMEOUT)) {
    return next(req);
  }

  const timeoutMs = req.context.get(HTTP_TIMEOUT_MS);
  if (timeoutMs <= 0) {
    return next(req);
  }

  return next(req).pipe(timeout(timeoutMs));
};
