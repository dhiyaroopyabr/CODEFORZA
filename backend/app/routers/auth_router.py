"""
routers/auth_router.py — Authentication endpoints.

Routes:
  POST /api/auth/register  — create new user account
  POST /api/auth/login     — login and receive JWT
  GET  /api/auth/me        — return current user's profile
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app import models
from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas import Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit("10/minute")  # prevent registration spam
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user. All new accounts start with role='user'.
    Promote to admin via PUT /api/users/{id}/role (admin-only).
    """
    if db.query(models.User).filter(models.User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=models.UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive a JWT access token",
)
@limiter.limit("5/minute")  # brute force protection
def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Exchange username + password for a signed JWT.
    The token encodes: sub (user_id), username, role, exp.
    """
    # Always query by username, then verify password hash
    user = db.query(models.User).filter(
        models.User.username == credentials.username
    ).first()

    # Deliberate vague error message — don't reveal whether username exists
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated",
        )

    access_token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
    })

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the currently authenticated user",
)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user
