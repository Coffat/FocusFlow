import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval } from 'rxjs';
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Coffee,
  ExternalLink,
  Lock,
  Minimize2,
  Pause,
  Play,
  RefreshCw,
  Square,
  Target,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
} from 'lucide-angular';
import {
  BreakType,
  ClockSize,
  ClockStyleId,
  MilestoneContextSummary,
  StudySessionResponse,
  TaskResponse,
  TimerTabMode,
} from '../models/workspace.model';

interface ModeTabItem {
  readonly id: TimerTabMode;
  readonly label: string;
  readonly testId: string;
}

interface RulerTick {
  readonly index: number;
  readonly major: boolean;
}

export interface StudyQuote {
  readonly quote: string;
  readonly author: string;
}

export const STUDY_QUOTES: readonly StudyQuote[] = [
  {
    quote: 'Sự tập trung sâu là siêu năng lực trong nền kinh tế mới.',
    author: 'Cal Newport',
  },
  {
    quote: 'Bạn không vươn tới tầm cao của mục tiêu, bạn rơi xuống mức độ của hệ thống mình xây dựng.',
    author: 'James Clear',
  },
  {
    quote: 'Không phải chúng ta có ít thời gian, mà là chúng ta lãng phí quá nhiều.',
    author: 'Seneca',
  },
  {
    quote: 'Chất lượng không phải là một hành động, đó là một thói quen.',
    author: 'Aristotle',
  },
  {
    quote: 'Nếu bạn không thể giải thích điều gì một cách đơn giản, bạn chưa hiểu đủ sâu.',
    author: 'Richard Feynman',
  },
  {
    quote: 'Kỷ luật là cầu nối giữa mục tiêu và thành tựu.',
    author: 'Jim Rohn',
  },
  {
    quote: 'Học tập không bao giờ làm tâm trí mệt mỏi.',
    author: 'Leonardo da Vinci',
  },
  {
    quote: 'Hãy làm việc gì đó mỗi ngày giúp bạn tiến gần hơn một bước tới tương lai mình muốn.',
    author: 'Marcus Aurelius',
  },
  {
    quote: 'Đầu tư vào tri thức luôn mang lại lợi tức cao nhất.',
    author: 'Benjamin Franklin',
  },
  {
    quote: 'Việc lớn được tạo thành từ chuỗi những việc nhỏ được gom lại.',
    author: 'Vincent van Gogh',
  },
  {
    quote: 'Bí quyết để tiến về phía trước là bắt đầu ngay bây giờ.',
    author: 'Mark Twain',
  },
  {
    quote: 'Một giờ tập trung trọn vẹn đáng giá hơn cả ngày làm việc hời hợt.',
    author: 'Cal Newport',
  },
];

const RING_RADIUS = 114;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

const RULER_TICKS: readonly RulerTick[] = Array.from({ length: 29 }, (_, index) => ({
  index,
  major: index % 4 === 0,
}));

function extractSafeHttpUrl(raw: unknown): string | null {
  if (typeof raw !== 'string') return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      return parsed.toString();
    }
    return null;
  } catch {
    return null;
  }
}

