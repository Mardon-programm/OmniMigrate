from typing import Annotated, AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CREDENTIALS_EXCEPTION_DETAIL, decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_prefix}/auth/login", auto_error=False
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    session: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENTIALS_EXCEPTION_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENTIALS_EXCEPTION_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    user = await session.get(User, int(user_id)) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENTIALS_EXCEPTION_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Dependency factory requiring the current user to have one of the roles."""

    def _dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return _dependency


async def get_user_or_none(
    session: AsyncSession, user_id: int
) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
