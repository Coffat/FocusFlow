import { Component, ChangeDetectionStrategy, input, output, computed, signal, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  Check,
  Zap,
  Clock,
  GraduationCap,
  Timer,
} from 'lucide-angular';
import { DashboardScheduleBlock, DashboardDataState } from '../models/dashboard.model';
import { ScheduleBlockDetailDialogComponent } from './schedule-block-detail-dialog.component';

interface DayHeader {
  dayOfWeek: number;
  label: string;
  name: string;
  date: string;
  isToday: boolean;
}

function getMondayOfWeek(offsetWeeks: number = 0): Date {
  const now = new Date();
  const day = now.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() + diffToMonday + offsetWeeks * 7);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

function getISOWeekNumber(d: Date): number {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}

function formatDayMonth(d: Date): string {
  const dd = d.getDate().toString().padStart(2, '0');
  const mm = (d.getMonth() + 1).toString().padStart(2, '0');
  return `${dd}/${mm}`;
}

@Component({
  selector: 'app-dashboard-weekly-grid',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LucideAngularModule, ScheduleBlockDetailDialogComponent],
  styles: [':host { display: block; width: 100%; }'],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        Check,
        Zap,
        Clock,
        GraduationCap,
        Timer,
      }),
    },
  ],
  template: `
    <section class="bg-white border border-neutral-200/80 rounded-2xl overflow-hidden shadow-xs">
      <!-- Week Header Toolbar -->
      <div class="px-6 py-4 border-b border-neutral-200/70 flex flex-wrap items-center justify-between gap-3 bg-white">
        <!-- Left: Week selector & Status tags -->
        <div class="flex items-center flex-wrap gap-2.5">
          <div class="flex items-center gap-1 bg-white border border-neutral-200/80 rounded-xl p-0.5 shadow-2xs">
            <button
              type="button"
              (click)="navigateWeek(-1)"
              class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-neutral-100 text-neutral-600 transition-colors cursor-pointer"
              title="Tuần trước"
              aria-label="Tuần trước"
            >
              <span class="material-symbols-outlined text-[18px]">chevron_left</span>
            </button>
            <span class="px-2.5 py-1 text-xs font-bold text-neutral-900 font-sans">
              {{ weekLabel() }}
            </span>
            <button
              type="button"
              (click)="navigateWeek(1)"
              class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-neutral-100 text-neutral-600 transition-colors cursor-pointer"
              title="Tuần sau"
              aria-label="Tuần sau"
            >
              <span class="material-symbols-outlined text-[18px]">chevron_right</span>
            </button>
          </div>

          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200/80">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
            Hôm nay ({{ currentTodayLabel() }})
          </span>

          @if (hasDominoShift()) {
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200/80">
              <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
              Domino Shift Active
            </span>
          }
        </div>

        <!-- Right: Actions -->
        <div class="flex items-center gap-2">
          <a
            routerLink="/settings"
            class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-neutral-200 bg-white text-xs font-medium text-neutral-700 hover:bg-neutral-50 transition-colors no-underline"
          >
            <span class="material-symbols-outlined text-[16px] text-emerald-800">sync</span>
            <span>Đồng bộ WebCal</span>
          </a>

          <a
            routerLink="/schedule"
            class="inline-flex items-center gap-1 px-3.5 py-1.5 rounded-xl bg-[#005234] text-white text-xs font-semibold hover:bg-[#246B4A] transition-colors shadow-xs no-underline"
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
          <h3 class="text-lg font-bold text-neutral-900 mb-2 font-serif">
            Chưa có buổi học nào được lên lịch
          </h3>
          <p class="text-xs text-neutral-500 leading-relaxed mb-6">
            Lộ trình học tập của bạn đã được thiết lập các chặng mốc kiến thức, nhưng chưa có thời gian biểu chi tiết. Hãy kích hoạt thuật toán xếp lịch để AI tự động tối ưu hóa các phiên học theo quỹ giờ rảnh của bạn.
          </p>
          <div class="flex items-center gap-3">
            <a
              routerLink="/roadmaps"
              class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#005234] text-white text-xs font-semibold hover:bg-[#246B4A] transition-colors shadow-xs no-underline"
            >
              <span class="material-symbols-outlined text-[16px]">auto_schedule</span>
              Tự động xếp lịch với AI
            </a>
            <a
              routerLink="/availability"
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-neutral-200 bg-white text-xs font-medium text-neutral-700 hover:bg-neutral-50 transition-colors no-underline"
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
          <h3 class="text-lg font-bold text-neutral-900 mb-2 font-serif">
            Tuần này chưa có lịch học
          </h3>
          <p class="text-xs text-neutral-500 leading-relaxed mb-6">
            Không tìm thấy buổi học nào trong khung thời gian tuần {{ weekNumber() }}. Bạn có thể tạo các slot học mới hoặc sao chép thời gian biểu từ tuần trước.
          </p>
          <div class="flex items-center gap-3">
            <a
              routerLink="/schedule"
              class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#005234] text-white text-xs font-semibold hover:bg-[#246B4A] transition-colors shadow-xs no-underline"
            >
              <span class="material-symbols-outlined text-[16px]">calendar_month</span>
              Xếp lịch tuần này
            </a>
            <button
              type="button"
              (click)="resetToCurrentWeek()"
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-neutral-200 bg-white text-xs font-medium text-neutral-700 hover:bg-neutral-50 transition-colors cursor-pointer"
            >
              <span class="material-symbols-outlined text-[16px]">today</span>
              Quay về tuần hiện tại
            </button>
          </div>
        </div>
      }

      <!-- Normal Weekly Grid -->
      @else {
        <div class="overflow-x-auto overflow-y-hidden">
          <div class="min-w-[800px] w-full">
            <!-- Day of Week Header Columns (Single Grid Aligned) -->
            <div class="grid grid-cols-[60px_repeat(7,minmax(0,1fr))] border-b border-neutral-200/70 bg-neutral-50/70 text-xs">
              <div class="p-2.5 text-center text-neutral-500 font-semibold border-r border-neutral-200/60 select-none">
                Giờ
              </div>
              @for (day of days(); track day.dayOfWeek) {
                <div
                  class="p-2.5 text-center border-r border-neutral-200/50 last:border-r-0 transition-colors"
                  [class]="day.isToday ? 'bg-emerald-50/70 font-bold text-emerald-900' : 'text-neutral-800 font-medium'"
                >
                  <div class="flex items-center justify-center gap-1.5">
                    <span class="font-bold">{{ day.label }}</span>
                    <span class="text-[11px] opacity-75 font-normal">({{ day.date }})</span>
                    @if (day.isToday) {
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                    }
                  </div>
                </div>
              }
            </div>

            <!-- Calendar Time Grid Area: 13 intervals of 48px + 24px padding = 648px -->
            <div class="relative grid grid-cols-[60px_repeat(7,minmax(0,1fr))] bg-white overflow-hidden" [style.height.px]="GRID_HEIGHT">
              <!-- Horizontal Time Grid Lines & Hour Labels Layer (spanning full width) -->
              <div class="absolute inset-0 pointer-events-none z-0">
                @for (h of hours; track h; let i = $index) {
                  <div
                    class="absolute left-0 right-0 flex items-start"
                    [style.top.px]="i * 48 + TOP_OFFSET"
                  >
                    <span class="w-[60px] text-right pr-2.5 text-[10px] font-mono font-medium text-neutral-400 select-none -translate-y-1/2 leading-none">
                      {{ formatHour(h) }}
                    </span>
                    <div class="flex-1 border-t border-neutral-200/60"></div>
                  </div>
                }
              </div>

              <!-- Column 1: Time Gutter Divider -->
              <div class="relative h-full border-r border-neutral-200/60 pointer-events-none z-10"></div>

              <!-- Columns 2..8: 7 Continuous Day Columns -->
              @for (day of days(); track day.dayOfWeek) {
                <div
                  class="relative h-full border-r border-neutral-200/50 last:border-r-0 z-20 transition-colors"
                  [class.bg-emerald-50/25]="day.isToday"
                >
                  @for (block of getBlocksForDay(day.dayOfWeek); track block.id) {
                    <div
                      class="absolute inset-x-1.5 rounded-lg p-2 sm:p-2.5 text-xs transition-all duration-150 select-none cursor-pointer flex flex-col gap-1 items-start justify-start overflow-hidden shadow-2xs hover:shadow-xs active:scale-[0.99] border border-l-[3.5px]"
                      [style.top.px]="calculateTop(block.startTime)"
                      [style.height.px]="calculateHeight(block.startTime, block.endTime)"
                      [class]="getBlockClass(block)"
                      (click)="openBlockDetail(block)"
                    >
                      <!-- Line 1: Title (most prominent, clean line clamp) -->
                      <div class="font-semibold text-xs text-neutral-900 leading-snug line-clamp-2 w-full">
                        {{ block.title }}
                      </div>

                      <!-- Line 2: Time & Status Symbol (pure symbols, no text) -->
                      <div class="w-full flex items-center justify-between gap-1 text-[10px] font-mono text-neutral-500">
                        <!-- Left: Start - End Time -->
                        <span class="flex items-center gap-1 shrink-0">
                          {{ block.startTime }} – {{ block.endTime }}
                        </span>

                        <!-- Right: Status Symbol Icon -->
                        <div class="flex items-center gap-1 shrink-0">
                          @if (block.type === 'live') {
                            <span class="w-2 h-2 rounded-full bg-emerald-600 ring-2 ring-emerald-200 animate-pulse" title="Đang diễn ra"></span>
                          } @else if (block.type === 'completed') {
                            <lucide-icon name="check" [size]="13" class="text-emerald-600 stroke-[2.5]" aria-hidden="true" title="Đã hoàn thành"></lucide-icon>
                          } @else if (block.type === 'domino_proposal') {
                            <lucide-icon name="zap" [size]="12" class="text-amber-600" aria-hidden="true" title="Đề xuất Domino Shift"></lucide-icon>
                          } @else if (block.type === 'university') {
                            <lucide-icon name="graduation-cap" [size]="12" class="text-neutral-500" aria-hidden="true" title="Lịch cố định / Trường"></lucide-icon>
                          } @else {
                            <lucide-icon name="clock" [size]="12" class="text-neutral-400" aria-hidden="true" title="Kế hoạch sắp tới"></lucide-icon>
                          }
                        </div>
                      </div>

                      <!-- Tier 3: Very Tall Blocks (duration >= 120 mins) -->
                      @if (getDurationMinutes(block) >= 120) {
                        <div class="w-full flex items-center flex-wrap gap-1.5 mt-0.5 pt-1 border-t border-neutral-200/50">
                          @if (block.code) {
                            <span class="inline-block px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-700 font-mono text-[9px] font-semibold border border-neutral-200/70">
                              {{ block.code }}
                            </span>
                          }
                          <span class="inline-flex items-center gap-1 text-[10px] text-neutral-600 font-mono">
                            <lucide-icon name="timer" [size]="11" class="text-emerald-700 shrink-0" aria-hidden="true"></lucide-icon>
                            <span>{{ getPomodoroEstimate(block) }} phiên</span>
                          </span>
                        </div>
                      }
                    </div>
                  }
                </div>
              }

              <!-- Live Current Time Indicator Line (dynamic client time, within 07:00 - 20:59) -->
              @if (currentTimeIndicator().visible) {
                <div
                  class="absolute left-[60px] right-0 z-30 pointer-events-none flex items-center"
                  [style.top.px]="currentTimeIndicator().topPx"
                >
                  <!-- Glowing current time badge -->
                  <div class="absolute left-2 -top-3 z-40 bg-[#005234] text-white text-[10px] font-mono font-bold px-2 py-0.5 rounded-full shadow-xs flex items-center gap-1.5 border border-emerald-400/30">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                    <span>{{ currentTimeIndicator().timeString }}</span>
                  </div>
                  <!-- Green glowing horizontal line -->
                  <div class="w-full h-[2px] bg-[#005234] shadow-[0_0_8px_rgba(0,82,52,0.3)]"></div>
                </div>
              }
            </div>
          </div>
        </div>

        <!-- Calendar Legend Footer Toolbar -->
        <div class="border-t border-neutral-200/70 bg-neutral-50/50 px-4 sm:px-6 py-2.5 flex flex-wrap items-center gap-4 sm:gap-6 text-xs text-neutral-600">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-600 ring-2 ring-emerald-200 animate-pulse" aria-hidden="true"></span>
            <span>Đang diễn ra</span>
          </div>

          <div class="flex items-center gap-1.5">
            <lucide-icon name="check" [size]="13" class="text-emerald-600 stroke-[2.5]" aria-hidden="true"></lucide-icon>
            <span>Đã hoàn thành</span>
          </div>

          <div class="flex items-center gap-1.5">
            <lucide-icon name="zap" [size]="12" class="text-amber-600" aria-hidden="true"></lucide-icon>
            <span>Đề xuất Domino Shift</span>
          </div>

          <div class="flex items-center gap-1.5">
            <lucide-icon name="clock" [size]="12" class="text-neutral-400" aria-hidden="true"></lucide-icon>
            <span>Kế hoạch sắp tới</span>
          </div>

          <div class="flex items-center gap-1.5">
            <lucide-icon name="graduation-cap" [size]="12" class="text-neutral-500" aria-hidden="true"></lucide-icon>
            <span>Lịch cố định / Trường</span>
          </div>
        </div>
      }
    </section>

    <!-- Schedule Block Detail Dialog -->
    <app-schedule-block-detail-dialog
      [open]="selectedBlock() !== null"
      [block]="selectedBlock()"
      (closeDialog)="closeBlockDetail()"
      (startSession)="onStartSession($event)"
    />
  `
})
export class DashboardWeeklyGridComponent {
  private readonly router = inject(Router);

