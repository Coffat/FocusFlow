import { Injectable, inject, signal, computed, effect } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';

export interface StudySessionState {
  sessionId: string | null;
  taskId: string | null;
  mode: 'pomodoro' | 'stopwatch';
  durationMinutes: number;
  remainingSeconds: number;
  isRunning: boolean;
  startedAt: number | null;
  pausedMs: number;
}

@Injectable({
  providedIn: 'root'
})
export class WorkspaceSessionService {
  private readonly http = inject(HttpClient);

  // Core reactive signals
  readonly sessionId = signal<string | null>(null);
  readonly taskId = signal<string | null>(null);
  readonly mode = signal<'pomodoro' | 'stopwatch'>('pomodoro');
  readonly durationMinutes = signal<number>(25);
  readonly remainingSeconds = signal<number>(25 * 60);
  readonly isRunning = signal<boolean>(false);
  readonly scratchpadNote = signal<string>('');

  private startedAt: number | null = null;
  private pausedMs = 0;
  private pauseTimestamp: number | null = null;

  private timerSubscription: Subscription | null = null;
  private heartbeatSubscription: Subscription | null = null;

  // Computed formatting for display
  readonly formattedTime = computed(() => {
    const totalSec = this.remainingSeconds();
    const minutes = Math.floor(totalSec / 60);
    const seconds = totalSec % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  });

  readonly progressPercentage = computed(() => {
    const total = this.durationMinutes() * 60;
    if (total === 0) return 0;
    const elapsed = total - this.remainingSeconds();
    return Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));
  });

  constructor() {
    // Listen for tab sleep / wake up to resync absolute time
    if (typeof window !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden && this.isRunning() && this.startedAt) {
          this.recalculateRemainingTime();
        }
      });
    }
  }

  startSession(sessionId: string, taskId: string, durationMinutes = 25): void {
    this.sessionId.set(sessionId);
    this.taskId.set(taskId);
    this.durationMinutes.set(durationMinutes);
    this.remainingSeconds.set(durationMinutes * 60);
    this.startedAt = Date.now();
    this.pausedMs = 0;
    this.isRunning.set(true);

    this.startCountdownTimer();
    this.startHeartbeat(sessionId);
  }

  pauseSession(): void {
    if (!this.isRunning()) return;
    this.isRunning.set(false);
    this.pauseTimestamp = Date.now();
    this.stopCountdownTimer();
  }

  resumeSession(): void {
    if (this.isRunning()) return;
    if (this.pauseTimestamp) {
      this.pausedMs += Date.now() - this.pauseTimestamp;
      this.pauseTimestamp = null;
    }
    this.isRunning.set(true);
    this.startCountdownTimer();
  }

  private startCountdownTimer(): void {
    this.stopCountdownTimer();
    this.timerSubscription = interval(1000).subscribe(() => {
      this.recalculateRemainingTime();
    });
  }

  private stopCountdownTimer(): void {
    if (this.timerSubscription) {
      this.timerSubscription.unsubscribe();
      this.timerSubscription = null;
    }
  }

  private recalculateRemainingTime(): void {
    if (!this.startedAt) return;
    const now = Date.now();
    const currentPausedMs = this.pauseTimestamp ? this.pausedMs + (now - this.pauseTimestamp) : this.pausedMs;
    const elapsedSec = Math.floor((now - this.startedAt - currentPausedMs) / 1000);
    const totalSec = this.durationMinutes() * 60;
    const remaining = Math.max(0, totalSec - elapsedSec);

    this.remainingSeconds.set(remaining);

    if (remaining === 0) {
      this.onTimerComplete();
    }
  }

  private onTimerComplete(): void {
    this.pauseSession();
    // Play completion chime / notification
  }

  private startHeartbeat(sessionId: string): void {
    this.stopHeartbeat();
    // Send heartbeat every 60 seconds (ADR-004, BUSR-09)
    this.heartbeatSubscription = interval(60000).subscribe(() => {
      if (this.isRunning()) {
        this.http.post(`/api/v1/sessions/${sessionId}/heartbeat`, {}).subscribe({
          error: (err) => console.warn('Heartbeat failed:', err)
        });
      }
    });
  }

  private stopHeartbeat(): void {
    if (this.heartbeatSubscription) {
      this.heartbeatSubscription.unsubscribe();
      this.heartbeatSubscription = null;
    }
  }
}
