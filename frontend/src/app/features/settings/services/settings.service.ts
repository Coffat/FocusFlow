import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import type { components } from '../../../core/api/schema';
import { UserPreferences } from '../models/settings.model';

type LearnerMemory = components['schemas']['LearnerMemoryResponseDTO'];
type MemoryUpdate = components['schemas']['UpdateLearnerMemoryRequestDTO'];

@Injectable({
  providedIn: 'root',
})
export class SettingsService {
  private readonly http = inject(HttpClient);

  readonly preferences = signal<UserPreferences>({
    theme: 'light',
    soundEnabled: true,
    defaultPomodoroDuration: 25,
    aiCreditsLimit: 10,
    aiCreditsUsed: 2,
  });

  readonly learnerMemory = signal<readonly LearnerMemory[]>([]);
  readonly memoryLoading = signal(false);
  readonly memoryError = signal<string | null>(null);

  async loadLearnerMemory(): Promise<void> {
    this.memoryLoading.set(true);
    this.memoryError.set(null);
    try {
      const items = await firstValueFrom(
        this.http.get<LearnerMemory[]>('/api/v1/account/learner-memory', { withCredentials: true }),
      );
      this.learnerMemory.set(items);
    } catch {
      this.memoryError.set('Không thể tải Learner Memory. Hãy kiểm tra kết nối và thử lại.');
    } finally {
      this.memoryLoading.set(false);
    }
  }

  async updateMemory(id: string, request: MemoryUpdate): Promise<void> {
    const updated = await firstValueFrom(
      this.http.patch<LearnerMemory>(`/api/v1/account/learner-memory/${id}`, request, {
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
        {
          withCredentials: true,
        },
      ),
    );
    this.learnerMemory.set([]);
  }
}
