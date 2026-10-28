import { TranslatePipe } from './translate.pipe';
import { TranslationService } from '../../core/services/translation.service';

describe('TranslatePipe', () => {
  let mockTranslationService: { get: ReturnType<typeof vi.fn> };
  let pipe: TranslatePipe;

  beforeEach(() => {
    mockTranslationService = {
      get: vi.fn((key: string) => {
        if (key === 'auth.signIn.title') return 'Đăng nhập vào FocusFlow';
        return key;
      })
    };
    pipe = new TranslatePipe(mockTranslationService as unknown as TranslationService);
  });

  it('should transform translation key into translated string', () => {
    const result = pipe.transform('auth.signIn.title');
    expect(result).toBe('Đăng nhập vào FocusFlow');
    expect(mockTranslationService.get).toHaveBeenCalledWith('auth.signIn.title');
  });

  it('should return original key when key does not exist', () => {
    const result = pipe.transform('nonexistent.key');
    expect(result).toBe('nonexistent.key');
    expect(mockTranslationService.get).toHaveBeenCalledWith('nonexistent.key');
  });
});
