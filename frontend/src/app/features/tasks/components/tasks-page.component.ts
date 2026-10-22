import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TaskService } from '../services/task.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { CardComponent, CardHeaderDirective, CardTitleDirective, CardDescriptionDirective } from '../../../shared/ui/card/card.component';

@Component({
  selector: 'app-tasks-page',
  standalone: true,
  imports: [
    RouterLink,
    ButtonDirective,
    BadgeDirective
  ],
  template: `
    <div class="max-w-5xl mx-auto w-full p-6 space-y-6">
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
              <span class="text-xs font-mono text-[var(--muted-foreground)]">
                {{ task.pomodorosCompleted }} / {{ task.pomodoroEstimate }} 🍅
              </span>
              @if (task.status !== 'COMPLETED') {
                <a routerLink="/workspace" appButton size="sm">Bắt đầu</a>
              }
            </div>
          </div>
        }
      </div>
    </div>
  `
})
export class TasksPageComponent {
  readonly taskService = inject(TaskService);
}
