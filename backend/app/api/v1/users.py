"""
User management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.middleware import get_current_user_id
from app.models.user import User

router = APIRouter()


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: str
    username: str
    full_name: str = None
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get current user information
    """
    user = db.query(User).filter(User.id == current_user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )

