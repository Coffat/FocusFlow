import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import type {
  ProfileResponseDTO,
  UpdateProfileRequestDTO,
  LearnerMemoryResponseDTO,
  UpdateLearnerMemoryRequestDTO,
  SrlMetrics,
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

  readonly srlMetrics = signal<SrlMetrics>({
    optSessionMinutes: 45,
    completionRateBias: 1.05,
    learningStyle: 'Tuần tự & Tập trung sâu (Sequential Deep Work)',
  });

  async loadProfile(): Promise<void> {
    this.profileLoading.set(true);
    try {
      const data = await firstValueFrom(
        this.http.get<ProfileResponseDTO>('/api/v1/account/profile', {
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
        this.http.patch<ProfileResponseDTO>('/api/v1/account/profile', req, {
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
        this.http.get<LearnerMemoryResponseDTO[]>('/api/v1/account/learner-memory', {
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
      this.http.patch<LearnerMemoryResponseDTO>(`/api/v1/account/learner-memory/${id}`, req, {
        withCredentials: true,
      }),
    );
    this.learnerMemory.update((items) => items.map((item) => (item.id === id ? updated : item)));
  }

  async resetLearnerMemory(): Promise<void> {
    await firstValueFrom(
      this.http.post<void>(
        '/api/v1/account/learner-memory/reset',
        { confirm: true },
        { withCredentials: true },
      ),
    );
    this.learnerMemory.set([]);
  }
}
