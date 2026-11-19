import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
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
  StudyScenariosComponent,
} from '../../shared/components/study-scenarios/study-scenarios.component';

export interface ArchitectureIntegrationItem {
  label: string;
  icon: string;
}

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

  readonly architectureIntegrations: readonly ArchitectureIntegrationItem[] = [
    { label: 'Chu trình 6 bước SRL', icon: 'autorenew' },
    { label: '3-Tier Validation Gate', icon: 'verified_user' },
    { label: 'RAG Grounding (pgvector)', icon: 'manage_search' },
    { label: '2-Stage SSE Streaming', icon: 'stream' },
    { label: 'Google Calendar OAuth2', icon: 'event' },
    { label: 'WebCal (.ics RFC 5545)', icon: 'rss_feed' },
  ];

  readonly testimonials: readonly TestimonialItem[] = [
    {
      quote:
        'Nhờ tách biệt Lộ trình và Lịch học Mode B, tuần nào đi làm về muộn mình chỉ cần chạy lại tối ưu hóa lịch và xem bản nháp trước khi bấm Áp dụng. Không còn cảnh AI tự ý ép giờ hay phá vỡ thứ tự bài học.',
      authorName: 'Đăng Nguyên',
      authorRole: 'Học viên Cao học CNTT • TP.HCM',
      avatarInitials: 'ĐN',
      badgeColor: 'bg-secondary-container text-on-secondary-container',
    },
    {
      quote:
        'Những hôm tăng ca chỉ còn đúng 15 phút buổi tối, chế độ Minimum Viable Session giúp mình giữ nhịp học mà không bị đứt quãng, kèm ghi chú Key Takeaways tối thiểu 20 ký tự để chốt lại kiến thức cốt lõi.',
      authorName: 'Thanh Loan',
      authorRole: 'Backend Engineer',
      avatarInitials: 'TL',
      badgeColor: 'bg-surface-container-high text-on-surface',
    },
    {
      quote:
        'Trước khi cam kết ôn chứng chỉ AWS, Feasibility Check báo thẳng tổng thời lượng đang vượt quỹ giờ rảnh Mode A của mình. Nhờ chỉnh lại phạm vi ngay từ bản nháp, mình đi hết lộ trình đúng hạn.',
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
