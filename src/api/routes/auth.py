# src/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from ...db.postgres import create_user, get_user_by_email, add_user_to_course
from ...core.auth import verify_password, get_password_hash, create_access_token
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "student"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    role: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user.
    """
    # Validate role
    if request.role not in ("student", "instructor"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'student' or 'instructor'",
        )
    
    # Check if user already exists
    existing = get_user_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    # Create user
    password_hash = get_password_hash(request.password)
    try:
        user_id = create_user(request.email, password_hash, request.role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Create access token (sub must be a string per JWT spec)
    access_token = create_access_token(data={"sub": str(user_id), "email": request.email, "role": request.role})
    
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user_id,
            "email": request.email,
            "role": request.role,
        },
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login and get access token.
    """
    user = get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    user_id, email, password_hash, role, _ = user
    
    if not verify_password(request.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Create access token (sub must be a string per JWT spec)
    access_token = create_access_token(data={"sub": str(user_id), "email": email, "role": role})
    
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user_id,
            "email": email,
            "role": role,
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current user information.
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
    )

