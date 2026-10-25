import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export type LanguageCode = 'vi' | 'en';

export type TranslationNode = string | { [key: string]: TranslationNode };
export type TranslationDictionary = { [key: string]: TranslationNode };

@Injectable({
  providedIn: 'root'
})
export class TranslationService {
  http: HttpClient;
  currentLanguage = signal<LanguageCode>('vi');
  translations = signal<TranslationDictionary>({});

  currentLang = computed(() => this.currentLanguage());

  constructor(http: HttpClient) {
    this.http = http;
  }

  async loadTranslations(lang: LanguageCode) {
    try {
      const data = await firstValueFrom(
        this.http.get<TranslationDictionary>(`/assets/i18n/${lang}.json`)
      );
      this.translations.set(data);
      this.currentLanguage.set(lang);
    } catch (_error) {
      // Keep existing translations
    }
  }

  async setLanguage(lang: LanguageCode) {
    await this.loadTranslations(lang);
  }

  get(keyPath: string): string {
    const keys = keyPath.split('.');
    let current: TranslationNode = this.translations();

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
