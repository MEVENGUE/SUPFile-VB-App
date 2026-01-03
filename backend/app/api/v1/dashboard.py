"""
Dashboard endpoints: statistics and analytics
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.sql import func as sql_func
from typing import Dict, List, Optional
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.core.middleware import get_current_user_id
from app.models.user import User
from app.models.file import File
from app.models.folder import Folder

logger = logging.getLogger(__name__)

router = APIRouter()


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response"""
    total_files: int
    total_folders: int
    total_size_bytes: int
    total_size_mb: float
    files_by_type: Dict[str, int]
    recent_files: List[Dict]
    storage_usage_percentage: float  # Percentage of quota used (if quota exists)


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for the current user
    """
    # Total files (not deleted)
    total_files = db.query(File).filter(
        and_(
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    ).count()

    # Total folders (not deleted)
    total_folders = db.query(Folder).filter(
        and_(
            Folder.user_id == current_user_id,
            Folder.deleted_at.is_(None)
        )
    ).count()

    # Total storage size
    total_size_result = db.query(func.sum(File.file_size)).filter(
        and_(
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    ).scalar()
    total_size_bytes = total_size_result or 0
    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

    # Files by type
    files_by_type_query = db.query(
        File.content_type,
        func.count(File.id).label('count')
    ).filter(
        and_(
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    ).group_by(File.content_type).all()

    files_by_type = {}
    for content_type, count in files_by_type_query:
        if content_type:
            # Simplify content types (e.g., "image/jpeg" -> "image")
            main_type = content_type.split('/')[0] if '/' in content_type else content_type
            files_by_type[main_type] = files_by_type.get(main_type, 0) + count
        else:
            files_by_type['unknown'] = files_by_type.get('unknown', 0) + count

    # Recent files (last 5 modified/uploaded)
    recent_files_query = db.query(File).filter(
        and_(
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    ).order_by(File.created_at.desc()).limit(5).all()

    recent_files = [
        {
            "id": f.id,
            "filename": f.original_filename,
            "size": f.file_size,
            "content_type": f.content_type,
            "created_at": f.created_at.isoformat(),
        }
        for f in recent_files_query
    ]

    # Storage usage percentage (assuming 100GB quota for now, can be made configurable)
    QUOTA_BYTES = 100 * 1024 * 1024 * 1024  # 100 GB
    storage_usage_percentage = round((total_size_bytes / QUOTA_BYTES) * 100, 2) if QUOTA_BYTES > 0 else 0

    return DashboardStatsResponse(
        total_files=total_files,
        total_folders=total_folders,
        total_size_bytes=total_size_bytes,
        total_size_mb=total_size_mb,
        files_by_type=files_by_type,
        recent_files=recent_files,
        storage_usage_percentage=min(storage_usage_percentage, 100.0)  # Cap at 100%
    )

