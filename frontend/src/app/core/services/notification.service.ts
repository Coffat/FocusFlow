import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { API_ENDPOINTS } from '../constants/api-endpoints';
import type { components } from '../api/schema';

export type NotificationItemDTO = components['schemas']['NotificationItemDTO'];
export type NotificationListResponseDTO = components['schemas']['NotificationListResponseDTO'];
export type MarkAllNotificationsReadResponseDTO =
  components['schemas']['MarkAllNotificationsReadResponseDTO'];

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  private readonly http = inject(HttpClient);

  readonly items = signal<NotificationItemDTO[]>([]);
  readonly unreadCount = signal<number>(0);
  readonly loading = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  loadNotifications(limit = 20, offset = 0): void {
    this.loading.set(true);
    this.error.set(null);

    const params = new HttpParams().set('limit', String(limit)).set('offset', String(offset));

    this.http
      .get<NotificationListResponseDTO>(API_ENDPOINTS.NOTIFICATIONS.LIST, {
        params,
        withCredentials: true,
      })
      .subscribe({
        next: (res) => {
          this.items.set(res.items ?? []);
          this.unreadCount.set(res.unread_count ?? 0);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('Không thể tải thông báo. Vui lòng thử lại.');
          this.loading.set(false);
        },
      });
  }

  markRead(id: string): Observable<NotificationItemDTO> {
    return this.http
      .post<NotificationItemDTO>(
        API_ENDPOINTS.NOTIFICATIONS.MARK_READ(id),
        {},
        { withCredentials: true },
      )
      .pipe(
        tap((updated) => {
          let decremented = false;
          this.items.update((list) =>
            list.map((item) => {
              if (item.id === id) {
                if (!item.is_read && updated.is_read) {
                  decremented = true;
                }
                return updated;
              }
              return item;
            }),
          );
          if (decremented) {
            this.unreadCount.update((c) => Math.max(0, c - 1));
          }
        }),
      );
  }

  markAllRead(): Observable<MarkAllNotificationsReadResponseDTO> {
    return this.http
      .post<MarkAllNotificationsReadResponseDTO>(
        API_ENDPOINTS.NOTIFICATIONS.READ_ALL,
        {},
        { withCredentials: true },
      )
      .pipe(
        tap(() => {
          const nowIso = new Date().toISOString();
          this.items.update((list) =>
            list.map((item) =>
              item.is_read ? item : { ...item, is_read: true, read_at: item.read_at ?? nowIso },
            ),
          );
          this.unreadCount.set(0);
        }),
      );
  }
}
