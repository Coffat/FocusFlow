export type UserRole = 'learner' | 'admin';

export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  isActive: boolean;
  aiCreditsRemaining: number;
  totalStudyMinutes: number;
  currentStreakDays: number;
  createdAt: string;
}
