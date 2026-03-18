"""This file defines authentication endpoints for the API.
It handles login, registration, and current-user flows used by the frontend."""


from fastapi import APIRouter, Depends, HTTPException, status

from ...core.auth import create_access_token
from ...db.postgres import create_user, get_user_by_email
from ..dependencies.auth import get_current_user
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
    try:
        user_id = create_user(request.email, request.password, request.role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Create access token (sub stays a string for stable decoding)
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
    
    if request.password != password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Create access token (sub stays a string for stable decoding)
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
