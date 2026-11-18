import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Clock,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
  Pause,
  Play,
  RefreshCw,
  Sparkles,
  Square,
  WifiOff,
  X,
} from 'lucide-angular';
import {
  TimeSufficiency,
  WorkspaceSessionService,
  evaluateTakeawayCheck,
} from '../../core/services/workspace-session.service';
import { SessionMode, TaskResponse } from './models/workspace.model';
import { ButtonDirective } from '../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../shared/ui/badge/badge.directive';

@Component({
  selector: 'app-workspace',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, FormsModule, RouterLink, LucideAngularModule, ButtonDirective, BadgeDirective],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        BookOpen,
        CheckCircle2,
        Clock,
        Pause,
        Play,
        RefreshCw,
        Sparkles,
        Square,
        WifiOff,
        X,
      }),
    },
  ],
  host: {
    '(document:keydown.escape)': 'onEscape()',
  },
  template: `
    <div class="max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <span class="text-[11px] uppercase tracking-wider font-semibold text-[var(--muted-foreground)]">
            Study Workspace (Pomodoro &amp; MVS)
          </span>
          <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--foreground)]">
            Phiên Học Tập Trung
          </h1>
          <p class="text-xs sm:text-sm text-[var(--muted-foreground)] mt-0.5">
            Thực thi nhiệm vụ học tập với nhịp tim đồng bộ 60 giây và lưu giữ Key Takeaway
          </p>
        </div>

        <div class="flex items-center gap-2 self-start sm:self-auto">
          @if (sessionService.todayFocus(); as tf) {
            @if (tf.overdue_tasks_count > 0) {
              <a
                routerLink="/tasks"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-800 dark:text-amber-300 border border-amber-500/30 no-underline hover:opacity-90"
              >
                <lucide-icon name="alert-triangle" [size]="14" aria-hidden="true"></lucide-icon>
                <span>{{ tf.overdue_tasks_count }} việc quá hạn</span>
              </a>
            }
          }
          <button
            type="button"
            appButton
            variant="outline"
            size="sm"
            [disabled]="sessionService.isLoading()"
            (click)="refreshWorkspace()"
            aria-label="Làm mới không gian học tập"
          >
            <lucide-icon name="refresh-cw" [size]="14" aria-hidden="true"></lucide-icon>
            <span>Làm mới</span>
          </button>
        </div>
      </div>

      <!-- Global Error Banner -->
      @if (sessionService.errorState(); as err) {
        <div
          role="alert"
          data-testid="workspace-error-banner"
          class="p-4 rounded-xl border border-red-500/40 bg-red-500/10 text-red-900 dark:text-red-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div class="space-y-0.5">
            <div class="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
              <lucide-icon name="alert-triangle" [size]="14" aria-hidden="true"></lucide-icon>
              <span>{{ err.isOffline ? 'Mất kết nối mạng' : 'Không thể thực hiện thao tác' }}</span>
              @if (err.code) {
                <span class="font-mono px-1.5 py-0.5 rounded bg-red-500/15 text-[11px]">{{ err.code }}</span>
              }
            </div>
            <p class="text-xs sm:text-sm">{{ err.message }}</p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button type="button" appButton variant="outline" size="sm" (click)="refreshWorkspace()">
              Thử lại
            </button>
            <button type="button" appButton variant="ghost" size="sm" (click)="sessionService.clearError()">
              Đóng
            </button>
          </div>
        </div>
      }

      <!-- Session Finalized Success Banner -->
      @if (sessionService.lastFinalizedSession(); as finished) {
        <div
          role="status"
          data-testid="session-finalized-banner"
          class="p-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div class="flex items-start gap-2.5">
            <lucide-icon name="check-circle-2" [size]="18" class="text-emerald-600 shrink-0 mt-0.5" aria-hidden="true"></lucide-icon>
            <div class="space-y-0.5">
              <div class="text-sm font-semibold">Đã hoàn tất phiên học ({{ finished.actual_minutes }} phút)</div>
              @if (finished.takeaway_content) {
                <p class="text-xs opacity-90 line-clamp-2">Takeaway: "{{ finished.takeaway_content }}"</p>
              }
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <a routerLink="/analytics" appButton variant="outline" size="sm">Xem Phân tích</a>
            <button type="button" appButton variant="ghost" size="sm" (click)="sessionService.clearFinalizedBanner()">
              Đóng
            </button>
          </div>
        </div>
      }

      <!-- Loading State -->
      @if (sessionService.isLoading() && !sessionService.todayFocus()) {
        <div class="p-8 rounded-2xl border border-[var(--border)] bg-[var(--card)] flex flex-col items-center justify-center gap-3 text-center">
          <lucide-icon name="refresh-cw" [size]="24" class="animate-spin text-[var(--primary)]" aria-hidden="true"></lucide-icon>
          <p class="text-sm text-[var(--muted-foreground)]">Đang đồng bộ phiên học và hàng đợi hôm nay...</p>
        </div>
      } @else {
        <!-- FR-SESSION-001: Takeaway Debt Resolution Banner/Form -->
        @if (sessionService.pendingTakeawaySession(); as debt) {
          <section
            aria-labelledby="takeaway-debt-heading"
            data-testid="pending-takeaway-card"
            class="rounded-2xl border-2 border-amber-500/60 bg-amber-50/70 dark:bg-amber-950/20 p-5 sm:p-6 space-y-4 shadow-xs"
          >
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-800 dark:text-amber-300 flex items-center justify-center shrink-0">
                <lucide-icon name="alert-triangle" [size]="20" aria-hidden="true"></lucide-icon>
              </div>
              <div class="space-y-1">
                <div class="flex flex-wrap items-center gap-2">
                  <h2 id="takeaway-debt-heading" class="text-base sm:text-lg font-bold text-[var(--foreground)]">
                    Bạn có phiên học chưa hoàn tất Key Takeaway
                  </h2>
                  <span appBadge variant="outline" class="border-amber-500/50 text-amber-800 dark:text-amber-300">
                    FR-SESSION-001
                  </span>
                </div>
                <p class="text-xs sm:text-sm text-[var(--muted-foreground)]">
                  Phiên học ({{ debt.session_mode }} &bull; {{ debt.actual_minutes }}/{{ debt.planned_minutes }} phút) đã tự động đóng trước đó.
                  Vui lòng tóm tắt kiến thức cốt lõi (tối thiểu 30 ký tự &amp; 6 từ phân biệt) trước khi bắt đầu phiên học mới.
                </p>
              </div>
            </div>

            <div class="space-y-3 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4">
              <div class="space-y-1.5">
                <label for="debt-takeaway-input" class="block text-xs font-semibold text-[var(--foreground)]">
                  Key Takeaway bắt buộc *
                </label>
                <textarea
                  id="debt-takeaway-input"
                  data-testid="debt-takeaway-textarea"
                  rows="3"
                  [ngModel]="debtTakeaway()"
                  (ngModelChange)="debtTakeaway.set($event)"
                  placeholder="Ví dụ: Em đã nắm được cách tách interface Port ở Application layer và Adapter ở Infrastructure layer..."
                  class="w-full rounded-lg border border-[var(--input)] bg-[var(--background)] p-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                ></textarea>
                <div class="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                  <span
                    [class.text-emerald-700]="debtTakeawayCheck().isValid"
                    [class.dark:text-emerald-400]="debtTakeawayCheck().isValid"
                    [class.text-[var(--muted-foreground)]]="!debtTakeawayCheck().isValid"
                  >
                    {{ debtTakeawayCheck().charCount }}/30 ký tự &bull; {{ debtTakeawayCheck().distinctWordCount }}/6 từ riêng biệt
                  </span>
                  @if (!debtTakeawayCheck().hasNoRepeatedChars) {
                    <span class="text-red-600 font-medium">Tránh lặp ký tự vô nghĩa quá 5 lần.</span>
                  }
                </div>
              </div>

              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                <div class="space-y-1">
                  <span class="block text-xs font-semibold text-[var(--foreground)]">Mức độ tự tin (1–5)</span>
                  <div class="flex items-center gap-1.5">
                    @for (score of confidenceScores; track score) {
                      <button
                        type="button"
                        (click)="debtConfidence.set(score)"
                        [attr.aria-pressed]="debtConfidence() === score"
                        class="w-8 h-8 rounded-lg text-xs font-bold border transition-colors cursor-pointer"
                        [class]="debtConfidence() === score
                          ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]'
                          : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:bg-[var(--muted)]'"
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
                  data-testid="resolve-takeaway-btn"
                  [disabled]="sessionService.isSubmitting() || !debtTakeawayCheck().isValid"
                  (click)="submitPendingTakeaway(debt.id)"
                >
                  {{ sessionService.isSubmitting() ? 'Đang lưu...' : 'Xác nhận Takeaway & Mở khóa' }}
                </button>
              </div>
            </div>
          </section>
        }

        <!-- ACTIVE SESSION VIEW -->
        @if (sessionService.activeSession(); as active) {
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <!-- Left: Pomodoro Clock & Controls -->
            <div class="lg:col-span-7 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 sm:p-8 flex flex-col items-center gap-6 shadow-xs">
              <div class="w-full flex items-center justify-between gap-2">
                <span appBadge variant="default">
                  {{ active.session_mode === 'MVS' ? 'Chế độ MVS (Tối thiểu)' : 'Phiên Tiêu chuẩn' }}
                </span>

                <!-- Heartbeat Status Pill -->
                <div
                  class="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--background)]"
                  aria-live="polite"
                >
                  @switch (sessionService.heartbeatStatus()) {
                    @case ('offline') {
                      <lucide-icon name="wifi-off" [size]="13" class="text-red-600" aria-hidden="true"></lucide-icon>
                      <span class="text-red-700 dark:text-red-300 font-medium">Ngoại tuyến</span>
                      <button
                        type="button"
                        (click)="retryHeartbeat()"
                        class="ml-1 underline font-semibold text-[var(--primary)] cursor-pointer"
                      >
                        Thử lại
                      </button>
                    }
                    @case ('error') {
                      <lucide-icon name="alert-triangle" [size]="13" class="text-amber-600" aria-hidden="true"></lucide-icon>
                      <span class="text-amber-700 dark:text-amber-300 font-medium">Lỗi đồng bộ</span>
                      <button
                        type="button"
                        (click)="retryHeartbeat()"
                        class="ml-1 underline font-semibold text-[var(--primary)] cursor-pointer"
                      >
                        Thử lại
                      </button>
                    }
                    @case ('syncing') {
                      <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                      <span class="text-[var(--muted-foreground)]">Đang đồng bộ...</span>
                    }
                    @default {
                      <span
                        class="w-2 h-2 rounded-full"
                        [class.bg-emerald-500]="sessionService.isRunning()"
                        [class.bg-amber-500]="!sessionService.isRunning()"
                      ></span>
                      <span class="text-[var(--muted-foreground)]">
                        {{ sessionService.isRunning() ? 'Heartbeat 60s đang bật' : 'Đã tạm dừng' }}
                      </span>
                    }
                  }
                </div>
              </div>

              <!-- Progress Bar -->
              <div class="w-full bg-[var(--muted)] h-2.5 rounded-full overflow-hidden">
                <div
                  class="bg-[var(--primary)] h-full transition-all duration-300"
                  [style.width.%]="sessionService.progressPercentage()"
                ></div>
              </div>

              <!-- Clock Face -->
              <div class="text-center space-y-1">
                <div
                  class="text-6xl sm:text-7xl font-mono font-bold tracking-tighter text-[var(--foreground)] select-none"
                  aria-live="polite"
                  data-testid="workspace-timer-display"
                >
                  {{ sessionService.formattedTime() }}
                </div>
                <div class="text-xs text-[var(--muted-foreground)]">
                  Đã học {{ sessionService.elapsedMinutes() }} / {{ sessionService.durationMinutes() }} phút
                  @if (sessionService.lastHeartbeatAt(); as hb) {
                    <span>&bull; Đồng bộ lúc {{ formatLocalTime(hb) }}</span>
                  }
                </div>
              </div>

              <!-- Timer Controls -->
              <div class="flex flex-wrap items-center justify-center gap-3 w-full">
                @if (!sessionService.isRunning()) {
                  <button
                    type="button"
                    appButton
                    variant="default"
                    data-testid="resume-session-btn"
                    (click)="sessionService.resumeSession()"
                  >
                    <lucide-icon name="play" [size]="15" aria-hidden="true"></lucide-icon>
                    <span>Tiếp tục</span>
                  </button>
                } @else {
                  <button
                    type="button"
                    appButton
                    variant="outline"
                    data-testid="pause-session-btn"
                    (click)="sessionService.pauseSession()"
                  >
                    <lucide-icon name="pause" [size]="15" aria-hidden="true"></lucide-icon>
                    <span>Tạm dừng</span>
                  </button>
                }

                <button
                  type="button"
                  appButton
                  variant="default"
                  data-testid="open-finalize-btn"
                  (click)="openFinalizeModal(false)"
                >
                  <lucide-icon name="check-circle-2" [size]="15" aria-hidden="true"></lucide-icon>
                  <span>Hoàn thành phiên</span>
                </button>

                <button
                  type="button"
                  appButton
                  variant="outline"
                  data-testid="open-early-stop-btn"
                  (click)="openFinalizeModal(true)"
                >
                  <lucide-icon name="square" [size]="14" aria-hidden="true"></lucide-icon>
                  <span>Kết thúc sớm</span>
                </button>
              </div>

              <!-- Active Session Tasks -->
              <div class="w-full pt-4 border-t border-[var(--border)] space-y-2.5">
                <div class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Nhiệm vụ trong phiên ({{ sessionService.activeSessionTasks().length || active.session_tasks?.length || 0 }})
                </div>
                @for (t of sessionService.activeSessionTasks(); track t.id) {
                  <div class="p-3 rounded-xl border border-[var(--border)] bg-[var(--background)] space-y-1.5">
                    <div class="flex items-center justify-between gap-2">
                      <span class="text-sm font-semibold text-[var(--foreground)]">{{ t.title }}</span>
                      <span class="text-xs font-mono text-[var(--muted-foreground)]">{{ t.estimated_minutes }}p</span>
                    </div>
                    @if (t.description) {
                      <p class="text-xs text-[var(--muted-foreground)]">{{ t.description }}</p>
                    }
                    @if (getTaskResources(t).length > 0) {
                      <div class="flex flex-wrap gap-1.5 pt-1">
                        @for (res of getTaskResources(t); track $index) {
                          @if (res.url) {
                            <a
                              [href]="res.url"
                              target="_blank"
                              rel="noopener noreferrer"
                              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-[var(--muted)] text-[var(--primary)] hover:underline"
                            >
                              <lucide-icon name="book-open" [size]="11" aria-hidden="true"></lucide-icon>
                              <span>{{ res.label }}</span>
                            </a>
                          } @else {
                            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-[var(--muted)] text-[var(--foreground)]">
                              <lucide-icon name="book-open" [size]="11" aria-hidden="true"></lucide-icon>
                              <span>{{ res.label }}</span>
                            </span>
                          }
                        }
                      </div>
                    }
                  </div>
                }
              </div>
            </div>

            <!-- Right: Scratchpad -->
            <div class="lg:col-span-5 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 sm:p-6 space-y-3 shadow-xs">
              <div class="flex items-center justify-between gap-2">
                <label for="workspace-scratchpad" class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Ghi chú nháp (Scratchpad)
                </label>
                <span class="text-[11px] text-[var(--muted-foreground)]">Tự đồng bộ sau 1.5s</span>
              </div>
              <textarea
                id="workspace-scratchpad"
                data-testid="scratchpad-textarea"
                [ngModel]="sessionService.scratchpadNote()"
                (ngModelChange)="sessionService.setScratchpadNote($event)"
                placeholder="Ghi nhanh suy nghĩ, thắc mắc hoặc ý chính khi đang học..."
                rows="10"
                class="w-full bg-[var(--background)] border border-[var(--input)] rounded-xl p-3.5 text-sm text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] resize-y"
              ></textarea>
              <div class="flex items-center justify-between text-[11px] text-[var(--muted-foreground)]">
                <span>Dữ liệu được lưu vào phiên học hiện tại.</span>
                <button
                  type="button"
                  (click)="retryHeartbeat()"
                  class="font-medium text-[var(--primary)] hover:underline cursor-pointer"
                >
                  Lưu ngay
                </button>
              </div>
            </div>
          </div>
        } @else {
          <!-- NO ACTIVE SESSION: Empty State OR Session Setup -->
          @if (sessionService.availableTasks().length === 0) {
            <div
              data-testid="workspace-empty-state"
              class="p-10 sm:p-12 text-center flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--card)]"
            >
              <div class="w-12 h-12 rounded-2xl bg-[var(--muted)] text-[var(--muted-foreground)] flex items-center justify-center mb-3">
                <lucide-icon name="clock" [size]="24" aria-hidden="true"></lucide-icon>
              </div>
              <h2 class="text-lg font-bold text-[var(--foreground)] mb-1">
                Chưa có nhiệm vụ nào cho hôm nay
              </h2>
              <p class="text-xs sm:text-sm text-[var(--muted-foreground)] max-w-md mb-5 leading-relaxed">
                Hàng đợi hôm nay đang trống. Bạn có thể chọn một nhiệm vụ từ danh sách Công việc hoặc mở Lộ trình học tập để xếp lịch.
              </p>
              <div class="flex flex-wrap items-center justify-center gap-3">
                <a routerLink="/tasks" appButton variant="default" size="sm">
                  Chọn việc từ Danh sách Nhiệm vụ
                </a>
                <a routerLink="/roadmaps" appButton variant="outline" size="sm">
                  Xem Lộ trình học tập
                </a>
              </div>
            </div>
          } @else {
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              <!-- Task Selection -->
              <div class="lg:col-span-7 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 sm:p-6 space-y-4 shadow-xs">
                <div class="flex items-center justify-between gap-2">
                  <div>
                    <h2 class="text-base font-bold text-[var(--foreground)]">Chọn nhiệm vụ cho phiên học</h2>
                    <p class="text-xs text-[var(--muted-foreground)]">
                      Chọn một hoặc nhiều nhiệm vụ để tập trung thực thi
                    </p>
                  </div>
                  <span appBadge variant="outline">{{ sessionService.availableTasks().length }} khả dụng</span>
                </div>

                <div class="space-y-2.5">
                  @for (task of sessionService.availableTasks(); track task.id) {
                    <label
                      class="flex items-start gap-3 p-3.5 rounded-xl border transition-colors cursor-pointer"
                      [class]="isTaskSelected(task.id)
                        ? 'border-[var(--primary)] bg-[var(--primary)]/5'
                        : 'border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]/50'"
                    >
                      <input
                        type="checkbox"
                        [checked]="isTaskSelected(task.id)"
                        (change)="toggleTaskSelection(task.id)"
                        class="mt-1 h-4 w-4 accent-[var(--primary)]"
                      />
                      <div class="min-w-0 flex-1 space-y-1">
                        <div class="flex flex-wrap items-center gap-2">
                          <span class="text-sm font-semibold text-[var(--foreground)]">{{ task.title }}</span>
                          @if (task.is_overdue) {
                            <span appBadge variant="destructive" class="text-[10px]">Quá hạn</span>
                          }
                          @if (task.is_blocked) {
                            <span appBadge variant="outline" class="text-[10px] border-amber-500 text-amber-700 dark:text-amber-300">
                              Bị chặn
                            </span>
                          }
                          @if (task.is_stalled) {
                            <span appBadge variant="outline" class="text-[10px] border-purple-500 text-purple-700 dark:text-purple-300">
                              Đình trệ
                            </span>
                          }
                        </div>
                        <div class="flex flex-wrap items-center gap-2 text-xs text-[var(--muted-foreground)]">
                          @if (task.roadmap_title) {
                            <span>{{ task.roadmap_title }}</span>
                            <span>&bull;</span>
                          }
                          <span class="font-mono">{{ task.estimated_minutes }} phút</span>
                          @if (task.scheduled_date) {
                            <span>&bull;</span>
                            <span>Ngày {{ task.scheduled_date }}</span>
                          }
                        </div>
                      </div>
                    </label>
                  }
                </div>
              </div>

              <!-- Session Configuration & Start -->
              <div class="lg:col-span-5 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 sm:p-6 space-y-5 shadow-xs">
                <div>
                  <h2 class="text-base font-bold text-[var(--foreground)]">Thiết lập phiên học</h2>
                  <p class="text-xs text-[var(--muted-foreground)]">
                    Chọn chế độ Tiêu chuẩn hoặc MVS (Minimum Viable Session) khi bạn bận rộn
                  </p>
                </div>

                <!-- Session Mode -->
                <div class="space-y-2" role="radiogroup" aria-label="Chế độ phiên học">
                  <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Chế độ
                  </span>
                  <div class="grid grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      data-testid="mode-standard-btn"
                      [attr.aria-pressed]="selectedMode() === 'STANDARD'"
                      (click)="selectMode('STANDARD')"
                      class="p-3 rounded-xl border text-left transition-colors cursor-pointer"
                      [class]="selectedMode() === 'STANDARD'
                        ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--foreground)]'
                        : 'border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)]'"
                    >
                      <div class="text-sm font-bold text-[var(--foreground)]">Tiêu chuẩn</div>
                      <div class="text-[11px] mt-0.5">Deep Work (25–90 phút)</div>
                    </button>

                    <button
                      type="button"
                      data-testid="mode-mvs-btn"
                      [attr.aria-pressed]="selectedMode() === 'MVS'"
                      (click)="selectMode('MVS')"
                      class="p-3 rounded-xl border text-left transition-colors cursor-pointer"
                      [class]="selectedMode() === 'MVS'
                        ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--foreground)]'
                        : 'border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)]'"
                    >
                      <div class="text-sm font-bold text-[var(--foreground)] flex items-center gap-1">
                        <lucide-icon name="sparkles" [size]="13" aria-hidden="true"></lucide-icon>
                        <span>MVS</span>
                      </div>
                      <div class="text-[11px] mt-0.5">Phiên tối thiểu (10–15 phút)</div>
                    </button>
                  </div>
                </div>

                <!-- Planned Minutes -->
                <div class="space-y-2">
                  <label for="planned-minutes-input" class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Thời lượng dự kiến (phút)
                  </label>
                  <div class="flex flex-wrap gap-2">
                    @for (preset of minutePresets(); track preset) {
                      <button
                        type="button"
                        (click)="plannedMinutes.set(preset)"
                        class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                        [class]="plannedMinutes() === preset
                          ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]'
                          : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:bg-[var(--muted)]'"
                      >
                        {{ preset }} phút
                      </button>
                    }
                  </div>
                  <input
                    id="planned-minutes-input"
                    type="number"
                    min="5"
                    max="180"
                    [ngModel]="plannedMinutes()"
                    (ngModelChange)="onPlannedMinutesChange($event)"
                    class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                  />
                </div>

                <button
                  type="button"
                  appButton
                  variant="default"
                  data-testid="start-session-btn"
                  class="w-full"
                  [disabled]="
                    sessionService.isSubmitting() ||
                    selectedTaskIds().length === 0 ||
                    sessionService.pendingTakeawaySession() !== null
                  "
                  (click)="startStudySession()"
                >
                  <lucide-icon name="play" [size]="15" aria-hidden="true"></lucide-icon>
                  <span>
                    {{ sessionService.isSubmitting() ? 'Đang khởi tạo...' : 'Bắt đầu phiên học' }}
                  </span>
                </button>

                @if (sessionService.pendingTakeawaySession() !== null) {
                  <p class="text-[11px] text-amber-700 dark:text-amber-300">
                    Cần hoàn tất Key Takeaway của phiên trước đó ở phía trên trước khi bắt đầu phiên mới.
                  </p>
                }
              </div>
            </div>
          }
        }
      }
    </div>

    <!-- Finalize / Early Stop Modal -->
    @if (finalizeModalOpen()) {
      <div
        class="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4"
        (click)="closeFinalizeModal()"
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
          class="pointer-events-auto w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] shadow-2xl p-5 sm:p-6 space-y-5"
          (click)="$event.stopPropagation()"
        >
          <div class="flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
            <div>
              <h2 id="finalize-dialog-title" class="text-lg font-bold">
                {{ isEarlyStop() ? 'Xác nhận Kết thúc sớm phiên học' : 'Hoàn tất phiên học &amp; Ghi nhận' }}
              </h2>
              <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
                Thời gian thực tế: {{ sessionService.elapsedMinutes() }} phút
              </p>
            </div>
            <button
              type="button"
              appButton
              variant="ghost"
              size="icon"
              (click)="closeFinalizeModal()"
              aria-label="Đóng hộp thoại hoàn tất phiên học"
            >
              <lucide-icon name="x" [size]="18" aria-hidden="true"></lucide-icon>
            </button>
          </div>

          @if (isEarlyStop()) {
            <div class="p-3 rounded-xl border border-amber-500/40 bg-amber-500/10 text-xs text-amber-900 dark:text-amber-200 space-y-2">
              <div class="font-semibold flex items-center gap-1.5">
                <lucide-icon name="alert-triangle" [size]="14" aria-hidden="true"></lucide-icon>
                <span>Bạn đang dừng trước thời lượng dự kiến ({{ sessionService.durationMinutes() }} phút).</span>
              </div>
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  data-testid="confirm-early-stop-checkbox"
                  [checked]="earlyStopConfirmed()"
                  (change)="earlyStopConfirmed.set($any($event.target).checked)"
                  class="h-4 w-4 accent-[var(--primary)]"
                />
                <span>Tôi xác nhận muốn kết thúc sớm và lưu lại tiến độ hiện tại.</span>
              </label>
            </div>
          }

          @if (finalizeError(); as fErr) {
            <div
              role="alert"
              data-testid="finalize-error-alert"
              class="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-xs text-red-900 dark:text-red-200 space-y-0.5"
            >
              @if (fErr.code) {
                <div class="font-mono font-bold">{{ fErr.code }}</div>
              }
              <div>{{ fErr.message }}</div>
            </div>
          }

          <!-- Completed Task Checkboxes -->
          @if (sessionService.activeSessionTasks().length > 0) {
            <div class="space-y-2">
              <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                Đánh dấu nhiệm vụ đã hoàn thành
              </span>
              <div class="space-y-1.5">
                @for (task of sessionService.activeSessionTasks(); track task.id) {
                  <label class="flex items-center gap-2.5 p-2.5 rounded-lg border border-[var(--border)] bg-[var(--background)] cursor-pointer text-sm">
                    <input
                      type="checkbox"
                      [checked]="completedTaskIds().includes(task.id)"
                      (change)="toggleCompletedTask(task.id)"
                      class="h-4 w-4 accent-[var(--primary)]"
                    />
                    <span class="flex-1 truncate">{{ task.title }}</span>
                  </label>
                }
              </div>
            </div>
          }

          <!-- Key Takeaway -->
          <div class="space-y-1.5">
            <label for="finalize-takeaway-input" class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Key Takeaway (Tóm tắt điều bạn rút ra) *
            </label>
            <textarea
              id="finalize-takeaway-input"
              data-testid="finalize-takeaway-textarea"
              rows="3"
              [ngModel]="finalizeTakeaway()"
              (ngModelChange)="finalizeTakeaway.set($event)"
              placeholder="Ví dụ: Đã hiểu rõ cơ chế Outbox Pattern đảm bảo nhất quán sự kiện giữa PostgreSQL và Redis..."
              class="w-full rounded-xl border border-[var(--input)] bg-[var(--background)] p-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            ></textarea>
            <div class="flex flex-wrap items-center justify-between gap-2 text-[11px]">
              <span
                [class.text-emerald-700]="finalizeTakeawayCheck().isValid"
                [class.dark:text-emerald-400]="finalizeTakeawayCheck().isValid"
                [class.text-[var(--muted-foreground)]]="!finalizeTakeawayCheck().isValid"
              >
                {{ finalizeTakeawayCheck().charCount }}/30 ký tự &bull; {{ finalizeTakeawayCheck().distinctWordCount }}/6 từ phân biệt
              </span>
              @if (!finalizeTakeawayCheck().hasAlpha && finalizeTakeaway().length > 0) {
                <span class="text-red-600">Cần chứa từ ngữ có nghĩa.</span>
              }
            </div>
          </div>

          <!-- Self Confidence (1..5) -->
          <div class="space-y-1.5">
            <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Mức độ tự tin nắm bài (1–5)
            </span>
            <div class="flex items-center gap-2">
              @for (score of confidenceScores; track score) {
                <button
                  type="button"
                  (click)="finalizeConfidence.set(score)"
                  [attr.aria-pressed]="finalizeConfidence() === score"
                  class="flex-1 h-9 rounded-lg text-xs font-bold border transition-colors cursor-pointer"
                  [class]="finalizeConfidence() === score
                    ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]'
                    : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:bg-[var(--muted)]'"
                >
                  {{ score }}
                </button>
              }
            </div>
          </div>

          <!-- Daily Learning Check-in -->
          <div class="space-y-3 pt-2 border-t border-[var(--border)]">
            <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Daily Learning Check-in
            </span>

            <div class="space-y-1.5">
              <span class="block text-xs font-medium text-[var(--foreground)]">Thời lượng phiên học vừa qua:</span>
              <div class="grid grid-cols-3 gap-2">
                @for (opt of timeSufficiencyOptions; track opt.value) {
                  <button
                    type="button"
                    (click)="checkinTimeSufficiency.set(opt.value)"
                    [attr.aria-pressed]="checkinTimeSufficiency() === opt.value"
                    class="py-2 px-2 rounded-lg text-xs font-medium border transition-colors cursor-pointer"
                    [class]="checkinTimeSufficiency() === opt.value
                      ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]'
                      : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:bg-[var(--muted)]'"
                  >
                    {{ opt.label }}
                  </button>
                }
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div class="space-y-1">
                <span class="block text-xs font-medium text-[var(--foreground)]">Độ khó cảm nhận (1–5)</span>
                <div class="flex items-center gap-1.5">
                  @for (lvl of confidenceScores; track lvl) {
                    <button
                      type="button"
                      (click)="checkinDifficulty.set(lvl)"
                      [attr.aria-pressed]="checkinDifficulty() === lvl"
                      class="flex-1 h-8 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                      [class]="checkinDifficulty() === lvl
                        ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]'
                        : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:bg-[var(--muted)]'"
                    >
                      {{ lvl }}
                    </button>
                  }
                </div>
              </div>

              <div class="space-y-1">
                <span class="block text-xs font-medium text-[var(--foreground)]">Mức độ tập trung (1–5)</span>
                <div class="flex items-center gap-1.5">
                  @for (lvl of confidenceScores; track lvl) {
                    <button
                      type="button"
                      (click)="checkinFocusLevel.set(lvl)"
                      [attr.aria-pressed]="checkinFocusLevel() === lvl"
                      class="flex-1 h-8 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                      [class]="checkinFocusLevel() === lvl
                        ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]'
                        : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:bg-[var(--muted)]'"
                    >
                      {{ lvl }}
                    </button>
                  }
                </div>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-[var(--border)]">
            <button type="button" appButton variant="outline" (click)="closeFinalizeModal()">
              Hủy
            </button>
            <button
              type="button"
              appButton
              variant="default"
              data-testid="submit-finalize-btn"
              [disabled]="
                sessionService.isSubmitting() ||
                (isEarlyStop() && !earlyStopConfirmed()) ||
                !finalizeTakeawayCheck().isValid
              "
              (click)="submitFinalize()"
            >
              {{ sessionService.isSubmitting() ? 'Đang lưu...' : 'Xác nhận hoàn tất' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class WorkspaceComponent implements OnInit {
  readonly sessionService = inject(WorkspaceSessionService);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  readonly confidenceScores = [1, 2, 3, 4, 5] as const;
  readonly timeSufficiencyOptions: ReadonlyArray<{ value: TimeSufficiency; label: string }> = [
    { value: 'TOO_SHORT', label: 'Quá ngắn' },
    { value: 'JUST_RIGHT', label: 'Vừa đủ' },
    { value: 'TOO_LONG', label: 'Quá dài' },
  ];

  // Setup state
  readonly preferredTaskId = signal<string | null>(null);
  readonly selectedTaskIds = signal<string[]>([]);
  readonly selectedMode = signal<SessionMode>('STANDARD');
  readonly plannedMinutes = signal<number>(25);

  readonly minutePresets = computed(() =>
    this.selectedMode() === 'MVS' ? [10, 15] : [25, 45, 60, 90]
  );

  // Takeaway debt form state
  readonly debtTakeaway = signal<string>('');
  readonly debtConfidence = signal<number>(3);
  readonly debtTakeawayCheck = computed(() => evaluateTakeawayCheck(this.debtTakeaway()));

  // Finalize modal state
  readonly finalizeModalOpen = signal<boolean>(false);
  readonly isEarlyStop = signal<boolean>(false);
  readonly earlyStopConfirmed = signal<boolean>(false);
  readonly completedTaskIds = signal<string[]>([]);
  readonly finalizeTakeaway = signal<string>('');
  readonly finalizeConfidence = signal<number>(4);
  readonly checkinTimeSufficiency = signal<TimeSufficiency>('JUST_RIGHT');
  readonly checkinDifficulty = signal<number>(3);
  readonly checkinFocusLevel = signal<number>(4);
  readonly finalizeTakeawayCheck = computed(() => evaluateTakeawayCheck(this.finalizeTakeaway()));
  readonly finalizeError = computed(() =>
    this.finalizeModalOpen() ? this.sessionService.errorState() : null
  );

  ngOnInit(): void {
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const taskId = params.get('taskId');
      this.preferredTaskId.set(taskId);
      this.loadInitialWorkspace(taskId);
    });
  }

  refreshWorkspace(): void {
    this.loadInitialWorkspace(this.preferredTaskId());
  }

  private loadInitialWorkspace(taskId: string | null): void {
    this.sessionService
      .loadWorkspace(taskId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((focus) => {
        const available = this.sessionService.availableTasks();
        if (taskId && available.some((t) => t.id === taskId)) {
          this.selectedTaskIds.set([taskId]);
          const matched = available.find((t) => t.id === taskId);
          if (matched && this.selectedMode() === 'STANDARD') {
            this.plannedMinutes.set(Math.min(180, Math.max(15, matched.estimated_minutes || 25)));
          }
        } else if (focus?.focus_task) {
          this.selectedTaskIds.set([focus.focus_task.id]);
          if (this.selectedMode() === 'STANDARD') {
            this.plannedMinutes.set(
              Math.min(180, Math.max(15, focus.focus_task.estimated_minutes || 25))
            );
          }
        } else if (available.length > 0 && this.selectedTaskIds().length === 0) {
          this.selectedTaskIds.set([available[0].id]);
        }
      });
  }

  selectMode(mode: SessionMode): void {
    this.selectedMode.set(mode);
    if (mode === 'MVS') {
      this.plannedMinutes.set(15);
    } else {
      const firstId = this.selectedTaskIds()[0];
      const matched = this.sessionService.availableTasks().find((t) => t.id === firstId);
      this.plannedMinutes.set(
        matched ? Math.min(180, Math.max(15, matched.estimated_minutes || 25)) : 25
      );
    }
  }

  onPlannedMinutesChange(val: number | string): void {
    const parsed = Number(val);
    if (!Number.isNaN(parsed)) {
      this.plannedMinutes.set(Math.min(180, Math.max(5, Math.round(parsed))));
    }
  }

  isTaskSelected(taskId: string): boolean {
    return this.selectedTaskIds().includes(taskId);
  }

  toggleTaskSelection(taskId: string): void {
    this.selectedTaskIds.update((current) =>
      current.includes(taskId) ? current.filter((id) => id !== taskId) : [...current, taskId]
    );
  }

  startStudySession(): void {
    const ids = this.selectedTaskIds();
    if (ids.length === 0) return;

    this.sessionService
      .beginSession({
        task_ids: ids,
        session_mode: this.selectedMode(),
        planned_minutes: this.plannedMinutes(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        error: () => {
          // If 409 due to pending takeaway or active session, reload state to reflect server truth
          if (
            this.sessionService.errorState()?.code === 'PENDING_TAKEAWAY_REQUIRED' ||
            this.sessionService.errorState()?.code === 'ACTIVE_SESSION_EXISTS'
          ) {
            this.refreshWorkspace();
          }
        },
      });
  }

  retryHeartbeat(): void {
    this.sessionService
      .sendHeartbeat()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  submitPendingTakeaway(sessionId: string): void {
    const check = this.debtTakeawayCheck();
    if (!check.isValid) return;

    this.sessionService
      .resolvePendingTakeaway(sessionId, {
        takeaway: this.debtTakeaway().trim(),
        self_confidence: this.debtConfidence(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.debtTakeaway.set('');
          this.refreshWorkspace();
        },
      });
  }

  openFinalizeModal(earlyStop: boolean): void {
    this.sessionService.clearError();
    this.isEarlyStop.set(earlyStop);
    this.earlyStopConfirmed.set(!earlyStop);
    this.completedTaskIds.set(earlyStop ? [] : [...this.sessionService.activeTaskIds()]);
    this.finalizeTakeaway.set('');
    this.finalizeConfidence.set(4);
    this.checkinTimeSufficiency.set('JUST_RIGHT');
    this.checkinDifficulty.set(3);
    this.checkinFocusLevel.set(4);
    this.finalizeModalOpen.set(true);
  }

  closeFinalizeModal(): void {
    this.finalizeModalOpen.set(false);
    this.sessionService.clearError();
  }

  onEscape(): void {
    if (this.finalizeModalOpen()) {
      this.closeFinalizeModal();
    }
  }

  toggleCompletedTask(taskId: string): void {
    this.completedTaskIds.update((ids) =>
      ids.includes(taskId) ? ids.filter((id) => id !== taskId) : [...ids, taskId]
    );
  }

  submitFinalize(): void {
    if (this.isEarlyStop() && !this.earlyStopConfirmed()) return;
    if (!this.finalizeTakeawayCheck().isValid) return;

    this.sessionService
      .finalizeSession({
        early_stop: this.isEarlyStop(),
        completed_task_ids: this.completedTaskIds(),
        takeaway: this.finalizeTakeaway().trim(),
        self_confidence: this.finalizeConfidence(),
        scratchpad_content: this.sessionService.scratchpadNote(),
        actual_minutes: Math.max(1, this.sessionService.elapsedMinutes()),
        checkin_time_sufficiency: this.checkinTimeSufficiency(),
        checkin_perceived_difficulty: this.checkinDifficulty(),
        checkin_focus_level: this.checkinFocusLevel(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.finalizeModalOpen.set(false);
          this.refreshWorkspace();
        },
      });
  }

  getTaskResources(task: TaskResponse): Array<{ label: string; url: string | null }> {
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

  formatLocalTime(iso: string): string {
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) return iso;
    return dt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  }
}
