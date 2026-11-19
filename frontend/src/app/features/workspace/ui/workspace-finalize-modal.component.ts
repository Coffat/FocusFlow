import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  AlertTriangle,
  Sparkles,
  StickyNote,
  X,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
} from 'lucide-angular';
import { evaluateTakeawayCheck } from '../../../core/services/workspace-session.service';
import {
  FinalizeSessionRequest,
  StickyNoteItem,
  TaskResponse,
  TimeSufficiency,
} from '../models/workspace.model';

@Component({
  selector: 'ff-workspace-finalize-modal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        Sparkles,
        StickyNote,
        X,
      }),
    },
  ],
  host: {
    '(document:keydown.escape)': 'onEscape()',
  },
  template: `
    @if (isOpen()) {
      <div
        class="fixed inset-0 z-40 bg-black/45 backdrop-blur-[1px]"
        (click)="closeModal.emit()"
        aria-hidden="true"
      ></div>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="finalize-dialog-title"
        data-testid="finalize-session-dialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
      >
        <div
          class="pointer-events-auto w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-[4px] border border-[var(--border,#bfc9c0)] bg-[var(--card,#ffffff)] text-[var(--foreground,#1b1c1c)] shadow-2xl p-5 sm:p-6 space-y-5"
          (click)="$event.stopPropagation()"
        >
          <!-- Header -->
          <div class="flex items-start justify-between gap-3 border-b border-[var(--border,#bfc9c0)] pb-3">
            <div>
              <h2 id="finalize-dialog-title" class="text-lg font-semibold tracking-tight">
                {{ earlyStop() ? 'Xác nhận Kết thúc sớm phiên học' : 'Hoàn tất phiên học &amp; Ghi nhận' }}
              </h2>
              <div class="flex flex-wrap items-center gap-2 text-xs text-[var(--muted-foreground,#404942)] mt-0.5">
                <span>Thời gian thực tế: {{ elapsedMinutes() }} phút</span>
                @if (focusScore() !== null) {
                  <span>&bull;</span>
                  <span class="inline-flex items-center gap-1 text-[#005234] font-medium">
                    <lucide-icon name="sparkles" [size]="12" aria-hidden="true"></lucide-icon>
                    <span>Focus {{ focusScore() }}/100</span>
                  </span>
                }
              </div>
            </div>
            <button
              type="button"
              (click)="closeModal.emit()"
              aria-label="Đóng hộp thoại hoàn tất phiên học"
              class="inline-flex items-center justify-center w-8 h-8 rounded-full border border-transparent hover:border-[var(--border,#bfc9c0)] hover:bg-[var(--muted,#f5f3f3)] text-[var(--muted-foreground,#404942)] cursor-pointer"
            >
              <lucide-icon name="x" [size]="18" aria-hidden="true"></lucide-icon>
            </button>
          </div>

          <!-- Early stop confirmation -->
          @if (earlyStop()) {
            <div class="p-3 rounded-[4px] border border-amber-500/40 bg-amber-500/10 text-xs text-amber-900 dark:text-amber-200 space-y-2">
              <div class="font-semibold flex items-center gap-1.5">
                <lucide-icon name="alert-triangle" [size]="14" aria-hidden="true"></lucide-icon>
                <span>Bạn đang dừng sớm phiên học trước thời lượng dự kiến.</span>
              </div>
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  data-testid="confirm-early-stop-checkbox"
                  [checked]="earlyStopConfirmed()"
                  (change)="earlyStopConfirmed.set($any($event.target).checked)"
                  class="h-4 w-4 accent-[#246B4A]"
                />
                <span>Tôi xác nhận muốn kết thúc sớm và lưu lại tiến độ hiện tại.</span>
              </label>
            </div>
          }

          <!-- Error alert -->
          @if (errorMessage(); as errMsg) {
            <div
              role="alert"
              data-testid="finalize-error-alert"
              class="p-3 rounded-[4px] border border-[#ba1a1a]/40 bg-[#ba1a1a]/10 text-xs text-[#ba1a1a]"
            >
              {{ errMsg }}
            </div>
          }

          <!-- Completed Task Checkboxes -->
          @if (activeSessionTasks().length > 0) {
            <div class="space-y-2">
              <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground,#404942)]">
                Đánh dấu nhiệm vụ đã hoàn thành
              </span>
              <div class="space-y-1.5">
                @for (task of activeSessionTasks(); track task.id) {
                  <label class="flex items-center gap-2.5 p-2.5 rounded-[4px] border border-[var(--border,#bfc9c0)] bg-[var(--background,#fbf9f8)] cursor-pointer text-sm">
                    <input
                      type="checkbox"
                      [checked]="completedTaskIds().includes(task.id)"
                      (change)="toggleCompletedTask(task.id)"
                      class="h-4 w-4 accent-[#246B4A]"
                    />
                    <span class="flex-1 truncate">{{ task.title }}</span>
                  </label>
                }
              </div>
            </div>
          }

          <!-- Key Takeaway -->
          <div class="space-y-2">
            <label
              for="finalize-takeaway-input"
              class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground,#404942)]"
            >
              Key Takeaway (Tóm tắt điều bạn rút ra) *
            </label>

            @if (usableStickyNotes().length > 0) {
              <div class="space-y-1.5">
                <span class="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--muted-foreground,#404942)]">
                  <lucide-icon name="sticky-note" [size]="12" aria-hidden="true"></lucide-icon>
                  <span>Chèn từ giấy note ghim:</span>
                </span>
                <div class="flex flex-wrap gap-1.5">
                  @for (note of usableStickyNotes(); track note.id) {
                    <button
                      type="button"
                      (click)="appendStickyNote(note)"
                      class="px-2.5 py-1 rounded-full border border-[var(--border,#bfc9c0)] bg-[var(--muted,#f5f3f3)] hover:border-[#246B4A] text-[11px] text-[var(--foreground,#1b1c1c)] truncate max-w-[200px] cursor-pointer transition-colors"
                      [title]="note.content"
                    >
                      + {{ noteChipLabel(note) }}
                    </button>
                  }
                </div>
              </div>
            }

            <textarea
              id="finalize-takeaway-input"
              data-testid="finalize-takeaway-textarea"
              rows="3"
              [ngModel]="takeaway()"
              (ngModelChange)="takeaway.set($event)"
              placeholder="Ví dụ: Đã hiểu rõ cơ chế Outbox Pattern đảm bảo nhất quán sự kiện giữa PostgreSQL và Redis..."
              class="w-full rounded-[4px] border border-[var(--border,#bfc9c0)] bg-[var(--background,#fbf9f8)] p-3 text-sm text-[var(--foreground,#1b1c1c)] focus:outline-none focus:border-[#246B4A]"
            ></textarea>
            <div class="flex flex-wrap items-center justify-between gap-2 text-[11px]">
              <span
                [class]="
                  takeawayCheck().isValid
                    ? 'text-[#005234] font-medium'
                    : 'text-[var(--muted-foreground,#707972)]'
                "
              >
                {{ takeawayCheck().charCount }}/30 ký tự &bull; {{ takeawayCheck().distinctWordCount }}/6 từ phân biệt
              </span>
              @if (!takeawayCheck().hasAlpha && takeaway().length > 0) {
                <span class="text-[#ba1a1a]">Cần chứa từ ngữ có nghĩa.</span>
              } @else if (!takeawayCheck().hasNoRepeatedChars && takeaway().length > 0) {
                <span class="text-[#ba1a1a]">Tránh lặp lại cùng một ký tự liên tiếp.</span>
              }
            </div>
          </div>

          <!-- Self Confidence (1..5) -->
          <div class="space-y-1.5">
            <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground,#404942)]">
              Mức độ tự tin nắm bài (1–5)
            </span>
            <div class="flex items-center gap-2">
              @for (score of ratingScale; track score) {
                <button
                  type="button"
                  (click)="selfConfidence.set(score)"
                  [attr.aria-pressed]="selfConfidence() === score"
                  class="flex-1 h-9 rounded-[4px] text-xs font-semibold border transition-colors cursor-pointer"
                  [class]="
                    selfConfidence() === score
                      ? 'bg-[#111111] text-white border-[#111111]'
                      : 'bg-[var(--background,#fbf9f8)] text-[var(--foreground,#1b1c1c)] border-[var(--border,#bfc9c0)] hover:border-[#246B4A]'
                  "
                >
                  {{ score }}
                </button>
              }
            </div>
          </div>

          <!-- Daily Learning Check-in -->
          <div class="space-y-3 pt-3 border-t border-[var(--border,#bfc9c0)]">
            <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground,#404942)]">
              Daily Learning Check-in
            </span>

            <div class="space-y-1.5">
              <span class="block text-xs font-medium">Thời lượng phiên học vừa qua:</span>
              <div class="grid grid-cols-3 gap-2">
                @for (opt of timeSufficiencyOptions; track opt.value) {
                  <button
                    type="button"
                    (click)="checkinTimeSufficiency.set(opt.value)"
                    [attr.aria-pressed]="checkinTimeSufficiency() === opt.value"
                    class="py-2 px-2 rounded-[4px] text-xs font-medium border transition-colors cursor-pointer"
                    [class]="
                      checkinTimeSufficiency() === opt.value
                        ? 'bg-[#111111] text-white border-[#111111]'
                        : 'bg-[var(--background,#fbf9f8)] text-[var(--foreground,#1b1c1c)] border-[var(--border,#bfc9c0)] hover:border-[#246B4A]'
                    "
                  >
                    {{ opt.label }}
                  </button>
                }
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div class="space-y-1">
                <span class="block text-xs font-medium">Độ khó cảm nhận (1–5)</span>
                <div class="flex items-center gap-1.5">
                  @for (lvl of ratingScale; track lvl) {
                    <button
                      type="button"
                      (click)="checkinDifficulty.set(lvl)"
                      [attr.aria-pressed]="checkinDifficulty() === lvl"
                      class="flex-1 h-8 rounded-[4px] text-xs font-semibold border transition-colors cursor-pointer"
                      [class]="
                        checkinDifficulty() === lvl
                          ? 'bg-[#111111] text-white border-[#111111]'
                          : 'bg-[var(--background,#fbf9f8)] text-[var(--foreground,#1b1c1c)] border-[var(--border,#bfc9c0)] hover:border-[#246B4A]'
                      "
                    >
                      {{ lvl }}
                    </button>
                  }
                </div>
              </div>

              <div class="space-y-1">
                <span class="block text-xs font-medium">Mức độ tập trung (1–5)</span>
                <div class="flex items-center gap-1.5">
                  @for (lvl of ratingScale; track lvl) {
                    <button
                      type="button"
                      (click)="checkinFocusLevel.set(lvl)"
                      [attr.aria-pressed]="checkinFocusLevel() === lvl"
                      class="flex-1 h-8 rounded-[4px] text-xs font-semibold border transition-colors cursor-pointer"
                      [class]="
                        checkinFocusLevel() === lvl
                          ? 'bg-[#111111] text-white border-[#111111]'
                          : 'bg-[var(--background,#fbf9f8)] text-[var(--foreground,#1b1c1c)] border-[var(--border,#bfc9c0)] hover:border-[#246B4A]'
                      "
                    >
                      {{ lvl }}
                    </button>
                  }
                </div>
              </div>
            </div>
          </div>

          <!-- Footer Actions -->
          <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-[var(--border,#bfc9c0)]">
            <button
              type="button"
              (click)="closeModal.emit()"
              class="px-4 py-2 rounded-full border border-[var(--border,#bfc9c0)] bg-[var(--background,#fbf9f8)] hover:border-[#111111] text-xs font-medium cursor-pointer transition-colors"
            >
              Hủy
            </button>
            <button
              type="button"
              data-testid="submit-finalize-btn"
              [disabled]="
                isSubmitting() ||
                (earlyStop() && !earlyStopConfirmed()) ||
                !takeawayCheck().isValid
              "
              (click)="onSubmit()"
              class="px-5 py-2 rounded-full bg-[#111111] hover:bg-[#246B4A] disabled:opacity-45 disabled:hover:bg-[#111111] disabled:cursor-not-allowed text-white text-xs font-medium cursor-pointer transition-colors"
            >
              {{ isSubmitting() ? 'Đang lưu...' : 'Xác nhận hoàn tất' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class WorkspaceFinalizeModalComponent {
  readonly isOpen = input.required<boolean>();
  readonly earlyStop = input.required<boolean>();
  readonly activeSessionTasks = input.required<TaskResponse[]>();
  readonly stickyNotes = input<StickyNoteItem[]>([]);
  readonly elapsedMinutes = input<number>(0);
  readonly focusScore = input<number | null>(null);
  readonly isSubmitting = input<boolean>(false);
  readonly errorMessage = input<string | null>(null);

  readonly closeModal = output<void>();
  readonly submitFinalize = output<FinalizeSessionRequest>();

  readonly ratingScale = [1, 2, 3, 4, 5] as const;
  readonly timeSufficiencyOptions: ReadonlyArray<{ value: TimeSufficiency; label: string }> = [
    { value: 'TOO_SHORT', label: 'Quá ngắn' },
    { value: 'JUST_RIGHT', label: 'Vừa đủ' },
    { value: 'TOO_LONG', label: 'Quá dài' },
  ];

  readonly earlyStopConfirmed = signal<boolean>(false);
  readonly completedTaskIds = signal<string[]>([]);
  readonly takeaway = signal<string>('');
  readonly selfConfidence = signal<number>(4);
  readonly checkinTimeSufficiency = signal<TimeSufficiency>('JUST_RIGHT');
  readonly checkinDifficulty = signal<number>(3);
  readonly checkinFocusLevel = signal<number>(4);

  readonly takeawayCheck = computed(() => evaluateTakeawayCheck(this.takeaway()));
  readonly usableStickyNotes = computed(() =>
    this.stickyNotes().filter((note) => note.content.trim().length > 0)
  );

  constructor() {
    effect(() => {
      if (this.isOpen()) {
        const isEarly = this.earlyStop();
        const tasks = this.activeSessionTasks();
        this.earlyStopConfirmed.set(!isEarly);
        this.completedTaskIds.set(
          isEarly
            ? tasks.filter((t) => t.status === 'COMPLETED').map((t) => t.id)
            : tasks.map((t) => t.id)
        );
        this.takeaway.set('');
        this.selfConfidence.set(4);
        this.checkinTimeSufficiency.set('JUST_RIGHT');
        this.checkinDifficulty.set(3);
        this.checkinFocusLevel.set(4);
      }
    });
  }

  onEscape(): void {
    if (this.isOpen()) {
      this.closeModal.emit();
    }
  }

  toggleCompletedTask(taskId: string): void {
    this.completedTaskIds.update((ids) =>
      ids.includes(taskId) ? ids.filter((id) => id !== taskId) : [...ids, taskId]
    );
  }

  noteChipLabel(note: StickyNoteItem): string {
    const title = note.title.trim();
    if (title.length > 0) return title;
    const text = note.content.trim();
    return text.length > 24 ? `${text.slice(0, 24)}…` : text;
  }

  appendStickyNote(note: StickyNoteItem): void {
    const addition = note.content.trim();
    if (!addition) return;
    this.takeaway.update((current) => {
      const trimmed = current.trim();
      return trimmed.length > 0 ? `${trimmed}\n${addition}` : addition;
    });
  }

  onSubmit(): void {
    if (this.earlyStop() && !this.earlyStopConfirmed()) return;
    if (!this.takeawayCheck().isValid) return;

    this.submitFinalize.emit({
      early_stop: this.earlyStop(),
      completed_task_ids: this.completedTaskIds(),
      takeaway: this.takeaway().trim(),
      self_confidence: this.selfConfidence(),
      actual_minutes: Math.max(1, this.elapsedMinutes()),
      checkin_time_sufficiency: this.checkinTimeSufficiency(),
      checkin_perceived_difficulty: this.checkinDifficulty(),
      checkin_focus_level: this.checkinFocusLevel(),
    });
  }
}
