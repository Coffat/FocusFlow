import { FormControl } from '@angular/forms';
import {
  checkPasswordMinLength,
  checkPasswordLetterCase,
  checkPasswordNumber,
  checkPasswordSpecialChar,
  evaluatePasswordStrength,
  checkPasswordMismatch,
  passwordComplexityValidator
} from './password.validator';

describe('PasswordValidator', () => {
  describe('checkPasswordMinLength', () => {
    it('should return false for passwords shorter than 8 characters', () => {
      expect(checkPasswordMinLength('Ab1!')).toBe(false);
      expect(checkPasswordMinLength('1234567')).toBe(false);
    });

    it('should return true for passwords with 8 or more characters', () => {
      expect(checkPasswordMinLength('12345678')).toBe(true);
      expect(checkPasswordMinLength('SecurePass123!')).toBe(true);
    });
  });

  describe('checkPasswordLetterCase', () => {
    it('should return false if only lowercase or only uppercase', () => {
      expect(checkPasswordLetterCase('abcdefgh')).toBe(false);
      expect(checkPasswordLetterCase('ABCDEFGH')).toBe(false);
    });

    it('should return true if containing both lower and upper case letters', () => {
      expect(checkPasswordLetterCase('Abcdefgh')).toBe(true);
      expect(checkPasswordLetterCase('passWORD')).toBe(true);
    });
  });

  describe('checkPasswordNumber', () => {
    it('should return false if no digits are present', () => {
      expect(checkPasswordNumber('Password!')).toBe(false);
    });

    it('should return true if at least one digit is present', () => {
      expect(checkPasswordNumber('Password1')).toBe(true);
      expect(checkPasswordNumber('12345678')).toBe(true);
    });
  });

  describe('checkPasswordSpecialChar', () => {
    it('should return false for alphanumeric-only strings', () => {
      expect(checkPasswordSpecialChar('Password123')).toBe(false);
    });

    it('should return true for strings with special characters', () => {
      expect(checkPasswordSpecialChar('Password123!')).toBe(true);
      expect(checkPasswordSpecialChar('pass@word')).toBe(true);
      expect(checkPasswordSpecialChar('pass#word$')).toBe(true);
    });
  });

  describe('evaluatePasswordStrength', () => {
    it('should calculate score 0 for empty or invalid password', () => {
      const result = evaluatePasswordStrength('');
      expect(result.score).toBe(0);
      expect(result.isValid).toBe(false);
    });

    it('should calculate full score 4 and mark isValid=true for strong password', () => {
      const result = evaluatePasswordStrength('FocusFlow2026!');
      expect(result.score).toBe(4);
      expect(result.hasMinLength).toBe(true);
      expect(result.hasLetterCase).toBe(true);
      expect(result.hasNumber).toBe(true);
      expect(result.hasSpecialChar).toBe(true);
      expect(result.isValid).toBe(true);
    });
  });

  describe('checkPasswordMismatch', () => {
    it('should return false when confirmPassword is empty', () => {
      expect(checkPasswordMismatch('Password123!', '')).toBe(false);
    });

    it('should return true when passwords do not match', () => {
      expect(checkPasswordMismatch('Password123!', 'Different123!')).toBe(true);
    });

    it('should return false when passwords match', () => {
      expect(checkPasswordMismatch('Password123!', 'Password123!')).toBe(false);
    });
  });

  describe('passwordComplexityValidator', () => {
    it('should return null for empty control value (letting required validator handle)', () => {
      const control = new FormControl('');
      expect(passwordComplexityValidator(control)).toBeNull();
    });

    it('should return complexity error object when password does not meet criteria', () => {
      const control = new FormControl('weakpass');
      const errors = passwordComplexityValidator(control);
      expect(errors).toEqual({ passwordComplexity: true, pattern: true });
    });

    it('should return null when password satisfies all complexity rules', () => {
      const control = new FormControl('SecurePass123!');
      expect(passwordComplexityValidator(control)).toBeNull();
    });
  });
});
