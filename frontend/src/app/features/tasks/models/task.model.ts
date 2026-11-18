import { components } from '../../../core/api/schema';

export type TaskResponse = components['schemas']['TaskResponse'];
export type CreateTaskRequest = components['schemas']['CreateTaskRequest'];
export type UpdateTaskRequest = components['schemas']['UpdateTaskRequest'];
export type CompleteTaskRequest = components['schemas']['CompleteTaskRequest'];
export type RescheduleTaskRequest = components['schemas']['RescheduleTaskRequest'];
export type TaskDependencyResponse = components['schemas']['TaskDependencyResponse'];
export type AddTaskDependencyRequest = components['schemas']['AddTaskDependencyRequest'];
export type RoadmapResponse = components['schemas']['RoadmapResponse'];
export type RoadmapDetailResponse = components['schemas']['RoadmapDetailResponse'];
export type MilestoneResponse = components['schemas']['MilestoneResponse'];

export type TaskFilterTab = 'ALL' | 'SCHEDULED' | 'BACKLOG' | 'COMPLETED';
