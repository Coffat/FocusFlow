import { isPlatformBrowser } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  PLATFORM_ID,
  computed,
  inject,
  model,
  signal,
} from '@angular/core';
import {
  AlertTriangle,
  ArrowRight,
  Award,
  BookOpen,
  CalendarClock,
  CalendarRange,
  Check,
  CheckCheck,
  ChevronRight,
  CircleCheck,
  CircleDot,
  Database,
  Flame,
  GitBranch,
  LUCIDE_ICONS,
  Lock,
  LucideAngularModule,
  LucideIconProvider,
  Pause,
  PenLine,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Timer,
} from 'lucide-angular';

export type WorkspaceTab = 'dag' | 'schedule' | 'pomodoro';
export type DagNodeId = 'indexing' | 'hexagonal' | 'outbox';
export type DagNodeStatus = 'COMPLETED' | 'IN_PROGRESS' | 'PENDING';

export interface DagNodeDetail {
  readonly id: DagNodeId;
  readonly title: string;
  readonly status: DagNodeStatus;
  readonly statusLabel: string;
  readonly effortMinutes: number;
  readonly effortLabel: string;
  readonly sessionSummary: string;
  readonly prerequisiteLabel: string;
  readonly dagValidatorStatus: string;
  readonly ragSourceTitle: string;
  readonly ragChunkId: string;
  readonly ragExcerpt: string;
  readonly gateChecks: readonly {
    readonly tier: string;
    readonly label: string;
    readonly detail: string;
  }[];
}

export interface ScheduleDiffBlock {
  readonly id: string;
  readonly daySlot: string;
  readonly title: string;
  readonly durationLabel: string;
  readonly beforeLabel: string;
  readonly afterLabel: string;
  readonly isSoftOverflow?: boolean;
  readonly badgeLabel: string;
}

