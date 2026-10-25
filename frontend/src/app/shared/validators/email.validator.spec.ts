import { FormControl } from '@angular/forms';
import {
  validateEmail,
  strictEmailValidator,
  createStrictEmailValidator
} from './email.validator';

describe('EmailValidator', () => {
  describe('validateEmail pure function', () => {
    it('should invalidate null, undefined or empty string', () => {
      expect(validateEmail(null).valid).toBe(false);
      expect(validateEmail(undefined).valid).toBe(false);
      expect(validateEmail('').valid).toBe(false);
    });

    it('should invalidate email exceeding 254 characters', () => {
      const longEmail = 'a'.repeat(250) + '@domain.com';
      const result = validateEmail(longEmail);
      expect(result.valid).toBe(false);
      expect(result.errorKey).toBe('validation.emailMaxLength');
    });

    it('should invalidate email without @ or with multiple @', () => {
      expect(validateEmail('userdomain.com').valid).toBe(false);
      expect(validateEmail('user@@domain.com').valid).toBe(false);
      expect(validateEmail('user@domain@sub.com').valid).toBe(false);
    });

    it('should invalidate local part shorter than 2 chars or longer than 64 chars', () => {
      expect(validateEmail('a@domain.com').valid).toBe(false);
      expect(validateEmail('x'.repeat(65) + '@domain.com').valid).toBe(false);
    });

    it('should invalidate local part with consecutive special characters or ending with special character', () => {
      expect(validateEmail('john..doe@domain.com').valid).toBe(false);
      expect(validateEmail('john.@domain.com').valid).toBe(false);
      expect(validateEmail('john-@domain.com').valid).toBe(false);
    });

    it('should invalidate domain with consecutive dots or invalid hyphens', () => {
      expect(validateEmail('user@domain..com').valid).toBe(false);
      expect(validateEmail('user@-domain.com').valid).toBe(false);
      expect(validateEmail('user@domain-.com').valid).toBe(false);
    });

    it('should invalidate unrecognized TLD extensions', () => {
      const result = validateEmail('user@domain.unrecognizedtld');
      expect(result.valid).toBe(false);
      expect(result.errorKey).toBe('validation.emailInvalidTld');
    });

    it('should validate and normalize valid emails across standard & academic domains', () => {
      const validCases = [
        'student@hust.edu.vn',
        'learner@focusflow.vn',
        'elena.smith@university.edu',
        'john_doe+test@gmail.com',
        'researcher@oxford.ac.uk',
        'developer@startup.io',
        'ai_enthusiast@platform.ai'
      ];

      for (const email of validCases) {
        const result = validateEmail(email);
        expect(result.valid).toBe(true);
        expect(result.cleanEmail).toBe(email.toLowerCase().trim());
      }
    });
  });

  describe('strictEmailValidator for Angular FormControl', () => {
    it('should return null for empty value', () => {
      const control = new FormControl('');
      expect(strictEmailValidator(control)).toBeNull();
    });

    it('should return error object for invalid email', () => {
      const control = new FormControl('invalid-email-string');
      const error = strictEmailValidator(control);
      expect(error).toBeTruthy();
      expect(error?.['email']).toBe(true);
      expect(error?.['invalidEmail']).toBe(true);
      expect(error?.['message']).toBeDefined();
    });

    it('should return null for valid email', () => {
      const control = new FormControl('learner@focusflow.vn');
      expect(strictEmailValidator(control)).toBeNull();
    });

    it('should support factory createStrictEmailValidator', () => {
      const validator = createStrictEmailValidator();
      const validControl = new FormControl('valid@domain.com');
      const invalidControl = new FormControl('invalid@');
      expect(validator(validControl)).toBeNull();
      expect(validator(invalidControl)).toBeTruthy();
    });
  });
});
