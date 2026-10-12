import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# Configure Argon2id with high-assurance production parameters:
# Type: Argon2id (default in argon2-cffi)
# Memory cost: 65,536 KiB (64 MiB)
# Time cost: 3 iterations
# Parallelism: 4 threads
hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2id.
    """
    return hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2id hash.
    Constant-time comparison protects against timing attacks.
    Returns True if valid, False otherwise.
    """
    try:
        return hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def generate_session_token() -> str:
    """
    Generate a cryptographically secure 256-bit random URL-safe token.
    """
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """
    Generate a cryptographically secure random token for CSRF protection.
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """
    Hash session token using SHA-256 for secure database storage.
    If the database is compromised, raw session tokens cannot be replayed.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
