"""
routers/users_router.py — User management (admin-only).

Routes (all require admin role):
  GET    /api/users/                   — list all users
  GET    /api/users/{user_id}          — get a single user
  PUT    /api/users/{user_id}/role     — change a user's role
  DELETE /api/users/{user_id}          — soft-delete (deactivate) a user
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.dependencies import require_admin
from app.schemas import RoleUpdate, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get(
    "/",
    response_model=List[UserOut],
    summary="List all users (admin only)",
)
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Get a specific user (admin only)",
)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put(
    "/{user_id}/role",
    response_model=UserOut,
    summary="Change a user's role (admin only)",
)
def update_role(
    user_id: UUID,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_admin),
):
    if str(user_id) == str(current_admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role_update.role
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user account (admin only)",
)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_admin),
):
    if str(user_id) == str(current_admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()
