import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import type {
  UserPreferences,
  AIQuotaResponseDTO,
  ChangePasswordRequestDTO,
  WebcalStatusResponseDTO,
  WebcalRotateResponseDTO,
  WebcalRevokeResponseDTO,
  AccountDataExportDTO,
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
  readonly quotaError = signal<string | null>(null);
  readonly passwordSaving = signal<boolean>(false);
  readonly webcalStatus = signal<WebcalStatusResponseDTO | null>(null);
  readonly webcalUrl = signal<string | null>(null);
  readonly webcalLoading = signal<boolean>(false);
  readonly webcalError = signal<string | null>(null);
  readonly exportLoading = signal<boolean>(false);
  readonly exportError = signal<string | null>(null);

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
    this.quotaError.set(null);
    try {
      const data = await firstValueFrom(
        this.http.get<AIQuotaResponseDTO>(API_ENDPOINTS.SETTINGS.QUOTA, {
          withCredentials: true,
        }),
      );
      this.quota.set(data);
    } catch {
      this.quota.set(null);
      this.quotaError.set('Không thể tải thông tin hạn ngạch AI. Vui lòng thử lại.');
    } finally {
      this.quotaLoading.set(false);
    }
  }

  async changePassword(req: ChangePasswordRequestDTO): Promise<{ message?: string }> {
    this.passwordSaving.set(true);
    try {
      const response = await firstValueFrom(
        this.http.post<{ message: string }>(API_ENDPOINTS.SETTINGS.CHANGE_PASSWORD, req, {
          withCredentials: true,
        }),
      );
      return response;
    } finally {
      this.passwordSaving.set(false);
    }
  }

  async loadWebcalStatus(): Promise<void> {
    this.webcalLoading.set(true);
    this.webcalError.set(null);
    try {
      const status = await firstValueFrom(
        this.http.get<WebcalStatusResponseDTO>(API_ENDPOINTS.CALENDAR.WEBCAL_STATUS, {
          withCredentials: true,
        }),
      );
      this.webcalStatus.set(status);
    } catch {
      this.webcalError.set('Không thể tải trạng thái liên kết WebCal. Vui lòng thử lại.');
    } finally {
      this.webcalLoading.set(false);
    }
  }

  async rotateWebcalToken(): Promise<WebcalRotateResponseDTO | null> {
    this.webcalLoading.set(true);
    this.webcalError.set(null);
    try {
      const res = await firstValueFrom(
        this.http.post<WebcalRotateResponseDTO>(
          API_ENDPOINTS.CALENDAR.WEBCAL_ROTATE,
          {},
          { withCredentials: true },
        ),
      );
      this.webcalUrl.set(res.webcal_url);
      this.webcalStatus.set({
        has_active_token: true,
        is_active: true,
        rotated_at: res.rotated_at,
        last_used_at: this.webcalStatus()?.last_used_at ?? null,
      });
      return res;
    } catch {
      this.webcalError.set('Không thể tạo hoặc xoay vòng liên kết WebCal. Vui lòng thử lại.');
      return null;
    } finally {
      this.webcalLoading.set(false);
    }
  }

  async revokeWebcalToken(): Promise<boolean> {
    this.webcalLoading.set(true);
    this.webcalError.set(null);
    try {
      await firstValueFrom(
        this.http.delete<WebcalRevokeResponseDTO>(API_ENDPOINTS.CALENDAR.WEBCAL_REVOKE, {
          withCredentials: true,
        }),
      );
      this.webcalUrl.set(null);
      this.webcalStatus.set({
        has_active_token: false,
        is_active: false,
        rotated_at: null,
        last_used_at: null,
      });
      return true;
    } catch {
      this.webcalError.set('Không thể thu hồi liên kết WebCal. Vui lòng thử lại.');
      return false;
    } finally {
      this.webcalLoading.set(false);
    }
  }

  async exportAccountData(): Promise<AccountDataExportDTO | null> {
    this.exportLoading.set(true);
    this.exportError.set(null);
    try {
      return await firstValueFrom(
        this.http.get<AccountDataExportDTO>(API_ENDPOINTS.SETTINGS.EXPORT, {
          withCredentials: true,
        }),
      );
    } catch {
      this.exportError.set('Không thể xuất dữ liệu cá nhân lúc này. Vui lòng thử lại sau.');
      return null;
    } finally {
      this.exportLoading.set(false);
    }
  }
}
