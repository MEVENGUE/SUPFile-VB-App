"""
File metadata endpoints (tags, descriptions, custom metadata)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.core.database import get_db
from app.core.middleware import get_current_user_id
from app.models.file import File
from app.models.file_metadata import FileMetadata
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class FileMetadataRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[str] = None  # Comma-separated tags
    custom_metadata: Optional[Dict[str, Any]] = None


class FileMetadataResponse(BaseModel):
    id: int
    file_id: int
    description: Optional[str]
    tags: Optional[str]
    custom_metadata: Optional[Dict[str, Any]]
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/files/{file_id}/metadata", response_model=FileMetadataResponse)
def get_file_metadata(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get metadata for a file
    """
    # Verify file exists and belongs to user
    file = db.query(File).filter(
        and_(
            File.id == file_id,
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    ).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable"
        )

    metadata = db.query(FileMetadata).filter(
        FileMetadata.file_id == file_id
    ).first()

    if not metadata:
        # Return empty metadata if none exists
        return FileMetadataResponse(
            id=0,
            file_id=file_id,
            description=None,
            tags=None,
            custom_metadata=None,
            created_at="",
            updated_at=None
        )

    return FileMetadataResponse(
        id=metadata.id,
        file_id=metadata.file_id,
        description=metadata.description,
        tags=metadata.tags,
        custom_metadata=metadata.custom_metadata,
        created_at=metadata.created_at.isoformat() if metadata.created_at else "",
        updated_at=metadata.updated_at.isoformat() if metadata.updated_at else None
    )


@router.put("/files/{file_id}/metadata", response_model=FileMetadataResponse)
def update_file_metadata(
    file_id: int,
    metadata_request: FileMetadataRequest = Body(...),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create or update metadata for a file
    """
    # Verify file exists and belongs to user
    file = db.query(File).filter(
        and_(
            File.id == file_id,
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    ).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable"
        )

    # Get or create metadata
    metadata = db.query(FileMetadata).filter(
        FileMetadata.file_id == file_id
    ).first()

    if metadata:
        # Update existing metadata
        if metadata_request.description is not None:
            metadata.description = metadata_request.description
        if metadata_request.tags is not None:
            metadata.tags = metadata_request.tags
        if metadata_request.custom_metadata is not None:
            metadata.custom_metadata = metadata_request.custom_metadata
    else:
        # Create new metadata
        metadata = FileMetadata(
            file_id=file_id,
            description=metadata_request.description,
            tags=metadata_request.tags,
            custom_metadata=metadata_request.custom_metadata
        )
        db.add(metadata)

    db.commit()
    db.refresh(metadata)

    return FileMetadataResponse(
        id=metadata.id,
        file_id=metadata.file_id,
        description=metadata.description,
        tags=metadata.tags,
        custom_metadata=metadata.custom_metadata,
        created_at=metadata.created_at.isoformat() if metadata.created_at else "",
        updated_at=metadata.updated_at.isoformat() if metadata.updated_at else None
    )


@router.delete("/files/{file_id}/metadata", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_metadata(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Delete metadata for a file
    """
    # Verify file exists and belongs to user
    file = db.query(File).filter(
        and_(
            File.id == file_id,
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    ).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable"
        )

    metadata = db.query(FileMetadata).filter(
        FileMetadata.file_id == file_id
    ).first()

    if metadata:
        db.delete(metadata)
        db.commit()

    return None

