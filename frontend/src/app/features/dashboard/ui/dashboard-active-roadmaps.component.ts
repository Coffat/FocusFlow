import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardActiveRoadmap } from '../models/dashboard.model';
import { RoadmapCardComponent } from '../../../shared/components/roadmap-card/roadmap-card.component';

@Component({
  selector: 'app-dashboard-active-roadmaps',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RoadmapCardComponent],
  template: `
    <div class="bg-white border border-[#DCDCDC] rounded-xl p-5 shadow-xs">
      <!-- Section Header -->
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[20px] text-emerald-800" aria-hidden="true">alt_route</span>
          <h3 class="font-bold text-base text-neutral-900 font-serif">
            Lộ trình Đang theo đuổi
          </h3>
        </div>
        <a
          routerLink="/roadmaps"
          class="inline-flex items-center gap-1 text-xs font-semibold text-emerald-800 hover:text-emerald-950 transition-colors no-underline"
        >
          <span class="material-symbols-outlined text-[16px]" aria-hidden="true">add</span>
          <span>Tạo lộ trình mới</span>
        </a>
      </div>

      <!-- Roadmap Cards List -->
      <div class="space-y-3.5">
        @for (roadmap of roadmaps(); track roadmap.id) {
          <app-roadmap-card
            [roadmap]="roadmap"
            variant="compact"
          />
        } @empty {
          <div class="p-6 text-center text-xs text-neutral-500 bg-[#FBF9F8] rounded-lg border border-dashed border-neutral-300">
            Chưa có lộ trình nào đang hoạt động.
            <a routerLink="/roadmaps" class="font-semibold text-emerald-800 ml-1 hover:underline no-underline">
              Bắt đầu tạo ngay
            </a>
          </div>
        }
      </div>
    </div>
  `,
})
export class DashboardActiveRoadmapsComponent {
  readonly roadmaps = input<DashboardActiveRoadmap[]>([]);
}
