"""
dependencies.py — Reusable FastAPI dependencies for auth & authorization.

get_current_user : extracts and validates the Bearer JWT → returns User model
require_admin    : get_current_user + role check (403 if not admin)
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.auth import decode_token, oauth2_scheme
from app.database import get_db

_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

_403 = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Admin access required",
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Decode the JWT and return the corresponding active User.

    Raises 401 on:
      - missing / expired / malformed token
      - user not found in DB
      - user account deactivated
    """
    token_data = decode_token(token)
    if token_data is None:
        raise _401

    user = db.query(models.User).filter(
        models.User.id == token_data.user_id
    ).first()

    if user is None or not user.is_active:
        raise _401

    return user


def require_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Same as get_current_user but also requires the admin role.

    Raises 403 if the authenticated user is not an admin.
    """
    if current_user.role != models.UserRole.admin:
        raise _403
    return current_user
