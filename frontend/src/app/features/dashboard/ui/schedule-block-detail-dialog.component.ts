import {
  Component,
  ChangeDetectionStrategy,
  input,
  output,
  HostListener,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  X,
  Clock,
  Calendar,
  BookOpen,
  Timer,
  Play,
  Check,
  Zap,
  GraduationCap,
} from 'lucide-angular';
import { DashboardScheduleBlock } from '../models/dashboard.model';

@Component({
  selector: 'app-schedule-block-detail-dialog',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        X,
        Clock,
        Calendar,
        BookOpen,
        Timer,
        Play,
        Check,
        Zap,
        GraduationCap,
      }),
    },
  ],
  template: `
    @if (open() && block(); as b) {
      <div
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-2xs"
        role="dialog"
        aria-modal="true"
        [attr.aria-label]="b.title"
        (click)="onBackdropClick($event)"
      >
        <div
          class="bg-white rounded-2xl shadow-xl border border-neutral-200/80 max-w-md w-full overflow-hidden flex flex-col"
          (click)="$event.stopPropagation()"
        >
          <!-- Header -->
          <div class="px-6 pt-5 pb-4 border-b border-neutral-100 flex items-start justify-between gap-3">
            <div class="min-w-0 flex-1">
              <!-- Status Badge -->
              <div class="mb-2">
                @switch (b.type) {
                  @case ('live') {
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse"></span>
                      <span>Đang diễn ra</span>
                    </span>
                  }
                  @case ('completed') {
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      <lucide-icon name="check" [size]="12" class="stroke-[2.5] text-emerald-600"></lucide-icon>
                      <span>Đã hoàn thành</span>
                    </span>
                  }
                  @case ('domino_proposal') {
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                      <lucide-icon name="zap" [size]="12" class="text-amber-600"></lucide-icon>
                      <span>Đề xuất Domino Shift</span>
                    </span>
                  }
                  @case ('university') {
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-100 text-neutral-700 border border-neutral-200">
                      <lucide-icon name="graduation-cap" [size]="12" class="text-neutral-600"></lucide-icon>
                      <span>Lịch cố định / Trường</span>
                    </span>
                  }
                  @default {
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-100 text-neutral-700 border border-neutral-200">
                      <lucide-icon name="clock" [size]="12" class="text-neutral-500"></lucide-icon>
                      <span>Kế hoạch sắp tới</span>
                    </span>
                  }
                }
              </div>

              <!-- Title -->
              <h3 class="text-lg font-bold text-neutral-900 font-serif leading-snug">
                {{ b.title }}
              </h3>
            </div>

            <!-- Close Button -->
            <button
              type="button"
              (click)="onClose()"
              class="w-8 h-8 rounded-full flex items-center justify-center text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors cursor-pointer shrink-0 mt-0.5"
              aria-label="Đóng"
            >
              <lucide-icon name="x" [size]="18"></lucide-icon>
            </button>
          </div>

          <!-- Body -->
          <div class="px-6 py-5 space-y-4 text-xs text-neutral-700">
            <!-- Time Box -->
            <div class="bg-neutral-50 border border-neutral-200/60 rounded-xl p-3 flex items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <div class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-800 flex items-center justify-center shrink-0">
                  <lucide-icon name="calendar" [size]="16"></lucide-icon>
                </div>
                <div>
                  <div class="font-semibold text-neutral-900">
                    {{ getDayName(b) }}
                  </div>
                  <div class="text-[11px] font-mono text-neutral-500">
                    {{ b.startTime }} – {{ b.endTime }}
                  </div>
                </div>
              </div>

              <div class="text-right">
                <span class="font-bold text-neutral-900 font-mono text-xs">
                  {{ durationMinutes() }} phút
                </span>
                <div class="text-[10px] text-neutral-400">
                  Thời lượng
                </div>
              </div>
            </div>

            <!-- Roadmap & Pomodoro Meta -->
            <div class="grid grid-cols-2 gap-3">
              <!-- Roadmap Info -->
              <div class="p-3 rounded-xl border border-neutral-200/60 bg-white">
                <div class="flex items-center gap-1.5 text-neutral-400 mb-1">
                  <lucide-icon name="book-open" [size]="13"></lucide-icon>
                  <span class="text-[10px] font-bold uppercase tracking-wider">Lộ trình</span>
                </div>
                <div class="font-semibold text-neutral-900 truncate">
                  @if (b.code) {
                    <span class="font-mono text-emerald-800 mr-1">{{ b.code }}</span>
                  }
                  <span>{{ getRoadmapName(b) }}</span>
                </div>
              </div>

              <!-- Pomodoro Estimate -->
              <div class="p-3 rounded-xl border border-neutral-200/60 bg-white">
                <div class="flex items-center gap-1.5 text-neutral-400 mb-1">
                  <lucide-icon name="timer" [size]="13" class="text-emerald-700"></lucide-icon>
                  <span class="text-[10px] font-bold uppercase tracking-wider">Pomodoro</span>
                </div>
                <div class="font-semibold text-neutral-900">
                  {{ pomodoroEstimate() }} phiên
                  <span class="text-[10px] font-normal text-neutral-500 block">
                    ~{{ pomodoroEstimate() * 25 }}p Deep Work
                  </span>
                </div>
              </div>
            </div>

            <!-- Description / Session Goals -->
            <div>
              <div class="text-[11px] font-bold uppercase tracking-wider text-neutral-400 mb-1.5">
                Mục tiêu & Nội dung phiên học
              </div>
              <div class="p-3 rounded-xl bg-neutral-50/70 border border-neutral-200/60 text-xs text-neutral-700 leading-relaxed">
                {{ b.description || 'Phiên học tập tập trung theo lộ trình cá nhân hóa, tối ưu theo phương pháp tự điều hòa học tập (SRL Zimmerman).' }}
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="px-6 py-3.5 bg-neutral-50/70 border-t border-neutral-200/70 flex items-center justify-end gap-2.5">
            <button
              type="button"
              (click)="onClose()"
              class="px-4 py-2 rounded-xl border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 text-xs font-medium transition cursor-pointer"
            >
              Đóng
            </button>

            <button
              type="button"
              (click)="onStart()"
              class="px-4 py-2 rounded-xl bg-[#005234] hover:bg-[#246B4A] text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition active:scale-95 cursor-pointer"
            >
              <lucide-icon name="play" [size]="14" class="fill-white" aria-hidden="true"></lucide-icon>
              <span>Vào phòng học ngay</span>
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class ScheduleBlockDetailDialogComponent {
  readonly open = input<boolean>(false);
  readonly block = input<DashboardScheduleBlock | null>(null);

  readonly closeDialog = output<void>();
  readonly startSession = output<DashboardScheduleBlock>();

  @HostListener('document:keydown.escape')
  handleEscape(): void {
    if (this.open()) {
      this.onClose();
    }
  }

  readonly durationMinutes = computed(() => {
    const b = this.block();
    if (!b) return 0;
    if (b.durationMinutes && b.durationMinutes > 0) return b.durationMinutes;
    const [sh, sm] = b.startTime.split(':').map(Number);
    const [eh, em] = b.endTime.split(':').map(Number);
    return Math.max(0, (eh * 60 + em) - (sh * 60 + sm));
  });

  readonly pomodoroEstimate = computed(() => {
    const b = this.block();
    if (!b) return 1;
    if (b.pomodoroCount && b.pomodoroCount > 0) return b.pomodoroCount;
    return Math.max(1, Math.round(this.durationMinutes() / 30));
  });

  getDayName(b: DashboardScheduleBlock): string {
    const days: Record<number, string> = {
      1: 'Thứ Hai',
      2: 'Thứ Ba',
      3: 'Thứ Tư',
      4: 'Thứ Năm',
      5: 'Thứ Sáu',
      6: 'Thứ Bảy',
      7: 'Chủ Nhật',
    };
    return days[b.dayOfWeek] ?? b.dayLabel ?? 'Thứ trong tuần';
  }

  getRoadmapName(b: DashboardScheduleBlock): string {
    if (b.code === 'RD-IELTS-75') return 'IELTS Academic 7.5';
    if (b.code === 'RD-GO-HEX') return 'Go Hexagonal Architecture';
    return b.code || 'Lộ trình học tập';
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.onClose();
    }
  }

  onClose(): void {
    this.closeDialog.emit();
  }

  onStart(): void {
    const b = this.block();
    if (b) {
      this.startSession.emit(b);
    }
  }
}
