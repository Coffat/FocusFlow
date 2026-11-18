import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subject, catchError, debounceTime, forkJoin, of, switchMap } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { ThemeSignalService } from '../../../core/services/theme-signal.service';
import {
  ClockSize,
  ClockStyleId,
  CreateStickyNoteRequest,
  FocusShieldConfig,
  ParkingThoughtItem,
  SceneMeta,
  StickyNoteColor,
  StickyNoteItem,
  StickyNoteResponse,
  UpdateStickyNoteRequest,
  UpdateWorkspaceStudioConfigRequest,
  WorkspaceSceneId,
  WorkspaceStudioConfigResponse,
  WorkspaceToolPopover,
} from '../models/workspace.model';

const STUDIO_STORAGE_KEY = 'focusflow_workspace_studio_v1';
const USER_PREFERENCES_STORAGE_KEY = 'focusflow_user_preferences';
const MAX_SCRATCHPAD_LENGTH = 9800;
const UNDO_NOTICE_DURATION_MS = 5000;
const LEGACY_NOTE_TITLE = 'Ghi chú phiên học';

export const WORKSPACE_SCENES: readonly SceneMeta[] = [
  {
    id: 'architectural',
    label: 'Architectural Paper',
    description: 'Giấy sáng tối giản, sắc nét',
    isDark: false,
    fallbackGradient: 'linear-gradient(135deg, #fbf9f8 0%, #efeded 100%)',
    scrimRgba: 'rgba(255, 255, 255, 0.35)',
  },
  {
    id: 'lofi-night',
    label: 'Lofi Night',
    description: 'Đêm tĩnh lặng, ánh đèn ấm',
    isDark: true,
    imageUrl: '/assets/scenes/lofi-night.webp',
    fallbackGradient:
      'linear-gradient(135deg, #131826 0%, #1d2336 55%, #111521 100%)',
    scrimRgba: 'rgba(12, 16, 28, 0.45)',
  },
  {
    id: 'rain',
    label: 'Mưa bên cửa sổ',
    description: 'Xám xanh dịu mắt, tĩnh lặng',
    isDark: true,
    imageUrl: '/assets/scenes/rain-window.webp',
    fallbackGradient: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
    scrimRgba: 'rgba(15, 23, 42, 0.48)',
  },
  {
    id: 'cafe',
    label: 'Quán Cafe chiều',
    description: 'Ấm áp, tông gỗ hổ phách',
    isDark: true,
    imageUrl: '/assets/scenes/cozy-cafe.webp',
    fallbackGradient: 'linear-gradient(135deg, #2b1e16 0%, #432f21 100%)',
    scrimRgba: 'rgba(24, 16, 11, 0.5)',
  },
  {
    id: 'library',
    label: 'Thư viện cổ điển',
    description: 'Trầm lắng, tập trung sâu',
    isDark: true,
    imageUrl: '/assets/scenes/quiet-library.webp',
    fallbackGradient: 'linear-gradient(135deg, #1b2821 0%, #0e1914 100%)',
    scrimRgba: 'rgba(10, 20, 15, 0.48)',
  },
];

const VALID_SCENES: readonly WorkspaceSceneId[] = [
  'architectural',
  'lofi-night',
  'rain',
  'cafe',
  'library',
];
const VALID_CLOCK_STYLES: readonly ClockStyleId[] = [
  'editorial',
  'ring',
  'flip',
  'minimal',
];
const VALID_CLOCK_SIZES: readonly ClockSize[] = ['md', 'lg'];
const VALID_NOTE_COLORS: readonly StickyNoteColor[] = [
  'cream',
  'pink',
  'sage',
  'blue',
  'amber',
  'lavender',
];

const DEFAULT_BLOCKLIST: readonly string[] = [
  'facebook.com',
  'youtube.com',
  'tiktok.com',
];

interface StudioPersistedState {
  scene: WorkspaceSceneId;
  clockStyle: ClockStyleId;
  clockSize: ClockSize;
  showSeconds: boolean;
  showInTabTitle: boolean;
  leftPanelCollapsed: boolean;
  notesPanelOpen: boolean;
  notes: StickyNoteItem[];
  shieldConfig: FocusShieldConfig;
}

interface UserDurationPreferences {
  defaultPomodoroDuration: number;
  shortBreakDuration: number;
  longBreakDuration: number;
  soundEnabled: boolean;
}