@Component({
  selector: 'ff-workspace-clock',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        CheckCircle2,
        ChevronDown,
        ChevronUp,
        Clock,
        Coffee,
        ExternalLink,
        Lock,
        Minimize2,
        Pause,
        Play,
        RefreshCw,
        Square,
        Target,
      }),
    },
  ],
  styles: [
    `
      .font-editorial {
        font-family: 'Newsreader', Georgia, serif;
        font-variant-numeric: tabular-nums;
      }
      .font-digital {
        font-family: 'Geist', ui-sans-serif, system-ui, sans-serif;
        font-variant-numeric: tabular-nums;
      }
      .flip-card {
        position: relative;
        transition: transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
      }
      @media (prefers-reduced-motion: reduce) {
        .flip-card,
        .breathing-dot,
        .clock-progress {
          transition: none !important;
          animation: none !important;
        }
      }
      @keyframes subtle-breathe {
        0%,
        100% {
          opacity: 0.35;
        }
        50% {
          opacity: 1;
        }
      }
      .breathing-dot {
        animation: subtle-breathe 2s ease-in-out infinite;
      }
    `,
  ],
  template: `
    <section
      aria-label="Đồng hồ phiên học"
      class="w-full py-3 sm:py-6 px-2 sm:px-4 text-[var(--ws-text-primary,#1b1c1c)] flex flex-col items-center space-y-5 sm:space-y-6"
    >
      <!-- Top Area: Mode Switcher + Compact Active Learning Context -->
      <div class="w-full flex flex-col items-center gap-3">
        <div
          role="tablist"
          aria-label="Chế độ đồng hồ"
          class="inline-flex flex-wrap items-center justify-center gap-1 p-1 rounded-full bg-[var(--ws-surface-control,var(--surface-container-lowest,rgba(255,255,255,0.78)))] backdrop-blur-sm border border-[var(--ws-border,var(--outline-variant,#bfc9c0))]"
        >
          @for (tab of modeTabs; track tab.id) {
            @let locked = isTabLocked(tab.id);
            @let active = activeTabMode() === tab.id;
            <button
              type="button"
              role="tab"
              [attr.data-testid]="tab.testId"
              [attr.aria-selected]="active"
              [attr.aria-disabled]="locked"
              [disabled]="locked"
              [title]="locked ? 'Đang trong phiên học' : tab.label"
              (click)="onTabClick(tab.id)"
              class="inline-flex items-center gap-1.5 px-3 sm:px-3.5 py-1.5 rounded-full text-[12px] font-medium tracking-[0.01em] transition-colors"
              [class]="
                active
                  ? 'bg-[var(--ws-text-primary,#111111)] text-[var(--ws-surface-control,#ffffff)]'
                  : locked
                    ? 'text-[var(--ws-text-muted,#707972)] opacity-45 cursor-not-allowed'
                    : 'text-[var(--ws-text-muted,#707972)] hover:text-[var(--ws-text-primary,#1b1c1c)] cursor-pointer'
              "
            >
              @if (locked) {
                <lucide-icon name="lock" [size]="11" aria-hidden="true"></lucide-icon>
              }
              <span>{{ tab.label }}</span>
            </button>
          }
        </div>

        <!-- Compact Active Learning Context -->
        @if (activeTask(); as task) {
          <div
            data-testid="active-task-context"
            class="w-full max-w-xl flex flex-col items-center gap-2 text-center"
          >
            <div
              class="inline-flex flex-wrap items-center justify-center gap-x-2 gap-y-1 px-3.5 py-1.5 rounded-2xl bg-[var(--ws-surface-control,var(--surface-container-lowest,rgba(255,255,255,0.72)))] border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] text-xs text-[var(--ws-text-muted,#707972)]"
            >
              @if (task.roadmap_title) {
                <span class="truncate max-w-[140px] sm:max-w-[200px]">{{ task.roadmap_title }}</span>
                <span aria-hidden="true">·</span>
              }
              @if (task.milestone_sequence !== null && task.milestone_sequence !== undefined) {
                <span>
                  Mốc #{{ task.milestone_sequence }}@if (task.milestone_title) {: {{ task.milestone_title }}}
                </span>
                <span aria-hidden="true">·</span>
              } @else if (task.milestone_title) {
                <span class="truncate max-w-[160px] sm:max-w-[200px]">{{ task.milestone_title }}</span>
                <span aria-hidden="true">·</span>
              }
              <strong class="font-semibold text-[var(--ws-text-primary,#1b1c1c)] truncate max-w-[200px] sm:max-w-[260px]">
                {{ task.title }}
              </strong>
              <span aria-hidden="true">·</span>
              <span class="font-digital tabular-nums">Ước lượng {{ task.estimated_minutes }}p</span>

              @if (safeResourceUrl(); as resourceUrl) {
                <span aria-hidden="true">·</span>
                <a
                  [href]="resourceUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="active-task-resource-link"
                  class="inline-flex items-center gap-1 font-medium text-[var(--ws-accent,#246B4A)] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ws-accent,#246B4A)] rounded"
                >
                  <span>Tài liệu</span>
                  <lucide-icon name="external-link" [size]="11" aria-hidden="true"></lucide-icon>
                </a>
              }

              @if (hasObjectiveDetails()) {
                <span aria-hidden="true">·</span>
                <button
                  type="button"
                  data-testid="toggle-objective-btn"
                  [attr.aria-expanded]="showObjectiveDetails()"
                  (click)="toggleObjectiveDetails()"
                  class="inline-flex items-center gap-1 font-medium text-[var(--ws-text-primary,#1b1c1c)] hover:text-[var(--ws-accent,#246B4A)] cursor-pointer transition-colors"
                >
                  <lucide-icon name="target" [size]="11" aria-hidden="true"></lucide-icon>
                  <span>Mục tiêu &amp; Tiêu chí</span>
                  <lucide-icon
                    [name]="showObjectiveDetails() ? 'chevron-up' : 'chevron-down'"
                    [size]="12"
                    aria-hidden="true"
                  ></lucide-icon>
                </button>
              }
            </div>

            @if (hasObjectiveDetails() && showObjectiveDetails()) {
              <div
                data-testid="objective-details-panel"
                class="w-full max-w-lg text-left rounded-xl border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-[var(--ws-surface-control,var(--surface-container-lowest,rgba(255,255,255,0.88)))] px-3.5 py-2.5 text-xs text-[var(--ws-text-primary,#1b1c1c)] space-y-1.5"
              >
                @if (task.description) {
                  <p class="m-0 text-[var(--ws-text-muted,#707972)] leading-relaxed">
                    {{ task.description }}
                  </p>
                }
                @if (milestoneContext()?.learningOutcomes?.length) {
                  <div>
                    <span class="font-medium text-[var(--ws-text-primary,#1b1c1c)]">Mục tiêu mốc:</span>
                    <ul class="mt-0.5 mb-0 pl-4 list-disc text-[var(--ws-text-muted,#707972)] space-y-0.5">
                      @for (outcome of milestoneContext()!.learningOutcomes; track $index) {
                        <li>{{ outcome }}</li>
                      }
                    </ul>
                  </div>
                }
                @if (milestoneContext()?.completionCriteria) {
                  <p class="m-0 text-[var(--ws-text-muted,#707972)]">
                    <span class="font-medium text-[var(--ws-text-primary,#1b1c1c)]">Tiêu chí hoàn thành:</span>
                    {{ milestoneContext()!.completionCriteria }}
                  </p>
                }
              </div>
            }
          </div>
        }
      </div>

      <!-- Center: Main Clock Display -->
      <div class="w-full flex flex-col items-center gap-3">
        <div
          data-testid="workspace-timer-display"
          aria-live="off"
          class="w-full flex flex-col items-center justify-center py-1 sm:py-2"
        >
          @switch (clockStyle()) {
            @case ('editorial') {
              <div class="w-full max-w-md flex flex-col items-center gap-4 text-center">
                <span class="text-[10px] uppercase tracking-[0.18em] font-medium text-[var(--ws-text-muted,#707972)]">
                  {{ clockModeCaption() }}
                </span>
                @if (showSeconds()) {
                  <div class="font-editorial font-light tracking-[-0.03em] leading-none" [class]="heroDigitSizeClass()">
                    {{ formattedPrimaryTime() }}
                  </div>
                } @else {
                  <div class="font-editorial font-light tracking-[-0.03em] leading-none inline-flex items-center gap-2.5" [class]="heroDigitSizeClass()">
                    <span>{{ formattedNoSecondsTime() }}</span>
                    @if (isCurrentlyTicking()) {
                      <span class="inline-block w-2 h-2 rounded-full bg-[var(--ws-accent,#246B4A)] breathing-dot" aria-hidden="true"></span>
                    }
                  </div>
                }

                <!-- Whisper-thin architectural drafting ruler -->
                <div class="w-full max-w-[280px] mx-auto space-y-1.5 pt-1" aria-hidden="true">
                  <div class="relative h-[1px] w-full bg-[var(--ws-border,var(--outline-variant,#bfc9c0))]/60 overflow-hidden">
                    <div
                      class="clock-progress h-full bg-[var(--ws-accent,#246B4A)] transition-[width] duration-300 ease-out"
                      [style.width.%]="activeProgress()"
                    ></div>
                  </div>
                  <div class="flex items-start justify-between w-full">
                    @for (tick of rulerTicks; track tick.index) {
                      <span
                        class="block w-[1px]"
                        [class]="tick.major ? 'h-2.5 bg-[var(--ws-text-primary,#1b1c1c)]/35' : 'h-1.5 bg-[var(--ws-border,var(--outline-variant,#bfc9c0))]/60'"
                      ></span>
                    }
                  </div>
                </div>
              </div>
            }

            @case ('flip') {
              <div class="flex flex-col items-center gap-3.5">
                <span class="text-[10px] uppercase tracking-[0.16em] font-medium text-[var(--ws-text-muted,#707972)]">
                  {{ clockModeCaption() }}
                </span>
                <div class="flex items-center gap-2.5 sm:gap-3.5">
                  <div
                    class="flip-card relative flex items-center justify-center rounded-[6px] border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-[var(--ws-surface-control,var(--surface-container-lowest,#ffffff))] px-5 py-3.5 min-w-[5.5rem] sm:min-w-[7rem]"
                  >
                    <span class="font-digital font-normal tracking-tight tabular-nums leading-none" [class]="flipDigitSizeClass()">
                      {{ flipPrimaryBlock() }}
                    </span>
                    <span
                      class="pointer-events-none absolute inset-x-0 top-1/2 h-[1px] bg-[var(--ws-border,var(--outline-variant,#bfc9c0))]/65"
                      aria-hidden="true"
                    ></span>
                  </div>

                  @if (showSeconds()) {
                    <span class="font-digital font-extralight text-[var(--ws-text-muted,#707972)]" [class]="flipDigitSizeClass()">:</span>
                    <div
                      class="flip-card relative flex items-center justify-center rounded-[6px] border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-[var(--ws-surface-control,var(--surface-container-lowest,#ffffff))] px-5 py-3.5 min-w-[5.5rem] sm:min-w-[7rem]"
                    >
                      <span class="font-digital font-normal tracking-tight tabular-nums leading-none" [class]="flipDigitSizeClass()">
                        {{ secondsString() }}
                      </span>
                      <span
                        class="pointer-events-none absolute inset-x-0 top-1/2 h-[1px] bg-[var(--ws-border,var(--outline-variant,#bfc9c0))]/65"
                        aria-hidden="true"
                      ></span>
                    </div>
                  } @else if (activeTabMode() !== 'stopwatch') {
                    <span class="text-xs font-medium text-[var(--ws-text-muted,#707972)] tracking-wide">phút</span>
                  }
                </div>
              </div>
            }

            @case ('minimal') {
              <div class="flex flex-col items-center gap-3 text-center">
                <span class="text-[10px] uppercase tracking-[0.16em] font-medium text-[var(--ws-text-muted,#707972)]">
                  {{ clockModeCaption() }}
                </span>
                @if (showSeconds()) {
                  <div class="font-digital font-extralight tracking-[-0.03em] leading-none" [class]="heroDigitSizeClass()">
                    {{ formattedPrimaryTime() }}
                  </div>
                } @else {
                  <div class="font-digital font-extralight tracking-[-0.03em] leading-none inline-flex items-center gap-2.5" [class]="heroDigitSizeClass()">
                    <span>{{ formattedNoSecondsTime() }}</span>
                    @if (isCurrentlyTicking()) {
                      <span class="inline-block w-2 h-2 rounded-full bg-[var(--ws-accent,#246B4A)] breathing-dot" aria-hidden="true"></span>
                    }
                  </div>
                }
              </div>
            }

            @default {
              <!-- Ring style (Default) -->
              <div class="flex flex-col items-center gap-4">
                <div
                  class="relative flex items-center justify-center w-[264px] h-[264px] min-[390px]:w-[288px] min-[390px]:h-[288px] sm:w-[324px] sm:h-[324px] max-w-full"
                >
                  <svg
                    viewBox="0 0 260 260"
                    class="w-full h-full"
                    aria-hidden="true"
                  >
                    <circle
                      cx="130"
                      cy="130"
                      [attr.r]="ringRadius"
                      fill="none"
                      stroke="var(--ws-border, #bfc9c0)"
                      stroke-width="6"
                    />
                    <circle
                      cx="130"
                      cy="130"
                      [attr.r]="ringRadius"
                      fill="none"
                      stroke="var(--ws-accent, #246B4A)"
                      stroke-width="6.5"
                      stroke-linecap="round"
                      transform="rotate(-90 130 130)"
                      [attr.stroke-dasharray]="ringCircumference"
                      [attr.stroke-dashoffset]="ringDashOffset()"
                      class="clock-progress transition-[stroke-dashoffset] duration-300 ease-out"
                    />
                  </svg>

                  <!-- Inside the Ring: Status + Time + Subtitle + Max 2 Controls -->
                  <div class="absolute inset-0 flex flex-col items-center justify-center text-center px-6 gap-2">
                    <!-- Status Icon + Explicit Text Label -->
                    <div
                      class="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.14em] font-medium"
                      [class]="ringStatusTextClass()"
                    >
                      <lucide-icon [name]="ringStatusIcon()" [size]="12" aria-hidden="true"></lucide-icon>
                      <span>{{ ringStatusLabel() }}</span>
                    </div>

                    <!-- Time Readout -->
                    @if (showSeconds()) {
                      <div class="font-digital tabular-nums text-5xl sm:text-6xl font-light tracking-[-0.02em] leading-none text-[var(--ws-text-primary,#1b1c1c)]">
                        {{ formattedPrimaryTime() }}
                      </div>
                    } @else {
                      <div class="font-digital tabular-nums text-3xl sm:text-4xl font-light tracking-[-0.02em] leading-none inline-flex items-center gap-1.5 text-[var(--ws-text-primary,#1b1c1c)]">
                        <span>{{ formattedNoSecondsTime() }}</span>
                        @if (isCurrentlyTicking()) {
                          <span class="inline-block w-1.5 h-1.5 rounded-full bg-[var(--ws-accent,#246B4A)] breathing-dot" aria-hidden="true"></span>
                        }
                      </div>
                    }

                    <!-- Subtitle -->
                    <p class="m-0 text-[11px] font-medium text-[var(--ws-text-muted,#707972)]">
                      {{ ringSubtitle() }}
                    </p>

                    <!-- Inside-Ring Primary / Secondary Buttons (max 2) -->
                    <div class="pt-1 flex items-center justify-center gap-2">
                      @if (activeTabMode() === 'break') {
                        @if (!activeBreakType()) {
                          <button
                            type="button"
                            (click)="startBreak.emit({ type: selectedBreakType(), minutes: selectedBreakMinutes() })"
                            class="inline-flex items-center justify-center gap-1.5 min-h-[44px] min-w-[44px] px-5 py-2 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-xs sm:text-sm font-medium transition-opacity cursor-pointer"
                          >
                            <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
                            <span>Bắt đầu nghỉ</span>
                          </button>
                        } @else {
                          @if (isBreakRunning()) {
                            <button
                              type="button"
                              (click)="pauseBreak.emit()"
                              class="inline-flex items-center justify-center gap-1.5 min-h-[44px] min-w-[44px] px-4 py-2 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-xs sm:text-sm font-medium transition-opacity cursor-pointer"
                            >
                              <lucide-icon name="pause" [size]="14" aria-hidden="true"></lucide-icon>
                              <span>Tạm dừng</span>
                            </button>
                          } @else {
                            <button
                              type="button"
                              (click)="resumeBreak.emit()"
                              class="inline-flex items-center justify-center gap-1.5 min-h-[44px] min-w-[44px] px-4 py-2 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-xs sm:text-sm font-medium transition-opacity cursor-pointer"
                            >
                              <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
                              <span>Tiếp tục</span>
                            </button>
                          }
                          <button
                            type="button"
                            (click)="stopBreak.emit()"
                            class="inline-flex items-center justify-center gap-1 min-h-[44px] min-w-[44px] px-3.5 py-2 rounded-full border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-[var(--ws-surface-control,transparent)] hover:bg-[var(--ws-surface-elevated,rgba(0,0,0,0.04))] text-[var(--ws-text-primary,#1b1c1c)] text-xs font-medium transition-colors cursor-pointer"
                          >
                            <span>Bỏ qua</span>
                          </button>
                        }
                      } @else if (!activeSession()) {
                        <button
                          type="button"
                          data-testid="start-session-btn"
                          [disabled]="!canStartSession() || isSubmitting()"
                          (click)="startSession.emit()"
                          class="inline-flex items-center justify-center gap-1.5 min-h-[44px] min-w-[44px] px-6 py-2 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed text-[var(--ws-accent-contrast,#ffffff)] text-xs sm:text-sm font-medium transition-opacity cursor-pointer"
                        >
                          <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
                          <span>{{ isSubmitting() ? 'Đang tạo...' : 'Bắt đầu' }}</span>
                        </button>
                      } @else {
                        @if (isRunning()) {
                          <button
                            type="button"
                            data-testid="pause-session-btn"
                            (click)="pauseSession.emit()"
                            class="inline-flex items-center justify-center gap-1.5 min-h-[44px] min-w-[44px] px-4 py-2 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-xs sm:text-sm font-medium transition-opacity cursor-pointer"
                          >
                            <lucide-icon name="pause" [size]="14" aria-hidden="true"></lucide-icon>
                            <span>Tạm dừng</span>
                          </button>
                        } @else {
                          <button
                            type="button"
                            data-testid="resume-session-btn"
                            (click)="resumeSession.emit()"
                            class="inline-flex items-center justify-center gap-1.5 min-h-[44px] min-w-[44px] px-4 py-2 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-xs sm:text-sm font-medium transition-opacity cursor-pointer"
                          >
                            <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
                            <span>Tiếp tục</span>
                          </button>
                        }
                        <button
                          type="button"
                          data-testid="open-finalize-btn"
                          (click)="openFinalize.emit(false)"
                          class="inline-flex items-center justify-center gap-1.5 min-h-[44px] min-w-[44px] px-3.5 py-2 rounded-full border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-[var(--ws-surface-control,transparent)] hover:bg-[var(--ws-surface-elevated,rgba(0,0,0,0.04))] text-[var(--ws-text-primary,#1b1c1c)] text-xs font-medium transition-colors cursor-pointer"
                        >
                          <lucide-icon name="check-circle-2" [size]="13" aria-hidden="true"></lucide-icon>
                          <span>Hoàn tất</span>
                        </button>
                      }
                    </div>
                  </div>
                </div>

                <!-- Destructive Action cleanly OUTSIDE/BELOW the ring -->
                @if (activeTabMode() !== 'break' && activeSession()) {
                  <button
                    type="button"
                    data-testid="open-early-stop-btn"
                    (click)="openFinalize.emit(true)"
                    class="inline-flex items-center justify-center gap-1.5 min-h-[44px] px-4 py-2 rounded-full bg-transparent hover:bg-[var(--ws-danger,#ba1a1a)]/10 text-[var(--ws-text-muted,#707972)] hover:text-[var(--ws-danger,#ba1a1a)] text-xs font-medium transition-colors cursor-pointer"
                  >
                    <lucide-icon name="square" [size]="13" aria-hidden="true"></lucide-icon>
                    <span>Dừng sớm</span>
                  </button>
                }
              </div>
            }
          }
        </div>

        <!-- Single subtle inline status line -->
        @if (activeSession()) {
          <p
            role="status"
            aria-live="polite"
            data-testid="heartbeat-status-pill"
            class="inline-flex items-center justify-center gap-1.5 text-[11px] tracking-[0.02em]"
            [class]="heartbeatInlineClass()"
          >
            <span class="inline-block w-1.5 h-1.5 rounded-full" [class]="heartbeatDotClass()" aria-hidden="true"></span>
            <span>{{ activeSession()?.session_mode }} · {{ heartbeatLabel() }}</span>
          </p>
        } @else if (focusScore() !== null) {
          <p class="text-[11px] tracking-[0.02em] text-[var(--ws-text-muted,#707972)]">
            Tập trung: {{ focusScore() }}/100
          </p>
        }
      </div>

      <!-- Bottom Area: Duration Presets, Non-Ring Action Controls, Quote / Focus Mode Exit -->
      @if (!activeSession() && (activeTabMode() === 'pomodoro' || activeTabMode() === 'mvs')) {
        <div class="flex flex-wrap items-center justify-center gap-1.5">
          @for (preset of durationPresets(); track preset) {
            <button
              type="button"
              (click)="selectDuration.emit(preset)"
              [attr.aria-pressed]="plannedMinutes() === preset"
              class="px-3 py-1 rounded-full text-xs font-digital transition-colors cursor-pointer"
              [class]="
                plannedMinutes() === preset
                  ? 'bg-[var(--ws-surface-elevated,var(--surface-container-low,#f4f5f4))] text-[var(--ws-text-primary,#1b1c1c)] font-medium underline decoration-[var(--ws-accent,#246B4A)] decoration-1 underline-offset-4'
                  : 'text-[var(--ws-text-muted,#707972)] hover:text-[var(--ws-text-primary,#1b1c1c)] hover:bg-[var(--ws-surface-elevated,var(--surface-container-low,#f4f5f4))]'
              "
            >
              {{ preset }}p
            </button>
          }

          <label class="inline-flex items-center gap-1 pl-2 text-[11px] text-[var(--ws-text-muted,#707972)]">
            <input
              type="number"
              [min]="minCustomMinutes()"
              [max]="maxCustomMinutes()"
              [value]="plannedMinutes()"
              (change)="onCustomDurationChange($any($event.target).value)"
              aria-label="Thời lượng tùy chỉnh (phút)"
              class="w-14 px-1.5 py-0.5 rounded-md border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-transparent text-xs font-digital text-center text-[var(--ws-text-primary,#1b1c1c)] focus:outline-none focus:border-[var(--ws-accent,#246B4A)]"
            />
            <span>p</span>
          </label>
        </div>
      }

      @if (activeTabMode() === 'break' && !activeBreakType()) {
        <div class="flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            (click)="selectBreakPreset('short', 5)"
            [attr.aria-pressed]="selectedBreakType() === 'short'"
            class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs transition-colors cursor-pointer"
            [class]="
              selectedBreakType() === 'short'
                ? 'bg-[var(--ws-surface-elevated,var(--surface-container-low,#f4f5f4))] text-[var(--ws-text-primary,#1b1c1c)] font-medium underline decoration-[var(--ws-accent,#246B4A)] decoration-1 underline-offset-4'
                : 'text-[var(--ws-text-muted,#707972)] hover:text-[var(--ws-text-primary,#1b1c1c)] hover:bg-[var(--ws-surface-elevated,var(--surface-container-low,#f4f5f4))]'
            "
          >
            <lucide-icon name="coffee" [size]="12" aria-hidden="true"></lucide-icon>
            <span>Nghỉ ngắn 5p</span>
          </button>
          <button
            type="button"
            (click)="selectBreakPreset('long', 15)"
            [attr.aria-pressed]="selectedBreakType() === 'long'"
            class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs transition-colors cursor-pointer"
            [class]="
              selectedBreakType() === 'long'
                ? 'bg-[var(--ws-surface-elevated,var(--surface-container-low,#f4f5f4))] text-[var(--ws-text-primary,#1b1c1c)] font-medium underline decoration-[var(--ws-accent,#246B4A)] decoration-1 underline-offset-4'
                : 'text-[var(--ws-text-muted,#707972)] hover:text-[var(--ws-text-primary,#1b1c1c)] hover:bg-[var(--ws-surface-elevated,var(--surface-container-low,#f4f5f4))]'
            "
          >
            <lucide-icon name="coffee" [size]="12" aria-hidden="true"></lucide-icon>
            <span>Nghỉ dài 15p</span>
          </button>
        </div>
      }

      <!-- Action Controls for non-ring styles (editorial, flip, minimal) -->
      @if (clockStyle() !== 'ring') {
        <div class="flex flex-wrap items-center justify-center gap-2.5">
          @if (activeTabMode() === 'break') {
            @if (!activeBreakType()) {
              <button
                type="button"
                (click)="startBreak.emit({ type: selectedBreakType(), minutes: selectedBreakMinutes() })"
                class="inline-flex items-center gap-2 px-8 py-2.5 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-sm font-medium transition-opacity cursor-pointer"
              >
                <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
                <span>Bắt đầu nghỉ</span>
              </button>
            } @else {
              @if (isBreakRunning()) {
                <button
                  type="button"
                  (click)="pauseBreak.emit()"
                  class="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-sm font-medium transition-opacity cursor-pointer"
                >
                  <lucide-icon name="pause" [size]="14" aria-hidden="true"></lucide-icon>
                  <span>Tạm dừng nghỉ</span>
                </button>
              } @else {
                <button
                  type="button"
                  (click)="resumeBreak.emit()"
                  class="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-sm font-medium transition-opacity cursor-pointer"
                >
                  <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
                  <span>Tiếp tục nghỉ</span>
                </button>
              }
              <button
                type="button"
                (click)="stopBreak.emit()"
                class="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-transparent hover:border-[var(--ws-danger,#ba1a1a)] hover:text-[var(--ws-danger,#ba1a1a)] text-xs sm:text-sm font-medium transition-colors cursor-pointer"
              >
                <lucide-icon name="square" [size]="13" aria-hidden="true"></lucide-icon>
                <span>Kết thúc nghỉ</span>
              </button>
            }
          } @else if (!activeSession()) {
            <button
              type="button"
              data-testid="start-session-btn"
              [disabled]="!canStartSession() || isSubmitting()"
              (click)="startSession.emit()"
              class="inline-flex items-center gap-2 px-8 py-2.5 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed text-[var(--ws-accent-contrast,#ffffff)] text-sm font-medium transition-opacity cursor-pointer"
            >
              <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
              <span>{{ isSubmitting() ? 'Đang khởi tạo...' : 'Bắt đầu phiên học' }}</span>
            </button>
          } @else {
            @if (isRunning()) {
              <button
                type="button"
                data-testid="pause-session-btn"
                (click)="pauseSession.emit()"
                class="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-sm font-medium transition-opacity cursor-pointer"
              >
                <lucide-icon name="pause" [size]="14" aria-hidden="true"></lucide-icon>
                <span>Tạm dừng</span>
              </button>
            } @else {
              <button
                type="button"
                data-testid="resume-session-btn"
                (click)="resumeSession.emit()"
                class="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[var(--ws-accent,#246B4A)] hover:opacity-90 text-[var(--ws-accent-contrast,#ffffff)] text-sm font-medium transition-opacity cursor-pointer"
              >
                <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
                <span>Tiếp tục</span>
              </button>
            }

            <button
              type="button"
              data-testid="open-finalize-btn"
              (click)="openFinalize.emit(false)"
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-transparent hover:bg-[var(--ws-surface-elevated,var(--surface-container-low,#f4f5f4))] text-xs sm:text-sm font-medium transition-colors cursor-pointer"
            >
              <lucide-icon name="check-circle-2" [size]="14" aria-hidden="true"></lucide-icon>
              <span>Hoàn tất</span>
            </button>

            <button
              type="button"
              data-testid="open-early-stop-btn"
              (click)="openFinalize.emit(true)"
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-transparent hover:border-[var(--ws-danger,#ba1a1a)] hover:text-[var(--ws-danger,#ba1a1a)] text-xs sm:text-sm font-medium transition-colors cursor-pointer"
            >
              <lucide-icon name="square" [size]="13" aria-hidden="true"></lucide-icon>
              <span>Dừng sớm</span>
            </button>
          }
        </div>
      }

      @if (!activeSession() && activeTabMode() !== 'break' && (hasPendingTakeaway() || selectedTaskCount() === 0)) {
        <p class="text-center text-xs text-[var(--ws-text-muted,#707972)]">
          @if (hasPendingTakeaway()) {
            Hoàn tất Key Takeaway của phiên trước để mở khóa phiên học mới.
          } @else {
            Chọn ít nhất 1 nhiệm vụ học tập ở bảng bên để bắt đầu phiên học.
          }
        </p>
      }

      <!-- Bottom Quote Pill or Focus Mode Exit Pill -->
      @if (focusMode()) {
        <button
          type="button"
          data-testid="exit-focus-mode-btn"
          (click)="exitFocusMode.emit()"
          class="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-full border border-[var(--ws-border,var(--outline-variant,#bfc9c0))] bg-[var(--ws-surface-control,var(--surface-container-lowest,rgba(255,255,255,0.8)))] hover:bg-[var(--ws-surface-elevated,var(--surface-container-low,#f4f5f4))] text-xs font-medium text-[var(--ws-text-primary,#1b1c1c)] transition-colors cursor-pointer"
        >
          <lucide-icon name="minimize-2" [size]="13" aria-hidden="true"></lucide-icon>
          <span>Thoát chế độ tập trung (Esc)</span>
        </button>
      } @else {
        <button
          type="button"
          data-testid="encouraging-quote-pill"
          (click)="rotateQuote()"
          aria-label="Đổi câu truyền cảm hứng khác"
          title="Nhấn để đổi câu trích dẫn khác"
          class="group inline-flex max-w-xl items-center gap-2 rounded-full border border-[var(--ws-border,var(--outline-variant,#bfc9c0))]/70 bg-[var(--ws-surface-control,var(--surface-container-lowest,rgba(255,255,255,0.65)))] px-4 py-1.5 text-center text-xs text-[var(--ws-text-muted,#707972)] transition-colors hover:border-[var(--ws-accent,#246B4A)]/50 hover:text-[var(--ws-text-primary,#1b1c1c)] cursor-pointer"
        >
          <span class="leading-snug">
            “{{ currentQuote().quote }}”
            <span class="font-medium text-[var(--ws-text-primary,#1b1c1c)]/80">
              — {{ currentQuote().author }}
            </span>
          </span>
          <lucide-icon
            name="refresh-cw"
            [size]="12"
            class="shrink-0 opacity-55 transition-transform duration-200 group-hover:rotate-45 group-hover:opacity-100"
            aria-hidden="true"
          ></lucide-icon>
        </button>
      }
    </section>
  `,
})
export class WorkspaceClockComponent {
  readonly activeTabMode = input.required<TimerTabMode>();
  readonly clockStyle = input<ClockStyleId>('ring');
  readonly clockSize = input.required<ClockSize>();
  readonly showSeconds = input.required<boolean>();
  readonly activeSession = input<StudySessionResponse | null>(null);
  readonly isRunning = input.required<boolean>();
  readonly isSubmitting = input.required<boolean>();
  readonly plannedMinutes = input.required<number>();
  readonly elapsedSeconds = input.required<number>();
  readonly remainingSeconds = input.required<number>();
  readonly progressPercentage = input.required<number>();
  readonly heartbeatStatus = input.required<'idle' | 'syncing' | 'synced' | 'offline' | 'error'>();
  readonly activeBreakType = input<BreakType | null>(null);
  readonly breakDurationMinutes = input<number>(5);
  readonly breakRemainingSeconds = input<number>(300);
  readonly isBreakRunning = input<boolean>(false);
  readonly breakProgressPercentage = input<number>(0);
  readonly canStartSession = input.required<boolean>();
  readonly selectedTaskCount = input<number>(0);
  readonly hasPendingTakeaway = input<boolean>(false);
  readonly focusScore = input<number | null>(null);

