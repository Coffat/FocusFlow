import type { components } from '../../../core/api/schema';

export type ProfileResponseDTO = components['schemas']['ProfileResponseDTO'];
export type UpdateProfileRequestDTO = components['schemas']['UpdateProfileRequestDTO'];
export type LearnerMemoryResponseDTO = components['schemas']['LearnerMemoryResponseDTO'];
export type UpdateLearnerMemoryRequestDTO = components['schemas']['UpdateLearnerMemoryRequestDTO'];
export type ResetLearnerMemoryRequestDTO = components['schemas']['ResetLearnerMemoryRequestDTO'];

export interface SrlMetrics {
  optSessionMinutes: number;
  completionRateBias: number;
  learningStyle: string;
}
