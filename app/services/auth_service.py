"""Auth service — JWT token creation and validation for admin routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.logging_config import get_logger

log = get_logger(__name__)
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_admin(username: str, password: str) -> bool:
    """Verify admin credentials against settings."""
    if username != settings.admin_username:
        return False
    # Compare plaintext (stored in env) — for production use hashed passwords
    return password == settings.admin_password


def create_access_token(data: dict[str, object]) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    to_encode["exp"] = expire
    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict[str, object] | None:
    """Decode and validate a JWT. Returns None if invalid."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload  # type: ignore[return-value]
    except JWTError:
        log.warning("jwt_decode_failed")
        return None
