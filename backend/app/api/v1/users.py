from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import PasswordChange, UserCreate, UserRead, UserUpdate
from app.services.repositories import UserRepository

router = APIRouter()


def _to_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserRead])
async def list_users(
    session: DbSession,
    _admin: User = Depends(require_roles(UserRole.admin)),
) -> list[UserRead]:
    repo = UserRepository(session)
    return [_to_read(u) for u in await repo.list_all()]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int, session: DbSession, current: CurrentUser
) -> UserRead:
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if current.role != UserRole.admin and current.id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return _to_read(user)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: DbSession,
    _admin: User = Depends(require_roles(UserRole.admin)),
) -> UserRead:
    repo = UserRepository(session)
    existing = await repo.get_by_email(payload.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered.")
    user = await repo.create(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    await session.commit()
    await session.refresh(user)
    return _to_read(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int, payload: UserUpdate, session: DbSession, current: CurrentUser
) -> UserRead:
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if current.role != UserRole.admin and current.id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if payload.role is not None and current.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can change roles.")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None and current.role == UserRole.admin:
        user.is_active = payload.is_active
    await session.commit()
    await session.refresh(user)
    return _to_read(user)


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def change_password(
    user_id: int, payload: PasswordChange, session: DbSession, current: CurrentUser
) -> None:
    if current.id != user_id:
        raise HTTPException(status_code=403, detail="You can only change your own password.")
    if not verify_password(payload.current_password, current.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    current.hashed_password = hash_password(payload.new_password)
    await session.commit()
