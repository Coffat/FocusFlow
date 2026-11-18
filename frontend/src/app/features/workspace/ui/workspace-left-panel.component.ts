import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  AlertTriangle,
  BookOpen,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  EyeOff,
  Focus,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
  Maximize2,
  Minimize2,
  Palette,
  PanelLeftClose,
  RotateCw,
  Shield,
  StickyNote,
  Volume2,
  VolumeX,
} from 'lucide-angular';
import { evaluateTakeawayCheck } from '../../../core/services/workspace-session.service';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import {
  StudySessionResponse,
  TaskFilterMode,
  TaskResponse,
  TodayProgressSummary,
  WorkspaceToolPopover,
} from '../models/workspace.model';

interface TaskResourceLink {
  label: string;
  url: string | null;
}

const TARGET_POMODOROS_PER_DAY = 4;

@Component({
  selector: 'ff-workspace-left-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LucideAngularModule, ButtonDirective, BadgeDirective],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        BookOpen,
        Check,
        CheckCircle2,
        Clock,
        ExternalLink,
        EyeOff,
        Focus,
        Maximize2,
        Minimize2,
        Palette,
        PanelLeftClose,
        RotateCw,
        Shield,
        StickyNote,
        Volume2,
        VolumeX,
      }),
    },
  ],
  template: `
    <aside
      aria-label="Bảng tiến độ và nhiệm vụ hôm nay"
      class="flex h-full flex-col gap-3 font-sans"
    >
      <!-- CARD 1: Phiên học hôm nay -->
      <section
        aria-label="Phiên học hôm nay"
        class="rounded-xl p-3.5 transition-colors"
        style="background: var(--ws-surface-panel, var(--surface-container-lowest)); border: 1px solid var(--ws-border, var(--outline-variant)); color: var(--ws-text-primary, var(--on-surface)); backdrop-filter: var(--ws-panel-blur, blur(16px));"
      >
        <header class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h2
              class="m-0 font-serif text-base font-medium tracking-[-0.015em]"
              style="color: var(--ws-text-primary, var(--on-surface));"
            >
              Phiên học hôm nay
            </h2>
            @if (localDate()) {
              <div
                class="mt-0.5 text-[11px] font-medium uppercase tracking-[0.06em]"
                style="color: var(--ws-text-secondary, var(--on-surface-variant));"
              >
                {{ localDate() }}
              </div>
            }
          </div>

          <div class="flex shrink-0 items-center gap-0.5">
            <button
              type="button"
              appButton
              variant="ghost"
              size="icon"
              class="h-7 w-7 rounded-md opacity-80 hover:opacity-100"
              aria-label="Làm mới dữ liệu"
              title="Làm mới"
              [disabled]="isLoading()"
              (click)="refreshWorkspace.emit()"
            >
              <lucide-icon
                name="rotate-cw"
                [size]="14"
                [class.animate-spin]="isLoading()"
                aria-hidden="true"
              ></lucide-icon>
            </button>

            <button
              type="button"
              appButton
              variant="ghost"
              size="icon"
              class="h-7 w-7 rounded-md"
              [class.bg-[var(--ws-accent,var(--primary))]/15]="focusMode()"
              [style.color]="focusMode() ? 'var(--ws-accent, var(--primary))' : 'inherit'"
              aria-label="Chế độ tập trung"
              [attr.aria-pressed]="focusMode()"
              [title]="focusMode() ? 'Tắt Focus Mode' : 'Bật Focus Mode'"
              (click)="toggleFocusMode.emit()"
            >
              <lucide-icon
                [name]="focusMode() ? 'eye-off' : 'focus'"
                [size]="14"
                aria-hidden="true"
              ></lucide-icon>
            </button>

            <button
              type="button"
              appButton
              variant="ghost"
              size="icon"
              class="h-7 w-7 rounded-md opacity-80 hover:opacity-100"
              aria-label="Toàn màn hình"
              [attr.aria-pressed]="isFullscreen()"
              [title]="isFullscreen() ? 'Thoát toàn màn hình' : 'Toàn màn hình'"
              (click)="toggleFullscreen.emit()"
            >
              <lucide-icon
                [name]="isFullscreen() ? 'minimize-2' : 'maximize-2'"
                [size]="14"
                aria-hidden="true"
              ></lucide-icon>
            </button>

            <button
              type="button"
              appButton
              variant="ghost"
              size="icon"
              class="h-7 w-7 rounded-md opacity-80 hover:opacity-100"
              aria-label="Thu gọn bảng điều khiển"
              title="Thu gọn"
              (click)="collapsePanel.emit()"
            >
              <lucide-icon name="panel-left-close" [size]="14" aria-hidden="true"></lucide-icon>
            </button>
          </div>
        </header>

        <div class="mt-3 space-y-2.5">
          <!-- Active goal / focus task title -->
          <div class="flex items-baseline justify-between gap-2">
            <p
              class="m-0 truncate text-xs font-medium"
              [title]="activeGoalTitle()"
              style="color: var(--ws-text-primary, var(--on-surface));"
            >
              {{ activeGoalTitle() }}
            </p>
            <span
              class="shrink-0 font-mono text-xs font-semibold tabular-nums"
              style="color: var(--ws-accent, #246B4A);"
            >
              {{ clampedPercentage() }}%
            </span>
          </div>

          <!-- Crisp Forest Green mechanical progress bar -->
          <div
            role="progressbar"
            aria-label="Tỷ lệ hoàn thành nhiệm vụ hôm nay"
            [attr.aria-valuenow]="clampedPercentage()"
            aria-valuemin="0"
            aria-valuemax="100"
            class="h-2 w-full overflow-hidden rounded-full"
            style="background: var(--ws-border, var(--outline-variant));"
          >
            <div
              class="h-full rounded-full transition-[width] duration-300"
              [style.width.%]="clampedPercentage()"
              style="background: var(--ws-accent, #246B4A);"
            ></div>
          </div>

          <!-- Sessions & Minutes targets -->
          <div
            class="flex items-center justify-between gap-2 text-[11px] font-mono tabular-nums"
            style="color: var(--ws-text-secondary, var(--on-surface-variant));"
          >
            <span>{{ completedPomodorosToday() }} / {{ targetPomodoros }} phiên</span>
            <span>{{ progress().totalStudiedMinutes }} phút / {{ progress().totalPlannedMinutes }} phút</span>
          </div>
        </div>
      </section>

      <!-- CARD 2: Danh sách việc cần làm -->
      <section
        aria-label="Danh sách việc cần làm"
        class="flex min-h-0 flex-1 flex-col gap-2.5 rounded-xl p-3.5 transition-colors"
        style="background: var(--ws-surface-panel, var(--surface-container-lowest)); border: 1px solid var(--ws-border, var(--outline-variant)); color: var(--ws-text-primary, var(--on-surface)); backdrop-filter: var(--ws-panel-blur, blur(16px));"
      >
        <div class="flex items-center justify-between gap-2">
          <h3
            class="m-0 font-serif text-sm font-medium tracking-[-0.01em]"
            style="color: var(--ws-text-primary, var(--on-surface));"
          >
            Danh sách việc cần làm
          </h3>
          <span
            class="font-mono text-[11px] tabular-nums"
            style="color: var(--ws-text-secondary, var(--on-surface-variant));"
          >
            {{ progress().completedCount }}/{{ progress().totalCount }}
          </span>
        </div>

        <!-- Takeaway Debt Card -->
        @if (pendingTakeawaySession(); as debt) {
          <div
            aria-labelledby="left-panel-debt-heading"
            data-testid="pending-takeaway-card"
            class="space-y-2.5 rounded-lg border border-amber-500/40 bg-amber-50/75 p-3 dark:bg-amber-950/25"
          >
            <div class="flex items-start gap-2">
              <div class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded border border-amber-500/40 bg-amber-500/15 text-amber-800 dark:text-amber-300">
                <lucide-icon name="alert-triangle" [size]="14" aria-hidden="true"></lucide-icon>
              </div>
              <div class="min-w-0 space-y-0.5">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="text-[10px] font-semibold uppercase tracking-[0.06em] text-amber-800 dark:text-amber-300">
                    Nợ Key Takeaway
                  </span>
                  <span appBadge variant="outline" class="rounded-[2px] border-amber-500/50 px-1.5 py-0 text-[10px] text-amber-800 dark:text-amber-300">
                    FR-SESSION-001
                  </span>
                </div>
                <h4 id="left-panel-debt-heading" class="m-0 font-serif text-sm font-medium leading-snug text-[var(--on-surface)]">
                  Hoàn tất tóm tắt phiên trước
                </h4>
                <p class="m-0 text-[11px] leading-relaxed text-[var(--on-surface-variant)]">
                  Phiên ({{ debt.session_mode }} &bull; {{ debt.actual_minutes }}/{{ debt.planned_minutes }} phút) cần tóm tắt cốt lõi trước khi mở phiên mới.
                </p>
              </div>
            </div>

            <div class="space-y-2 rounded-md border border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] p-2.5">
              <div class="space-y-1">
                <label for="debt-takeaway-input" class="block text-[10px] font-medium uppercase tracking-[0.05em] text-[var(--on-surface-variant)]">
                  Key Takeaway bắt buộc *
                </label>
                <textarea
                  id="debt-takeaway-input"
                  data-testid="debt-takeaway-textarea"
                  rows="3"
                  [value]="debtTakeaway()"
                  (input)="onDebtTakeawayInput($event)"
                  placeholder="Ví dụ: Em đã nắm được cách tách interface Port ở Application layer và Adapter ở Infrastructure layer..."
                  class="w-full rounded border border-[var(--outline-variant)] bg-[var(--surface)] p-2 text-xs leading-relaxed text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/60 focus:border-[var(--primary)] focus:outline-none"
                ></textarea>
                <div class="flex flex-wrap items-center justify-between gap-1 text-[10px]">
                  <span
                    [class.text-[#246B4A]]="debtTakeawayCheck().isValid"
                    [class.dark:text-[var(--primary)]]="debtTakeawayCheck().isValid"
                    [class.text-[var(--on-surface-variant)]]="!debtTakeawayCheck().isValid"
                  >
                    {{ debtTakeawayCheck().charCount }}/30 ký tự &bull; {{ debtTakeawayCheck().distinctWordCount }}/6 từ riêng biệt
                  </span>
                  @if (!debtTakeawayCheck().hasNoRepeatedChars) {
                    <span class="font-medium text-[var(--error)]">Tránh lặp ký tự quá 5 lần.</span>
                  }
                </div>
              </div>

              <div class="space-y-1">
                <span class="block text-[10px] font-medium uppercase tracking-[0.05em] text-[var(--on-surface-variant)]">
                  Mức độ tự tin (1–5)
                </span>
                <div class="flex items-center gap-1.5">
                  @for (score of confidenceScores; track score) {
                    <button
                      type="button"
                      (click)="debtConfidence.set(score)"
                      [attr.aria-pressed]="debtConfidence() === score"
                      [attr.aria-label]="'Mức độ tự tin ' + score + ' trên 5'"
                      class="h-7 flex-1 rounded-full border text-xs font-semibold transition-colors cursor-pointer"
                      [class]="debtConfidence() === score
                        ? 'border-[var(--primary)] bg-[var(--primary)] text-[var(--on-primary)]'
                        : 'border-[var(--outline-variant)] bg-[var(--surface)] text-[var(--on-surface)] hover:bg-[var(--surface-container-low)]'"
                    >
                      {{ score }}
                    </button>
                  }
                </div>
              </div>

              <button
                type="button"
                appButton
                variant="default"
                size="sm"
                data-testid="resolve-takeaway-btn"
                class="w-full rounded"
                [disabled]="isSubmitting() || !debtTakeawayCheck().isValid"
                (click)="submitDebt(debt.id)"
              >
                {{ isSubmitting() ? 'Đang lưu...' : 'Xác nhận Takeaway & Mở khóa' }}
              </button>
            </div>
          </div>
        }

        @if (tasks().length === 0) {
          <div
            data-testid="workspace-empty-state"
            class="rounded-lg border border-dashed border-[var(--ws-border,var(--outline-variant))] px-3.5 py-6 text-center"
          >
            <div class="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-md border border-[var(--ws-border,var(--outline-variant))] opacity-80">
              <lucide-icon name="clock" [size]="16" aria-hidden="true"></lucide-icon>
            </div>
            <h4 class="m-0 font-serif text-sm font-medium">
              Chưa có nhiệm vụ nào cho hôm nay
            </h4>
            <p
              class="mt-1 text-xs leading-relaxed"
              style="color: var(--ws-text-secondary, var(--on-surface-variant));"
            >
              Hàng đợi hôm nay đang trống. Hãy chọn việc từ danh sách hoặc lập lịch học mới.
            </p>
            <div class="mt-3 flex flex-wrap items-center justify-center gap-2">
              <a routerLink="/tasks" appButton variant="default" size="sm" class="rounded">
                Mở Công việc
              </a>
              <a routerLink="/planning" appButton variant="outline" size="sm" class="rounded">
                Lập kế hoạch
              </a>
            </div>
          </div>
        } @else {
          <!-- Filter Pills -->
          <div class="flex flex-wrap items-center gap-1.5" role="group" aria-label="Lọc nhiệm vụ">
            <button
              type="button"
              (click)="filterMode.set('all')"
              [attr.aria-pressed]="filterMode() === 'all'"
              class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors cursor-pointer"
              [class]="filterMode() === 'all'
                ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))] text-[var(--on-primary)]'
                : 'border-[var(--ws-border,var(--outline-variant))] opacity-80 hover:opacity-100'"
            >
              <span>Tất cả</span>
              <span class="font-mono opacity-80">{{ tasks().length }}</span>
            </button>

            <button
              type="button"
              (click)="filterMode.set('todo')"
              [attr.aria-pressed]="filterMode() === 'todo'"
              class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors cursor-pointer"
              [class]="filterMode() === 'todo'
                ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))] text-[var(--on-primary)]'
                : 'border-[var(--ws-border,var(--outline-variant))] opacity-80 hover:opacity-100'"
            >
              <span>Cần làm</span>
              <span class="font-mono opacity-80">{{ todoCount() }}</span>
            </button>

            <button
              type="button"
              (click)="filterMode.set('overdue')"
              [attr.aria-pressed]="filterMode() === 'overdue'"
              class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors cursor-pointer"
              [class]="filterMode() === 'overdue'
                ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))] text-[var(--on-primary)]'
                : 'border-[var(--ws-border,var(--outline-variant))] opacity-80 hover:opacity-100'"
            >
              <span>Quá hạn</span>
              <span class="font-mono opacity-80">{{ overdueCount() }}</span>
            </button>
          </div>

          <!-- Scrollable Task List -->
          <div class="max-h-[26vh] overflow-y-auto pr-0.5 space-y-3">
            @if (activeSession()) {
              <!-- Group 1: Active session tasks -->
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <span
                    class="text-[10px] font-semibold uppercase tracking-[0.06em]"
                    style="color: var(--ws-accent, var(--primary));"
                  >
                    Đang học trong phiên
                  </span>
                  <span
                    class="font-mono text-[11px]"
                    style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                  >
                    {{ filteredActiveTasks().length }}
                  </span>
                </div>

                @if (filteredActiveTasks().length === 0) {
                  <p
                    class="m-0 rounded-md border border-dashed border-[var(--ws-border,var(--outline-variant))] px-3 py-2 text-xs"
                    style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                  >
                    Không có nhiệm vụ nào trong phiên khớp bộ lọc hiện tại.
                  </p>
                } @else {
                  <div class="space-y-1.5">
                    @for (task of filteredActiveTasks(); track task.id) {
                      @let isFocused = activeFocusTaskId() === task.id;
                      <div
                        class="rounded-lg border p-2.5 space-y-1.5 transition-colors cursor-pointer"
                        [class]="isFocused
                          ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))]/10'
                          : 'border-[var(--ws-accent,var(--primary))]/35 hover:border-[var(--ws-accent,var(--primary))]/70'"
                        (click)="selectFocusTask.emit(task.id)"
                        (keydown.enter)="selectFocusTask.emit(task.id)"
                        tabindex="0"
                        role="button"
                        [attr.aria-pressed]="isFocused"
                        [attr.aria-label]="'Chọn làm mục tiêu chính: ' + task.title"
                      >
                        <div class="flex items-start gap-2">
                          <button
                            type="button"
                            [disabled]="togglingTaskId() === task.id || task.status === 'CANCELLED'"
                            (click)="onToggleCompleteClick($event, task)"
                            [attr.aria-label]="
                              task.status === 'COMPLETED'
                                ? 'Mở lại nhiệm vụ: ' + task.title
                                : 'Đánh dấu hoàn thành: ' + task.title
                            "
                            [attr.aria-pressed]="task.status === 'COMPLETED'"
                            class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-[3px] border transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
                            [class]="task.status === 'COMPLETED'
                              ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))] text-[var(--on-primary)]'
                              : 'border-[var(--outline)] bg-transparent text-transparent hover:border-[var(--ws-accent,var(--primary))]'"
                          >
                            <lucide-icon name="check" [size]="11" aria-hidden="true"></lucide-icon>
                          </button>

                          <div class="min-w-0 flex-1 space-y-0.5">
                            <div class="flex flex-wrap items-center gap-1.5">
                              <span
                                class="text-xs font-medium leading-snug"
                                [class.line-through]="task.status === 'COMPLETED'"
                                [class.opacity-60]="task.status === 'COMPLETED'"
                              >
                                {{ task.title }}
                              </span>
                              <span
                                appBadge
                                [variant]="task.status === 'COMPLETED' ? 'success' : 'secondary'"
                                class="rounded-[2px] px-1.5 py-0 text-[10px]"
                              >
                                {{ statusLabel(task.status) }}
                              </span>
                              @if (task.is_overdue && task.status !== 'COMPLETED') {
                                <span appBadge variant="destructive" class="rounded-[2px] px-1.5 py-0 text-[10px]">
                                  Quá hạn
                                </span>
                              }
                            </div>

                            <div
                              class="flex flex-wrap items-center gap-1.5 text-[11px]"
                              style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                            >
                              @if (task.roadmap_title) {
                                <span class="max-w-[140px] truncate">{{ task.roadmap_title }}</span>
                                <span>&bull;</span>
                              }
                              <span class="font-mono">{{ task.estimated_minutes }} phút</span>
                            </div>
                          </div>
                        </div>

                        @if (getTaskResources(task).length > 0) {
                          <div class="flex flex-wrap gap-1.5 pl-6">
                            @for (res of getTaskResources(task); track $index) {
                              @if (res.url) {
                                <a
                                  [href]="res.url"
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  (click)="$event.stopPropagation()"
                                  class="inline-flex items-center gap-1 rounded border border-[var(--ws-border,var(--outline-variant))] px-2 py-0.5 text-[11px] no-underline hover:opacity-85"
                                  style="color: var(--ws-accent, var(--primary));"
                                >
                                  <lucide-icon name="book-open" [size]="11" aria-hidden="true"></lucide-icon>
                                  <span class="max-w-[150px] truncate">{{ res.label }}</span>
                                  <lucide-icon name="external-link" [size]="10" aria-hidden="true"></lucide-icon>
                                </a>
                              } @else {
                                <span
                                  class="inline-flex items-center gap-1 rounded border border-[var(--ws-border,var(--outline-variant))] px-2 py-0.5 text-[11px]"
                                  style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                                >
                                  <lucide-icon name="book-open" [size]="11" aria-hidden="true"></lucide-icon>
                                  <span class="max-w-[150px] truncate">{{ res.label }}</span>
                                </span>
                              }
                            }
                          </div>
                        }
                      </div>
                    }
                  </div>
                }
              </div>

              <!-- Group 2: Remaining queue -->
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <span
                    class="text-[10px] font-semibold uppercase tracking-[0.06em]"
                    style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                  >
                    Hàng đợi còn lại
                  </span>
                  <span
                    class="font-mono text-[11px]"
                    style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                  >
                    {{ filteredRemainingTasks().length }}
                  </span>
                </div>

                @if (filteredRemainingTasks().length === 0) {
                  <p
                    class="m-0 rounded-md border border-dashed border-[var(--ws-border,var(--outline-variant))] px-3 py-2 text-xs"
                    style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                  >
                    Không còn nhiệm vụ nào khác trong hàng đợi phù hợp bộ lọc.
                  </p>
                } @else {
                  <div class="space-y-1.5">
                    @for (task of filteredRemainingTasks(); track task.id) {
                      <div
                        class="flex items-start gap-2 rounded-lg border border-[var(--ws-border,var(--outline-variant))] p-2.5 opacity-85 transition-opacity hover:opacity-100 cursor-pointer"
                        (click)="attemptSwitchOutsideTask.emit(task)"
                        (keydown.enter)="attemptSwitchOutsideTask.emit(task)"
                        tabindex="0"
                        role="button"
                        [attr.aria-label]="'Nhiệm vụ ngoài phiên: ' + task.title"
                      >
                        <button
                          type="button"
                          [disabled]="togglingTaskId() === task.id || task.status === 'CANCELLED'"
                          (click)="onToggleCompleteClick($event, task)"
                          [attr.aria-label]="
                            task.status === 'COMPLETED'
                              ? 'Mở lại nhiệm vụ: ' + task.title
                              : 'Đánh dấu hoàn thành: ' + task.title
                          "
                          [attr.aria-pressed]="task.status === 'COMPLETED'"
                          class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-[3px] border transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
                          [class]="task.status === 'COMPLETED'
                            ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))] text-[var(--on-primary)]'
                            : 'border-[var(--outline)] bg-transparent text-transparent hover:border-[var(--ws-accent,var(--primary))]'"
                        >
                          <lucide-icon name="check" [size]="11" aria-hidden="true"></lucide-icon>
                        </button>

                        <div class="min-w-0 flex-1 space-y-0.5">
                          <div class="flex flex-wrap items-center gap-1.5">
                            <span
                              class="text-xs font-medium leading-snug"
                              [class.line-through]="task.status === 'COMPLETED'"
                              [class.opacity-60]="task.status === 'COMPLETED'"
                            >
                              {{ task.title }}
                            </span>
                            @if (task.is_overdue && task.status !== 'COMPLETED') {
                              <span appBadge variant="destructive" class="rounded-[2px] px-1.5 py-0 text-[10px]">
                                Quá hạn
                              </span>
                            }
                            @if (task.is_blocked) {
                              <span appBadge variant="outline" class="rounded-[2px] border-amber-500/60 px-1.5 py-0 text-[10px] text-amber-700 dark:text-amber-300">
                                Bị chặn
                              </span>
                            }
                          </div>

                          <div
                            class="flex flex-wrap items-center gap-1.5 text-[11px]"
                            style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                          >
                            @if (task.roadmap_title) {
                              <span class="max-w-[140px] truncate">{{ task.roadmap_title }}</span>
                              <span>&bull;</span>
                            }
                            <span class="font-mono">{{ task.estimated_minutes }} phút</span>
                          </div>
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            } @else {
              <!-- No Active Session Mode: Task Selection Checkboxes -->
              @if (filteredTasks().length === 0) {
                <p
                  class="m-0 rounded-md border border-dashed border-[var(--ws-border,var(--outline-variant))] px-3 py-4 text-center text-xs"
                  style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                >
                  Không có nhiệm vụ nào phù hợp với bộ lọc đã chọn.
                </p>
              } @else {
                <div class="space-y-1.5">
                  @for (task of filteredTasks(); track task.id) {
                    @let disabledReason = getSelectDisabledReason(task);
                    @let selected = isTaskSelected(task.id);
                    <div
                      class="flex items-start gap-2 rounded-lg border p-2.5 transition-colors"
                      [class]="selected
                        ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))]/10'
                        : disabledReason
                          ? 'border-[var(--ws-border,var(--outline-variant))] opacity-70'
                          : 'border-[var(--ws-border,var(--outline-variant))] hover:border-[var(--ws-accent,var(--primary))]/50'"
                    >
                      <label
                        class="flex min-w-0 flex-1 items-start gap-2"
                        [class.cursor-pointer]="!disabledReason"
                        [class.cursor-not-allowed]="!!disabledReason"
                      >
                        <input
                          type="checkbox"
                          [checked]="selected"
                          [disabled]="!!disabledReason"
                          (change)="toggleSelectTask.emit(task.id)"
                          [attr.aria-label]="'Chọn nhiệm vụ vào phiên học: ' + task.title"
                          class="mt-0.5 h-4 w-4 shrink-0 rounded-[2px] border border-[var(--outline)] accent-[var(--ws-accent,var(--primary))] disabled:cursor-not-allowed"
                        />
                        <div class="min-w-0 flex-1 space-y-0.5">
                          <div class="flex flex-wrap items-center gap-1.5">
                            <span
                              class="text-xs font-medium leading-snug"
                              [class.line-through]="task.status === 'COMPLETED'"
                              [class.opacity-60]="task.status === 'COMPLETED'"
                            >
                              {{ task.title }}
                            </span>
                            @if (task.is_overdue && task.status !== 'COMPLETED') {
                              <span appBadge variant="destructive" class="rounded-[2px] px-1.5 py-0 text-[10px]">
                                Quá hạn
                              </span>
                            }
                            @if (disabledReason) {
                              <span
                                appBadge
                                variant="outline"
                                class="rounded-[2px] border-[var(--ws-border,var(--outline-variant))] px-1.5 py-0 text-[10px]"
                              >
                                {{ disabledReason }}
                              </span>
                            }
                          </div>

                          <div
                            class="flex flex-wrap items-center gap-1.5 text-[11px]"
                            style="color: var(--ws-text-secondary, var(--on-surface-variant));"
                          >
                            @if (task.roadmap_title) {
                              <span class="max-w-[140px] truncate">{{ task.roadmap_title }}</span>
                              <span>&bull;</span>
                            }
                            <span class="font-mono">{{ task.estimated_minutes }} phút</span>
                            @if (task.scheduled_date) {
                              <span>&bull;</span>
                              <span>{{ task.scheduled_date }}</span>
                            }
                          </div>
                        </div>
                      </label>

                      <button
                        type="button"
                        [disabled]="togglingTaskId() === task.id || task.status === 'CANCELLED'"
                        (click)="toggleTaskComplete.emit(task)"
                        [attr.aria-label]="
                          task.status === 'COMPLETED'
                            ? 'Mở lại nhiệm vụ: ' + task.title
                            : 'Hoàn thành nhanh nhiệm vụ: ' + task.title
                        "
                        [attr.aria-pressed]="task.status === 'COMPLETED'"
                        class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded border transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
                        [class]="task.status === 'COMPLETED'
                          ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))] text-[var(--on-primary)]'
                          : 'border-[var(--ws-border,var(--outline-variant))] opacity-75 hover:border-[var(--ws-accent,var(--primary))] hover:opacity-100'"
                      >
                        <lucide-icon name="check-circle-2" [size]="13" aria-hidden="true"></lucide-icon>
                      </button>
                    </div>
                  }
                </div>
              }
            }
          </div>
        }
      </section>

      <!-- CARD 3: Công cụ nhanh -->
      <section
        aria-label="Công cụ nhanh"
        class="rounded-xl p-3 transition-colors"
        style="background: var(--ws-surface-panel, var(--surface-container-lowest)); border: 1px solid var(--ws-border, var(--outline-variant)); color: var(--ws-text-primary, var(--on-surface)); backdrop-filter: var(--ws-panel-blur, blur(16px));"
      >
        @if (activeTool() === null) {
          <div class="mb-2 flex items-center justify-between">
            <h3
              class="m-0 font-serif text-xs font-medium uppercase tracking-[0.06em]"
              style="color: var(--ws-text-secondary, var(--on-surface-variant));"
            >
              Công cụ nhanh
            </h3>
          </div>

          <nav aria-label="Lưới công cụ không gian học" class="grid grid-cols-3 gap-2">
            <!-- 1. Âm thanh -->
            <button
              type="button"
              (click)="toggleTool.emit('audio')"
              [attr.aria-expanded]="false"
              aria-label="Âm thanh & Nhạc nền"
              class="relative flex min-h-[64px] flex-col items-center justify-center gap-1.5 rounded-lg border border-[var(--ws-border,var(--outline-variant))] p-2 text-[11px] font-medium transition-colors hover:border-[var(--ws-accent,var(--primary))]/60 cursor-pointer"
            >
              <lucide-icon [name]="isMuted() ? 'volume-x' : 'volume-2'" [size]="16" aria-hidden="true"></lucide-icon>
              <span class="w-full truncate text-center leading-tight">Âm thanh</span>
              @if (isAnySoundPlaying() && !isMuted()) {
                <span
                  class="absolute right-2 top-2 h-2 w-2 rounded-full"
                  style="background: var(--ws-accent, #246B4A);"
                  aria-hidden="true"
                ></span>
              }
            </button>

            <!-- 2. Bối cảnh -->
            <button
              type="button"
              (click)="toggleTool.emit('scene')"
              [attr.aria-expanded]="false"
              aria-label="Bối cảnh không gian"
              class="relative flex min-h-[64px] flex-col items-center justify-center gap-1.5 rounded-lg border border-[var(--ws-border,var(--outline-variant))] p-2 text-[11px] font-medium transition-colors hover:border-[var(--ws-accent,var(--primary))]/60 cursor-pointer"
            >
              <lucide-icon name="palette" [size]="16" aria-hidden="true"></lucide-icon>
              <span class="w-full truncate text-center leading-tight">Bối cảnh</span>
            </button>

            <!-- 3. Chặn sao nhãng -->
            <button
              type="button"
              (click)="toggleTool.emit('shield')"
              [attr.aria-expanded]="false"
              aria-label="Chặn sao nhãng"
              class="relative flex min-h-[64px] flex-col items-center justify-center gap-1.5 rounded-lg border border-[var(--ws-border,var(--outline-variant))] p-2 text-[11px] font-medium transition-colors hover:border-[var(--ws-accent,var(--primary))]/60 cursor-pointer"
            >
              <lucide-icon name="shield" [size]="16" aria-hidden="true"></lucide-icon>
              <span class="w-full truncate text-center leading-tight">Chặn sao nhãng</span>
              @if (tabGuardEnabled()) {
                <span
                  class="absolute right-1.5 top-1.5 rounded-full px-1 font-mono text-[9px] font-semibold"
                  style="background: color-mix(in srgb, var(--ws-accent, #246B4A) 15%, transparent); color: var(--ws-accent, #246B4A);"
                  aria-hidden="true"
                >
                  {{ focusScore() }}
                </span>
              }
            </button>

            <!-- 4. Đồng hồ -->
            <button
              type="button"
              (click)="toggleTool.emit('clock')"
              [attr.aria-expanded]="false"
              aria-label="Giao diện đồng hồ"
              class="relative flex min-h-[64px] flex-col items-center justify-center gap-1.5 rounded-lg border border-[var(--ws-border,var(--outline-variant))] p-2 text-[11px] font-medium transition-colors hover:border-[var(--ws-accent,var(--primary))]/60 cursor-pointer"
            >
              <lucide-icon name="clock" [size]="16" aria-hidden="true"></lucide-icon>
              <span class="w-full truncate text-center leading-tight">Đồng hồ</span>
            </button>

            <!-- 5. Ghi chú nhanh -->
            <button
              type="button"
              (click)="toggleNotesPanel.emit()"
              [attr.aria-pressed]="notesPanelOpen()"
              aria-label="Ghi chú nhanh"
              class="relative flex min-h-[64px] flex-col items-center justify-center gap-1.5 rounded-lg border p-2 text-[11px] font-medium transition-colors cursor-pointer"
              [class]="notesPanelOpen()
                ? 'border-[var(--ws-accent,var(--primary))] bg-[var(--ws-accent,var(--primary))] text-[var(--on-primary)]'
                : 'border-[var(--ws-border,var(--outline-variant))] hover:border-[var(--ws-accent,var(--primary))]/60'"
            >
              <lucide-icon name="sticky-note" [size]="16" aria-hidden="true"></lucide-icon>
              <span class="w-full truncate text-center leading-tight">Ghi chú nhanh</span>
              @if (notesCount() > 0) {
                <span
                  class="absolute right-1.5 top-1.5 inline-flex min-w-[1rem] items-center justify-center rounded-full px-1 text-[9px] font-semibold tabular-nums"
                  [class]="notesPanelOpen()
                    ? 'bg-[var(--on-primary)] text-[var(--ws-accent,var(--primary))]'
                    : 'bg-[var(--surface-container-high)] text-[var(--on-surface)]'"
                >
                  {{ notesCount() }}
                </span>
              }
            </button>
          </nav>
        } @else {
          <div class="max-h-[40vh] overflow-y-auto">
            <ng-content select="[left-tool-panel]"></ng-content>
          </div>
        }
      </section>
    </aside>
  `,
})
export class WorkspaceLeftPanelComponent {
  readonly progress = input.required<TodayProgressSummary>();
  readonly completedPomodorosToday = input<number>(0);
  readonly localDate = input<string>('');
  readonly tasks = input.required<TaskResponse[]>();
  readonly activeSession = input<StudySessionResponse | null>(null);
  readonly activeSessionTasks = input<TaskResponse[]>([]);
  readonly pendingTakeawaySession = input<StudySessionResponse | null>(null);
  readonly selectedTaskIds = input.required<string[]>();
  readonly isSubmitting = input<boolean>(false);
  readonly togglingTaskId = input<string | null>(null);
  readonly isLoading = input<boolean>(false);
  readonly isFullscreen = input<boolean>(false);
  readonly focusMode = input<boolean>(false);
  readonly activeFocusTaskId = input<string | null>(null);
  readonly activeTool = input<WorkspaceToolPopover>(null);
  readonly isAnySoundPlaying = input<boolean>(false);
  readonly isMuted = input<boolean>(false);
  readonly tabGuardEnabled = input<boolean>(false);
  readonly focusScore = input<number>(100);
  readonly notesPanelOpen = input<boolean>(false);
  readonly notesCount = input<number>(0);

