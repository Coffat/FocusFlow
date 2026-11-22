import { ApplicationConfig, provideZonelessChangeDetection, provideAppInitializer, inject } from '@angular/core';
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from '@angular/router';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { providePrimeNG } from 'primeng/config';
import { ConfirmationService, MessageService } from 'primeng/api';
import Aura from '@primeng/themes/aura';

import { routes } from './app.routes';
import { ColorService } from './core/services/color.service';
import { TranslationService } from './core/services/translation.service';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { timeoutInterceptor } from './core/interceptors/timeout.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZonelessChangeDetection(),
    provideRouter(
      routes,
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'top', anchorScrolling: 'enabled' })
    ),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor, timeoutInterceptor])),
    provideAnimationsAsync(),
    ConfirmationService,
    MessageService,
    providePrimeNG({
      theme: {
        preset: Aura,
        options: {
          darkModeSelector: '.dark-mode'
        }
      }
    }),
    provideAppInitializer(async () => {
      const colorService = inject(ColorService);
      const translationService = inject(TranslationService);
      await Promise.all([
        colorService.loadColors(),
        translationService.loadTranslations('vi')
      ]);
    })
  ]
};
