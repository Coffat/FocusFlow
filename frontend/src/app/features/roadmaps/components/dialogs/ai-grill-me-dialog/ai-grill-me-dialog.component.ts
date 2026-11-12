import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RoadmapService } from '../../../services/roadmap.service';
import {
  ClarificationAnswerItem,
  ClarificationQuestion,
  PriorKnowledgeLevel,
} from '../../../models/roadmap.model';

export const STANDARD_PEDAGOGICAL_QUESTIONS: ClarificationQuestion[] = [
  {
    question_id: 'q1',
    id: 'q1',
    text: 'Rào cản lớn nhất hoặc mảng kiến thức nào bạn cần ưu tiên củng cố nhất trong mục tiêu này?',
    question:
      'Rào cản lớn nhất hoặc mảng kiến thức nào bạn cần ưu tiên củng cố nhất trong mục tiêu này?',
    placeholder: 'Nhập trọng tâm hoặc chọn phương án gợi ý...',
    question_type: 'single_choice',
    options: [
      'Củng cố lý thuyết cốt lõi & thực hành từ đầu',
      'Tập trung giải đề & dự án thực chiến chuyên sâu',
      'Khắc phục điểm nghẽn kiến trúc & tối ưu hiệu năng',
    ],
    question_purpose: 'Xác định trọng số phân bổ thời lượng cho từng cột mốc.',
    expected_answer_format: 'short_text',
    diagnostic_dimension: 'KNOWLEDGE_BASELINE',
  },
  {
    question_id: 'q2',
    id: 'q2',
    text: 'Khung giờ nào trong ngày bạn duy trì trạng thái tập trung sâu (Flow State) hiệu quả nhất?',
    question:
      'Khung giờ nào trong ngày bạn duy trì trạng thái tập trung sâu (Flow State) hiệu quả nhất?',
    placeholder: 'Chọn nhịp sinh học học tập của bạn...',
    question_type: 'single_choice',
    options: [
      'Evening Deep Work (20:00 - 22:00)',
      'Morning Focus (06:00 - 08:00)',
      'Weekend Intensive & Linh hoạt buổi tối',
    ],
    question_purpose: 'Đồng bộ hóa các phiên Pomodoro khó với nhịp sinh học của bạn.',
    expected_answer_format: 'short_text',
    diagnostic_dimension: 'LEARNING_CONSTRAINTS',
  },
  {
    question_id: 'q3',
    id: 'q3',
    text: 'Khi bận đột xuất và lỡ các phiên học trong tuần, bạn muốn hệ thống thích ứng như thế nào?',
    question:
      'Khi bận đột xuất và lỡ các phiên học trong tuần, bạn muốn hệ thống thích ứng như thế nào?',
    placeholder: 'Chọn cơ chế tái cân bằng lịch...',
    question_type: 'single_choice',
    options: [
      'Dời lịch Domino Shift (+2 ngày, bảo toàn nhịp độ)',
      'Phân bổ bù vào các khung giờ trống cuối tuần',
      'Đưa vào Hàng chờ Backlog để tự sắp xếp',
    ],
    question_purpose: 'Cấu hình chiến lược thích ứng Domino Shift v2.',
    expected_answer_format: 'short_text',
    diagnostic_dimension: 'PRACTICAL_EXPERIENCE',
  },
];

