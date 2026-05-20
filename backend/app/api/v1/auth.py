"""
Authentication endpoints: register, login, refresh token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.rate_limit import limiter
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.middleware import get_current_user_id
from app.models.user import User
from datetime import timedelta
from app.core.config import settings

router = APIRouter()


class UserRegister(BaseModel):
    """User registration schema"""
    email: EmailStr
    username: str
    password: str
    full_name: str = None


class UserLogin(BaseModel):
    """User login schema"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "username": new_user.username
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and get access token
    Uses OAuth2PasswordRequestForm for compatibility
    """
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(token_data: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    """
    payload = verify_token(token_data.refresh_token, token_type="refresh")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Create new tokens
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get current user information
    """
    from app.api.v1.users import get_current_user
    return await get_current_user(current_user_id, db)

