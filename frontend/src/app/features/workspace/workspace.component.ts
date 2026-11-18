import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';
import {
  AlertTriangle,
  CheckCircle2,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
  PanelLeftOpen,
  RefreshCw,
  ShieldAlert,
  StickyNote,
} from 'lucide-angular';
import { WorkspaceSessionService } from '../../core/services/workspace-session.service';
import { ButtonDirective } from '../../shared/ui/button/button.directive';
import { AmbientAudioService } from './data/ambient-audio.service';
import { WorkspaceStudioStore } from './data/workspace-studio.store';
import {
  BreakType,
  FinalizeSessionRequest,
  SessionMode,
  StickyNoteColor,
  TaskResponse,
  TimerTabMode,
} from './models/workspace.model';
import { WorkspaceClockComponent } from './ui/workspace-clock.component';
import { WorkspaceFinalizeModalComponent } from './ui/workspace-finalize-modal.component';
import { WorkspaceLeftPanelComponent } from './ui/workspace-left-panel.component';
import { WorkspaceSceneBackdropComponent } from './ui/workspace-scene-backdrop.component';
import { WorkspaceStickyNoteCardComponent } from './ui/workspace-sticky-note-card.component';
import { WorkspaceStickyNotesPanelComponent } from './ui/workspace-sticky-notes-panel.component';
import { WorkspaceToolPanelComponent } from './ui/workspace-tool-panel.component';

