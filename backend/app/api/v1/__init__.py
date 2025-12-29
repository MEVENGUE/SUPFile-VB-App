"""
API v1 routes
"""
from fastapi import APIRouter
from app.api.v1 import auth, files, users

api_router = APIRouter()

# Include route modules
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

