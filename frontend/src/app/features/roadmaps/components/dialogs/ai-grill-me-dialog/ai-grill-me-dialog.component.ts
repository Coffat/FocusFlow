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
  ClarificationOption,
  ClarificationQuestion,
  DraftKnowledgeAttachment,
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
      { id: 'q1-opt-1', label: 'Củng cố lý thuyết cốt lõi & thực hành từ đầu' },
      { id: 'q1-opt-2', label: 'Tập trung giải đề & dự án thực chiến chuyên sâu' },
      { id: 'q1-opt-3', label: 'Khắc phục điểm nghẽn kiến trúc & tối ưu hiệu năng' },
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
      { id: 'q2-opt-1', label: 'Evening Deep Work (20:00 - 22:00)' },
      { id: 'q2-opt-2', label: 'Morning Focus (06:00 - 08:00)' },
      { id: 'q2-opt-3', label: 'Weekend Intensive & Linh hoạt buổi tối' },
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
      { id: 'q3-opt-1', label: 'Dời lịch Domino Shift (+2 ngày, bảo toàn nhịp độ)' },
      { id: 'q3-opt-2', label: 'Phân bổ bù vào các khung giờ trống cuối tuần' },
      { id: 'q3-opt-3', label: 'Đưa vào Hàng chờ Backlog để tự sắp xếp' },
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
  readonly readyToPlan = output<void>();

  readonly answersMap = signal<Record<string, string>>({});
  readonly selectedOptionIdsMap = signal<Record<string, string[]>>({});
  readonly freeTextMap = signal<Record<string, string>>({});
  readonly expandedCustomInputs = signal<Record<string, boolean>>({});

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

  readonly attachedSources = computed<DraftKnowledgeAttachment[]>(() => {
    return typeof this.roadmapService.draftAttachments === 'function'
      ? this.roadmapService.draftAttachments()
      : [];
  });

  readonly answeredCount = computed<number>(() => {
    const qs = this.questions();
    const selected = this.selectedOptionIdsMap();
    const freeText = this.freeTextMap();
    return qs.filter(q => {
      const qid = q.question_id || q.id;
      return Boolean(selected[qid]?.length || freeText[qid]?.trim());
    }).length;
  });

  readonly answerProgressPercent = computed<number>(() => {
    const qs = this.questions();
    if (qs.length === 0) {
      return ['READY_TO_PLAN', 'SKIPPED'].includes(
        this.roadmapService.clarificationStatus()
      )
        ? 100
        : 0;
    }
    const answered = this.answeredCount();
    return Math.min(100, Math.round((answered / qs.length) * 100));
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

  getSuggestedOptions(q: ClarificationQuestion): ClarificationOption[] {
    return Array.isArray(q.options) ? q.options : [];
  }

  getAnswer(q: ClarificationQuestion, index: number): string {
    const qid = this.getQuestionId(q, index);
    return this.freeTextMap()[qid] ?? '';
  }

  isMultipleChoice(q: ClarificationQuestion): boolean {
    return q.question_type === 'multiple_choice';
  }

  isTextOnly(q: ClarificationQuestion): boolean {
    return q.question_type === 'text' && (!q.options || q.options.length === 0);
  }

  isChipSelected(q: ClarificationQuestion, index: number, chip: ClarificationOption): boolean {
    const qid = this.getQuestionId(q, index);
    return (this.selectedOptionIdsMap()[qid] ?? []).includes(chip.id);
  }

  selectSuggestedChip(q: ClarificationQuestion, index: number, chip: ClarificationOption): void {
    const qid = this.getQuestionId(q, index);
    const current = this.selectedOptionIdsMap()[qid] ?? [];
    let next: string[];
    if (this.isMultipleChoice(q)) {
      next = current.includes(chip.id)
        ? current.filter(id => id !== chip.id)
        : [...current, chip.id];
    } else {
      next = [chip.id];
    }
    this.selectedOptionIdsMap.update(prev => ({ ...prev, [qid]: next }));
    const labels = this.getSuggestedOptions(q)
      .filter(option => next.includes(option.id))
      .map(option => option.label);
    this.answersMap.update(prev => ({ ...prev, [qid]: labels.join(', ') }));

    if (chip.label.toLowerCase().includes('khác')) {
      this.expandedCustomInputs.update(prev => ({ ...prev, [qid]: true }));
    }
  }

  isCustomInputOpen(q: ClarificationQuestion, index: number): boolean {
    if (this.isTextOnly(q)) return true;
    const qid = this.getQuestionId(q, index);
    if (this.expandedCustomInputs()[qid]) return true;
    const selectedIds = this.selectedOptionIdsMap()[qid] ?? [];
    return this.getSuggestedOptions(q).some(
      option => selectedIds.includes(option.id) && option.label.toLowerCase().includes('khác')
    );
  }

  toggleCustomInput(q: ClarificationQuestion, index: number): void {
    const qid = this.getQuestionId(q, index);
    this.expandedCustomInputs.update(prev => ({ ...prev, [qid]: !prev[qid] }));
  }

  onAnswerChange(q: ClarificationQuestion, index: number, value: string): void {
    const qid = this.getQuestionId(q, index);
    this.freeTextMap.update(prev => ({ ...prev, [qid]: value }));
    if (this.isTextOnly(q)) {
      this.answersMap.update(prev => ({ ...prev, [qid]: value }));
    }
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

  onReadyToPlan(): void {
    this.readyToPlan.emit();
  }

  onSubmit(): void {
    const qs = this.questions();
    const selected = this.selectedOptionIdsMap();
    const freeText = this.freeTextMap();
    const payload: ClarificationAnswerItem[] = qs.map((q, idx) => {
      const qid = this.getQuestionId(q, idx);
      return {
        question_id: qid,
        answer: '',
        selected_option_ids: selected[qid] ?? [],
        free_text: (freeText[qid] || '').trim() || null,
      };
    }).filter(item => Boolean(item.selected_option_ids?.length || item.free_text));
    this.submitAnswers.emit(payload);
  }
}
