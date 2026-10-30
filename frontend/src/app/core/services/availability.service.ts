import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { catchError, finalize, of, tap } from 'rxjs';
import { API_ENDPOINTS } from '../constants/api-endpoints';
import {
  AllowedWindowDTO,
  AvailabilityMode,
  AvailabilityResponseDTO,
  CalendarIntegrationMode,
  DayOfWeek,
  DayScheduleDTO,
  PreferredPeriod,
  TimeSlotDTO,
  UpdateAvailabilityRequestDTO,
  WeeklyScheduleDTO
} from '../models/availability.model';

export const DAYS_OF_WEEK: readonly DayOfWeek[] = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday'
] as const;

export const DAY_LABELS: Record<DayOfWeek, string> = {
  monday: 'Thứ Hai',
  tuesday: 'Thứ Ba',
  wednesday: 'Thứ Tư',
  thursday: 'Thứ Năm',
  friday: 'Thứ Sáu',
  saturday: 'Thứ Bảy',
  sunday: 'Chủ Nhật'
};

export function calculateDurationMinutes(start: string, end: string, end_day_offset: number = 0): number {
  if (!start || !end) return 0;
  const [sh, sm] = start.split(':').map(Number);
  const [eh, em] = end.split(':').map(Number);
  if (isNaN(sh) || isNaN(sm) || isNaN(eh) || isNaN(em)) return 0;
  const startMin = sh * 60 + sm;
  const endMin = eh * 60 + em + (end_day_offset || 0) * 1440;
  return Math.max(0, endMin - startMin);
}

function minutesToTimeString(totalMinutes: number): string {
  const clamped = Math.max(0, Math.min(1439, totalMinutes));
  const h = Math.floor(clamped / 60);
  const m = clamped % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function findNextNonOverlappingSlot(slots: TimeSlotDTO[]): TimeSlotDTO {
  if (!slots || slots.length === 0) {
    return { start: '19:30', end: '21:30', end_day_offset: 0 };
  }

  const intervals = slots.map(slot => {
    const [sh, sm] = (slot.start || '00:00').split(':').map(Number);
    const [eh, em] = (slot.end || '00:00').split(':').map(Number);
    const startMin = (isNaN(sh) ? 0 : sh) * 60 + (isNaN(sm) ? 0 : sm);
    const endMin = (isNaN(eh) ? 0 : eh) * 60 + (isNaN(em) ? 0 : em) + (slot.end_day_offset || 0) * 1440;
    return { startMin, endMin };
  });

  const overlapsAny = (candStart: number, candEnd: number): boolean =>
    intervals.some(iv => Math.max(candStart, iv.startMin) < Math.min(candEnd, iv.endMin));

  // Try placing right after the latest same-day slot end if <= 22:30 (1350m)
  const sameDayEnds = intervals.filter(iv => iv.endMin <= 1440).map(iv => iv.endMin);
  if (sameDayEnds.length > 0) {
    const lastEnd = Math.max(...sameDayEnds);
    if (lastEnd <= 22 * 60 + 30) {
      const candStart = lastEnd;
      const candEnd = Math.min(23 * 60 + 30, candStart + 90);
      if (candEnd - candStart >= 30 && !overlapsAny(candStart, candEnd)) {
        return {
          start: minutesToTimeString(candStart),
          end: minutesToTimeString(candEnd),
          end_day_offset: 0
        };
      }
    }
  }

  // Otherwise search for a free 90-minute (or 60-minute) window between 08:00 and 23:30
  for (const duration of [90, 60]) {
    for (let candStart = 8 * 60; candStart + duration <= 23 * 60 + 30; candStart += 30) {
      const candEnd = candStart + duration;
      if (!overlapsAny(candStart, candEnd)) {
        return {
          start: minutesToTimeString(candStart),
          end: minutesToTimeString(candEnd),
          end_day_offset: 0
        };
      }
    }
  }

  return { start: '06:00', end: '07:00', end_day_offset: 0 };
}

export function createDefaultSchedule(): WeeklyScheduleDTO {
  return {
    monday: {
      enabled: true,
      quota_hours: 2.0,
      time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }],
      allowed_window: { start: '07:00', end: '23:00' },
      preferred_period: 'EVENING',
      min_session_minutes: 30
    },
    tuesday: {
      enabled: true,
      quota_hours: 2.0,
      time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }],
      allowed_window: { start: '07:00', end: '23:00' },
      preferred_period: 'EVENING',
      min_session_minutes: 30
    },
    wednesday: {
      enabled: true,
      quota_hours: 2.0,
      time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }],
      allowed_window: { start: '07:00', end: '23:00' },
      preferred_period: 'EVENING',
      min_session_minutes: 30
    },
    thursday: {
      enabled: true,
      quota_hours: 2.0,
      time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }],
      allowed_window: { start: '07:00', end: '23:00' },
      preferred_period: 'EVENING',
      min_session_minutes: 30
    },
    friday: {
      enabled: true,
      quota_hours: 2.0,
      time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }],
      allowed_window: { start: '07:00', end: '23:00' },
      preferred_period: 'EVENING',
      min_session_minutes: 30
    },
    saturday: {
      enabled: true,
      quota_hours: 3.0,
      time_slots: [{ start: '14:00', end: '17:00', end_day_offset: 0 }],
      allowed_window: { start: '07:00', end: '23:00' },
      preferred_period: 'AFTERNOON',
      min_session_minutes: 30
    },
    sunday: {
      enabled: true,
      quota_hours: 3.0,
      time_slots: [{ start: '14:00', end: '17:00', end_day_offset: 0 }],
      allowed_window: { start: '07:00', end: '23:00' },
      preferred_period: 'AFTERNOON',
      min_session_minutes: 30
    }
  };
}