@Component({
  selector: 'app-workspace',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './workspace.component.scss',
  imports: [
    RouterLink,
    LucideAngularModule,
    ButtonDirective,
    WorkspaceSceneBackdropComponent,
    WorkspaceLeftPanelComponent,
    WorkspaceToolPanelComponent,
    WorkspaceClockComponent,
    WorkspaceStickyNoteCardComponent,
    WorkspaceStickyNotesPanelComponent,
    WorkspaceFinalizeModalComponent,
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        CheckCircle2,
        PanelLeftOpen,
        RefreshCw,
        ShieldAlert,
        StickyNote,
      }),
    },
  ],
  template: `
    <div
      class="workspace-studio relative min-h-[calc(100vh-115px)] w-full overflow-x-clip flex flex-col justify-center transition-colors duration-300"
      [attr.data-ws-contrast]="studioStore.isDarkSurface() ? 'dark' : 'light'"
      [class.text-white]="isDarkScene()"
    >
      <ff-workspace-scene-backdrop
        [scene]="studioStore.scene()"
        [zenDimmed]="studioStore.shieldConfig().zenLockEnabled && sessionService.isRunning()"
      />

      <!-- Top-Left Pill to Reopen Left Panel on Desktop (when collapsed & not in Focus Mode) -->
      @if (!studioStore.focusMode()) {
        @if (studioStore.leftPanelCollapsed()) {
          <button
            type="button"
            data-testid="open-left-panel-btn"
            (click)="openLeftPanel()"
            aria-label="Mở bảng điều khiển"
            class="hidden lg:inline-flex absolute top-4 left-4 z-20 items-center gap-1.5 h-8 px-3 rounded-full border text-xs font-medium transition-colors cursor-pointer backdrop-blur-sm"
            [class]="studioBarBtnClass(false)"
          >
            <lucide-icon name="panel-left-open" [size]="14" aria-hidden="true"></lucide-icon>
            <span>Mở bảng điều khiển</span>
          </button>
        }

        <!-- Mobile/Tablet (< lg) Compact Top Bar -->
        <div
          class="relative z-20 flex lg:hidden items-center justify-between gap-2 px-3 pt-3 w-full"
        >
          <button
            type="button"
            data-testid="mobile-open-left-panel-btn"
            (click)="openLeftPanel()"
            aria-label="Mở bảng nhiệm vụ"
            class="inline-flex items-center gap-1.5 h-9 px-3 rounded-full border text-xs font-medium transition-colors cursor-pointer backdrop-blur-sm"
            [class]="studioBarBtnClass(mobileLeftOpen())"
          >
            <lucide-icon name="panel-left-open" [size]="14" aria-hidden="true"></lucide-icon>
            <span>Bảng nhiệm vụ</span>
          </button>

          <button
            type="button"
            data-testid="mobile-open-notes-btn"
            (click)="studioStore.toggleNotesPanel()"
            aria-label="Mở ghi chú"
            [attr.aria-pressed]="studioStore.notesPanelOpen()"
            class="inline-flex items-center gap-1.5 h-9 px-3 rounded-full border text-xs font-medium transition-colors cursor-pointer backdrop-blur-sm"
            [class]="studioBarBtnClass(studioStore.notesPanelOpen())"
          >
            <lucide-icon name="sticky-note" [size]="14" aria-hidden="true"></lucide-icon>
            <span>Ghi chú</span>
            @if (studioStore.notes().length > 0) {
              <span class="font-mono text-[11px] opacity-80">({{ studioStore.notes().length }})</span>
            }
          </button>
        </div>
      }

      <!-- Subtle Top-Center Floating Alert Banners -->
      @if (
        sessionService.errorState() ||
        sessionService.lastFinalizedSession() ||
        studioStore.showReturnBanner() ||
        switchTaskWarning() ||
        (sessionService.todayFocus()?.overdue_tasks_count ?? 0) > 0
      ) {
        <div class="relative z-20 w-full max-w-xl mx-auto px-3 pt-4 flex flex-col gap-2">
          @if (sessionService.todayFocus(); as tf) {
            @if (tf.overdue_tasks_count > 0) {
              <div class="flex justify-center">
                <a
                  routerLink="/tasks"
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold no-underline transition-opacity hover:opacity-90 border"
                  [class]="
                    isDarkScene()
                      ? 'bg-amber-500/20 text-amber-200 border-amber-400/40'
                      : 'bg-amber-500/15 text-amber-800 dark:text-amber-300 border-amber-500/30'
                  "
                >
                  <lucide-icon name="alert-triangle" [size]="13" aria-hidden="true"></lucide-icon>
                  <span>{{ tf.overdue_tasks_count }} việc quá hạn</span>
                </a>
              </div>
            }
          }

          <!-- Global Error Banner -->
          @if (sessionService.errorState(); as err) {
            <div
              role="alert"
              data-testid="workspace-error-banner"
              class="p-3.5 rounded-xl border border-red-500/40 bg-red-500/10 text-red-900 dark:text-red-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              [class.bg-red-950/75]="isDarkScene()"
              [class.text-red-100]="isDarkScene()"
            >
              <div class="space-y-0.5">
                <div class="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <lucide-icon name="alert-triangle" [size]="14" aria-hidden="true"></lucide-icon>
                  <span>{{ err.isOffline ? 'Mất kết nối mạng' : 'Không thể thực hiện thao tác' }}</span>
                  @if (err.code) {
                    <span class="font-mono px-1.5 py-0.5 rounded bg-red-500/15 text-[11px]">{{ err.code }}</span>
                  }
                </div>
                <p class="text-xs sm:text-sm m-0">{{ err.message }}</p>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <button type="button" appButton variant="outline" size="sm" (click)="refreshWorkspace()">
                  Thử lại
                </button>
                <button type="button" appButton variant="ghost" size="sm" (click)="sessionService.clearError()">
                  Đóng
                </button>
              </div>
            </div>
          }

          <!-- Session Finalized Success Banner -->
          @if (sessionService.lastFinalizedSession(); as finished) {
            <div
              role="status"
              data-testid="session-finalized-banner"
              class="p-3.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              [class.bg-emerald-950/75]="isDarkScene()"
              [class.text-emerald-100]="isDarkScene()"
            >
              <div class="flex items-start gap-2.5">
                <lucide-icon name="check-circle-2" [size]="18" class="text-emerald-600 shrink-0 mt-0.5" aria-hidden="true"></lucide-icon>
                <div class="space-y-0.5">
                  <div class="text-sm font-semibold">Đã hoàn tất phiên học ({{ finished.actual_minutes }} phút)</div>
                  @if (finished.takeaway_content) {
                    <p class="text-xs opacity-90 line-clamp-2 m-0">Takeaway: "{{ finished.takeaway_content }}"</p>
                  }
                </div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <a routerLink="/analytics" appButton variant="outline" size="sm">Xem Phân tích</a>
                <button type="button" appButton variant="ghost" size="sm" (click)="sessionService.clearFinalizedBanner()">
                  Đóng
                </button>
              </div>
            </div>
          }

          <!-- Focus Shield Return Banner -->
          @if (studioStore.showReturnBanner()) {
            <div
              role="status"
              data-testid="focus-return-banner"
              class="p-3 rounded-xl border border-amber-500/40 bg-amber-500/15 text-amber-950 dark:text-amber-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5"
              [class.bg-amber-950/80]="isDarkScene()"
              [class.text-amber-100]="isDarkScene()"
            >
              <div class="flex items-center gap-2 text-xs sm:text-sm">
                <lucide-icon name="shield-alert" [size]="16" class="shrink-0" aria-hidden="true"></lucide-icon>
                <span>
                  Bạn vừa rời khỏi tab học tập (tổng {{ studioStore.distractionCount() }} lần sao nhãng trong phiên).
                </span>
              </div>
              <button
                type="button"
                appButton
                variant="outline"
                size="sm"
                data-testid="dismiss-return-banner-btn"
                (click)="studioStore.dismissReturnBanner()"
              >
                Tôi đã quay lại tập trung
              </button>
            </div>
          }

          <!-- Switch Outside Task Warning Banner -->
          @if (switchTaskWarning(); as warningMsg) {
            <div
              role="status"
              data-testid="switch-task-warning-banner"
              class="p-3 rounded-xl border border-amber-500/40 bg-amber-500/15 text-amber-950 dark:text-amber-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5"
              [class.bg-amber-950/80]="isDarkScene()"
              [class.text-amber-100]="isDarkScene()"
            >
              <div class="flex items-center gap-2 text-xs sm:text-sm">
                <lucide-icon name="alert-triangle" [size]="16" class="shrink-0" aria-hidden="true"></lucide-icon>
                <span>{{ warningMsg }}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  appButton
                  variant="outline"
                  size="sm"
                  data-testid="switch-task-end-session-btn"
                  (click)="onEndSessionFromWarning()"
                >
                  Kết thúc phiên
                </button>
                <button
                  type="button"
                  appButton
                  variant="ghost"
                  size="sm"
                  (click)="dismissSwitchTaskWarning()"
                >
                  Đóng
                </button>
              </div>
            </div>
          }
        </div>
      }

      <!-- Loading State -->
      @if (sessionService.isLoading() && !sessionService.todayFocus()) {
        <div class="relative z-10 w-full max-w-md mx-auto px-4 py-8">
          <div class="p-8 rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] flex flex-col items-center justify-center gap-3 text-center">
            <lucide-icon name="refresh-cw" [size]="24" class="animate-spin text-[var(--primary)]" aria-hidden="true"></lucide-icon>
            <p class="text-sm text-[var(--muted-foreground)] m-0">Đang đồng bộ phiên học và hàng đợi hôm nay...</p>
          </div>
        </div>
      } @else if (studioStore.focusMode()) {
        <!-- Focus Mode: ONLY Ring Timer + Active Task Context + Exit Button -->
        <main
          data-testid="workspace-focus-mode-region"
          class="relative z-10 flex-1 flex items-center justify-center px-4 py-8"
        >
          <div class="w-full max-w-2xl">
            <ff-workspace-clock
              [activeTabMode]="activeTabMode()"
              [clockStyle]="studioStore.clockStyle()"
              [clockSize]="studioStore.clockSize()"
              [showSeconds]="studioStore.showSeconds()"
              [activeSession]="sessionService.activeSession()"
              [isRunning]="sessionService.isRunning()"
              [isSubmitting]="sessionService.isSubmitting()"
              [plannedMinutes]="plannedMinutes()"
              [elapsedSeconds]="sessionService.elapsedSeconds()"
              [remainingSeconds]="sessionService.remainingSeconds()"
              [progressPercentage]="sessionService.progressPercentage()"
              [heartbeatStatus]="sessionService.heartbeatStatus()"
              [activeBreakType]="sessionService.activeBreakType()"
              [breakDurationMinutes]="sessionService.breakDurationMinutes()"
              [breakRemainingSeconds]="sessionService.breakRemainingSeconds()"
              [isBreakRunning]="sessionService.isBreakRunning()"
              [breakProgressPercentage]="sessionService.breakProgressPercentage()"
              [canStartSession]="canStartSession()"
              [selectedTaskCount]="selectedTaskIds().length"
              [hasPendingTakeaway]="sessionService.pendingTakeawaySession() !== null"
              [focusScore]="studioStore.focusScore()"
              [activeTask]="activeTask()"
              [milestoneContext]="milestoneContext()"
              [completedPomodorosToday]="sessionService.completedPomodorosToday()"
              [focusMode]="true"
              (selectTabMode)="selectTabMode($event)"
              (selectDuration)="onPlannedMinutesChange($event)"
              (startSession)="startStudySession()"
              (pauseSession)="sessionService.pauseSession()"
              (resumeSession)="sessionService.resumeSession()"
              (openFinalize)="openFinalizeModal($event)"
              (startBreak)="onStartBreak($event)"
              (pauseBreak)="sessionService.pauseBreak()"
              (resumeBreak)="sessionService.resumeBreak()"
              (stopBreak)="sessionService.stopBreak()"
              (exitFocusMode)="studioStore.setFocusMode(false)"
            />
          </div>
        </main>
      } @else if (studioStore.leftPanelCollapsed()) {
        <!-- Collapsed Layout: Centered Clock + Optional Right Notes Region -->
        <main class="relative z-10 flex-1 flex items-center justify-center px-4 py-8">
          <div class="w-full max-w-2xl">
            <ff-workspace-clock
              [activeTabMode]="activeTabMode()"
              [clockStyle]="studioStore.clockStyle()"
              [clockSize]="studioStore.clockSize()"
              [showSeconds]="studioStore.showSeconds()"
              [activeSession]="sessionService.activeSession()"
              [isRunning]="sessionService.isRunning()"
              [isSubmitting]="sessionService.isSubmitting()"
              [plannedMinutes]="plannedMinutes()"
              [elapsedSeconds]="sessionService.elapsedSeconds()"
              [remainingSeconds]="sessionService.remainingSeconds()"
              [progressPercentage]="sessionService.progressPercentage()"
              [heartbeatStatus]="sessionService.heartbeatStatus()"
              [activeBreakType]="sessionService.activeBreakType()"
              [breakDurationMinutes]="sessionService.breakDurationMinutes()"
              [breakRemainingSeconds]="sessionService.breakRemainingSeconds()"
              [isBreakRunning]="sessionService.isBreakRunning()"
              [breakProgressPercentage]="sessionService.breakProgressPercentage()"
              [canStartSession]="canStartSession()"
              [selectedTaskCount]="selectedTaskIds().length"
              [hasPendingTakeaway]="sessionService.pendingTakeawaySession() !== null"
              [focusScore]="studioStore.focusScore()"
              [activeTask]="activeTask()"
              [milestoneContext]="milestoneContext()"
              [completedPomodorosToday]="sessionService.completedPomodorosToday()"
              [focusMode]="false"
              (selectTabMode)="selectTabMode($event)"
              (selectDuration)="onPlannedMinutesChange($event)"
              (startSession)="startStudySession()"
              (pauseSession)="sessionService.pauseSession()"
              (resumeSession)="sessionService.resumeSession()"
              (openFinalize)="openFinalizeModal($event)"
              (startBreak)="onStartBreak($event)"
              (pauseBreak)="sessionService.pauseBreak()"
              (resumeBreak)="sessionService.resumeBreak()"
              (stopBreak)="sessionService.stopBreak()"
              (exitFocusMode)="studioStore.setFocusMode(false)"
            />
          </div>
        </main>

        @if (showNotesRegion()) {
          @if (studioStore.notesPanelOpen()) {
            <div
              class="fixed inset-0 z-30 bg-black/35 lg:hidden"
              (click)="studioStore.setNotesPanelOpen(false)"
              aria-hidden="true"
            ></div>
          }
          <div
            [class]="
              studioStore.notesPanelOpen()
                ? 'fixed inset-y-0 right-0 z-40 w-[330px] max-w-[92vw] p-3 bg-[var(--surface)] shadow-xl overflow-y-auto lg:fixed lg:inset-y-auto lg:top-16 lg:right-6 lg:z-30 lg:w-[320px] lg:max-w-none lg:p-0 lg:bg-transparent lg:shadow-none'
                : 'hidden lg:block lg:fixed lg:top-16 lg:right-6 lg:z-20 lg:w-[320px]'
            "
          >
            <ff-workspace-sticky-notes-panel
              [composerOpen]="studioStore.notesPanelOpen()"
              [visiblePinnedNotes]="studioStore.visiblePinnedNotes()"
              [collectionNotes]="studioStore.collectionNotes()"
              [hasActiveSession]="sessionService.activeSession() !== null"
              [heartbeatStatus]="sessionService.heartbeatStatus()"
              [serializedLength]="studioStore.serializedNotesLength()"
              [isOverLimit]="studioStore.isScratchpadOverLimit()"
              [undoNotice]="studioStore.undoNotice()"
              (closeComposer)="studioStore.setNotesPanelOpen(false)"
              (pinNewNote)="onPinNewNote($event)"
              (updateNote)="studioStore.updateNote($event.id, { title: $event.title, content: $event.content })"
              (unpinNote)="studioStore.unpinNote($event)"
              (pinNote)="studioStore.togglePin($event)"
              (changeColor)="studioStore.updateNote($event.id, { color: $event.color })"
              (deleteNote)="studioStore.deleteNote($event)"
              (copyToTakeaway)="openFinalizeModal(false)"
              (undoAction)="studioStore.undoLastNoteAction()"
            />
          </div>
        }
      } @else {
        <!-- Symmetric 3-Column Desktop Grid -->
        <div
          class="relative z-10 w-full max-w-[1520px] mx-auto px-3 sm:px-6 py-4 grid grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)_320px] items-center gap-6 min-h-[calc(100vh-115px)]"
        >
          <!-- Left Column: Consolidated Left Panel + Inline Tool Panel -->
          @if (mobileLeftOpen()) {
            <div
              class="fixed inset-0 z-30 bg-black/40 lg:hidden"
              (click)="mobileLeftOpen.set(false)"
              aria-hidden="true"
            ></div>
          }
          <div
            data-testid="workspace-left-region"
            [class]="
              mobileLeftOpen()
                ? 'fixed inset-y-0 left-0 z-40 w-[320px] max-w-[88vw] p-3 bg-[var(--surface)] shadow-xl overflow-y-auto lg:static lg:z-auto lg:w-full lg:max-w-none lg:p-0 lg:bg-transparent lg:shadow-none lg:overflow-visible lg:self-center'
                : 'hidden lg:block lg:self-center'
            "
          >
            <ff-workspace-left-panel
              [progress]="sessionService.todayProgress()"
              [completedPomodorosToday]="sessionService.completedPomodorosToday()"
              [localDate]="sessionService.todayFocus()?.local_date ?? ''"
              [tasks]="sessionService.availableTasks()"
              [activeSession]="sessionService.activeSession()"
              [activeSessionTasks]="sessionService.activeSessionTasks()"
              [pendingTakeawaySession]="sessionService.pendingTakeawaySession()"
              [selectedTaskIds]="selectedTaskIds()"
              [isSubmitting]="sessionService.isSubmitting()"
              [togglingTaskId]="togglingTaskId()"
              [isLoading]="sessionService.isLoading()"
              [isFullscreen]="studioStore.isFullscreen()"
              [focusMode]="studioStore.focusMode()"
              [activeFocusTaskId]="sessionService.activeFocusTaskId()"
              [activeTool]="studioStore.activeToolPopover()"
              [isAnySoundPlaying]="audioService.isAnySoundPlaying()"
              [isMuted]="audioService.isMuted()"
              [tabGuardEnabled]="studioStore.shieldConfig().tabGuardEnabled"
              [focusScore]="studioStore.focusScore()"
              [notesPanelOpen]="studioStore.notesPanelOpen()"
              [notesCount]="studioStore.notes().length"
              (toggleSelectTask)="toggleTaskSelection($event)"
              (toggleTaskComplete)="onToggleTaskComplete($event)"
              (resolveDebt)="onResolveDebt($event)"
              (collapsePanel)="onLeftPanelCollapse()"
              (refreshWorkspace)="refreshWorkspace()"
              (toggleFullscreen)="toggleFullscreen()"
              (toggleFocusMode)="studioStore.toggleFocusMode()"
              (selectFocusTask)="sessionService.setActiveFocusTask($event)"
              (attemptSwitchOutsideTask)="onAttemptSwitchOutsideTask($event)"
              (toggleTool)="studioStore.toggleToolPopover($event)"
              (toggleNotesPanel)="studioStore.toggleNotesPanel()"
            >
              <ff-workspace-tool-panel
                left-tool-panel
                [activeTool]="studioStore.activeToolPopover()"
                [scene]="studioStore.scene()"
                [clockStyle]="studioStore.clockStyle()"
                [clockSize]="studioStore.clockSize()"
                [showSeconds]="studioStore.showSeconds()"
                [showInTabTitle]="studioStore.showInTabTitle()"
                [masterVolume]="audioService.masterVolume()"
                [isMuted]="audioService.isMuted()"
                [chimeEnabled]="audioService.chimeEnabled()"
                [channels]="audioService.channels()"
                [embedProvider]="audioService.embedProvider()"
                [safeEmbedUrl]="audioService.safeEmbedResourceUrl()"
                [embedRawInput]="audioService.embedRawInput()"
                [embedError]="audioService.embedError()"
                [shieldConfig]="studioStore.shieldConfig()"
                [distractionCount]="studioStore.distractionCount()"
                [focusScore]="studioStore.focusScore()"
                [isFullscreen]="studioStore.isFullscreen()"
                (closePanel)="studioStore.closeToolPopover()"
                (selectScene)="studioStore.setScene($event)"
                (selectClockStyle)="studioStore.setClockStyle($event)"
                (selectClockSize)="studioStore.setClockSize($event)"
                (toggleShowSeconds)="studioStore.toggleShowSeconds()"
                (toggleShowInTabTitle)="studioStore.toggleShowInTabTitle()"
                (toggleChannel)="audioService.toggleChannel($event)"
                (changeChannelVolume)="audioService.setChannelVolume($event.id, $event.volume)"
                (changeMasterVolume)="audioService.setMasterVolume($event)"
                (toggleMute)="audioService.toggleMute()"
                (toggleChime)="audioService.toggleChime()"
                (applySceneAudio)="audioService.applyScenePreset(studioStore.scene())"
                (applyMediaEmbed)="audioService.setMediaEmbed($event)"
                (clearMediaEmbed)="audioService.clearMediaEmbed()"
                (toggleTabGuard)="studioStore.setTabGuardEnabled($event)"
                (toggleZenLock)="studioStore.setZenLockEnabled($event)"
                (toggleFullscreen)="toggleFullscreen()"
                (addBlockedSite)="studioStore.addBlockedSite($event)"
                (removeBlockedSite)="studioStore.removeBlockedSite($event)"
                (addParkingThought)="studioStore.addThought($event)"
                (toggleParkingThought)="studioStore.toggleThought($event)"
                (removeParkingThought)="studioStore.removeThought($event)"
              />
            </ff-workspace-left-panel>
          </div>

          <!-- Center Column: Dead-Center Minimalist Clock -->
          <main class="flex flex-col items-center justify-center min-w-0">
            <div class="w-full max-w-2xl">
              <ff-workspace-clock
                [activeTabMode]="activeTabMode()"
                [clockStyle]="studioStore.clockStyle()"
                [clockSize]="studioStore.clockSize()"
                [showSeconds]="studioStore.showSeconds()"
                [activeSession]="sessionService.activeSession()"
                [isRunning]="sessionService.isRunning()"
                [isSubmitting]="sessionService.isSubmitting()"
                [plannedMinutes]="plannedMinutes()"
                [elapsedSeconds]="sessionService.elapsedSeconds()"
                [remainingSeconds]="sessionService.remainingSeconds()"
                [progressPercentage]="sessionService.progressPercentage()"
                [heartbeatStatus]="sessionService.heartbeatStatus()"
                [activeBreakType]="sessionService.activeBreakType()"
                [breakDurationMinutes]="sessionService.breakDurationMinutes()"
                [breakRemainingSeconds]="sessionService.breakRemainingSeconds()"
                [isBreakRunning]="sessionService.isBreakRunning()"
                [breakProgressPercentage]="sessionService.breakProgressPercentage()"
                [canStartSession]="canStartSession()"
                [selectedTaskCount]="selectedTaskIds().length"
                [hasPendingTakeaway]="sessionService.pendingTakeawaySession() !== null"
                [focusScore]="studioStore.focusScore()"
                [activeTask]="activeTask()"
                [milestoneContext]="milestoneContext()"
                [completedPomodorosToday]="sessionService.completedPomodorosToday()"
                [focusMode]="false"
                (selectTabMode)="selectTabMode($event)"
                (selectDuration)="onPlannedMinutesChange($event)"
                (startSession)="startStudySession()"
                (pauseSession)="sessionService.pauseSession()"
                (resumeSession)="sessionService.resumeSession()"
                (openFinalize)="openFinalizeModal($event)"
                (startBreak)="onStartBreak($event)"
                (pauseBreak)="sessionService.pauseBreak()"
                (resumeBreak)="sessionService.resumeBreak()"
                (stopBreak)="sessionService.stopBreak()"
                (exitFocusMode)="studioStore.setFocusMode(false)"
              />
            </div>
          </main>

          <!-- Right Column: Sticky Notes Panel or Symmetric Spacer -->
          @if (showNotesRegion()) {
            @if (studioStore.notesPanelOpen()) {
              <div
                class="fixed inset-0 z-30 bg-black/35 lg:hidden"
                (click)="studioStore.setNotesPanelOpen(false)"
                aria-hidden="true"
              ></div>
            }
            <div
              [class]="
                studioStore.notesPanelOpen()
                  ? 'fixed inset-y-0 right-0 z-40 w-[330px] max-w-[92vw] p-3 bg-[var(--surface)] shadow-xl overflow-y-auto lg:static lg:z-30 lg:w-[320px] lg:max-w-none lg:p-0 lg:bg-transparent lg:shadow-none lg:overflow-visible lg:self-center shrink-0'
                  : 'hidden lg:block lg:w-[320px] lg:self-center shrink-0'
              "
            >
              <ff-workspace-sticky-notes-panel
                [composerOpen]="studioStore.notesPanelOpen()"
                [visiblePinnedNotes]="studioStore.visiblePinnedNotes()"
                [collectionNotes]="studioStore.collectionNotes()"
                [hasActiveSession]="sessionService.activeSession() !== null"
                [heartbeatStatus]="sessionService.heartbeatStatus()"
                [serializedLength]="studioStore.serializedNotesLength()"
                [isOverLimit]="studioStore.isScratchpadOverLimit()"
                [undoNotice]="studioStore.undoNotice()"
                (closeComposer)="studioStore.setNotesPanelOpen(false)"
                (pinNewNote)="onPinNewNote($event)"
                (updateNote)="studioStore.updateNote($event.id, { title: $event.title, content: $event.content })"
                (unpinNote)="studioStore.unpinNote($event)"
                (pinNote)="studioStore.togglePin($event)"
                (changeColor)="studioStore.updateNote($event.id, { color: $event.color })"
                (deleteNote)="studioStore.deleteNote($event)"
                (copyToTakeaway)="openFinalizeModal(false)"
                (undoAction)="studioStore.undoLastNoteAction()"
              />
            </div>
          } @else {
            <div class="hidden lg:block" aria-hidden="true"></div>
          }
        </div>
      }

      <!-- Desktop Floating Pinned Notes Overlay (>= lg) -->
      @if (!studioStore.focusMode() && studioStore.visiblePinnedNotes().length > 0) {
        <div
          data-testid="desktop-floating-notes-layer"
          aria-label="Ghi chú đã ghim trên Studio"
          class="hidden lg:block pointer-events-none absolute inset-0 z-20 overflow-hidden"
        >
          @for (note of studioStore.visiblePinnedNotes(); track note.id; let idx = $index) {
            <ff-workspace-sticky-note-card
              [note]="note"
              [index]="idx"
              [isEditing]="floatingEditingNoteId() === note.id"
              [hasActiveSession]="sessionService.activeSession() !== null"
              [draggableMode]="true"
              (unpin)="studioStore.unpinNote($event)"
              (updateNote)="studioStore.updateNote($event.id, { title: $event.title, content: $event.content })"
              (changeColor)="studioStore.updateNote($event.id, { color: $event.color })"
              (deleteNote)="studioStore.deleteNote($event)"
              (copyToTakeaway)="openFinalizeModal(false)"
              (startEdit)="floatingEditingNoteId.set($event)"
              (stopEdit)="floatingEditingNoteId.set(null)"
              (bringToFront)="studioStore.bringNoteToFront($event)"
              (moveNote)="studioStore.updateNotePosition($event.id, $event.posX, $event.posY)"
            />
          }
        </div>
      }

      <!-- Finalize / Early Stop Modal -->
      <ff-workspace-finalize-modal
        [isOpen]="finalizeModalOpen()"
        [earlyStop]="isEarlyStop()"
        [activeSessionTasks]="sessionService.activeSessionTasks()"
        [stickyNotes]="studioStore.sortedNotes()"
        [elapsedMinutes]="sessionService.elapsedMinutes()"
        [focusScore]="studioStore.focusScore()"
        [isSubmitting]="sessionService.isSubmitting()"
        [errorMessage]="finalizeErrorMessage()"
        (closeModal)="closeFinalizeModal()"
        (submitFinalize)="onSubmitFinalize($event)"
      />
    </div>
  `,
})
export class WorkspaceComponent implements OnInit {
  readonly sessionService = inject(WorkspaceSessionService);
  readonly studioStore = inject(WorkspaceStudioStore);
  readonly audioService = inject(AmbientAudioService);

  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly titleService = inject(Title);

