import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { provideRouter, Router } from '@angular/router';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { PricingComponent } from './pricing.component';
import { AuthService } from '../../core/services/auth.service';
import {
  BillingService,
  type BillingConfigResponseDTO,
  type BillingWebhookResponseDTO,
  type CheckoutResponseDTO,
} from '../../core/services/billing.service';

describe('PricingComponent', () => {
  let component: PricingComponent;
  let fixture: ComponentFixture<PricingComponent>;
  let router: Router;
  let authServiceMock: {
    isAuthenticated: ReturnType<typeof signal<boolean>>;
    checkSession: ReturnType<typeof vi.fn>;
  };
  let billingServiceMock: {
    getBillingConfig: ReturnType<typeof vi.fn>;
    createCheckout: ReturnType<typeof vi.fn>;
    listTransactions: ReturnType<typeof vi.fn>;
    confirmMockCheckout: ReturnType<typeof vi.fn>;
  };

  const freeBetaConfig: BillingConfigResponseDTO = {
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
      {
        plan_code: 'PREMIUM_YEARLY',
        name: 'Premium Hàng Năm',
        amount_vnd: 990000,
        currency: 'VND',
        billing_cycle: 'YEARLY',
        ai_monthly_limit: 300,
        max_active_roadmaps: 15,
      },
    ],
  };

  const paidEnabledConfig: BillingConfigResponseDTO = {
    ...freeBetaConfig,
    release_mode: 'PAID_ENABLED',
    checkout_enabled: true,
    mock_confirm_enabled: true,
    provider: 'local_mock',
    status_message: 'Thanh toán Premium đang hoạt động ở chế độ thử nghiệm.',
  };

  const mockCheckoutRes: CheckoutResponseDTO = {
    transaction_id: 'tx-123',
    transaction_ref: 'FF-2026-MOCK',
    plan_code: 'PREMIUM_MONTHLY',
    amount_vnd: 99000,
    status: 'PENDING',
    provider: 'local_mock',
    checkout_url: 'http://localhost:8000/mock/checkout/tx-123',
    qr_code_url: 'http://localhost:8000/mock/qr/tx-123',
    expires_at: '2026-11-21T10:30:00Z',
    is_mock_provider: true,
  };

  const mockSettlementRes: BillingWebhookResponseDTO = {
    status: 'COMPLETED',
    transaction_id: 'tx-123',
    already_processed: false,
  };

  function createComponent(config: BillingConfigResponseDTO = freeBetaConfig): void {
    billingServiceMock.getBillingConfig.mockReturnValue(of(config));
    fixture = TestBed.createComponent(PricingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  beforeEach(async () => {
    authServiceMock = {
      isAuthenticated: signal<boolean>(false),
      checkSession: vi.fn().mockReturnValue(of(true)),
    };
    billingServiceMock = {
      getBillingConfig: vi.fn().mockReturnValue(of(freeBetaConfig)),
      createCheckout: vi.fn().mockReturnValue(of(mockCheckoutRes)),
      listTransactions: vi.fn().mockReturnValue(of([])),
      confirmMockCheckout: vi.fn().mockReturnValue(of(mockSettlementRes)),
    };

    await TestBed.configureTestingModule({
      imports: [PricingComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceMock },
        { provide: BillingService, useValue: billingServiceMock },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockImplementation(() => Promise.resolve(true));
    createComponent(freeBetaConfig);
  });

  it('should create and render server-owned prices, entitlements, and FREE_BETA banner by default', () => {
    expect(component).toBeTruthy();
    expect(component.billingCycle()).toBe('monthly');
    expect(component.premiumMonthlyPrice()).toBe('99.000đ');
    expect(component.checkoutEnabled()).toBe(false);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Gói Miễn Phí (Free)');
    expect(el.textContent).toContain('Gói Nâng Cao (Premium)');
    expect(el.textContent).toContain('99.000đ');
    expect(el.textContent).toContain('300 lượt / tháng');
    expect(el.textContent).toContain('15 lộ trình ACTIVE');

    const betaBanner = el.querySelector('[data-testid="billing-free-beta-banner"]');
    expect(betaBanner?.textContent).toContain(freeBetaConfig.status_message);

    const premiumBtn = el.querySelector(
      '[data-testid="pricing-select-premium-btn"]',
    ) as HTMLButtonElement;
    expect(premiumBtn.disabled).toBe(true);
    expect(premiumBtn.textContent).toContain('Sắp ra mắt (Free Beta)');
  });

  it('should block checkout call and keep modal closed in FREE_BETA mode', () => {
    authServiceMock.isAuthenticated.set(true);
    component.selectPlan('premium');
    component.openPremiumCheckout();
    fixture.detectChanges();

    expect(billingServiceMock.createCheckout).not.toHaveBeenCalled();
    expect(component.checkoutModalOpen()).toBe(false);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="billing-checkout-modal"]')).toBeNull();
  });

  it('should toggle billing cycle and update displayed server-owned prices', () => {
    component.setBillingCycle('annual');
    fixture.detectChanges();

    expect(component.billingCycle()).toBe('annual');
    expect(component.premiumMonthlyPrice()).toBe('82.500đ');

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('82.500đ');
    expect(el.textContent).toContain('990.000đ / năm');

    component.setBillingCycle('monthly');
    fixture.detectChanges();

    expect(component.billingCycle()).toBe('monthly');
    expect(component.premiumMonthlyPrice()).toBe('99.000đ');
  });

  it('should navigate unauthenticated user to sign-up on selectPlan when PAID_ENABLED', () => {
    createComponent(paidEnabledConfig);
    authServiceMock.isAuthenticated.set(false);

    component.selectPlan('free');
    expect(router.navigate).toHaveBeenCalledWith(['/sign-up']);

    component.selectPlan('premium');
    expect(router.navigate).toHaveBeenCalledWith(['/sign-up'], {
      queryParams: { plan: 'premium' },
    });
  });

  it('should open billing checkout modal and run mock-confirm flow when PAID_ENABLED + mock_confirm_enabled (FE-API-05)', () => {
    createComponent(paidEnabledConfig);
    authServiceMock.isAuthenticated.set(true);

    component.selectPlan('free');
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="billing-free-beta-banner"]')).toBeNull();
    const premiumBtn = el.querySelector(
      '[data-testid="pricing-select-premium-btn"]',
    ) as HTMLButtonElement;
    expect(premiumBtn.disabled).toBe(false);

    component.selectPlan('premium');
    fixture.detectChanges();

    expect(billingServiceMock.createCheckout).toHaveBeenCalledWith('PREMIUM_MONTHLY');
    expect(component.checkoutModalOpen()).toBe(true);

    expect(el.querySelector('[data-testid="billing-checkout-modal"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="billing-mock-badge"]')?.textContent).toContain(
      'Chế độ mô phỏng (Dev/Test)',
    );
    expect(el.querySelector('[data-testid="billing-amount"]')?.textContent).toContain('99,000đ');

    const confirmBtn = el.querySelector(
      '[data-testid="billing-mock-confirm-btn"]',
    ) as HTMLButtonElement;
    expect(confirmBtn).toBeTruthy();
    authServiceMock.checkSession.mockClear();
    confirmBtn.click();
    fixture.detectChanges();

    expect(billingServiceMock.confirmMockCheckout).toHaveBeenCalledWith('tx-123');
    expect(authServiceMock.checkSession).toHaveBeenCalledTimes(1);
    expect(el.querySelector('[data-testid="billing-mock-success-banner"]')).toBeTruthy();
  });

  it('FE-API-05: hiển thị banner lỗi trung thực khi cổng thanh toán trả về HTTP 503 ở chế độ PAID_ENABLED và KHÔNG báo thành công giả', () => {
    createComponent(paidEnabledConfig);
    authServiceMock.isAuthenticated.set(true);
    billingServiceMock.createCheckout.mockReturnValueOnce(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 503,
            statusText: 'Service Unavailable',
            error: { detail: 'Cổng thanh toán trực tuyến hiện chưa sẵn sàng.' },
          }),
      ),
    );

    component.setBillingCycle('annual');
    component.selectPlan('premium');
    fixture.detectChanges();

    expect(billingServiceMock.createCheckout).toHaveBeenCalledWith('PREMIUM_YEARLY');
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="billing-checkout-modal"]')).toBeTruthy();
    const errorBanner = el.querySelector('[data-testid="billing-error-banner"]');
    expect(errorBanner?.textContent).toContain('Cổng thanh toán trực tuyến hiện chưa sẵn sàng.');
    expect(el.querySelector('[data-testid="billing-checkout-details"]')).toBeNull();
    expect(el.querySelector('[data-testid="billing-mock-success-banner"]')).toBeNull();
  });

  it('should toggle mini-faq accordion items', () => {
    expect(component.faqOpenIndex()).toBeNull();
    expect(component.isFaqOpen(0)).toBe(false);

    component.toggleFaq(0);
    expect(component.faqOpenIndex()).toBe(0);
    expect(component.isFaqOpen(0)).toBe(true);

    // Toggle same index closes it
    component.toggleFaq(0);
    expect(component.faqOpenIndex()).toBeNull();
    expect(component.isFaqOpen(0)).toBe(false);

    // Toggle another index opens that one
    component.toggleFaq(2);
    expect(component.faqOpenIndex()).toBe(2);
    expect(component.isFaqOpen(2)).toBe(true);
  });

  it('should render capability matrix with 4 categories', () => {
    expect(component.capabilityMatrix().length).toBe(4);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Không gian Học tập cốt lõi (Core Experience)');
    expect(el.textContent).toContain(
      'Trí tuệ Nhân tạo & Cổng Kiểm định (AI Reasoning & Verification)',
    );
    expect(el.textContent).toContain('Môi trường Kỷ luật & Đo lường SRL (Self-Regulated Learning)');
    expect(el.textContent).toContain('Lưu trữ, Đo lường & Hỗ trợ Chuyên biệt');
  });
});