@Injectable({
  providedIn: 'root'
})
export class AvailabilityService {
  private readonly http = inject(HttpClient);

  // Core signals
  readonly profile = signal<AvailabilityResponseDTO | null>(null);
  readonly activeMode = signal<AvailabilityMode>('MODE_A');
  readonly calendarIntegrationMode = signal<CalendarIntegrationMode>('NONE');
  readonly minSessionMinutes = signal<number>(30);
  readonly allowedWindow = signal<AllowedWindowDTO>({ start: '07:00', end: '23:00' });
  readonly weeklySchedule = signal<WeeklyScheduleDTO>(createDefaultSchedule());

  readonly loading = signal<boolean>(false);
  readonly saving = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly saveSuccessMessage = signal<string | null>(null);

  // Computed signals
  readonly totalWeeklyHours = computed(() => {
    const schedule = this.weeklySchedule();
    const mode = this.activeMode();
    let total = 0;

    for (const day of DAYS_OF_WEEK) {
      const dayData = schedule[day];
      if (dayData && dayData.enabled) {
        if (mode === 'MODE_A') {
          total += dayData.quota_hours || 0;
        } else {
          const slots = dayData.time_slots || [];
          const dayMinutes = slots.reduce((acc, slot) => {
            return acc + calculateDurationMinutes(slot.start, slot.end, slot.end_day_offset);
          }, 0);
          total += dayMinutes / 60;
        }
      }
    }

    return Math.round(total * 10) / 10;
  });

