"""
SecureIoT-X Security Module — JWT Authentication & Password Hashing.

ALL user data lives in MongoDB `users` collection.
SQLite is NO LONGER used for any authentication or user management.

Provides:
- Password hashing (bcrypt)
- JWT token creation / verification
- Role-based access control helpers
- FastAPI dependency for protected routes (reads users from MongoDB)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.core.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Password hashing ───────────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt (handles UTF-8 up to 72 bytes)."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against its bcrypt hash."""
    pwd_bytes = plain.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT tokens ─────────────────────────────────────────────────


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expiry_minutes)
    )
    to_encode.update({"exp": expire, "jti": uuid.uuid4().hex})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependencies (MongoDB-based) ──────────────────────


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
):
    """Extract and validate the current user from JWT. Looks up user in MongoDB."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    # Look up user in MongoDB `users` collection
    from backend.core.mongodb import get_mongodb
    db = get_mongodb()
    user = await db["users"].find_one({"username": username, "is_active": True})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Return a simple namespace-like object that behaves like the old SQLAlchemy User
    class _UserProxy:
        def __init__(self, doc):
            self.username = doc["username"]
            self.email = doc.get("email", "")
            self.role = doc.get("role", "VIEWER")
            self.is_active = doc.get("is_active", True)
            self.last_login = doc.get("last_login")

    return _UserProxy(user)


def require_role(*allowed_roles: str):
    """Dependency factory: restrict endpoint to specific roles."""

    async def _role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not permitted. Required: {allowed_roles}",
            )
        return current_user

    return _role_checker
