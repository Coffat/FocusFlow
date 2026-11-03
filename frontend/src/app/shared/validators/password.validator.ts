import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_PATTERN = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$/;

export interface PasswordStrengthDetails {
  score: number;
  hasMinLength: boolean;
  hasLetterCase: boolean;
  hasNumber: boolean;
  hasSpecialChar: boolean;
  isValid: boolean;
}

export function checkPasswordMinLength(password: string): boolean {
  return typeof password === 'string' && password.length >= PASSWORD_MIN_LENGTH;
}

export function checkPasswordLetterCase(password: string): boolean {
  return typeof password === 'string' && /[a-z]/.test(password) && /[A-Z]/.test(password);
}

export function checkPasswordNumber(password: string): boolean {
  return typeof password === 'string' && /\d/.test(password);
}

export function checkPasswordSpecialChar(password: string): boolean {
  return typeof password === 'string' && /[^a-zA-Z0-9]/.test(password);
}

export function evaluatePasswordStrength(password: string): PasswordStrengthDetails {
  const safePass = password || '';
  const hasMinLength = checkPasswordMinLength(safePass);
  const hasLetterCase = checkPasswordLetterCase(safePass);
  const hasNumber = checkPasswordNumber(safePass);
  const hasSpecialChar = checkPasswordSpecialChar(safePass);

  let score = 0;
  if (hasMinLength) score++;
  if (hasLetterCase) score++;
  if (hasNumber) score++;
  if (hasSpecialChar) score++;

  const isValid = hasMinLength && hasLetterCase && hasNumber && hasSpecialChar;

  return {
    score,
    hasMinLength,
    hasLetterCase,
    hasNumber,
    hasSpecialChar,
    isValid
  };
}

export function checkPasswordMismatch(password?: string | null, confirmPassword?: string | null): boolean {
  const pass = password || '';
  const confirm = confirmPassword || '';
  if (!confirm) return false;
  return pass !== confirm;
}

/**
 * Angular ValidatorFn enforcing FocusFlow password complexity:
 * At least 8 characters, with lowercase, uppercase, digit, and special symbol.
 * Compatible with backend Pydantic validation schema.
 */
export const passwordComplexityValidator: ValidatorFn = (
  control: AbstractControl
): ValidationErrors | null => {
  const value = control.value;
  if (!value) {
    return null; // Required validator will handle empty values
  }

  const isValid = PASSWORD_PATTERN.test(String(value));
  return isValid ? null : { passwordComplexity: true, pattern: true };
};
