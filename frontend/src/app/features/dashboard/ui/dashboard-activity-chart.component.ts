import { Component, ChangeDetectionStrategy, input, signal } from '@angular/core';
import { DayStudyDistribution } from '../models/dashboard.model';

type TimeRange = '7days' | 'october' | 'q3';

@Component({
  selector: 'app-dashboard-activity-chart',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [':host { display: block; width: 100%; }'],
  template: `
    <div class="bg-white border border-neutral-200/80 rounded-2xl p-6 shadow-xs">
      <!-- Header -->
      <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-bold text-base text-neutral-900 font-serif">
              Phân bổ giờ học theo tuần
            </h3>
            <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              <span class="material-symbols-outlined text-[13px]">trending_up</span>
              Đang tăng tốc
            </span>
          </div>
          <p class="text-xs text-neutral-500 mt-0.5">
            Dữ liệu tổng hợp tuần 42 &bull; Tháng 10 / 2026
          </p>
        </div>

        <!-- Range Toggles -->
        <div class="flex items-center gap-1 bg-neutral-100 p-0.5 rounded-xl border border-neutral-200/60 text-xs">
          <button
            type="button"
            (click)="setRange('7days')"
            class="px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer"
            [class]="activeRange() === '7days' ? 'bg-white text-neutral-900 font-semibold shadow-2xs' : 'text-neutral-500 hover:text-neutral-800'"
          >
            7 ngày qua
          </button>
          <button
            type="button"
            (click)="setRange('october')"
            class="px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer"
            [class]="activeRange() === 'october' ? 'bg-white text-neutral-900 font-semibold shadow-2xs' : 'text-neutral-500 hover:text-neutral-800'"
          >
            Tháng 10
          </button>
          <button
            type="button"
            (click)="setRange('q3')"
            class="px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer"
            [class]="activeRange() === 'q3' ? 'bg-white text-neutral-900 font-semibold shadow-2xs' : 'text-neutral-500 hover:text-neutral-800'"
          >
            Quý 3
          </button>
        </div>
      </div>

      <!-- Pill Bar Chart Container with Guidelines -->
      <div class="relative h-48 w-full flex flex-col justify-end pt-6 pb-2">
        <!-- 4.0h Dashed Guideline -->
        <div class="absolute left-0 right-0 top-6 border-b border-dashed border-neutral-200 flex items-center justify-end">
          <span class="text-[10px] font-mono text-neutral-400 bg-white pl-1 -translate-y-1/2">
            4.0h
          </span>
        </div>

        <!-- 2.0h Dashed Guideline -->
        <div class="absolute left-0 right-0 top-24 border-b border-dashed border-neutral-200 flex items-center justify-end">
          <span class="text-[10px] font-mono text-neutral-400 bg-white pl-1 -translate-y-1/2">
            2.0h
          </span>
        </div>

        <!-- 0.0h Baseline -->
        <div class="absolute left-0 right-0 bottom-8 border-b border-neutral-200/80"></div>

        <!-- 7 Columns Grid -->
        <div class="relative z-10 grid grid-cols-7 gap-2 h-36 items-end px-2">
          @for (item of distribution(); track item.day) {
            <div class="flex flex-col items-center h-full justify-end group">
              <!-- Value tooltip / label on hover or for today -->
              <span
                class="text-[10px] font-mono mb-1 transition-opacity duration-150"
                [class]="item.isToday ? 'opacity-100 font-bold text-[#246B4A]' : 'opacity-0 group-hover:opacity-100 text-neutral-500'"
              >
                {{ item.hours }}h
              </span>

              <!-- Pill Bar -->
              <div class="w-5 sm:w-7 bg-neutral-100 rounded-full h-full flex flex-col justify-end p-0.5">
                <div
                  class="w-full rounded-full transition-all duration-300"
                  [style.height.%]="getBarPercent(item.hours)"
                  [class]="item.isToday
                    ? 'shadow-xs'
                    : 'bg-neutral-200 group-hover:bg-[#246B4A]/60'"
                  [style.background-color]="item.isToday ? '#246B4A' : null"
                ></div>
              </div>

              <!-- Day Label -->
              <div class="mt-2 text-center">
                <span
                  class="text-xs transition-colors"
                  [class]="item.isToday ? 'font-bold text-[#005234]' : 'font-medium text-neutral-500'"
                >
                  {{ item.day }}
                </span>
              </div>
            </div>
          }
        </div>
      </div>
    </div>
  `
})
export class DashboardActivityChartComponent {
  readonly distribution = input<DayStudyDistribution[]>([]);

  readonly activeRange = signal<TimeRange>('october');

  setRange(range: TimeRange): void {
    this.activeRange.set(range);
  }

  getBarPercent(hours: number): number {
    // Max scale 5.0h
    return Math.min(100, Math.round((hours / 5.0) * 100));
  }
}
