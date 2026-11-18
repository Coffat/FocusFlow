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
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AlertTriangle,
  Calendar,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
  Play,
  RefreshCw,
  X,
  Zap,
} from 'lucide-angular';
import {
  ScheduleService,
  formatLocalDateKey,
  formatLocalTimeRange,
  getLocalMondayIso,
} from '../services/schedule.service';
import { RoadmapResponse, WeeklyScheduleItemResponse } from '../models/schedule.model';
import { CalendarIntegrationService } from '../../../core/services/calendar-integration.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';

export type QuickActionType = 'MOVE_TODAY_TO_BACKLOG' | 'REOPTIMIZE_SCHEDULE' | 'PAUSE_ROADMAP';

function toLocalIsoDateTime(dateStr: string, timeStr: string): string | null {
  if (!dateStr || !timeStr) return null;
  const dt = new Date(`${dateStr}T${timeStr}:00`);
  if (Number.isNaN(dt.getTime())) return null;
  return dt.toISOString();
}

@Component({
  selector: 'app-schedule-page',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    LucideAngularModule,
    ButtonDirective,
    BadgeDirective,
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        Calendar,
        Check,
        ChevronLeft,
        ChevronRight,
        Clock,
        Play,
        RefreshCw,
        X,
        Zap,
      }),
    },
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '(document:keydown.escape)': 'onEscapeKey()',
  },
  template: `
    <div class="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
      <!-- Top Bar -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight text-[var(--foreground)]">
            Thời Khóa Biểu Học Tập
          </h1>
          <p class="text-xs sm:text-sm text-[var(--muted-foreground)] mt-0.5">
            Lịch học chính thức hiển thị theo múi giờ địa phương của bạn
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          @if (!calendarService.isConnected()) {
            <button
              type="button"
              appButton
              variant="outline"
              size="sm"
              [disabled]="calendarService.isLoading()"
              (click)="connectGoogleCalendar()"
              class="inline-flex items-center gap-1.5"
            >
              <svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
              </svg>
              <span>{{ calendarService.isLoading() ? 'Đang kết nối...' : 'Đồng bộ Google Calendar' }}</span>
            </button>
          } @else {
            <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-xs font-medium text-emerald-700 dark:text-emerald-400">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Google Calendar: Đã liên kết</span>
              <button
                type="button"
                (click)="disconnectGoogleCalendar()"
                [disabled]="calendarService.isLoading()"
                class="ml-1 text-[11px] hover:text-red-600 underline cursor-pointer"
                title="Ngắt kết nối Google Calendar"
              >
                Ngắt
              </button>
            </div>
          }

          <button
            type="button"
            appButton
            variant="default"
            size="sm"
            data-testid="open-quick-drawer-btn"
            (click)="openQuickDrawer()"
          >
            <lucide-icon name="zap" [size]="14" aria-hidden="true"></lucide-icon>
            <span>Điều chỉnh lịch hôm nay</span>
          </button>
        </div>
      </div>

      <!-- Drawer / Action Success Notice -->
      @if (drawerSuccess(); as notice) {
        <div
          role="status"
          data-testid="quick-drawer-notification"
          class="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs sm:text-sm text-emerald-900 dark:text-emerald-200 font-medium flex flex-col sm:flex-row sm:items-center justify-between gap-2"
        >
          <div class="flex items-center gap-2">
            <lucide-icon name="check" [size]="15" class="shrink-0 text-emerald-600" aria-hidden="true"></lucide-icon>
            <span>{{ notice.message }}</span>
            @if (notice.roadmapId) {
              <a
                [routerLink]="['/roadmaps', notice.roadmapId]"
                class="underline font-semibold text-[var(--primary)] ml-1"
              >
                Xem &amp; Áp dụng đề xuất &rarr;
              </a>
            }
          </div>
          <button type="button" (click)="drawerSuccess.set(null)" class="text-xs hover:underline self-end sm:self-auto cursor-pointer">
            Đóng
          </button>
        </div>
      }

      <!-- Page Error Banner -->
      @if (pageError(); as err) {
        <div
          role="alert"
          data-testid="schedule-error-banner"
          class="p-4 rounded-xl border border-red-500/40 bg-red-500/10 text-red-900 dark:text-red-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div class="text-xs sm:text-sm space-y-0.5">
            <div class="font-bold flex items-center gap-1.5">
              <lucide-icon name="alert-triangle" [size]="14" aria-hidden="true"></lucide-icon>
              <span>{{ err.message }}</span>
              @if (err.code) {
                <span class="font-mono px-1.5 py-0.5 rounded bg-red-500/15 text-[11px]">{{ err.code }}</span>
              }
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button type="button" appButton variant="outline" size="sm" (click)="reloadCurrentWeek()">Thử lại</button>
            <button type="button" appButton variant="ghost" size="sm" (click)="scheduleService.clearError()">Đóng</button>
          </div>
        </div>
      }

      <!-- Week Navigation Toolbar -->
      <div class="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl border border-[var(--border)] bg-[var(--card)]">
        <div class="flex items-center gap-2">
          <button
            type="button"
            appButton
            variant="outline"
            size="sm"
            data-testid="prev-week-btn"
            (click)="navigateWeek(-1)"
            aria-label="Tuần trước"
          >
            <lucide-icon name="chevron-left" [size]="15" aria-hidden="true"></lucide-icon>
            <span>Tuần trước</span>
          </button>

          <span class="px-3 py-1 text-xs sm:text-sm font-semibold text-[var(--foreground)]" data-testid="week-range-label">
            {{ weekRangeLabel() }}
          </span>

          <button
            type="button"
            appButton
            variant="outline"
            size="sm"
            data-testid="next-week-btn"
            (click)="navigateWeek(1)"
            aria-label="Tuần sau"
          >
            <span>Tuần sau</span>
            <lucide-icon name="chevron-right" [size]="15" aria-hidden="true"></lucide-icon>
          </button>
        </div>

        <div class="flex items-center gap-2">
          @if (scheduleService.weekOffset() !== 0) {
            <button type="button" appButton variant="ghost" size="sm" (click)="resetToCurrentWeek()">
              Về tuần hiện tại
            </button>
          }
          <button
            type="button"
            appButton
            variant="ghost"
            size="sm"
            [disabled]="scheduleService.isLoading()"
            (click)="reloadCurrentWeek()"
            aria-label="Làm mới lịch tuần"
          >
            <lucide-icon name="refresh-cw" [size]="14" aria-hidden="true"></lucide-icon>
          </button>
        </div>
      </div>

      <!-- Loading State -->
      @if (scheduleService.isLoading() && scheduleService.items().length === 0) {
        <div class="p-10 rounded-2xl border border-[var(--border)] bg-[var(--card)] flex flex-col items-center justify-center gap-3">
          <lucide-icon name="refresh-cw" [size]="22" class="animate-spin text-[var(--primary)]" aria-hidden="true"></lucide-icon>
          <p class="text-sm text-[var(--muted-foreground)]">Đang tải lịch học tuần...</p>
        </div>
      } @else {
        <!-- Weekly Schedule Grouped by Local Day -->
        @if (scheduleService.dayGroups().length === 0) {
          <div class="p-10 sm:p-12 text-center flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--card)]">
            <div class="w-12 h-12 rounded-2xl bg-[var(--muted)] text-[var(--muted-foreground)] flex items-center justify-center mb-3">
              <lucide-icon name="calendar" [size]="24" aria-hidden="true"></lucide-icon>
            </div>
            <h2 class="text-base font-semibold text-[var(--foreground)] mb-1">
              Chưa có buổi học nào trong tuần
            </h2>
            <p class="text-xs sm:text-sm text-[var(--muted-foreground)] max-w-md mb-5 leading-relaxed">
              Bạn chưa có lịch học nào được xếp trong tuần này. Hãy tạo một Lộ trình học tập mới với AI hoặc cấu hình khung giờ rảnh để hệ thống tự động điều phối.
            </p>
            <div class="flex flex-wrap items-center justify-center gap-3">
              <a routerLink="/roadmaps" appButton variant="default" size="sm" class="no-underline">
                Tạo Lộ trình mới với AI
              </a>
              <a routerLink="/availability" appButton variant="outline" size="sm" class="no-underline">
                Cấu hình Giờ rảnh
              </a>
            </div>
          </div>
        } @else {
          <div class="space-y-5">
            @for (group of scheduleService.dayGroups(); track group.localDate) {
              <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-xs">
                <header
                  class="px-4 sm:px-5 py-3 border-b border-[var(--border)] flex items-center justify-between gap-2"
                  [class]="group.isToday ? 'bg-[var(--primary)]/10' : 'bg-[var(--muted)]/50'"
                >
                  <div class="flex items-center gap-2">
                    <h2 class="text-sm sm:text-base font-bold text-[var(--foreground)]">
                      {{ group.dayLabel }}
                    </h2>
                    @if (group.isToday) {
                      <span appBadge variant="default" class="text-[10px]">Hôm nay</span>
                    }
                  </div>
                  <span class="text-xs text-[var(--muted-foreground)] font-mono">
                    {{ group.items.length }} khung giờ
                  </span>
                </header>

                <div class="divide-y divide-[var(--border)]">
                  @for (item of group.items; track item.block_id) {
                    <div
                      data-testid="schedule-block-item"
                      class="p-4 sm:px-5 flex flex-col md:flex-row md:items-center justify-between gap-3"
                    >
                      <div class="flex items-start sm:items-center gap-3.5 min-w-0">
                        <div class="px-2.5 py-1.5 rounded-lg bg-[var(--muted)] font-mono text-xs font-bold text-[var(--foreground)] shrink-0">
                          {{ formatTimeRange(item.start_time, item.end_time) }}
                        </div>

                        <div class="min-w-0 space-y-1">
                          <div class="flex flex-wrap items-center gap-2">
                            <span class="font-semibold text-sm text-[var(--foreground)]">
                              {{ item.task?.title ?? item.roadmap_title }}
                            </span>

                            @if (item.block_status === 'COMPLETED' || item.task?.status === 'COMPLETED') {
                              <span appBadge variant="success">Đã hoàn thành</span>
                            } @else if (item.block_status === 'CANCELLED') {
                              <span appBadge variant="outline">Đã hủy</span>
                            } @else {
                              <span appBadge variant="outline">{{ item.block_status }}</span>
                            }

                            @if (item.task?.is_overdue) {
                              <span appBadge variant="destructive">Quá hạn</span>
                            }
                            @if (item.task?.is_blocked) {
                              <span appBadge variant="outline" class="border-amber-500 text-amber-700 dark:text-amber-300">
                                Bị chặn
                              </span>
                            }
                            @if (item.task?.is_stalled || (item.task?.reschedule_count ?? 0) >= 3) {
                              <span appBadge variant="outline" class="border-purple-500 text-purple-700 dark:text-purple-300">
                                Đình trệ ({{ item.task?.reschedule_count ?? 3 }} lần)
                              </span>
                            }
                          </div>

                          <div class="text-xs text-[var(--muted-foreground)] flex flex-wrap items-center gap-2">
                            <span>{{ item.roadmap_title }}</span>
                            <span>&bull;</span>
                            <span class="inline-flex items-center gap-1 font-mono">
                              <lucide-icon name="clock" [size]="11" aria-hidden="true"></lucide-icon>
                              {{ item.scheduled_duration_minutes }} phút
                            </span>
                            @if (item.placement_rationale) {
                              <span>&bull;</span>
                              <span class="truncate max-w-md">{{ item.placement_rationale }}</span>
                            }
                          </div>
                        </div>
                      </div>

                      <div class="flex flex-wrap items-center gap-2 shrink-0">
                        @if (
                          item.task_id &&
                          item.block_status !== 'COMPLETED' &&
                          item.block_status !== 'CANCELLED' &&
                          item.task?.status !== 'COMPLETED'
                        ) {
                          <a
                            [routerLink]="['/workspace']"
                            [queryParams]="{ taskId: item.task_id }"
                            appButton
                            variant="default"
                            size="sm"
                            class="no-underline"
                          >
                            <lucide-icon name="play" [size]="13" aria-hidden="true"></lucide-icon>
                            <span>Vào học</span>
                          </a>

                          <button
                            type="button"
                            appButton
                            variant="outline"
                            size="sm"
                            (click)="openRescheduleModal(item)"
                          >
                            Dời lịch
                          </button>
                        }
                      </div>
                    </div>
                  }
                </div>
              </section>
            }
          </div>
        }
      }
    </div>

    <!-- Quick Reschedule / Move to Backlog Modal -->
    @if (reschedulingItem(); as blockItem) {
      <div
        class="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs"
        (click)="closeRescheduleModal()"
        aria-hidden="true"
      ></div>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="schedule-reschedule-title"
        data-testid="schedule-reschedule-dialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
      >
        <div
          class="pointer-events-auto w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] shadow-2xl p-5 sm:p-6 space-y-4"
          (click)="$event.stopPropagation()"
        >
          <div class="flex items-start justify-between gap-2 border-b border-[var(--border)] pb-3">
            <div>
              <h2 id="schedule-reschedule-title" class="text-base font-bold">
                Dời lịch nhiệm vụ
              </h2>
              <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
                {{ blockItem.task?.title ?? blockItem.roadmap_title }}
              </p>
            </div>
            <button type="button" appButton variant="ghost" size="icon" (click)="closeRescheduleModal()" aria-label="Đóng">
              <lucide-icon name="x" [size]="18" aria-hidden="true"></lucide-icon>
            </button>
          </div>

          @if (modalError(); as mErr) {
            <div
              role="alert"
              data-testid="schedule-reschedule-error"
              class="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-xs text-red-900 dark:text-red-200 space-y-1"
            >
              @if (mErr.code) {
                <div class="font-mono font-bold">{{ mErr.code }}</div>
              }
              <div>{{ mErr.message }}</div>
              @if (mErr.violations.length > 0) {
                <ul class="list-disc list-inside space-y-0.5 pt-1">
                  @for (v of mErr.violations; track $index) {
                    <li>{{ v }}</li>
                  }
                </ul>
              }
            </div>
          }

          @if (blockItem.task?.is_stalled || (blockItem.task?.reschedule_count ?? 0) >= 3) {
            <div class="p-3 rounded-xl border border-purple-500/40 bg-purple-500/10 text-xs space-y-2">
              <div class="font-bold">Nhiệm vụ đang đình trệ (STALLED)</div>
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  [checked]="allowStalledCommitment()"
                  (change)="allowStalledCommitment.set($any($event.target).checked)"
                  class="h-4 w-4 accent-[var(--primary)]"
                />
                <span>Tôi cam kết hoàn thành nhiệm vụ ở khung giờ mới</span>
              </label>
            </div>
          }

          <div class="space-y-3">
            <div class="space-y-1">
              <label for="sched-reschedule-date" class="block text-xs font-semibold">Ngày mới</label>
              <input
                id="sched-reschedule-date"
                type="date"
                [ngModel]="rescheduleDate()"
                (ngModelChange)="rescheduleDate.set($event)"
                class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1">
                <label for="sched-reschedule-start" class="block text-xs font-semibold">Giờ bắt đầu</label>
                <input
                  id="sched-reschedule-start"
                  type="time"
                  [ngModel]="rescheduleStart()"
                  (ngModelChange)="rescheduleStart.set($event)"
                  class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                />
              </div>
              <div class="space-y-1">
                <label for="sched-reschedule-end" class="block text-xs font-semibold">Giờ kết thúc</label>
                <input
                  id="sched-reschedule-end"
                  type="time"
                  [ngModel]="rescheduleEnd()"
                  (ngModelChange)="rescheduleEnd.set($event)"
                  class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                />
              </div>
            </div>
            <div class="space-y-1">
              <label for="sched-reschedule-reason" class="block text-xs font-semibold">Lý do (tùy chọn)</label>
              <input
                id="sched-reschedule-reason"
                type="text"
                [ngModel]="rescheduleReason()"
                (ngModelChange)="rescheduleReason.set($event)"
                placeholder="Ví dụ: Bận họp đột xuất"
                class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
              />
            </div>

            <label class="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                [checked]="confirmSoftOverflow()"
                (change)="confirmSoftOverflow.set($any($event.target).checked)"
                class="h-4 w-4 accent-[var(--primary)]"
              />
              <span>Xác nhận Soft Overflow (&le; 30 phút) nếu cần</span>
            </label>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border)]">
            <button
              type="button"
              appButton
              variant="outline"
              size="sm"
              [disabled]="scheduleService.isSubmitting()"
              (click)="submitMoveItemToBacklog()"
            >
              Đưa về Backlog
            </button>
            <div class="flex items-center gap-2">
              <button type="button" appButton variant="ghost" size="sm" (click)="closeRescheduleModal()">Hủy</button>
              <button
                type="button"
                appButton
                variant="default"
                size="sm"
                [disabled]="scheduleService.isSubmitting() || !rescheduleDate()"
                (click)="submitRescheduleItem()"
              >
                {{ scheduleService.isSubmitting() ? 'Đang lưu...' : 'Xác nhận dời' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    }

    <!-- Quick Drawer (Điều chỉnh lịch hôm nay) -->
    @if (isDrawerOpen()) {
      <div
        class="fixed inset-0 bg-black/50 backdrop-blur-xs z-50 transition-opacity"
        (click)="closeQuickDrawer()"
        aria-hidden="true"
      ></div>

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="quick-drawer-title"
        data-testid="quick-drawer-dialog"
        class="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-[var(--card)] border-l border-[var(--border)] shadow-2xl p-6 flex flex-col justify-between overflow-y-auto"
      >
        <div class="space-y-5">
          <div class="flex items-center justify-between border-b border-[var(--border)] pb-4">
            <div>
              <h2 id="quick-drawer-title" class="text-lg font-bold text-[var(--foreground)]">
                Điều Chỉnh Lịch Hôm Nay
              </h2>
              <p class="text-xs text-[var(--muted-foreground)]">
                Thao tác trực tiếp với lịch trình hôm nay qua API hệ thống
              </p>
            </div>
            <button
              type="button"
              appButton
              variant="ghost"
              size="icon"
              (click)="closeQuickDrawer()"
              aria-label="Đóng bảng điều khiển"
            >
              <lucide-icon name="x" [size]="18" aria-hidden="true"></lucide-icon>
            </button>
          </div>

          @if (drawerError(); as dErr) {
            <div
              role="alert"
              data-testid="quick-drawer-error"
              class="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-xs text-red-900 dark:text-red-200 space-y-0.5"
            >
              @if (dErr.code) {
                <div class="font-mono font-bold">{{ dErr.code }}</div>
              }
              <div>{{ dErr.message }}</div>
            </div>
          }

          <div class="space-y-3" role="radiogroup" aria-label="Hình thức điều chỉnh">
            <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Hình thức điều chỉnh
            </span>

            <label class="flex items-start gap-3 p-3 rounded-xl border border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]/50 cursor-pointer transition-colors">
              <input
                type="radio"
                name="quickActionType"
                value="MOVE_TODAY_TO_BACKLOG"
                data-testid="action-move-backlog"
                [ngModel]="selectedActionType()"
                (ngModelChange)="selectedActionType.set($event)"
                class="mt-1 accent-[var(--primary)]"
              />
              <div class="space-y-0.5">
                <div class="text-sm font-semibold">Chuyển việc chưa xong hôm nay về Backlog</div>
                <div class="text-xs text-[var(--muted-foreground)]">
                  Đưa {{ todayIncompleteTaskIds().length }} nhiệm vụ chưa hoàn thành hôm nay về Hàng đợi Phục hồi để sắp xếp lại sau.
                </div>
              </div>
            </label>

            <label class="flex items-start gap-3 p-3 rounded-xl border border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]/50 cursor-pointer transition-colors">
              <input
                type="radio"
                name="quickActionType"
                value="REOPTIMIZE_SCHEDULE"
                data-testid="action-reoptimize"
                [ngModel]="selectedActionType()"
                (ngModelChange)="selectedActionType.set($event)"
                class="mt-1 accent-[var(--primary)]"
              />
              <div class="space-y-0.5">
                <div class="text-sm font-semibold">Tạo đề xuất tái tối ưu lịch trình (0 AI credit)</div>
                <div class="text-xs text-[var(--muted-foreground)]">
                  Sinh bản nháp đề xuất lịch mới (DRAFT) cho lộ trình để bạn kiểm tra và bấm Áp dụng (BUSR-02).
                </div>
              </div>
            </label>

            <label class="flex items-start gap-3 p-3 rounded-xl border border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]/50 cursor-pointer transition-colors">
              <input
                type="radio"
                name="quickActionType"
                value="PAUSE_ROADMAP"
                data-testid="action-pause-roadmap"
                [ngModel]="selectedActionType()"
                (ngModelChange)="selectedActionType.set($event)"
                class="mt-1 accent-[var(--primary)]"
              />
              <div class="space-y-0.5">
                <div class="text-sm font-semibold">Tạm dừng lộ trình học (Pause)</div>
                <div class="text-xs text-[var(--muted-foreground)]">
                  Tạm dừng lộ trình đang học khi bạn bận việc đột xuất nhiều ngày.
                </div>
              </div>
            </label>
          </div>

          @if (selectedActionType() !== 'MOVE_TODAY_TO_BACKLOG') {
            <div class="space-y-1.5">
              <label for="drawer-roadmap-select" class="block text-xs font-semibold">
                Chọn lộ trình áp dụng
              </label>
              <select
                id="drawer-roadmap-select"
                [ngModel]="selectedDrawerRoadmapId()"
                (ngModelChange)="selectedDrawerRoadmapId.set($event)"
                class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-2.5 text-sm"
              >
                @for (rm of activeRoadmaps(); track rm.id) {
                  <option [value]="rm.id">{{ rm.title }} ({{ rm.status }})</option>
                }
              </select>
            </div>
          }

          @if (selectedActionType() === 'MOVE_TODAY_TO_BACKLOG') {
            <div class="space-y-1.5">
              <label for="adjustment-reason" class="block text-xs font-medium text-[var(--muted-foreground)]">
                Lý do điều chỉnh (Tùy chọn):
              </label>
              <input
                id="adjustment-reason"
                data-testid="adjustment-reason-input"
                type="text"
                [ngModel]="actionReason()"
                (ngModelChange)="actionReason.set($event)"
                placeholder="Ví dụ: Tăng ca đột xuất..."
                class="flex h-9 w-full rounded-md border border-[var(--input)] bg-[var(--background)] px-3 py-1 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)]"
              />
            </div>
          }
        </div>

        <div class="pt-6 border-t border-[var(--border)] flex items-center justify-end gap-3">
          <button type="button" appButton variant="outline" (click)="closeQuickDrawer()">
            Hủy bỏ
          </button>
          <button
            type="button"
            appButton
            variant="default"
            data-testid="confirm-today-adjustment-btn"
            [disabled]="scheduleService.isSubmitting()"
            (click)="applyTodayAdjustment()"
          >
            {{ scheduleService.isSubmitting() ? 'Đang xử lý...' : 'Xác nhận điều chỉnh hôm nay' }}
          </button>
        </div>
      </div>
    }
  `,
})
export class SchedulePageComponent implements OnInit {
  readonly scheduleService = inject(ScheduleService);
  readonly calendarService = inject(CalendarIntegrationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly isDrawerOpen = signal<boolean>(false);
  readonly drawerSuccess = signal<{ message: string; roadmapId?: string } | null>(null);
  readonly localDrawerNotice = signal<string | null>(null);

  readonly selectedActionType = signal<QuickActionType>('MOVE_TODAY_TO_BACKLOG');
  readonly actionReason = signal<string>('');
  readonly selectedDrawerRoadmapId = signal<string>('');

  // Reschedule modal state
  readonly reschedulingItem = signal<WeeklyScheduleItemResponse | null>(null);
  readonly rescheduleDate = signal<string>('');
  readonly rescheduleStart = signal<string>('19:00');
  readonly rescheduleEnd = signal<string>('19:30');
  readonly rescheduleReason = signal<string>('');
  readonly allowStalledCommitment = signal<boolean>(false);
  readonly confirmSoftOverflow = signal<boolean>(false);

  readonly pageError = computed(() =>
    !this.isDrawerOpen() && !this.reschedulingItem() ? this.scheduleService.errorState() : null
  );
  readonly modalError = computed(() =>
    this.reschedulingItem() ? this.scheduleService.errorState() : null
  );
  readonly drawerError = computed(() => {
    if (!this.isDrawerOpen()) return null;
    const svcErr = this.scheduleService.errorState();
    if (svcErr) return svcErr;
    const localMsg = this.localDrawerNotice();
    return localMsg ? { code: null, message: localMsg, violations: [], isOffline: false } : null;
  });

  readonly activeRoadmaps = computed<RoadmapResponse[]>(() => {
    const all = this.scheduleService.roadmaps();
    const active = all.filter((r) => r.status === 'ACTIVE');
    return active.length > 0 ? active : all;
  });

  readonly todayIncompleteTaskIds = computed<string[]>(() => {
    const todayKey = formatLocalDateKey(new Date());
    const todayGroup = this.scheduleService.dayGroups().find((g) => g.localDate === todayKey);
    if (!todayGroup) return [];
    const ids = todayGroup.items
      .filter(
        (item) =>
          item.task_id &&
          item.block_status !== 'COMPLETED' &&
          item.block_status !== 'CANCELLED' &&
          item.task?.status !== 'COMPLETED'
      )
      .map((item) => item.task_id as string);
    return Array.from(new Set(ids));
  });

  readonly weekRangeLabel = computed(() => {
    const ws = this.scheduleService.weeklySchedule();
    if (ws) {
      return `Tuần ${ws.week_start} – ${ws.week_end}`;
    }
    return `Tuần bắt đầu ${getLocalMondayIso(this.scheduleService.weekOffset())}`;
  });

  ngOnInit(): void {
    this.calendarService.checkUrlCallback(this.route, this.router);
    this.calendarService.loadStatus().pipe(takeUntilDestroyed(this.destroyRef)).subscribe();
    this.reloadCurrentWeek();
    this.scheduleService.loadRoadmaps().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((list) => {
      const firstActive = list.find((r) => r.status === 'ACTIVE') ?? list[0];
      if (firstActive && !this.selectedDrawerRoadmapId()) {
        this.selectedDrawerRoadmapId.set(firstActive.id);
      }
    });
  }

  reloadCurrentWeek(): void {
    const weekStart = getLocalMondayIso(this.scheduleService.weekOffset());
    this.scheduleService
      .loadWeeklySchedule(weekStart)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  navigateWeek(delta: number): void {
    this.scheduleService.weekOffset.update((v) => v + delta);
    this.reloadCurrentWeek();
  }

  resetToCurrentWeek(): void {
    this.scheduleService.weekOffset.set(0);
    this.reloadCurrentWeek();
  }

  formatTimeRange(startIso: string, endIso: string): string {
    return formatLocalTimeRange(startIso, endIso);
  }

  connectGoogleCalendar(): void {
    this.calendarService.connectGoogleCalendar('/schedule');
  }

  disconnectGoogleCalendar(): void {
    if (confirm('Bạn có chắc chắn muốn ngắt kết nối Google Calendar?')) {
      this.calendarService.disconnectGoogleCalendar().pipe(takeUntilDestroyed(this.destroyRef)).subscribe();
    }
  }

  openRescheduleModal(item: WeeklyScheduleItemResponse): void {
    this.scheduleService.clearError();
    const localDate = item.task?.scheduled_date ?? item.block_date;
    this.rescheduleDate.set(localDate);
    this.rescheduleStart.set(this.extractLocalHHmm(item.start_time) || '19:00');
    this.rescheduleEnd.set(this.extractLocalHHmm(item.end_time) || '19:30');
    this.rescheduleReason.set('');
    this.allowStalledCommitment.set(false);
    this.confirmSoftOverflow.set(false);
    this.reschedulingItem.set(item);
  }

  closeRescheduleModal(): void {
    this.reschedulingItem.set(null);
    this.scheduleService.clearError();
  }

  submitRescheduleItem(): void {
    const item = this.reschedulingItem();
    const dateStr = this.rescheduleDate().trim();
    if (!item?.task_id || !dateStr) return;

    this.scheduleService
      .rescheduleTask(item.task_id, {
        scheduled_date: dateStr,
        scheduled_start: toLocalIsoDateTime(dateStr, this.rescheduleStart()),
        scheduled_end: toLocalIsoDateTime(dateStr, this.rescheduleEnd()),
        reason: this.rescheduleReason().trim() || null,
        allow_stalled_commitment: this.allowStalledCommitment(),
        confirm_soft_overflow: this.confirmSoftOverflow(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closeRescheduleModal();
          this.drawerSuccess.set({ message: 'Đã cập nhật lịch học cho nhiệm vụ.' });
          this.reloadCurrentWeek();
        },
      });
  }

  submitMoveItemToBacklog(): void {
    const item = this.reschedulingItem();
    if (!item?.task_id) return;

    this.scheduleService
      .rescheduleTask(item.task_id, {
        scheduled_date: null,
        scheduled_start: null,
        scheduled_end: null,
        reason: this.rescheduleReason().trim() || 'Chuyển về Backlog',
        allow_stalled_commitment: this.allowStalledCommitment(),
        confirm_soft_overflow: false,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closeRescheduleModal();
          this.drawerSuccess.set({ message: 'Đã chuyển nhiệm vụ về Hàng đợi Phục hồi (Backlog).' });
          this.reloadCurrentWeek();
        },
      });
  }

  openQuickDrawer(): void {
    this.scheduleService.clearError();
    this.localDrawerNotice.set(null);
    if (!this.selectedDrawerRoadmapId()) {
      const firstActive = this.activeRoadmaps()[0];
      if (firstActive) {
        this.selectedDrawerRoadmapId.set(firstActive.id);
      }
    }
    this.isDrawerOpen.set(true);
  }

  closeQuickDrawer(): void {
    this.isDrawerOpen.set(false);
    this.localDrawerNotice.set(null);
    this.scheduleService.clearError();
  }

  onEscapeKey(): void {
    if (this.reschedulingItem()) {
      this.closeRescheduleModal();
    } else if (this.isDrawerOpen()) {
      this.closeQuickDrawer();
    }
  }

  applyTodayAdjustment(): void {
    this.scheduleService.clearError();
    this.localDrawerNotice.set(null);

    const action = this.selectedActionType();
    if (action === 'MOVE_TODAY_TO_BACKLOG') {
      const taskIds = this.todayIncompleteTaskIds();
      if (taskIds.length === 0) {
        this.localDrawerNotice.set('Không có nhiệm vụ chưa hoàn thành nào trong hôm nay để chuyển về Backlog.');
        return;
      }
      this.scheduleService
        .moveTasksToBacklog(taskIds, this.actionReason().trim() || null)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.closeQuickDrawer();
            this.drawerSuccess.set({
              message: `Đã chuyển ${taskIds.length} nhiệm vụ chưa xong hôm nay về Hàng đợi Phục hồi (Backlog).`,
            });
            this.reloadCurrentWeek();
          },
        });
      return;
    }

    const roadmapId = this.selectedDrawerRoadmapId();
    if (!roadmapId) {
      this.localDrawerNotice.set('Vui lòng chọn một lộ trình học tập.');
      return;
    }

    if (action === 'REOPTIMIZE_SCHEDULE') {
      this.scheduleService
        .reoptimizeRoadmapSchedule(roadmapId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.closeQuickDrawer();
            this.drawerSuccess.set({
              message: 'Đã tạo bản nháp tái tối ưu lịch trình (DRAFT).',
              roadmapId,
            });
          },
        });
      return;
    }

    if (action === 'PAUSE_ROADMAP') {
      this.scheduleService
        .pauseRoadmap(roadmapId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (rm) => {
            this.closeQuickDrawer();
            this.drawerSuccess.set({
              message: `Đã tạm dừng lộ trình "${rm.title}".`,
            });
            this.reloadCurrentWeek();
            this.scheduleService.loadRoadmaps().pipe(takeUntilDestroyed(this.destroyRef)).subscribe();
          },
        });
    }
  }

  private extractLocalHHmm(iso: string | null | undefined): string {
    if (!iso) return '';
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) return '';
    return dt.toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }
}
