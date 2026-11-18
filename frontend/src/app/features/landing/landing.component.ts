import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { FloatingNavbarComponent } from '../../shared/components/floating-navbar/floating-navbar.component';
import { LandingFooterComponent } from '../../shared/components/landing-footer/landing-footer.component';
import { BentoCardComponent } from '../../shared/components/bento-card/bento-card.component';
import { TestimonialCardComponent } from '../../shared/components/testimonial-card/testimonial-card.component';
import { SkeletonLoaderComponent } from '../../shared/ui/skeleton-loader/skeleton-loader.component';
import { ScrollRevealDirective } from '../../shared/directives/scroll-reveal.directive';
import {
  InteractiveWorkspaceComponent,
  WorkspaceTab,
} from '../../shared/components/interactive-workspace/interactive-workspace.component';
import {
  ScenarioId,
  ScenarioMilestone,
  StudyScenario,
  StudyScenariosComponent,
} from '../../shared/components/study-scenarios/study-scenarios.component';

export type { ScenarioMilestone, StudyScenario };

export interface TestimonialItem {
  quote: string;
  authorName: string;
  authorRole: string;
  avatarInitials: string;
  badgeColor: string;
}

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [
    RouterLink,
    FloatingNavbarComponent,
    LandingFooterComponent,
    BentoCardComponent,
    TestimonialCardComponent,
    SkeletonLoaderComponent,
    ScrollRevealDirective,
    InteractiveWorkspaceComponent,
    StudyScenariosComponent,
  ],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingComponent {
  protected readonly authService = inject(AuthService);

  readonly activeWorkspaceTab = signal<WorkspaceTab>('dag');
  readonly activeScenario = signal<ScenarioId>('thesis');
  readonly mobileMenuOpen = signal<boolean>(false);

  readonly scenarios: Record<ScenarioId, StudyScenario> = {
    thesis: {
      id: 'thesis',
      tabTitle: 'Khóa luận Tốt nghiệp CNTT',
      title: 'Kịch bản: Hoàn thành Đồ án Tốt nghiệp & Khóa luận (12 tuần)',
      objective: 'Mục tiêu: Đạt điểm A, kiến trúc sạch, tài liệu chuẩn IEEE',
      durationBadge: 'Thời lượng: 6h/tuần • Tự thích ứng',
      milestones: [
        {
          timeframe: 'Tuần 1 - 4',
          title: 'SRS & Đặc tả Kiến trúc',
          description: 'Xác lập phạm vi đề tài, thiết kế ERD và sơ đồ tuần tự hệ thống.',
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 5 - 8',
          title: 'Kiến trúc Hexagonal & Core API',
          description: 'Hiện thực hóa domain logic, tích hợp thanh toán và xác thực JWT.',
          status: 'Đang thực thi (Tuần 6)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 9 - 12',
          title: 'Kiểm thử tải & Bảo vệ',
          description: 'Viết luận văn, đo lường benchmark K6 và diễn tập phản biện cùng hội đồng.',
          status: 'Dự kiến',
          statusType: 'upcoming',
        },
      ],
    },
    aws: {
      id: 'aws',
      tabTitle: 'Luyện thi AWS Solutions Architect',
      title: 'Kịch bản: Chinh phục chứng chỉ AWS SAA-C03 (8 tuần)',
      objective: 'Mục tiêu: Đạt chứng chỉ SAA-C03 (800+ điểm), làm chủ 40+ dịch vụ cốt lõi',
      durationBadge: 'Thời lượng: 5h/tuần • Phản xạ thực chiến',
      milestones: [
        {
          timeframe: 'Tuần 1 - 3',
          title: 'IAM, VPC & Mạng Đám Mây Toàn Diện',
          description: 'Cấu hình CIDR, Subnet, Route Table, NAT Gateway và Security Group chuẩn Well-Architected.',
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 4 - 6',
          title: 'Compute, Storage & High Availability',
          description: 'Thiết kế hệ thống Auto Scaling EC2, S3 Tiering, Aurora Serverless v2 và DynamoDB.',
          status: 'Đang thực thi (Tuần 5)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 7 - 8',
          title: 'Mock Exam & Tối Ưu Chi Phí (FinOps)',
          description: 'Giải 6 bộ đề thi thử chuẩn Stephane Maarek, tối ưu hóa chi phí và bảo mật multi-account.',
          status: 'Dự kiến',
          statusType: 'upcoming',
        },
      ],
    },
    ai: {
      id: 'ai',
      tabTitle: 'Chuyển ngành AI Engineer',
      title: 'Kịch bản: Chuyển dịch năng lực AI Engineer (12 tuần)',
      objective: 'Mục tiêu: Làm chủ Fine-tuning LLM, kiến trúc RAG nâng cao & Multi-Agent Harness',
      durationBadge: 'Thời lượng: 8h/tuần • Dự án Portfolio',
      milestones: [
        {
          timeframe: 'Tuần 1 - 4',
          title: 'Nền tảng PyTorch, Transformers & Vector DBs',
          description: 'Toán đại số tuyến tính cho Deep Learning, Transformers self-attention, indexing với pgvector & Qdrant.',
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 5 - 8',
          title: 'Advanced RAG & Multi-Agent Frameworks',
          description: 'Tối ưu Hybrid Search, Re-ranking, Context Compression và xây dựng multi-agent điều phối tuần tự.',
          status: 'Đang thực thi (Tuần 6)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 9 - 12',
          title: 'Fine-tuning Llama/Qwen & Production Deployment',
          description: 'LoRA/QLoRA fine-tuning trên custom dataset, vLLM serving, benchmark throughput và đánh giá Hallucination.',
          status: 'Dự kiến',
          statusType: 'upcoming',
        },
      ],
    },
  };

  readonly currentScenario = computed(() => this.scenarios[this.activeScenario()]);

  readonly testimonials: TestimonialItem[] = [
    {
      quote:
        'Tính năng Domino Shift đã cứu sống khóa luận của mình. Mỗi lần làm thêm ở công ty về muộn, ứng dụng tự tính toán lại mà mình không hề cảm thấy tội lỗi hay nản chí.',
      authorName: 'Đăng Nguyên',
      authorRole: 'Thủ khoa CNTT • ĐH Bách Khoa',
      avatarInitials: 'ĐN',
      badgeColor: 'bg-secondary-container text-on-secondary-container',
    },
    {
      quote:
        'Giao diện phẳng, sạch và tinh tế như một cuốn sổ da đắt tiền. Không có chuông báo phiền nhiễu hay gamification trẻ con. Rất chuẩn mực cho người làm kỹ thuật.',
      authorName: 'Thanh Loan',
      authorRole: 'Senior Backend Engineer',
      avatarInitials: 'TL',
      badgeColor: 'bg-surface-container-high text-on-surface',
    },
    {
      quote:
        'Việc phân rã đồ thị tri thức giúp mình thi đỗ chứng chỉ AWS chỉ trong 5 tuần tự học mỗi tối. Một công cụ định hình tư duy xuất sắc.',
      authorName: 'Minh Huy',
      authorRole: 'Cloud Solutions Architect',
      avatarInitials: 'MH',
      badgeColor: 'bg-tertiary-fixed text-on-tertiary-fixed',
    },
  ];

  setWorkspaceTab(tab: WorkspaceTab): void {
    this.activeWorkspaceTab.set(tab);
  }

  setScenario(scenario: ScenarioId): void {
    this.activeScenario.set(scenario);
  }

  toggleMobileMenu(): void {
    this.mobileMenuOpen.update((v) => !v);
  }

  closeMobileMenu(): void {
    this.mobileMenuOpen.set(false);
  }

  scrollTo(elementId: string, event?: Event): void {
    if (event) {
      event.preventDefault();
    }
    this.closeMobileMenu();
    const element = document.getElementById(elementId);
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}
