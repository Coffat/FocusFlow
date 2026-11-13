import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule, LUCIDE_ICONS, LucideIconProvider, Zap, Check, Calendar } from 'lucide-angular';
import { ScheduleService } from '../services/schedule.service';
import { CalendarIntegrationService } from '../../../core/services/calendar-integration.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { CardComponent } from '../../../shared/ui/card/card.component';

export type QuickActionType = 'DOMINO_SHIFT' | 'TODAY_OFF' | 'EXTEND_TIME';

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
    CardComponent
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({ Zap, Check, Calendar })
    }
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '(document:keydown.escape)': 'onEscapeKey()'
  },
  template: `
    <div class="max-w-7xl mx-auto w-full p-4 sm:p-6 lg:p-8 space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Thời Khóa Biểu Học Tập</h1>
          <p class="text-sm text-[var(--muted-foreground)]">Lịch trình tự động được đồng bộ với quỹ thời gian rảnh của bạn</p>
        </div>

        <div class="flex items-center gap-3">
          @if (!calendarService.isConnected()) {
            <button
              type="button"
              appButton
              variant="outline"
              size="sm"
              [disabled]="calendarService.isLoading()"
              (click)="connectGoogleCalendar()"
              class="inline-flex items-center gap-1.5 cursor-pointer"
            >
              <svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24">
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
                class="ml-1 text-[11px] text-muted-foreground hover:text-red-600 underline cursor-pointer"
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
            class="inline-flex items-center gap-1.5"
          >
            <lucide-icon name="zap" [size]="14" class="shrink-0" aria-hidden="true"></lucide-icon>
            <span>Điều chỉnh lịch hôm nay</span>
          </button>
        </div>
      </div>

      <!-- Quick Drawer Notification -->
      @if (drawerSuccess()) {
        <div
          role="status"
          data-testid="quick-drawer-notification"
          class="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-700 dark:text-amber-400 font-medium flex items-center justify-between shadow-xs"
        >
          <div class="flex items-center gap-2">
            <lucide-icon name="check" [size]="14" class="shrink-0 text-emerald-600" aria-hidden="true"></lucide-icon>
            <span>{{ drawerSuccess() }}</span>
          </div>
          <button type="button" (click)="drawerSuccess.set(null)" class="text-xs hover:underline">Đóng</button>
        </div>
      }

      <!-- WebCal Sync Box -->
      @if (scheduleService.webCalInfo().tokenUrl) {
        <app-card class="bg-[var(--accent)]/30 border-dashed">
          <div class="flex items-center justify-between">
            <div class="space-y-1">
              <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">Đồng bộ lịch 1 chiều (RFC 5545)</span>
              <div class="text-xs font-mono select-all bg-[var(--card)] px-3 py-1.5 rounded-md border border-[var(--border)] max-w-lg truncate">
                {{ scheduleService.webCalInfo().tokenUrl }}
              </div>
            </div>
            <button appButton variant="secondary" size="sm">Sao chép URL</button>
          </div>
        </app-card>
      }

      <!-- Weekly Slots -->
      <div class="space-y-3">
        <h2 class="text-base font-semibold">Các khung giờ học tuần này</h2>
        @if (scheduleService.weeklySlots().length === 0) {
          <div class="p-12 text-center flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--card)]">
            <div class="w-12 h-12 rounded-2xl bg-neutral-100 text-neutral-500 flex items-center justify-center mb-3">
              <lucide-icon name="calendar" [size]="24" aria-hidden="true"></lucide-icon>
            </div>
            <h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100 mb-1">
              Chưa có buổi học nào trong tuần
            </h3>
            <p class="text-xs text-[var(--muted-foreground)] max-w-sm mb-5 leading-relaxed">
              Bạn chưa có lịch học nào được xếp trong tuần này. Hãy tạo một Lộ trình học tập mới với AI hoặc cấu hình khung giờ rảnh để hệ thống tự động điều phối.
            </p>
            <div class="flex items-center gap-3">
              <a
                routerLink="/roadmaps"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#005234] text-white text-xs font-semibold hover:bg-[#246B4A] transition-colors shadow-xs no-underline"
              >
                Tạo Lộ trình mới với AI
              </a>
              <a
                routerLink="/availability"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors no-underline"
              >
                Cấu hình Giờ rảnh
              </a>
            </div>
          </div>
        } @else {
          @for (slot of scheduleService.weeklySlots(); track slot.id) {
            <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)] flex items-center justify-between shadow-xs">
              <div class="flex items-center gap-4">
                <div class="w-16 text-center py-1 rounded bg-[var(--muted)] font-mono text-xs font-bold">
                  {{ slot.startTime }}
                </div>
                <div>
                  <div class="font-medium text-sm">{{ slot.taskTitle }}</div>
                  <div class="text-xs text-[var(--muted-foreground)]">Khung giờ: {{ slot.startTime }} - {{ slot.endTime }}</div>
                </div>
              </div>

              <div class="flex items-center gap-2">
                @if (slot.isCompleted) {
                  <span appBadge variant="success">Đã hoàn thành</span>
                } @else {
                  <span appBadge variant="outline">Chưa bắt đầu</span>
                }
              </div>
            </div>
          }
        }
      </div>
    </div>

    <!-- Quick Drawer (SCR-05: In-context Adjustment §2.5 & §7.1) -->
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
              <h2 id="quick-drawer-title" class="text-lg font-bold">Điều Chỉnh Lịch Hôm Nay</h2>
              <p class="text-xs text-[var(--muted-foreground)]">Thiết lập ngoại lệ đột xuất cho ngày hiện tại</p>
            </div>
            <button
              type="button"
              appButton
              variant="ghost"
              size="sm"
              (click)="closeQuickDrawer()"
              class="h-9 w-9 min-h-9 min-w-9 p-0"
              aria-label="Đóng bảng điều khiển"
            >
              ✕
            </button>
          </div>

          <!-- Architectural Boundary Notice -->
          <div class="p-3 rounded-lg bg-[var(--muted)] border border-[var(--border)] space-y-1">
            <span appBadge variant="secondary" class="text-[10px]">Quy tắc kiến trúc §2.5 & §7.1</span>
            <p class="text-xs text-[var(--muted-foreground)] leading-relaxed">
              Thao tác này tương tác với cơ chế lập lịch thích ứng (Domino Shift) cho riêng ngày hôm nay,
              <strong class="text-[var(--foreground)]">không ghi đè khuôn mẫu tuần lặp lại</strong> trong Cài đặt chung.
            </p>
          </div>

          <!-- Action Options -->
          <div class="space-y-3" role="radiogroup" aria-label="Hình thức điều chỉnh">
            <span class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Hình thức điều chỉnh
            </span>

            <label class="flex items-start gap-3 p-3 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)]/50 cursor-pointer transition-colors">
              <input
                type="radio"
                name="quickActionType"
                value="DOMINO_SHIFT"
                data-testid="action-domino-shift"
                [ngModel]="selectedActionType()"
                (ngModelChange)="selectedActionType.set($event)"
                class="mt-1"
              />
              <div class="space-y-0.5">
                <div class="text-sm font-semibold">Dời lịch tự động (Domino Shift)</div>
                <div class="text-xs text-[var(--muted-foreground)]">
                  Chuyển các task chưa hoàn thành hôm nay sang các khung rảnh của ngày tiếp theo mà không làm tăng reschedule_count.
                </div>
              </div>
            </label>

            <label class="flex items-start gap-3 p-3 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)]/50 cursor-pointer transition-colors">
              <input
                type="radio"
                name="quickActionType"
                value="TODAY_OFF"
                data-testid="action-today-off"
                [ngModel]="selectedActionType()"
                (ngModelChange)="selectedActionType.set($event)"
                class="mt-1"
              />
              <div class="space-y-0.5">
                <div class="text-sm font-semibold">Đánh dấu nghỉ hôm nay (Pause Today)</div>
                <div class="text-xs text-[var(--muted-foreground)]">
                  Bận việc đột xuất, tạm dừng toàn bộ phiên học dự kiến hôm nay.
                </div>
              </div>
            </label>

            <label class="flex items-start gap-3 p-3 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)]/50 cursor-pointer transition-colors">
              <input
                type="radio"
                name="quickActionType"
                value="EXTEND_TIME"
                data-testid="action-extend-time"
                [ngModel]="selectedActionType()"
                (ngModelChange)="selectedActionType.set($event)"
                class="mt-1"
              />
              <div class="space-y-0.5">
                <div class="text-sm font-semibold">Tăng thêm 30 phút học hôm nay</div>
                <div class="text-xs text-[var(--muted-foreground)]">
                  Áp dụng cơ chế Soft Overflow (dung sai &le; 30 phút) cho phiên học tối nay.
                </div>
              </div>
            </label>
          </div>

          <!-- Note text area -->
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
              placeholder="Ví dụ: Tăng ca đột xuất, ôn thi đại học..."
              class="flex h-9 w-full rounded-md border border-[var(--input)] bg-[var(--card)] px-3 py-1 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)]"
            />
          </div>
        </div>

        <!-- Drawer Footer Buttons -->
        <div class="pt-6 border-t border-[var(--border)] flex items-center justify-end gap-3">
          <button
            type="button"
            appButton
            variant="outline"
            size="default"
            (click)="closeQuickDrawer()"
          >
            Hủy bỏ
          </button>
          <button
            type="button"
            appButton
            variant="default"
            size="default"
            data-testid="confirm-today-adjustment-btn"
            (click)="applyTodayAdjustment()"
          >
            Xác nhận điều chỉnh hôm nay
          </button>
        </div>
      </div>
    }
  `
})
export class SchedulePageComponent implements OnInit {
  readonly scheduleService = inject(ScheduleService);
  readonly calendarService = inject(CalendarIntegrationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly isDrawerOpen = signal<boolean>(false);
  readonly drawerSuccess = signal<string | null>(null);

  readonly selectedActionType = signal<QuickActionType>('DOMINO_SHIFT');
  readonly actionReason = signal<string>('');

  ngOnInit(): void {
    this.calendarService.checkUrlCallback(this.route, this.router);
    this.calendarService.loadStatus().subscribe();
  }

  connectGoogleCalendar(): void {
    this.calendarService.connectGoogleCalendar('/schedule');
  }

  disconnectGoogleCalendar(): void {
    if (confirm('Bạn có chắc chắn muốn ngắt kết nối Google Calendar?')) {
      this.calendarService.disconnectGoogleCalendar().subscribe();
    }
  }

  openQuickDrawer(): void {
    this.isDrawerOpen.set(true);
  }

  closeQuickDrawer(): void {
    this.isDrawerOpen.set(false);
  }

  onEscapeKey(): void {
    if (this.isDrawerOpen()) {
      this.closeQuickDrawer();
    }
  }

  applyTodayAdjustment(): void {
    const actionLabels: Record<QuickActionType, string> = {
      DOMINO_SHIFT: 'Đã kích hoạt Domino Shift: Các phiên học còn lại đã được dời sang ngày tiếp theo.',
      TODAY_OFF: 'Đã ghi nhận ngày nghỉ đột xuất hôm nay.',
      EXTEND_TIME: 'Đã bổ sung 30 phút Soft Overflow cho phiên học hôm nay.'
    };

    const reason = this.actionReason().trim();
    const baseMsg = actionLabels[this.selectedActionType()] || 'Đã áp dụng điều chỉnh thành công.';
    this.drawerSuccess.set(reason ? `${baseMsg} (Lý do: ${reason})` : baseMsg);
    this.closeQuickDrawer();
  }
}
