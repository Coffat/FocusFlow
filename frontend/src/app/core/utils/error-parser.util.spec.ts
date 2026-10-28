import { HttpErrorResponse } from '@angular/common/http';
import { parseHttpErrorMessage } from './error-parser.util';

describe('ErrorParserUtil', () => {
  it('should return fallback message when error is null or undefined', () => {
    expect(parseHttpErrorMessage(null, 'Fallback error')).toBe('Fallback error');
    expect(parseHttpErrorMessage(undefined, 'Fallback error')).toBe('Fallback error');
  });

  it('should extract error message from FastAPI 422 detail array and strip Value error prefix', () => {
    const errorResponse = new HttpErrorResponse({
      error: {
        detail: [
          {
            loc: ['body', 'password'],
            msg: 'Value error, Mật khẩu phải chứa ít nhất 1 chữ số.',
            type: 'value_error'
          }
        ]
      },
      status: 422,
      statusText: 'Unprocessable Entity'
    });

    const parsed = parseHttpErrorMessage(errorResponse);
    expect(parsed).toBe('Mật khẩu phải chứa ít nhất 1 chữ số.');
  });

  it('should extract string detail message from HttpErrorResponse', () => {
    const errorResponse = new HttpErrorResponse({
      error: {
        detail: 'Invalid credentials. Please verify your email and password.'
      },
      status: 401,
      statusText: 'Unauthorized'
    });

    const parsed = parseHttpErrorMessage(errorResponse);
    expect(parsed).toBe('Invalid credentials. Please verify your email and password.');
  });

  it('should extract error.message when detail is absent', () => {
    const errorResponse = new HttpErrorResponse({
      error: {
        message: 'Custom server error message'
      },
      status: 500
    });

    expect(parseHttpErrorMessage(errorResponse)).toBe('Custom server error message');
  });

  it('should fall back to err.message if error body has no details', () => {
    const errorResponse = new HttpErrorResponse({
      status: 503,
      statusText: 'Service Unavailable'
    });

    const parsed = parseHttpErrorMessage(errorResponse, 'Default fallback');
    expect(parsed).toContain('503 Service Unavailable');
  });
});
