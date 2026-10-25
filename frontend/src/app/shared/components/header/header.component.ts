import { Component, OnInit, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { TranslationService, LanguageCode } from '../../../core/services/translation.service';

@Component({
  selector: 'app-header',
  imports: [RouterLink, ButtonModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent implements OnInit {
  translationService: TranslationService;

  @Input() showBrand = false;

  constructor(translationService: TranslationService) {
    this.translationService = translationService;
  }

  ngOnInit() {}

  switchLanguage(lang: LanguageCode) {
    this.translationService.setLanguage(lang);
  }
}
