import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  AvailabilityService,
  DAYS_OF_WEEK,
  DAY_LABELS,
  calculateDurationMinutes
} from '../../../../core/services/availability.service';
import {
  AvailabilityMode,
  CalendarIntegrationMode,
  DayOfWeek,
  TimeSlotDTO
} from '../../../../core/models/availability.model';
import { ButtonDirective } from '../../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../../shared/ui/badge/badge.directive';

@Component({
  selector: 'app-availability-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonDirective,
    BadgeDirective
  ],
  templateUrl: './availability-config.component.html',
  styleUrl: './availability-config.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AvailabilityConfigComponent implements OnInit {
  readonly service = inject(AvailabilityService);

  readonly daysOfWeek = DAYS_OF_WEEK;
  readonly dayLabels = DAY_LABELS;
  readonly Math = Math;

  ngOnInit(): void {
    this.service.loadMyAvailability();
  }

  setMode(mode: AvailabilityMode): void {
    this.service.setMode(mode);
  }

  onMinSessionChange(event: Event): void {
    const val = Number((event.target as HTMLSelectElement).value);
    this.service.setMinSessionMinutes(val);
  }

  onCalendarModeChange(event: Event): void {
    const val = (event.target as HTMLSelectElement).value as CalendarIntegrationMode;
    this.service.setCalendarIntegrationMode(val);
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
  }

  adjustDayQuota(day: DayOfWeek, delta: number): void {
    const current = this.service.weeklySchedule()[day].quota_hours || 0;
    const nextVal = Math.max(0.5, Math.min(14.0, Math.round((current + delta) * 10) / 10));
    this.service.updateDayQuota(day, nextVal);
  }

  onSlotFieldChange(day: DayOfWeek, index: number, field: keyof TimeSlotDTO, event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.service.updateTimeSlot(day, index, field, val);
  }

  onSlotOffsetChange(day: DayOfWeek, index: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.service.updateTimeSlot(day, index, 'end_day_offset', checked ? 1 : 0);
  }

  getSlotDuration(slot: TimeSlotDTO): number {
    return calculateDurationMinutes(slot.start, slot.end, slot.end_day_offset);
  }

  getDaySlotHours(slots: TimeSlotDTO[]): number {
    const minutes = slots.reduce((acc, s) => acc + calculateDurationMinutes(s.start, s.end, s.end_day_offset), 0);
    return Math.round((minutes / 60) * 10) / 10;
  }

  clearError(): void {
    this.service.errorMessage.set(null);
  }

  clearSuccess(): void {
    this.service.saveSuccessMessage.set(null);
  }
}
