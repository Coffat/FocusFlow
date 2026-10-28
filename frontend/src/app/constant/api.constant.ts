export const API_BASE_URL = 'http://localhost:8000/api/v1';

export const AUTH_ENDPOINTS = {
  LOGIN: `${API_BASE_URL}/auth/login`,
  REGISTER: `${API_BASE_URL}/auth/register`,
  REGISTER_REQUEST_OTP: `${API_BASE_URL}/auth/register/request-otp`,
  REGISTER_RESEND_OTP: `${API_BASE_URL}/auth/register/resend-otp`,
  REGISTER_VERIFY_OTP: `${API_BASE_URL}/auth/register/verify-otp`,
  PASSWORD_RESET_REQUEST_OTP: `${API_BASE_URL}/auth/password-reset/request-otp`,
  PASSWORD_RESET_VERIFY_OTP: `${API_BASE_URL}/auth/password-reset/verify-otp`,
  PASSWORD_RESET_CONFIRM: `${API_BASE_URL}/auth/password-reset/confirm`,
  GOOGLE: `${API_BASE_URL}/auth/google`,
  ME: `${API_BASE_URL}/auth/me`,
  REFRESH_TOKEN: `${API_BASE_URL}/auth/refresh`,
  LOGOUT: `${API_BASE_URL}/auth/logout`
};

export const GOOGLE_CLIENT_ID = '408847171120-dldrof0cc90f3nn19qsl7amrl7fpc9jc.apps.googleusercontent.com';
