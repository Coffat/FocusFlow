import { Component, ChangeDetectionStrategy, input, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { TranslationService, LanguageCode } from '../../../core/services/translation.service';

@Component({
  selector: 'app-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ButtonModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {
  readonly translationService = inject(TranslationService);
  readonly showBrand = input<boolean>(false);

  switchLanguage(lang: LanguageCode) {
    this.translationService.setLanguage(lang);
  }
}
