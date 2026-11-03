import { HttpInterceptorFn } from '@angular/common/http';
import { API_BASE_URL } from '../constant/api.constant';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const isRelativeApi = req.url.startsWith('/api/v1');
  const isApiRequest =
    isRelativeApi ||
    req.url.startsWith(API_BASE_URL) ||
    req.url.startsWith('http://localhost:8000') ||
    req.url.startsWith('http://127.0.0.1:8000');

  const token = localStorage.getItem('access_token') || '';
  const headers: Record<string, string> = {};

  if (token.length > 0 && isApiRequest) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const targetUrl = isRelativeApi ? `${API_BASE_URL}${req.url.slice('/api/v1'.length)}` : req.url;

  const cloned = req.clone({
    url: targetUrl,
    withCredentials: isApiRequest,
    setHeaders: headers
  });

  return next(cloned);
};