  readonly activeTask = input<TaskResponse | null>(null);
  readonly milestoneContext = input<MilestoneContextSummary | null>(null);
  readonly completedPomodorosToday = input<number>(0);
  readonly focusMode = input<boolean>(false);

  readonly selectTabMode = output<TimerTabMode>();
  readonly selectDuration = output<number>();
  readonly startSession = output<void>();
  readonly pauseSession = output<void>();
  readonly resumeSession = output<void>();
  readonly openFinalize = output<boolean>();
  readonly startBreak = output<{ type: BreakType; minutes: number }>();
  readonly pauseBreak = output<void>();
  readonly resumeBreak = output<void>();
  readonly stopBreak = output<void>();
  readonly exitFocusMode = output<void>();

  readonly rulerTicks = RULER_TICKS;
  readonly ringRadius = RING_RADIUS;
  readonly ringCircumference = RING_CIRCUMFERENCE;

  readonly modeTabs: readonly ModeTabItem[] = [
    { id: 'pomodoro', label: 'Pomodoro', testId: 'mode-standard-btn' },
    { id: 'mvs', label: 'MVS', testId: 'mode-mvs-btn' },
    { id: 'stopwatch', label: 'Đếm xuôi', testId: 'mode-stopwatch-btn' },
    { id: 'break', label: 'Nghỉ ngơi', testId: 'mode-break-btn' },
  ];

