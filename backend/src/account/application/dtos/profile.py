import re
import zoneinfo

from pydantic import BaseModel, Field, field_validator


class UpdateProfileRequestDTO(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    timezone: str = Field(default="Asia/Ho_Chi_Minh")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in zoneinfo.available_timezones():
            raise ValueError(f"'{v}' is not a valid IANA timezone.")
        return v


class ProfileResponseDTO(BaseModel):
    id: str
    email: str
    full_name: str
    timezone: str
    role: str
    tier: str
    created_at: str


class AIQuotaResponseDTO(BaseModel):
    monthly_limit: int
    used_calls: int
    reserved_calls: int
    remaining_calls: int
    tokens_consumed: int
    cycle_start: str
    cycle_end: str


class ChangePasswordRequestDTO(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu phải có tối thiểu 8 ký tự.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái in thường.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái in hoa.")
        if not re.search(r"\d", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số.")
        if not re.search(r"[^a-zA-Z0-9]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt.")
        return v
