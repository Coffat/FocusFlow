import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import type {
  ProfileResponseDTO,
  UpdateProfileRequestDTO,
  LearnerMemoryResponseDTO,
  UpdateLearnerMemoryRequestDTO,
  LearnerSrlProfileDTO,
} from '../models/profile.model';

@Injectable({
  providedIn: 'root',
})
export class ProfileService {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);

  readonly profile = signal<ProfileResponseDTO | null>(null);
  readonly profileLoading = signal<boolean>(false);
  readonly profileSaving = signal<boolean>(false);

  readonly learnerMemory = signal<readonly LearnerMemoryResponseDTO[]>([]);
  readonly memoryLoading = signal<boolean>(false);
  readonly memoryError = signal<string | null>(null);

  readonly srlProfile = computed<LearnerSrlProfileDTO | null>(
    () => this.profile()?.srl_profile ?? null,
  );
  readonly isSrlColdStart = computed<boolean>(() => this.srlProfile()?.is_cold_start ?? true);

  async loadProfile(): Promise<void> {
    this.profileLoading.set(true);
    try {
      const data = await firstValueFrom(
        this.http.get<ProfileResponseDTO>(API_ENDPOINTS.SETTINGS.PROFILE, {
          withCredentials: true,
        }),
      );
      this.profile.set(data);
    } catch {
      // Fallback to authService.currentUser if profile endpoint is unavailable or fails
      const user = this.authService.currentUser();
      if (user) {
        this.profile.set({
          id: user.id,
          email: user.email,
          full_name: user.fullName || user.email.split('@')[0],
          timezone: 'Asia/Ho_Chi_Minh',
          role: user.role,
          tier: user.tier,
          created_at: user.createdAt || new Date().toISOString(),
        });
      }
    } finally {
      this.profileLoading.set(false);
    }
  }

  async updateProfile(req: UpdateProfileRequestDTO): Promise<ProfileResponseDTO> {
    this.profileSaving.set(true);
    try {
      const updated = await firstValueFrom(
        this.http.patch<ProfileResponseDTO>(API_ENDPOINTS.SETTINGS.PROFILE, req, {
          withCredentials: true,
        }),
      );
      this.profile.set(updated);

      // Keep AuthService in sync so navbar reflects full name immediately
      const currentUser = this.authService.currentUser();
      if (currentUser) {
        this.authService.setUser({
          ...currentUser,
          fullName: updated.full_name,
        });
      }

      return updated;
    } finally {
      this.profileSaving.set(false);
    }
  }

  async loadLearnerMemory(): Promise<void> {
    this.memoryLoading.set(true);
    this.memoryError.set(null);
    try {
      const items = await firstValueFrom(
        this.http.get<LearnerMemoryResponseDTO[]>(API_ENDPOINTS.SETTINGS.LEARNER_MEMORY, {
          withCredentials: true,
        }),
      );
      this.learnerMemory.set(items);
    } catch {
      this.memoryError.set('Không thể tải Learner Memory. Hãy kiểm tra kết nối và thử lại.');
    } finally {
      this.memoryLoading.set(false);
    }
  }

  async updateMemory(id: string, req: UpdateLearnerMemoryRequestDTO): Promise<void> {
    const updated = await firstValueFrom(
      this.http.patch<LearnerMemoryResponseDTO>(
        API_ENDPOINTS.SETTINGS.LEARNER_MEMORY_DETAIL(id),
        req,
        {
          withCredentials: true,
        },
      ),
    );
    this.learnerMemory.update((items) => items.map((item) => (item.id === id ? updated : item)));
  }

  async resetLearnerMemory(): Promise<void> {
    await firstValueFrom(
      this.http.post<void>(
        API_ENDPOINTS.SETTINGS.LEARNER_MEMORY_RESET,
        { confirm: true },
        { withCredentials: true },
      ),
    );
    this.learnerMemory.set([]);
    await this.loadProfile();
  }
}
