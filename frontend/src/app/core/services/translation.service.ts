import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export type LanguageCode = 'vi' | 'en';

export type TranslationNode = string | { [key: string]: TranslationNode };
export type TranslationDictionary = { [key: string]: TranslationNode };

@Injectable({
  providedIn: 'root'
})
export class TranslationService {
  private readonly http = inject(HttpClient, { optional: true });
  private readonly _currentLanguage = signal<LanguageCode>('vi');
  readonly currentLanguage = this._currentLanguage.asReadonly();
  private readonly _translations = signal<TranslationDictionary>({});
  readonly translations = this._translations.asReadonly();

  readonly currentLang = computed(() => this._currentLanguage());

  async loadTranslations(lang: LanguageCode) {
    if (!this.http) {
      this._currentLanguage.set(lang);
      return;
    }
    try {
      const data = await firstValueFrom(
        this.http.get<TranslationDictionary>(`/assets/i18n/${lang}.json`)
      );
      this._translations.set(data);
      this._currentLanguage.set(lang);
    } catch (_error) {
      // Keep existing translations
    }
  }

  async setLanguage(lang: LanguageCode) {
    await this.loadTranslations(lang);
  }

  get(keyPath: string): string {
    // Track both signals for zoneless change detection reactivity
    this._currentLanguage();
    const keys = keyPath.split('.');
    let current: TranslationNode = this._translations();

    for (const key of keys) {
      if (typeof current === 'object' && key in current) {
        current = current[key];
      } else {
        return keyPath;
      }
    }

    if (typeof current === 'string') {
      return current;
    }

    return keyPath;
  }
}
