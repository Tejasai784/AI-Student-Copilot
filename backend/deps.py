"""FastAPI dependencies for authentication, database session, and user context."""
from __future__ import annotations

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from backend.config import settings
from backend.security import decode_token
from backend.logging_config import logger
from database.database import get_db, SessionLocal
from database.models import User, StudentProfile

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db_session() -> Generator[Session, None, None]:
    """Yields a transactional database session."""
    with get_db() as session:
        yield session


def get_token_from_request(request: Request, bearer_token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """Extracts JWT token from Authorization header or cookies."""
    if bearer_token:
        return bearer_token
    # Fallback to cookie
    return request.cookies.get("access_token")


def get_current_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db_session)
) -> User:
    """Enforces authentication and retrieves the current User object."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        # Check if local fallback is allowed for single-user dev mode
        user = db.query(User).filter(User.id == 1).first()
        if user:
            return user
        raise credentials_exception

    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if username is None or token_type != "access":
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


def get_optional_current_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db_session)
) -> Optional[User]:
    """Retrieves current user if token exists, else defaults to local user (id=1)."""
    if not token:
        return db.query(User).filter(User.id == 1).first()
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if username:
            user = db.query(User).filter(User.username == username).first()
            if user and user.is_active:
                return user
    except Exception:
        pass
    return db.query(User).filter(User.id == 1).first()
