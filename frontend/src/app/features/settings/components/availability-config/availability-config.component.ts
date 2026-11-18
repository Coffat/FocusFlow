import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  Clock,
  Calendar,
  Check,
  AlertTriangle,
  Sparkles,
  Plus,
  Trash2,
  ArrowRight,
  Copy,
  RotateCcw,
  Save,
  Sun,
  Moon,
  Sunrise,
  Sliders,
  CheckCircle2,
  Info,
  Layers,
  CalendarClock
} from 'lucide-angular';
import {
  AvailabilityService,
  DAYS_OF_WEEK,
  DAY_LABELS,
  calculateDurationMinutes,
  createDefaultSchedule
} from '../../../../core/services/availability.service';
import {
  AvailabilityMode,
  CalendarIntegrationMode,
  DayOfWeek,
  TimeSlotDTO
} from '../../../../core/models/availability.model';
import { ButtonDirective } from '../../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../../shared/ui/badge/badge.directive';

export interface CommonShift {
  readonly id: string;
  readonly label: string;
  readonly timeRange: string;
  readonly duration: string;
  readonly start: string;
  readonly end: string;
}

@Component({
  selector: 'app-availability-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideAngularModule,
    ButtonDirective,
    BadgeDirective
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        Clock,
        Calendar,
        Check,
        AlertTriangle,
        Sparkles,
        Plus,
        Trash2,
        ArrowRight,
        Copy,
        RotateCcw,
        Save,
        Sun,
        Moon,
        Sunrise,
        Sliders,
        CheckCircle2,
        Info,
        Layers,
        CalendarClock
      })
    }
  ],
  templateUrl: './availability-config.component.html',
  styleUrl: './availability-config.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AvailabilityConfigComponent implements OnInit {
  readonly service = inject(AvailabilityService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly messageService = inject(MessageService, { optional: true });

  readonly daysOfWeek = DAYS_OF_WEEK;
  readonly dayLabels = DAY_LABELS;
  readonly Math = Math;

  readonly commonShifts: readonly CommonShift[] = [
    { id: 'morning', label: 'Sáng', timeRange: '08:00 - 11:30', duration: '3.5h', start: '08:00', end: '11:30' },
    { id: 'afternoon', label: 'Chiều', timeRange: '13:30 - 17:00', duration: '3.5h', start: '13:30', end: '17:00' },
    { id: 'evening', label: 'Tối', timeRange: '19:00 - 22:00', duration: '3.0h', start: '19:00', end: '22:00' }
  ];

  readonly totalWeeklyHours = computed(() => this.service.totalWeeklyHours());
  readonly isWeeklyValid = computed(() => this.service.isWeeklyValid());

  readonly modeConflictPending = signal<boolean>(false);
  readonly confirmedPrimaryMode = signal<'MANUAL_HYBRID' | 'GOOGLE_CALENDAR' | null>(null);
  readonly showModeConflictBox = computed<boolean>(() => this.modeConflictPending());
  readonly isGoogleCalendarPrimaryMode = computed<boolean>(
    () =>
      this.service.calendarIntegrationMode() === 'CONNECTED' &&
      this.confirmedPrimaryMode() === 'GOOGLE_CALENDAR' &&
      !this.modeConflictPending()
  );

  private triggerConflictIfConnected(): void {
    if (this.service.calendarIntegrationMode() === 'CONNECTED') {
      this.modeConflictPending.set(true);
    }
  }

  chooseManualHybridPrimaryMode(): void {
    this.service.setCalendarIntegrationMode('NONE');
    this.confirmedPrimaryMode.set('MANUAL_HYBRID');
    this.modeConflictPending.set(false);
  }

  chooseGoogleCalendarPrimaryMode(): void {
    this.service.setCalendarIntegrationMode('CONNECTED');
    this.confirmedPrimaryMode.set('GOOGLE_CALENDAR');
    this.modeConflictPending.set(false);
  }

  ngOnInit(): void {
    this.service.loadMyAvailability();

    const focus = this.route.snapshot.queryParamMap.get('focus');
    if (focus === 'calendar') {
      setTimeout(() => {
        const el = document.getElementById('calendar-sync-section') || document.getElementById('calendar-mode-select');
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        (document.getElementById('calendar-mode-select') as HTMLElement)?.focus?.();
      }, 150);
    }
  }

  loadMyAvailability(): void {
    this.service.loadMyAvailability();
  }

  setMode(mode: AvailabilityMode): void {
    this.service.setMode(mode);
    this.triggerConflictIfConnected();
  }

  onMinSessionChange(event: Event): void {
    const val = Number((event.target as HTMLSelectElement).value);
    this.service.setMinSessionMinutes(val);
  }

  onCalendarModeChange(event: Event): void {
    const val = (event.target as HTMLSelectElement).value as CalendarIntegrationMode;
    this.service.setCalendarIntegrationMode(val);
    if (val === 'CONNECTED') {
      this.modeConflictPending.set(true);
    } else {
      this.modeConflictPending.set(false);
      this.confirmedPrimaryMode.set('MANUAL_HYBRID');
    }
  }

  onAllowedWindowChange(field: 'start' | 'end', event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    const current = this.service.allowedWindow();
    if (field === 'start') {
      this.service.setAllowedWindow(val, current.end);
    } else {
      this.service.setAllowedWindow(current.start, val);
    }
  }

  onQuotaRangeInput(day: DayOfWeek, event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    this.service.updateDayQuota(day, val);
    this.triggerConflictIfConnected();
  }

  updateDayQuota(day: DayOfWeek, quota: number): void {
    this.service.updateDayQuota(day, quota);
    this.triggerConflictIfConnected();
  }

  adjustDayQuota(day: DayOfWeek, delta: number): void {
    const current = this.service.weeklySchedule()[day].quota_hours || 0;
    const nextVal = Math.max(0.5, Math.min(14.0, Math.round((current + delta) * 10) / 10));
    this.service.updateDayQuota(day, nextVal);
    this.triggerConflictIfConnected();
  }

  onSlotFieldChange(day: DayOfWeek, index: number, field: keyof TimeSlotDTO, event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.service.updateTimeSlot(day, index, field, val);
    this.triggerConflictIfConnected();
  }

  updateTimeSlot(day: DayOfWeek, index: number, field: keyof TimeSlotDTO, value: string | number | undefined): void {
    this.service.updateTimeSlot(day, index, field, value);
    this.triggerConflictIfConnected();
  }

  onSlotOffsetChange(day: DayOfWeek, index: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.service.updateTimeSlot(day, index, 'end_day_offset', checked ? 1 : 0);
    this.triggerConflictIfConnected();
  }

  addTimeSlot(day: DayOfWeek): void {
    this.service.addTimeSlot(day);
    this.triggerConflictIfConnected();
  }

  removeTimeSlot(day: DayOfWeek, index: number): void {
    this.service.removeTimeSlot(day, index);
    this.triggerConflictIfConnected();
  }

  saveAvailability(): void {
    this.onSaveAvailability();
  }

  resetToDefault(): void {
    this.service.weeklySchedule.set(createDefaultSchedule());
    this.service.activeMode.set('MODE_A');
    this.service.allowedWindow.set({ start: '07:00', end: '23:00' });
    this.service.minSessionMinutes.set(30);
    this.service.calendarIntegrationMode.set('NONE');
    this.modeConflictPending.set(false);
    this.confirmedPrimaryMode.set(null);
    this.service.errorMessage.set(null);
    this.service.saveSuccessMessage.set(null);
  }

  copyMondayToWeekdays(): void {
    this.service.copyMondayToWeekdays();
    this.triggerConflictIfConnected();
  }

  toggleDayEnabled(day: DayOfWeek): void {
    this.service.toggleDayEnabled(day);
    this.triggerConflictIfConnected();
  }

  updateDayPeriod(day: DayOfWeek, period: import('../../../../core/models/availability.model').PreferredPeriod | string): void {
    this.service.updateDayPeriod(day, period);
    this.triggerConflictIfConnected();
  }

  applyPreset(presetId: 'BUSY_PRO' | 'UNI_STUDENT' | 'BOOTCAMPER'): void {
    this.service.applyPreset(presetId);
    this.triggerConflictIfConnected();
  }

  onModeKeydown(event: KeyboardEvent, currentMode: AvailabilityMode): void {
    if (
      event.key === 'ArrowRight' ||
      event.key === 'ArrowLeft' ||
      event.key === 'ArrowDown' ||
      event.key === 'ArrowUp'
    ) {
      event.preventDefault();
      const targetMode: AvailabilityMode = currentMode === 'MODE_A' ? 'MODE_B' : 'MODE_A';
      this.setMode(targetMode);
      const targetId = targetMode === 'MODE_A' ? 'tab-mode-a' : 'tab-mode-b';
      document.getElementById(targetId)?.focus();
    }
  }

  isShiftActive(day: DayOfWeek, start: string, end: string): boolean {
    const dayData = this.service.weeklySchedule()[day];
    if (!dayData?.time_slots) return false;
    return dayData.time_slots.some(s => s.start === start && s.end === end);
  }

  toggleShift(day: DayOfWeek, start: string, end: string): void {
    const dayData = this.service.weeklySchedule()[day];
    if (!dayData) return;

    this.triggerConflictIfConnected();

    if (!dayData.enabled) {
      this.service.toggleDayEnabled(day);
    }

    const slots = [...(this.service.weeklySchedule()[day]?.time_slots || [])];
    const existingIndex = slots.findIndex(s => s.start === start && s.end === end);

    if (existingIndex >= 0) {
      this.service.removeTimeSlot(day, existingIndex);
    } else {
      this.service.weeklySchedule.update(sched => {
        const cur = sched[day];
        const [sh, sm] = start.split(':').map(Number);
        const [eh, em] = end.split(':').map(Number);
        const shiftStartMin = sh * 60 + sm;
        const shiftEndMin = eh * 60 + em;

        // Filter out any slots that overlap with the new shift to avoid collisions
        const nonOverlappingSlots = (cur.time_slots || []).filter(slot => {
          const [sH, sM] = (slot.start || '00:00').split(':').map(Number);
          const [eH, eM] = (slot.end || '00:00').split(':').map(Number);
          const slotStartMin = sH * 60 + sM;
          const slotEndMin = eH * 60 + eM + (slot.end_day_offset || 0) * 1440;
          return Math.max(shiftStartMin, slotStartMin) >= Math.min(shiftEndMin, slotEndMin);
        });

        const newSlots = [...nonOverlappingSlots, { start, end, end_day_offset: 0 }];
        newSlots.sort((a, b) => a.start.localeCompare(b.start));
        return {
          ...sched,
          [day]: {
            ...cur,
            time_slots: newSlots
          }
        };
      });
    }
  }

  getSlotDuration(slot: TimeSlotDTO): number {
    return calculateDurationMinutes(slot.start, slot.end, slot.end_day_offset);
  }

  getDaySlotHours(slots: TimeSlotDTO[]): number {
    const minutes = (slots || []).reduce(
      (acc, s) => acc + calculateDurationMinutes(s.start, s.end, s.end_day_offset),
      0
    );
    return Math.round((minutes / 60) * 10) / 10;
  }

  onSaveAvailability(): void {
    this.service.saveMyAvailability((res) => {
      if (res) {
        const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
        if (returnUrl) {
          this.messageService?.add({
            severity: 'success',
            summary: 'Thành công',
            detail: 'Đã lưu cấu hình thời gian rảnh thành công!',
          });
          const autoOpen = this.route.snapshot.queryParamMap.get('autoOpen');
          let targetUrl = returnUrl;
          if (autoOpen === 'true' && !targetUrl.includes('autoOpen=')) {
            const separator = targetUrl.includes('?') ? '&' : '?';
            targetUrl = `${targetUrl}${separator}autoOpen=true`;
          }
          this.router.navigateByUrl(targetUrl);
        }
      }
    });
  }

  clearError(): void {
    this.service.errorMessage.set(null);
  }

  clearSuccess(): void {
    this.service.saveSuccessMessage.set(null);
  }
}
