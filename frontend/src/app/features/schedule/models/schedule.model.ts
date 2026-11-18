import { components } from '../../../core/api/schema';

export type WeeklyScheduleResponse = components['schemas']['WeeklyScheduleResponse'];
export type WeeklyScheduleItemResponse = components['schemas']['WeeklyScheduleItemResponse'];
export type RescheduleTaskRequest = components['schemas']['RescheduleTaskRequest'];
export type TaskResponse = components['schemas']['TaskResponse'];
export type RoadmapResponse = components['schemas']['RoadmapResponse'];
export type ScheduleProposalResponse = components['schemas']['ScheduleProposalResponse'];

export interface ScheduleDayGroup {
  localDate: string; // YYYY-MM-DD in learner local timezone
  dayLabel: string;  // e.g. 'Thứ Hai, 18/11'
  isToday: boolean;
  items: WeeklyScheduleItemResponse[];
}
