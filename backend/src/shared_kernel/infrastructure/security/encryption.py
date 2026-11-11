import base64

from cryptography.fernet import Fernet, InvalidToken

from src.shared_kernel.config import Settings, get_settings


def validate_fernet_key(key: str | bytes) -> bool:
    """Validate that the given key is a 32-byte url-safe base64 Fernet key."""
    if not key:
        return False
    try:
        raw_key = key.encode("utf-8") if isinstance(key, str) else key
        decoded = base64.urlsafe_b64decode(raw_key)
        if len(decoded) != 32:
            return False
        Fernet(raw_key)
        return True
    except (ValueError, TypeError, Exception):
        return False


def generate_fernet_key() -> str:
    """Generate a new 32-byte url-safe base64 Fernet key string."""
    return Fernet.generate_key().decode("utf-8")


def _resolve_fernet_key(key: str | bytes | None = None) -> bytes:
    """Resolve and validate a Fernet key, falling back to application settings."""
    if key is None:
        settings = get_settings()
        key_str = settings.calendar_encryption_key or settings.fernet_key
    elif isinstance(key, bytes):
        key_str = key.decode("utf-8")
    else:
        key_str = key

    if not key_str or not validate_fernet_key(key_str):
        raise ValueError("Invalid or missing 32-byte url-safe base64 Fernet encryption key.")

    return key_str.encode("utf-8") if isinstance(key_str, str) else key_str


def encrypt_token(token: str, key: str | bytes | None = None) -> str:
    """Encrypt a plaintext token using Fernet AES-CBC with HMAC-SHA256."""
    key_bytes = _resolve_fernet_key(key)
    fernet = Fernet(key_bytes)
    return fernet.encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str, key: str | bytes | None = None) -> str:
    """Decrypt a Fernet encrypted token ciphertext back to plaintext string."""
    key_bytes = _resolve_fernet_key(key)
    fernet = Fernet(key_bytes)
    try:
        return fernet.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Ciphertext decryption failed: invalid token or wrong key.") from exc


def ensure_calendar_encryption_key_valid(settings: Settings | None = None) -> None:
    """Fail-fast validation for calendar encryption key when CALENDAR_PROVIDER is 'google'."""
    if settings is None:
        settings = get_settings()

    provider = settings.calendar_provider.strip().lower()
    if provider in ("google", "google_calendar"):
        if not settings.calendar_encryption_key or not validate_fernet_key(
            settings.calendar_encryption_key
        ):
            raise ValueError(
                "CALENDAR_ENCRYPTION_KEY must be a valid 32-byte url-safe base64 string "
                "when CALENDAR_PROVIDER is 'google'."
            )