@Component({
  selector: 'app-ai-grill-me-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-grill-me-dialog.component.html',
  styleUrl: './ai-grill-me-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiGrillMeDialogComponent {
  readonly roadmapService = inject(RoadmapService);

  readonly goalTitle = input<string>('');
  readonly baselineLevel = input<PriorKnowledgeLevel>('INTERMEDIATE');
  readonly weeklyHours = input<number>(12);
  readonly targetDeadline = input<string>('');

  readonly backToStep1 = output<void>();
  readonly skipInterview = output<void>();
  readonly generateQuestions = output<void>();
  readonly submitAnswers = output<ClarificationAnswerItem[]>();

  readonly answersMap = signal<Record<string, string>>({});

  readonly questions = computed<ClarificationQuestion[]>(() =>
    this.roadmapService.clarificationQuestions()
  );

  readonly displayGoalTitle = computed<string>(() => {
    return (
      this.goalTitle() ||
      this.roadmapService.selectedRoadmapDetail()?.title ||
      'Mục tiêu học tập cá nhân hóa'
    );
  });

  readonly displayLevel = computed<string>(() => {
    return (
      this.baselineLevel() ||
      this.roadmapService.selectedRoadmapDetail()?.goal?.prior_knowledge_level ||
      'INTERMEDIATE'
    );
  });

  readonly displayDeadline = computed<string>(() => {
    return (
      this.targetDeadline() ||
      this.roadmapService.selectedRoadmapDetail()?.target_date ||
      '12 tuần'
    );
  });

  readonly answeredCount = computed<number>(() => {
    const qs = this.questions();
    const map = this.answersMap();
    return qs.filter(q => {
      const qid = q.question_id || q.id;
      return Boolean(map[qid]?.trim());
    }).length;
  });

  readonly contextUnderstandingPercent = computed<number>(() => {
    const qs = this.questions();
    if (qs.length === 0) return 40;
    const answered = this.answeredCount();
    return Math.min(100, Math.round(40 + (answered / qs.length) * 60));
  });

  readonly answeredEntries = computed<Array<{ id: string; answer: string }>>(() => {
    const qs = this.questions();
    const map = this.answersMap();
    return qs
      .map(q => {
        const qid = q.question_id || q.id;
        return {
          id: qid,
          answer: (map[qid] || '').trim(),
        };
      })
      .filter(item => item.answer.length > 0);
  });

  getQuestionId(q: ClarificationQuestion, index: number): string {
    return q.question_id || q.id || `q-${index + 1}`;
  }

  getSuggestedOptions(q: ClarificationQuestion): string[] {
    if (Array.isArray(q.options) && q.options.length > 0) {
      return q.options;
    }
    return [
      'Ưu tiên nắm vững kiến thức cốt lõi & thực hành',
      'Tập trung giải quyết bài toán thực tế & luyện đề',
      'Học theo nhịp độ ổn định vào buổi tối (20:00 - 22:00)',
    ];
  }

  getAnswer(q: ClarificationQuestion, index: number): string {
    const qid = this.getQuestionId(q, index);
    return this.answersMap()[qid] ?? '';
  }

  selectSuggestedChip(q: ClarificationQuestion, index: number, chip: string): void {
    const qid = this.getQuestionId(q, index);
    this.answersMap.update(prev => ({ ...prev, [qid]: chip }));
  }

  onAnswerChange(q: ClarificationQuestion, index: number, value: string): void {
    const qid = this.getQuestionId(q, index);
    this.answersMap.update(prev => ({ ...prev, [qid]: value }));
  }

  onGenerateQuestions(): void {
    this.generateQuestions.emit();
  }

  onLoadStandardPreviewQuestions(): void {
    this.roadmapService.clarificationQuestions.set(STANDARD_PEDAGOGICAL_QUESTIONS);
  }

  onSkipInterview(): void {
    this.skipInterview.emit();
  }

  onBack(): void {
    this.backToStep1.emit();
  }

  onSubmit(): void {
    const qs = this.questions();
    const map = this.answersMap();
    const payload: ClarificationAnswerItem[] = qs.map((q, idx) => {
      const qid = this.getQuestionId(q, idx);
      const fallback = this.getSuggestedOptions(q)[0] ?? 'Theo cấu hình tiêu chuẩn';
      return {
        question_id: qid,
        question_text: q.text || q.question,
        answer: (map[qid] || '').trim() || fallback,
      };
    });
    this.submitAnswers.emit(payload);
  }
}