  readonly dailyErrors = computed<Record<DayOfWeek, string[]>>(() => {
    const schedule = this.weeklySchedule();
    const mode = this.activeMode();
    const globalAllowedWindow = this.allowedWindow();
    const errors: Record<DayOfWeek, string[]> = {
      monday: [],
      tuesday: [],
      wednesday: [],
      thursday: [],
      friday: [],
      saturday: [],
      sunday: []
    };

    for (const day of DAYS_OF_WEEK) {
      const dayData = schedule[day];
      if (!dayData || !dayData.enabled) {
        continue;
      }

      if (mode === 'MODE_A') {
        if (dayData.quota_hours < 0.5) {
          errors[day].push('Thời gian học tối thiểu là 0.5 giờ khi ngày được bật.');
        } else if (dayData.quota_hours > 14.0) {
          errors[day].push('Thời gian học tối đa là 14.0 giờ.');
        }

        const aw = dayData.allowed_window ?? globalAllowedWindow;
        if (aw) {
          const awDuration = calculateDurationMinutes(aw.start, aw.end, 0);
          if (!aw.start || !aw.end || aw.end <= aw.start || awDuration < 30) {
            errors[day].push('Khung giờ cho phép xếp lịch phải có giờ kết thúc sau giờ bắt đầu ít nhất 30 phút.');
          }
        }
      } else {
        // Mode B
        const slots = dayData.time_slots || [];
        if (slots.length === 0) {
          errors[day].push('Cần ít nhất một khung giờ khi ngày được kích hoạt.');
          continue;
        }

        const intervals: Array<{ startMin: number; endMin: number; index: number }> = [];

        for (let i = 0; i < slots.length; i++) {
          const slot = slots[i];
          const dur = calculateDurationMinutes(slot.start, slot.end, slot.end_day_offset);

          if (slot.start >= slot.end && (!slot.end_day_offset || slot.end_day_offset <= 0)) {
            errors[day].push(`Khung giờ #${i + 1} (${slot.start} - ${slot.end}): Giờ bắt đầu phải trước giờ kết thúc.`);
          } else if (dur < 30) {
            errors[day].push(`Khung giờ #${i + 1} (${slot.start} - ${slot.end}): Thời lượng tối thiểu phải từ 30 phút.`);
          }

          const [sh, sm] = (slot.start || '0:0').split(':').map(Number);
          const [eh, em] = (slot.end || '0:0').split(':').map(Number);
          const startMin = sh * 60 + sm;
          const endMin = eh * 60 + em + (slot.end_day_offset || 0) * 1440;
          intervals.push({ startMin, endMin, index: i });
        }

        // Check overlaps
        let hasOverlap = false;
        for (let i = 0; i < intervals.length; i++) {
          for (let j = i + 1; j < intervals.length; j++) {
            const a = intervals[i];
            const b = intervals[j];
            if (Math.max(a.startMin, b.startMin) < Math.min(a.endMin, b.endMin)) {
              hasOverlap = true;
              break;
            }
          }
          if (hasOverlap) break;
        }

        if (hasOverlap) {
          errors[day].push('Có khung giờ bị chồng lấn nhau trong ngày.');
        }
      }
    }

    return errors;
  });

  readonly isWeeklyValid = computed(() => {
    if (this.totalWeeklyHours() < 1.0) {
      return false;
    }
    const errors = this.dailyErrors();
    for (const day of DAYS_OF_WEEK) {
      if (errors[day] && errors[day].length > 0) {
        return false;
      }
    }
    return true;
  });

  // Mutators & Actions
  setMode(mode: AvailabilityMode): void {
    this.activeMode.set(mode);
    this.saveSuccessMessage.set(null);
  }

  setCalendarIntegrationMode(mode: CalendarIntegrationMode): void {
    this.calendarIntegrationMode.set(mode);
  }

  setMinSessionMinutes(minutes: number): void {
    this.minSessionMinutes.set(minutes);
    this.weeklySchedule.update(sched => {
      const next = { ...sched };
      for (const day of DAYS_OF_WEEK) {
        next[day] = {
          ...next[day],
          min_session_minutes: minutes
        };
      }
      return next;
    });
  }

  setAllowedWindow(start: string, end: string): void {
    this.allowedWindow.set({ start, end });
    this.weeklySchedule.update(sched => {
      const next = { ...sched };
      for (const day of DAYS_OF_WEEK) {
        next[day] = {
          ...next[day],
          allowed_window: { start, end }
        };
      }
      return next;
    });
  }

  toggleDayEnabled(day: DayOfWeek): void {
    this.weeklySchedule.update(sched => {
      const current = sched[day];
      return {
        ...sched,
        [day]: {
          ...current,
          enabled: !current.enabled
        }
      };
    });
  }

  updateDayQuota(day: DayOfWeek, quota: number): void {
    this.weeklySchedule.update(sched => {
      const current = sched[day];
      return {
        ...sched,
        [day]: {
          ...current,
          quota_hours: quota
        }
      };
    });
  }

  updateDayPeriod(day: DayOfWeek, period: PreferredPeriod | string): void {
    this.weeklySchedule.update(sched => {
      const current = sched[day];
      return {
        ...sched,
        [day]: {
          ...current,
          preferred_period: period
        }
      };
    });
  }

  updateAllowedWindow(day: DayOfWeek, start: string, end: string): void {
    this.weeklySchedule.update(sched => {
      const current = sched[day];
      return {
        ...sched,
        [day]: {
          ...current,
          allowed_window: { start, end }
        }
      };
    });
  }

