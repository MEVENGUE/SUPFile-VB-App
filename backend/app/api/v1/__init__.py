"""
API v1 routes
"""
from fastapi import APIRouter
from app.api.v1 import auth, files, users, folders, share, oauth, dashboard, file_versions, file_metadata, file_history, file_comments

api_router = APIRouter()

# Include route modules
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(oauth.router, prefix="/auth", tags=["oauth2"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(share.router, prefix="/share", tags=["share"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(file_versions.router, tags=["file-versions"])
api_router.include_router(file_metadata.router, tags=["file-metadata"])
api_router.include_router(file_history.router, prefix="/history", tags=["history"])
api_router.include_router(file_comments.router, prefix="/comments", tags=["comments"])

