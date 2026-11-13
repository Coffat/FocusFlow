import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable, catchError, finalize, of, tap } from 'rxjs';
import { MessageService } from 'primeng/api';
import { components } from '../api/schema';

export type CalendarConnectionResponseDTO = components['schemas']['CalendarConnectionResponseDTO'];
export type InitiateCalendarAuthResponseDTO = components['schemas']['InitiateCalendarAuthResponseDTO'];

@Injectable({
  providedIn: 'root',
})
export class CalendarIntegrationService {
  private readonly http = inject(HttpClient);
  private readonly messageService = inject(MessageService, { optional: true });

  private readonly _connection = signal<CalendarConnectionResponseDTO | null>(null);
  readonly connection = this._connection.asReadonly();

  private readonly _isLoading = signal<boolean>(false);
  readonly isLoading = this._isLoading.asReadonly();

  readonly isConnected = computed(() => this._connection()?.connected ?? false);

  /**
   * Load external calendar connection status from GET /api/v1/account/calendar/status
   */
  loadStatus(): Observable<CalendarConnectionResponseDTO> {
    this._isLoading.set(true);
    return this.http
      .get<CalendarConnectionResponseDTO>('/api/v1/account/calendar/status', {
        withCredentials: true,
      })
      .pipe(
        tap((res) => {
          this._connection.set(res);
        }),
        catchError((err) => {
          const fallback: CalendarConnectionResponseDTO = {
            connected: false,
            provider: 'GOOGLE',
            sync_status: 'REVOKED',
            error_detail: err?.message || 'Không thể lấy trạng thái kết nối Google Calendar',
          };
          this._connection.set(fallback);
          return of(fallback);
        }),
        finalize(() => {
          this._isLoading.set(false);
        })
      );
  }

  /**
   * Connect to Google Calendar via full redirect OAuth (UC-17)
   */
  connectGoogleCalendar(returnTo: string = '/settings'): void {
    this._isLoading.set(true);
    this.http
      .post<InitiateCalendarAuthResponseDTO>(
        '/api/v1/account/calendar/google/authorize',
        {
          sync_type: 'two_way',
          return_to: returnTo,
        },
        { withCredentials: true }
      )
      .subscribe({
        next: (res) => {
          if (res.authorization_url) {
            window.location.href = res.authorization_url;
          } else {
            this._isLoading.set(false);
            this.showToast(
              'error',
              'Lỗi chuyển hướng',
              'Không nhận được đường dẫn ủy quyền từ máy chủ.'
            );
          }
        },
        error: (err) => {
          this._isLoading.set(false);
          this.showToast(
            'error',
            'Lỗi kết nối',
            err?.error?.detail ||
              'Không thể khởi tạo phiên kết nối Google Calendar. Vui lòng thử lại.'
          );
        },
      });
  }

  /**
   * Disconnect Google Calendar and revoke watch channel
   */
  disconnectGoogleCalendar(): Observable<CalendarConnectionResponseDTO> {
    this._isLoading.set(true);
    return this.http
      .post<CalendarConnectionResponseDTO>(
        '/api/v1/account/calendar/disconnect',
        {},
        { withCredentials: true }
      )
      .pipe(
        tap((res) => {
          this._connection.set(res);
          this.showToast(
            'info',
            'Đã ngắt kết nối',
            'Đã hủy liên kết Google Calendar thành công.'
          );
        }),
        catchError((err) => {
          this.showToast(
            'error',
            'Lỗi ngắt kết nối',
            err?.error?.detail || 'Không thể ngắt kết nối Google Calendar.'
          );
          throw err;
        }),
        finalize(() => {
          this._isLoading.set(false);
        })
      );
  }

  /**
   * Inspect URL query parameters for OAuth callback result (?calendar_connected=success|error)
   */
  checkUrlCallback(route: ActivatedRoute, router: Router): void {
    const params = route.snapshot.queryParamMap;
    const status = params.get('calendar_connected');
    if (!status) {
      return;
    }

    if (status === 'success') {
      this.showToast(
        'success',
        'Kết nối Google Calendar thành công',
        'Lịch học FocusFlow của bạn đã được liên kết và đồng bộ tự động 2 chiều.'
      );
      this.loadStatus().subscribe();
    } else if (status === 'error') {
      const errorDetail = params.get('error_detail');
      this.showToast(
        'error',
        'Lỗi kết nối Google Calendar',
        errorDetail
          ? decodeURIComponent(errorDetail)
          : 'Ủy quyền Google Calendar thất bại hoặc bị hủy.'
      );
    }

    router.navigate([], {
      relativeTo: route,
      queryParams: { calendar_connected: null, error_detail: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  private showToast(
    severity: 'success' | 'info' | 'warn' | 'error',
    summary: string,
    detail: string
  ): void {
    if (this.messageService) {
      this.messageService.add({
        severity,
        summary,
        detail,
        life: 5000,
      });
    }
  }
}
