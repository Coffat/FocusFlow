import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  CreateRoadmapRequest,
  DraftKnowledgeAttachment,
  PriorKnowledgeLevel,
} from '../../../models/roadmap.model';

export interface BaselineLevelOption {
  value: PriorKnowledgeLevel;
  title: string;
  badge: string;
  description: string;
}

function getDefaultDeadlineIso(weeksAhead = 12): string {
  const now = new Date();
  const target = new Date(now.getTime() + weeksAhead * 7 * 24 * 60 * 60 * 1000);
  return target.toISOString().split('T')[0];
}

function getTodayIso(): string {
  return new Date().toISOString().split('T')[0];
}

@Component({
  selector: 'app-goal-setup-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './goal-setup-dialog.component.html',
  styleUrl: './goal-setup-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GoalSetupDialogComponent {
  readonly initialTitle = input<string>('');
  readonly initialLevel = input<PriorKnowledgeLevel>('BEGINNER');
  readonly initialWeeklyHours = input<number>(12);
  readonly isSubmitting = input<boolean>(false);

  readonly submitGoal = output<CreateRoadmapRequest>();
  readonly submitAttachments = output<DraftKnowledgeAttachment[]>();
  readonly canceled = output<void>();

  readonly maxAttachments = 3;
  readonly maxFileSizeBytes = 5 * 1024 * 1024; // 5 MB
  readonly allowedExtensions: readonly string[] = ['.pdf', '.md', '.txt'];

  readonly goalTitle = signal<string>('');
  readonly currentLevel = signal<PriorKnowledgeLevel>('BEGINNER');
  readonly weeklyHours = signal<number>(12);
  readonly targetDeadline = signal<string>(getDefaultDeadlineIso(12));
  readonly validationError = signal<string | null>(null);

  readonly attachments = signal<DraftKnowledgeAttachment[]>([]);
  readonly showUrlInput = signal<boolean>(false);
  readonly urlInputValue = signal<string>('');
  readonly attachmentError = signal<string | null>(null);
  readonly isAttachmentLimitReached = computed<boolean>(
    () => this.attachments().length >= this.maxAttachments
  );

  readonly quickSuggestions: readonly string[] = [
    'Chứng chỉ AWS Solutions Architect',
    'Luyện thi IELTS 7.5 Academic',
    'System Design & Distributed Systems',
    'Full-stack Rust & WebAssembly',
  ];

  readonly levelOptions: readonly BaselineLevelOption[] = [
    {
      value: 'BEGINNER',
      title: 'Mới bắt đầu',
      badge: 'BEGINNER',
      description: 'Chưa có nền tảng, đi bài bản từ các khái niệm cơ bản.',
    },
    {
      value: 'INTERMEDIATE',
      title: 'Đã có nền tảng',
      badge: 'INTERMEDIATE',
      description: 'Đã nắm lý thuyết cơ bản, tập trung thực hành và làm dự án.',
    },
    {
      value: 'ADVANCED',
      title: 'Nâng cao',
      badge: 'ADVANCED',
      description: 'Đi sâu tối ưu hóa kiến trúc và giải quyết bài toán phức tạp.',
    },
  ];

  readonly charCount = computed<number>(() => this.goalTitle().length);

  readonly dailyHoursEstimate = computed<string>(() => {
    const daily = this.weeklyHours() / 7;
    return daily.toFixed(1);
  });

  readonly remainingDays = computed<number>(() => {
    const deadlineStr = this.targetDeadline();
    if (!deadlineStr) return 84;
    const target = new Date(deadlineStr);
    if (Number.isNaN(target.getTime())) return 84;
    const now = new Date();
    const diffMs = target.getTime() - now.getTime();
    const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    return Math.max(7, days);
  });

  readonly remainingWeeks = computed<number>(() => {
    return Math.max(1, Math.round(this.remainingDays() / 7));
  });

  readonly totalEstimatedHours = computed<number>(() => {
    return this.remainingWeeks() * this.weeklyHours();
  });

  readonly estimatedPomodoros = computed<number>(() => {
    return Math.max(1, Math.round((this.totalEstimatedHours() * 60) / 30));
  });

  readonly estimatedMilestones = computed<number>(() => {
    return Math.max(3, Math.min(8, Math.round(this.remainingWeeks() / 2)));
  });

  constructor() {
    effect(() => {
      const title = this.initialTitle();
      const level = this.initialLevel();
      const hours = this.initialWeeklyHours();
      this.goalTitle.set(title);
      this.currentLevel.set(level);
      this.weeklyHours.set(hours);
      this.validationError.set(null);
    });
  }

  onTitleInput(value: string): void {
    this.goalTitle.set(value.slice(0, 250));
    if (value.trim()) {
      this.validationError.set(null);
    }
  }

  selectSuggestion(suggestion: string): void {
    this.goalTitle.set(suggestion);
    this.validationError.set(null);
  }

  selectLevel(level: PriorKnowledgeLevel): void {
    this.currentLevel.set(level);
  }

  onWeeklyHoursChange(value: number | string): void {
    const parsed = Number(value);
    if (!Number.isNaN(parsed)) {
      this.weeklyHours.set(Math.min(40, Math.max(3, parsed)));
    }
  }

  onDeadlineChange(value: string): void {
    this.targetDeadline.set(value);
  }

  toggleUrlInput(): void {
    this.showUrlInput.update(prev => !prev);
    this.attachmentError.set(null);
  }

  onUrlInputChange(val: string): void {
    this.urlInputValue.set(val);
    this.attachmentError.set(null);
  }

  addUrlAttachment(): void {
    if (this.attachments().length >= this.maxAttachments) {
      this.attachmentError.set(
        'Chỉ được đính kèm tối đa 3 nguồn (tệp + URL) để tránh tràn ngữ cảnh AI.'
      );
      return;
    }

    const trimmed = this.urlInputValue().trim();
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      this.attachmentError.set(
        'Vui lòng nhập đường dẫn URL hợp lệ (bắt đầu bằng http:// hoặc https://).'
      );
      return;
    }

    let parsedUrl: URL;
    try {
      parsedUrl = new URL(trimmed);
    } catch {
      this.attachmentError.set(
        'Vui lòng nhập đường dẫn URL hợp lệ (bắt đầu bằng http:// hoặc https://).'
      );
      return;
    }

    const isDuplicate = this.attachments().some(
      item => item.kind === 'URL' && item.url?.toLowerCase() === trimmed.toLowerCase()
    );
    if (isDuplicate) {
      this.attachmentError.set('Đường dẫn URL này đã có trong danh sách đính kèm.');
      return;
    }

    const displayTitle =
      parsedUrl.hostname + (parsedUrl.pathname && parsedUrl.pathname !== '/' ? parsedUrl.pathname : '') ||
      trimmed;

    const newItem: DraftKnowledgeAttachment = {
      id: `url-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      kind: 'URL',
      title: displayTitle,
      url: trimmed,
    };

    this.attachments.update(list => [...list, newItem]);
    this.urlInputValue.set('');
    this.showUrlInput.set(false);
    this.attachmentError.set(null);
  }

  onFilesSelected(event: Event): void {
    const inputEl = event.target as HTMLInputElement | null;
    if (!inputEl?.files || inputEl.files.length === 0) {
      return;
    }
    this.addFiles(inputEl.files);
    inputEl.value = '';
  }

  addFiles(files: FileList | File[]): void {
    const fileArray = Array.from(files);
    this.attachmentError.set(null);

    for (const file of fileArray) {
      if (this.attachments().length >= this.maxAttachments) {
        this.attachmentError.set(
          'Chỉ được đính kèm tối đa 3 nguồn (tệp + URL) để tránh tràn ngữ cảnh AI.'
        );
        break;
      }

      const lowerName = file.name.toLowerCase();
      const hasValidExt = this.allowedExtensions.some(ext => lowerName.endsWith(ext));
      if (!hasValidExt) {
        this.attachmentError.set('Chỉ hỗ trợ tệp định dạng .pdf, .md hoặc .txt.');
        continue;
      }

      if (file.size > this.maxFileSizeBytes) {
        this.attachmentError.set('Dung lượng tệp vượt quá giới hạn 5 MB cho phép.');
        continue;
      }

      const newItem: DraftKnowledgeAttachment = {
        id: `file-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        kind: 'FILE',
        title: file.name,
        file,
        sizeBytes: file.size,
      };
      this.attachments.update(list => [...list, newItem]);
    }
  }

  removeAttachment(id: string): void {
    this.attachments.update(list => list.filter(item => item.id !== id));
    this.attachmentError.set(null);
  }

  formatFileSize(bytes?: number): string {
    if (!bytes || bytes <= 0) return '0 KB';
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  onSubmit(): void {
    const trimmed = this.goalTitle().trim();
    if (!trimmed) {
      this.validationError.set('Vui lòng nhập mục tiêu học tập cốt lõi trước khi tiếp tục.');
      return;
    }

    this.validationError.set(null);
    const attachedSummary =
      this.attachments().length > 0
        ? ` • Tài liệu đính kèm (${this.attachments().length}/3): ${this.attachments()
            .map(a => a.title)
            .join(', ')}`
        : '';
    const description = `Cam kết ${this.weeklyHours()} giờ/tuần (~${this.dailyHoursEstimate()}h/ngày) • Tổng ước tính ${this.totalEstimatedHours()} giờ (${this.estimatedPomodoros()} phiên Pomodoro).${attachedSummary}`;

    const payload: CreateRoadmapRequest = {
      title: trimmed,
      description,
      goal_title: trimmed,
      goal_description: description,
      prior_knowledge_level: this.currentLevel(),
      start_date: getTodayIso(),
      target_date: this.targetDeadline() || getDefaultDeadlineIso(12),
    };

    this.submitAttachments.emit(this.attachments());
    this.submitGoal.emit(payload);
  }

  onCancel(): void {
    this.canceled.emit();
  }
}
