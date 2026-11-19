import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { FloatingNavbarComponent } from '../../shared/components/floating-navbar/floating-navbar.component';
import { LandingFooterComponent } from '../../shared/components/landing-footer/landing-footer.component';

export type FaqCategoryId = 'all' | 'engine' | 'pedagogy' | 'calendar' | 'pricing';

export interface FaqQuestion {
  id: string;
  orderNumber: string;
  question: string;
  answer: string;
  tags: string[];
}

export interface FaqCategory {
  id: Exclude<FaqCategoryId, 'all'>;
  badge: string;
  title: string;
  subtitle: string;
  questions: FaqQuestion[];
}

@Component({
  selector: 'app-faq',
  standalone: true,
  imports: [FormsModule, FloatingNavbarComponent, LandingFooterComponent],
  templateUrl: './faq.component.html',
  styleUrl: './faq.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FaqComponent {
  protected readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  @ViewChild('searchInput') searchInputElement?: ElementRef<HTMLInputElement>;

  // Interactive Signals
  readonly searchQuery = signal<string>('');
  readonly selectedCategory = signal<FaqCategoryId>('all');

  // Track accordion open state by question id
  readonly openQuestionIds = signal<Record<string, boolean>>({
    q1: true, // First question open by default
  });

  // 10 Core Questions grouped into 4 SRS v1.3 Categories
  readonly faqCategories: readonly FaqCategory[] = [
    {
      id: 'engine',
      badge: '01 / THUẬT TOÁN & ĐỘNG CƠ THÍCH ỨNG',
      title: 'Thuật Toán & Động Cơ Thích Ứng',
      subtitle: 'Triết lý phân rã khoa học Bloom DAG & cơ chế tự phục hồi kế hoạch',
      questions: [
        {
          id: 'q1',
          orderNumber: '01.',
          question: 'FocusFlow khác biệt như thế nào so với Notion hay Google Calendar thông thường?',
          answer:
            'Notion yêu cầu bạn phải tự cấu hình thủ công mọi thứ; Google Calendar chỉ là lịch tĩnh, không tự biết phân rã bài học hay dời lịch khi bạn bận. FocusFlow là hệ thống điều phối chủ động (Active Orchestrator): vừa tự phân rã mục tiêu lớn thành cây tri thức DAG chuẩn khoa học, vừa xếp lịch học theo nhịp sinh học và tự động phục hồi kế hoạch khi có biến cố.',
          tags: ['DAG Engine', 'Auto-Scheduling', 'Active Orchestration'],
        },
        {
          id: 'q2',
          orderNumber: '02.',
          question: 'Thuật toán Domino Shift hoạt động như thế nào khi tôi bị ốm hoặc bận việc đột xuất?',
          answer:
            'Khác với các ứng dụng to-do list dồn ứ việc sang ngày hôm sau gây quá tải tâm lý, Domino Shift coi lịch học như một chuỗi khối động lực học. Thuật toán tự động quét các khung giờ trống dự phòng trong tuần, tịnh tiến bài học bị lỡ sang thời điểm thích hợp nhất mà không vượt quá hạn mức giờ học tối đa mỗi ngày và không tăng chỉ số dời lịch quá đà.',
          tags: ['Domino Shift v2.0', 'Zero-Guilt', 'Burnout Prevention'],
        },
        {
          id: 'q3',
          orderNumber: '03.',
          question: 'Cơ chế phân rã 2 cấp độ có chính xác với các môn kỹ thuật phức tạp (như Khóa luận CNTT)?',
          answer:
            "Rất chính xác. Hệ thống áp dụng thang đo nhận thức Bloom's Taxonomy kết hợp mô hình phân cấp DAG (Directed Acyclic Graph). Mức 1 phân rã thành các Cột mốc năng lực (Milestones - ví dụ: Đặc tả SRS, Kiến trúc Hexagonal, Hiện thực Domain); Mức 2 phân rã thành các Nhiệm vụ nguyên tử (Tasks) có ước lượng số phiên Pomodoro 25 phút. Bạn hoàn toàn có quyền phê duyệt hoặc tinh chỉnh từng mốc trước khi bắt đầu.",
          tags: ["Bloom's Taxonomy", 'Milestones & Tasks', 'Human-in-the-loop'],
        },
        {
          id: 'q4',
          orderNumber: '04.',
          question: 'Cổng kiểm định 3-Tier Validation Gate hoạt động ra sao để loại bỏ ảo giác của AI?',
          answer:
            'Mọi lộ trình AI sinh ra đều phải trải qua 3 tầng chốt chặn tất định trước khi đến tay người học: Tầng 1 (JSON Schema Pydantic v2) kiểm tra cấu trúc dữ liệu nghiêm ngặt; Tầng 2 (DAG Cycle Check) kiểm tra thuật toán đồ thị không chu trình và không có nút cô lập; Tầng 3 (Workload Feasibility) đối chiếu tổng thời lượng với quỹ thời gian rảnh thực tế của bạn, ngăn chặn tình trạng nhồi nhét quá tải 12h/ngày.',
          tags: ['3-Tier Validation', 'Anti-Hallucination', 'DAG Cycle Check'],
        },
      ],
    },
    {
      id: 'pedagogy',
      badge: '02 / MÔI TRƯỜNG TẬP TRUNG & KỶ LUẬT SRL',
      title: 'Môi Trường Tập Trung & Kỷ Luật SRL',
      subtitle: 'Khoa học nhận thức Zimmerman & cơ chế kiểm chứng năng lực thực tế',
      questions: [
        {
          id: 'q5',
          orderNumber: '05.',
          question: 'Tại sao FocusFlow bắt buộc phiên học tối thiểu MVS 10–15 phút?',
          answer:
            'Theo nguyên lý Khoa học Thần kinh Nhận thức (Cognitive Load Theory) và mô hình SRL của Zimmerman, não bộ cần ít nhất 10–15 phút để vượt qua "ma sát khởi động" (activation energy) và kích hoạt mạng lưới Attention Network. Các phiên học dưới 10 phút được xem là bị phân mảnh và không đủ để tạo ra trí nhớ làm việc (working memory) bền vững.',
          tags: ['Minimum Viable Session', 'Cognitive Load', 'Zimmerman SRL'],
        },
        {
          id: 'q6',
          orderNumber: '06.',
          question: 'Cổng kiểm chứng TakeawayGuard (≥ 30 ký tự) ngăn chặn thói quen tự lừa dối như thế nào?',
          answer:
            'Để hoàn thành một phiên Pomodoro, TakeawayGuard yêu cầu bạn đúc kết ít nhất 1 bài học cốt lõi (tối thiểu 30 ký tự và ít nhất 5 từ phân biệt). Thuật toán kiểm tra chống spam ký tự lặp và sao chép tiêu đề bài học. Đây là bước Phản tỉnh (Self-Reflection) bắt buộc trong chu trình SRL giúp củng cố tri thức thay vì chỉ bấm giờ thụ động.',
          tags: ['TakeawayGuard', 'Active Recall', 'Self-Reflection'],
        },
        {
          id: 'q7',
          orderNumber: '07.',
          question: 'Cơ chế Cầu dao STALLED kích hoạt khi nào và xử lý ra sao khi dời lịch ≥ 3 lần?',
          answer:
            'Khi một nhiệm vụ bị hoãn hoặc dời lịch từ 3 lần trở lên, hệ thống sẽ tự động kích hoạt Cầu dao STALLED. Thay vì tiếp tục đẩy dời vô tận, FocusFlow đóng băng nhiệm vụ, yêu cầu phiên phân rã lại (Re-decomposition) thành các bước nhỏ hơn 15 phút hoặc kích hoạt phỏng vấn AI Grill-Me để tìm ra rào cản nhận thức thực sự.',
          tags: ['Circuit Breaker', 'STALLED State', 'Anti-Procrastination'],
        },
      ],
    },
    {
      id: 'calendar',
      badge: '03 / ĐỒNG BỘ ĐA NỀN TẢNG & BẢO MẬT DỮ LIỆU',
      title: 'Đồng Bộ Đa Nền Tảng & Bảo Mật Dữ Liệu',
      subtitle: 'Chuẩn WebCal RFC 5545 và kiến trúc mã hóa không chia sẻ bên thứ 3',
      questions: [
        {
          id: 'q8',
          orderNumber: '08.',
          question: 'Tôi có thể đồng bộ lịch học với Google Calendar hay Apple Calendar như thế nào?',
          answer:
            'Cực kỳ đơn giản chỉ với 1 cú click. FocusFlow cung cấp đường dẫn WebCal (.ics) đạt chuẩn RFC 5545. Bạn chỉ cần dán link này vào Google Calendar, Apple Calendar hoặc Outlook. Mọi phiên học mới hoặc các buổi học được Domino Shift dời lịch sẽ tự động cập nhật lên điện thoại của bạn sau vài giây. Token WebCal được băm SHA-256 bảo đảm an toàn.',
          tags: ['WebCal RFC 5545', 'Google Calendar', 'Apple Calendar'],
        },
        {
          id: 'q9',
          orderNumber: '09.',
          question: 'FocusFlow có lưu trữ thông tin riêng tư hay bán dữ liệu học tập của tôi không?',
          answer:
            'Cam kết 100% KHÔNG. Dữ liệu học tập và ghi chú nháp của bạn được mã hóa đầu cuối với chuẩn AES-256. Hệ thống tuân thủ nghiêm ngặt chuẩn GDPR Điều 17 (Quyền được lãng quên — cho phép xóa sạch toàn bộ dữ liệu chỉ bằng 1 thao tác), không chia sẻ dữ liệu với bất kỳ bên thứ ba hay dùng để huấn luyện mô hình công cộng.',
          tags: ['AES-256 Cloud', 'GDPR Article 17', 'Zero-Data-Brokers'],
        },
      ],
    },
    {
      id: 'pricing',
      badge: '04 / GÓI GIÁ & KHỞI ĐẦU HỌC TẬP',
      title: 'Gói Giá & Khởi Đầu Học Tập',
      subtitle: 'Chính sách hỗ trợ sinh viên và lộ trình tiếp cận 30 giây',
      questions: [
        {
          id: 'q10',
          orderNumber: '10.',
          question: 'Tôi có thể sử dụng FocusFlow hoàn toàn miễn phí không và bắt đầu như thế nào?',
          answer:
            'Có. Gói Sinh Viên (Free) hoàn toàn miễn phí trọn đời với đầy đủ tính năng cốt lõi: 3 lộ trình đồng thời, Pomodoro Zen Mode, thuật toán xếp lịch và đồng bộ lịch. Bạn chỉ cần nhấn nút "Bắt đầu ngay", nhập mục tiêu học tập và trả lời 3 câu hỏi nhanh về quỹ thời gian rảnh. AI sẽ lập tức phác thảo lộ trình mẫu cho bạn trong 30 giây.',
          tags: ['Free Forever', '30s Onboarding', 'Hạn Ngạch 2 Pha'],
        },
      ],
    },
  ];

  // Category Tab Items
  readonly categoryTabs: readonly { id: FaqCategoryId; label: string }[] = [
    { id: 'all', label: 'Tất cả câu hỏi' },
    { id: 'engine', label: 'Động cơ Thích ứng' },
    { id: 'pedagogy', label: 'Kỷ luật SRL & Tập trung' },
    { id: 'calendar', label: 'Tích hợp Lịch & Bảo mật' },
    { id: 'pricing', label: 'Gói Giá & Khởi đầu' },
  ];

  // Filtered Categories based on search query and active tab
  readonly filteredFaqCategories = computed(() => {
    const query = this.searchQuery().toLowerCase().trim();
    const category = this.selectedCategory();

    return this.faqCategories
      .filter((cat) => category === 'all' || cat.id === category)
      .map((cat) => {
        if (!query) {
          return cat;
        }

        const filteredQuestions = cat.questions.filter((q) => {
          return (
            q.question.toLowerCase().includes(query) ||
            q.answer.toLowerCase().includes(query) ||
            q.tags.some((t) => t.toLowerCase().includes(query))
          );
        });

        return {
          ...cat,
          questions: filteredQuestions,
        };
      })
      .filter((cat) => cat.questions.length > 0);
  });

  // Total count of matching questions
  readonly totalMatchingQuestions = computed(() =>
    this.filteredFaqCategories().reduce((acc, cat) => acc + cat.questions.length, 0)
  );

  @HostListener('window:keydown', ['$event'])
  onKeyDown(event: KeyboardEvent): void {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      this.searchInputElement?.nativeElement.focus();
    }
  }

  selectCategory(category: FaqCategoryId): void {
    this.selectedCategory.set(category);
  }

  updateSearchQuery(query: string): void {
    this.searchQuery.set(query);
  }

  clearSearch(): void {
    this.searchQuery.set('');
  }

  toggleQuestion(id: string): void {
    this.openQuestionIds.update((state) => ({
      ...state,
      [id]: !state[id],
    }));
  }

  isQuestionOpen(id: string): boolean {
    // When a search query is entered, auto-expand matching questions
    if (this.searchQuery().trim().length > 0) {
      return true;
    }
    return !!this.openQuestionIds()[id];
  }

  startFreeJourney(): void {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/dashboard']);
    } else {
      this.router.navigate(['/sign-up']);
    }
  }
}
