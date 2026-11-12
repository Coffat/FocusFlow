import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { Subject, of, throwError, Observable } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { SignUpComponent } from './sign-up.component';
import { AuthService } from '../../../core/services/auth.service';
import { GoogleSsoService } from '../../../core/services/google-sso.service';
import { TranslationService } from '../../../core/services/translation.service';
import { MessageResponse, LoginResponse } from '../../../models/auth.interface';

describe('SignUpComponent', () => {
  let component: SignUpComponent;
  let fixture: ComponentFixture<SignUpComponent>;
  let router: Router;

  let credentialSubject: Subject<string>;
  let tokenSubject: Subject<string>;
  let errorSubject: Subject<string>;

  const mockAuthService = {
    requestRegisterOtp: vi.fn(),
    signInWithGoogle: vi.fn()
  };

  const mockGoogleSsoService: {
    credential$: Observable<string>;
    token$: Observable<string>;
    error$: Observable<string>;
    initialize: ReturnType<typeof vi.fn>;
    requestGoogleSignIn: ReturnType<typeof vi.fn>;
  } = {
    credential$: of(''),
    token$: of(''),
    error$: of(''),
    initialize: vi.fn(),
    requestGoogleSignIn: vi.fn()
  };

  const mockTranslationService = {
    get: vi.fn((key: string) => key),
    setLanguage: vi.fn(),
    currentLanguage: () => 'vi'
  };

  const mockLoginResponse: LoginResponse = {
    accessToken: 'jwt-token-xyz',
    tokenType: 'Bearer',
    expiresIn: 3600,
    user: {
      id: 'usr-123',
      email: 'alex@example.com',
      fullName: 'Alex Johnson',
      role: 'learner',
      tier: 'free',
      createdAt: '2026-11-01T00:00:00Z'
    }
  };

  const mockMessageResponse: MessageResponse = {
    message: 'OTP dispatched successfully'
  };

  beforeEach(async () => {
    credentialSubject = new Subject<string>();
    tokenSubject = new Subject<string>();
    errorSubject = new Subject<string>();

    mockGoogleSsoService.credential$ = credentialSubject.asObservable();
    mockGoogleSsoService.token$ = tokenSubject.asObservable();
    mockGoogleSsoService.error$ = errorSubject.asObservable();

    sessionStorage.clear();
    vi.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [SignUpComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: mockAuthService },
        { provide: GoogleSsoService, useValue: mockGoogleSsoService },
        { provide: TranslationService, useValue: mockTranslationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SignUpComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fixture.detectChanges();
  });

  it('should create and initialize form defaults', () => {
    expect(component).toBeTruthy();
    expect(component.signUpForm.get('fullName')?.value).toBe('');
    expect(component.signUpForm.get('email')?.value).toBe('');
    expect(component.signUpForm.get('password')?.value).toBe('');
    expect(component.signUpForm.get('confirmPassword')?.value).toBe('');
    expect(component.signUpForm.get('termsAccepted')?.value).toBe(true);
    expect(component.isPasswordVisible()).toBe(false);
    expect(component.isConfirmPasswordVisible()).toBe(false);
    expect(component.isLoading()).toBe(false);
    expect(mockGoogleSsoService.initialize).toHaveBeenCalled();
  });

  describe('Form Validations', () => {
    it('should validate required fields', () => {
      expect(component.signUpForm.valid).toBe(false);
      expect(component.signUpForm.get('fullName')?.errors?.['required']).toBeTruthy();
      expect(component.signUpForm.get('email')?.errors?.['required']).toBeTruthy();
      expect(component.signUpForm.get('password')?.errors?.['required']).toBeTruthy();
      expect(component.signUpForm.get('confirmPassword')?.errors?.['required']).toBeTruthy();
    });

    it('should validate strict email format', () => {
      const emailCtrl = component.signUpForm.get('email');
      emailCtrl?.setValue('not-an-email');
      expect(emailCtrl?.valid).toBe(false);
      expect(emailCtrl?.errors?.['email']).toBe(true);

      emailCtrl?.setValue('learner@campus.edu.vn');
      expect(emailCtrl?.valid).toBe(true);
    });

    it('should validate password complexity and update entropy', () => {
      const passCtrl = component.signUpForm.get('password');
      passCtrl?.setValue('weak');
      expect(passCtrl?.valid).toBe(false);
      expect(component.passwordStrength()).toBeLessThanOrEqual(1);
      expect(component.strengthLabelKey()).toBe('auth.signUp.weakSecurity');

      passCtrl?.setValue('P@ssword123!');
      expect(passCtrl?.valid).toBe(true);
      expect(component.passwordStrength()).toBeGreaterThanOrEqual(3);
      expect(component.hasMinLength).toBe(true);
      expect(component.hasLetterCase).toBe(true);
      expect(component.hasNumber).toBe(true);
      expect(component.hasSpecialChar).toBe(true);
      expect(component.isPasswordValid).toBe(true);
    });

    it('should detect password mismatch', () => {
      component.signUpForm.patchValue({
        password: 'P@ssword123!',
        confirmPassword: 'DifferentPassword123!'
      });
      expect(component.isPasswordMismatch).toBe(true);

      component.signUpForm.patchValue({
        confirmPassword: 'P@ssword123!'
      });
      expect(component.isPasswordMismatch).toBe(false);
    });

    it('should require termsAccepted to be true', () => {
      const termsCtrl = component.signUpForm.get('termsAccepted');
      termsCtrl?.setValue(false);
      expect(termsCtrl?.valid).toBe(false);
      expect(termsCtrl?.errors?.['required']).toBeTruthy();
    });
  });

  describe('Password Visibility Toggles', () => {
    it('should toggle password and confirm password visibility', () => {
      expect(component.isPasswordVisible()).toBe(false);
      component.togglePasswordVisibility();
      expect(component.isPasswordVisible()).toBe(true);

      expect(component.isConfirmPasswordVisible()).toBe(false);
      component.toggleConfirmPasswordVisibility();
      expect(component.isConfirmPasswordVisible()).toBe(true);
    });
  });

  describe('Request OTP Registration Flow', () => {
    it('should not proceed if form is invalid', () => {
      component.requestOtp();
      expect(component.signUpForm.touched).toBe(true);
      expect(mockAuthService.requestRegisterOtp).not.toHaveBeenCalled();
    });

    it('should show error and not proceed if passwords mismatch', () => {
      component.signUpForm.setValue({
        fullName: 'Elena Rostova',
        email: 'elena@institute.ac.uk',
        password: 'P@ssword123!',
        confirmPassword: 'P@ssword456!',
        termsAccepted: true
      });

      component.requestOtp();
      expect(component.errorMessage()).toBe('auth.signUp.passwordMismatchError');
      expect(mockAuthService.requestRegisterOtp).not.toHaveBeenCalled();
    });

    it('should submit registration and navigate to verify-otp with query params on success', () => {
      mockAuthService.requestRegisterOtp.mockReturnValue(of(mockMessageResponse));

      component.signUpForm.setValue({
        fullName: 'Elena Rostova',
        email: 'elena@institute.ac.uk',
        password: 'P@ssword123!',
        confirmPassword: 'P@ssword123!',
        termsAccepted: true
      });

      component.requestOtp();

      expect(mockAuthService.requestRegisterOtp).toHaveBeenCalledWith({
        fullName: 'Elena Rostova',
        email: 'elena@institute.ac.uk',
        password: 'P@ssword123!'
      });
      expect(sessionStorage.getItem('pending_register_email')).toBe('elena@institute.ac.uk');
      expect(router.navigate).toHaveBeenCalledWith(['/verify-otp'], {
        queryParams: { email: 'elena@institute.ac.uk', flow: 'register' }
      });
      expect(component.isLoading()).toBe(false);
    });

    it('should handle registration error and display error message', () => {
      const errorResponse = new HttpErrorResponse({
        error: { detail: 'Email is already registered' },
        status: 409,
        statusText: 'Conflict'
      });
      mockAuthService.requestRegisterOtp.mockReturnValue(throwError(() => errorResponse));

      component.signUpForm.setValue({
        fullName: 'Elena Rostova',
        email: 'elena@institute.ac.uk',
        password: 'P@ssword123!',
        confirmPassword: 'P@ssword123!',
        termsAccepted: true
      });

      component.requestOtp();

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toContain('Email is already registered');
      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('Google SSO Flow', () => {
    it('should trigger Google SSO request on signInWithGoogle', () => {
      component.signInWithGoogle();
      expect(component.isLoading()).toBe(true);
      expect(mockGoogleSsoService.requestGoogleSignIn).toHaveBeenCalled();
    });

    it('should handle Google SSO credential and navigate to dashboard', () => {
      mockAuthService.signInWithGoogle.mockReturnValue(of(mockLoginResponse));
      credentialSubject.next('google-credential-abc');

      expect(mockAuthService.signInWithGoogle).toHaveBeenCalledWith({
        idToken: 'google-credential-abc',
        accessToken: ''
      });
      expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
    });
  });
});
