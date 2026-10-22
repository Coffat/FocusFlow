import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { RoadmapService } from '../services/roadmap.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { CardComponent, CardHeaderDirective, CardTitleDirective, CardDescriptionDirective } from '../../../shared/ui/card/card.component';

@Component({
  selector: 'app-roadmap-page',
  standalone: true,
  imports: [
    RouterLink,
    ButtonDirective,
    BadgeDirective,
    CardComponent
  ],
  template: `
    <div class="max-w-5xl mx-auto w-full p-6 space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span appBadge variant="success">Đang thực thi</span>
            <span class="text-xs text-[var(--muted-foreground)]">Quỹ thời gian: {{ roadmapService.currentRoadmap()?.hoursPerWeek }}h / tuần</span>
          </div>
          <h1 class="text-2xl font-bold tracking-tight">{{ roadmapService.currentRoadmap()?.title }}</h1>
          <p class="text-sm text-[var(--muted-foreground)]">Mục tiêu: {{ roadmapService.currentRoadmap()?.targetGoal }}</p>
        </div>

        <div class="flex items-center gap-3">
          <button appButton variant="outline" size="sm">
            Tạm dừng lộ trình
          </button>
          <a routerLink="/workspace" appButton variant="default" size="sm">
            Tiếp tục học
          </a>
        </div>
      </div>

      <!-- Milestones List -->
      <div class="space-y-4">
        <h2 class="text-lg font-semibold tracking-tight">Các Chặng Kiến Thức (Milestones)</h2>

        @for (milestone of roadmapService.currentRoadmap()?.milestones; track milestone.id) {
          <app-card class="hover:border-[var(--primary)]/40 transition-colors">
            <div class="flex items-start justify-between">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-mono font-semibold text-[var(--muted-foreground)]">Chặng {{ milestone.orderIndex }}</span>
                  <h3 class="text-base font-semibold">{{ milestone.title }}</h3>
                </div>
                <p class="text-xs text-[var(--muted-foreground)]">{{ milestone.description }}</p>
              </div>

              <div class="text-right space-y-1">
                <span appBadge variant="outline">{{ milestone.completedPomodoros }} / {{ milestone.totalPomodoros }} Pomodoro</span>
                <div class="text-[11px] text-[var(--muted-foreground)]">{{ milestone.tasksCount }} công việc</div>
              </div>
            </div>
          </app-card>
        }
      </div>
    </div>
  `
})
export class RoadmapPageComponent {
  readonly roadmapService = inject(RoadmapService);
}
