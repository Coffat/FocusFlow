import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { UserPreferences } from '../models/settings.model';

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private readonly http = inject(HttpClient);

  readonly preferences = signal<UserPreferences>({
    theme: 'light',
    soundEnabled: true,
    defaultPomodoroDuration: 25,
    aiCreditsLimit: 10,
    aiCreditsUsed: 2
  });
}
