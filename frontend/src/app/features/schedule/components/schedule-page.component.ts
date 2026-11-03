import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ScheduleService } from '../services/schedule.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { CardComponent } from '../../../shared/ui/card/card.component';

export type QuickActionType = 'DOMINO_SHIFT' | 'TODAY_OFF' | 'EXTEND_TIME';

@Component({
  selector: 'app-schedule-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonDirective,
    BadgeDirective,
    CardComponent
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '(document:keydown.escape)': 'onEscapeKey()'
  },
  template: `
    <div class="max-w-5xl mx-auto w-full p-6 space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Thời Khóa Biểu Học Tập</h1>
          <p class="text-sm text-[var(--muted-foreground)]">Lịch trình tự động được đồng bộ với quỹ thời gian rảnh của bạn</p>
        </div>

        <div class="flex items-center gap-3">
          <button appButton variant="outline" size="sm">
            Đồng bộ WebCal (.ics)
          </button>
          <button
            type="button"
            appButton
            variant="default"
            size="sm"
            data-testid="open-quick-drawer-btn"
            (click)="openQuickDrawer()"
          >
            ⚡ Điều chỉnh lịch hôm nay
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
            <span>✅</span>
            <span>{{ drawerSuccess() }}</span>
          </div>
          <button type="button" (click)="drawerSuccess.set(null)" class="text-xs hover:underline">Đóng</button>
        </div>
      }

      <!-- WebCal Sync Box -->
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

      <!-- Weekly Slots -->
      <div class="space-y-3">
        <h2 class="text-base font-semibold">Các khung giờ học tuần này</h2>
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
export class SchedulePageComponent {
  readonly scheduleService = inject(ScheduleService);

  readonly isDrawerOpen = signal<boolean>(false);
  readonly drawerSuccess = signal<string | null>(null);

  readonly selectedActionType = signal<QuickActionType>('DOMINO_SHIFT');
  readonly actionReason = signal<string>('');

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
