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
import { CreateRoadmapRequest, PriorKnowledgeLevel } from '../../../models/roadmap.model';

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
  readonly cancel = output<void>();

  readonly goalTitle = signal<string>('');
  readonly currentLevel = signal<PriorKnowledgeLevel>('BEGINNER');
  readonly weeklyHours = signal<number>(12);
  readonly targetDeadline = signal<string>(getDefaultDeadlineIso(12));
  readonly validationError = signal<string | null>(null);

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
      description: 'Chưa có kiến thức nền, cần đi từ khái niệm cơ bản và lộ trình nhập môn bài bản.',
    },
    {
      value: 'INTERMEDIATE',
      title: 'Đã có nền tảng',
      badge: 'INTERMEDIATE',
      description: 'Đã nắm lý thuyết cơ bản, muốn đi sâu thực hành, giải đề và xây dựng dự án.',
    },
    {
      value: 'ADVANCED',
      title: 'Nâng cao / Chuyên sâu',
      badge: 'ADVANCED',
      description: 'Tối ưu hóa kiến trúc, giải quyết các bài toán hệ thống phức tạp chuyên sâu.',
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

  onSubmit(): void {
    const trimmed = this.goalTitle().trim();
    if (!trimmed) {
      this.validationError.set('Vui lòng nhập mục tiêu học tập cốt lõi trước khi tiếp tục.');
      return;
    }

    this.validationError.set(null);
    const description = `Cam kết ${this.weeklyHours()} giờ/tuần (~${this.dailyHoursEstimate()}h/ngày) • Tổng ước tính ${this.totalEstimatedHours()} giờ (${this.estimatedPomodoros()} phiên Pomodoro).`;

    const payload: CreateRoadmapRequest = {
      title: trimmed,
      description,
      goal_title: trimmed,
      goal_description: description,
      prior_knowledge_level: this.currentLevel(),
      start_date: getTodayIso(),
      target_date: this.targetDeadline() || getDefaultDeadlineIso(12),
    };

    this.submitGoal.emit(payload);
  }

  onCancel(): void {
    this.cancel.emit();
  }
}
