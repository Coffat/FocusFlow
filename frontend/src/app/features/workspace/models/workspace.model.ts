export interface StudyTask {
  id: string;
  title: string;
  pomodoroEstimate: number;
  pomodorosCompleted: number;
  isCompleted: boolean;
}

export interface WorkspaceConfig {
  defaultPomodoroMinutes: number;
  shortBreakMinutes: number;
  longBreakMinutes: number;
  autoStartBreaks: boolean;
}
