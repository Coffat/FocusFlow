import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, catchError, map, of, tap } from 'rxjs';
import {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  RequestRegisterOtpRequest,
  ResendRegisterOtpRequest,
  VerifyRegisterOtpRequest,
  RequestPasswordResetOtpRequest,
  VerifyPasswordResetOtpRequest,
  VerifyPasswordResetOtpResponse,
  ConfirmPasswordResetRequest,
  MessageResponse,
  UserProfile,
  BackendAuthResponse,
  BackendUserPayload,
  GoogleAuthRequest
} from '../../models/auth.interface';
import { AUTH_ENDPOINTS } from '../../constant/api.constant';

export type User = UserProfile;

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  // Angular Signals state with strict encapsulation
  private readonly _currentUser = signal<User | null>(null);
  readonly currentUser = this._currentUser.asReadonly();
  readonly isAuthenticated = computed(() => this._currentUser() !== null);
  private readonly _isLoading = signal<boolean>(false);
  readonly isLoading = this._isLoading.asReadonly();

  private sessionCheck$: Observable<boolean> | null = null;

  constructor() {
    this.initAuth();
  }

  setUser(user: UserProfile, accessToken?: string): void {
    if (accessToken) {
      // Retain token in localStorage as optional fallback for dev inspection,
      // but primary authentication relies on HttpOnly cookies (ADR-008)
      localStorage.setItem('access_token', accessToken);
    }
    this._currentUser.set(user);
  }

  clearUser(): void {
    this.clearSession();
  }

  private clearSession(): void {
    localStorage.removeItem('access_token');
    this._currentUser.set(null);
  }

  checkSession(): Observable<boolean> {
    if (this._currentUser() !== null) {
      return of(true);
    }
    if (this.sessionCheck$) {
      return this.sessionCheck$;
    }

    this.sessionCheck$ = this.http.get<BackendUserPayload>(AUTH_ENDPOINTS.ME, { withCredentials: true }).pipe(
      map((user: BackendUserPayload) => {
        const mappedUser: UserProfile = {
          id: user.id,
          email: user.email,
          fullName: user.full_name,
          role: user.role,
          tier: user.tier,
          createdAt: user.created_at
        };
        this.setUser(mappedUser);
        this.sessionCheck$ = null;
        return true;
      }),
      catchError(() => {
        this.clearSession();
        this.sessionCheck$ = null;
        return of(false);
      })
    );

    return this.sessionCheck$;
  }

  initAuth(): void {
    this.checkSession().subscribe();
  }

  login(credentials: { email: string; password: string }): Observable<User> {
    this._isLoading.set(true);
    this.clearSession();
    const payload = {
      email: credentials.email,
      password: credentials.password
    };

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.LOGIN, payload, { withCredentials: true }).pipe(
      tap({
        next: (response: BackendAuthResponse) => {
          const user: User = {
            id: response.user.id,
            email: response.user.email,
            fullName: response.user.full_name,
            role: response.user.role,
            tier: response.user.tier,
            createdAt: response.user.created_at
          };
          this.setUser(user, response.access_token);
          this._isLoading.set(false);
        },
        error: () => {
          this._isLoading.set(false);
        }
      }),
      map((response: BackendAuthResponse): User => ({
        id: response.user.id,
        email: response.user.email,
        fullName: response.user.full_name,
        role: response.user.role,
        tier: response.user.tier,
        createdAt: response.user.created_at
      }))
    );
  }

  signIn(credentials: LoginRequest): Observable<LoginResponse> {
    this._isLoading.set(true);
    const payload = {
      email: credentials.email,
      password: credentials.password,
      remember_me: credentials.rememberMe
    };

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.LOGIN, payload, { withCredentials: true }).pipe(
      map((response: BackendAuthResponse): LoginResponse => {
        const mappedUser: UserProfile = {
          id: response.user.id,
          email: response.user.email,
          fullName: response.user.full_name,
          role: response.user.role,
          tier: response.user.tier,
          createdAt: response.user.created_at
        };
        return {
          accessToken: response.access_token,
          tokenType: response.token_type,
          expiresIn: response.expires_in,
          user: mappedUser
        };
      }),
      tap({
        next: (response: LoginResponse) => {
          this.setUser(response.user, response.accessToken);
          this._isLoading.set(false);
        },
        error: (_err: Error) => {
          this._isLoading.set(false);
        }
      })
    );
  }

  signUp(data: RegisterRequest): Observable<RegisterResponse> {
    this._isLoading.set(true);
    const payload = {
      full_name: data.fullName,
      email: data.email,
      password: data.password
    };

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.REGISTER, payload, { withCredentials: true }).pipe(
      map((response: BackendAuthResponse): RegisterResponse => {
        const mappedUser: UserProfile = {
          id: response.user.id,
          email: response.user.email,
          fullName: response.user.full_name,
          role: response.user.role,
          tier: response.user.tier,
          createdAt: response.user.created_at
        };
        return {
          message: 'Account registered successfully',
          accessToken: response.access_token,
          user: mappedUser
        };
      }),
      tap({
        next: (response: RegisterResponse) => {
          this.setUser(response.user, response.accessToken);
          this._isLoading.set(false);
        },
        error: () => {
          this._isLoading.set(false);
        }
      })
    );
  }

  requestRegisterOtp(data: RequestRegisterOtpRequest): Observable<MessageResponse> {
    const payload = {
      full_name: data.fullName,
      email: data.email,
      password: data.password
    };
    return this.http.post<MessageResponse>(AUTH_ENDPOINTS.REGISTER_REQUEST_OTP, payload);
  }

  resendRegisterOtp(data: ResendRegisterOtpRequest): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(AUTH_ENDPOINTS.REGISTER_RESEND_OTP, {
      email: data.email
    });
  }

  verifyRegisterOtp(data: VerifyRegisterOtpRequest): Observable<LoginResponse> {
    const payload = {
      email: data.email,
      otp_code: data.otpCode
    };

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.REGISTER_VERIFY_OTP, payload, { withCredentials: true }).pipe(
      map((response: BackendAuthResponse): LoginResponse => {
        const mappedUser: UserProfile = {
          id: response.user.id,
          email: response.user.email,
          fullName: response.user.full_name,
          role: response.user.role,
          tier: response.user.tier,
          createdAt: response.user.created_at
        };
        return {
          accessToken: response.access_token,
          tokenType: response.token_type,
          expiresIn: response.expires_in,
          user: mappedUser
        };
      }),
      tap({
        next: (response: LoginResponse) => {
          this.setUser(response.user, response.accessToken);
        }
      })
    );
  }

  requestPasswordResetOtp(data: RequestPasswordResetOtpRequest): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(AUTH_ENDPOINTS.PASSWORD_RESET_REQUEST_OTP, {
      email: data.email
    });
  }

  verifyPasswordResetOtp(data: VerifyPasswordResetOtpRequest): Observable<VerifyPasswordResetOtpResponse> {
    return this.http.post<VerifyPasswordResetOtpResponse>(AUTH_ENDPOINTS.PASSWORD_RESET_VERIFY_OTP, {
      email: data.email,
      otp_code: data.otpCode
    });
  }

  confirmPasswordReset(data: ConfirmPasswordResetRequest): Observable<MessageResponse> {
    const payload: Record<string, string> = {
      email: data.email,
      new_password: data.newPassword
    };
    if (data.resetToken && data.resetToken.length > 0) {
      payload['reset_token'] = data.resetToken;
    }
    if (data.otpCode && data.otpCode.length > 0) {
      payload['otp_code'] = data.otpCode;
    }
    return this.http.post<MessageResponse>(AUTH_ENDPOINTS.PASSWORD_RESET_CONFIRM, payload);
  }

  signInWithGoogle(data: GoogleAuthRequest): Observable<LoginResponse> {
    const payload: Record<string, string> = {};
    if (data.idToken.length > 0) {
      payload['id_token'] = data.idToken;
    }
    if (data.accessToken.length > 0) {
      payload['access_token'] = data.accessToken;
    }

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.GOOGLE, payload, { withCredentials: true }).pipe(
      map((response: BackendAuthResponse): LoginResponse => {
        const mappedUser: UserProfile = {
          id: response.user.id,
          email: response.user.email,
          fullName: response.user.full_name,
          role: response.user.role,
          tier: response.user.tier,
          createdAt: response.user.created_at
        };
        return {
          accessToken: response.access_token,
          tokenType: response.token_type,
          expiresIn: response.expires_in,
          user: mappedUser
        };
      }),
      tap({
        next: (response: LoginResponse) => {
          this.setUser(response.user, response.accessToken);
        }
      })
    );
  }

  refreshToken(token?: string): Observable<LoginResponse> {
    const payload = token && token.length > 0 ? { refresh_token: token } : {};

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.REFRESH_TOKEN, payload, { withCredentials: true }).pipe(
      map((response: BackendAuthResponse): LoginResponse => {
        const mappedUser: UserProfile = {
          id: response.user.id,
          email: response.user.email,
          fullName: response.user.full_name,
          role: response.user.role,
          tier: response.user.tier,
          createdAt: response.user.created_at
        };
        return {
          accessToken: response.access_token,
          tokenType: response.token_type,
          expiresIn: response.expires_in,
          user: mappedUser
        };
      }),
      tap({
        next: (response: LoginResponse) => {
          this.setUser(response.user, response.accessToken);
        },
        error: (_err: Error) => {
          this.signOut();
        }
      })
    );
  }

  signOut(): void {
    localStorage.removeItem('access_token');
    this.http.post(AUTH_ENDPOINTS.LOGOUT, {}, { withCredentials: true }).pipe(
      catchError(() => of({}))
    ).subscribe();
    this.clearSession();
  }

  logout(): void {
    this.signOut();
  }

  handleSessionExpired(): void {
    this.clearSession();
    this.router.navigate(['/sign-in'], { queryParams: { expired: '1' } });
  }
}
