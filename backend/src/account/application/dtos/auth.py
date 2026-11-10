import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# --- Domain / Application Transfer Objects ---
@dataclass
class UserDTO:
    id: str
    email: str
    full_name: str
    role: str
    tier: str
    created_at: str


@dataclass
class AuthResultDTO:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserDTO


# --- Commands for Use Cases ---
@dataclass
class LoginCommand:
    email: str
    password: str
    remember_me: bool = True


@dataclass
class RegisterCommand:
    full_name: str
    email: str
    password: str


@dataclass
class RequestRegisterOtpCommand:
    full_name: str
    email: str
    password: str


@dataclass
class ResendRegisterOtpCommand:
    email: str


@dataclass
class VerifyRegisterOtpCommand:
    email: str
    otp_code: str


@dataclass
class RequestPasswordResetOtpCommand:
    email: str


@dataclass
class VerifyPasswordResetOtpCommand:
    email: str
    otp_code: str


@dataclass
class VerifyPasswordResetOtpResult:
    message: str
    reset_token: str


@dataclass
class ConfirmPasswordResetCommand:
    email: str
    new_password: str
    reset_token: str | None = None
    otp_code: str | None = None


@dataclass
class GoogleAuthCommand:
    id_token: str | None = None
    access_token: str | None = None


@dataclass
class RefreshTokenCommand:
    raw_refresh_token: str


# --- Presentation / API Request & Response Schemas ---
class UserProfileSchema(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tier: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = True


class RegisterRequestSchema(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái in thường.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái in hoa.")
        if not re.search(r"\d", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số.")
        if not re.search(r"[^a-zA-Z0-9]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt.")
        return v


class ResendRegisterOtpSchema(BaseModel):
    email: EmailStr


class VerifyRegisterOtpSchema(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class RequestPasswordResetOtpSchema(BaseModel):
    email: EmailStr


class VerifyPasswordResetOtpSchema(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class VerifyPasswordResetOtpResponseSchema(BaseModel):
    message: str
    reset_token: str


class ConfirmPasswordResetSchema(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=8, max_length=100)
    reset_token: str | None = None
    otp_code: str | None = None

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái in thường.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái in hoa.")
        if not re.search(r"\d", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số.")
        if not re.search(r"[^a-zA-Z0-9]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt.")
        return v


class MessageResponseSchema(BaseModel):
    message: str


class GoogleAuthRequestSchema(BaseModel):
    id_token: str | None = None
    credential: str | None = None
    access_token: str | None = None


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str | None = None


class LoginResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    user: UserProfileSchema
