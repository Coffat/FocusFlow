import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { FloatingNavbarComponent } from '../../shared/components/floating-navbar/floating-navbar.component';
import { LandingFooterComponent } from '../../shared/components/landing-footer/landing-footer.component';

export type DisciplineKey = 'thesis' | 'certificate' | 'language';

export interface DisciplineInfo {
  id: DisciplineKey;
  tabLabel: string;
  badge: string;
  icon: string;
  title: string;
  desc: string;
  highlights: string[];
  codeOrDataTitle: string;
  codeOrDataBadge: string;
  previewType: DisciplineKey;
  milestoneTitle: string;
  milestoneDesc: string;
}

export interface WorkspaceTimerModeInfo {
  id: 'pomodoro' | 'mvs' | 'stopwatch';
  label: string;
  duration: string;
  active: boolean;
}

@Component({
  selector: 'app-features',
  standalone: true,
  imports: [RouterLink, FloatingNavbarComponent, LandingFooterComponent],
  templateUrl: './features.component.html',
  styleUrl: './features.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FeaturesComponent {
  protected readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  // Active Scenario Tab Signal
  readonly activeDisciplineTab = signal<DisciplineKey>('thesis');

  // Real Study Workspace Studio Timer Modes (Pomodoro 25/45/90p, MVS 10-15p, Stopwatch)
  readonly timerModes: readonly WorkspaceTimerModeInfo[] = [
    { id: 'pomodoro', label: 'Pomodoro', duration: '25:00', active: true },
    { id: 'mvs', label: 'MVS', duration: '15:00', active: false },
    { id: 'stopwatch', label: 'Stopwatch', duration: '00:00', active: false },
  ];

  // 3 Real FocusFlow Scenarios (SRS v1.3+ & StudyScenariosComponent aligned)
  readonly disciplinesData: Record<DisciplineKey, DisciplineInfo> = {
    thesis: {
      id: 'thesis',
      tabLabel: 'Đồ án & Nghiên cứu CNTT',
      badge: 'Hybrid RAG • DAG • Prove Mode',
      icon: 'account_tree',
      title: 'Phân rã đồ án phức tạp thành đồ thị DAG khả thi và chứng minh năng lực thực chứng.',
      desc: 'Nạp đặc tả SRS, tài liệu PDF/DOCX hoặc URL qua bộ chỉ mục lai pgvector + tsvector (đóng gói an toàn <untrusted_knowledge_context>). Hệ thống kiểm tra 0 chu trình DAG, đối chiếu quỹ giờ Mode B và kích hoạt Prove Mode ở cuối mỗi Milestone.',
      highlights: [
        'Phỏng vấn Pedagogy Grill-Me (0–3 câu hỏi) làm rõ trình độ nền tảng và ràng buộc',
        'Kiểm tra 0 chu trình DAG qua DagCycleValidator và quy tắc khóa bài học tiên quyết',
        'Prove Mode đối chiếu Key Takeaways phát hiện điểm mù & Confidence Calibration Gap',
      ],
      codeOrDataTitle: 'roadmap_feasibility.json',
      codeOrDataBadge: '● Tier 2 Verified',
      previewType: 'thesis',
      milestoneTitle: 'Phê duyệt 2 Cấp độ & Feasibility Check',
      milestoneDesc: 'Chỉ ghi OfficialSchedule khi người học bấm Áp dụng (Apply) từ bản nháp DRAFT.',
    },
    certificate: {
      id: 'certificate',
      tabLabel: 'Chứng chỉ & Người đi làm',
      badge: 'BUSY_PRO • FIT_CAPACITY • MVS',
      icon: 'schedule',
      title: 'Giữ vững tiến độ chứng chỉ dài hạn ngay cả trong những tuần tăng ca bận rộn.',
      desc: 'Cấu hình nhanh với Preset BUSY_PRO và chế độ FIT_CAPACITY tự thu gọn phạm vi theo quỹ giờ thực tế. Ngày bận chỉ cần 10–15 phút Minimum Viable Session (MVS) để bảo toàn chuỗi kỷ luật mà không gãy lịch.',
      highlights: [
        'Tái tối ưu lịch khi đổi giờ rảnh (reoptimize-schedule) tốn 0 AI credit',
        'Heartbeat 60s & Auto-Recovery bảo toàn phiên MVS >= 10 phút thành PARTIAL_COMPLETED',
        'Domino Shift tịnh tiến lịch khi Pause/Resume mà không tăng reschedule_count',
      ],
      codeOrDataTitle: 'workspace_session_spec.json',
      codeOrDataBadge: '● Heartbeat 60s',
      previewType: 'certificate',
      milestoneTitle: 'Bảo Toàn Nhịp Học Không Áp Lực',
      milestoneDesc: 'TakeawayGuard yêu cầu >= 30 ký tự & >= 6 từ phân biệt với 0 AI credit.',
    },
    language: {
      id: 'language',
      tabLabel: 'Ngoại ngữ & Tự học Dài hạn',
      badge: 'Focus Shield • Web Audio • Weekly Review',
      icon: 'psychology',
      title: 'Học sâu theo khung năng lượng sinh học và phản tư định kỳ mỗi tuần.',
      desc: 'Phân bổ các khối học đòi hỏi tập trung cao vào khung giờ năng lượng HIGH trong Mode B. Kết hợp Study Workspace Studio với 5 kênh âm thanh Web Audio API, Focus Shield chống rời tab và báo cáo Weekly AI Review tổng kết tuần.',
      highlights: [
        '5 kênh âm thanh tổng hợp Web Audio API (Mưa, Cafe, Brown/Pink Noise, Lò sưởi)',
        'Focus Shield đếm sao nhãng rời tab, tính Focus Score, hỗ trợ Zen Lock & Parking Lot',
        'Hồ sơ Người học 4x3 (EXPLICIT / OBSERVED / INFERRED) lưu giữ xuyên suốt nhiều lộ trình',
      ],
      codeOrDataTitle: 'weekly_review_summary.json',
      codeOrDataBadge: '● SRL Reflection',
      previewType: 'language',
      milestoneTitle: 'Khép Kín Chu Trình Zimmerman SRL',
      milestoneDesc: 'Đo lường 4 chỉ số: Tổng giờ tập trung, Task Completion, Plan Adherence và WRLS.',
    },
  };

  readonly currentDiscipline = computed(() => this.disciplinesData[this.activeDisciplineTab()]);

  setDiscipline(discipline: DisciplineKey): void {
    this.activeDisciplineTab.set(discipline);
  }

  getStarted(): void {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/roadmaps']);
    } else {
      this.router.navigate(['/sign-up']);
    }
  }
}
