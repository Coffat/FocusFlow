import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { signal } from '@angular/core';
import { PricingComponent } from './pricing.component';
import { AuthService } from '../../core/services/auth.service';

describe('PricingComponent', () => {
  let component: PricingComponent;
  let fixture: ComponentFixture<PricingComponent>;
  let router: Router;
  let authServiceMock: {
    isAuthenticated: ReturnType<typeof signal<boolean>>;
  };

  beforeEach(async () => {
    authServiceMock = {
      isAuthenticated: signal<boolean>(false),
    };

    await TestBed.configureTestingModule({
      imports: [PricingComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PricingComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockImplementation(() => Promise.resolve(true));
    fixture.detectChanges();
  });

  it('should create and render default billing cycle and tiers', () => {
    expect(component).toBeTruthy();
    expect(component.billingCycle()).toBe('monthly');
    expect(component.premiumMonthlyPrice()).toBe('199.000đ');

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Gói Miễn Phí (Free)');
    expect(el.textContent).toContain('Gói Nâng Cao (Premium)');
    expect(el.textContent).toContain('199.000đ');
  });

  it('should toggle billing cycle and update displayed prices', () => {
    component.setBillingCycle('annual');
    fixture.detectChanges();

    expect(component.billingCycle()).toBe('annual');
    expect(component.premiumMonthlyPrice()).toBe('165.000đ');

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('165.000đ');
    expect(el.textContent).toContain('1.990.000đ / năm');

    component.setBillingCycle('monthly');
    fixture.detectChanges();

    expect(component.billingCycle()).toBe('monthly');
    expect(component.premiumMonthlyPrice()).toBe('199.000đ');
  });

  it('should navigate unauthenticated user to sign-up on selectPlan', () => {
    authServiceMock.isAuthenticated.set(false);

    component.selectPlan('free');
    expect(router.navigate).toHaveBeenCalledWith(['/sign-up']);

    component.selectPlan('premium');
    expect(router.navigate).toHaveBeenCalledWith(['/sign-up'], {
      queryParams: { plan: 'premium' },
    });
  });

  it('should navigate authenticated user to dashboard or settings on selectPlan', () => {
    authServiceMock.isAuthenticated.set(true);

    component.selectPlan('free');
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);

    component.selectPlan('premium');
    expect(router.navigate).toHaveBeenCalledWith(['/settings']);
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
    expect(component.capabilityMatrix.length).toBe(4);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Không gian Học tập cốt lõi (Core Experience)');
    expect(el.textContent).toContain('Trí tuệ Nhân tạo & Cổng Kiểm định (AI Reasoning & Verification)');
    expect(el.textContent).toContain('Môi trường Kỷ luật & Đo lường SRL (Self-Regulated Learning)');
    expect(el.textContent).toContain('Lưu trữ, Đo lường & Hỗ trợ Chuyên biệt');
  });
});