  private readonly originalTitle = this.titleService.getTitle();
  private lastChimeTick = this.sessionService.timerCompletedTick();
  private lastHydratedSessionId: string | null = null;

  // Setup & UI state
  readonly preferredTaskId = signal<string | null>(null);
  readonly selectedTaskIds = signal<string[]>([]);
  readonly activeTabMode = signal<TimerTabMode>('pomodoro');
  readonly plannedMinutes = signal<number>(this.studioStore.defaultPomodoroMinutes() || 25);
  readonly mobileLeftOpen = signal<boolean>(false);
  readonly togglingTaskId = signal<string | null>(null);
  readonly switchTaskWarning = signal<string | null>(null);
  readonly floatingEditingNoteId = signal<string | null>(null);

  readonly activeTask = this.sessionService.activeFocusTask;
  readonly milestoneContext = this.sessionService.milestoneContext;

  // Finalize modal state
  readonly finalizeModalOpen = signal<boolean>(false);
  readonly isEarlyStop = signal<boolean>(false);

  readonly isDarkScene = computed<boolean>(() => {
    return this.studioStore.isDarkSurface();
  });

  readonly showNotesRegion = computed<boolean>(
    () =>
      !this.studioStore.focusMode() &&
      (this.studioStore.notesPanelOpen() ||
        this.studioStore.undoNotice() !== null ||
        this.studioStore.isScratchpadOverLimit())
  );