  addTimeSlot(day: DayOfWeek): void {
    this.weeklySchedule.update(sched => {
      const current = sched[day];
      const slots = [...current.time_slots];
      const nextSlot = findNextNonOverlappingSlot(slots);
      slots.push(nextSlot);

      return {
        ...sched,
        [day]: {
          ...current,
          time_slots: slots
        }
      };
    });
  }

  removeTimeSlot(day: DayOfWeek, index: number): void {
    this.weeklySchedule.update(sched => {
      const current = sched[day];
      const slots = current.time_slots.filter((_, i) => i !== index);
      return {
        ...sched,
        [day]: {
          ...current,
          time_slots: slots
        }
      };
    });
  }

  updateTimeSlot(day: DayOfWeek, index: number, field: keyof TimeSlotDTO, value: string | number | undefined): void {
    this.weeklySchedule.update(sched => {
      const current = sched[day];
      const slots = current.time_slots.map((slot, i) => {
        if (i === index) {
          return {
            ...slot,
            [field]: value
          };
        }
        return slot;
      });

      return {
        ...sched,
        [day]: {
          ...current,
          time_slots: slots
        }
      };
    });
  }

  copyMondayToWeekdays(): void {
    this.weeklySchedule.update(sched => {
      const monday = JSON.parse(JSON.stringify(sched.monday)) as DayScheduleDTO;
      return {
        ...sched,
        tuesday: JSON.parse(JSON.stringify(monday)),
        wednesday: JSON.parse(JSON.stringify(monday)),
        thursday: JSON.parse(JSON.stringify(monday)),
        friday: JSON.parse(JSON.stringify(monday))
      };
    });
  }

