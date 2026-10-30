import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SettingsService } from '../services/settings.service';
import { CardComponent, CardHeaderDirective, CardTitleDirective, CardDescriptionDirective } from '../../../shared/ui/card/card.component';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { AvailabilityConfigComponent } from './availability-config/availability-config.component';

@Component({
  selector: 'app-settings-page',
  standalone: true,
  imports: [
    RouterLink,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective,
    ButtonDirective,
    BadgeDirective,
    AvailabilityConfigComponent
  ],
  template: `
    <div class="max-w-4xl mx-auto w-full p-6 space-y-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Cài Đặt Hệ Thống</h1>
          <p class="text-sm text-[var(--muted-foreground)]">Quản lý tùy chọn cá nhân, hạn ngạch AI và phiên bảo mật</p>
        </div>
        <a routerLink="/availability" appButton variant="outline">
          ⏰ Quản lý Thời Gian Rảnh
        </a>
      </div>

      <!-- Quick Link to Availability -->
      <app-card>
        <div appCardHeader class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 appCardTitle>Thời Gian Rảnh Lai (Hybrid Availability)</h3>
            <p appCardDescription>
              Trang cấu hình quỹ giờ linh hoạt (Mode A) và khung giờ cố định (Mode B) hiện là trang độc lập tại
              <code class="px-1.5 py-0.5 rounded bg-[var(--muted)] text-xs font-mono">/availability</code>.
            </p>
          </div>
          <a routerLink="/availability" appButton variant="default">
            Mở trang Lịch Rảnh &rarr;
          </a>
        </div>
      </app-card>

      <!-- Availability Management Section (FR-AVAIL v2.0) -->
      <app-availability-config />

      <!-- AI Quota Card -->
      <app-card>
        <div appCardHeader>
          <div class="flex items-center justify-between">
            <div>
              <h3 appCardTitle>Hạn Ngạch Trí Tuệ Nhân Tạo (AI Credits)</h3>
              <p appCardDescription>Cơ chế bảo toàn hạn ngạch 2 pha (Reserve/Commit) theo ADR-005</p>
            </div>
            <span appBadge variant="outline">
              {{ settingsService.preferences().aiCreditsUsed }} / {{ settingsService.preferences().aiCreditsLimit }} Credits
            </span>
          </div>
        </div>

        <div class="w-full bg-[var(--muted)] h-2 rounded-full overflow-hidden my-2">
          <div class="bg-[var(--primary)] h-full" [style.width.%]="(settingsService.preferences().aiCreditsUsed / settingsService.preferences().aiCreditsLimit) * 100"></div>
        </div>
        <p class="text-xs text-[var(--muted-foreground)]">Mỗi lộ trình học tạo bằng Gemini AI chỉ tính là 1 AI Credit duy nhất.</p>
      </app-card>

      <!-- Preferences -->
      <app-card>
        <div appCardHeader>
          <h3 appCardTitle>Tùy chọn Học Tập</h3>
          <p appCardDescription>Cấu hình mặc định cho phiên Pomodoro và âm thanh chuông báo</p>
        </div>

        <div class="space-y-4 pt-2">
          <div class="flex items-center justify-between py-2 border-b border-[var(--border)]">
            <div>
              <div class="text-sm font-medium">Thời lượng Pomodoro mặc định</div>
              <div class="text-xs text-[var(--muted-foreground)]">Thời gian cho mỗi phiên làm việc tập trung</div>
            </div>
            <span class="text-sm font-mono font-semibold">{{ settingsService.preferences().defaultPomodoroDuration }} phút</span>
          </div>

          <div class="flex items-center justify-between py-2">
            <div>
              <div class="text-sm font-medium">Âm thanh chuông báo</div>
              <div class="text-xs text-[var(--muted-foreground)]">Phát chuông khi kết thúc phiên học hoặc giờ nghỉ</div>
            </div>
            <span appBadge variant="success">Bật</span>
          </div>
        </div>
      </app-card>
    </div>
  `
})
export class SettingsPageComponent {
  readonly settingsService = inject(SettingsService);
}
