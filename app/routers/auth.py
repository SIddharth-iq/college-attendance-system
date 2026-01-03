"""
Authentication and authorization utilities.
Handles role-based access control (RBAC) for API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, RoleEnum
from app.config import settings
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from passlib.context import (
    CryptContext,
)  # Simple password hashing (use bcrypt in production)

router = APIRouter()
security = HTTPBearer()
from fastapi import Header


# Pydantic schemas for login
class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str  # Email address used as username
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    token_type: str = "Bearer"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with the provided data.

    Args:
        data: Dictionary containing the data to encode in the token (typically user info)
        expires_delta: Optional timedelta for token expiration. If not provided, uses default from config.

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary containing the decoded token payload

    Raises:
        HTTPException: If token is invalid, expired, or cannot be decoded
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    user = (
        db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_role(allowed_roles: list[RoleEnum]):
    """
    Dependency factory for role-based access control.
    Creates a dependency that checks if user has one of the allowed roles.

    Usage:
        @app.get("/admin-only")
        def admin_endpoint(current_user: User = Depends(require_role([RoleEnum.ADMIN]))):
            ...
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


# Common role dependencies for convenience
require_admin = Depends(require_role([RoleEnum.ADMIN]))
require_faculty = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN]))
require_student = Depends(
    require_role([RoleEnum.STUDENT, RoleEnum.FACULTY, RoleEnum.ADMIN])
)
require_any_authenticated = Depends(get_current_user)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint - authenticates user and returns JWT access token.

    Args:
        login_data: Login credentials (username/email and password)
        db: Database session

    Returns:
        TokenResponse containing access_token and token_type

    Raises:
        HTTPException: If credentials are invalid or user is inactive
    """
    # Query user by email (username field contains email)
    user = db.query(User).filter(User.email == login_data.username).first()

    # Check if user exists and password is correct
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(access_token=access_token, token_type="Bearer")


@router.get("/ping")
def auth_ping():
    return {"auth": "ok"}