  applyPreset(presetId: 'BUSY_PRO' | 'UNI_STUDENT' | 'BOOTCAMPER'): void {
    const currentAllowedWindow = { ...this.allowedWindow() };
    const currentMinSession = this.minSessionMinutes();

    this.weeklySchedule.update(sched => {
      const nextSched: WeeklyScheduleDTO = JSON.parse(JSON.stringify(sched));

      if (presetId === 'BUSY_PRO') {
        // T2-T6: 20:30 - 22:00 (1.5h), T7-CN: 14:00 - 17:00 (3.0h) -> Tổng 13.5h
        for (const day of ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'] as const) {
          nextSched[day] = {
            enabled: true,
            quota_hours: 1.5,
            preferred_period: 'EVENING',
            min_session_minutes: currentMinSession,
            allowed_window: { ...currentAllowedWindow },
            time_slots: [{ start: '20:30', end: '22:00', end_day_offset: 0 }]
          };
        }
        for (const day of ['saturday', 'sunday'] as const) {
          nextSched[day] = {
            enabled: true,
            quota_hours: 3.0,
            preferred_period: 'AFTERNOON',
            min_session_minutes: currentMinSession,
            allowed_window: { ...currentAllowedWindow },
            time_slots: [{ start: '14:00', end: '17:00', end_day_offset: 0 }]
          };
        }
      } else if (presetId === 'UNI_STUDENT') {
        // T2, T4, T6: 19:30 - 22:00 (2.5h)
        for (const day of ['monday', 'wednesday', 'friday'] as const) {
          nextSched[day] = {
            enabled: true,
            quota_hours: 2.5,
            preferred_period: 'EVENING',
            min_session_minutes: currentMinSession,
            allowed_window: { ...currentAllowedWindow },
            time_slots: [{ start: '19:30', end: '22:00', end_day_offset: 0 }]
          };
        }
        // T3, T5: nghỉ (enabled: false) - giữ sẵn quota & slot mặc định hợp lệ để bật lại không lỗi
        for (const day of ['tuesday', 'thursday'] as const) {
          nextSched[day] = {
            enabled: false,
            quota_hours: 2.0,
            preferred_period: 'EVENING',
            min_session_minutes: currentMinSession,
            allowed_window: { ...currentAllowedWindow },
            time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }]
          };
        }
        // T7, CN: 08:30 - 11:00 (2.5h) + 14:30 - 16:00 (1.5h) = 4.0h
        for (const day of ['saturday', 'sunday'] as const) {
          nextSched[day] = {
            enabled: true,
            quota_hours: 4.0,
            preferred_period: 'MORNING',
            min_session_minutes: currentMinSession,
            allowed_window: { ...currentAllowedWindow },
            time_slots: [
              { start: '08:30', end: '11:00', end_day_offset: 0 },
              { start: '14:30', end: '16:00', end_day_offset: 0 }
            ]
          };
        }
      } else if (presetId === 'BOOTCAMPER') {
        // T2-T7: 08:30 - 11:30 (3.0h) + 14:00 - 17:00 (3.0h) = 6.0h
        for (const day of ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'] as const) {
          nextSched[day] = {
            enabled: true,
            quota_hours: 6.0,
            preferred_period: 'MORNING',
            min_session_minutes: currentMinSession,
            allowed_window: { ...currentAllowedWindow },
            time_slots: [
              { start: '08:30', end: '11:30', end_day_offset: 0 },
              { start: '14:00', end: '17:00', end_day_offset: 0 }
            ]
          };
        }
        // CN: nghỉ - giữ sẵn quota & slot mặc định hợp lệ để bật lại không lỗi
        nextSched.sunday = {
          enabled: false,
          quota_hours: 2.0,
          preferred_period: 'EVENING',
          min_session_minutes: currentMinSession,
          allowed_window: { ...currentAllowedWindow },
          time_slots: [{ start: '19:30', end: '21:30', end_day_offset: 0 }]
        };
      }

      return nextSched;
    });
  }

  loadMyAvailability(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.http
      .get<AvailabilityResponseDTO>(API_ENDPOINTS.SETTINGS.AVAILABILITY, { withCredentials: true })
      .pipe(
        tap(res => {
          this.profile.set(res);
          if (res.mode) {
            this.activeMode.set(res.mode);
          }
          if (res.calendar_integration_mode) {
            this.calendarIntegrationMode.set(res.calendar_integration_mode as CalendarIntegrationMode);
          }
          if (res.min_session_minutes) {
            this.minSessionMinutes.set(res.min_session_minutes);
          }
          if (res.weekly_schedule) {
            this.weeklySchedule.set(res.weekly_schedule);
            const firstAw = res.weekly_schedule.monday?.allowed_window;
            if (firstAw && firstAw.start && firstAw.end) {
              this.allowedWindow.set({ start: firstAw.start, end: firstAw.end });
            }
          }
        }),
        catchError((err: HttpErrorResponse) => {
          const message = err.error?.message || err.message || 'Không thể tải cấu hình thời gian rảnh.';
          this.errorMessage.set(message);
          return of(null);
        }),
        finalize(() => {
          this.loading.set(false);
        })
      )
      .subscribe();
  }

  saveMyAvailability(): void {
    if (!this.isWeeklyValid()) {
      this.errorMessage.set('Vui lòng điều chỉnh lại cấu hình tuần hợp lệ trước khi lưu.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set(null);
    this.saveSuccessMessage.set(null);

    const payload: UpdateAvailabilityRequestDTO = {
      mode: this.activeMode(),
      calendar_integration_mode: this.calendarIntegrationMode(),
      min_session_minutes: this.minSessionMinutes(),
      weekly_schedule: this.weeklySchedule()
    };

    this.http
      .put<AvailabilityResponseDTO>(API_ENDPOINTS.SETTINGS.AVAILABILITY, payload, { withCredentials: true })
      .pipe(
        tap(res => {
          this.profile.set(res);
          if (res.weekly_schedule) {
            this.weeklySchedule.set(res.weekly_schedule);
            const firstAw = res.weekly_schedule.monday?.allowed_window;
            if (firstAw && firstAw.start && firstAw.end) {
              this.allowedWindow.set({ start: firstAw.start, end: firstAw.end });
            }
          }
          this.saveSuccessMessage.set('Đã lưu cấu hình thời gian rảnh thành công!');
        }),
        catchError((err: HttpErrorResponse) => {
          const detailMsg = err.error?.message || err.error?.detail || err.message || 'Không thể lưu cấu hình thời gian rảnh.';
          this.errorMessage.set(detailMsg);
          return of(null);
        }),
        finalize(() => {
          this.saving.set(false);
        })
      )
      .subscribe();
  }
}
