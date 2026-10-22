import { Component, inject } from '@angular/core';
import { ScheduleService } from '../services/schedule.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { CardComponent, CardHeaderDirective, CardTitleDirective, CardDescriptionDirective } from '../../../shared/ui/card/card.component';

@Component({
  selector: 'app-schedule-page',
  standalone: true,
  imports: [
    ButtonDirective,
    BadgeDirective,
    CardComponent
  ],
  template: `
    <div class="max-w-5xl mx-auto w-full p-6 space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Thời Khóa Biểu Học Tập</h1>
          <p class="text-sm text-[var(--muted-foreground)]">Lịch trình tự động được đồng bộ với quỹ thời gian rảnh của bạn</p>
        </div>

        <div class="flex items-center gap-3">
          <button appButton variant="outline" size="sm">
            Đồng bộ WebCal (.ics)
          </button>
        </div>
      </div>

      <!-- WebCal Sync Box -->
      <app-card class="bg-[var(--accent)]/30 border-dashed">
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">Đồng bộ lịch 1 chiều (RFC 5545)</span>
            <div class="text-xs font-mono select-all bg-[var(--card)] px-3 py-1.5 rounded-md border border-[var(--border)] max-w-lg truncate">
              {{ scheduleService.webCalInfo().tokenUrl }}
            </div>
          </div>
          <button appButton variant="secondary" size="sm">Sao chép URL</button>
        </div>
      </app-card>

      <!-- Weekly Slots -->
      <div class="space-y-3">
        <h2 class="text-base font-semibold">Các khung giờ học tuần này</h2>
        @for (slot of scheduleService.weeklySlots(); track slot.id) {
          <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)] flex items-center justify-between shadow-xs">
            <div class="flex items-center gap-4">
              <div class="w-16 text-center py-1 rounded bg-[var(--muted)] font-mono text-xs font-bold">
                {{ slot.startTime }}
              </div>
              <div>
                <div class="font-medium text-sm">{{ slot.taskTitle }}</div>
                <div class="text-xs text-[var(--muted-foreground)]">Khung giờ: {{ slot.startTime }} - {{ slot.endTime }}</div>
              </div>
            </div>

            <div class="flex items-center gap-2">
              @if (slot.isCompleted) {
                <span appBadge variant="success">Đã hoàn thành</span>
              } @else {
                <span appBadge variant="outline">Chưa bắt đầu</span>
              }
            </div>
          </div>
        }
      </div>
    </div>
  `
})
export class SchedulePageComponent {
  readonly scheduleService = inject(ScheduleService);
}
