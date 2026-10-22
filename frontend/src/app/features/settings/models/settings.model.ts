export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  soundEnabled: boolean;
  defaultPomodoroDuration: number;
  aiCreditsLimit: number;
  aiCreditsUsed: number;
}