  readonly selectedBreakType = signal<BreakType>('short');
  readonly selectedBreakMinutes = signal<number>(5);
  readonly showObjectiveDetails = signal<boolean>(false);
  readonly currentQuoteIndex = signal<number>(
    Math.floor(Math.random() * STUDY_QUOTES.length)
  );
  readonly currentQuote = computed<StudyQuote>(
    () => STUDY_QUOTES[this.currentQuoteIndex()]
  );

  constructor() {
    interval(60_000)
      .pipe(takeUntilDestroyed())
      .subscribe(() => {
        this.rotateQuote();
      });

    let prevSessionId: string | null | undefined;
    let prevTabMode: TimerTabMode | undefined;
    effect(() => {
      const sessionId = this.activeSession()?.id ?? null;
      const tabMode = this.activeTabMode();
      if (
        prevTabMode !== undefined &&
        (sessionId !== prevSessionId || tabMode !== prevTabMode)
      ) {
        untracked(() => this.rotateQuote());
      }
      prevSessionId = sessionId;
      prevTabMode = tabMode;
    });
  }

  readonly isSessionInProgress = computed(
    () => this.activeSession()?.status === 'IN_PROGRESS'
  );

  readonly safeResourceUrl = computed<string | null>(() => {
    const resources = this.activeTask()?.learning_resources;
    if (!resources?.length) return null;
    for (const item of resources) {
      if (!item || typeof item !== 'object') continue;
      const candidate =
        extractSafeHttpUrl(item['url']) ??
        extractSafeHttpUrl(item['href']) ??
        extractSafeHttpUrl(item['link']);
      if (candidate) return candidate;
    }
    return null;
  });

