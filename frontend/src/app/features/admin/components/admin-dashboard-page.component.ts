import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import {
  CardComponent,
  CardDescriptionDirective,
  CardHeaderDirective,
  CardTitleDirective,
} from '../../../shared/ui/card/card.component';
import { AdminStatusService } from '../services/admin-status.service';

@Component({
  selector: 'app-admin-dashboard-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    BadgeDirective,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective,
  ],
  template: `
    <div class="max-w-4xl mx-auto w-full p-6 space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Cổng Quản Trị Hệ Thống (Admin Portal)</h1>
          <p class="text-sm text-[var(--muted-foreground)]">
            Khu vực dành riêng cho Quản trị viên hệ thống FocusFlow (ADR-008)
          </p>
        </div>
        <span appBadge variant="default">RBAC: ADMIN</span>
      </div>

      @if (loading()) {
        <app-card>
          <div
            role="status"
            aria-live="polite"
            data-testid="admin-status-loading"
            class="p-6 text-sm text-[var(--muted-foreground)]"
          >
            Đang kiểm tra trạng thái Cổng Quản Trị từ máy chủ...
          </div>
        </app-card>
      } @else if (forbidden()) {
        <app-card>
          <div
            role="alert"
            data-testid="admin-status-forbidden"
            class="p-6 space-y-3"
          >
            <h2 class="text-base font-semibold text-rose-700">
              Không có quyền truy cập Cổng Quản Trị (403 Forbidden)
            </h2>
            <p class="text-sm text-[var(--muted-foreground)]">
              Tài khoản hiện tại không có vai trò quản trị viên (ADMIN). Vui lòng quay lại Bảng điều khiển học tập.
            </p>
            <a
              routerLink="/dashboard"
              class="inline-flex items-center text-sm font-semibold text-[#246B4A] hover:underline"
            >
              &larr; Quay lại Bảng điều khiển
            </a>
          </div>
        </app-card>
      } @else if (errorMessage(); as err) {
        <app-card>
          <div
            role="alert"
            data-testid="admin-status-error"
            class="p-6 space-y-3"
          >
            <h2 class="text-base font-semibold text-rose-700">
              Không thể kết nối máy chủ quản trị
            </h2>
            <p class="text-sm text-[var(--muted-foreground)]">{{ err }}</p>
            <button
              type="button"
              data-testid="admin-status-retry-btn"
              (click)="loadStatus()"
              class="inline-flex items-center px-4 py-2 rounded-full text-xs font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors cursor-pointer"
            >
              Thử lại
            </button>
          </div>
        </app-card>
      } @else {
        <app-card>
          <div appCardHeader class="pb-2">
            <h2 appCardTitle class="text-base font-semibold" data-testid="admin-honest-status-title">
              Cổng Quản Trị chưa được kích hoạt trong bản phát hành hiện tại
            </h2>
            <p appCardDescription>
              Bảo vệ tuyến đường bằng quyền ADMIN (Route Guard + Backend RBAC)
            </p>
          </div>

          <div data-testid="admin-honest-status-card" class="space-y-4 pt-2 text-sm text-[var(--muted-foreground)]">
            <p class="text-[var(--foreground)] leading-relaxed">
              {{ statusMessage() }}
            </p>
            <p class="leading-relaxed">
              Các API giám sát AI telemetry (UC-28) và quản lý tài khoản / hạn ngạch người học (UC-26) chưa được bật ở máy chủ trong phiên bản này. Hệ thống không hiển thị số liệu giả lập hay thao tác cộng hạn ngạch cục bộ.
            </p>
            <div>
              <a
                routerLink="/dashboard"
                class="inline-flex items-center text-xs font-semibold text-[#246B4A] hover:underline"
              >
                &larr; Quay lại Bảng điều khiển học tập
              </a>
            </div>
          </div>
        </app-card>
      }
    </div>
  `,
})
export class AdminDashboardPageComponent implements OnInit {
  private readonly adminStatusService = inject(AdminStatusService);
  private readonly destroyRef = inject(DestroyRef);

  readonly loading = signal<boolean>(true);
  readonly forbidden = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly statusMessage = signal<string>(
    'Cổng quản trị chưa được kích hoạt trong bản phát hành hiện tại.'
  );

  ngOnInit(): void {
    this.loadStatus();
  }

  loadStatus(): void {
    this.loading.set(true);
    this.forbidden.set(false);
    this.errorMessage.set(null);

    this.adminStatusService
      .getStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          const msg = res['message'];
          if (typeof msg === 'string' && msg.trim().length > 0) {
            this.statusMessage.set(msg);
          }
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          if (err instanceof HttpErrorResponse && err.status === 403) {
            this.forbidden.set(true);
            return;
          }
          this.errorMessage.set('Không thể tải trạng thái Cổng Quản Trị. Vui lòng thử lại sau.');
        },
      });
  }
}
