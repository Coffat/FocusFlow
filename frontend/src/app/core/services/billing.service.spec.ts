import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import {
  BillingService,
  type BillingConfigResponseDTO,
  type BillingWebhookResponseDTO,
  type CheckoutResponseDTO,
  type PaymentTransactionDTO,
} from './billing.service';

describe('BillingService (FE-API-05)', () => {
  let service: BillingService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [BillingService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(BillingService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('getBillingConfig gọi GET /api/v1/account/billing/config với withCredentials', async () => {
    const mockConfig: BillingConfigResponseDTO = {
      release_mode: 'FREE_BETA',
      checkout_enabled: false,
      mock_confirm_enabled: false,
      provider: 'none',
      status_message: 'FocusFlow đang trong giai đoạn Free Beta — gói Premium sẽ sớm mở bán.',
      plans: [
        {
          plan_code: 'PREMIUM_MONTHLY',
          name: 'Premium Hàng Tháng',
          amount_vnd: 99000,
          currency: 'VND',
          billing_cycle: 'MONTHLY',
          ai_monthly_limit: 300,
          max_active_roadmaps: 15,
        },
      ],
    };

    const promise = firstValueFrom(service.getBillingConfig());
    const req = httpMock.expectOne('/api/v1/account/billing/config');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush(mockConfig);

    const res = await promise;
    expect(res).toEqual(mockConfig);
  });

  it('createCheckout gửi POST /api/v1/account/billing/checkout với plan_code và withCredentials', async () => {
    const mockRes: CheckoutResponseDTO = {
      transaction_id: 'tx-1',
      transaction_ref: 'FF-2026-001',
      plan_code: 'PREMIUM_MONTHLY',
      amount_vnd: 99000,
      status: 'PENDING',
      provider: 'local_mock',
      checkout_url: 'http://localhost:8000/mock/checkout/tx-1',
      qr_code_url: 'http://localhost:8000/mock/qr/tx-1',
      expires_at: '2026-11-21T10:00:00Z',
      is_mock_provider: true,
    };

    const promise = firstValueFrom(service.createCheckout('PREMIUM_MONTHLY'));
    const req = httpMock.expectOne('/api/v1/account/billing/checkout');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.body).toEqual({ plan_code: 'PREMIUM_MONTHLY' });
    req.flush(mockRes);

    const res = await promise;
    expect(res).toEqual(mockRes);
  });

  it('listTransactions gọi GET /api/v1/account/billing/transactions với withCredentials', async () => {
    const mockTx: PaymentTransactionDTO[] = [
      {
        id: 'tx-1',
        transaction_ref: 'FF-2026-001',
        plan_code: 'PREMIUM_MONTHLY',
        amount_vnd: 99000,
        currency: 'VND',
        status: 'COMPLETED',
        provider: 'local_mock',
        qr_code_url: null,
        webhook_signature_verified: true,
        paid_at: '2026-11-21T09:15:00Z',
        created_at: '2026-11-21T09:00:00Z',
      },
    ];

    const promise = firstValueFrom(service.listTransactions());
    const req = httpMock.expectOne('/api/v1/account/billing/transactions');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush(mockTx);

    const list = await promise;
    expect(list).toEqual(mockTx);
  });

  it('confirmMockCheckout gửi POST /api/v1/account/billing/mock-confirm/{id} với withCredentials', async () => {
    const settled: BillingWebhookResponseDTO = {
      status: 'COMPLETED',
      transaction_id: 'tx-1',
      already_processed: false,
    };

    const promise = firstValueFrom(service.confirmMockCheckout('tx-1'));
    const req = httpMock.expectOne('/api/v1/account/billing/mock-confirm/tx-1');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush(settled);

    const res = await promise;
    expect(res).toEqual(settled);
    expect(res.status).toBe('COMPLETED');
  });
});