  readonly hasObjectiveDetails = computed<boolean>(() => {
    const task = this.activeTask();
    const milestone = this.milestoneContext();
    return Boolean(
      task?.description?.trim() ||
        milestone?.learningOutcomes?.length ||
        milestone?.completionCriteria?.trim()
    );
  });

  readonly durationPresets = computed<readonly number[]>(() =>
    this.activeTabMode() === 'mvs' ? [10, 15] : [25, 45, 60, 90]
  );

  readonly minCustomMinutes = computed(() => (this.activeTabMode() === 'mvs' ? 10 : 5));
  readonly maxCustomMinutes = computed(() => (this.activeTabMode() === 'mvs' ? 15 : 180));

  readonly displaySeconds = computed<number>(() => {
    const mode = this.activeTabMode();
    if (mode === 'break') {
      return this.activeBreakType()
        ? Math.max(0, this.breakRemainingSeconds())
        : Math.max(0, this.selectedBreakMinutes() * 60);
    }
    if (mode === 'stopwatch') {
      return Math.max(0, this.elapsedSeconds());
    }
    if (this.activeSession()) {
      return Math.max(0, this.remainingSeconds());
    }
    return Math.max(0, this.plannedMinutes() * 60);
  });

  readonly secondsString = computed(() =>
    String(this.displaySeconds() % 60).padStart(2, '0')
  );

