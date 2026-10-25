from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class PasswordHasher:
    """Argon2id Password Hashing Domain Service (ADR-008)."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using Argon2id."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against the stored Argon2id hash."""
        return pwd_context.verify(plain_password, hashed_password)
