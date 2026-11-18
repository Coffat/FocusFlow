import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { ThemeSignalService } from './theme-signal.service';

describe('ThemeSignalService', () => {
  let storageMap: Map<string, string>;
  let prefersDarkMatches = false;
  let mediaListeners: Array<(e: MediaQueryListEvent) => void> = [];
  let removeMediaSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    storageMap = new Map<string, string>();
    prefersDarkMatches = false;
    mediaListeners = [];
    removeMediaSpy = vi.fn((_type: string, cb: (e: MediaQueryListEvent) => void) => {
      mediaListeners = mediaListeners.filter((fn) => fn !== cb);
    });

    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storageMap.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storageMap.set(key, value);
      },
      removeItem: (key: string) => {
        storageMap.delete(key);
      },
      clear: () => {
        storageMap.clear();
      },
    });

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: prefersDarkMatches,
        media: query,
        onchange: null,
        addEventListener: (_type: string, cb: (e: MediaQueryListEvent) => void) => {
          mediaListeners.push(cb);
        },
        removeEventListener: removeMediaSpy,
        dispatchEvent: vi.fn(),
      })),
    });

    document.documentElement.classList.remove('dark', 'dark-mode');
  });

  afterEach(() => {
    TestBed.resetTestingModule();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    document.documentElement.classList.remove('dark', 'dark-mode');
  });

  it('defaults to light theme when storage is empty', () => {
    TestBed.configureTestingModule({});
    const service = TestBed.inject(ThemeSignalService);
    TestBed.flushEffects();

    expect(service.themePreference()).toBe('light');
    expect(service.isDark()).toBe(false);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(document.documentElement.classList.contains('dark-mode')).toBe(false);
  });

  it('reads initial theme from focusflow_user_preferences and syncs document classes', () => {
    storageMap.set(
      'focusflow_user_preferences',
      JSON.stringify({ theme: 'dark', soundEnabled: true })
    );

    TestBed.configureTestingModule({});
    const service = TestBed.inject(ThemeSignalService);
    TestBed.flushEffects();

    expect(service.themePreference()).toBe('dark');
    expect(service.isDark()).toBe(true);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(document.documentElement.classList.contains('dark-mode')).toBe(true);
  });

  it('tracks system prefers-color-scheme when theme is system', () => {
    prefersDarkMatches = false;
    TestBed.configureTestingModule({});
    const service = TestBed.inject(ThemeSignalService);

    service.setTheme('system');
    TestBed.flushEffects();
    expect(service.isDark()).toBe(false);

    // Simulate OS switching to dark mode
    for (const listener of mediaListeners) {
      listener({ matches: true } as MediaQueryListEvent);
    }
    TestBed.flushEffects();

    expect(service.isDark()).toBe(true);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(document.documentElement.classList.contains('dark-mode')).toBe(true);

    const saved = JSON.parse(storageMap.get('focusflow_user_preferences') ?? '{}') as {
      theme?: string;
    };
    expect(saved.theme).toBe('system');
  });

  it('syncs from storage on syncFromStorage() and storage event', () => {
    TestBed.configureTestingModule({});
    const service = TestBed.inject(ThemeSignalService);
    TestBed.flushEffects();
    expect(service.isDark()).toBe(false);

    storageMap.set('focusflow_user_preferences', JSON.stringify({ theme: 'dark' }));
    window.dispatchEvent(
      new StorageEvent('storage', { key: 'focusflow_user_preferences' })
    );
    TestBed.flushEffects();

    expect(service.themePreference()).toBe('dark');
    expect(service.isDark()).toBe(true);

    storageMap.set('focusflow_user_preferences', JSON.stringify({ theme: 'light' }));
    service.syncFromStorage();
    TestBed.flushEffects();

    expect(service.themePreference()).toBe('light');
    expect(service.isDark()).toBe(false);
  });

  it('cleans up matchMedia and storage listeners on destroy', () => {
    const removeWindowListenerSpy = vi.spyOn(window, 'removeEventListener');
    TestBed.configureTestingModule({});
    TestBed.inject(ThemeSignalService);

    TestBed.resetTestingModule();

    expect(removeMediaSpy).toHaveBeenCalledTimes(1);
    expect(removeWindowListenerSpy).toHaveBeenCalledWith(
      'storage',
      expect.any(Function)
    );
  });
});