  readonly scheduleBlocks = input<DashboardScheduleBlock[]>([]);
  readonly currentState = input<DashboardDataState>('normal');
  readonly weekOffset = input<number>(0);
  readonly hasDominoShift = input<boolean>(false);
  readonly weekOffsetChange = output<number>();

  readonly selectedBlock = signal<DashboardScheduleBlock | null>(null);

  openBlockDetail(block: DashboardScheduleBlock): void {
    this.selectedBlock.set(block);
  }

  closeBlockDetail(): void {
    this.selectedBlock.set(null);
  }

  onStartSession(block: DashboardScheduleBlock): void {
    this.selectedBlock.set(null);
    this.router.navigate(['/workspace']);
  }

  readonly TOP_OFFSET = 12;
  readonly BOTTOM_OFFSET = 12;
  readonly GRID_HEIGHT = 13 * 48 + 12 + 12; // 648px

  readonly hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

  readonly currentTodayLabel = computed(() => {
    const dayLabels = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
    return dayLabels[new Date().getDay()];
  });

  readonly days = computed<DayHeader[]>(() => {
    const offset = this.weekOffset();
    const monday = getMondayOfWeek(offset);
    const today = new Date();
    const todayYear = today.getFullYear();
    const todayMonth = today.getMonth();
    const todayDate = today.getDate();

    const DAY_CONFIGS = [
      { dayOfWeek: 1, label: 'T2', name: 'Thứ Hai' },
      { dayOfWeek: 2, label: 'T3', name: 'Thứ Ba' },
      { dayOfWeek: 3, label: 'T4', name: 'Thứ Tư' },
      { dayOfWeek: 4, label: 'T5', name: 'Thứ Năm' },
      { dayOfWeek: 5, label: 'T6', name: 'Thứ Sáu' },
      { dayOfWeek: 6, label: 'T7', name: 'Thứ Bảy' },
      { dayOfWeek: 7, label: 'CN', name: 'Chủ Nhật' },
    ];

    return DAY_CONFIGS.map((cfg, idx) => {
      const dayDate = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + idx);
      const isToday =
        dayDate.getFullYear() === todayYear &&
        dayDate.getMonth() === todayMonth &&
        dayDate.getDate() === todayDate;

      return {
        ...cfg,
        date: formatDayMonth(dayDate),
        isToday,
      };
    });
  });

  readonly weekNumber = computed(() => {
    const monday = getMondayOfWeek(this.weekOffset());
    const thursday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 3);
    return getISOWeekNumber(thursday);
  });

  readonly weekLabel = computed(() => {
    const offset = this.weekOffset();
    const monday = getMondayOfWeek(offset);
    const sunday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6);
    const num = this.weekNumber();
    return `Tuần ${num} (${formatDayMonth(monday)} – ${formatDayMonth(sunday)})`;
  });

  readonly currentTimeIndicator = computed<{ visible: boolean; topPx: number; timeString: string }>(() => {
    if (this.weekOffset() !== 0) {
      return { visible: false, topPx: 0, timeString: '' };
    }
    const now = new Date();
    const h = now.getHours();
    const m = now.getMinutes();
    if (h < 7 || h > 20) {
      return { visible: false, topPx: 0, timeString: '' };
    }
    const totalMinutes = (h - 7) * 60 + m;
    const topPx = this.TOP_OFFSET + Math.max(0, totalMinutes * 0.8);
    const timeString = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
    return { visible: true, topPx, timeString };
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
    // Each hour is 48px -> 48 / 60 = 0.8px per minute
    return this.TOP_OFFSET + Math.max(0, totalMinutes * 0.8);
  }

  calculateHeight(startTime: string, endTime: string): number {
    const [sh, sm] = startTime.split(':').map(Number);
    const [eh, em] = endTime.split(':').map(Number);
    const duration = (eh * 60 + em) - (sh * 60 + sm);
    // At 0.8px per minute, minimum 34px height
    return Math.max(34, duration * 0.8 - 2);
  }

  getDurationMinutes(block: DashboardScheduleBlock): number {
    if (block.durationMinutes && block.durationMinutes > 0) {
      return block.durationMinutes;
    }
    const [sh, sm] = block.startTime.split(':').map(Number);
    const [eh, em] = block.endTime.split(':').map(Number);
    return Math.max(0, (eh * 60 + em) - (sh * 60 + sm));
  }

  getPomodoroEstimate(block: DashboardScheduleBlock): number {
    if (block.pomodoroCount && block.pomodoroCount > 0) {
      return block.pomodoroCount;
    }
    const duration = this.getDurationMinutes(block);
    return Math.max(1, Math.round(duration / 30));
  }

  getBlockClass(block: DashboardScheduleBlock): string {
    switch (block.type) {
      case 'completed':
        return 'border-l-emerald-600 bg-emerald-50/50 text-neutral-900 hover:bg-emerald-50/80';
      case 'live':
        return 'border-l-[#246B4A] bg-white ring-1 ring-emerald-500/20 text-neutral-900 shadow-xs';
      case 'upcoming':
        return 'border-l-neutral-400 bg-white text-neutral-900 hover:border-neutral-300 hover:shadow-xs';
      case 'domino_proposal':
        return 'border-l-amber-500 bg-amber-50/60 border-dashed border-amber-300 text-neutral-900 hover:bg-amber-50/80';
      case 'university':
        return 'border-l-neutral-400 bg-neutral-50/80 text-neutral-800 hover:bg-neutral-100/80';
      default:
        return 'border-l-neutral-400 bg-white text-neutral-900';
    }
  }
}