import { Component, ChangeDetectionStrategy, input, computed } from '@angular/core';
import { DashboardKpi } from '../models/dashboard.model';

@Component({
  selector: 'app-dashboard-kpi-grid',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Card 1: Tổng giờ tháng -->
      <div class="bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/70 rounded-md p-4 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[var(--secondary,#5f5e5e)] mb-2">
            <span>Tổng giờ tháng</span>
            <span class="material-symbols-outlined text-[18px] text-[var(--primary,#005234)]">schedule</span>
          </div>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl lg:text-3xl font-bold text-[var(--on-surface,#1b1c1c)] tracking-tight font-sans">
              {{ kpi().monthlyHours }}
            </span>
            <span class="text-sm font-medium text-[var(--secondary,#5f5e5e)]">
              / {{ kpi().monthlyTarget }}h
            </span>
          </div>
        </div>

        <div class="mt-3 pt-3 border-t border-[var(--outline-variant,#bfc9c0)]/40 space-y-2">
          <div class="flex items-center justify-between text-xs text-[var(--secondary,#5f5e5e)]">
            <span class="font-medium text-[var(--primary-container,#246b4a)]">{{ monthlyPercent() }}% mục tiêu</span>
            <span>Cam kết {{ kpi().weeklyCommitment }}h/tuần</span>
          </div>
          <!-- Progress bar with moss color #246B4A -->
          <div class="w-full h-1.5 bg-[var(--surface-container-high,#eae8e7)] rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              style="background-color: #246B4A;"
              [style.width.%]="monthlyPercent()"
            ></div>
          </div>
        </div>
      </div>

      <!-- Card 2: Chuỗi liên tục -->
      <div class="bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/70 rounded-md p-4 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[var(--secondary,#5f5e5e)] mb-2">
            <span>Chuỗi liên tục</span>
            <span class="material-symbols-outlined text-[18px] text-amber-600">local_fire_department</span>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-2xl lg:text-3xl font-bold text-[var(--on-surface,#1b1c1c)] tracking-tight font-sans">
              {{ kpi().streakDays }} ngày
            </span>
            <span class="text-xs text-[var(--secondary,#5f5e5e)]">
              (Kỷ lục: {{ kpi().streakRecord }} ngày)
            </span>
          </div>
        </div>

        <div class="mt-3 pt-3 border-t border-[var(--outline-variant,#bfc9c0)]/40 space-y-2">
          <div class="flex items-center justify-between text-xs text-[var(--secondary,#5f5e5e)]">
            <span>7 ngày gần nhất</span>
            <span class="font-medium text-[var(--primary,#005234)]">Hôm nay: Đã học 🔥</span>
          </div>
          <!-- 7 horizontal indicator bars with first 4 active -->
          <div class="grid grid-cols-7 gap-1">
            @for (active of kpi().recentStreak; track $index) {
              <div
                class="h-2 rounded-xs transition-colors"
                [class]="active ? 'bg-[#246B4A]' : 'bg-[var(--surface-container-high,#eae8e7)]'"
                [title]="'Ngày ' + ($index + 1) + ': ' + (active ? 'Hoàn thành' : 'Chưa học')"
              ></div>
            }
          </div>
        </div>
      </div>

      <!-- Card 3: Tỷ lệ bám sát lịch -->
      <div class="bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/70 rounded-md p-4 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[var(--secondary,#5f5e5e)] mb-2">
            <span>Tỷ lệ bám sát lịch</span>
            <span class="material-symbols-outlined text-[18px] text-[var(--primary,#005234)]">track_changes</span>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-2xl lg:text-3xl font-bold text-[var(--on-surface,#1b1c1c)] tracking-tight font-sans">
              {{ kpi().adherenceRate }}%
            </span>
            <span class="inline-flex items-center gap-0.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <span class="material-symbols-outlined text-[12px]">trending_up</span>
              +{{ kpi().adherenceChange }}%
            </span>
          </div>
        </div>

        <div class="mt-3 pt-3 border-t border-[var(--outline-variant,#bfc9c0)]/40 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="inline-flex items-center gap-1 text-[var(--tertiary,#583878)] font-semibold text-[11px] bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
              <span class="material-symbols-outlined text-[13px]">auto_awesome</span>
              Adaptive AI
            </span>
            <span class="text-[var(--secondary,#5f5e5e)]">Độ chính xác cao</span>
          </div>
          <div class="w-full h-1.5 bg-[var(--surface-container-high,#eae8e7)] rounded-full overflow-hidden">
            <div
              class="h-full bg-emerald-600 rounded-full transition-all duration-300"
              [style.width.%]="kpi().adherenceRate"
            ></div>
          </div>
        </div>
      </div>

      <!-- Card 4: Pomodoro hoàn tất -->
      <div class="bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/70 rounded-md p-4 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[var(--secondary,#5f5e5e)] mb-2">
            <span>Pomodoro hoàn tất</span>
            <span class="material-symbols-outlined text-[18px] text-[var(--primary,#005234)]">timer</span>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-2xl lg:text-3xl font-bold text-[var(--on-surface,#1b1c1c)] tracking-tight font-sans">
              {{ kpi().pomodoroCompleted }} phiên
            </span>
            <span class="text-xs text-[var(--secondary,#5f5e5e)]">
              25m/phiên
            </span>
          </div>
        </div>

        <div class="mt-3 pt-3 border-t border-[var(--outline-variant,#bfc9c0)]/40 space-y-2">
          <div class="flex items-center justify-between text-xs text-[var(--secondary,#5f5e5e)]">
            <span class="font-medium text-[var(--on-surface,#1b1c1c)]">~{{ kpi().pomodoroDeepWorkHours }}h Deep Work</span>
            <span class="text-[var(--primary-container,#246b4a)] font-medium">{{ kpi().pomodoroTargetRate }}%</span>
          </div>
          <div class="w-full h-1.5 bg-[var(--surface-container-high,#eae8e7)] rounded-full overflow-hidden">
            <div
              class="h-full bg-[var(--primary-container,#246b4a)] rounded-full transition-all duration-300"
              [style.width.%]="kpi().pomodoroTargetRate"
            ></div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class DashboardKpiGridComponent {
  readonly kpi = input.required<DashboardKpi>();

  readonly monthlyPercent = computed(() => {
    const k = this.kpi();
    if (!k || !k.monthlyTarget) return 0;
    return Math.min(100, Math.round((k.monthlyHours / k.monthlyTarget) * 100));
  });
}
