import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import {
  CalendarIntegrationService,
  CalendarConnectionResponseDTO,
} from './calendar-integration.service';

describe('CalendarIntegrationService', () => {
  let service: CalendarIntegrationService;
  let httpTesting: HttpTestingController;
  let messageService: MessageService;
  let router: { navigate: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    router = {
      navigate: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        CalendarIntegrationService,
        MessageService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
      ],
    });

    service = TestBed.inject(CalendarIntegrationService);
    httpTesting = TestBed.inject(HttpTestingController);
    messageService = TestBed.inject(MessageService);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('khởi tạo với trạng thái ban đầu connection null và isConnected false', () => {
    expect(service.connection()).toBeNull();
    expect(service.isConnected()).toBe(false);
    expect(service.isLoading()).toBe(false);
  });

  it('loadStatus() gọi GET /api/v1/account/calendar/status và cập nhật signal connection', () => {
    const mockStatus: CalendarConnectionResponseDTO = {
      connected: true,
      provider: 'GOOGLE',
      sync_status: 'ACTIVE',
      external_calendar_id: 'cal_test_123',
      last_synced_at: '2026-11-12T16:00:00Z',
    };

    service.loadStatus().subscribe((res) => {
      expect(res.connected).toBe(true);
      expect(res.sync_status).toBe('ACTIVE');
    });

    const req = httpTesting.expectOne('/api/v1/account/calendar/status');
    expect(req.request.method).toBe('GET');
    req.flush(mockStatus);

    expect(service.connection()).toEqual(mockStatus);
    expect(service.isConnected()).toBe(true);
    expect(service.isLoading()).toBe(false);
  });

  it('connectGoogleCalendar() gửi request tạo URL ủy quyền OAuth', () => {
    service.connectGoogleCalendar('/schedule');

    const req = httpTesting.expectOne('/api/v1/account/calendar/google/authorize');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      sync_type: 'two_way',
      return_to: '/schedule',
    });
  });

  it('disconnectGoogleCalendar() gọi POST /api/v1/account/calendar/disconnect và cập nhật connection', () => {
    const mockDisconnected: CalendarConnectionResponseDTO = {
      connected: false,
      provider: 'GOOGLE',
      sync_status: 'REVOKED',
    };

    service.disconnectGoogleCalendar().subscribe((res) => {
      expect(res.connected).toBe(false);
    });

    const req = httpTesting.expectOne('/api/v1/account/calendar/disconnect');
    expect(req.request.method).toBe('POST');
    req.flush(mockDisconnected);

    expect(service.connection()?.connected).toBe(false);
    expect(service.isConnected()).toBe(false);
  });

  it('checkUrlCallback() hiển thị toast thành công và xóa param khi calendar_connected=success', () => {
    const toastSpy = vi.spyOn(messageService, 'add');
    const mockRoute = {
      snapshot: {
        queryParamMap: {
          get: (key: string) => (key === 'calendar_connected' ? 'success' : null),
        },
      },
    } as unknown as ActivatedRoute;

    service.checkUrlCallback(mockRoute, router as unknown as Router);

    expect(toastSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'success',
        summary: 'Kết nối Google Calendar thành công',
      })
    );

    expect(router.navigate).toHaveBeenCalledWith(
      [],
      expect.objectContaining({
        queryParams: { calendar_connected: null, error_detail: null },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      })
    );

    // loadStatus is triggered
    const req = httpTesting.expectOne('/api/v1/account/calendar/status');
    req.flush({ connected: true, provider: 'GOOGLE', sync_status: 'ACTIVE' });
  });
});
