import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule, LUCIDE_ICONS, LucideIconProvider, Timer, ListTodo } from 'lucide-angular';
import { TaskService } from '../services/task.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';

@Component({
  selector: 'app-tasks-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    LucideAngularModule,
    ButtonDirective,
    BadgeDirective
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({ Timer, ListTodo })
    }
  ],
  template: `
    <div class="max-w-7xl mx-auto w-full p-4 sm:p-6 lg:p-8 space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Hàng Đợi Công Việc (Task Queue)</h1>
          <p class="text-sm text-[var(--muted-foreground)]">Quản lý và điều chỉnh ước lượng Pomodoro cho từng nhiệm vụ</p>
        </div>

        <div class="flex items-center gap-3">
          <button appButton variant="outline" size="sm">
            + Thêm việc mới
          </button>
        </div>
      </div>

      <div class="space-y-3">
        @if (taskService.tasks().length === 0) {
          <div class="p-12 text-center flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--card)]">
            <div class="w-12 h-12 rounded-2xl bg-neutral-100 text-neutral-500 flex items-center justify-center mb-3">
              <lucide-icon name="list-todo" [size]="24" aria-hidden="true"></lucide-icon>
            </div>
            <h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100 mb-1">
              Hàng đợi nhiệm vụ đang trống
            </h3>
            <p class="text-xs text-[var(--muted-foreground)] max-w-sm mb-5 leading-relaxed">
              Bạn chưa có nhiệm vụ học tập nào trong hàng đợi. Các nhiệm vụ sẽ tự động được tạo ra khi bạn kích hoạt hoặc tiếp tục Lộ trình học tập.
            </p>
            <a
              routerLink="/roadmaps"
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#005234] text-white text-xs font-semibold hover:bg-[#246B4A] transition-colors shadow-xs no-underline"
            >
              Xem Lộ trình học tập
            </a>
          </div>
        } @else {
          @for (task of taskService.tasks(); track task.id) {
            <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)] flex items-center justify-between shadow-xs">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-sm">{{ task.title }}</span>
                  @if (task.status === 'COMPLETED') {
                    <span appBadge variant="success">Hoàn thành</span>
                  } @else if (task.status === 'IN_PROGRESS') {
                    <span appBadge variant="default">Đang học</span>
                  } @else {
                    <span appBadge variant="outline">Chờ xếp lịch</span>
                  }
                </div>
                <p class="text-xs text-[var(--muted-foreground)]">{{ task.description }}</p>
              </div>

              <div class="flex items-center gap-3">
                <span class="text-xs font-mono text-[var(--muted-foreground)] inline-flex items-center gap-1.5">
                  <lucide-icon name="timer" [size]="14" class="shrink-0 text-emerald-700" aria-hidden="true"></lucide-icon>
                  <span>{{ task.pomodorosCompleted }} / {{ task.pomodoroEstimate }} phiên</span>
                </span>
                @if (task.status !== 'COMPLETED') {
                  <a routerLink="/workspace" appButton size="sm">Bắt đầu</a>
                }
              </div>
            </div>
          }
        }
      </div>
    </div>
  `
})
export class TasksPageComponent {
  readonly taskService = inject(TaskService);
}
