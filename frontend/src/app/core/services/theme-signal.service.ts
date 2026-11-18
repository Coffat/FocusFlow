import {
  DestroyRef,
  Injectable,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';

export type ThemePreference = 'light' | 'dark' | 'system';

const PREFERENCES_STORAGE_KEY = 'focusflow_user_preferences';
const VALID_THEMES: readonly ThemePreference[] = ['light', 'dark', 'system'];

function isValidTheme(value: unknown): value is ThemePreference {
  return (
    typeof value === 'string' &&
    (VALID_THEMES as readonly string[]).includes(value)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

@Injectable({ providedIn: 'root' })
export class ThemeSignalService {
  private readonly destroyRef = inject(DestroyRef);

  private readonly _themePreference = signal<ThemePreference>(
    this.readThemeFromStorage()
  );
  readonly themePreference = this._themePreference.asReadonly();

  private readonly _systemPrefersDark = signal<boolean>(
    this.readSystemPrefersDark()
  );

  readonly isDark = computed<boolean>(() => {
    const pref = this._themePreference();
    return pref === 'dark' || (pref === 'system' && this._systemPrefersDark());
  });

  private readonly mediaQueryList: MediaQueryList | null =
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null;

  private readonly mediaChangeHandler = (event: MediaQueryListEvent): void => {
    this._systemPrefersDark.set(event.matches);
  };

  private readonly storageHandler = (event: StorageEvent): void => {
    if (event.key === PREFERENCES_STORAGE_KEY || event.key === null) {
      this.syncFromStorage();
    }
  };

  constructor() {
    effect(() => {
      const dark = this.isDark();
      if (typeof document !== 'undefined') {
        document.documentElement.classList.toggle('dark', dark);
        document.documentElement.classList.toggle('dark-mode', dark);
      }
    });

    if (this.mediaQueryList) {
      this.mediaQueryList.addEventListener('change', this.mediaChangeHandler);
    }

    if (typeof window !== 'undefined') {
      window.addEventListener('storage', this.storageHandler);
    }

    this.destroyRef.onDestroy(() => {
      if (this.mediaQueryList) {
        this.mediaQueryList.removeEventListener(
          'change',
          this.mediaChangeHandler
        );
      }
      if (typeof window !== 'undefined') {
        window.removeEventListener('storage', this.storageHandler);
      }
    });
  }

  setTheme(theme: ThemePreference): void {
    this._themePreference.set(theme);
    this.writeThemeToStorage(theme);
  }

  syncFromStorage(): void {
    this._themePreference.set(this.readThemeFromStorage());
  }

  private readThemeFromStorage(): ThemePreference {
    try {
      if (typeof localStorage === 'undefined') {
        return 'light';
      }
      const raw = localStorage.getItem(PREFERENCES_STORAGE_KEY);
      if (!raw) {
        return 'light';
      }
      const parsed: unknown = JSON.parse(raw);
      if (isRecord(parsed) && isValidTheme(parsed['theme'])) {
        return parsed['theme'];
      }
    } catch {
      // Ignore storage or JSON parse errors
    }
    return 'light';
  }

  private writeThemeToStorage(theme: ThemePreference): void {
    try {
      if (typeof localStorage === 'undefined') {
        return;
      }
      const raw = localStorage.getItem(PREFERENCES_STORAGE_KEY);
      let existing: Record<string, unknown> = {};
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        if (isRecord(parsed)) {
          existing = parsed;
        }
      }
      localStorage.setItem(
        PREFERENCES_STORAGE_KEY,
        JSON.stringify({ ...existing, theme })
      );
    } catch {
      // Ignore storage errors
    }
  }

  private readSystemPrefersDark(): boolean {
    if (
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function'
    ) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  }
}
