export interface ScheduleSlot {
  id: string;
  dayOfWeek: number; // 0 = Sunday, 1 = Monday, etc.
  startTime: string; // HH:mm
  endTime: string;   // HH:mm
  taskId: string;
  taskTitle: string;
  isCompleted: boolean;
}

export interface WebCalTokenInfo {
  tokenUrl: string;
  isActive: boolean;
  lastAccessedAt: string | null;
}
