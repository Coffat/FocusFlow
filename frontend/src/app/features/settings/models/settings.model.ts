import type { components } from '../../../core/api/schema';

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  soundEnabled: boolean;
  defaultPomodoroDuration: number;
  shortBreakDuration: number;
  longBreakDuration: number;
  aiCreditsLimit?: number;
  aiCreditsUsed?: number;
}

export type AIQuotaResponseDTO = components['schemas']['AIQuotaResponseDTO'];
export type ChangePasswordRequestDTO = components['schemas']['ChangePasswordRequestDTO'];
export type WebcalStatusResponseDTO = components['schemas']['WebcalStatusResponseDTO'];
export type WebcalRotateResponseDTO = components['schemas']['WebcalRotateResponseDTO'];
export type WebcalRevokeResponseDTO = components['schemas']['WebcalRevokeResponseDTO'];
export type AccountDataExportDTO = components['schemas']['AccountDataExportDTO'];
