import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { vi } from 'vitest';
import { ThemeSignalService } from '../../../core/services/theme-signal.service';
import { StickyNoteResponse, WorkspaceStudioConfigResponse } from '../models/workspace.model';
import { WORKSPACE_SCENES, WorkspaceStudioStore } from './workspace-studio.store';

let mockStore: Record<string, string> = {};
let httpMock: HttpTestingController | null = null;

const storageMock: Storage = {
  getItem: (key: string) => mockStore[key] ?? null,
  setItem: (key: string, value: string) => {
    mockStore[key] = value;
  },
  removeItem: (key: string) => {
    delete mockStore[key];
  },
  clear: () => {
    mockStore = {};
  },
  key: (index: number) => Object.keys(mockStore)[index] ?? null,
  get length() {
    return Object.keys(mockStore).length;
  },
};

function createStore(): WorkspaceStudioStore {
  TestBed.configureTestingModule({
    providers: [WorkspaceStudioStore, provideHttpClient(), provideHttpClientTesting()],
  });
  httpMock = TestBed.inject(HttpTestingController);
  return TestBed.inject(WorkspaceStudioStore);
}

function makeServerNote(overrides: Partial<StickyNoteResponse> = {}): StickyNoteResponse {
  return {
    id: '01933c2a-1111-7000-8000-000000000001',
    task_id: null,
    title: 'Server Note',
    body: 'Body from server',
    color: 'sage',
    pinned: true,
    pos_x: 120,
    pos_y: 80,
    z_index: 2,
    origin_session_id: null,
    created_at: '2026-11-18T10:00:00Z',
    updated_at: '2026-11-18T10:05:00Z',
    ...overrides,
  };
}

function makeServerConfig(
  overrides: Partial<WorkspaceStudioConfigResponse> = {}
): WorkspaceStudioConfigResponse {
  return {
    scene: 'lofi-night',
    clock_style: 'ring',
    clock_size: 'lg',
    show_seconds: true,
    show_in_tab_title: true,
    tab_guard_enabled: true,
    zen_lock_enabled: false,
    blocklist: ['facebook.com', 'youtube.com', 'tiktok.com'],
    parking_lot: [],
    updated_at: '2026-11-18T10:00:00Z',
    ...overrides,
  };
}

