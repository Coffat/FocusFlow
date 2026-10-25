import { Pipe, PipeTransform } from '@angular/core';
import { TranslationService } from '../../core/services/translation.service';

@Pipe({
  name: 'translate',
  pure: false
})
export class TranslatePipe implements PipeTransform {
  translationService: TranslationService;

  constructor(translationService: TranslationService) {
    this.translationService = translationService;
  }

  transform(key: string): string {
    return this.translationService.get(key);
  }
}
