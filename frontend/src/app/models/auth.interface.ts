export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  role: string;
  tier: string;
  createdAt: string;
}

export interface BackendUserPayload {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tier: string;
  created_at: string;
}

export interface BackendAuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: BackendUserPayload;
}

export interface LoginRequest {
  email: string;
  password: string;
  rememberMe: boolean;
}

export interface LoginResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  user: UserProfile;
}

export interface RegisterRequest {
  fullName: string;
  email: string;
  password: string;
}

export interface RegisterResponse {
  message: string;
  accessToken: string;
  user: UserProfile;
}

export interface RequestRegisterOtpRequest {
  fullName: string;
  email: string;
  password: string;
}

export interface ResendRegisterOtpRequest {
  email: string;
}

export interface VerifyRegisterOtpRequest {
  email: string;
  otpCode: string;
}

export interface RequestPasswordResetOtpRequest {
  email: string;
}

export interface VerifyPasswordResetOtpRequest {
  email: string;
  otpCode: string;
}

export interface VerifyPasswordResetOtpResponse {
  message: string;
  reset_token: string;
}

export interface ConfirmPasswordResetRequest {
  email: string;
  newPassword: string;
  resetToken?: string;
  otpCode?: string;
}

export interface MessageResponse {
  message: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: UserProfile;
  error: string;
}

export interface GoogleAuthRequest {
  idToken: string;
  accessToken: string;
}

