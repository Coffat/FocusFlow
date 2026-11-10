export interface DailyStudyMetric {
  date: string;
  minutesStudied: number;
  pomodorosCompleted: number;
}

export interface AnalyticsSummary {
  weeklyStudyHours: number;
  taskCompletionRate: number; // percentage (e.g. 92%)
  averageFocusScore: number;  // 1-100
  dailyMetrics: DailyStudyMetric[];
}
