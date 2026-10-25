import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, map, tap, catchError, of } from 'rxjs';
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

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  http: HttpClient;

  currentUserSubject = new BehaviorSubject<UserProfile>({
    id: '',
    email: '',
    fullName: '',
    role: '',
    tier: '',
    createdAt: ''
  });
  currentUser$ = this.currentUserSubject.asObservable();

  isAuthenticatedSubject = new BehaviorSubject<boolean>(false);
  isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

  constructor(http: HttpClient) {
    this.http = http;
    this.initAuth();
  }

  initAuth() {
    const token = localStorage.getItem('access_token') || '';
    if (token.length > 0) {
      this.http.get<BackendUserPayload>(AUTH_ENDPOINTS.ME).subscribe({
        next: (user: BackendUserPayload) => {
          const mappedUser: UserProfile = {
            id: user.id,
            email: user.email,
            fullName: user.full_name,
            role: user.role,
            tier: user.tier,
            createdAt: user.created_at
          };
          this.currentUserSubject.next(mappedUser);
          this.isAuthenticatedSubject.next(true);
        },
        error: (_err: Error) => {
          localStorage.removeItem('access_token');
          this.isAuthenticatedSubject.next(false);
        },
        complete: () => {}
      });
    }
  }

  signIn(credentials: LoginRequest): Observable<LoginResponse> {
    const payload = {
      email: credentials.email,
      password: credentials.password,
      remember_me: credentials.rememberMe
    };

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.LOGIN, payload).pipe(
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
          localStorage.setItem('access_token', response.accessToken);
          this.currentUserSubject.next(response.user);
          this.isAuthenticatedSubject.next(true);
        },
        error: (_err: Error) => {
          this.isAuthenticatedSubject.next(false);
        }
      })
    );
  }

  signUp(data: RegisterRequest): Observable<RegisterResponse> {
    const payload = {
      full_name: data.fullName,
      email: data.email,
      password: data.password
    };

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.REGISTER, payload).pipe(
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
          localStorage.setItem('access_token', response.accessToken);
          this.currentUserSubject.next(response.user);
          this.isAuthenticatedSubject.next(true);
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

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.REGISTER_VERIFY_OTP, payload).pipe(
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
          localStorage.setItem('access_token', response.accessToken);
          this.currentUserSubject.next(response.user);
          this.isAuthenticatedSubject.next(true);
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

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.GOOGLE, payload).pipe(
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
          localStorage.setItem('access_token', response.accessToken);
          this.currentUserSubject.next(response.user);
          this.isAuthenticatedSubject.next(true);
        },
        error: (_err: Error) => {
          this.isAuthenticatedSubject.next(false);
        }
      })
    );
  }

  refreshToken(token?: string): Observable<LoginResponse> {
    const payload = token && token.length > 0 ? { refresh_token: token } : {};

    return this.http.post<BackendAuthResponse>(AUTH_ENDPOINTS.REFRESH_TOKEN, payload).pipe(
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
          localStorage.setItem('access_token', response.accessToken);
          this.currentUserSubject.next(response.user);
          this.isAuthenticatedSubject.next(true);
        },
        error: (_err: Error) => {
          this.signOut();
        }
      })
    );
  }

  signOut() {
    localStorage.removeItem('access_token');
    this.http.post(AUTH_ENDPOINTS.LOGOUT, {}).pipe(
      catchError(() => of({}))
    ).subscribe({
      next: () => {},
      error: () => {},
      complete: () => {}
    });

    this.currentUserSubject.next({
      id: '',
      email: '',
      fullName: '',
      role: '',
      tier: '',
      createdAt: ''
    });
    this.isAuthenticatedSubject.next(false);
  }
}