describe('WorkspaceStudioStore', () => {
  beforeAll(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: storageMock,
      writable: true,
      configurable: true,
    });
  });

  beforeEach(() => {
    storageMock.clear();
    httpMock = null;
    TestBed.resetTestingModule();
  });

  afterEach(() => {
    httpMock?.verify();
    TestBed.resetTestingModule();
    vi.useRealTimers();
    vi.restoreAllMocks();
    storageMock.clear();
  });

  it('initializes with default state and default user duration preferences', () => {
    const store = createStore();

    expect(store.scene()).toBe('lofi-night');
    expect(store.clockStyle()).toBe('ring');
    expect(store.clockSize()).toBe('lg');
    expect(store.showSeconds()).toBe(true);
    expect(store.showInTabTitle()).toBe(true);
    expect(store.leftPanelCollapsed()).toBe(false);
    expect(store.notesPanelOpen()).toBe(false);
    expect(store.activeToolPopover()).toBeNull();
    expect(store.notes()).toEqual([]);
    expect(store.sortedNotes()).toEqual([]);
    expect(store.serializedNotesLength()).toBe(0);

    expect(store.shieldConfig()).toEqual({
      tabGuardEnabled: true,
      zenLockEnabled: false,
      blocklist: ['facebook.com', 'youtube.com', 'tiktok.com'],
      parkingLot: [],
    });
    expect(store.distractionCount()).toBe(0);
    expect(store.showReturnBanner()).toBe(false);
    expect(store.isFullscreen()).toBe(false);
    expect(store.focusScore()).toBe(100);

    expect(store.defaultPomodoroMinutes()).toBe(25);
    expect(store.shortBreakMinutes()).toBe(5);
    expect(store.longBreakMinutes()).toBe(15);
    expect(store.soundEnabledPreference()).toBe(true);
  });

  it('reads user duration preferences safely from focusflow_user_preferences', () => {
    storageMock.setItem(
      'focusflow_user_preferences',
      JSON.stringify({
        defaultPomodoroDuration: 50,
        shortBreakDuration: 10,
        longBreakDuration: 20,
        soundEnabled: false,
      })
    );

    const store = createStore();

    expect(store.defaultPomodoroMinutes()).toBe(50);
    expect(store.shortBreakMinutes()).toBe(10);
    expect(store.longBreakMinutes()).toBe(20);
    expect(store.soundEnabledPreference()).toBe(false);
  });

  it('falls back to defaults when localStorage contains invalid JSON or throws', () => {
    storageMock.setItem('focusflow_user_preferences', '{bad-json');
    storageMock.setItem('focusflow_workspace_studio_v1', 'not-json');

    const store = createStore();
    expect(store.scene()).toBe('lofi-night');
    expect(store.defaultPomodoroMinutes()).toBe(25);

    vi.spyOn(storageMock, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    expect(() => store.setScene('rain')).not.toThrow();
    expect(store.scene()).toBe('rain');
  });

  it('updates UI preferences and persists to focusflow_workspace_studio_v1', () => {
    const store = createStore();

    store.setScene('cafe');
    store.setClockStyle('ring');
    store.setClockSize('md');
    store.toggleShowSeconds();
    store.toggleShowInTabTitle();
    store.toggleLeftPanel();
    store.setNotesPanelOpen(true);

    expect(store.scene()).toBe('cafe');
    expect(store.clockStyle()).toBe('ring');
    expect(store.clockSize()).toBe('md');
    expect(store.showSeconds()).toBe(false);
    expect(store.showInTabTitle()).toBe(false);
    expect(store.leftPanelCollapsed()).toBe(true);
    expect(store.notesPanelOpen()).toBe(true);

    store.setLeftPanelCollapsed(false);
    store.toggleNotesPanel();
    expect(store.leftPanelCollapsed()).toBe(false);
    expect(store.notesPanelOpen()).toBe(false);

    store.toggleToolPopover('audio');
    expect(store.activeToolPopover()).toBe('audio');
    store.toggleToolPopover('audio');
    expect(store.activeToolPopover()).toBeNull();
    store.toggleToolPopover('scene');
    expect(store.activeToolPopover()).toBe('scene');
    store.closeToolPopover();
    expect(store.activeToolPopover()).toBeNull();

    // Verify persistence across reload
    TestBed.resetTestingModule();
    const reloaded = createStore();
    expect(reloaded.scene()).toBe('cafe');
    expect(reloaded.clockStyle()).toBe('ring');
    expect(reloaded.clockSize()).toBe('md');
    expect(reloaded.showSeconds()).toBe(false);
    expect(reloaded.showInTabTitle()).toBe(false);
    expect(reloaded.activeToolPopover()).toBeNull();
  });

  it('supports sticky notes CRUD and sorts pinned first then newest updatedAt', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-18T10:00:00Z'));

    const store = createStore();
    const n1 = store.addNote('cream', 'Note 1', 'First');
    vi.setSystemTime(new Date('2026-11-18T10:01:00Z'));
    const n2 = store.addNote('sage', 'Note 2', 'Second');
    vi.setSystemTime(new Date('2026-11-18T10:02:00Z'));
    const n3 = store.addNote('amber', 'Note 3', 'Third');

    expect(store.sortedNotes().map((n) => n.id)).toEqual([n3.id, n2.id, n1.id]);

    vi.setSystemTime(new Date('2026-11-18T10:03:00Z'));
    store.togglePin(n1.id);
    expect(store.sortedNotes().map((n) => n.id)).toEqual([n1.id, n3.id, n2.id]);

    vi.setSystemTime(new Date('2026-11-18T10:04:00Z'));
    store.updateNote(n2.id, { title: 'Updated 2', content: 'New body', color: 'lavender' });
    const updated2 = store.notes().find((n) => n.id === n2.id);
    expect(updated2?.title).toBe('Updated 2');
    expect(updated2?.content).toBe('New body');
    expect(updated2?.color).toBe('lavender');
    expect(store.sortedNotes().map((n) => n.id)).toEqual([n1.id, n2.id, n3.id]);

    store.deleteNote(n3.id);
    expect(store.notes().map((n) => n.id)).not.toContain(n3.id);

    vi.useRealTimers();
  });

  it('serializes and hydrates notes via scratchpad markers within 9800 chars', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-18T10:00:00Z'));

    const store = createStore();
    expect(store.serializeNotesForScratchpad()).toBe('');

    const n1 = store.addNote('sage', 'Ý chính', 'Nội dung 1');
    store.togglePin(n1.id);
    vi.setSystemTime(new Date('2026-11-18T10:01:00Z'));
    store.addNote('lavender', 'Câu hỏi', 'Nội dung 2');

    const serialized = store.serializeNotesForScratchpad();
    expect(serialized).toContain('<!--ff-note:sage:1:Ý chính-->\nNội dung 1');
    expect(serialized).toContain('\n\n---\n\n');
    expect(serialized).toContain('<!--ff-note:lavender:0:Câu hỏi-->\nNội dung 2');
    expect(store.serializedNotesLength()).toBe(serialized.length);

    // Hydrate into a fresh store
    storageMock.clear();
    TestBed.resetTestingModule();
    const freshStore = createStore();
    freshStore.hydrateNotesFromScratchpad('');
    expect(freshStore.notes()).toEqual([]);

    freshStore.hydrateNotesFromScratchpad(serialized);
    expect(freshStore.sortedNotes().length).toBe(2);
    expect(freshStore.sortedNotes()[0].pinned).toBe(true);
    expect(freshStore.sortedNotes()[0].color).toBe('sage');
    expect(freshStore.sortedNotes()[0].title).toBe('Ý chính');
    expect(freshStore.sortedNotes()[0].content).toBe('Nội dung 1');
    expect(freshStore.sortedNotes()[1].pinned).toBe(false);
    expect(freshStore.sortedNotes()[1].color).toBe('lavender');

    // Enforce <= 9800 chars cap
    freshStore.addNote('cream', 'Long', 'x'.repeat(12000));
    const capped = freshStore.serializeNotesForScratchpad();
    expect(capped.length).toBeLessThanOrEqual(9800);

    vi.useRealTimers();
  });

  it('hydrates legacy plain text scratchpad as a single pinned note without duplicates', () => {
    const store = createStore();
    store.hydrateNotesFromScratchpad('Ghi chú cũ không có marker');

    expect(store.notes().length).toBe(1);
    expect(store.notes()[0].title).toBe('Ghi chú phiên học');
    expect(store.notes()[0].content).toBe('Ghi chú cũ không có marker');
    expect(store.notes()[0].pinned).toBe(true);

    // Calling again with same content does not duplicate
    store.hydrateNotesFromScratchpad('Ghi chú cũ không có marker');
    expect(store.notes().length).toBe(1);
  });

  it('manages Focus Shield state, distractions, blocklist, and parking lot', () => {
    const store = createStore();

    store.setTabGuardEnabled(false);
    store.setZenLockEnabled(true);
    store.setFullscreen(true);
    expect(store.shieldConfig().tabGuardEnabled).toBe(false);
    expect(store.shieldConfig().zenLockEnabled).toBe(true);
    expect(store.isFullscreen()).toBe(true);

    store.recordDistraction();
    store.recordDistraction();
    expect(store.distractionCount()).toBe(2);
    expect(store.showReturnBanner()).toBe(true);
    expect(store.focusScore()).toBe(84);

    store.dismissReturnBanner();
    expect(store.showReturnBanner()).toBe(false);

    for (let i = 0; i < 20; i++) {
      store.recordDistraction();
    }
    expect(store.focusScore()).toBe(0);

    store.resetSessionDistractions();
    expect(store.distractionCount()).toBe(0);
    expect(store.showReturnBanner()).toBe(false);
    expect(store.focusScore()).toBe(100);

    // Blocklist normalization & deduplication
    store.addBlockedSite('  Reddit.COM ');
    store.addBlockedSite('reddit.com');
    store.addBlockedSite('   ');
    expect(store.shieldConfig().blocklist).toContain('reddit.com');
    expect(
      store.shieldConfig().blocklist.filter((s) => s === 'reddit.com').length
    ).toBe(1);

    store.removeBlockedSite('REDDIT.COM');
    expect(store.shieldConfig().blocklist).not.toContain('reddit.com');

    // Parking lot CRUD
    store.addThought('  Mua sách mới  ');
    store.addThought('   ');
    store.addThought('Gửi email');
    expect(store.shieldConfig().parkingLot.length).toBe(2);

    const firstId = store.shieldConfig().parkingLot[0].id;
    const secondId = store.shieldConfig().parkingLot[1].id;
    store.toggleThought(firstId);
    expect(store.shieldConfig().parkingLot[0].done).toBe(true);

    store.clearCompletedThoughts();
    expect(store.shieldConfig().parkingLot.map((t) => t.id)).toEqual([secondId]);

    store.removeThought(secondId);
    expect(store.shieldConfig().parkingLot).toEqual([]);
  });

  it('migrates legacy scenes and computes isDarkSurface and focusMode', () => {
    storageMock.setItem(
      'focusflow_workspace_studio_v1',
      JSON.stringify({ scene: 'forest' })
    );
    const store1 = createStore();
    expect(store1.scene()).toBe('library');
    expect(store1.isDarkSurface()).toBe(true);

    TestBed.resetTestingModule();
    storageMock.setItem(
      'focusflow_workspace_studio_v1',
      JSON.stringify({ scene: 'dawn' })
    );
    const store2 = createStore();
    expect(store2.scene()).toBe('lofi-night');
    expect(WORKSPACE_SCENES.length).toBe(5);

    store2.setScene('architectural');
    expect(store2.isDarkSurface()).toBe(false);

    const themeSignal = TestBed.inject(ThemeSignalService);
    themeSignal.setTheme('dark');
    expect(store2.isDarkSurface()).toBe(true);

    expect(store2.focusMode()).toBe(false);
    store2.toggleFocusMode();
    expect(store2.focusMode()).toBe(true);
    store2.setFocusMode(false);
    expect(store2.focusMode()).toBe(false);
  });

  it('manages pinned notes limit, composer pinning, unpinning, undo, and safe serialization truncation', () => {
    vi.useFakeTimers();
    const store = createStore();

    expect(store.pinNewNoteFromComposer('   ', 'cream', null, null)).toBeNull();

    for (let i = 1; i <= 5; i++) {
      vi.advanceTimersByTime(10);
      store.pinNewNoteFromComposer(
        `Ghi chú ${i}`,
        'amber',
        'sess-01',
        'task-01'
      );
    }
    httpMock!.match('/api/v1/sessions/notes').forEach((req, idx) =>
      req.flush(
        makeServerNote({
          id: `01933c2a-0000-7000-8000-00000000000${idx + 1}`,
          body: req.request.body.body,
          color: req.request.body.color,
          pinned: req.request.body.pinned,
          origin_session_id: req.request.body.origin_session_id,
          task_id: req.request.body.task_id,
        })
      )
    );

    expect(store.collectionNotes().length).toBe(5);
    expect(store.visiblePinnedNotes().length).toBe(4);
    expect(store.visiblePinnedNotes()[0].sessionId).toBe('sess-01');
    expect(store.visiblePinnedNotes()[0].taskId).toBe('task-01');

    const topId = store.visiblePinnedNotes()[0].id;
    store.unpinNote(topId);
    expect(store.collectionNotes().length).toBe(5);
    expect(store.collectionNotes().find((n) => n.id === topId)?.pinned).toBe(
      false
    );

    store.deleteNote(topId);
    httpMock!
      .expectOne(`/api/v1/sessions/notes/${topId}`)
      .flush(null, { status: 204, statusText: 'No Content' });
    expect(store.collectionNotes().length).toBe(4);
    expect(store.undoNotice()).not.toBeNull();

    store.undoLastNoteAction();
    httpMock!
      .expectOne('/api/v1/sessions/notes')
      .flush(makeServerNote({ id: '01933c2a-0000-7000-8000-000000000099' }));
    expect(store.collectionNotes().length).toBe(5);
    expect(store.undoNotice()).toBeNull();

    const restoredTopId = store.collectionNotes().find((n) => n.pinned === false)?.id ?? topId;
    store.deleteNote(restoredTopId);
    httpMock!
      .expectOne(`/api/v1/sessions/notes/${restoredTopId}`)
      .flush(null, { status: 204, statusText: 'No Content' });
    expect(store.undoNotice()).not.toBeNull();
    vi.advanceTimersByTime(5000);
    expect(store.undoNotice()).toBeNull();

    // Serialization truncates output at 9800 chars without mutating local notes
    const longContent = 'x'.repeat(10000);
    store.pinNewNoteFromComposer(longContent, 'sage', null, null);
    httpMock!
      .expectOne('/api/v1/sessions/notes')
      .flush(makeServerNote({ id: '01933c2a-0000-7000-8000-000000000100', body: longContent }));
    const serialized = store.serializeNotesForScratchpad();
    expect(serialized.length).toBeLessThanOrEqual(9800);
    expect(store.isScratchpadOverLimit()).toBe(true);
    expect(store.notes()[0].content.length).toBe(10000);

    vi.useRealTimers();
  });

  it('configures architectural without imageUrl and maps all 4 scene WebP paths', () => {
    const byId = new Map(WORKSPACE_SCENES.map((scene) => [scene.id, scene]));
    expect(byId.get('architectural')?.imageUrl).toBeUndefined();
    expect(byId.get('lofi-night')?.imageUrl).toBe('/assets/scenes/lofi-night.webp');
    expect(byId.get('rain')?.imageUrl).toBe('/assets/scenes/rain-window.webp');
    expect(byId.get('cafe')?.imageUrl).toBe('/assets/scenes/cozy-cafe.webp');
    expect(byId.get('library')?.imageUrl).toBe('/assets/scenes/quiet-library.webp');
  });

  it('stores trimmed optional title when pinning a new note from composer', () => {
    const store = createStore();
    const withTitle = store.pinNewNoteFromComposer(
      'Nội dung có tiêu đề',
      'lavender',
      'sess-02',
      'task-02',
      '  Ghi chú quan trọng  '
    );
    expect(withTitle?.title).toBe('Ghi chú quan trọng');

    const withoutTitle = store.pinNewNoteFromComposer(
      'Nội dung không tiêu đề',
      'cream',
      null,
      null
    );
    expect(withoutTitle?.title).toBe('');

    const reqs = httpMock!.match('/api/v1/sessions/notes');
    expect(reqs.length).toBe(2);
    reqs.forEach((req, idx) =>
      req.flush(makeServerNote({ id: `01933c2a-0000-7000-8000-00000000020${idx}` }))
    );
  });

  it('persists note coordinates via updateNotePosition and manages zIndex via bringNoteToFront', () => {
    const store = createStore();
    const n1 = store.pinNewNoteFromComposer('Ghi chú 1', 'cream', null, null);
    const n2 = store.pinNewNoteFromComposer('Ghi chú 2', 'sage', null, null);
    expect(n1).not.toBeNull();
    expect(n2).not.toBeNull();
    expect(n1!.zIndex).toBe(1);
    expect(n2!.zIndex).toBe(2);

    const postReqs = httpMock!.match('/api/v1/sessions/notes');
    expect(postReqs.length).toBe(2);
    postReqs[0].flush(makeServerNote({ id: '01933c2a-0000-7000-8000-000000000301', z_index: 1 }));
    postReqs[1].flush(makeServerNote({ id: '01933c2a-0000-7000-8000-000000000302', z_index: 2 }));

    store.updateNotePosition('01933c2a-0000-7000-8000-000000000301', 240, 180);
    store.bringNoteToFront('01933c2a-0000-7000-8000-000000000301');

    const updatedN1 = store
      .notes()
      .find((n) => n.id === '01933c2a-0000-7000-8000-000000000301');
    expect(updatedN1?.posX).toBe(240);
    expect(updatedN1?.posY).toBe(180);
    expect(updatedN1?.zIndex).toBe(3);

    // Verify persistence across reload
    TestBed.resetTestingModule();
    const reloaded = createStore();
    const reloadedN1 = reloaded
      .notes()
      .find((n) => n.id === '01933c2a-0000-7000-8000-000000000301');
    expect(reloadedN1?.posX).toBe(240);
    expect(reloadedN1?.posY).toBe(180);
    expect(reloadedN1?.zIndex).toBe(3);
  });

  it('syncFromServer() hydrates notes (preserving unsynced local notes) and studio config, tolerating partial failure', () => {
    const store = createStore();
    const localUnsynced = store.addNote('cream', 'Local Only', 'Offline draft');

    store.syncFromServer();

    const notesReq = httpMock!.expectOne('/api/v1/sessions/notes');
    expect(notesReq.request.method).toBe('GET');
    expect(notesReq.request.withCredentials).toBe(true);
    notesReq.flush([
      makeServerNote({
        id: '01933c2a-1111-7000-8000-000000000001',
        title: 'Server Title',
        body: 'Server Body',
        color: 'blue',
        pinned: true,
        pos_x: 44,
        pos_y: 88,
        z_index: 5,
      }),
    ]);

    const configReq = httpMock!.expectOne('/api/v1/sessions/studio-config');
    expect(configReq.request.method).toBe('GET');
    expect(configReq.request.withCredentials).toBe(true);
    configReq.flush(
      makeServerConfig({
        scene: 'cafe',
        clock_style: 'flip',
        clock_size: 'md',
        show_seconds: false,
        show_in_tab_title: false,
        tab_guard_enabled: false,
        zen_lock_enabled: true,
        blocklist: ['x.com', 'reddit.com'],
        parking_lot: [
          {
            id: 'thought-srv-1',
            text: 'Check docs',
            created_at: '2026-11-18T09:00:00Z',
            done: true,
          },
        ],
      })
    );

    expect(store.notes().length).toBe(2);
    const serverNote = store
      .notes()
      .find((n) => n.id === '01933c2a-1111-7000-8000-000000000001');
    expect(serverNote?.title).toBe('Server Title');
    expect(serverNote?.content).toBe('Server Body');
    expect(serverNote?.color).toBe('blue');
    expect(serverNote?.posX).toBe(44);
    expect(serverNote?.posY).toBe(88);
    expect(serverNote?.zIndex).toBe(5);
    expect(serverNote?.serverSynced).toBe(true);
    expect(store.notes().some((n) => n.id === localUnsynced.id)).toBe(true);

    expect(store.scene()).toBe('cafe');
    expect(store.clockStyle()).toBe('flip');
    expect(store.clockSize()).toBe('md');
    expect(store.showSeconds()).toBe(false);
    expect(store.showInTabTitle()).toBe(false);
    expect(store.shieldConfig()).toEqual({
      tabGuardEnabled: false,
      zenLockEnabled: true,
      blocklist: ['x.com', 'reddit.com'],
      parkingLot: [
        {
          id: 'thought-srv-1',
          text: 'Check docs',
          createdAt: Date.parse('2026-11-18T09:00:00Z'),
          done: true,
        },
      ],
    });

    // One failing stream never blocks the other
    store.syncFromServer();
    httpMock!
      .expectOne('/api/v1/sessions/notes')
      .flush({ detail: 'Server Error' }, { status: 500, statusText: 'Server Error' });
    httpMock!
      .expectOne('/api/v1/sessions/studio-config')
      .flush(makeServerConfig({ scene: 'library' }));
    expect(store.scene()).toBe('library');
    expect(store.notes().length).toBe(2);
  });

  it('sends POST, debounced PATCH, and DELETE for sticky notes and falls back silently on error', () => {
    vi.useFakeTimers();
    const store = createStore();

    const createdLocal = store.pinNewNoteFromComposer(
      'Initial body',
      'amber',
      'sess-1',
      'task-1',
      'Initial title'
    );
    expect(createdLocal).not.toBeNull();
    const tempId = createdLocal!.id;

    const postReq = httpMock!.expectOne('/api/v1/sessions/notes');
    expect(postReq.request.method).toBe('POST');
    expect(postReq.request.withCredentials).toBe(true);
    expect(postReq.request.body).toEqual({
      title: 'Initial title',
      body: 'Initial body',
      color: 'amber',
      pinned: true,
      pos_x: null,
      pos_y: null,
      z_index: 1,
      origin_session_id: 'sess-1',
      task_id: 'task-1',
    });

    const serverId = '01933c2a-9999-7000-8000-000000000001';
    postReq.flush(makeServerNote({ id: serverId, title: 'Initial title', body: 'Initial body' }));

    const syncedNote = store.notes().find((n) => n.id === serverId);
    expect(syncedNote).toBeDefined();
    expect(syncedNote?.serverSynced).toBe(true);
    expect(store.notes().find((n) => n.id === tempId)).toBeUndefined();

    // Multiple rapid mutations coalesce into one debounced PATCH after 600ms
    store.updateNote(serverId, { title: 'Updated title', content: 'Updated body', color: 'sage' });
    store.updateNotePosition(serverId, 150, 220);
    store.unpinNote(serverId);
    store.togglePin(serverId);

    vi.advanceTimersByTime(599);
    httpMock!.expectNone(`/api/v1/sessions/notes/${serverId}`);

    vi.advanceTimersByTime(1);
    const patchReq = httpMock!.expectOne(`/api/v1/sessions/notes/${serverId}`);
    expect(patchReq.request.method).toBe('PATCH');
    expect(patchReq.request.withCredentials).toBe(true);
    expect(patchReq.request.body).toEqual({
      title: 'Updated title',
      body: 'Updated body',
      color: 'sage',
      pinned: true,
      pos_x: 150,
      pos_y: 220,
      z_index: 1,
    });
    patchReq.flush(makeServerNote({ id: serverId }));

    // Delete sends DELETE immediately
    store.deleteNote(serverId);
    const delReq = httpMock!.expectOne(`/api/v1/sessions/notes/${serverId}`);
    expect(delReq.request.method).toBe('DELETE');
    expect(delReq.request.withCredentials).toBe(true);
    delReq.flush(null, { status: 204, statusText: 'No Content' });

    // Offline POST failure keeps local note in store and localStorage
    const offlineNote = store.pinNewNoteFromComposer('Offline content', 'cream', null, null);
    const failedPost = httpMock!.expectOne('/api/v1/sessions/notes');
    failedPost.error(new ProgressEvent('error'));
    expect(store.notes().find((n) => n.id === offlineNote!.id)?.serverSynced).toBe(false);
  });

  it('debounces PUT /api/v1/sessions/studio-config (600ms) across studio config mutations', () => {
    vi.useFakeTimers();
    const store = createStore();

    store.setScene('rain');
    store.setClockStyle('editorial');
    store.setClockSize('md');
    store.toggleShowSeconds();
    store.toggleShowInTabTitle();
    store.setTabGuardEnabled(false);
    store.setZenLockEnabled(true);
    store.addBlockedSite('news.ycombinator.com');
    store.removeBlockedSite('tiktok.com');
    store.addThought('Need water');
    const thoughtId = store.shieldConfig().parkingLot[0].id;
    store.toggleThought(thoughtId);

    vi.advanceTimersByTime(599);
    httpMock!.expectNone('/api/v1/sessions/studio-config');

    vi.advanceTimersByTime(1);
    const putReq = httpMock!.expectOne('/api/v1/sessions/studio-config');
    expect(putReq.request.method).toBe('PUT');
    expect(putReq.request.withCredentials).toBe(true);
    expect(putReq.request.body).toMatchObject({
      scene: 'rain',
      clock_style: 'editorial',
      clock_size: 'md',
      show_seconds: false,
      show_in_tab_title: false,
      tab_guard_enabled: false,
      zen_lock_enabled: true,
      blocklist: ['facebook.com', 'youtube.com', 'news.ycombinator.com'],
    });
    expect(putReq.request.body.parking_lot).toHaveLength(1);
    expect(putReq.request.body.parking_lot[0].text).toBe('Need water');
    expect(putReq.request.body.parking_lot[0].done).toBe(true);
    putReq.flush(makeServerConfig({ scene: 'rain' }));
  });
});
