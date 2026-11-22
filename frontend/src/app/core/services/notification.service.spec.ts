import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import { NotificationService, type NotificationItemDTO } from './notification.service';

describe('NotificationService (FE-MOCK-08)', () => {
  let service: NotificationService;
  let httpMock: HttpTestingController;

  const sampleUnread: NotificationItemDTO = {
    id: 'notif-1',
    notification_type: 'SCHEDULE_APPLIED',
    title: 'Lịch học chính thức đã được áp dụng',
    content: 'Lộ trình Học TypeScript đã có lịch học mới.',
    resource_url: '/schedule',
    is_read: false,
    read_at: null,
    created_at: '2026-11-21T09:00:00Z',
  };

  const sampleRead: NotificationItemDTO = {
    id: 'notif-2',
    notification_type: 'SYSTEM_INFO',
    title: 'Chào mừng đến FocusFlow',
    content: 'Bắt đầu thiết lập thời gian rảnh.',
    resource_url: '/availability',
    is_read: true,
    read_at: '2026-11-20T09:00:00Z',
    created_at: '2026-11-20T08:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [NotificationService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(NotificationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('loadNotifications gọi GET /api/v1/account/notifications với withCredentials và cập nhật items + unreadCount', () => {
    service.loadNotifications(10, 0);
    expect(service.loading()).toBe(true);

    const req = httpMock.expectOne('/api/v1/account/notifications?limit=10&offset=0');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush({
      items: [sampleUnread, sampleRead],
      total: 2,
      unread_count: 1,
    });

    expect(service.loading()).toBe(false);
    expect(service.error()).toBeNull();
    expect(service.items().length).toBe(2);
    expect(service.unreadCount()).toBe(1);
  });

  it('loadNotifications đặt error và KHÔNG sinh thông báo giả khi backend trả lỗi', () => {
    service.loadNotifications();
    const req = httpMock.expectOne('/api/v1/account/notifications?limit=20&offset=0');
    req.flush('Server Error', { status: 500, statusText: 'Internal Server Error' });

    expect(service.loading()).toBe(false);
    expect(service.items()).toEqual([]);
    expect(service.unreadCount()).toBe(0);
    expect(service.error()).toBe('Không thể tải thông báo. Vui lòng thử lại.');
  });

  it('markRead gọi POST /api/v1/account/notifications/{id}/read và giảm unreadCount trên HTTP 200', async () => {
    service.items.set([sampleUnread, sampleRead]);
    service.unreadCount.set(1);

    const promise = firstValueFrom(service.markRead('notif-1'));
    const req = httpMock.expectOne('/api/v1/account/notifications/notif-1/read');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush({
      ...sampleUnread,
      is_read: true,
      read_at: '2026-11-21T09:10:00Z',
    });

    const updated = await promise;
    expect(updated.is_read).toBe(true);
    expect(service.unreadCount()).toBe(0);
    expect(service.items()[0].is_read).toBe(true);
  });

  it('markAllRead gọi POST /api/v1/account/notifications/read-all và đặt tất cả đã đọc + unreadCount = 0', async () => {
    service.items.set([sampleUnread, sampleRead]);
    service.unreadCount.set(1);

    const promise = firstValueFrom(service.markAllRead());
    const req = httpMock.expectOne('/api/v1/account/notifications/read-all');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush({ updated_count: 1 });

    const res = await promise;
    expect(res.updated_count).toBe(1);
    expect(service.unreadCount()).toBe(0);
    expect(service.items().every((i) => i.is_read)).toBe(true);
  });
});
