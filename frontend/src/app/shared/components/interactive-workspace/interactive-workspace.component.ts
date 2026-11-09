import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  model,
  signal,
} from '@angular/core';

export type WorkspaceTab = 'dag' | 'schedule' | 'pomodoro';

@Component({
  selector: 'app-interactive-workspace',
  standalone: true,
  templateUrl: './interactive-workspace.component.html',
  styleUrl: './interactive-workspace.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InteractiveWorkspaceComponent {
  private readonly destroyRef = inject(DestroyRef);

  readonly activeTab = model<WorkspaceTab>('dag');

  // Interactive Pomodoro Timer Signals
  readonly isTimerRunning = signal<boolean>(false);
  readonly timerSeconds = signal<number>(1500); // 25:00 default Pomodoro
  private timerInterval: ReturnType<typeof setInterval> | null = null;

  // Formatted timer mm:ss
  readonly formattedTime = computed(() => {
    const totalSecs = this.timerSeconds();
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  });

  // Cognitive Scratchpad Interactive Note
  readonly scratchpadNote = signal<string>(
    'Lưu ý: Domain models không được import bất kỳ dependency nào từ SQLAlchemy hay FastAPI.'
  );

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.pauseTimer();
    });
  }

  setTab(tab: WorkspaceTab): void {
    this.activeTab.set(tab);
  }

  toggleTimer(): void {
    if (this.isTimerRunning()) {
      this.pauseTimer();
    } else {
      this.startTimer();
    }
  }

  startTimer(): void {
    if (this.timerInterval) {
      return;
    }
    this.isTimerRunning.set(true);
    this.timerInterval = setInterval(() => {
      if (this.timerSeconds() > 0) {
        this.timerSeconds.update((s) => s - 1);
      } else {
        this.pauseTimer();
      }
    }, 1000);
  }

  pauseTimer(): void {
    this.isTimerRunning.set(false);
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  resetTimer(): void {
    this.pauseTimer();
    this.timerSeconds.set(1500);
  }

  onScratchpadInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null;
    if (target) {
      this.scratchpadNote.set(target.value);
    }
  }

  scrollTo(elementId: string, event?: Event): void {
    if (event) {
      event.preventDefault();
    }
    const element = document.getElementById(elementId);
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}
