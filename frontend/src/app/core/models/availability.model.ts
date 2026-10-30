import type { components } from '../api/schema';

export type TimeSlotDTO = Omit<components['schemas']['TimeSlotDTO'], 'end_day_offset'> & {
  end_day_offset?: components['schemas']['TimeSlotDTO']['end_day_offset'];
};
export type AllowedWindowDTO = components['schemas']['AllowedWindowDTO'];
export type PreferredPeriod = 'MORNING' | 'AFTERNOON' | 'EVENING' | 'ANY';
export type AvailabilityMode = 'MODE_A' | 'MODE_B';
export type CalendarIntegrationMode = 'NONE' | 'EXPORT_ICS' | 'CONNECTED';
export type DayOfWeek = keyof components['schemas']['WeeklyScheduleDTO'];
export type DayScheduleDTO = Omit<
  components['schemas']['DayScheduleDTO'],
  'time_slots' | 'preferred_period' | 'min_session_minutes'
> & {
  time_slots: TimeSlotDTO[];
  preferred_period?: PreferredPeriod | string;
  min_session_minutes?: number;
};
export type WeeklyScheduleDTO = Record<DayOfWeek, DayScheduleDTO>;
export type UpdateAvailabilityRequestDTO = Omit<
  components['schemas']['UpdateAvailabilityRequestDTO'],
  'mode' | 'calendar_integration_mode' | 'min_session_minutes' | 'weekly_schedule'
> & {
  mode: AvailabilityMode;
  calendar_integration_mode?: CalendarIntegrationMode;
  min_session_minutes?: number;
  weekly_schedule: WeeklyScheduleDTO;
};
export type AvailabilityResponseDTO = Omit<
  components['schemas']['AvailabilityResponseDTO'],
  'id' | 'mode' | 'weekly_schedule'
> & {
  id: string | null;
  mode: AvailabilityMode;
  weekly_schedule: WeeklyScheduleDTO;
};
export type ApiProblemDetailsDTO = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};