  readonly toggleSelectTask = output<string>();
  readonly toggleTaskComplete = output<TaskResponse>();
  readonly resolveDebt = output<{ sessionId: string; takeaway: string; selfConfidence: number }>();
  readonly collapsePanel = output<void>();
  readonly refreshWorkspace = output<void>();
  readonly toggleFullscreen = output<void>();
  readonly toggleFocusMode = output<void>();
  readonly selectFocusTask = output<string>();
  readonly attemptSwitchOutsideTask = output<TaskResponse>();
  readonly toggleTool = output<Exclude<WorkspaceToolPopover, null>>();
  readonly toggleNotesPanel = output<void>();

  protected readonly confidenceScores = [1, 2, 3, 4, 5] as const;
  protected readonly targetPomodoros = TARGET_POMODOROS_PER_DAY;

  readonly filterMode = signal<TaskFilterMode>('all');
  readonly debtTakeaway = signal<string>('');
  readonly debtConfidence = signal<number>(3);

  readonly debtTakeawayCheck = computed(() => evaluateTakeawayCheck(this.debtTakeaway()));

  readonly clampedPercentage = computed(() =>
    Math.max(0, Math.min(100, Math.round(this.progress().percentage)))
  );

  readonly activeGoalTitle = computed<string>(() => {
    const focusId = this.activeFocusTaskId();
    if (focusId) {
      const focused =
        this.activeSessionTasks().find((t) => t.id === focusId) ??
        this.tasks().find((t) => t.id === focusId);
      if (focused) return focused.title;
    }
    if (this.activeSessionTasks().length > 0) {
      return this.activeSessionTasks()[0].title;
    }
    const selectedIds = this.selectedTaskIds();
    if (selectedIds.length > 0) {
      const firstSelected = this.tasks().find((t) => selectedIds.includes(t.id));
      if (firstSelected) return firstSelected.title;
    }
    return this.tasks()[0]?.title ?? 'Sẵn sàng cho phiên học mới';
  });

