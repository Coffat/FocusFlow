import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardService } from '../services/dashboard.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { CardComponent, CardHeaderDirective, CardTitleDirective, CardDescriptionDirective } from '../../../shared/ui/card/card.component';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    ButtonDirective,
    BadgeDirective,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective
  ],
  template: `
    <div class="max-w-6xl mx-auto w-full p-6 space-y-6">
      <!-- Welcome Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Bảng Điều Khiển Học Tập</h1>
          <p class="text-sm text-[var(--muted-foreground)]">Chào mừng bạn quay trở lại, hãy tiếp tục mục tiêu hôm nay!</p>
        </div>
        <div class="flex items-center gap-3">
          <a routerLink="/roadmaps/new" appButton variant="outline">
            Tạo lộ trình AI
          </a>
          <a routerLink="/workspace" appButton variant="default">
            Vào phòng học ngay
          </a>
        </div>
      </div>

      <!-- Stats Grid -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <app-card>
          <div class="space-y-1">
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Chuỗi ngày học liên tục</span>
            <div class="text-3xl font-bold flex items-center gap-2">
              🔥 {{ dashboardService.summary()?.streakDays }} ngày
            </div>
          </div>
        </app-card>

        <app-card>
          <div class="space-y-1">
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Tổng số giờ đã học</span>
            <div class="text-3xl font-bold">
              {{ dashboardService.summary()?.totalStudyHours }}h
            </div>
          </div>
        </app-card>

        <app-card>
          <div class="space-y-1">
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Tiến độ Mốc kiến thức</span>
            <div class="text-3xl font-bold">
              {{ dashboardService.summary()?.completedMilestones }} / {{ dashboardService.summary()?.totalMilestones }}
            </div>
          </div>
        </app-card>

        <app-card>
          <div class="space-y-1">
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Mục tiêu tuần này</span>
            <div class="text-3xl font-bold text-emerald-600">
              {{ dashboardService.summary()?.weeklyTargetHours }}h
            </div>
          </div>
        </app-card>
      </div>

      <!-- Active Roadmap Banner -->
      <app-card class="border-l-4 border-l-[var(--primary)]">
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span appBadge variant="default">Lộ trình Đang chạy</span>
              <span class="text-xs text-[var(--muted-foreground)]">Cập nhật 2 giờ trước</span>
            </div>
            <h2 class="text-lg font-semibold">{{ dashboardService.summary()?.activeRoadmapTitle }}</h2>
          </div>
          <a routerLink="/roadmaps" appButton variant="secondary" size="sm">
            Xem chi tiết lộ trình
          </a>
        </div>
      </app-card>

      <!-- Upcoming Tasks -->
      <app-card>
        <div appCardHeader class="pb-2">
          <h3 appCardTitle class="text-base font-semibold">Công việc sắp tới trong ngày</h3>
          <p appCardDescription>Các phiên học được phân bổ theo quỹ thời gian của bạn</p>
        </div>

        <div class="space-y-3 pt-2">
          @for (task of dashboardService.summary()?.upcomingTasks; track task.id) {
            <div class="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]/50 transition-colors">
              <div class="space-y-0.5">
                <div class="font-medium text-sm">{{ task.title }}</div>
                <div class="text-xs text-[var(--muted-foreground)]">{{ task.milestoneTitle }} • {{ task.scheduledDate }}</div>
              </div>
              <div class="flex items-center gap-3">
                <span appBadge variant="outline">{{ task.pomodoroEstimate }} Pomodoro ({{ task.pomodoroEstimate * 25 }}p)</span>
                <a routerLink="/workspace" appButton size="sm">Học ngay</a>
              </div>
            </div>
          }
        </div>
      </app-card>
    </div>
  `
})
export class DashboardPageComponent {
  readonly dashboardService = inject(DashboardService);
}
