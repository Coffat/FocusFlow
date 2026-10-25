class AuthError(Exception):
    """Base exception for all authentication and authorization errors."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when email or password verification fails (UC-AUTH-02)."""
    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(message)


class AccountLockedError(AuthError):
    """Raised when an account is marked as locked (UC-AUTH-02)."""
    def __init__(self, message: str = "Account is currently locked or suspended."):
        super().__init__(message)


class UserAlreadyExistsError(AuthError):
    """Raised during registration when an email is already registered."""
    def __init__(self, message: str = "An account with this email address already exists."):
        super().__init__(message)


class TokenExpiredError(AuthError):
    """Raised when JWT token has expired."""
    def __init__(self, message: str = "Authentication token has expired."):
        super().__init__(message)


class InvalidTokenError(AuthError):
    """Raised when JWT signature or claims are invalid."""
    def __init__(self, message: str = "Invalid authentication token."):
        super().__init__(message)


class RateLimitError(AuthError):
    """Raised when an operation violates rate limits or cooldown windows."""
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message)


class InvalidOtpError(AuthError):
    """Raised when OTP code verification fails or code has expired."""
    def __init__(self, message: str = "Invalid or expired verification code."):
        super().__init__(message)