  readonly todoCount = computed(
    () =>
      this.tasks().filter((t) => t.status !== 'COMPLETED' && t.status !== 'CANCELLED').length
  );

  readonly overdueCount = computed(
    () =>
      this.tasks().filter(
        (t) => t.is_overdue && t.status !== 'COMPLETED' && t.status !== 'CANCELLED'
      ).length
  );

  readonly filteredTasks = computed<TaskResponse[]>(() => this.applyFilter(this.tasks()));

  readonly filteredActiveTasks = computed<TaskResponse[]>(() =>
    this.applyFilter(this.activeSessionTasks())
  );

  readonly filteredRemainingTasks = computed<TaskResponse[]>(() => {
    const activeIds = new Set(this.activeSessionTasks().map((t) => t.id));
    return this.filteredTasks().filter((t) => !activeIds.has(t.id));
  });

  private readonly selectedRoadmapId = computed<string | null>(() => {
    const selectedIds = this.selectedTaskIds();
    if (selectedIds.length === 0) return null;
    const firstSelected = this.tasks().find((t) => selectedIds.includes(t.id));
    return firstSelected?.roadmap_id ?? null;
  });

  isTaskSelected(taskId: string): boolean {
    return this.selectedTaskIds().includes(taskId);
  }

  getSelectDisabledReason(task: TaskResponse): string | null {
    if (task.status === 'COMPLETED') return 'Đã hoàn thành';
    if (task.status === 'CANCELLED') return 'Đã hủy';
    if (task.is_blocked) return 'Bị chặn';
    const lockedRoadmapId = this.selectedRoadmapId();
    if (lockedRoadmapId && task.roadmap_id !== lockedRoadmapId && !this.isTaskSelected(task.id)) {
      return 'Khác lộ trình';
    }
    return null;
  }

