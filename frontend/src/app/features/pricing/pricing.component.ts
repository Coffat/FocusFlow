import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
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

@Component({
  selector: 'app-pricing',
  standalone: true,
  imports: [FloatingNavbarComponent, LandingFooterComponent],
  templateUrl: './pricing.component.html',
  styleUrl: './pricing.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PricingComponent {
  protected readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  // Billing Cycle Signal
  readonly billingCycle = signal<BillingCycle>('monthly');

  // Computed Pricing Labels
  readonly premiumMonthlyPrice = computed(() =>
    this.billingCycle() === 'monthly' ? '199.000đ' : '165.000đ'
  );

  readonly premiumBillingNote = computed(() =>
    this.billingCycle() === 'monthly'
      ? '/ tháng (thanh toán từng tháng)'
      : '/ tháng (thanh toán 1.990.000đ / năm)'
  );

  // Mini-FAQ accordion state
  readonly faqOpenIndex = signal<number | null>(null);

  // 4 Feature Categories in Capability Matrix (SRS v1.3)
  readonly capabilityMatrix: readonly MatrixCategory[] = [
    {
      title: 'Không gian Học tập cốt lõi (Core Experience)',
      rows: [
        {
          name: 'Số lộ trình học tập đồng thời (ACTIVE)',
          freeValue: 'Tối đa 3 lộ trình',
          premiumValue: 'Không giới hạn',
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
          premiumValue: '300 lượt / tháng',
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
          premiumValue: 'Hỗ trợ ưu tiên 1-on-1 trong 4h',
        },
      ],
    },
  ];

  // Mini-FAQ Data
  readonly miniFaqItems: readonly PricingFaqItem[] = [
    {
      question: 'Tôi có thể chuyển đổi giữa gói tháng và gói năm bất kỳ lúc nào không?',
      answer:
        'Hoàn toàn có thể. Khi bạn nâng cấp từ gói tháng lên gói năm, số tiền dư của tháng hiện tại sẽ được tự động quy đổi thành số ngày tương ứng trong gói năm. Bạn cũng có thể quay lại gói tháng khi chu kỳ năm kết thúc.',
    },
    {
      question: 'Điều gì xảy ra khi chu kỳ sử dụng kết thúc hoặc tôi muốn hủy gói Premium?',
      answer:
        'Bạn có thể hủy đăng ký bất kỳ lúc nào chỉ với một cú nhấp chuột trong Cài đặt tài khoản. Tài khoản của bạn vẫn giữ trọn vẹn quyền lợi Premium cho đến ngày cuối cùng của chu kỳ đã thanh toán, sau đó tự động chuyển về Gói Miễn Phí mà không mất mát bất kỳ dữ liệu nào.',
    },
    {
      question: 'FocusFlow có chính sách ưu đãi cho sinh viên và giảng viên không?',
      answer:
        'Có. Sinh viên và giảng viên đăng ký bằng email có đuôi trường học (.edu.vn hoặc tương đương) sẽ nhận được ưu đãi giảm thêm 35% trên mức giá niêm yết cho gói Premium sau khi xác thực danh tính học thuật.',
    },
    {
      question: 'Chính sách hoàn tiền 14 ngày hoạt động như thế nào?',
      answer:
        'Nếu trong 14 ngày đầu tiên sử dụng FocusFlow Premium bạn cảm thấy phương pháp điều phối thích ứng không phù hợp với nhịp học tập của mình, chỉ cần nhấn nút "Yêu cầu hoàn tiền" trong trang cài đặt hoặc gửi email cho chúng tôi. 100% học phí sẽ được hoàn trả nguyên vẹn không cần giải trình lý do.',
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
        this.router.navigate(['/dashboard']);
      } else {
        this.router.navigate(['/sign-up']);
      }
    } else {
      if (isAuthed) {
        this.router.navigate(['/settings']);
      } else {
        this.router.navigate(['/sign-up'], { queryParams: { plan: 'premium' } });
      }
    }
  }
}
