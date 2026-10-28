from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions.auth_exceptions import InvalidTokenError, TokenExpiredError
from src.infrastructure.database.models.user_orm import UserORM
from src.infrastructure.database.repositories.user_repository import SqlUserRepository
from src.infrastructure.database.session import get_db
from src.infrastructure.security.jwt_token_provider import JwtTokenProvider

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> UserORM:
    """Extract and validate current authenticated user via JWT header or HttpOnly cookie."""
    token: str | None = None

    # Priority 1: Authorization Header (Bearer token)
    if bearer and bearer.credentials:
        token = bearer.credentials
    # Priority 2: Cookie fallback (ADR-008 SameSite Cookie)
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = JwtTokenProvider.decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise InvalidTokenError("Missing subject in token.")
        user_id = UUID(user_id_str)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh your session.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_repo = SqlUserRepository(db)
    user = await user_repo.find_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
        )

    if user.role == "LOCKED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been locked or suspended.",
        )

    return user
