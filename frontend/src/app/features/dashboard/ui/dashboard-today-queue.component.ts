import { Component, ChangeDetectionStrategy, input, computed } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardTodayQueueItem } from '../models/dashboard.model';

@Component({
  selector: 'app-dashboard-today-queue',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/70 rounded-xl p-5 shadow-xs flex flex-col justify-between">
      <div>
        <!-- Section Header -->
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-[20px] text-[var(--primary,#005234)]">center_focus_strong</span>
            <h3 class="font-bold text-base text-[var(--on-surface,#1b1c1c)] font-serif">
              Hàng đợi Trọng tâm Hôm nay
            </h3>
          </div>
          <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-[var(--surface-container-high,#eae8e7)] text-[var(--secondary,#5f5e5e)]">
            {{ tasks().length }} phiên
          </span>
        </div>

        <!-- Active Focus Task Card -->
        @if (activeTask(); as active) {
          <div class="p-4 rounded-xl border-2 border-[#246B4A] bg-emerald-50/50 dark:bg-emerald-950/20 mb-4 shadow-xs">
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold bg-[#005234] text-white">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-ping"></span>
                Phiên học Hiện tại
              </span>
              <span class="text-xs font-mono font-semibold text-[#005234]">
                {{ active.scheduledTime }}
              </span>
            </div>

            <div class="mb-3">
              <div class="text-[11px] font-mono font-bold text-emerald-800 dark:text-emerald-300 mb-0.5">
                {{ active.taskId }} &bull; {{ active.roadmapTitle }}
              </div>
              <h4 class="text-base font-bold text-[var(--on-surface,#1b1c1c)] leading-snug">
                {{ active.title }}
              </h4>
              <p class="text-xs text-[var(--secondary,#5f5e5e)] mt-1">
                {{ active.milestoneTitle }} &bull; {{ active.pomodoroCount }} Pomodoro (~{{ active.durationMinutes }} phút)
              </p>
            </div>

            <a
              routerLink="/workspace"
              class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-full bg-[#005234] text-white text-xs font-bold hover:bg-[#246B4A] transition-all shadow-md group cursor-pointer"
            >
              <span class="material-symbols-outlined text-[18px]">play_arrow</span>
              <span>Vào học ngay (Start)</span>
              <span class="group-hover:translate-x-0.5 transition-transform">&rarr;</span>
            </a>
          </div>
        }

        <!-- Upcoming Tasks in Queue -->
        <div class="space-y-2.5">
          <div class="text-[11px] font-bold uppercase tracking-wider text-[var(--secondary,#5f5e5e)]">
            Kế hoạch các ca tiếp theo:
          </div>

          @for (task of upcomingTasks(); track task.id) {
            <div class="p-3 rounded-lg border border-[var(--outline-variant,#bfc9c0)]/60 bg-[var(--surface,#fbf9f8)] flex items-center justify-between gap-3 hover:border-[var(--primary,#005234)]/50 transition-colors">
              <div class="min-w-0">
                <div class="flex items-center gap-1.5 text-xs text-[var(--secondary,#5f5e5e)] mb-0.5">
                  <span class="font-mono font-semibold text-[var(--on-surface,#1b1c1c)]">{{ task.scheduledTime }}</span>
                  <span>&bull;</span>
                  <span class="font-mono text-[11px]">{{ task.taskId }}</span>
                </div>
                <div class="font-semibold text-xs text-[var(--on-surface,#1b1c1c)] truncate">
                  {{ task.title }}
                </div>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <span class="text-[11px] font-medium text-[var(--secondary,#5f5e5e)] bg-[var(--surface-container-high,#eae8e7)] px-2 py-0.5 rounded-full">
                  {{ task.pomodoroCount }}🍅
                </span>
                <a
                  routerLink="/workspace"
                  class="text-xs font-semibold text-[var(--primary,#005234)] hover:underline"
                >
                  Bắt đầu &rarr;
                </a>
              </div>
            </div>
          } @empty {
            @if (!activeTask()) {
              <div class="p-4 text-center text-xs text-[var(--secondary,#5f5e5e)] bg-[var(--surface,#fbf9f8)] rounded-lg border border-dashed border-[var(--outline-variant,#bfc9c0)]">
                Không có nhiệm vụ nào trong hàng đợi hôm nay.
              </div>
            }
          }
        </div>
      </div>
    </div>
  `
})
export class DashboardTodayQueueComponent {
  readonly tasks = input<DashboardTodayQueueItem[]>([]);

  readonly activeTask = computed(() => {
    const list = this.tasks();
    return list.find(t => t.status === 'active') || list[0] || null;
  });

  readonly upcomingTasks = computed(() => {
    const active = this.activeTask();
    if (!active) return this.tasks();
    return this.tasks().filter(t => t.id !== active.id);
  });
}