  readonly formattedPrimaryTime = computed<string>(() => {
    const total = this.displaySeconds();
    if (this.activeTabMode() === 'stopwatch') {
      const hrs = Math.floor(total / 3600);
      const mins = Math.floor((total % 3600) / 60);
      const secs = total % 60;
      if (hrs > 0) {
        return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
      }
      return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  });

  readonly formattedNoSecondsTime = computed<string>(() => {
    const total = this.displaySeconds();
    if (this.activeTabMode() === 'stopwatch') {
      const hrs = Math.floor(total / 3600);
      const mins = Math.floor((total % 3600) / 60);
      return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
    }
    const mins = Math.floor(total / 60);
    return `${String(mins).padStart(2, '0')} phút`;
  });

  readonly flipPrimaryBlock = computed<string>(() => {
    const total = this.displaySeconds();
    if (this.activeTabMode() === 'stopwatch') {
      const hrs = Math.floor(total / 3600);
      const mins = Math.floor((total % 3600) / 60);
      if (!this.showSeconds() || hrs > 0) {
        return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
      }
      return String(mins).padStart(2, '0');
    }
    return String(Math.floor(total / 60)).padStart(2, '0');
  });

  readonly activeProgress = computed<number>(() => {
    if (this.activeTabMode() === 'break') {
      return Math.min(100, Math.max(0, this.breakProgressPercentage()));
    }
    if (this.activeSession()) {
      return Math.min(100, Math.max(0, this.progressPercentage()));
    }
    return 0;
  });

  readonly ringDashOffset = computed<number>(
    () => RING_CIRCUMFERENCE * (1 - this.activeProgress() / 100)
  );

  readonly isCurrentlyTicking = computed<boolean>(() =>
    this.activeTabMode() === 'break' ? this.isBreakRunning() : this.isRunning()
  );

  readonly ringStatusLabel = computed<string>(() => {
    if (this.activeTabMode() === 'break') {
      if (!this.activeBreakType()) return 'Sẵn sàng';
      return this.isBreakRunning() ? 'Đang nghỉ' : 'Tạm dừng';
    }
    if (!this.activeSession()) return 'Sẵn sàng';
    return this.isRunning() ? 'Đang học' : 'Tạm dừng';
  });

  readonly ringStatusIcon = computed<string>(() => {
    if (this.activeTabMode() === 'break') {
      if (!this.activeBreakType()) return 'coffee';
      return this.isBreakRunning() ? 'coffee' : 'pause';
    }
    if (!this.activeSession()) return 'clock';
    return this.isRunning() ? 'play' : 'pause';
  });

  readonly ringStatusTextClass = computed<string>(() => {
    if (this.activeTabMode() === 'break') {
      return this.isBreakRunning()
        ? 'text-[var(--ws-accent,#246B4A)]'
        : 'text-[var(--ws-text-muted,#707972)]';
    }
    if (!this.activeSession()) {
      return 'text-[var(--ws-text-muted,#707972)]';
    }
    return this.isRunning()
      ? 'text-[var(--ws-accent,#246B4A)]'
      : 'text-amber-700 dark:text-amber-300';
  });

  readonly ringSubtitle = computed<string>(() => {
    if (this.activeTabMode() === 'break') {
      const breakType = this.activeBreakType() ?? this.selectedBreakType();
      return breakType === 'long' ? 'Nghỉ dài phục hồi' : 'Nghỉ ngắn thư giãn';
    }
    return `Phiên tập trung ${this.completedPomodorosToday() + 1} / 4`;
  });

  readonly clockModeCaption = computed<string>(() => {
    switch (this.activeTabMode()) {
      case 'mvs':
        return 'Minimum Viable Session';
      case 'stopwatch':
        return 'Đếm xuôi thời gian';
      case 'break':
        return this.activeBreakType() === 'long'
          ? 'Nghỉ dài phục hồi'
          : 'Nghỉ ngắn thư giãn';
      default:
        return 'Pomodoro Tập Trung';
    }
  });

  readonly heroDigitSizeClass = computed<string>(() =>
    this.clockSize() === 'lg'
      ? 'text-7xl sm:text-8xl'
      : 'text-6xl sm:text-7xl'
  );

  readonly flipDigitSizeClass = computed<string>(() =>
    this.clockSize() === 'lg'
      ? 'text-5xl sm:text-6xl'
      : 'text-4xl sm:text-5xl'
  );

  readonly heartbeatLabel = computed<string>(() => {
    switch (this.heartbeatStatus()) {
      case 'syncing':
        return 'Đang đồng bộ...';
      case 'offline':
        return 'Ngoại tuyến';
      case 'error':
        return 'Lỗi đồng bộ';
      default:
        return 'Đã đồng bộ';
    }
  });

  readonly heartbeatInlineClass = computed<string>(() => {
    switch (this.heartbeatStatus()) {
      case 'offline':
        return 'text-amber-700 dark:text-amber-300';
      case 'error':
        return 'text-[var(--ws-danger,#ba1a1a)]';
      default:
        return 'text-[var(--ws-text-muted,#707972)]';
    }
  });

  readonly heartbeatDotClass = computed<string>(() => {
    switch (this.heartbeatStatus()) {
      case 'syncing':
        return 'bg-[var(--ws-text-muted,#707972)] animate-pulse';
      case 'offline':
        return 'bg-amber-500';
      case 'error':
        return 'bg-[var(--ws-danger,#ba1a1a)]';
      case 'synced':
        return 'bg-[var(--ws-accent,#246B4A)]';
      default:
        return 'bg-[var(--ws-text-muted,#707972)]';
    }
  });

  isTabLocked(tab: TimerTabMode): boolean {
    const session = this.activeSession();
    if (!session || session.status !== 'IN_PROGRESS') {
      return false;
    }
    if (tab === 'break') {
      return true;
    }
    if (session.session_mode === 'MVS') {
      return tab !== 'mvs';
    }
    if (session.session_mode === 'STANDARD') {
      return tab === 'mvs';
    }
    return false;
  }

  onTabClick(tab: TimerTabMode): void {
    if (this.isTabLocked(tab)) return;
    this.selectTabMode.emit(tab);
  }

  onCustomDurationChange(rawValue: string): void {
    const parsed = Number(rawValue);
    if (Number.isNaN(parsed)) return;
    const min = this.minCustomMinutes();
    const max = this.maxCustomMinutes();
    const clamped = Math.min(max, Math.max(min, Math.round(parsed)));
    this.selectDuration.emit(clamped);
  }

  selectBreakPreset(type: BreakType, minutes: number): void {
    this.selectedBreakType.set(type);
    this.selectedBreakMinutes.set(minutes);
  }

  toggleObjectiveDetails(): void {
    this.showObjectiveDetails.update((prev) => !prev);
  }

  rotateQuote(): void {
    if (STUDY_QUOTES.length <= 1) return;
    this.currentQuoteIndex.update((current) => {
      const offset = 1 + Math.floor(Math.random() * (STUDY_QUOTES.length - 1));
      return (current + offset) % STUDY_QUOTES.length;
    });
  }
}
