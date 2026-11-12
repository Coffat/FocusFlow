import { Component, ChangeDetectionStrategy, input, output } from '@angular/core';
import { DashboardDataState } from '../models/dashboard.model';

@Component({
  selector: 'app-dashboard-state-switcher',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <aside aria-label="Mô phỏng trạng thái dữ liệu" class="w-full bg-[var(--surface-container-low,#f5f3f3)] border border-[var(--outline-variant,#bfc9c0)]/60 rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
      <div class="flex items-center gap-2 text-[var(--on-surface-variant,#404942)] font-medium">
        <span class="material-symbols-outlined text-[18px] text-[var(--primary,#005234)]">tune</span>
        <span class="font-semibold text-[var(--on-surface,#1b1c1c)]">Mô phỏng dữ liệu (Data States):</span>
        <span class="hidden sm:inline text-[var(--secondary,#5f5e5e)]">Kiểm tra hiển thị giao diện theo các kịch bản của người học</span>
      </div>

      <div class="flex items-center flex-wrap gap-1.5" role="group" aria-label="Lựa chọn trạng thái dữ liệu">
        @for (item of stateOptions; track item.id) {
          <button
            type="button"
            (click)="selectState(item.id)"
            [attr.aria-pressed]="activeState() === item.id"
            class="px-3 py-1 rounded-full font-medium transition-all duration-150 flex items-center gap-1.5 cursor-pointer"
            [class]="activeState() === item.id
              ? 'bg-[var(--primary,#005234)] text-white shadow-xs font-semibold'
              : 'bg-[var(--surface-container-lowest,#ffffff)] text-[var(--on-surface-variant,#404942)] border border-[var(--outline-variant,#bfc9c0)]/70 hover:bg-[var(--surface-container,#efeded)]'"
          >
            <span class="w-1.5 h-1.5 rounded-full" [class]="activeState() === item.id ? 'bg-emerald-300' : 'bg-[var(--outline,#707972)]'"></span>
            <span>{{ item.label }}</span>
          </button>
        }
      </div>
    </aside>
  `
})
export class DashboardStateSwitcherComponent {
  readonly activeState = input.required<DashboardDataState>();
  readonly stateChange = output<DashboardDataState>();

  readonly stateOptions: Array<{ id: DashboardDataState; label: string }> = [
    { id: 'normal', label: 'Hoạt động bình thường' },
    { id: 'new-user', label: 'Người dùng mới 100%' },
    { id: 'unscheduled', label: 'Có lộ trình - Chưa xếp lịch' },
    { id: 'empty-week', label: 'Tuần trống không có lịch' }
  ];

  selectState(state: DashboardDataState): void {
    if (this.activeState() !== state) {
      this.stateChange.emit(state);
    }
  }
}
