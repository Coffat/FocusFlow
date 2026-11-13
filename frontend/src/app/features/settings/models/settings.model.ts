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
