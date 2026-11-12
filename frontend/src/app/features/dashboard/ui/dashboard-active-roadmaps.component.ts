import { Component, ChangeDetectionStrategy, input, output } from '@angular/core';
import { DashboardActiveRoadmap } from '../models/dashboard.model';
import { RoadmapCardComponent } from '../../../shared/components/roadmap-card/roadmap-card.component';

@Component({
  selector: 'app-dashboard-active-roadmaps',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RoadmapCardComponent],
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
        <button
          type="button"
          data-testid="dashboard-active-roadmaps-create-btn"
          (click)="onCreateRoadmap()"
          class="inline-flex items-center gap-1 text-xs font-semibold text-emerald-800 hover:text-emerald-950 transition-colors cursor-pointer bg-transparent border-none p-0"
        >
          <span class="material-symbols-outlined text-[16px]" aria-hidden="true">add</span>
          <span>Khởi tạo Lộ trình Mới với AI</span>
        </button>
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
            <button
              type="button"
              (click)="onCreateRoadmap()"
              class="font-semibold text-emerald-800 ml-1 hover:underline cursor-pointer bg-transparent border-none p-0"
            >
              Tạo Lộ trình Học tập Đầu tiên với AI
            </button>
          </div>
        }
      </div>
    </div>
  `,
})
export class DashboardActiveRoadmapsComponent {
  readonly roadmaps = input<DashboardActiveRoadmap[]>([]);
  readonly createRoadmap = output<void>();

  onCreateRoadmap(): void {
    this.createRoadmap.emit();
  }
}
