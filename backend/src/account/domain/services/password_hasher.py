from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


class PasswordHasher:
    """Argon2id Password Hashing Domain Service (ADR-008)."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using Argon2id."""
        return password_hash.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against the stored Argon2id hash."""
        return password_hash.verify(plain_password, hashed_password)