  statusLabel(status: string): string {
    switch (status) {
      case 'COMPLETED':
        return 'Hoàn thành';
      case 'IN_PROGRESS':
        return 'Đang học';
      case 'CANCELLED':
        return 'Đã hủy';
      case 'SKIPPED':
        return 'Bỏ qua';
      default:
        return 'Chờ thực hiện';
    }
  }

  getTaskResources(task: TaskResponse): TaskResourceLink[] {
    const items = task.learning_resources ?? [];
    return items.map((raw, idx) => {
      const labelCandidate = raw['title'] ?? raw['name'] ?? raw['label'] ?? raw['url'];
      const label =
        typeof labelCandidate === 'string' && labelCandidate.trim().length > 0
          ? labelCandidate.trim()
          : `Tài liệu #${idx + 1}`;
      const urlCandidate = raw['url'] ?? raw['href'];
      const url =
        typeof urlCandidate === 'string' && /^https?:\/\//i.test(urlCandidate.trim())
          ? urlCandidate.trim()
          : null;
      return { label, url };
    });
  }

  onToggleCompleteClick(event: Event, task: TaskResponse): void {
    event.stopPropagation();
    this.toggleTaskComplete.emit(task);
  }

  onDebtTakeawayInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null;
    this.debtTakeaway.set(target?.value ?? '');
  }

  submitDebt(sessionId: string): void {
    if (!this.debtTakeawayCheck().isValid || this.isSubmitting()) return;
    this.resolveDebt.emit({
      sessionId,
      takeaway: this.debtTakeaway().trim(),
      selfConfidence: this.debtConfidence(),
    });
  }

  private applyFilter(list: TaskResponse[]): TaskResponse[] {
    const mode = this.filterMode();
    if (mode === 'todo') {
      return list.filter((t) => t.status !== 'COMPLETED' && t.status !== 'CANCELLED');
    }
    if (mode === 'overdue') {
      return list.filter(
        (t) => t.is_overdue && t.status !== 'COMPLETED' && t.status !== 'CANCELLED'
      );
    }
    return list;
  }
}
