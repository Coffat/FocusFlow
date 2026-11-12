import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { Subject, of, throwError, Observable } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { SignInComponent } from './sign-in.component';
import { AuthService } from '../../../core/services/auth.service';
import { GoogleSsoService } from '../../../core/services/google-sso.service';
import { TranslationService } from '../../../core/services/translation.service';
import { LoginResponse } from '../../../models/auth.interface';

describe('SignInComponent', () => {
  let component: SignInComponent;
  let fixture: ComponentFixture<SignInComponent>;
  let router: Router;

  let credentialSubject: Subject<string>;
  let tokenSubject: Subject<string>;
  let errorSubject: Subject<string>;

  const mockAuthService = {
    signIn: vi.fn(),
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

  beforeEach(async () => {
    credentialSubject = new Subject<string>();
    tokenSubject = new Subject<string>();
    errorSubject = new Subject<string>();

    mockGoogleSsoService.credential$ = credentialSubject.asObservable();
    mockGoogleSsoService.token$ = tokenSubject.asObservable();
    mockGoogleSsoService.error$ = errorSubject.asObservable();

    vi.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [SignInComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: mockAuthService },
        { provide: GoogleSsoService, useValue: mockGoogleSsoService },
        { provide: TranslationService, useValue: mockTranslationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SignInComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fixture.detectChanges();
  });

  it('should create and initialize form defaults', () => {
    expect(component).toBeTruthy();
    expect(component.signInForm.get('email')?.value).toBe('');
    expect(component.signInForm.get('password')?.value).toBe('');
    expect(component.signInForm.get('rememberMe')?.value).toBe(true);
    expect(component.isPasswordVisible()).toBe(false);
    expect(component.isLoading()).toBe(false);
    expect(mockGoogleSsoService.initialize).toHaveBeenCalled();
  });

  describe('Form Validation', () => {
    it('should require email and password', () => {
      const emailControl = component.signInForm.get('email');
      const passwordControl = component.signInForm.get('password');

      expect(emailControl?.valid).toBe(false);
      expect(emailControl?.errors?.['required']).toBeTruthy();
      expect(passwordControl?.valid).toBe(false);
      expect(passwordControl?.errors?.['required']).toBeTruthy();
    });

    it('should validate email format using strictEmailValidator', () => {
      const emailControl = component.signInForm.get('email');

      emailControl?.setValue('invalid-email');
      expect(emailControl?.valid).toBe(false);
      expect(emailControl?.errors?.['email']).toBe(true);

      emailControl?.setValue('valid.learner@university.edu');
      expect(emailControl?.valid).toBe(true);
    });

    it('should be valid when email and password are provided correctly', () => {
      component.signInForm.setValue({
        email: 'alex@university.edu',
        password: 'Password123!',
        rememberMe: true
      });
      expect(component.signInForm.valid).toBe(true);
    });
  });

  describe('Password Visibility', () => {
    it('should toggle password visibility signal', () => {
      expect(component.isPasswordVisible()).toBe(false);
      component.togglePasswordVisibility();
      expect(component.isPasswordVisible()).toBe(true);
      component.togglePasswordVisibility();
      expect(component.isPasswordVisible()).toBe(false);
    });
  });

  describe('Email & Password Sign In Submission', () => {
    it('should not call authService.signIn if form is invalid and should mark controls as touched', () => {
      component.signIn();

      expect(component.signInForm.get('email')?.touched).toBe(true);
      expect(component.signInForm.get('password')?.touched).toBe(true);
      expect(mockAuthService.signIn).not.toHaveBeenCalled();
    });

    it('should call authService.signIn and navigate to /dashboard on success', () => {
      mockAuthService.signIn.mockReturnValue(of(mockLoginResponse));

      component.signInForm.setValue({
        email: 'ALEX@university.edu ',
        password: 'SecretPassword123',
        rememberMe: true
      });

      component.signIn();

      expect(mockAuthService.signIn).toHaveBeenCalledWith({
        email: 'alex@university.edu',
        password: 'SecretPassword123',
        rememberMe: true
      });
      expect(component.isLoading()).toBe(false);
      expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
      expect(component.errorMessage()).toBe('');
    });

    it('should handle signIn error and display error message', () => {
      const errorResponse = new HttpErrorResponse({
        error: { detail: 'Invalid credentials' },
        status: 401,
        statusText: 'Unauthorized'
      });
      mockAuthService.signIn.mockReturnValue(throwError(() => errorResponse));

      component.signInForm.setValue({
        email: 'alex@university.edu',
        password: 'WrongPassword',
        rememberMe: false
      });

      component.signIn();

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toContain('Invalid credentials');
      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('Google SSO Flow', () => {
    it('should trigger googleSsoService.requestGoogleSignIn when signInWithGoogle is called', () => {
      component.signInWithGoogle();

      expect(component.isLoading()).toBe(true);
      expect(component.errorMessage()).toBe('');
      expect(mockGoogleSsoService.requestGoogleSignIn).toHaveBeenCalled();
    });

    it('should handle credential$ event and invoke authService.signInWithGoogle', () => {
      mockAuthService.signInWithGoogle.mockReturnValue(of(mockLoginResponse));

      credentialSubject.next('google-id-token-xyz');

      expect(mockAuthService.signInWithGoogle).toHaveBeenCalledWith({
        idToken: 'google-id-token-xyz',
        accessToken: ''
      });
      expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
    });

    it('should handle token$ event and invoke authService.signInWithGoogle', () => {
      mockAuthService.signInWithGoogle.mockReturnValue(of(mockLoginResponse));

      tokenSubject.next('google-access-token-abc');

      expect(mockAuthService.signInWithGoogle).toHaveBeenCalledWith({
        idToken: '',
        accessToken: 'google-access-token-abc'
      });
      expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
    });

    it('should handle google error$ event and update errorMessage', () => {
      errorSubject.next('popup_closed');

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toBe('auth.signIn.googleAuthFailed');
    });

    it('should handle error when authService.signInWithGoogle fails', () => {
      const errorResponse = new HttpErrorResponse({
        error: { detail: 'Google account not linked' },
        status: 400,
        statusText: 'Bad Request'
      });
      mockAuthService.signInWithGoogle.mockReturnValue(throwError(() => errorResponse));

      credentialSubject.next('bad-token');

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toContain('Google account not linked');
    });
  });
});
