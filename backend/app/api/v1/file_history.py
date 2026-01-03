"""
API routes for file and folder history
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.middleware import get_current_user_id
from app.models.file_history import FileHistory, FolderHistory, ActionType
from app.models.file import File
from app.models.folder import Folder
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class HistoryResponse(BaseModel):
    id: int
    file_id: Optional[int] = None
    folder_id: Optional[int] = None
    user_id: int
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/files/{file_id}/history", response_model=List[HistoryResponse])
async def get_file_history(
    file_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get history for a specific file
    """
    # Verify file exists and belongs to user
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == current_user_id,
        File.deleted_at.is_(None)
    ).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable"
        )

    # Get history
    history = db.query(FileHistory).filter(
        FileHistory.file_id == file_id
    ).order_by(desc(FileHistory.created_at)).offset(skip).limit(limit).all()

    return history


@router.get("/folders/{folder_id}/history", response_model=List[HistoryResponse])
async def get_folder_history(
    folder_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get history for a specific folder
    """
    # Verify folder exists and belongs to user
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current_user_id,
        Folder.deleted_at.is_(None)
    ).first()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable"
        )

    # Get history
    history = db.query(FolderHistory).filter(
        FolderHistory.folder_id == folder_id
    ).order_by(desc(FolderHistory.created_at)).offset(skip).limit(limit).all()

    return history


@router.get("/history", response_model=List[HistoryResponse])
async def get_user_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[ActionType] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get all history for the current user
    """
    # Get file history
    file_history_query = db.query(FileHistory).filter(
        FileHistory.user_id == current_user_id
    )
    
    # Get folder history
    folder_history_query = db.query(FolderHistory).filter(
        FolderHistory.user_id == current_user_id
    )

    if action:
        file_history_query = file_history_query.filter(FileHistory.action == action)
        folder_history_query = folder_history_query.filter(FolderHistory.action == action)

    # Combine and sort
    file_history = file_history_query.all()
    folder_history = folder_history_query.all()

    # Combine and sort by created_at
    all_history = sorted(
        list(file_history) + list(folder_history),
        key=lambda x: x.created_at,
        reverse=True
    )

    return all_history[skip:skip + limit]


# Helper function to create history entries
def create_file_history(
    db: Session,
    file_id: int,
    user_id: int,
    action: ActionType,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    description: Optional[str] = None,
    extra_data: Optional[dict] = None
):
    """Create a file history entry"""
    import json
    history = FileHistory(
        file_id=file_id,
        user_id=user_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        description=description,
        extra_data=json.dumps(extra_data) if extra_data else None
    )
    db.add(history)
    db.commit()
    return history


def create_folder_history(
    db: Session,
    folder_id: int,
    user_id: int,
    action: ActionType,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    description: Optional[str] = None,
    extra_data: Optional[dict] = None
):
    """Create a folder history entry"""
    import json
    history = FolderHistory(
        folder_id=folder_id,
        user_id=user_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        description=description,
        extra_data=json.dumps(extra_data) if extra_data else None
    )
    db.add(history)
    db.commit()
    return history

