import { Component, ChangeDetectionStrategy, input, computed } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule, LUCIDE_ICONS, LucideIconProvider, Timer } from 'lucide-angular';
import { DashboardTodayQueueItem } from '../models/dashboard.model';

@Component({
  selector: 'app-dashboard-today-queue',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LucideAngularModule],
  styles: [':host { display: block; width: 100%; }'],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({ Timer })
    }
  ],
  template: `
    <div class="bg-white border border-neutral-200/80 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
      <div>
        <!-- Section Header -->
        <div class="flex items-center justify-between mb-5">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-[20px] text-emerald-800">center_focus_strong</span>
            <h3 class="font-bold text-base text-neutral-900 font-serif">
              Hàng đợi Trọng tâm Hôm nay
            </h3>
          </div>
          <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-neutral-100 text-neutral-600 border border-neutral-200/60">
            {{ tasks().length }} phiên
          </span>
        </div>

        <!-- Active Focus Task Card -->
        @if (activeTask(); as active) {
          <div class="p-4 rounded-xl border-2 border-[#246B4A] bg-emerald-50/50 mb-4 shadow-xs">
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#005234] text-white">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-ping"></span>
                Phiên học Hiện tại
              </span>
              <span class="text-xs font-mono font-bold text-[#005234]">
                {{ active.scheduledTime }}
              </span>
            </div>

            <div class="mb-3">
              <div class="text-[11px] font-mono font-bold text-emerald-800 mb-0.5">
                {{ active.taskId }} &bull; {{ active.roadmapTitle }}
              </div>
              <h4 class="text-base font-bold text-neutral-900 leading-snug">
                {{ active.title }}
              </h4>
              <p class="text-xs text-neutral-500 mt-1">
                {{ active.milestoneTitle }} &bull; {{ active.pomodoroCount }} Pomodoro (~{{ active.durationMinutes }} phút)
              </p>
            </div>

            <a
              routerLink="/workspace"
              class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-full bg-[#005234] text-white text-xs font-bold hover:bg-[#246B4A] transition-all shadow-xs group cursor-pointer no-underline"
            >
              <span class="material-symbols-outlined text-[18px]">play_arrow</span>
              <span>Vào học ngay (Start)</span>
              <span class="group-hover:translate-x-0.5 transition-transform">&rarr;</span>
            </a>
          </div>
        }

        <!-- Upcoming Tasks in Queue -->
        <div class="space-y-2.5">
          <div class="text-[11px] font-bold uppercase tracking-wider text-neutral-400 font-sans">
            Kế hoạch các ca tiếp theo:
          </div>

          @for (task of upcomingTasks(); track task.id) {
            <div class="p-3 rounded-xl border border-neutral-200/80 bg-neutral-50/50 flex items-center justify-between gap-3 hover:border-emerald-600/40 hover:bg-white transition-all">
              <div class="min-w-0">
                <div class="flex items-center gap-1.5 text-xs text-neutral-500 mb-0.5">
                  <span class="font-mono font-bold text-neutral-800">{{ task.scheduledTime }}</span>
                  <span>&bull;</span>
                  <span class="font-mono text-[11px] font-semibold text-neutral-600">{{ task.taskId }}</span>
                </div>
                <div class="font-semibold text-xs text-neutral-900 truncate">
                  {{ task.title }}
                </div>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <span class="inline-flex items-center gap-1 text-[11px] font-medium text-neutral-600 bg-neutral-100 px-2 py-0.5 rounded-full border border-neutral-200/60">
                  <lucide-icon name="timer" [size]="11" class="shrink-0 text-emerald-800" aria-hidden="true"></lucide-icon>
                  <span>{{ task.pomodoroCount }} phiên</span>
                </span>
                <a
                  routerLink="/workspace"
                  class="text-xs font-semibold text-emerald-800 hover:text-emerald-950 hover:underline no-underline"
                >
                  Bắt đầu &rarr;
                </a>
              </div>
            </div>
          } @empty {
            <div class="p-4 text-center text-xs text-neutral-500 bg-neutral-50/60 rounded-xl border border-dashed border-neutral-200">
              Không còn ca học nào trong hàng đợi hôm nay.
            </div>
          }
        </div>
      </div>
    </div>
  `
})
export class DashboardTodayQueueComponent {
  readonly tasks = input<DashboardTodayQueueItem[]>([]);

  readonly activeTask = computed(() => {
    return this.tasks().find(t => t.status === 'active') || this.tasks()[0];
  });

  readonly upcomingTasks = computed(() => {
    const active = this.activeTask();
    return this.tasks().filter(t => t.id !== active?.id);
  });
}