const DEFAULT_USER_PREFERENCES: UserDurationPreferences = {
  defaultPomodoroDuration: 25,
  shortBreakDuration: 5,
  longBreakDuration: 15,
  soundEnabled: true,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isOneOf<T extends string>(value: unknown, allowed: readonly T[]): value is T {
  return typeof value === 'string' && (allowed as readonly string[]).includes(value);
}

function migrateSceneId(
  raw: unknown,
  fallback: WorkspaceSceneId
): WorkspaceSceneId {
  if (raw === 'forest') {
    return 'library';
  }
  if (raw === 'dawn') {
    return 'lofi-night';
  }
  return isOneOf(raw, VALID_SCENES) ? raw : fallback;
}

function generateId(prefix: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}_${crypto.randomUUID()}`;
  }
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function safeReadStorage(key: string): string | null {
  try {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeWriteStorage(key: string, value: string): void {
  try {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.setItem(key, value);
  } catch {
    // Ignore storage errors in SSR / private browsing / quota exceeded
  }
}

function sanitizeNote(raw: unknown): StickyNoteItem | null {
  if (!isRecord(raw)) {
    return null;
  }
  if (typeof raw['id'] !== 'string' || !raw['id'].trim()) {
    return null;
  }
  const title = typeof raw['title'] === 'string' ? raw['title'] : '';
  const content = typeof raw['content'] === 'string' ? raw['content'] : '';
  const color = isOneOf(raw['color'], VALID_NOTE_COLORS) ? raw['color'] : 'cream';
  const pinned = typeof raw['pinned'] === 'boolean' ? raw['pinned'] : false;
  const updatedAt =
    typeof raw['updatedAt'] === 'number' && Number.isFinite(raw['updatedAt'])
      ? raw['updatedAt']
      : Date.now();
  const createdAt =
    typeof raw['createdAt'] === 'number' && Number.isFinite(raw['createdAt'])
      ? raw['createdAt']
      : updatedAt;
  const sessionId =
    typeof raw['sessionId'] === 'string' ? raw['sessionId'] : null;
  const taskId = typeof raw['taskId'] === 'string' ? raw['taskId'] : null;
  const posX =
    typeof raw['posX'] === 'number' && Number.isFinite(raw['posX'])
      ? raw['posX']
      : undefined;
  const posY =
    typeof raw['posY'] === 'number' && Number.isFinite(raw['posY'])
      ? raw['posY']
      : undefined;
  const zIndex =
    typeof raw['zIndex'] === 'number' && Number.isFinite(raw['zIndex'])
      ? raw['zIndex']
      : undefined;
  const serverSynced = raw['serverSynced'] === true ? true : undefined;

  return {
    id: raw['id'],
    title,
    content,
    color,
    pinned,
    sessionId,
    taskId,
    createdAt,
    updatedAt,
    ...(posX !== undefined ? { posX } : {}),
    ...(posY !== undefined ? { posY } : {}),
    ...(zIndex !== undefined ? { zIndex } : {}),
    ...(serverSynced !== undefined ? { serverSynced } : {}),
  };
}

function sanitizeThought(raw: unknown): ParkingThoughtItem | null {
  if (!isRecord(raw)) {
    return null;
  }
  if (typeof raw['id'] !== 'string' || typeof raw['text'] !== 'string') {
    return null;
  }
  const createdAt =
    typeof raw['createdAt'] === 'number' && Number.isFinite(raw['createdAt'])
      ? raw['createdAt']
      : Date.now();
  const done = typeof raw['done'] === 'boolean' ? raw['done'] : false;
  return {
    id: raw['id'],
    text: raw['text'],
    createdAt,
    done,
  };
}

function sanitizeShieldConfig(raw: unknown): FocusShieldConfig {
  const defaults: FocusShieldConfig = {
    tabGuardEnabled: true,
    zenLockEnabled: false,
    blocklist: [...DEFAULT_BLOCKLIST],
    parkingLot: [],
  };

  if (!isRecord(raw)) {
    return defaults;
  }

  const blocklist = Array.isArray(raw['blocklist'])
    ? Array.from(
        new Set(
          raw['blocklist']
            .filter((item): item is string => typeof item === 'string')
            .map((item) => item.trim().toLowerCase())
            .filter((item) => item.length > 0)
        )
      )
    : defaults.blocklist;

  const parkingLot = Array.isArray(raw['parkingLot'])
    ? raw['parkingLot']
        .map((item) => sanitizeThought(item))
        .filter((item): item is ParkingThoughtItem => item !== null)
    : [];

  return {
    tabGuardEnabled:
      typeof raw['tabGuardEnabled'] === 'boolean'
        ? raw['tabGuardEnabled']
        : defaults.tabGuardEnabled,
    zenLockEnabled:
      typeof raw['zenLockEnabled'] === 'boolean'
        ? raw['zenLockEnabled']
        : defaults.zenLockEnabled,
    blocklist,
    parkingLot,
  };
}

type UndoActionMeta =
  | { type: 'create'; noteId: string; synced: boolean }
  | { type: 'delete'; deletedNote: StickyNoteItem };

@Injectable({ providedIn: 'root' })
export class WorkspaceStudioStore {
  private readonly http = inject(HttpClient, { optional: true });
  private readonly themeSignal = inject(ThemeSignalService);
  private readonly destroyRef = inject(DestroyRef);

  private undoTimerId: ReturnType<typeof setTimeout> | null = null;
  private undoMeta: UndoActionMeta | null = null;

  private readonly studioConfigSync$ = new Subject<void>();
  private readonly notePatchSubjects = new Map<string, Subject<void>>();
  private readonly creatingNoteIds = new Set<string>();
  private readonly deletedWhileCreating = new Set<string>();
  private readonly pendingPatchAfterCreate = new Set<string>();

  private readonly initialStudio = this.loadStudioState();
  private readonly initialUserPrefs = this.loadUserPreferences();

  private readonly _scene = signal<WorkspaceSceneId>(this.initialStudio.scene);
  private readonly _clockStyle = signal<ClockStyleId>(this.initialStudio.clockStyle);
  private readonly _clockSize = signal<ClockSize>(this.initialStudio.clockSize);
  private readonly _showSeconds = signal<boolean>(this.initialStudio.showSeconds);
  private readonly _showInTabTitle = signal<boolean>(this.initialStudio.showInTabTitle);
  private readonly _leftPanelCollapsed = signal<boolean>(
    this.initialStudio.leftPanelCollapsed
  );
  private readonly _notesPanelOpen = signal<boolean>(this.initialStudio.notesPanelOpen);
  private readonly _activeToolPopover = signal<WorkspaceToolPopover>(null);
  private readonly _notes = signal<StickyNoteItem[]>(this.initialStudio.notes);
  private readonly _shieldConfig = signal<FocusShieldConfig>(
    this.initialStudio.shieldConfig
  );
  private readonly _distractionCount = signal<number>(0);
  private readonly _showReturnBanner = signal<boolean>(false);
  private readonly _isFullscreen = signal<boolean>(false);
  readonly focusMode = signal<boolean>(false);
  readonly undoNotice = signal<{ message: string; snapshot: StickyNoteItem[] } | null>(
    null
  );

  constructor() {
    if (this.http) {
      this.studioConfigSync$
        .pipe(
          debounceTime(600),
          switchMap(() =>
            this.http!.put<WorkspaceStudioConfigResponse>(
              API_ENDPOINTS.SESSIONS.STUDIO_CONFIG,
              this.buildStudioConfigRequest(),
              { withCredentials: true }
            ).pipe(catchError(() => of(null)))
          ),
          takeUntilDestroyed(this.destroyRef)
        )
        .subscribe();
    }

    this.destroyRef.onDestroy(() => {
      this.clearUndoTimer();
      this.studioConfigSync$.complete();
      for (const subject of this.notePatchSubjects.values()) {
        subject.complete();
      }
      this.notePatchSubjects.clear();
      this.creatingNoteIds.clear();
      this.deletedWhileCreating.clear();
      this.pendingPatchAfterCreate.clear();
    });
  }

  private readonly _defaultPomodoroMinutes = signal<number>(
    this.initialUserPrefs.defaultPomodoroDuration
  );
  private readonly _shortBreakMinutes = signal<number>(
    this.initialUserPrefs.shortBreakDuration
  );
  private readonly _longBreakMinutes = signal<number>(
    this.initialUserPrefs.longBreakDuration
  );
  private readonly _soundEnabledPreference = signal<boolean>(
    this.initialUserPrefs.soundEnabled
  );

  readonly scene = this._scene.asReadonly();
  readonly clockStyle = this._clockStyle.asReadonly();
  readonly clockSize = this._clockSize.asReadonly();
  readonly showSeconds = this._showSeconds.asReadonly();
  readonly showInTabTitle = this._showInTabTitle.asReadonly();
  readonly leftPanelCollapsed = this._leftPanelCollapsed.asReadonly();
  readonly notesPanelOpen = this._notesPanelOpen.asReadonly();
  readonly activeToolPopover = this._activeToolPopover.asReadonly();
  readonly notes = this._notes.asReadonly();
  readonly shieldConfig = this._shieldConfig.asReadonly();
  readonly distractionCount = this._distractionCount.asReadonly();
  readonly showReturnBanner = this._showReturnBanner.asReadonly();
  readonly isFullscreen = this._isFullscreen.asReadonly();

  readonly defaultPomodoroMinutes = this._defaultPomodoroMinutes.asReadonly();
  readonly shortBreakMinutes = this._shortBreakMinutes.asReadonly();
  readonly longBreakMinutes = this._longBreakMinutes.asReadonly();
  readonly soundEnabledPreference = this._soundEnabledPreference.asReadonly();

  readonly sortedNotes = computed<StickyNoteItem[]>(() => {
    return [...this._notes()].sort((a, b) => {
      if (a.pinned !== b.pinned) {
        return a.pinned ? -1 : 1;
      }
      return b.updatedAt - a.updatedAt;
    });
  });

  readonly visiblePinnedNotes = computed<StickyNoteItem[]>(() =>
    this.sortedNotes()
      .filter((n) => n.pinned)
      .slice(0, 4)
  );

  readonly collectionNotes = computed<StickyNoteItem[]>(() => this.sortedNotes());

  readonly activeSceneMeta = computed<SceneMeta>(
    () =>
      WORKSPACE_SCENES.find((s) => s.id === this._scene()) ??
      WORKSPACE_SCENES[1]
  );

  readonly isDarkSurface = computed<boolean>(
    () => this.activeSceneMeta().isDark || this.themeSignal.isDark()
  );

  readonly serializedNotesLength = computed<number>(() => {
    this._notes();
    return this.serializeNotesForScratchpad().length;
  });

  readonly isScratchpadOverLimit = computed<boolean>(
    () => this.serializedNotesLength() >= MAX_SCRATCHPAD_LENGTH
  );

  readonly focusScore = computed<number>(() => {
    return Math.max(0, 100 - this._distractionCount() * 8);
  });

  syncFromServer(): void {
    if (!this.http) {
      return;
    }

    const notes$ = this.http
      .get<StickyNoteResponse[]>(API_ENDPOINTS.SESSIONS.NOTES, {
        withCredentials: true,
      })
      .pipe(catchError(() => of(null)));

    const config$ = this.http
      .get<WorkspaceStudioConfigResponse>(API_ENDPOINTS.SESSIONS.STUDIO_CONFIG, {
        withCredentials: true,
      })
      .pipe(catchError(() => of(null)));

    forkJoin({ notes: notes$, config: config$ })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(({ notes, config }) => {
        if (notes !== null) {
          this.mergeServerNotes(notes);
        }
        if (config !== null) {
          this.applyServerStudioConfig(config);
        }
      });
  }

  setScene(scene: WorkspaceSceneId): void {
    this._scene.set(scene);
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  setClockStyle(style: ClockStyleId): void {
    this._clockStyle.set(style);
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  setClockSize(size: ClockSize): void {
    this._clockSize.set(size);
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  toggleShowSeconds(): void {
    this._showSeconds.update((v) => !v);
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  toggleShowInTabTitle(): void {
    this._showInTabTitle.update((v) => !v);
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  toggleLeftPanel(): void {
    this._leftPanelCollapsed.update((v) => !v);
    this.persistStudioState();
  }

  setLeftPanelCollapsed(val: boolean): void {
    this._leftPanelCollapsed.set(val);
    this.persistStudioState();
  }

  toggleNotesPanel(): void {
    this._notesPanelOpen.update((v) => !v);
    this.persistStudioState();
  }

  setNotesPanelOpen(val: boolean): void {
    this._notesPanelOpen.set(val);
    this.persistStudioState();
  }

  toggleToolPopover(popover: WorkspaceToolPopover): void {
    this._activeToolPopover.update((current) => (current === popover ? null : popover));
  }

  closeToolPopover(): void {
    this._activeToolPopover.set(null);
  }

  toggleFocusMode(): void {
    this.focusMode.update((v) => !v);
  }

  setFocusMode(val: boolean): void {
    this.focusMode.set(val);
  }

  addNote(
    color: StickyNoteColor = 'cream',
    title = '',
    content = ''
  ): StickyNoteItem {
    const now = Date.now();
    const note: StickyNoteItem = {
      id: generateId('note'),
      title,
      content,
      color,
      pinned: false,
      sessionId: null,
      taskId: null,
      createdAt: now,
      updatedAt: now,
    };
    this._notes.update((items) => [note, ...items]);
    this.persistStudioState();
    return note;
  }

  pinNewNoteFromComposer(
    content: string,
    color: StickyNoteColor,
    sessionId: string | null,
    taskId: string | null,
    title?: string
  ): StickyNoteItem | null {
    const trimmed = content.trim();
    if (!trimmed) {
      return null;
    }
    const snapshot = this._notes();
    const now = Date.now();
    const maxZ = snapshot.reduce((max, item) => Math.max(max, item.zIndex ?? 0), 0);
    const note: StickyNoteItem = {
      id: generateId('note'),
      title: (title ?? '').trim(),
      content: trimmed,
      color,
      pinned: true,
      sessionId,
      taskId,
      createdAt: now,
      updatedAt: now,
      zIndex: maxZ + 1,
      serverSynced: false,
    };
    this._notes.update((items) => [note, ...items]);
    this.persistStudioState();
    this.setUndoNotice('Đã ghim ghi chú mới.', snapshot, {
      type: 'create',
      noteId: note.id,
      synced: false,
    });
    this.createNoteOnServer(note);
    return note;
  }

  updateNotePosition(id: string, posX: number, posY: number): void {
    if (!Number.isFinite(posX) || !Number.isFinite(posY)) {
      return;
    }
    let changed = false;
    this._notes.update((items) =>
      items.map((item) => {
        if (item.id !== id) {
          return item;
        }
        changed = true;
        return {
          ...item,
          posX,
          posY,
        };
      })
    );
    if (changed) {
      this.persistStudioState();
      this.scheduleNotePatch(id);
    }
  }

  bringNoteToFront(id: string): void {
    const items = this._notes();
    const target = items.find((item) => item.id === id);
    if (!target) {
      return;
    }
    const maxZ = items.reduce((max, item) => Math.max(max, item.zIndex ?? 0), 0);
    const nextZ = maxZ + 1;
    this._notes.update((prev) =>
      prev.map((item) => (item.id === id ? { ...item, zIndex: nextZ } : item))
    );
    this.persistStudioState();
    this.scheduleNotePatch(id);
  }

  unpinNote(id: string): void {
    let changed = false;
    this._notes.update((items) =>
      items.map((item) => {
        if (item.id !== id || !item.pinned) {
          return item;
        }
        changed = true;
        return {
          ...item,
          pinned: false,
          updatedAt: Date.now(),
        };
      })
    );
    if (changed) {
      this.persistStudioState();
      this.scheduleNotePatch(id);
    }
  }

  updateNote(
    id: string,
    patch: Partial<Pick<StickyNoteItem, 'title' | 'content' | 'color' | 'pinned'>>
  ): void {
    let changed = false;
    this._notes.update((items) =>
      items.map((item) => {
        if (item.id !== id) {
          return item;
        }
        changed = true;
        return {
          ...item,
          ...patch,
          updatedAt: Date.now(),
        };
      })
    );
    if (changed) {
      this.persistStudioState();
      this.scheduleNotePatch(id);
    }
  }

  togglePin(id: string): void {
    let changed = false;
    this._notes.update((items) =>
      items.map((item) => {
        if (item.id !== id) {
          return item;
        }
        changed = true;
        return {
          ...item,
          pinned: !item.pinned,
          updatedAt: Date.now(),
        };
      })
    );
    if (changed) {
      this.persistStudioState();
      this.scheduleNotePatch(id);
    }
  }

  deleteNote(id: string): void {
    const snapshot = this._notes();
    const target = snapshot.find((item) => item.id === id);
    const next = snapshot.filter((item) => item.id !== id);
    if (next.length !== snapshot.length) {
      this._notes.set(next);
      this.persistStudioState();
      this.setUndoNotice(
        'Đã xóa ghi chú.',
        snapshot,
        target ? { type: 'delete', deletedNote: target } : null
      );
      this.cancelNotePatch(id);
      if (target) {
        this.deleteNoteOnServer(target);
      }
    }
  }

  undoLastNoteAction(): void {
    const notice = this.undoNotice();
    if (!notice) {
      return;
    }
    const meta = this.undoMeta;
    this.clearUndoTimer();
    this._notes.set(notice.snapshot);
    this.undoNotice.set(null);
    this.undoMeta = null;
    this.persistStudioState();

    if (meta?.type === 'delete' && meta.deletedNote.serverSynced) {
      this.createNoteOnServer(meta.deletedNote);
    } else if (meta?.type === 'create') {
      this.cancelNotePatch(meta.noteId);
      if (this.creatingNoteIds.has(meta.noteId)) {
        this.deletedWhileCreating.add(meta.noteId);
      } else if (meta.synced) {
        this.deleteNoteByIdOnServer(meta.noteId);
      }
    }
  }

  serializeNotesForScratchpad(): string {
    const ordered = this.sortedNotes();
    if (ordered.length === 0) {
      return '';
    }

    const blocks = ordered.map((note) => {
      const safeTitle = note.title.replace(/[\r\n]+/g, ' ').replace(/-->/g, '—');
      const pinFlag = note.pinned ? '1' : '0';
      return `<!--ff-note:${note.color}:${pinFlag}:${safeTitle}-->\n${note.content}`;
    });

    const joined = blocks.join('\n\n---\n\n');
    if (joined.length <= MAX_SCRATCHPAD_LENGTH) {
      return joined;
    }
    return joined.slice(0, MAX_SCRATCHPAD_LENGTH);
  }

  hydrateNotesFromScratchpad(raw: string): void {
    if (!raw || !raw.trim()) {
      return;
    }

    if (raw.includes('<!--ff-note:')) {
      const blocks = raw.split(/\n\n---\n\n/);
      const parsed: StickyNoteItem[] = [];
      const baseTime = Date.now();

      blocks.forEach((block, index) => {
        const match = /^<!--ff-note:([^:]+):([01]):(.*?)-->\r?\n?([\s\S]*)$/.exec(
          block.trimStart()
        );
        if (!match) {
          return;
        }
        const [, rawColor, pinFlag, title, content] = match;
        const color: StickyNoteColor = isOneOf(rawColor, VALID_NOTE_COLORS)
          ? rawColor
          : 'cream';
        parsed.push({
          id: generateId('note'),
          title: title.trim(),
          content,
          color,
          pinned: pinFlag === '1',
          sessionId: null,
          taskId: null,
          createdAt: baseTime - index,
          updatedAt: baseTime - index,
        });
      });

      if (parsed.length > 0) {
        this._notes.set(parsed);
        this.persistStudioState();
      }
      return;
    }

    const normalizedRaw = raw.trim();
    const alreadyExists = this._notes().some(
      (note) =>
        note.title === LEGACY_NOTE_TITLE && note.content.trim() === normalizedRaw
    );
    if (alreadyExists) {
      return;
    }

    const now = Date.now();
    const legacyNote: StickyNoteItem = {
      id: generateId('note'),
      title: LEGACY_NOTE_TITLE,
      content: raw,
      color: 'cream',
      pinned: true,
      sessionId: null,
      taskId: null,
      createdAt: now,
      updatedAt: now,
    };
    this._notes.update((items) => [legacyNote, ...items]);
    this.persistStudioState();
  }

  setTabGuardEnabled(enabled: boolean): void {
    this._shieldConfig.update((cfg) => ({ ...cfg, tabGuardEnabled: enabled }));
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  setZenLockEnabled(enabled: boolean): void {
    this._shieldConfig.update((cfg) => ({ ...cfg, zenLockEnabled: enabled }));
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  setFullscreen(val: boolean): void {
    this._isFullscreen.set(val);
  }

  recordDistraction(): void {
    this._distractionCount.update((c) => c + 1);
    this._showReturnBanner.set(true);
  }

  dismissReturnBanner(): void {
    this._showReturnBanner.set(false);
  }

  resetSessionDistractions(): void {
    this._distractionCount.set(0);
    this._showReturnBanner.set(false);
  }

  addBlockedSite(site: string): void {
    const normalized = site.trim().toLowerCase();
    if (!normalized) {
      return;
    }
    const current = this._shieldConfig().blocklist;
    if (current.includes(normalized)) {
      return;
    }
    this._shieldConfig.update((cfg) => ({
      ...cfg,
      blocklist: [...cfg.blocklist, normalized],
    }));
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  removeBlockedSite(site: string): void {
    const normalized = site.trim().toLowerCase();
    const current = this._shieldConfig().blocklist;
    const filtered = current.filter((item) => item !== normalized);
    if (filtered.length === current.length) {
      return;
    }
    this._shieldConfig.update((cfg) => ({
      ...cfg,
      blocklist: filtered,
    }));
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  addThought(text: string): void {
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }
    const item: ParkingThoughtItem = {
      id: generateId('thought'),
      text: trimmed,
      createdAt: Date.now(),
      done: false,
    };
    this._shieldConfig.update((cfg) => ({
      ...cfg,
      parkingLot: [item, ...cfg.parkingLot],
    }));
    this.persistStudioState();
    this.scheduleStudioConfigSync();
  }

  toggleThought(id: string): void {
    let changed = false;
    this._shieldConfig.update((cfg) => ({
      ...cfg,
      parkingLot: cfg.parkingLot.map((item) => {
        if (item.id !== id) {
          return item;
        }
        changed = true;
        return { ...item, done: !item.done };
      }),
    }));
    if (changed) {
      this.persistStudioState();
      this.scheduleStudioConfigSync();
    }
  }

  removeThought(id: string): void {
    const before = this._shieldConfig().parkingLot.length;
    this._shieldConfig.update((cfg) => ({
      ...cfg,
      parkingLot: cfg.parkingLot.filter((item) => item.id !== id),
    }));
    if (this._shieldConfig().parkingLot.length !== before) {
      this.persistStudioState();
      this.scheduleStudioConfigSync();
    }
  }

  clearCompletedThoughts(): void {
    const before = this._shieldConfig().parkingLot.length;
    this._shieldConfig.update((cfg) => ({
      ...cfg,
      parkingLot: cfg.parkingLot.filter((item) => !item.done),
    }));
    if (this._shieldConfig().parkingLot.length !== before) {
      this.persistStudioState();
      this.scheduleStudioConfigSync();
    }
  }

  private loadStudioState(): StudioPersistedState {
    const defaults: StudioPersistedState = {
      scene: 'lofi-night',
      clockStyle: 'ring',
      clockSize: 'lg',
      showSeconds: true,
      showInTabTitle: true,
      leftPanelCollapsed: false,
      notesPanelOpen: false,
      notes: [],
      shieldConfig: {
        tabGuardEnabled: true,
        zenLockEnabled: false,
        blocklist: [...DEFAULT_BLOCKLIST],
        parkingLot: [],
      },
    };

    const raw = safeReadStorage(STUDIO_STORAGE_KEY);
    if (!raw) {
      return defaults;
    }

    try {
      const parsed: unknown = JSON.parse(raw);
      if (!isRecord(parsed)) {
        return defaults;
      }

      const notes = Array.isArray(parsed['notes'])
        ? parsed['notes']
            .map((item) => sanitizeNote(item))
            .filter((item): item is StickyNoteItem => item !== null)
        : [];

      return {
        scene: migrateSceneId(parsed['scene'], defaults.scene),
        clockStyle: isOneOf(parsed['clockStyle'], VALID_CLOCK_STYLES)
          ? parsed['clockStyle']
          : defaults.clockStyle,
        clockSize: isOneOf(parsed['clockSize'], VALID_CLOCK_SIZES)
          ? parsed['clockSize']
          : defaults.clockSize,
        showSeconds:
          typeof parsed['showSeconds'] === 'boolean'
            ? parsed['showSeconds']
            : defaults.showSeconds,
        showInTabTitle:
          typeof parsed['showInTabTitle'] === 'boolean'
            ? parsed['showInTabTitle']
            : defaults.showInTabTitle,
        leftPanelCollapsed:
          typeof parsed['leftPanelCollapsed'] === 'boolean'
            ? parsed['leftPanelCollapsed']
            : defaults.leftPanelCollapsed,
        notesPanelOpen:
          typeof parsed['notesPanelOpen'] === 'boolean'
            ? parsed['notesPanelOpen']
            : defaults.notesPanelOpen,
        notes,
        shieldConfig: sanitizeShieldConfig(parsed['shieldConfig']),
      };
    } catch {
      return defaults;
    }
  }

  private loadUserPreferences(): UserDurationPreferences {
    const raw = safeReadStorage(USER_PREFERENCES_STORAGE_KEY);
    if (!raw) {
      return { ...DEFAULT_USER_PREFERENCES };
    }

    try {
      const parsed: unknown = JSON.parse(raw);
      if (!isRecord(parsed)) {
        return { ...DEFAULT_USER_PREFERENCES };
      }

      const readPositiveInt = (val: unknown, fallback: number): number =>
        typeof val === 'number' && Number.isFinite(val) && val > 0 ? val : fallback;

      return {
        defaultPomodoroDuration: readPositiveInt(
          parsed['defaultPomodoroDuration'],
          DEFAULT_USER_PREFERENCES.defaultPomodoroDuration
        ),
        shortBreakDuration: readPositiveInt(
          parsed['shortBreakDuration'],
          DEFAULT_USER_PREFERENCES.shortBreakDuration
        ),
        longBreakDuration: readPositiveInt(
          parsed['longBreakDuration'],
          DEFAULT_USER_PREFERENCES.longBreakDuration
        ),
        soundEnabled:
          typeof parsed['soundEnabled'] === 'boolean'
            ? parsed['soundEnabled']
            : DEFAULT_USER_PREFERENCES.soundEnabled,
      };
    } catch {
      return { ...DEFAULT_USER_PREFERENCES };
    }
  }

  private setUndoNotice(
    message: string,
    snapshot: StickyNoteItem[],
    meta: UndoActionMeta | null = null
  ): void {
    this.clearUndoTimer();
    this.undoMeta = meta;
    this.undoNotice.set({ message, snapshot });
    this.undoTimerId = setTimeout(() => {
      this.undoNotice.set(null);
      this.undoMeta = null;
      this.undoTimerId = null;
    }, UNDO_NOTICE_DURATION_MS);
  }

  private clearUndoTimer(): void {
    if (this.undoTimerId !== null) {
      clearTimeout(this.undoTimerId);
      this.undoTimerId = null;
    }
    this.undoMeta = null;
  }

  private scheduleStudioConfigSync(): void {
    if (!this.http) {
      return;
    }
    this.studioConfigSync$.next();
  }

  private buildStudioConfigRequest(): UpdateWorkspaceStudioConfigRequest {
    const shield = this._shieldConfig();
    return {
      scene: this._scene(),
      clock_style: this._clockStyle(),
      clock_size: this._clockSize(),
      show_seconds: this._showSeconds(),
      show_in_tab_title: this._showInTabTitle(),
      tab_guard_enabled: shield.tabGuardEnabled,
      zen_lock_enabled: shield.zenLockEnabled,
      blocklist: [...shield.blocklist],
      parking_lot: shield.parkingLot.map((t) => ({
        id: t.id,
        text: t.text,
        created_at: new Date(t.createdAt).toISOString(),
        done: t.done,
      })),
    };
  }

  private mergeServerNotes(serverNotes: StickyNoteResponse[]): void {
    const mapped = serverNotes.map((dto) => this.mapServerNote(dto));
    const serverIds = new Set(mapped.map((n) => n.id));
    const unsyncedLocal = this._notes().filter(
      (n) => !n.serverSynced && !serverIds.has(n.id)
    );
    this._notes.set([...mapped, ...unsyncedLocal]);
    this.persistStudioState();
  }

  private mapServerNote(dto: StickyNoteResponse): StickyNoteItem {
    const createdAt = Date.parse(dto.created_at);
    const updatedAt = Date.parse(dto.updated_at);
    const color: StickyNoteColor = isOneOf(dto.color, VALID_NOTE_COLORS)
      ? dto.color
      : 'cream';
    return {
      id: dto.id,
      title: dto.title ?? '',
      content: dto.body ?? '',
      color,
      pinned: Boolean(dto.pinned),
      sessionId: dto.origin_session_id ?? null,
      taskId: dto.task_id ?? null,
      createdAt: Number.isNaN(createdAt) ? Date.now() : createdAt,
      updatedAt: Number.isNaN(updatedAt) ? Date.now() : updatedAt,
      serverSynced: true,
      ...(typeof dto.pos_x === 'number' && Number.isFinite(dto.pos_x)
        ? { posX: dto.pos_x }
        : {}),
      ...(typeof dto.pos_y === 'number' && Number.isFinite(dto.pos_y)
        ? { posY: dto.pos_y }
        : {}),
      ...(typeof dto.z_index === 'number' && Number.isFinite(dto.z_index)
        ? { zIndex: dto.z_index }
        : {}),
    };
  }

  private applyServerStudioConfig(config: WorkspaceStudioConfigResponse): void {
    const nextScene = migrateSceneId(config.scene, this._scene());
    const nextClockStyle = isOneOf(config.clock_style, VALID_CLOCK_STYLES)
      ? config.clock_style
      : this._clockStyle();
    const nextClockSize = isOneOf(config.clock_size, VALID_CLOCK_SIZES)
      ? config.clock_size
      : this._clockSize();
    const nextShowSeconds =
      typeof config.show_seconds === 'boolean'
        ? config.show_seconds
        : this._showSeconds();
    const nextShowInTabTitle =
      typeof config.show_in_tab_title === 'boolean'
        ? config.show_in_tab_title
        : this._showInTabTitle();

    const blocklist = Array.isArray(config.blocklist)
      ? Array.from(
          new Set(
            config.blocklist
              .filter((item): item is string => typeof item === 'string')
              .map((item) => item.trim().toLowerCase())
              .filter((item) => item.length > 0)
          )
        )
      : this._shieldConfig().blocklist;

    const parkingLot: ParkingThoughtItem[] = Array.isArray(config.parking_lot)
      ? config.parking_lot
          .map((item): ParkingThoughtItem | null => {
            if (!item || typeof item.id !== 'string' || typeof item.text !== 'string') {
              return null;
            }
            const parsedCreated =
              typeof item.created_at === 'string' ? Date.parse(item.created_at) : NaN;
            const rawDone = item['done'];
            return {
              id: item.id,
              text: item.text,
              createdAt: Number.isNaN(parsedCreated) ? Date.now() : parsedCreated,
              done: typeof rawDone === 'boolean' ? rawDone : false,
            };
          })
          .filter((item): item is ParkingThoughtItem => item !== null)
      : this._shieldConfig().parkingLot;

    this._scene.set(nextScene);
    this._clockStyle.set(nextClockStyle);
    this._clockSize.set(nextClockSize);
    this._showSeconds.set(nextShowSeconds);
    this._showInTabTitle.set(nextShowInTabTitle);
    this._shieldConfig.set({
      tabGuardEnabled:
        typeof config.tab_guard_enabled === 'boolean'
          ? config.tab_guard_enabled
          : this._shieldConfig().tabGuardEnabled,
      zenLockEnabled:
        typeof config.zen_lock_enabled === 'boolean'
          ? config.zen_lock_enabled
          : this._shieldConfig().zenLockEnabled,
      blocklist,
      parkingLot,
    });
    this.persistStudioState();
  }

  private createNoteOnServer(note: StickyNoteItem): void {
    if (!this.http) {
      return;
    }

    const tempId = note.id;
    this.creatingNoteIds.add(tempId);

    const payload: CreateStickyNoteRequest = {
      title: note.title,
      body: note.content,
      color: note.color,
      pinned: note.pinned,
      pos_x: note.posX ?? null,
      pos_y: note.posY ?? null,
      z_index: note.zIndex ?? null,
      origin_session_id: note.sessionId,
      task_id: note.taskId,
    };

    this.http
      .post<StickyNoteResponse>(API_ENDPOINTS.SESSIONS.NOTES, payload, {
        withCredentials: true,
      })
      .pipe(
        catchError(() => of(null)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((created) => {
        this.creatingNoteIds.delete(tempId);
        if (!created) {
          this.deletedWhileCreating.delete(tempId);
          this.pendingPatchAfterCreate.delete(tempId);
          return;
        }

        if (this.deletedWhileCreating.has(tempId)) {
          this.deletedWhileCreating.delete(tempId);
          this.pendingPatchAfterCreate.delete(tempId);
          this.deleteNoteByIdOnServer(created.id);
          return;
        }

        const needsPatch = this.pendingPatchAfterCreate.delete(tempId);

        if (this.undoMeta?.type === 'create' && this.undoMeta.noteId === tempId) {
          this.undoMeta.noteId = created.id;
          this.undoMeta.synced = true;
        }

        const currentNotice = this.undoNotice();
        if (currentNotice && currentNotice.snapshot.some((n) => n.id === tempId)) {
          this.undoNotice.set({
            ...currentNotice,
            snapshot: currentNotice.snapshot.map((n) =>
              n.id === tempId ? { ...n, id: created.id, serverSynced: true } : n
            ),
          });
        }

        this._notes.update((items) =>
          items.map((item) =>
            item.id === tempId
              ? {
                  ...item,
                  id: created.id,
                  serverSynced: true,
                }
              : item
          )
        );
        this.persistStudioState();

        if (needsPatch) {
          this.scheduleNotePatch(created.id);
        }
      });
  }

  private scheduleNotePatch(noteId: string): void {
    if (!this.http) {
      return;
    }
    const note = this._notes().find((n) => n.id === noteId);
    if (!note) {
      return;
    }
    if (!note.serverSynced) {
      if (this.creatingNoteIds.has(noteId)) {
        this.pendingPatchAfterCreate.add(noteId);
      }
      return;
    }

    let subject = this.notePatchSubjects.get(noteId);
    if (!subject) {
      subject = new Subject<void>();
      this.notePatchSubjects.set(noteId, subject);
      subject
        .pipe(
          debounceTime(600),
          switchMap(() => {
            const latest = this._notes().find((n) => n.id === noteId);
            if (!latest || !latest.serverSynced) {
              return of(null);
            }
            const payload: UpdateStickyNoteRequest = {
              title: latest.title,
              body: latest.content,
              color: latest.color,
              pinned: latest.pinned,
              pos_x: latest.posX ?? null,
              pos_y: latest.posY ?? null,
              z_index: latest.zIndex ?? null,
            };
            return this.http!.patch<StickyNoteResponse>(
              API_ENDPOINTS.SESSIONS.NOTE_DETAIL(noteId),
              payload,
              { withCredentials: true }
            ).pipe(catchError(() => of(null)));
          }),
          takeUntilDestroyed(this.destroyRef)
        )
        .subscribe();
    }
    subject.next();
  }

  private cancelNotePatch(noteId: string): void {
    const subject = this.notePatchSubjects.get(noteId);
    if (subject) {
      subject.complete();
      this.notePatchSubjects.delete(noteId);
    }
  }

  private deleteNoteOnServer(note: StickyNoteItem): void {
    if (!this.http) {
      return;
    }
    if (!note.serverSynced) {
      if (this.creatingNoteIds.has(note.id)) {
        this.deletedWhileCreating.add(note.id);
      }
      return;
    }
    this.deleteNoteByIdOnServer(note.id);
  }

  private deleteNoteByIdOnServer(noteId: string): void {
    if (!this.http) {
      return;
    }
    this.http
      .delete<void>(API_ENDPOINTS.SESSIONS.NOTE_DETAIL(noteId), {
        withCredentials: true,
      })
      .pipe(
        catchError(() => of(null)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe();
  }

  private persistStudioState(): void {
    const snapshot: StudioPersistedState = {
      scene: this._scene(),
      clockStyle: this._clockStyle(),
      clockSize: this._clockSize(),
      showSeconds: this._showSeconds(),
      showInTabTitle: this._showInTabTitle(),
      leftPanelCollapsed: this._leftPanelCollapsed(),
      notesPanelOpen: this._notesPanelOpen(),
      notes: this._notes(),
      shieldConfig: this._shieldConfig(),
    };
    safeWriteStorage(STUDIO_STORAGE_KEY, JSON.stringify(snapshot));
  }
}
