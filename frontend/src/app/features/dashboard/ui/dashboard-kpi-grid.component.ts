import { Component, ChangeDetectionStrategy, input, computed } from '@angular/core';
import { DashboardKpi } from '../models/dashboard.model';
import { KpiCardComponent } from '../../../shared/components/kpi-card/kpi-card.component';

@Component({
  selector: 'app-dashboard-kpi-grid',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [KpiCardComponent],
  template: `
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Card 1: Tổng giờ tháng -->
      <app-kpi-card
        label="Tổng giờ tháng"
        [value]="kpi().monthlyHours"
        [target]="kpi().monthlyTarget + 'h'"
        icon="schedule"
        tone="moss"
        [progress]="monthlyPercent()"
        [subtitle]="monthlyPercent() + '% mục tiêu'"
        [footerText]="'Cam kết ' + kpi().weeklyCommitment + 'h/tuần'"
      />

      <!-- Card 2: Chuỗi liên tục -->
      <app-kpi-card
        label="Chuỗi liên tục"
        [value]="kpi().streakDays + ' ngày'"
        icon="local_fire_department"
        tone="amber"
        [subtitle]="'Kỷ lục: ' + kpi().streakRecord + ' ngày'"
        footerText="Hôm nay: Đã học 🔥"
      />

      <!-- Card 3: Tỷ lệ bám sát lịch -->
      <app-kpi-card
        label="Tỷ lệ bám sát lịch"
        [value]="kpi().adherenceRate + '%'"
        [delta]="'+' + kpi().adherenceChange + '%'"
        trend="up"
        icon="track_changes"
        tone="emerald"
        [progress]="kpi().adherenceRate"
        subtitle="Adaptive AI"
        footerText="Độ chính xác cao"
      />

      <!-- Card 4: Pomodoro hoàn tất -->
      <app-kpi-card
        label="Pomodoro hoàn tất"
        [value]="kpi().pomodoroCompleted + ' phiên'"
        target="25m/phiên"
        icon="timer"
        tone="moss"
        [progress]="kpi().pomodoroTargetRate"
        [subtitle]="'~' + kpi().pomodoroDeepWorkHours + 'h Deep Work'"
        [footerText]="kpi().pomodoroTargetRate + '%'"
      />
    </div>
  `,
})
export class DashboardKpiGridComponent {
  readonly kpi = input.required<DashboardKpi>();

  readonly monthlyPercent = computed(() => {
    const k = this.kpi();
    if (!k || !k.monthlyTarget) return 0;
    return Math.min(100, Math.round((k.monthlyHours / k.monthlyTarget) * 100));
  });
}
