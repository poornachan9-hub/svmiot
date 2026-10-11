"""
Authentication API — login, register, current user.

ALL user data stored in MongoDB `users` collection.
SQLite is NO LONGER used for authentication.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.core.mongodb import get_mongodb
from backend.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "VIEWER"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


# ── Routes ─────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse, summary="User Login")
async def login(req: LoginRequest):
    """Authenticate user from MongoDB and return JWT token."""
    db = get_mongodb()
    user = await db["users"].find_one({"username": req.username})

    if user is None or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )

    # Update last_login in MongoDB
    await db["users"].update_one(
        {"username": req.username},
        {"$set": {"last_login": datetime.now(timezone.utc)}},
    )

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(
        access_token=token,
        role=user["role"],
        username=user["username"],
    )


@router.post("/register", summary="Register New User")
async def register(req: RegisterRequest):
    """Register a new user (writes to MongoDB `users` collection)."""
    db = get_mongodb()
    existing = await db["users"].find_one({"username": req.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    role = req.role if req.role in ("ADMIN", "ANALYST", "VIEWER") else "VIEWER"
    new_user = {
        "username": req.username,
        "email": req.email,
        "hashed_password": hash_password(req.password),
        "role": role,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }
    await db["users"].insert_one(new_user)
    return {"message": "User created", "username": req.username, "role": role}


@router.get("/me", summary="Current User")
async def get_me(current_user=Depends(get_current_user)):
    """Get current authenticated user info from MongoDB."""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login,
    }
