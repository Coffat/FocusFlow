import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  AvailabilityService,
  DAYS_OF_WEEK,
  DAY_LABELS,
  calculateDurationMinutes
} from '../../../../core/services/availability.service';
import {
  AvailabilityMode,
  CalendarIntegrationMode,
  DayOfWeek,
  TimeSlotDTO
} from '../../../../core/models/availability.model';
import {
  CardComponent,
  CardHeaderDirective,
  CardTitleDirective,
  CardDescriptionDirective
} from '../../../../shared/ui/card/card.component';
import { ButtonDirective } from '../../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../../shared/ui/badge/badge.directive';
import { InputDirective } from '../../../../shared/ui/input/input.directive';

@Component({
  selector: 'app-availability-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective,
    ButtonDirective,
    BadgeDirective,
    InputDirective
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="space-y-6">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold tracking-tight">
            Cấu Hình Thời Gian Rảnh Lai (Hybrid Availability — FR-AVAIL v2.0)
          </h2>
          <p class="text-sm text-[var(--muted-foreground)]">
            Thiết lập lịch rảnh tuần lặp lại định kỳ để AI tự động tối ưu hóa và phân bổ lộ trình học tập.
          </p>
        </div>

        <!-- Mode Switcher Tabs -->
        <div
          role="tablist"
          aria-label="Chế độ cấu hình thời gian rảnh"
          class="inline-flex p-1 rounded-xl bg-[var(--muted)] border border-[var(--border)] self-start sm:self-auto"
        >
          <button
            type="button"
            role="tab"
            data-testid="mode-a-tab"
            [attr.aria-selected]="service.activeMode() === 'MODE_A'"
            (click)="setMode('MODE_A')"
            class="px-4 py-2 text-xs font-semibold rounded-lg transition-all"
            [ngClass]="service.activeMode() === 'MODE_A'
              ? 'bg-[var(--card)] text-[var(--foreground)] shadow-xs font-bold'
              : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
          >
            Chế độ A: Quỹ giờ linh hoạt
          </button>
          <button
            type="button"
            role="tab"
            data-testid="mode-b-tab"
            [attr.aria-selected]="service.activeMode() === 'MODE_B'"
            (click)="setMode('MODE_B')"
            class="px-4 py-2 text-xs font-semibold rounded-lg transition-all"
            [ngClass]="service.activeMode() === 'MODE_B'
              ? 'bg-[var(--card)] text-[var(--foreground)] shadow-xs font-bold'
              : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'"
          >
            Chế độ B: Khung giờ cố định
          </button>
        </div>
      </div>

      <!-- Loading State Skeleton / Banner -->
      @if (service.loading()) {
        <div
          aria-busy="true"
          role="status"
          data-testid="availability-loading"
          class="p-4 rounded-xl border border-[var(--border)] bg-[var(--muted)]/50 animate-pulse flex items-center gap-3 text-xs text-[var(--muted-foreground)]"
        >
          <span class="inline-block animate-spin">⏳</span>
          <span>Đang tải cấu hình thời gian rảnh của bạn...</span>
        </div>
      }

      <!-- Presets & Quick Actions Toolbar -->
      <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)] space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">
            Mẫu cấu hình gợi ý (Productivity Presets) & Tiện ích
          </span>
          <span class="text-xs text-[var(--muted-foreground)]">Nhấn để áp dụng nhanh</span>
        </div>

        <div class="flex flex-wrap gap-2.5">
          <button
            type="button"
            appButton
            variant="outline"
            size="sm"
            data-testid="preset-busy-pro"
            (click)="service.applyPreset('BUSY_PRO')"
            class="flex items-center gap-1.5"
          >
            <span>💼</span>
            <span class="font-medium">Người đi làm bận rộn</span>
            <span appBadge variant="secondary" class="ml-1 text-[10px]">13.5h/tuần</span>
          </button>

          <button
            type="button"
            appButton
            variant="outline"
            size="sm"
            data-testid="preset-uni-student"
            (click)="service.applyPreset('UNI_STUDENT')"
            class="flex items-center gap-1.5"
          >
            <span>🎓</span>
            <span class="font-medium">Sinh viên đại học</span>
            <span appBadge variant="secondary" class="ml-1 text-[10px]">15.5h/tuần</span>
          </button>

          <button
            type="button"
            appButton
            variant="outline"
            size="sm"
            data-testid="preset-bootcamper"
            (click)="service.applyPreset('BOOTCAMPER')"
            class="flex items-center gap-1.5"
          >
            <span>🚀</span>
            <span class="font-medium">Học toàn thời gian</span>
            <span appBadge variant="secondary" class="ml-1 text-[10px]">36.0h/tuần</span>
          </button>

          <div class="hidden sm:block w-px h-6 bg-[var(--border)] my-auto mx-1"></div>

          <button
            type="button"
            appButton
            variant="secondary"
            size="sm"
            data-testid="batch-copy-monday"
            (click)="service.copyMondayToWeekdays()"
            class="flex items-center gap-1.5 ml-auto sm:ml-0"
          >
            <span>📋</span>
            <span>Sao chép Thứ 2 sang T3–T6</span>
          </button>
        </div>
      </div>

      <!-- General Settings (Allowed Window & Min Session) -->
      <app-card>
        <div appCardHeader>
          <h3 appCardTitle class="text-sm font-semibold">Tùy chọn lập lịch AI chung</h3>
          <p appCardDescription class="text-xs">
            Giới hạn thời lượng phiên tập trung và khung giờ cho phép sắp xếp lịch học
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div>
            <label for="min-session-select" class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">
              Thời lượng phiên học tối thiểu (phút)
            </label>
            <select
              id="min-session-select"
              data-testid="min-session-select"
              [value]="service.minSessionMinutes()"
              (change)="onMinSessionChange($event)"
              class="flex h-9 w-full rounded-md border border-[var(--input)] bg-[var(--card)] px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)]"
            >
              <option [value]="15">15 phút (Micro-learning)</option>
              <option [value]="30">30 phút (Tiêu chuẩn Pomodoro)</option>
              <option [value]="45">45 phút (Tập trung trung bình)</option>
              <option [value]="60">60 phút (Phiên học sâu 1h)</option>
              <option [value]="90">90 phút (Deep Work 1.5h)</option>
              <option [value]="120">120 phút (Chuyên đề 2h)</option>
            </select>
          </div>

          <div>
            <label for="calendar-mode-select" class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">
              Tích hợp Lịch ngoại vi (Calendar Sync)
            </label>
            <select
              id="calendar-mode-select"
              data-testid="calendar-mode-select"
              [value]="service.calendarIntegrationMode()"
              (change)="onCalendarModeChange($event)"
              class="flex h-9 w-full rounded-md border border-[var(--input)] bg-[var(--card)] px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)]"
            >
              <option value="NONE">Chỉ dùng nội bộ (Internal Only)</option>
              <option value="EXPORT_ICS">Xuất file WebCal (.ics)</option>
              <option value="CONNECTED">Đồng bộ Google Calendar 2 chiều</option>
            </select>
          </div>
        </div>

        @if (service.activeMode() === 'MODE_A') {
          <div class="mt-4 pt-4 border-t border-[var(--border)]">
            <div class="text-xs font-medium text-[var(--muted-foreground)] mb-2">
              Khung giờ cho phép xếp lịch trong ngày (Allowed Window — Chế độ A)
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label for="allowed-window-start" class="block text-xs text-[var(--muted-foreground)] mb-1">
                  Giờ bắt đầu sớm nhất
                </label>
                <input
                  id="allowed-window-start"
                  data-testid="allowed-window-start"
                  type="time"
                  appInput
                  [value]="service.allowedWindow().start"
                  (change)="onAllowedWindowChange('start', $event)"
                  class="h-9 w-full text-xs font-mono"
                />
              </div>
              <div>
                <label for="allowed-window-end" class="block text-xs text-[var(--muted-foreground)] mb-1">
                  Giờ kết thúc muộn nhất
                </label>
                <input
                  id="allowed-window-end"
                  data-testid="allowed-window-end"
                  type="time"
                  appInput
                  [value]="service.allowedWindow().end"
                  (change)="onAllowedWindowChange('end', $event)"
                  class="h-9 w-full text-xs font-mono"
                />
              </div>
            </div>
          </div>
        }
      </app-card>

      <!-- 7 Days Grid -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-base font-semibold">
            @if (service.activeMode() === 'MODE_A') {
              Lịch trình theo Ngày (Quỹ giờ linh hoạt)
            } @else {
              Lịch trình theo Ngày (Các khung giờ cố định)
            }
          </h3>
          <span class="text-xs text-[var(--muted-foreground)]">
            Chuyển công tắc để Bật hoặc Tắt ngày nghỉ
          </span>
        </div>

        <div class="space-y-3">
          @for (day of daysOfWeek; track day) {
            @let dayData = service.weeklySchedule()[day];
            @let dayErrors = service.dailyErrors()[day];

            <div
              [attr.data-testid]="'day-card-' + day"
              class="p-4 rounded-xl border transition-all"
              [ngClass]="{
                'border-[var(--border)] bg-[var(--card)]': dayData.enabled && dayErrors.length === 0,
                'border-destructive/60 bg-destructive/5': dayData.enabled && dayErrors.length > 0,
                'border-dashed border-[var(--border)] bg-[var(--muted)]/40 opacity-70': !dayData.enabled
              }"
            >
              <!-- Day Header Row -->
              <div class="flex items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                  <button
                    type="button"
                    role="switch"
                    [attr.data-testid]="'toggle-day-' + day"
                    [attr.aria-checked]="dayData.enabled"
                    [attr.aria-label]="'Bật lịch học cho ' + dayLabels[day]"
                    (click)="service.toggleDayEnabled(day)"
                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
                    [ngClass]="dayData.enabled ? 'bg-[var(--primary)]' : 'bg-[var(--muted)] border-[var(--border)]'"
                  >
                    <span
                      class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out"
                      [ngClass]="dayData.enabled ? 'translate-x-5' : 'translate-x-0'"
                    ></span>
                  </button>

                  <div>
                    <span class="font-semibold text-sm">{{ dayLabels[day] }}</span>
                    @if (!dayData.enabled) {
                      <span class="ml-2 text-xs text-[var(--muted-foreground)]">(Đang nghỉ)</span>
                    }
                  </div>
                </div>

                <!-- Daily Summary Badge -->
                <div>
                  @if (dayData.enabled) {
                    @if (service.activeMode() === 'MODE_A') {
                      <span appBadge variant="outline" class="font-mono text-xs">
                        {{ dayData.quota_hours }} giờ/ngày
                      </span>
                    } @else {
                      <span appBadge variant="outline" class="font-mono text-xs">
                        {{ getDaySlotHours(dayData.time_slots) }} giờ ({{ dayData.time_slots.length }} khung)
                      </span>
                    }
                  } @else {
                    <span appBadge variant="secondary" class="text-xs">Đang nghỉ</span>
                  }
                </div>
              </div>

              <!-- Day Content when Enabled -->
              @if (dayData.enabled) {
                <div class="mt-4 pt-3 border-t border-[var(--border)]">
                  <!-- MODE A VIEW -->
                  @if (service.activeMode() === 'MODE_A') {
                    <div class="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                      <!-- Quota Hours Slider & Stepper -->
                      <div class="md:col-span-7 space-y-2">
                        <div class="flex items-center justify-between text-xs">
                          <label [attr.for]="'quota-range-' + day" class="font-medium text-[var(--muted-foreground)]">
                            Quỹ thời gian học trong ngày:
                          </label>
                          <span class="font-mono font-bold text-sm text-[var(--primary)]">
                            {{ dayData.quota_hours }} giờ
                          </span>
                        </div>

                        <div class="flex items-center gap-3">
                          <button
                            type="button"
                            appButton
                            variant="outline"
                            size="sm"
                            [disabled]="dayData.quota_hours <= 0.5"
                            [attr.aria-label]="'Giảm quỹ giờ ' + dayLabels[day]"
                            (click)="adjustDayQuota(day, -0.5)"
                            class="h-9 w-9 min-h-9 min-w-9 p-0"
                          >
                            -
                          </button>

                          <input
                            [id]="'quota-range-' + day"
                            [attr.data-testid]="'quota-range-' + day"
                            type="range"
                            min="0.5"
                            max="14.0"
                            step="0.5"
                            [value]="dayData.quota_hours"
                            (input)="onQuotaRangeInput(day, $event)"
                            class="w-full accent-[var(--primary)] cursor-pointer"
                          />

                          <button
                            type="button"
                            appButton
                            variant="outline"
                            size="sm"
                            [disabled]="dayData.quota_hours >= 14.0"
                            [attr.aria-label]="'Tăng quỹ giờ ' + dayLabels[day]"
                            (click)="adjustDayQuota(day, 0.5)"
                            class="h-9 w-9 min-h-9 min-w-9 p-0"
                          >
                            +
                          </button>
                        </div>

                        <!-- Quick Quota Chips -->
                        <div class="flex items-center gap-1.5 pt-1">
                          <span class="text-[11px] text-[var(--muted-foreground)]">Nhanh:</span>
                          @for (q of [1.0, 1.5, 2.0, 3.5, 4.0]; track q) {
                            <button
                              type="button"
                              [attr.aria-pressed]="dayData.quota_hours === q"
                              (click)="service.updateDayQuota(day, q)"
                              class="px-2 py-0.5 rounded text-[11px] border border-[var(--border)] hover:bg-[var(--muted)]"
                              [ngClass]="dayData.quota_hours === q ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-transparent' : ''"
                            >
                              {{ q }}h
                            </button>
                          }
                        </div>
                      </div>

                      <!-- Preferred Period Selection -->
                      <div class="md:col-span-5 space-y-2">
                        <span class="block text-xs font-medium text-[var(--muted-foreground)]">
                          Buổi học ưu tiên:
                        </span>
                        <div class="grid grid-cols-2 gap-1.5" role="group" [attr.aria-label]="'Buổi học ưu tiên ' + dayLabels[day]">
                          <button
                            type="button"
                            [attr.data-testid]="'period-MORNING-' + day"
                            [attr.aria-pressed]="dayData.preferred_period === 'MORNING'"
                            (click)="service.updateDayPeriod(day, 'MORNING')"
                            class="px-2.5 py-1.5 rounded-lg text-xs font-medium border text-left flex items-center gap-1.5 transition-colors"
                            [ngClass]="dayData.preferred_period === 'MORNING'
                              ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)] font-semibold'
                              : 'border-[var(--border)] hover:bg-[var(--muted)]'"
                          >
                            <span>🌅</span> <span>Sáng</span>
                          </button>

                          <button
                            type="button"
                            [attr.data-testid]="'period-AFTERNOON-' + day"
                            [attr.aria-pressed]="dayData.preferred_period === 'AFTERNOON'"
                            (click)="service.updateDayPeriod(day, 'AFTERNOON')"
                            class="px-2.5 py-1.5 rounded-lg text-xs font-medium border text-left flex items-center gap-1.5 transition-colors"
                            [ngClass]="dayData.preferred_period === 'AFTERNOON'
                              ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)] font-semibold'
                              : 'border-[var(--border)] hover:bg-[var(--muted)]'"
                          >
                            <span>☀️</span> <span>Chiều</span>
                          </button>

                          <button
                            type="button"
                            [attr.data-testid]="'period-EVENING-' + day"
                            [attr.aria-pressed]="dayData.preferred_period === 'EVENING'"
                            (click)="service.updateDayPeriod(day, 'EVENING')"
                            class="px-2.5 py-1.5 rounded-lg text-xs font-medium border text-left flex items-center gap-1.5 transition-colors"
                            [ngClass]="dayData.preferred_period === 'EVENING'
                              ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)] font-semibold'
                              : 'border-[var(--border)] hover:bg-[var(--muted)]'"
                          >
                            <span>🌙</span> <span>Tối</span>
                          </button>

                          <button
                            type="button"
                            [attr.data-testid]="'period-ANY-' + day"
                            [attr.aria-pressed]="dayData.preferred_period === 'ANY' || !dayData.preferred_period"
                            (click)="service.updateDayPeriod(day, 'ANY')"
                            class="px-2.5 py-1.5 rounded-lg text-xs font-medium border text-left flex items-center gap-1.5 transition-colors"
                            [ngClass]="dayData.preferred_period === 'ANY' || !dayData.preferred_period
                              ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)] font-semibold'
                              : 'border-[var(--border)] hover:bg-[var(--muted)]'"
                          >
                            <span>🔄</span> <span>Linh hoạt</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  }

                  <!-- MODE B VIEW -->
                  @if (service.activeMode() === 'MODE_B') {
                    <div class="space-y-3">
                      @for (slot of dayData.time_slots; track $index) {
                        @let slotIndex = $index;
                        @let durationMin = getSlotDuration(slot);

                        <div
                          [attr.data-testid]="'slot-row-' + day + '-' + slotIndex"
                          class="flex flex-wrap items-center gap-2.5 p-2 rounded-lg bg-[var(--muted)]/50 border border-[var(--border)]"
                        >
                          <span class="text-xs font-mono font-bold text-[var(--muted-foreground)] w-5">
                            #{{ slotIndex + 1 }}
                          </span>

                          <div class="flex items-center gap-1.5">
                            <input
                              type="time"
                              appInput
                              [attr.data-testid]="'slot-start-' + day + '-' + slotIndex"
                              [value]="slot.start"
                              (change)="onSlotFieldChange(day, slotIndex, 'start', $event)"
                              class="h-8 w-24 text-xs font-mono"
                              [attr.aria-label]="'Giờ bắt đầu khung ' + (slotIndex + 1) + ' ' + dayLabels[day]"
                            />
                            <span class="text-xs text-[var(--muted-foreground)]">→</span>
                            <input
                              type="time"
                              appInput
                              [attr.data-testid]="'slot-end-' + day + '-' + slotIndex"
                              [value]="slot.end"
                              (change)="onSlotFieldChange(day, slotIndex, 'end', $event)"
                              class="h-8 w-24 text-xs font-mono"
                              [attr.aria-label]="'Giờ kết thúc khung ' + (slotIndex + 1) + ' ' + dayLabels[day]"
                            />
                          </div>

                          <label class="inline-flex items-center gap-1 text-xs text-[var(--muted-foreground)] cursor-pointer select-none">
                            <input
                              type="checkbox"
                              [attr.data-testid]="'slot-offset-' + day + '-' + slotIndex"
                              [checked]="slot.end_day_offset === 1"
                              (change)="onSlotOffsetChange(day, slotIndex, $event)"
                              class="rounded border-[var(--input)]"
                            />
                            <span>+1 ngày (qua đêm)</span>
                          </label>

                          <div class="ml-auto flex items-center gap-2">
                            <span
                              appBadge
                              [variant]="durationMin >= 30 ? 'outline' : 'destructive'"
                              class="font-mono text-xs"
                            >
                              {{ durationMin }} phút
                            </span>

                            <button
                              type="button"
                              appButton
                              variant="ghost"
                              size="sm"
                              [attr.data-testid]="'remove-slot-' + day + '-' + slotIndex"
                              (click)="service.removeTimeSlot(day, slotIndex)"
                              class="h-9 w-9 min-h-9 min-w-9 p-0 text-[var(--destructive)] hover:bg-[var(--destructive)]/10"
                              [attr.aria-label]="'Xóa khung giờ ' + (slotIndex + 1) + ' ' + dayLabels[day]"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      }

                      <div class="pt-1">
                        <button
                          type="button"
                          appButton
                          variant="outline"
                          size="sm"
                          [attr.data-testid]="'add-slot-' + day"
                          (click)="service.addTimeSlot(day)"
                          class="text-xs"
                        >
                          + Thêm khung giờ
                        </button>
                      </div>
                    </div>
                  }

                  <!-- Daily Error Messages -->
                  @if (dayErrors.length > 0) {
                    <div
                      role="alert"
                      [attr.data-testid]="'day-errors-' + day"
                      class="mt-2 text-xs text-[var(--destructive)] font-medium space-y-0.5"
                    >
                      @for (err of dayErrors; track err) {
                        <p class="flex items-center gap-1">
                          <span>⚠️</span> <span>{{ err }}</span>
                        </p>
                      }
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>
      </div>

      <!-- Footer Action & Validation Bar (Sticky) -->
      <div class="sticky bottom-4 z-10 p-4 rounded-xl border border-[var(--border)] bg-[var(--card)]/95 backdrop-blur shadow-lg space-y-3">
        <!-- Error / Success Alert Messages -->
        @if (service.errorMessage()) {
          <div role="alert" class="p-3 rounded-lg bg-[var(--destructive)]/10 border border-[var(--destructive)]/30 text-xs text-[var(--destructive)] font-medium flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span>❌</span>
              <span>{{ service.errorMessage() }}</span>
            </div>
            <button type="button" (click)="clearError()" class="text-xs hover:underline">Đóng</button>
          </div>
        }

        @if (service.saveSuccessMessage()) {
          <div
            role="status"
            data-testid="save-success-banner"
            class="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-600 font-medium flex items-center justify-between"
          >
            <div class="flex items-center gap-2">
              <span>✅</span>
              <span>{{ service.saveSuccessMessage() }}</span>
            </div>
            <button type="button" (click)="clearSuccess()" class="text-xs hover:underline">Đóng</button>
          </div>
        }

        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <!-- Total Hours & Status Badge -->
          <div class="flex items-center gap-3">
            <div>
              <div class="text-xs text-[var(--muted-foreground)]">Tổng quỹ thời gian tuần:</div>
              <div data-testid="total-weekly-hours" class="text-lg font-bold font-mono text-[var(--foreground)]">
                {{ service.totalWeeklyHours().toFixed(1) }} giờ / tuần
              </div>
            </div>

            @if (service.isWeeklyValid()) {
              <span appBadge variant="success" data-testid="weekly-valid-badge" class="text-xs">
                ✓ Đạt chuẩn (≥ 1.0h/tuần)
              </span>
            } @else {
              <span appBadge variant="destructive" data-testid="weekly-invalid-badge" class="text-xs">
                @if (service.totalWeeklyHours() < 1.0) {
                  Cần tối thiểu 1.0 giờ/tuần
                } @else {
                  Chưa hợp lệ
                }
              </span>
            }
          </div>

          <!-- Save Button -->
          <button
            type="button"
            appButton
            variant="default"
            size="lg"
            data-testid="save-availability-btn"
            [disabled]="!service.isWeeklyValid() || service.saving()"
            (click)="service.saveMyAvailability()"
            class="w-full sm:w-auto"
          >
            @if (service.saving()) {
              <span class="inline-block animate-spin mr-2">⏳</span>
              <span>Đang lưu...</span>
            } @else {
              <span>Lưu cấu hình thời gian rảnh</span>
            }
          </button>
        </div>
      </div>
    </div>
  `
})
export class AvailabilityConfigComponent implements OnInit {
  readonly service = inject(AvailabilityService);

  readonly daysOfWeek = DAYS_OF_WEEK;
  readonly dayLabels = DAY_LABELS;

  ngOnInit(): void {
    this.service.loadMyAvailability();
  }

  setMode(mode: AvailabilityMode): void {
    this.service.setMode(mode);
  }

  onMinSessionChange(event: Event): void {
    const val = Number((event.target as HTMLSelectElement).value);
    this.service.setMinSessionMinutes(val);
  }

  onCalendarModeChange(event: Event): void {
    const val = (event.target as HTMLSelectElement).value as CalendarIntegrationMode;
    this.service.setCalendarIntegrationMode(val);
  }

  onAllowedWindowChange(field: 'start' | 'end', event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    const current = this.service.allowedWindow();
    if (field === 'start') {
      this.service.setAllowedWindow(val, current.end);
    } else {
      this.service.setAllowedWindow(current.start, val);
    }
  }

  onQuotaRangeInput(day: DayOfWeek, event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    this.service.updateDayQuota(day, val);
  }

  adjustDayQuota(day: DayOfWeek, delta: number): void {
    const current = this.service.weeklySchedule()[day].quota_hours || 0;
    const nextVal = Math.max(0.5, Math.min(14.0, Math.round((current + delta) * 10) / 10));
    this.service.updateDayQuota(day, nextVal);
  }

  onSlotFieldChange(day: DayOfWeek, index: number, field: keyof TimeSlotDTO, event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.service.updateTimeSlot(day, index, field, val);
  }

  onSlotOffsetChange(day: DayOfWeek, index: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.service.updateTimeSlot(day, index, 'end_day_offset', checked ? 1 : 0);
  }

  getSlotDuration(slot: TimeSlotDTO): number {
    return calculateDurationMinutes(slot.start, slot.end, slot.end_day_offset);
  }

  getDaySlotHours(slots: TimeSlotDTO[]): number {
    const minutes = slots.reduce((acc, s) => acc + calculateDurationMinutes(s.start, s.end, s.end_day_offset), 0);
    return Math.round((minutes / 60) * 10) / 10;
  }

  clearError(): void {
    this.service.errorMessage.set(null);
  }

  clearSuccess(): void {
    this.service.saveSuccessMessage.set(null);
  }
}
