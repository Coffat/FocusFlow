import { Component, ChangeDetectionStrategy, input, output, computed } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardScheduleBlock, DashboardDataState } from '../models/dashboard.model';

interface DayHeader {
  dayOfWeek: number;
  label: string;
  name: string;
  date: string;
  isToday: boolean;
}

@Component({
  selector: 'app-dashboard-weekly-grid',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/70 rounded-xl overflow-hidden shadow-xs">
      <!-- Week Header Toolbar -->
      <div class="px-4 py-3.5 border-b border-[var(--outline-variant,#bfc9c0)]/60 flex flex-wrap items-center justify-between gap-3 bg-[var(--surface,#fbf9f8)]">
        <!-- Left: Week selector & Status tags -->
        <div class="flex items-center flex-wrap gap-2.5">
          <div class="flex items-center gap-1 bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/60 rounded-lg p-0.5">
            <button
              type="button"
              (click)="navigateWeek(-1)"
              class="w-7 h-7 flex items-center justify-center rounded-md hover:bg-[var(--surface-container-high,#eae8e7)] text-[var(--on-surface-variant,#404942)] transition-colors cursor-pointer"
              title="Tuần trước"
              aria-label="Tuần trước"
            >
              <span class="material-symbols-outlined text-[18px]">chevron_left</span>
            </button>
            <span class="px-2.5 py-1 text-xs font-bold text-[var(--on-surface,#1b1c1c)] font-sans">
              {{ weekLabel() }}
            </span>
            <button
              type="button"
              (click)="navigateWeek(1)"
              class="w-7 h-7 flex items-center justify-center rounded-md hover:bg-[var(--surface-container-high,#eae8e7)] text-[var(--on-surface-variant,#404942)] transition-colors cursor-pointer"
              title="Tuần sau"
              aria-label="Tuần sau"
            >
              <span class="material-symbols-outlined text-[18px]">chevron_right</span>
            </button>
          </div>

          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#246B4A]/10 text-[#005234] border border-[#246B4A]/30">
            <span class="w-1.5 h-1.5 rounded-full bg-[#246B4A]"></span>
            Hôm nay (T4)
          </span>

          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-800 border border-amber-500/30">
            <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
            Domino Shift Active
          </span>
        </div>

        <!-- Right: Actions -->
        <div class="flex items-center gap-2">
          <a
            routerLink="/settings"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--outline-variant,#bfc9c0)]/70 bg-[var(--surface-container-lowest,#ffffff)] text-xs font-medium text-[var(--on-surface-variant,#404942)] hover:bg-[var(--surface-container,#efeded)] transition-colors"
          >
            <span class="material-symbols-outlined text-[16px] text-[var(--primary,#005234)]">sync</span>
            <span>Đồng bộ WebCal</span>
          </a>

          <a
            routerLink="/schedule"
            class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[var(--primary,#005234)] text-white text-xs font-semibold hover:bg-[var(--primary-container,#246b4a)] transition-colors shadow-xs"
          >
            <span class="material-symbols-outlined text-[16px]">add</span>
            <span>Thêm slot học</span>
          </a>
        </div>
      </div>

      <!-- State: Unscheduled -->
      @if (currentState() === 'unscheduled') {
        <div class="p-12 text-center flex flex-col items-center justify-center max-w-lg mx-auto">
          <div class="w-14 h-14 rounded-2xl bg-amber-50 text-amber-700 border border-amber-200 flex items-center justify-center mb-4">
            <span class="material-symbols-outlined text-3xl">event_upcoming</span>
          </div>
          <h3 class="text-lg font-bold text-[var(--on-surface,#1b1c1c)] mb-2 font-serif">
            Chưa có buổi học nào được lên lịch
          </h3>
          <p class="text-xs text-[var(--secondary,#5f5e5e)] leading-relaxed mb-6">
            Lộ trình học tập của bạn đã được thiết lập các chặng mốc kiến thức, nhưng chưa có thời gian biểu chi tiết. Hãy kích hoạt thuật toán xếp lịch để AI tự động tối ưu hóa các phiên học theo quỹ giờ rảnh của bạn.
          </p>
          <div class="flex items-center gap-3">
            <a
              routerLink="/roadmaps"
              class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--primary,#005234)] text-white text-xs font-semibold hover:bg-[var(--primary-container,#246b4a)] transition-colors shadow-xs"
            >
              <span class="material-symbols-outlined text-[16px]">auto_schedule</span>
              Tự động xếp lịch với AI
            </a>
            <a
              routerLink="/availability"
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[var(--outline-variant,#bfc9c0)] bg-[var(--surface-container-lowest,#ffffff)] text-xs font-medium text-[var(--on-surface-variant,#404942)] hover:bg-[var(--surface-container,#efeded)] transition-colors"
            >
              <span class="material-symbols-outlined text-[16px]">tune</span>
              Cấu hình giờ rảnh
            </a>
          </div>
        </div>
      }

      <!-- State: Empty Week -->
      @else if (currentState() === 'empty-week' || (currentState() === 'normal' && scheduleBlocks().length === 0)) {
        <div class="p-12 text-center flex flex-col items-center justify-center max-w-lg mx-auto">
          <div class="w-14 h-14 rounded-2xl bg-slate-50 text-slate-700 border border-slate-200 flex items-center justify-center mb-4">
            <span class="material-symbols-outlined text-3xl">event_busy</span>
          </div>
          <h3 class="text-lg font-bold text-[var(--on-surface,#1b1c1c)] mb-2 font-serif">
            Tuần này chưa có lịch học
          </h3>
          <p class="text-xs text-[var(--secondary,#5f5e5e)] leading-relaxed mb-6">
            Không tìm thấy buổi học nào trong khung thời gian tuần {{ weekNumber() }}. Bạn có thể tạo các slot học mới hoặc sao chép thời gian biểu từ tuần trước.
          </p>
          <div class="flex items-center gap-3">
            <a
              routerLink="/schedule"
              class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--primary,#005234)] text-white text-xs font-semibold hover:bg-[var(--primary-container,#246b4a)] transition-colors shadow-xs"
            >
              <span class="material-symbols-outlined text-[16px]">calendar_month</span>
              Xếp lịch tuần này
            </a>
            <button
              type="button"
              (click)="resetToCurrentWeek()"
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[var(--outline-variant,#bfc9c0)] bg-[var(--surface-container-lowest,#ffffff)] text-xs font-medium text-[var(--on-surface-variant,#404942)] hover:bg-[var(--surface-container,#efeded)] transition-colors cursor-pointer"
            >
              <span class="material-symbols-outlined text-[16px]">today</span>
              Quay về tuần hiện tại
            </button>
          </div>
        </div>
      }

      <!-- Normal Weekly Grid -->
      @else {
        <div class="overflow-x-auto">
          <div class="min-w-[840px]">
            <!-- Day of Week Header Columns -->
            <div class="grid grid-cols-[60px_repeat(7,1fr)] border-b border-[var(--outline-variant,#bfc9c0)]/60 bg-[var(--surface-container-low,#f5f3f3)] text-xs">
              <div class="p-2.5 text-center text-[var(--secondary,#5f5e5e)] font-semibold border-r border-[var(--outline-variant,#bfc9c0)]/50">
                Giờ
              </div>
              @for (day of days; track day.dayOfWeek) {
                <div
                  class="p-2.5 text-center border-r border-[var(--outline-variant,#bfc9c0)]/50 last:border-r-0 transition-colors"
                  [class]="day.isToday ? 'bg-[#246B4A]/10 font-bold text-[#005234]' : 'text-[var(--on-surface,#1b1c1c)]'"
                >
                  <div class="flex items-center justify-center gap-1.5">
                    <span class="font-bold">{{ day.label }}</span>
                    <span class="text-[11px] opacity-75 font-normal">({{ day.date }})</span>
                    @if (day.isToday) {
                      <span class="w-1.5 h-1.5 rounded-full bg-[#246B4A]"></span>
                    }
                  </div>
                </div>
              }
            </div>

            <!-- Calendar Time Grid Area -->
            <div class="relative grid grid-cols-[60px_repeat(7,1fr)] bg-[var(--surface-container-lowest,#ffffff)]" style="height: 864px;">
              <!-- Left Time Labels & Horizontal Grid Lines (07:00 to 22:00 = 16 intervals of 54px) -->
              <div class="col-span-8 pointer-events-none absolute inset-0 grid grid-rows-[repeat(16,54px)]">
                @for (h of hours; track h) {
                  <div class="border-b border-[var(--outline-variant,#bfc9c0)]/30 flex items-start">
                    <span class="w-[60px] text-right pr-2 pt-1 text-[10px] font-mono font-medium text-[var(--secondary,#5f5e5e)] select-none">
                      {{ formatHour(h) }}
                    </span>
                    <div class="flex-1 h-full border-l border-[var(--outline-variant,#bfc9c0)]/30"></div>
                  </div>
                }
              </div>

              <!-- Day Column Vertical Dividers -->
              <div class="col-start-1 col-span-1 border-r border-[var(--outline-variant,#bfc9c0)]/50"></div>
              @for (day of days; track day.dayOfWeek) {
                <div
                  class="col-span-1 border-r border-[var(--outline-variant,#bfc9c0)]/40 last:border-r-0 relative transition-colors"
                  [class]="day.isToday ? 'bg-emerald-50/20' : ''"
                ></div>
              }

              <!-- Live Current Time Indicator Line (Wed - 10:30) -->
              <div
                class="absolute left-[60px] right-0 z-30 pointer-events-none flex items-center"
                style="top: 189px;"
              >
                <!-- Glowing current time badge -->
                <div class="absolute left-2 -top-3.5 z-40 bg-[#005234] text-white text-[10px] font-mono font-bold px-2 py-0.5 rounded-full shadow-md flex items-center gap-1.5 border border-emerald-300">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                  <span>10:30</span>
                </div>
                <!-- Green glowing horizontal line -->
                <div class="w-full h-[2px] bg-[#005234] shadow-[0_0_8px_rgba(0,82,52,0.4)]"></div>
              </div>

              <!-- Schedule Block Cards Layer -->
              <div class="col-start-2 col-span-7 absolute inset-y-0 left-[60px] right-0 grid grid-cols-7 pointer-events-auto">
                @for (day of days; track day.dayOfWeek) {
                  <div class="relative h-full col-span-1 px-1">
                    @for (block of getBlocksForDay(day.dayOfWeek); track block.id) {
                      <div
                        class="absolute left-1 right-1 rounded-md p-2 text-xs transition-all duration-150 overflow-hidden select-none cursor-pointer group shadow-2xs"
                        [style.top.px]="calculateTop(block.startTime)"
                        [style.height.px]="calculateHeight(block.startTime, block.endTime)"
                        [class]="getBlockClass(block)"
                      >
                        <!-- Header badge/code & time -->
                        <div class="flex items-center justify-between gap-1 mb-1">
                          <div class="flex items-center gap-1 min-w-0">
                            @if (block.type === 'completed') {
                              <span class="inline-flex items-center gap-0.5 text-[10px] font-bold text-emerald-800 bg-emerald-100/90 px-1.5 py-0.2 rounded-xs">
                                ✓ Xong
                              </span>
                            } @else if (block.type === 'live') {
                              <span class="inline-flex items-center gap-1 text-[10px] font-bold text-white bg-[#005234] px-1.5 py-0.2 rounded-xs animate-pulse">
                                <span class="w-1.5 h-1.5 rounded-full bg-emerald-300"></span>
                                Đang học
                              </span>
                            } @else if (block.type === 'domino_proposal') {
                              <span class="inline-flex items-center gap-0.5 text-[10px] font-bold text-amber-800 bg-amber-100 px-1.5 py-0.2 rounded-xs">
                                ⚡ Domino AI
                              </span>
                            } @else if (block.type === 'university') {
                              <span class="text-[10px] font-semibold text-[var(--secondary,#5f5e5e)] bg-[var(--surface-container-high,#eae8e7)] px-1.5 py-0.2 rounded-xs">
                                WebCal
                              </span>
                            }
                            <span class="text-[10px] font-mono font-semibold truncate opacity-85">
                              {{ block.code || block.startTime }}
                            </span>
                          </div>

                          <span class="text-[10px] font-mono text-[var(--secondary,#5f5e5e)] shrink-0">
                            {{ block.startTime }}
                          </span>
                        </div>

                        <!-- Title -->
                        <div class="font-semibold text-[11px] leading-tight line-clamp-2">
                          {{ block.title }}
                        </div>

                        <!-- Room / Subtext if available -->
                        @if (block.room) {
                          <div class="mt-1 flex items-center gap-1 text-[10px] text-[var(--secondary,#5f5e5e)]">
                            <span class="material-symbols-outlined text-[12px]">location_on</span>
                            <span>{{ block.room }}</span>
                          </div>
                        }

                        @if (block.description) {
                          <div class="mt-0.5 text-[10px] text-amber-800 truncate italic">
                            {{ block.description }}
                          </div>
                        }
                      </div>
                    }
                  </div>
                }
              </div>
            </div>
          </div>
        </div>
      }
    </section>
  `
})
export class DashboardWeeklyGridComponent {
  readonly scheduleBlocks = input<DashboardScheduleBlock[]>([]);
  readonly currentState = input<DashboardDataState>('normal');
  readonly weekOffset = input<number>(0);
  readonly weekOffsetChange = output<number>();

  readonly hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22];

  readonly days: DayHeader[] = [
    { dayOfWeek: 1, label: 'T2', name: 'Thứ Hai', date: '14/10', isToday: false },
    { dayOfWeek: 2, label: 'T3', name: 'Thứ Ba', date: '15/10', isToday: false },
    { dayOfWeek: 3, label: 'T4', name: 'Thứ Tư', date: '16/10', isToday: true },
    { dayOfWeek: 4, label: 'T5', name: 'Thứ Năm', date: '17/10', isToday: false },
    { dayOfWeek: 5, label: 'T6', name: 'Thứ Sáu', date: '18/10', isToday: false },
    { dayOfWeek: 6, label: 'T7', name: 'Thứ Bảy', date: '19/10', isToday: false },
    { dayOfWeek: 7, label: 'CN', name: 'Chủ Nhật', date: '20/10', isToday: false }
  ];

  readonly weekNumber = computed(() => 42 + this.weekOffset());

  readonly weekLabel = computed(() => {
    const num = this.weekNumber();
    if (this.weekOffset() === 0) {
      return `Tuần ${num} (14/10 – 20/10)`;
    }
    return `Tuần ${num}`;
  });

  navigateWeek(delta: number): void {
    const nextOffset = this.weekOffset() + delta;
    this.weekOffsetChange.emit(nextOffset);
  }

  resetToCurrentWeek(): void {
    this.weekOffsetChange.emit(0);
  }

  getBlocksForDay(dayOfWeek: number): DashboardScheduleBlock[] {
    return this.scheduleBlocks().filter(b => b.dayOfWeek === dayOfWeek);
  }

  formatHour(hour: number): string {
    return `${hour.toString().padStart(2, '0')}:00`;
  }

  calculateTop(startTime: string): number {
    const [h, m] = startTime.split(':').map(Number);
    const totalMinutes = (h - 7) * 60 + m;
    // Each hour is 54px -> 54 / 60 = 0.9px per minute
    return Math.max(0, totalMinutes * 0.9);
  }

  calculateHeight(startTime: string, endTime: string): number {
    const [sh, sm] = startTime.split(':').map(Number);
    const [eh, em] = endTime.split(':').map(Number);
    const duration = (eh * 60 + em) - (sh * 60 + sm);
    // At 0.9px per minute, minimum 36px height
    return Math.max(36, duration * 0.9 - 2);
  }

  getBlockClass(block: DashboardScheduleBlock): string {
    switch (block.type) {
      case 'university':
        return 'bg-[var(--surface-container-low,#f5f3f3)] border border-[var(--outline-variant,#bfc9c0)] text-[var(--on-surface-variant,#404942)] hover:border-[var(--outline,#707972)]';
      case 'completed':
        return 'bg-emerald-50/90 border border-emerald-300 text-emerald-950 dark:bg-emerald-950/40 dark:border-emerald-700 dark:text-emerald-100';
      case 'live':
        return 'bg-emerald-50 border-2 border-[#246B4A] text-emerald-950 shadow-md ring-2 ring-emerald-500/20';
      case 'upcoming':
        return 'bg-[var(--surface-container-lowest,#ffffff)] border border-[var(--outline-variant,#bfc9c0)]/80 text-[var(--on-surface,#1b1c1c)] hover:border-[var(--primary,#005234)] hover:shadow-xs';
      case 'domino_proposal':
        return 'bg-amber-50/90 border-2 border-dashed border-amber-500 text-amber-950 shadow-xs';
      default:
        return 'bg-neutral-100 border border-neutral-300 text-neutral-800';
    }
  }
}
