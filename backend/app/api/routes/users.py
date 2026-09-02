from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.core.security import hash_password, verify_password
from app.core.deps import require_roles, get_current_user
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/users", tags=["users"])


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_own_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.add(current_user)
    db.commit()
    log_action(
        db, action="password_changed", entity_type="user", entity_id=str(current_user.id),
        user_id=str(current_user.id),
    )


@router.get("/", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(
        db,
        action="user_created",
        entity_type="user",
        entity_id=str(user.id),
        user_id=str(current_user.id),
        details={"email": user.email, "role": user.role.value},
    )
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _active_admin_count(db: Session) -> int:
    return (
        db.query(User)
        .filter(User.role == UserRole.ADMIN, User.is_active.is_(True))
        .count()
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """
    Update a user's name, role or active status (admin only).

    Guards against administrator lock-out:
      * an admin cannot change their own role or deactivate themselves;
      * the last remaining active administrator cannot be demoted or disabled.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = payload.model_dump(exclude_unset=True)

    # Resulting state after the proposed change.
    new_role = data.get("role", user.role)
    new_active = data.get("is_active", user.is_active)

    is_self = str(user.id) == str(current_user.id)
    if is_self and "role" in data and new_role != user.role:
        raise HTTPException(status_code=400, detail="You cannot change your own role.")
    if is_self and "is_active" in data and new_active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")

    # Protect the last active administrator.
    removing_admin = user.role == UserRole.ADMIN and (
        new_role != UserRole.ADMIN or new_active is False
    )
    if removing_admin and _active_admin_count(db) <= 1:
        raise HTTPException(
            status_code=400,
            detail="At least one active administrator is required.",
        )

    changed = {}
    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data["full_name"]
        changed["full_name"] = user.full_name
    if "role" in data and data["role"] is not None:
        user.role = data["role"]
        changed["role"] = user.role.value
    if "is_active" in data and data["is_active"] is not None:
        user.is_active = data["is_active"]
        changed["is_active"] = user.is_active

    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(
        db,
        action="user_updated",
        entity_type="user",
        entity_id=str(user.id),
        user_id=str(current_user.id),
        details={"changes": changed},
    )
    return user
