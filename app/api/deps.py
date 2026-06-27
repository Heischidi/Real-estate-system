"""FastAPI auth dependency — protects admin routes with JWT."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.killswitch import SYSTEM_PAUSED, LICENSE_EXPIRED_API
from app.services.auth_service import decode_access_token

bearer_scheme = HTTPBearer()


async def check_system_active() -> None:
    """
    Global FastAPI dependency. Raises HTTP 503 for every request
    when SYSTEM_PAUSED is True. Attach to the root api_router so
    every endpoint is blocked automatically.
    """
    if SYSTEM_PAUSED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=LICENSE_EXPIRED_API["detail"],
        )


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, object]:
    """
    FastAPI dependency that validates the Bearer JWT token.
    Raises 401 if invalid. Returns the decoded payload if valid.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or payload.get("sub") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
