import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AuthService } from '../../core/services/auth.service';
import {
  BillingConfigResponseDTO,
  BillingService,
  BillingWebhookResponseDTO,
  CheckoutResponseDTO,
} from '../../core/services/billing.service';
import { FloatingNavbarComponent } from '../../shared/components/floating-navbar/floating-navbar.component';
import { LandingFooterComponent } from '../../shared/components/landing-footer/landing-footer.component';

export type BillingCycle = 'monthly' | 'annual';

export interface MatrixFeatureRow {
  name: string;
  freeValue: string;
  premiumValue: string;
  isCheckFree?: boolean;
  isCheckPremium?: boolean;
  isDashFree?: boolean;
}

export interface MatrixCategory {
  title: string;
  rows: MatrixFeatureRow[];
}

export interface PricingFaqItem {
  question: string;
  answer: string;
}

const DEFAULT_BILLING_CONFIG: BillingConfigResponseDTO = {
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

@Component({
  selector: 'app-pricing',
  standalone: true,
  imports: [DatePipe, DecimalPipe, FloatingNavbarComponent, LandingFooterComponent],
  templateUrl: './pricing.component.html',
  styleUrl: './pricing.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PricingComponent {
  protected readonly authService = inject(AuthService);
  private readonly billingService = inject(BillingService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  // Server-owned Billing Release Config (P1C)
  readonly billingConfig = signal<BillingConfigResponseDTO>(DEFAULT_BILLING_CONFIG);
  readonly releaseMode = computed(() => this.billingConfig().release_mode);
  readonly checkoutEnabled = computed(() => this.billingConfig().checkout_enabled);
  readonly mockConfirmEnabled = computed(() => this.billingConfig().mock_confirm_enabled);
  readonly billingStatusMessage = computed(() => this.billingConfig().status_message);

  readonly monthlyPlan = computed(
    () => this.billingConfig().plans.find((p) => p.plan_code === 'PREMIUM_MONTHLY') ?? null,
  );
  readonly yearlyPlan = computed(
    () => this.billingConfig().plans.find((p) => p.plan_code === 'PREMIUM_YEARLY') ?? null,
  );
  readonly premiumAiMonthlyLimit = computed(
    () => this.monthlyPlan()?.ai_monthly_limit ?? this.yearlyPlan()?.ai_monthly_limit ?? 300,
  );
  readonly premiumMaxActiveRoadmaps = computed(
    () => this.monthlyPlan()?.max_active_roadmaps ?? this.yearlyPlan()?.max_active_roadmaps ?? 15,
  );

  // Billing Cycle Signal
  readonly billingCycle = signal<BillingCycle>('monthly');

  // Checkout Modal State (FE-API-05)
  readonly checkoutModalOpen = signal<boolean>(false);
  readonly checkoutLoading = signal<boolean>(false);
  readonly checkoutError = signal<string | null>(null);
  readonly checkoutData = signal<CheckoutResponseDTO | null>(null);
  readonly mockConfirmLoading = signal<boolean>(false);
  readonly mockConfirmSuccess = signal<BillingWebhookResponseDTO | null>(null);

  constructor() {
    if (!this.authService.isAuthenticated()) {
      this.authService.checkSession().pipe(takeUntilDestroyed(this.destroyRef)).subscribe();
    }
    this.billingService
      .getBillingConfig()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (config) => this.billingConfig.set(config),
        error: () => {
          // Fail-closed to honest FREE_BETA defaults if billing config endpoint is unreachable.
        },
      });
  }

  // Computed Pricing Labels (server-owned amounts with SRS v1.3 fallback defaults)
  readonly premiumMonthlyPrice = computed(() => {
    const monthlyAmount = this.monthlyPlan()?.amount_vnd ?? 99000;
    const yearlyAmount = this.yearlyPlan()?.amount_vnd ?? 990000;
    if (this.billingCycle() === 'monthly') {
      return this.formatVnd(monthlyAmount);
    }
    return this.formatVnd(Math.round(yearlyAmount / 12));
  });

  readonly premiumBillingNote = computed(() => {
    const yearlyAmount = this.yearlyPlan()?.amount_vnd ?? 990000;
    return this.billingCycle() === 'monthly'
      ? '/ tháng (thanh toán từng tháng)'
      : `/ tháng (thanh toán ${this.formatVnd(yearlyAmount)} / năm)`;
  });

  // Mini-FAQ accordion state
  readonly faqOpenIndex = signal<number | null>(null);

  // 4 Feature Categories in Capability Matrix (SRS v1.3 / OS-02)
  readonly capabilityMatrix = computed<readonly MatrixCategory[]>(() => [
    {
      title: 'Không gian Học tập cốt lõi (Core Experience)',
      rows: [
        {
          name: 'Số lộ trình học tập đồng thời (ACTIVE)',
          freeValue: 'Tối đa 3 lộ trình',
          premiumValue: `Tối đa ${this.premiumMaxActiveRoadmaps()} lộ trình ACTIVE`,
        },
        {
          name: 'Study Workspace Studio & Pomodoro Zen',
          freeValue: 'Đầy đủ (MVS 10–15p)',
          premiumValue: 'Đầy đủ (MVS 10–15p)',
        },
        {
          name: 'Focus Chamber & Không gian âm thanh mộc',
          freeValue: '2 preset tiêu chuẩn',
          premiumValue: 'Trọn bộ 5 không gian âm thanh',
        },
        {
          name: 'Đồng bộ lịch WebCal RFC 5545 (.ics)',
          freeValue: '1 thiết bị',
          premiumValue: 'Đa thiết bị không giới hạn',
        },
      ],
    },
    {
      title: 'Trí tuệ Nhân tạo & Cổng Kiểm định (AI Reasoning & Verification)',
      rows: [
        {
          name: 'Hạn ngạch AI phân rã & cố vấn hàng tháng',
          freeValue: '30 lượt / tháng',
          premiumValue: `${this.premiumAiMonthlyLimit()} lượt / tháng`,
        },
        {
          name: 'Mô hình suy luận & 2-Stage SSE Streaming',
          freeValue: 'Tốc độ tiêu chuẩn',
          premiumValue: 'Ưu tiên băng thông cao, độ trễ thấp',
        },
        {
          name: 'Cổng kiểm định 3-Tier Validation Gate',
          freeValue: 'Đầy đủ 3 cấp',
          premiumValue: 'Đầy đủ 3 cấp',
        },
        {
          name: 'Động cơ thích ứng lịch tự động Domino Shift',
          freeValue: 'Tất định (0 AI quota)',
          premiumValue: 'Tất định + Ưu tiên dự phòng (0 AI quota)',
        },
      ],
    },
    {
      title: 'Môi trường Kỷ luật & Đo lường SRL (Self-Regulated Learning)',
      rows: [
        {
          name: 'Cổng nghiệm thu TakeawayGuard (≥ 30 ký tự)',
          freeValue: 'Bắt buộc',
          premiumValue: 'Bắt buộc',
        },
        {
          name: 'Chế độ thi cử & phản biện Prove Mode',
          freeValue: 'Cơ bản',
          premiumValue: 'Chuyên sâu không giới hạn',
        },
        {
          name: 'Báo cáo phản tỉnh AI tuần (Weekly AI Review)',
          freeValue: '—',
          premiumValue: 'Báo cáo nhận thức & khuyến nghị AI',
          isDashFree: true,
        },
        {
          name: 'Cầu dao cảnh báo trì hoãn STALLED (≥ 3 lần dời)',
          freeValue: 'Kích hoạt',
          premiumValue: 'Kích hoạt',
        },
      ],
    },
    {
      title: 'Lưu trữ, Đo lường & Hỗ trợ Chuyên biệt',
      rows: [
        {
          name: 'Lịch sử tiến độ & phân tích nhận thức',
          freeValue: '30 ngày gần nhất',
          premiumValue: 'Lưu trữ trọn đời',
        },
        {
          name: 'Quyền riêng tư & Xuất dữ liệu GDPR Điều 17',
          freeValue: 'Mã hóa AES-256 (JSON)',
          premiumValue: 'Mã hóa AES-256 (JSON, CSV, WebCal)',
        },
        {
          name: 'Kênh giải đáp kỹ thuật & hỗ trợ học thuật',
          freeValue: 'Cộng đồng Discord sinh viên',
          premiumValue: 'Hỗ trợ ưu tiên qua email & tài liệu chuyên sâu',
        },
      ],
    },
  ]);

  // Mini-FAQ Data
  readonly miniFaqItems: readonly PricingFaqItem[] = [
    {
      question: 'FocusFlow hiện đang ở giai đoạn Free Beta nghĩa là gì?',
      answer:
        'Trong giai đoạn Free Beta, toàn bộ tính năng cốt lõi của gói Miễn Phí (3 lộ trình ACTIVE, 30 lượt AI / tháng, Study Workspace, Domino Shift và xuất dữ liệu JSON) hoạt động hoàn toàn miễn phí. Cổng thanh toán gói Premium sẽ được mở khi hoàn tất giai đoạn thử nghiệm.',
    },
    {
      question: 'Tôi có thể chuyển đổi giữa gói tháng và gói năm khi Premium mở bán không?',
      answer:
        'Có. Khi cổng thanh toán gói Premium được kích hoạt, bạn có thể lựa chọn thanh toán linh hoạt theo tháng (99.000đ / tháng) hoặc theo năm (990.000đ / năm — tiết kiệm 2 tháng) và không bị ràng buộc gia hạn ẩn.',
    },
    {
      question: 'Dữ liệu học tập của tôi có bị mất khi thay đổi gói sử dụng không?',
      answer:
        'Không. Mọi lộ trình, ghi chú phiên học, lịch sử Pomodoro và dữ liệu tiến độ luôn thuộc quyền sở hữu của bạn. Bạn cũng có thể tải về toàn bộ bản sao lưu JSON bất kỳ lúc nào trong mục Cài đặt → Tài khoản & Bảo mật.',
    },
    {
      question: 'Hạn ngạch AI hàng tháng và giới hạn lộ trình ACTIVE được tính như thế nào?',
      answer:
        'Gói Miễn Phí cung cấp 30 lượt gọi AI / tháng và tối đa 3 lộ trình ACTIVE đồng thời. Gói Premium nâng lên 300 lượt gọi AI / tháng và tối đa 15 lộ trình ACTIVE (theo chuẩn SRS v1.3). Các thao tác dời lịch tất định Domino Shift không tiêu tốn hạn ngạch AI.',
    },
  ];

  setBillingCycle(cycle: BillingCycle): void {
    this.billingCycle.set(cycle);
  }

  toggleFaq(index: number): void {
    this.faqOpenIndex.update((current) => (current === index ? null : index));
  }

  isFaqOpen(index: number): boolean {
    return this.faqOpenIndex() === index;
  }

  selectPlan(plan: 'free' | 'premium'): void {
    const isAuthed = this.authService.isAuthenticated();

    if (plan === 'free') {
      if (isAuthed) {
        void this.router.navigate(['/dashboard']);
      } else {
        void this.router.navigate(['/sign-up']);
      }
      return;
    }

    if (!this.checkoutEnabled()) {
      return;
    }

    if (isAuthed) {
      this.openPremiumCheckout();
    } else {
      void this.router.navigate(['/sign-up'], { queryParams: { plan: 'premium' } });
    }
  }

  openPremiumCheckout(): void {
    if (!this.checkoutEnabled()) {
      return;
    }

    const planCode = this.billingCycle() === 'annual' ? 'PREMIUM_YEARLY' : 'PREMIUM_MONTHLY';
    this.checkoutModalOpen.set(true);
    this.checkoutLoading.set(true);
    this.checkoutError.set(null);
    this.checkoutData.set(null);
    this.mockConfirmSuccess.set(null);

    this.billingService
      .createCheckout(planCode)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.checkoutData.set(res);
          this.checkoutLoading.set(false);
        },
        error: (err: unknown) => {
          this.checkoutLoading.set(false);
          this.checkoutData.set(null);
          this.checkoutError.set(this.extractCheckoutError(err));
        },
      });
  }

  confirmMockPayment(): void {
    const current = this.checkoutData();
    if (
      !current ||
      !current.is_mock_provider ||
      !this.mockConfirmEnabled() ||
      this.mockConfirmLoading()
    ) {
      return;
    }

    this.mockConfirmLoading.set(true);
    this.checkoutError.set(null);

    this.billingService
      .confirmMockCheckout(current.transaction_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (settlement) => {
          this.mockConfirmLoading.set(false);
          this.mockConfirmSuccess.set(settlement);
          this.checkoutData.set({ ...current, status: settlement.status });
          this.authService.checkSession().pipe(takeUntilDestroyed(this.destroyRef)).subscribe();
        },
        error: (err: unknown) => {
          this.mockConfirmLoading.set(false);
          this.checkoutError.set(this.extractCheckoutError(err));
        },
      });
  }

  closeCheckoutModal(): void {
    this.checkoutModalOpen.set(false);
  }

  private formatVnd(amount: number): string {
    return `${Math.round(amount)
      .toString()
      .replace(/\B(?=(\d{3})+(?!\d))/g, '.')}đ`;
  }

  private extractCheckoutError(err: unknown): string {
    if (err instanceof HttpErrorResponse) {
      const payload = err.error as { detail?: unknown; message?: unknown } | null;
      if (typeof payload?.detail === 'string' && payload.detail.trim()) {
        return payload.detail;
      }
      if (typeof payload?.message === 'string' && payload.message.trim()) {
        return payload.message;
      }
    }
    return 'Cổng thanh toán trực tuyến hiện chưa sẵn sàng. Vui lòng thử lại sau.';
  }
}
