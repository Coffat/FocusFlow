import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardActiveRoadmap } from '../models/dashboard.model';

@Component({
  selector: 'app-dashboard-active-roadmaps',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/70 rounded-xl p-5 shadow-xs">
      <!-- Section Header -->
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[20px] text-[var(--primary,#005234)]">alt_route</span>
          <h3 class="font-bold text-base text-[var(--on-surface,#1b1c1c)] font-serif">
            Lộ trình Đang theo đuổi
          </h3>
        </div>
        <a
          routerLink="/roadmaps"
          class="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary,#005234)] hover:text-[var(--primary-container,#246b4a)] transition-colors"
        >
          <span class="material-symbols-outlined text-[16px]">add</span>
          <span>Tạo lộ trình mới</span>
        </a>
      </div>

      <!-- Roadmap Cards List -->
      <div class="space-y-3.5">
        @for (roadmap of roadmaps(); track roadmap.id) {
          <div class="p-4 rounded-lg border border-[var(--outline-variant,#bfc9c0)]/60 bg-[var(--surface,#fbf9f8)] hover:border-[var(--primary,#005234)]/60 transition-all group">
            <div class="flex items-start justify-between gap-3 mb-2">
              <div>
                <span class="inline-block text-[10px] font-semibold uppercase tracking-wider text-[var(--secondary,#5f5e5e)] mb-0.5">
                  {{ roadmap.category }}
                </span>
                <h4 class="font-bold text-sm text-[var(--on-surface,#1b1c1c)] group-hover:text-[var(--primary,#005234)] transition-colors">
                  {{ roadmap.title }}
                </h4>
              </div>
              <span class="text-xs font-bold font-mono text-[var(--primary,#005234)] bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 shrink-0">
                {{ roadmap.progressPercentage }}%
              </span>
            </div>

            <!-- Progress Bar -->
            <div class="w-full h-1.5 bg-[var(--surface-container-high,#eae8e7)] rounded-full overflow-hidden mb-3">
              <div
                class="h-full rounded-full transition-all duration-300"
                style="background-color: #246B4A;"
                [style.width.%]="roadmap.progressPercentage"
              ></div>
            </div>

            <!-- Next Task & Meta Footer -->
            <div class="pt-2 border-t border-[var(--outline-variant,#bfc9c0)]/40 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div class="flex items-center gap-1.5 text-[var(--secondary,#5f5e5e)] min-w-0">
                <span class="material-symbols-outlined text-[14px] text-[var(--primary,#005234)] shrink-0">arrow_forward</span>
                <span class="truncate font-medium text-[var(--on-surface,#1b1c1c)]">{{ roadmap.nextTaskTitle }}</span>
              </div>

              <div class="flex items-center gap-3 text-[var(--secondary,#5f5e5e)] shrink-0">
                <span class="text-[11px]">{{ roadmap.completedTasks }}/{{ roadmap.totalTasks }} tasks &bull; Hạn: {{ roadmap.deadline }}</span>
                <a
                  routerLink="/roadmaps"
                  class="font-semibold text-[var(--primary,#005234)] hover:underline inline-flex items-center gap-0.5 text-xs"
                >
                  Chi tiết &rarr;
                </a>
              </div>
            </div>
          </div>
        } @empty {
          <div class="p-6 text-center text-xs text-[var(--secondary,#5f5e5e)] bg-[var(--surface,#fbf9f8)] rounded-lg border border-dashed border-[var(--outline-variant,#bfc9c0)]">
            Chưa có lộ trình nào đang hoạt động.
            <a routerLink="/roadmaps" class="font-semibold text-[var(--primary,#005234)] ml-1 hover:underline">
              Bắt đầu tạo ngay
            </a>
          </div>
        }
      </div>
    </div>
  `
})
export class DashboardActiveRoadmapsComponent {
  readonly roadmaps = input<DashboardActiveRoadmap[]>([]);
}