  readonly canStartSession = computed<boolean>(
    () =>
      this.selectedTaskIds().length > 0 &&
      this.sessionService.pendingTakeawaySession() === null
  );

  readonly finalizeErrorMessage = computed<string | null>(() =>
    this.finalizeModalOpen() ? (this.sessionService.errorState()?.message ?? null) : null
  );

  constructor() {
    // 1. Tab Title Timer
    effect(() => {
      const show = this.studioStore.showInTabTitle();
      const running = this.sessionService.isRunning();
      const breakRunning = this.sessionService.isBreakRunning();
      const sessionTime = this.sessionService.formattedTime();
      const breakTime = this.sessionService.breakFormattedTime();

      if (show && breakRunning) {
        this.titleService.setTitle(`${breakTime} (Nghỉ) • FocusFlow`);
      } else if (show && running) {
        this.titleService.setTitle(`${sessionTime} • FocusFlow`);
      } else {
        this.titleService.setTitle(this.originalTitle);
      }
    });

    // 2. Completion Chime
    effect(() => {
      const tick = this.sessionService.timerCompletedTick();
      if (tick > this.lastChimeTick) {
        this.lastChimeTick = tick;
        if (this.audioService.chimeEnabled()) {
          this.audioService.playCompletionChime();
        }
      }
    });

    // 3. Scratchpad Sync Bridge (Server -> Local Sticky Notes)
    effect(() => {
      const active = this.sessionService.activeSession();
      if (!active) {
        this.lastHydratedSessionId = null;
        return;
      }

      const raw = active.scratchpad_content;
      if (
        raw &&
        raw.trim().length > 0 &&
        this.lastHydratedSessionId !== active.id
      ) {
        this.lastHydratedSessionId = active.id;
        const currentSerialized = untracked(() =>
          this.studioStore.serializeNotesForScratchpad()
        );
        if (currentSerialized !== raw) {
          untracked(() => this.studioStore.hydrateNotesFromScratchpad(raw));
        }
      }
    });

    // 4. Scratchpad Sync Bridge (Local Sticky Notes -> Session Heartbeat)
    effect(() => {
      this.studioStore.notes();
      const activeSessionId = this.sessionService.sessionId();
      if (!activeSessionId) {
        return;
      }

      const serialized = this.studioStore.serializeNotesForScratchpad();
      const currentScratchpad = untracked(() => this.sessionService.scratchpadNote());
      if (serialized !== currentScratchpad) {
        untracked(() => this.sessionService.setScratchpadNote(serialized));
      }
    });

    // 4b. Derive inline milestone context from TaskResponse, or fetch roadmap detail if absent
    effect(() => {
      const task = this.sessionService.activeFocusTask();
      const active = this.sessionService.activeSession();
      if (!task?.roadmap_id || !task?.milestone_id) {
        untracked(() => this.sessionService.milestoneContext.set(null));
        return;
      }
      if (untracked(() => this.sessionService.applyInlineMilestoneContext(task))) {
        return;
      }
      if (active?.status === 'IN_PROGRESS') {
        untracked(() =>
          this.sessionService.loadMilestoneContext(task.roadmap_id, task.milestone_id)
        );
      } else {
        untracked(() => this.sessionService.milestoneContext.set(null));
      }
    });

    // 5. Focus Shield & Global Keyboard Listeners
    const onVisibilityChange = (): void => {
      if (
        typeof document !== 'undefined' &&
        document.hidden &&
        this.sessionService.isRunning() &&
        this.studioStore.shieldConfig().tabGuardEnabled
      ) {
        this.studioStore.recordDistraction();
      }
    };

    const onBeforeUnload = (event: BeforeUnloadEvent): void => {
      if (
        this.sessionService.isRunning() &&
        this.studioStore.shieldConfig().zenLockEnabled
      ) {
        event.preventDefault();
      }
    };

    const onFullscreenChange = (): void => {
      if (typeof document !== 'undefined') {
        this.studioStore.setFullscreen(Boolean(document.fullscreenElement));
      }
    };

    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName?.toUpperCase() ?? '';
      const isEditable =
        tagName === 'INPUT' ||
        tagName === 'TEXTAREA' ||
        tagName === 'SELECT' ||
        Boolean(target?.isContentEditable);

      if (isEditable) {
        return;
      }

      if (event.key === 'Escape') {
        if (this.finalizeModalOpen()) {
          this.closeFinalizeModal();
        } else if (this.studioStore.activeToolPopover() !== null) {
          this.studioStore.closeToolPopover();
        } else if (this.mobileLeftOpen()) {
          this.mobileLeftOpen.set(false);
        } else if (this.studioStore.focusMode()) {
          this.studioStore.setFocusMode(false);
        }
        return;
      }

      if (
        (event.key === 'n' || event.key === 'N') &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.altKey
      ) {
        this.studioStore.toggleNotesPanel();
      }
    };

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVisibilityChange);
      document.addEventListener('fullscreenchange', onFullscreenChange);
      document.addEventListener('keydown', onKeyDown);
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', onBeforeUnload);
    }

    this.destroyRef.onDestroy(() => {
      this.titleService.setTitle(this.originalTitle);
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', onVisibilityChange);
        document.removeEventListener('fullscreenchange', onFullscreenChange);
        document.removeEventListener('keydown', onKeyDown);
      }
      if (typeof window !== 'undefined') {
        window.removeEventListener('beforeunload', onBeforeUnload);
      }
    });
  }

  ngOnInit(): void {
    this.studioStore.syncFromServer();
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const taskId = params.get('taskId');
      this.preferredTaskId.set(taskId);
      this.loadInitialWorkspace(taskId);
    });
  }

  refreshWorkspace(): void {
    this.loadInitialWorkspace(this.preferredTaskId());
  }

  selectMode(mode: SessionMode): void {
    if (mode === 'MVS') {
      this.activeTabMode.set('mvs');
      this.plannedMinutes.set(15);
    } else {
      this.activeTabMode.set('pomodoro');
      this.plannedMinutes.set(this.studioStore.defaultPomodoroMinutes() || 25);
    }
  }

  selectTabMode(tab: TimerTabMode): void {
    this.activeTabMode.set(tab);
    if (tab === 'mvs') {
      this.plannedMinutes.set(15);
    } else if (tab === 'pomodoro') {
      this.plannedMinutes.set(this.studioStore.defaultPomodoroMinutes() || 25);
    }
  }

  onPlannedMinutesChange(val: number | string): void {
    const parsed = Number(val);
    if (!Number.isNaN(parsed)) {
      this.plannedMinutes.set(Math.min(180, Math.max(5, Math.round(parsed))));
    }
  }

  toggleTaskSelection(taskId: string): void {
    this.selectedTaskIds.update((current) =>
      current.includes(taskId) ? current.filter((id) => id !== taskId) : [...current, taskId]
    );
  }

  startStudySession(): void {
    const ids = this.selectedTaskIds();
    if (ids.length === 0) return;

    const tab = this.activeTabMode();
    const sessionMode: SessionMode = tab === 'mvs' ? 'MVS' : 'STANDARD';
    this.sessionService.mode.set(tab === 'stopwatch' ? 'stopwatch' : 'pomodoro');
    this.studioStore.resetSessionDistractions();

    const serializedNotes = this.studioStore.serializeNotesForScratchpad();

    this.sessionService
      .beginSession({
        task_ids: ids,
        session_mode: sessionMode,
        planned_minutes: this.plannedMinutes(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          if (serializedNotes.length > 0) {
            this.sessionService.setScratchpadNote(serializedNotes);
          }
        },
        error: () => {
          if (
            this.sessionService.errorState()?.code === 'PENDING_TAKEAWAY_REQUIRED' ||
            this.sessionService.errorState()?.code === 'ACTIVE_SESSION_EXISTS'
          ) {
            this.refreshWorkspace();
          }
        },
      });
  }

  openFinalizeModal(earlyStop: boolean): void {
    this.sessionService.clearError();
    this.isEarlyStop.set(earlyStop);
    this.finalizeModalOpen.set(true);
  }

  closeFinalizeModal(): void {
    this.finalizeModalOpen.set(false);
    this.sessionService.clearError();
  }

  onSubmitFinalize(request: FinalizeSessionRequest): void {
    this.sessionService
      .finalizeSession({
        ...request,
        scratchpad_content: this.sessionService.scratchpadNote(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.finalizeModalOpen.set(false);
          this.switchTaskWarning.set(null);
          this.refreshWorkspace();
        },
      });
  }

  onAttemptSwitchOutsideTask(_task: TaskResponse): void {
    this.switchTaskWarning.set(
      'Cần hoàn tất hoặc dừng sớm phiên hiện tại trước khi chuyển sang nhiệm vụ khác'
    );
  }

  dismissSwitchTaskWarning(): void {
    this.switchTaskWarning.set(null);
  }

  onEndSessionFromWarning(): void {
    this.switchTaskWarning.set(null);
    this.openFinalizeModal(true);
  }

  onPinNewNote(payload: { title: string; content: string; color: StickyNoteColor }): void {
    this.studioStore.pinNewNoteFromComposer(
      payload.content,
      payload.color,
      this.sessionService.sessionId(),
      this.sessionService.activeFocusTaskId(),
      payload.title
    );
  }

  onToggleTaskComplete(task: TaskResponse): void {
    this.togglingTaskId.set(task.id);
    this.sessionService
      .toggleTaskCompletion(task)
      .pipe(
        finalize(() => this.togglingTaskId.set(null)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe();
  }

  onResolveDebt(payload: { sessionId: string; takeaway: string; selfConfidence: number }): void {
    this.sessionService
      .resolvePendingTakeaway(payload.sessionId, {
        takeaway: payload.takeaway,
        self_confidence: payload.selfConfidence,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.refreshWorkspace();
        },
      });
  }

  onStartBreak(payload: { type: BreakType; minutes: number }): void {
    this.sessionService.startBreak(payload.type, payload.minutes);
  }

  openLeftPanel(): void {
    this.studioStore.setLeftPanelCollapsed(false);
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      this.mobileLeftOpen.set(true);
    }
  }

  onLeftPanelCollapse(): void {
    if (this.mobileLeftOpen()) {
      this.mobileLeftOpen.set(false);
    } else {
      this.studioStore.setLeftPanelCollapsed(true);
    }
  }

  toggleFullscreen(): void {
    if (typeof document === 'undefined') return;
    if (document.fullscreenElement) {
      void document.exitFullscreen?.();
    } else {
      void document.documentElement.requestFullscreen?.();
    }
  }

  protected studioBarBtnClass(active: boolean): string {
    if (this.isDarkScene()) {
      return active
        ? 'border-white/50 bg-white/25 text-white'
        : 'border-white/25 bg-white/10 text-white/95 hover:bg-white/20';
    }
    return active
      ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]'
      : 'border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] text-[var(--on-surface)] hover:bg-[var(--surface-container-low)]';
  }

  private loadInitialWorkspace(taskId: string | null): void {
    this.sessionService
      .loadWorkspace(taskId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((focus) => {
        const active = this.sessionService.activeSession();
        if (active) {
          this.activeTabMode.set(active.session_mode === 'MVS' ? 'mvs' : 'pomodoro');
          this.sessionService.mode.set('pomodoro');
        }

        const available = this.sessionService.availableTasks();
        if (taskId && available.some((t) => t.id === taskId)) {
          this.selectedTaskIds.set([taskId]);
          const matched = available.find((t) => t.id === taskId);
          if (matched && this.activeTabMode() === 'pomodoro') {
            this.plannedMinutes.set(Math.min(180, Math.max(15, matched.estimated_minutes || 25)));
          }
        } else if (focus?.focus_task) {
          this.selectedTaskIds.set([focus.focus_task.id]);
          if (this.activeTabMode() === 'pomodoro') {
            this.plannedMinutes.set(
              Math.min(180, Math.max(15, focus.focus_task.estimated_minutes || 25))
            );
          }
        } else if (available.length > 0 && this.selectedTaskIds().length === 0) {
          this.selectedTaskIds.set([available[0].id]);
        }
      });
  }
}
