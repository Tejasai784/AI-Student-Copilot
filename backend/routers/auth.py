"""Authentication and user session router."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from backend.config import settings
from backend.deps import get_db_session, get_current_user
from backend.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.schemas import (
    ApiResponse,
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
)
from database.models import User, RefreshToken

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=ApiResponse[UserResponse])
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db_session)):
    """Registers a new user account."""
    existing_user = db.query(User).filter(User.username == req.username.strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )

    if req.email:
        existing_email = db.query(User).filter(User.email == req.email.strip().lower()).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )

    hashed_pw = hash_password(req.password)
    user = User(
        username=req.username.strip(),
        email=req.email.strip().lower() if req.email else None,
        hashed_password=hashed_pw,
        full_name=req.full_name.strip() if req.full_name else req.username.strip(),
        role="student",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return ApiResponse(
        success=True,
        data=UserResponse.model_validate(user),
        message="Registration successful."
    )


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login_user(
    req: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db_session)
):
    """Authenticates a user and issues access/refresh tokens."""
    user = db.query(User).filter(User.username == req.username.strip()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    # If the user has a password set, verify it
    if user.hashed_password:
        if not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password."
            )
    else:
        # Default local_student user or initial seed without password
        # Set the password now if matching default or initial login
        if user.username == "local_student":
            user.hashed_password = hash_password(req.password)
            db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Password not configured."
            )

    access_token = create_access_token({"sub": user.username, "user_id": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.username, "user_id": user.id})

    # Store refresh token for revocation
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rt_record = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at,
        revoked=False
    )
    db.add(rt_record)
    db.commit()

    # Set httpOnly cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        samesite="lax",
        secure=False  # True in HTTPS production
    )
    # Set access token cookie as well for easy client auth
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False
    )

    return ApiResponse(
        success=True,
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        ),
        message="Login successful."
    )


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session)
):
    """Refreshes the access token using the refresh token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing."
        )

    try:
        payload = decode_token(token)
        username = payload.get("sub")
        token_type = payload.get("type")
        if not username or token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired or invalid refresh token.")

    # Check database revocation
    rt_record = db.query(RefreshToken).filter(RefreshToken.token == token, RefreshToken.revoked == False).first()
    if not rt_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or not found.")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found.")

    new_access_token = create_access_token({"sub": user.username, "user_id": user.id, "role": user.role})
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False
    )

    return ApiResponse(
        success=True,
        data=TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            refresh_token=token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        ),
        message="Token refreshed."
    )


@router.post("/logout", response_model=ApiResponse[None])
def logout_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session)
):
    """Logs out user by revoking refresh token and clearing auth cookies."""
    token = request.cookies.get("refresh_token")
    if token:
        rt_record = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        if rt_record:
            rt_record.revoked = True
            db.commit()

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return ApiResponse(success=True, data=None, message="Logged out successfully.")


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_current_user_profile(user: User = Depends(get_current_user)):
    """Returns the authenticated user details."""
    return ApiResponse(success=True, data=UserResponse.model_validate(user))