@Component({
  selector: 'app-interactive-workspace',
  standalone: true,
  imports: [LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        ArrowRight,
        Award,
        BookOpen,
        CalendarClock,
        CalendarRange,
        Check,
        CheckCheck,
        ChevronRight,
        CircleCheck,
        CircleDot,
        Database,
        Flame,
        GitBranch,
        Lock,
        Pause,
        PenLine,
        Play,
        RotateCcw,
        ShieldCheck,
        Sparkles,
        Timer,
      }),
    },
  ],
  templateUrl: './interactive-workspace.component.html',
  styleUrl: './interactive-workspace.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InteractiveWorkspaceComponent {
  private static readonly TAB_ORDER: readonly WorkspaceTab[] = ['dag', 'schedule', 'pomodoro'];
  private static readonly AUTO_PLAY_INTERVAL_MS = 6000;
  private static readonly TIMER_POLL_INTERVAL_MS = 250;
  private static readonly POMODORO_DURATION_MS = 25 * 60 * 1000;
  private static readonly MVS_DURATION_MS = 15 * 60 * 1000;
  static readonly MIN_TAKEAWAY_CHARS = 20;

  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);

  readonly activeTab = model<WorkspaceTab>('dag');
  readonly isAutoPlayPaused = signal<boolean>(false);
  readonly isHovering = signal<boolean>(false);

  // Tab 1: DAG Roadmap State
  readonly selectedDagNodeId = signal<DagNodeId>('hexagonal');
  readonly dagNodes: readonly DagNodeDetail[] = [
    {
      id: 'indexing',
      title: 'PostgreSQL Indexing & Query Plan',
      status: 'COMPLETED',
      statusLabel: 'COMPLETED',
      effortMinutes: 60,
      effortLabel: '60 phút',
      sessionSummary: '2 phiên',
      prerequisiteLabel: 'Root Node — Không có tác vụ tiên quyết',
      dagValidatorStatus: 'DagCycleValidator: Hợp lệ (0 chu trình • Root node đã hoàn tất)',
      ragSourceTitle: 'PostgreSQL 16 Indexing & EXPLAIN ANALYZE Guide',
      ragChunkId: 'rag_chunk #104',
      ragExcerpt:
        'Ưu tiên Composite B-Tree theo thứ tự chọn lọc (user_id, scheduled_date) và Partial Index cho outbox_events WHERE processed_at IS NULL.',
      gateChecks: [
        { tier: 'Tier 1', label: 'Pydantic Schema (30–120m)', detail: '60 phút nằm trong ngưỡng hợp lệ' },
        { tier: 'Tier 2', label: 'Deterministic Rule Engine', detail: 'DAG topological order đã xác minh' },
        { tier: 'Tier 3', label: 'Pedagogical Judge', detail: 'Đủ căn cứ RAG & tiêu chí hoàn thành' },
      ],
    },
    {
      id: 'hexagonal',
      title: 'Hexagonal Ports & Adapters',
      status: 'IN_PROGRESS',
      statusLabel: 'IN_PROGRESS',
      effortMinutes: 90,
      effortLabel: '90 phút',
      sessionSummary: 'Đang thực thi',
      prerequisiteLabel: 'Phụ thuộc: PostgreSQL Indexing & Query Plan (Đã hoàn tất)',
      dagValidatorStatus: 'DagCycleValidator: Hợp lệ (0 chu trình • Mở khóa an toàn)',
      ragSourceTitle: 'Architecture ADR-002 & Clean Architecture Notes',
      ragChunkId: 'rag_chunk #218',
      ragExcerpt:
        'Domain layer thuần Python, không phụ thuộc FastAPI hay SQLAlchemy. Giao tiếp liên context qua Query Port và Outbox Event cùng AsyncUnitOfWork.',
      gateChecks: [
        { tier: 'Tier 1', label: 'Pydantic Schema (30–120m)', detail: '90 phút nằm trong ngưỡng hợp lệ' },
        { tier: 'Tier 2', label: 'Deterministic Rule Engine', detail: 'import-linter & ranh giới Port/Adapter đạt chuẩn' },
        { tier: 'Tier 3', label: 'Pedagogical Judge', detail: 'Phù hợp trình độ Learner Model 4×3 hiện tại' },
      ],
    },
    {
      id: 'outbox',
      title: 'Taskiq Outbox & Idempotent Consumer',
      status: 'PENDING',
      statusLabel: 'PENDING',
      effortMinutes: 90,
      effortLabel: '90 phút',
      sessionSummary: 'Khóa bởi DAG — chờ hoàn tất Hexagonal',
      prerequisiteLabel: 'Chờ hoàn tất: Hexagonal Ports & Adapters',
      dagValidatorStatus: 'DagCycleValidator: Hợp lệ (Đang khóa bởi cạnh tiên quyết DAG)',
      ragSourceTitle: 'ADR-005 Taskiq Redis Streams & Outbox Pattern',
      ragChunkId: 'rag_chunk #309',
      ragExcerpt:
        'Ghi outbox_events trong cùng transaction với business state; consumer khử trùng lặp idempotent qua bảng processed_events.',
      gateChecks: [
        { tier: 'Tier 1', label: 'Pydantic Schema (30–120m)', detail: '90 phút nằm trong ngưỡng hợp lệ' },
        { tier: 'Tier 2', label: 'Deterministic Rule Engine', detail: 'Phát hiện cạnh phụ thuộc chưa hoàn tất (BLOCKED)' },
        { tier: 'Tier 3', label: 'Pedagogical Judge', detail: 'Chỉ mở thực thi sau khi nắm vững Port/Adapter' },
      ],
    },
  ];

  readonly selectedDagNode = computed<DagNodeDetail>(
    () => this.dagNodes.find((node) => node.id === this.selectedDagNodeId()) ?? this.dagNodes[1]
  );

  // Tab 2: Schedule Proposal State (BUSR-02 & BUSR-04)
  readonly proposalApplied = signal<boolean>(false);
  readonly scheduleDiffBlocks: readonly ScheduleDiffBlock[] = [
    {
      id: 'mon-block',
      daySlot: 'T2 • 19:30–20:30',
      title: 'PostgreSQL Indexing & Query Plan',
      durationLabel: '60 phút',
      beforeLabel: 'OfficialSchedule: 19:30–20:30',
      afterLabel: 'Giữ nguyên (Đã hoàn tất 2 phiên)',
      badgeLabel: 'Không đổi',
    },
    {
      id: 'wed-block',
      daySlot: 'T4 • 19:30–21:00',
      title: 'Hexagonal Ports & Adapters',
      durationLabel: '90 phút',
      beforeLabel: 'OfficialSchedule: Chưa xếp slot',
      afterLabel: 'Đề xuất: Khối học sâu 90 phút',
      badgeLabel: 'Mới (Draft)',
    },
    {
      id: 'fri-block',
      daySlot: 'T6 • 20:15–21:45',
      title: 'Taskiq Outbox & Idempotent Consumer',
      durationLabel: '90 phút',
      beforeLabel: 'OfficialSchedule: 20:00–21:30',
      afterLabel: 'Đề xuất: 20:15–21:45 (+15 phút sau mốc 21:30)',
      isSoftOverflow: true,
      badgeLabel: 'Soft Overflow +15m',
    },
  ];

  // Tab 3: Timestamp-based Pomodoro / MVS & TakeawayGuard (OS-01)
  readonly isMvsMode = signal<boolean>(false);
  readonly sessionDurationMs = computed<number>(() =>
    this.isMvsMode()
      ? InteractiveWorkspaceComponent.MVS_DURATION_MS
      : InteractiveWorkspaceComponent.POMODORO_DURATION_MS
  );
  readonly isTimerRunning = signal<boolean>(false);
  readonly sessionCompleted = signal<boolean>(false);

  private targetEndTimeMs: number | null = null;
  private remainingMsWhenPaused: number = InteractiveWorkspaceComponent.POMODORO_DURATION_MS;
  private readonly remainingMs = signal<number>(InteractiveWorkspaceComponent.POMODORO_DURATION_MS);

  readonly timerSeconds = computed<number>(() => Math.max(0, Math.ceil(this.remainingMs() / 1000)));
  readonly formattedTime = computed<string>(() => {
    const totalSecs = this.timerSeconds();
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  });

  readonly scratchpadNote = signal<string>(
    'Domain layer thuần Python, không import SQLAlchemy hay FastAPI; mọi I/O đi qua Port.'
  );
  readonly takeawayLength = computed<number>(() => this.scratchpadNote().trim().length);
  readonly minTakeawayChars = InteractiveWorkspaceComponent.MIN_TAKEAWAY_CHARS;
  readonly canCompleteSession = computed<boolean>(
    () => this.takeawayLength() >= InteractiveWorkspaceComponent.MIN_TAKEAWAY_CHARS
  );

  readonly isEffectiveAutoPlayPaused = computed<boolean>(
    () => this.isAutoPlayPaused() || this.isHovering() || this.isTimerRunning()
  );

  private timerInterval: ReturnType<typeof setInterval> | null = null;
  private autoPlayInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.syncAutoPlayTimer();

    this.destroyRef.onDestroy(() => {
      this.pauseTimer();
      this.clearAutoPlayInterval();
    });
  }

  onShellMouseEnter(): void {
    this.isHovering.set(true);
    this.clearAutoPlayInterval();
  }

  onShellMouseLeave(): void {
    this.isHovering.set(false);
    this.syncAutoPlayTimer();
  }

  setTab(tab: WorkspaceTab): void {
    this.activeTab.set(tab);
    this.pauseAutoPlayManually();
  }

  toggleAutoPlay(): void {
    this.isAutoPlayPaused.update((paused) => !paused);
    this.syncAutoPlayTimer();
  }

  selectDagNode(nodeId: DagNodeId): void {
    this.selectedDagNodeId.set(nodeId);
    this.pauseAutoPlayManually();
  }

  applyProposal(): void {
    this.proposalApplied.set(true);
    this.pauseAutoPlayManually();
  }

  resetProposal(): void {
    this.proposalApplied.set(false);
    this.pauseAutoPlayManually();
  }

  setMvsMode(mvs: boolean): void {
    this.pauseTimer();
    this.isMvsMode.set(mvs);
    const fullMs = mvs
      ? InteractiveWorkspaceComponent.MVS_DURATION_MS
      : InteractiveWorkspaceComponent.POMODORO_DURATION_MS;
    this.remainingMsWhenPaused = fullMs;
    this.remainingMs.set(fullMs);
    this.sessionCompleted.set(false);
    this.pauseAutoPlayManually();
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
    if (this.remainingMsWhenPaused <= 0) {
      const fullMs = this.sessionDurationMs();
      this.remainingMsWhenPaused = fullMs;
      this.remainingMs.set(fullMs);
    }

    this.targetEndTimeMs = Date.now() + this.remainingMsWhenPaused;
    this.isTimerRunning.set(true);
    this.pauseAutoPlayManually();
    this.sessionCompleted.set(false);
    this.syncRemainingFromClock();

    if (isPlatformBrowser(this.platformId)) {
      this.timerInterval = setInterval(() => {
        this.syncRemainingFromClock();
      }, InteractiveWorkspaceComponent.TIMER_POLL_INTERVAL_MS);
    }
  }

  pauseTimer(): void {
    if (this.targetEndTimeMs !== null) {
      const remaining = Math.max(0, this.targetEndTimeMs - Date.now());
      this.remainingMsWhenPaused = remaining;
      this.remainingMs.set(remaining);
      this.targetEndTimeMs = null;
    }
    this.isTimerRunning.set(false);
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  resetTimer(): void {
    this.pauseTimer();
    const fullMs = this.sessionDurationMs();
    this.remainingMsWhenPaused = fullMs;
    this.remainingMs.set(fullMs);
    this.sessionCompleted.set(false);
  }

  completeSession(): void {
    if (!this.canCompleteSession()) {
      return;
    }
    this.pauseTimer();
    this.sessionCompleted.set(true);
  }

  onScratchpadInput(event: Event): void {
    const target = event.target;
    let nextValue: string | null = null;
    if (target instanceof HTMLTextAreaElement) {
      nextValue = target.value;
    } else if (target && typeof target === 'object' && 'value' in target && typeof target.value === 'string') {
      nextValue = target.value;
    }

    if (nextValue !== null) {
      this.scratchpadNote.set(nextValue);
      this.pauseAutoPlayManually();
      if (nextValue.trim().length < InteractiveWorkspaceComponent.MIN_TAKEAWAY_CHARS) {
        this.sessionCompleted.set(false);
      }
    }
  }

  scrollTo(elementId: string, event?: Event): void {
    if (event) {
      event.preventDefault();
    }
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
    const element = document.getElementById(elementId);
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  private advanceTab(): void {
    const currentIndex = InteractiveWorkspaceComponent.TAB_ORDER.indexOf(this.activeTab());
    const nextIndex = (currentIndex + 1) % InteractiveWorkspaceComponent.TAB_ORDER.length;
    this.activeTab.set(InteractiveWorkspaceComponent.TAB_ORDER[nextIndex]);
  }

  private syncRemainingFromClock(): void {
    if (this.targetEndTimeMs === null) {
      return;
    }
    const remaining = Math.max(0, this.targetEndTimeMs - Date.now());
    this.remainingMs.set(remaining);
    if (remaining <= 0) {
      this.remainingMsWhenPaused = 0;
      this.targetEndTimeMs = null;
      this.isTimerRunning.set(false);
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }
    }
  }

  private pauseAutoPlayManually(): void {
    this.isAutoPlayPaused.set(true);
    this.clearAutoPlayInterval();
  }

  private syncAutoPlayTimer(): void {
    if (!isPlatformBrowser(this.platformId) || this.isEffectiveAutoPlayPaused()) {
      this.clearAutoPlayInterval();
      return;
    }
    if (!this.autoPlayInterval) {
      this.autoPlayInterval = setInterval(() => {
        this.advanceTab();
      }, InteractiveWorkspaceComponent.AUTO_PLAY_INTERVAL_MS);
    }
  }

  private clearAutoPlayInterval(): void {
    if (this.autoPlayInterval) {
      clearInterval(this.autoPlayInterval);
      this.autoPlayInterval = null;
    }
  }
}
