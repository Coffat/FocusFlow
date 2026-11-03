import { HttpErrorResponse } from '@angular/common/http';

export function parseHttpErrorMessage(
  err: HttpErrorResponse | unknown,
  fallback: string = 'Đã có lỗi xảy ra. Vui lòng thử lại.'
): string {
  if (!err) {
    return fallback;
  }

  if (err instanceof HttpErrorResponse) {
    // 1. FastAPI 422 validation array [{ loc: [...], msg: "...", type: "..." }]
    if (Array.isArray(err.error?.detail) && err.error.detail.length > 0) {
      const firstError = err.error.detail[0];
      const msg = typeof firstError === 'string' ? firstError : firstError?.msg;
      if (typeof msg === 'string') {
        return msg.replace(/^Value error,\s*/i, '');
      }
    }

    // 2. String detail
    if (typeof err.error?.detail === 'string' && err.error.detail.length > 0) {
      return err.error.detail;
    }

    // 3. String message in error body
    if (typeof err.error?.message === 'string' && err.error.message.length > 0) {
      return err.error.message;
    }

    // 4. HTTP status message fallback
    if (typeof err.message === 'string' && err.message.length > 0) {
      return err.message;
    }
  }

  return fallback;
}
