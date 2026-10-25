import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export interface ValidationTranslator {
  get?(key: string): string;
  instant?(key: string, params?: Record<string, string | number>): string;
}

export interface EmailValidationResult {
  valid: boolean;
  message?: string;
  cleanEmail?: string;
  errorKey?: string;
}

function resolveMessage(
  translator: ValidationTranslator | null | undefined,
  key: string,
  fallback: string,
  params?: Record<string, string | number>
): string {
  let translated: string | undefined;

  if (translator) {
    if (typeof translator.get === 'function') {
      const val = translator.get(key);
      if (val && val !== key) {
        translated = val;
      }
    } else if (typeof translator.instant === 'function') {
      const val = translator.instant(key, params);
      if (val && val !== key) {
        translated = val;
      }
    }
  }

  let out = translated || fallback;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      out = out.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    }
  }
  return out;
}

export const ALLOWED_TLDS = new Set([
  // Generic & Traditional TLDs
  'com', 'net', 'org', 'edu', 'gov', 'mil', 'info', 'biz', 'int', 'pro', 'name',
  // Technology & Modern gTLDs
  'io', 'ai', 'dev', 'app', 'tech', 'store', 'online', 'site', 'xyz', 'me', 'co', 'cloud', 'digital', 'space', 'club', 'design',
  // Top ccTLDs (Vietnam, UK, US, EU, Asia-Pacific)
  'vn', 'us', 'uk', 'ca', 'au', 'de', 'fr', 'jp', 'kr', 'sg', 'in', 'ch', 'nl', 'se', 'no', 'fi', 'nz', 'ru', 'cn', 'tw', 'hk', 'eu'
]);

export function validateEmail(
  email: string | null | undefined,
  translator?: ValidationTranslator
): EmailValidationResult {
  if (!email || typeof email !== 'string') {
    return {
      valid: false,
      errorKey: 'validation.emailRequired',
      message: resolveMessage(translator, 'validation.emailRequired', 'Email address is required.')
    };
  }

  const cleanEmail = email.trim().toLowerCase();
  if (cleanEmail.length > 254) {
    return {
      valid: false,
      errorKey: 'validation.emailMaxLength',
      message: resolveMessage(translator, 'validation.emailMaxLength', 'Email address cannot exceed 254 characters.')
    };
  }

  const atIndex = cleanEmail.indexOf('@');
  if (atIndex === -1 || cleanEmail.lastIndexOf('@') !== atIndex) {
    return {
      valid: false,
      errorKey: 'validation.emailOneAt',
      message: resolveMessage(translator, 'validation.emailOneAt', 'Email must contain exactly one @ symbol.')
    };
  }

  const localPart = cleanEmail.substring(0, atIndex);
  const domainPart = cleanEmail.substring(atIndex + 1);

  if (localPart.length < 2 || localPart.length > 64) {
    return {
      valid: false,
      errorKey: 'validation.emailUsernameLength',
      message: resolveMessage(translator, 'validation.emailUsernameLength', 'Email username must be between 2 and 64 characters.')
    };
  }

  if (!/^[a-zA-Z0-9]/.test(localPart)) {
    return {
      valid: false,
      errorKey: 'validation.emailUsernameStartAlphanumeric',
      message: resolveMessage(
        translator,
        'validation.emailUsernameStartAlphanumeric',
        'Email username must start with a letter or number.'
      )
    };
  }

  if (!/^[a-zA-Z0-9._%+-]+$/.test(localPart)) {
    return {
      valid: false,
      errorKey: 'validation.emailUsernameInvalidChars',
      message: resolveMessage(translator, 'validation.emailUsernameInvalidChars', 'Email username contains invalid characters.')
    };
  }

  if (/[._%+\-]$/.test(localPart)) {
    return {
      valid: false,
      errorKey: 'validation.emailUsernameNoEndSpecial',
      message: resolveMessage(translator, 'validation.emailUsernameNoEndSpecial', 'The part before @ cannot end with a special character.')
    };
  }

  if (/[._%+\-]{2,}/.test(localPart)) {
    return {
      valid: false,
      errorKey: 'validation.emailConsecutiveSpecial',
      message: resolveMessage(translator, 'validation.emailConsecutiveSpecial', 'Email cannot contain consecutive special characters.')
    };
  }

  if (!domainPart || domainPart.length < 4 || domainPart.length > 253) {
    return {
      valid: false,
      errorKey: 'validation.emailDomainLength',
      message: resolveMessage(translator, 'validation.emailDomainLength', 'Invalid email domain length.')
    };
  }

  if (domainPart.startsWith('.') || domainPart.endsWith('.') || domainPart.startsWith('-') || domainPart.endsWith('-')) {
    return {
      valid: false,
      errorKey: 'validation.emailDomainHyphenDot',
      message: resolveMessage(translator, 'validation.emailDomainHyphenDot', 'Domain cannot start or end with a dot or hyphen.')
    };
  }

  if (/\.\./.test(domainPart)) {
    return {
      valid: false,
      errorKey: 'validation.emailDomainConsecutiveDots',
      message: resolveMessage(translator, 'validation.emailDomainConsecutiveDots', 'Domain cannot contain consecutive dots.')
    };
  }

  const labels = domainPart.split('.');
  if (labels.length < 2) {
    return {
      valid: false,
      errorKey: 'validation.emailDomainFormat',
      message: resolveMessage(translator, 'validation.emailDomainFormat', 'Invalid email domain format (e.g. name@example.com).')
    };
  }

  for (const label of labels) {
    if (label.length < 2 || label.length > 63) {
      return {
        valid: false,
        errorKey: 'validation.emailDomainSegmentLength',
        message: resolveMessage(translator, 'validation.emailDomainSegmentLength', 'Each domain segment must be between 2 and 63 characters (e.g. name@example.com).')
      };
    }
    if (!/^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$/.test(label)) {
      return {
        valid: false,
        errorKey: 'validation.emailDomainFormatting',
        message: resolveMessage(translator, 'validation.emailDomainFormatting', 'Domain contains invalid characters or formatting.')
      };
    }
  }

  const tld = labels[labels.length - 1];
  if (!/^[a-zA-Z]{2,24}$/.test(tld) || !ALLOWED_TLDS.has(tld)) {
    return {
      valid: false,
      errorKey: 'validation.emailInvalidTld',
      message: resolveMessage(
        translator,
        'validation.emailInvalidTld',
        `Invalid domain extension (.${tld}). Please use a valid domain (e.g. .com, .vn, .net, .org, .edu).`,
        { tld }
      )
    };
  }

  return { valid: true, cleanEmail };
}

/**
 * Angular ValidatorFn enforcing strict, RFC-compliant email formatting.
 * Compatible directly with FormBuilder and ReactiveFormsModule.
 */
export function strictEmailValidator(
  control: AbstractControl,
  translator?: ValidationTranslator
): ValidationErrors | null {
  const value = control.value;
  if (!value) return null; // Let Validators.required handle empty values
  const result = validateEmail(value, translator);
  return result.valid
    ? null
    : {
        email: true,
        invalidEmail: true,
        message: result.message
      };
}

/**
 * Validator factory enabling injection of FocusFlow's TranslationService.
 */
export function createStrictEmailValidator(translator?: ValidationTranslator): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    return strictEmailValidator(control, translator);
  };
}
