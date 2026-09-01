from datetime import UTC, datetime, timedelta

import pyotp
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_redis
from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.models.password_reset import PasswordResetStatus, PasswordResetToken
from app.models.user import User, UserRole
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MfaDisableRequest,
    MfaEnableRequest,
    MfaSetupResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserInfo,
)

router = APIRouter()

RESET_TOKEN_EXPIRE_MINUTES = 30


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DbSession) -> TokenResponse:
    """Register a new user. Only admins can create engineer/admin accounts."""
    if payload.role in (UserRole.admin, UserRole.engineer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privileged roles must be assigned by an administrator.",
        )

    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def _otpauth_uri(email: str, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="OmniMigrate")


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    """Authenticate a user and return JWT access/refresh tokens.

    When TOTP MFA is enabled the request must include `mfa_code`;
    otherwise responds 401 with code "mfa_required".
    """
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")

    if user.mfa_enabled and user.mfa_secret:
        if not payload.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required.",
                headers={"X-MFA-Required": "true"},
            )
        if not pyotp.TOTP(user.mfa_secret).verify(payload.mfa_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code.",
                headers={"X-MFA-Required": "true"},
            )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: DbSession) -> TokenResponse:
    """Exchange a valid refresh token for a fresh access token."""
    redis = await get_redis()
    blocked = await redis.get(f"blocklist:refresh:{payload.refresh_token}")
    if blocked is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked.",
        )
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from None
    user = await session.get(User, int(token_payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active."
        )
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserInfo)
async def me(user: CurrentUser) -> UserInfo:
    """Return the currently authenticated user."""
    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(user: CurrentUser, session: DbSession) -> MfaSetupResponse:
    """Generate a TOTP secret for the user. Idempotent until enabled."""
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA is already enabled. Disable it first.",
        )
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    await session.commit()
    return MfaSetupResponse(secret=secret, otpauth_uri=_otpauth_uri(user.email, secret))


@router.post("/mfa/enable", response_model=UserInfo)
async def mfa_enable(payload: MfaEnableRequest, user: CurrentUser, session: DbSession) -> UserInfo:
    """Confirm a TOTP code to activate MFA."""
    if not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call /auth/mfa/setup first.",
        )
    if not pyotp.TOTP(user.mfa_secret).verify(payload.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code."
        )
    user.mfa_enabled = True
    await session.commit()
    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        mfa_enabled=True,
    )


@router.post("/mfa/disable", response_model=UserInfo)
async def mfa_disable(
    payload: MfaDisableRequest, user: CurrentUser, session: DbSession
) -> UserInfo:
    """Disable MFA; requires password confirmation plus a valid current code."""
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect password.")
    if not user.mfa_secret or not pyotp.TOTP(user.mfa_secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code.")
    user.mfa_enabled = False
    user.mfa_secret = None
    await session.commit()
    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        mfa_enabled=False,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    payload: LogoutRequest,
    user: CurrentUser,
    session: DbSession,
) -> None:
    """Revoke refresh token by adding it to Redis blocklist."""
    if payload.refresh_token:
        try:
            decoded = decode_token(payload.refresh_token, expected_type="refresh")
            exp = decoded.get("exp")
            if exp:
                exp_dt = datetime.fromtimestamp(exp, tz=UTC)
                ttl = max(0, int((exp_dt - datetime.now(UTC)).total_seconds()))
                redis = await get_redis()
                await redis.setex(f"blocklist:refresh:{payload.refresh_token}", ttl, "1")
        except Exception:
            pass


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(payload: ForgotPasswordRequest, session: DbSession) -> dict:
    """Send a password reset token (always returns 200 to prevent enumeration)."""
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is not None:
        from app.core.security import create_password_reset_token

        raw_token = create_password_reset_token(user.id)
        token_hash = hash_reset_token(raw_token)
        now = datetime.now(UTC)
        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            status=PasswordResetStatus.pending,
            expires_at=now + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
            created_at=now,
        )
        session.add(reset)
        await session.commit()
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(payload: ResetPasswordRequest, session: DbSession) -> dict:
    """Reset user password using a valid token."""
    token_hash = hash_reset_token(payload.token)
    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.status == PasswordResetStatus.pending,
            PasswordResetToken.is_active == True,  # noqa: E712
        )
    )
    reset = result.scalar_one_or_none()
    if reset is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )
    if reset.expires_at.replace(tzinfo=None) < datetime.now(UTC).replace(tzinfo=None):
        reset.status = PasswordResetStatus.expired
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    user = await session.get(User, reset.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")

    user.hashed_password = hash_password(payload.new_password)
    reset.status = PasswordResetStatus.used
    reset.used_at = datetime.now(UTC)
    await session.commit()

    return {"message": "Password has been reset successfully."}
