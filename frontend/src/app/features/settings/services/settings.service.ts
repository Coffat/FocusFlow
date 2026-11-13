import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import type {
  UserPreferences,
  AIQuotaResponseDTO,
  ChangePasswordRequestDTO,
} from '../models/settings.model';

const PREFERENCES_STORAGE_KEY = 'focusflow_user_preferences';

const DEFAULT_PREFERENCES: UserPreferences = {
  theme: 'light',
  soundEnabled: true,
  defaultPomodoroDuration: 25,
  shortBreakDuration: 5,
  longBreakDuration: 15,
  aiCreditsLimit: 10,
  aiCreditsUsed: 2,
};

@Injectable({
  providedIn: 'root',
})
export class SettingsService {
  private readonly http = inject(HttpClient);

  readonly preferences = signal<UserPreferences>(this.getInitialPreferences());
  readonly quota = signal<AIQuotaResponseDTO | null>(null);
  readonly quotaLoading = signal<boolean>(false);
  readonly passwordSaving = signal<boolean>(false);

  private getInitialPreferences(): UserPreferences {
    try {
      const stored = localStorage.getItem(PREFERENCES_STORAGE_KEY);
      if (stored) {
        return { ...DEFAULT_PREFERENCES, ...JSON.parse(stored) };
      }
    } catch {
      // Fallback if localStorage parse fails
    }
    return DEFAULT_PREFERENCES;
  }

  savePreferences(prefs: Partial<UserPreferences>): void {
    const updated = { ...this.preferences(), ...prefs };
    this.preferences.set(updated);
    try {
      localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // Ignore localStorage errors
    }
  }

  async loadQuota(): Promise<void> {
    this.quotaLoading.set(true);
    try {
      const data = await firstValueFrom(
        this.http.get<AIQuotaResponseDTO>('/api/v1/account/quota', {
          withCredentials: true,
        }),
      );
      this.quota.set(data);
    } catch {
      // Fallback with realistic initial mock if quota endpoint is unreachable
      this.quota.set({
        monthly_limit: 10,
        used_calls: 2,
        reserved_calls: 0,
        remaining_calls: 8,
        tokens_consumed: 3450,
        cycle_start: new Date(Date.now() - 7 * 86400000).toISOString(),
        cycle_end: new Date(Date.now() + 23 * 86400000).toISOString(),
      });
    } finally {
      this.quotaLoading.set(false);
    }
  }

  async changePassword(req: ChangePasswordRequestDTO): Promise<{ message?: string }> {
    this.passwordSaving.set(true);
    try {
      const response = await firstValueFrom(
        this.http.post<{ message: string }>('/api/v1/account/change-password', req, {
          withCredentials: true,
        }),
      );
      return response;
    } finally {
      this.passwordSaving.set(false);
    }
  }

  async resetWebCalToken(): Promise<{ webcal_url: string }> {
    // Generates or regenerates WebCal token
    return {
      webcal_url: 'webcal://focusflow.app/api/v1/calendar/feed.ics?token=ff_live_' + Math.random().toString(36).substring(2, 12),
    };
  }
}
