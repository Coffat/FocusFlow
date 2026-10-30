/**
 * OpenAPI 3.1 schema definitions for FocusFlow frontend.
 * Generated / aligned with backend DTOs (FR-AVAIL v2.0).
 */

export interface paths {
  '/api/v1/availabilities/me': {
    get: {
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['AvailabilityResponseDTO'];
          };
        };
        422: {
          content: {
            'application/json': components['schemas']['ApiProblemDetailsDTO'];
          };
        };
      };
    };
    put: {
      requestBody: {
        content: {
          'application/json': components['schemas']['UpdateAvailabilityRequestDTO'];
        };
      };
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['AvailabilityResponseDTO'];
          };
        };
        422: {
          content: {
            'application/json': components['schemas']['ApiProblemDetailsDTO'];
          };
        };
      };
    };
  };
}

export interface components {
  schemas: {
    TimeSlotDTO: {
      start: string;
      end: string;
      end_day_offset?: number;
    };
    AllowedWindowDTO: {
      start: string;
      end: string;
    };
    PreferredPeriod: 'MORNING' | 'AFTERNOON' | 'EVENING' | 'ANY';
    AvailabilityMode: 'MODE_A' | 'MODE_B';
    CalendarIntegrationMode: 'NONE' | 'EXPORT_ICS' | 'CONNECTED';
    DayOfWeek:
      | 'monday'
      | 'tuesday'
      | 'wednesday'
      | 'thursday'
      | 'friday'
      | 'saturday'
      | 'sunday';
    DayScheduleDTO: {
      enabled: boolean;
      quota_hours: number;
      time_slots: components['schemas']['TimeSlotDTO'][];
      allowed_window?: components['schemas']['AllowedWindowDTO'];
      preferred_period?: components['schemas']['PreferredPeriod'] | string;
      min_session_minutes?: number;
    };
    WeeklyScheduleDTO: {
      monday: components['schemas']['DayScheduleDTO'];
      tuesday: components['schemas']['DayScheduleDTO'];
      wednesday: components['schemas']['DayScheduleDTO'];
      thursday: components['schemas']['DayScheduleDTO'];
      friday: components['schemas']['DayScheduleDTO'];
      saturday: components['schemas']['DayScheduleDTO'];
      sunday: components['schemas']['DayScheduleDTO'];
    };
    UpdateAvailabilityRequestDTO: {
      mode: components['schemas']['AvailabilityMode'];
      calendar_integration_mode?: components['schemas']['CalendarIntegrationMode'];
      min_session_minutes?: number;
      weekly_schedule: components['schemas']['WeeklyScheduleDTO'];
    };
    AvailabilityResponseDTO: {
      id: string | null;
      user_id: string;
      mode: components['schemas']['AvailabilityMode'];
      calendar_integration_mode: string;
      min_session_minutes: number;
      weekly_schedule: components['schemas']['WeeklyScheduleDTO'];
      total_weekly_hours: number;
      updated_at: string;
    };
    ApiProblemDetailsDTO: {
      code: string;
      message: string;
      details?: Record<string, unknown>;
    };
  };
}
