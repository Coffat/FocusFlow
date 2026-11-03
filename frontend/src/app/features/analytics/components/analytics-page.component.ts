import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { AnalyticsService } from '../services/analytics.service';
import { CardComponent, CardHeaderDirective, CardTitleDirective, CardDescriptionDirective } from '../../../shared/ui/card/card.component';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';

@Component({
  selector: 'app-analytics-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective,
    BadgeDirective
  ],
  template: `
    <div class="max-w-5xl mx-auto w-full p-6 space-y-6">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">Báo Cáo & Phân Tích Hiệu Suất</h1>
        <p class="text-sm text-[var(--muted-foreground)]">Đo lường tiến độ học tập và các chỉ số định lượng KPI đồ án</p>
      </div>

      <!-- KPI Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <app-card>
          <span class="text-xs text-[var(--muted-foreground)] font-medium">Tỷ lệ hoàn thành công việc (TSR)</span>
          <div class="text-3xl font-bold text-emerald-600 flex items-center gap-2">
            {{ analyticsService.analyticsData().taskCompletionRate }}%
            <span appBadge variant="success">Đạt KPI (>=90%)</span>
          </div>
          <p class="text-xs text-[var(--muted-foreground)]">Đo lường năng lực cam kết theo kế hoạch tuần</p>
        </app-card>

        <app-card>
          <span class="text-xs text-[var(--muted-foreground)] font-medium">Điểm tập trung & công thái học (SUS)</span>
          <div class="text-3xl font-bold text-indigo-600 flex items-center gap-2">
            {{ analyticsService.analyticsData().averageFocusScore }} / 100
            <span appBadge variant="default">Đạt KPI (>=80)</span>
          </div>
          <p class="text-xs text-[var(--muted-foreground)]">Đánh giá độ thỏa dụng của người học</p>
        </app-card>

        <app-card>
          <span class="text-xs text-[var(--muted-foreground)] font-medium">Tổng giờ học tuần này</span>
          <div class="text-3xl font-bold">
            {{ analyticsService.analyticsData().weeklyStudyHours }} giờ
          </div>
          <p class="text-xs text-[var(--muted-foreground)]">Ghi nhận qua nhịp tim thực tế 60s</p>
        </app-card>
      </div>

      <!-- Daily Activity Breakdown -->
      <app-card>
        <div appCardHeader class="pb-2">
          <h3 appCardTitle class="text-base font-semibold">Phân bổ thời gian học các ngày trong tuần</h3>
          <p appCardDescription>Thống kê số lượng Pomodoro hoàn thành mỗi ngày</p>
        </div>

        <div class="space-y-3 pt-2">
          @for (metric of analyticsService.analyticsData().dailyMetrics; track metric.date) {
            <div class="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--background)]">
              <span class="font-medium text-sm">{{ metric.date }}</span>
              <div class="flex items-center gap-4">
                <span class="text-xs text-[var(--muted-foreground)]">{{ metric.minutesStudied }} phút học</span>
                <span appBadge variant="outline">{{ metric.pomodorosCompleted }} Pomodoro</span>
              </div>
            </div>
          }
        </div>
      </app-card>
    </div>
  `
})
export class AnalyticsPageComponent {
  readonly analyticsService = inject(AnalyticsService);
}
