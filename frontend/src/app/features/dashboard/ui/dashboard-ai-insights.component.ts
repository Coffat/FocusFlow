import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardAiInsight, DashboardAdaptationStatus } from '../models/dashboard.model';

@Component({
  selector: 'app-dashboard-ai-insights',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="space-y-4">
      <!-- AI Cognitive Insight Card -->
      <div class="bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/70 rounded-xl p-5 shadow-xs relative overflow-hidden">
        <!-- Subtle Purple Accent Glow on Top Right -->
        <div class="absolute -right-8 -top-8 w-24 h-24 bg-purple-100 rounded-full blur-2xl opacity-50 pointer-events-none"></div>

        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <div class="w-7 h-7 rounded-md bg-purple-50 text-[var(--tertiary,#583878)] flex items-center justify-center">
              <span class="material-symbols-outlined text-[18px]">psychology</span>
            </div>
            <div>
              <span class="text-[10px] font-bold uppercase tracking-wider text-[var(--tertiary,#583878)]">
                Focus AI Cognitive Insight
              </span>
              <h3 class="font-bold text-sm text-[var(--on-surface,#1b1c1c)] leading-none">
                Phân tích Nhận thức & Hiệu suất
              </h3>
            </div>
          </div>
          <span class="text-[10px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
            SRL Zimmerman
          </span>
        </div>

        @if (insight(); as ins) {
          <!-- Quick Metric Indicators -->
          <div class="grid grid-cols-2 gap-2 mb-3 pt-1">
            <div class="p-2.5 rounded-lg bg-[var(--surface,#fbf9f8)] border border-[var(--outline-variant,#bfc9c0)]/40">
              <span class="text-[10px] text-[var(--secondary,#5f5e5e)] block">Khung giờ tập trung đỉnh cao</span>
              <span class="text-xs font-bold font-mono text-[var(--on-surface,#1b1c1c)]">{{ ins.peakHourRange }}</span>
            </div>
            <div class="p-2.5 rounded-lg bg-[var(--surface,#fbf9f8)] border border-[var(--outline-variant,#bfc9c0)]/40">
              <span class="text-[10px] text-[var(--secondary,#5f5e5e)] block">Tăng trưởng hiệu suất ca sáng</span>
              <span class="text-xs font-bold font-mono text-emerald-700">+{{ ins.efficiencyChange }}%</span>
            </div>
          </div>

          <!-- Summary Description -->
          <p class="text-xs text-[var(--on-surface-variant,#404942)] leading-relaxed mb-3">
            {{ ins.summary }}
          </p>

          <!-- Recommendations List -->
          <div class="space-y-1.5 pt-2 border-t border-[var(--outline-variant,#bfc9c0)]/40">
            <span class="text-[10px] font-bold uppercase tracking-wider text-[var(--secondary,#5f5e5e)] block mb-1">
              Khuyến nghị thích ứng:
            </span>
            @for (rec of ins.recommendations; track $index) {
              <div class="flex items-start gap-1.5 text-xs text-[var(--secondary,#5f5e5e)]">
                <span class="material-symbols-outlined text-[14px] text-purple-700 shrink-0 mt-0.5">check_small</span>
                <span>{{ rec }}</span>
              </div>
            }
          </div>
        }
      </div>

      <!-- Domino Shift & Adaptation Alert Card -->
      @if (adaptation(); as adapt) {
        <div class="bg-amber-50/70 border border-amber-300 rounded-xl p-4 shadow-xs">
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-[20px]">swap_horiz</span>
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2 mb-1">
                <h4 class="font-bold text-xs text-amber-950 flex items-center gap-1.5">
                  <span>Điều phối Thích ứng: Domino Shift</span>
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-600 animate-pulse"></span>
                </h4>
                <span class="text-[10px] font-semibold text-amber-800 bg-amber-100/90 px-1.5 py-0.2 rounded-xs border border-amber-300">
                  {{ adapt.affectedTasksCount }} task tự dịch chuyển
                </span>
              </div>

              <p class="text-xs text-amber-900/90 leading-relaxed mb-2">
                {{ adapt.alertMessage }}
              </p>

              <div class="flex items-center justify-between text-[11px] pt-2 border-t border-amber-200/60">
                <span class="text-amber-800 italic truncate mr-2">
                  Lý do: {{ adapt.rescheduleReason }}
                </span>
                <a
                  routerLink="/schedule"
                  class="font-semibold text-amber-900 hover:text-amber-950 hover:underline shrink-0 inline-flex items-center gap-0.5"
                >
                  Xem lịch biểu &rarr;
                </a>
              </div>
            </div>
          </div>
        </div>
      }
    </div>
  `
})
export class DashboardAiInsightsComponent {
  readonly insight = input<DashboardAiInsight | null>(null);
  readonly adaptation = input<DashboardAdaptationStatus | null>(null);
}
