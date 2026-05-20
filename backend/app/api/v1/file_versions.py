"""
File versioning endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.core.middleware import get_current_user_id
from app.models.file import File
from app.models.file_version import FileVersion
from app.services.storage_service import get_storage_service
from fastapi.responses import StreamingResponse
import logging
import io

logger = logging.getLogger(__name__)

router = APIRouter()


class FileVersionResponse(BaseModel):
    id: int
    file_id: int
    version_number: int
    file_size: int
    content_type: Optional[str]
    created_by: int
    change_description: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.post("/files/{file_id}/versions", response_model=FileVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_file_version(
    file_id: int,
    change_description: Optional[str] = Query(None),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create a new version of a file (save current state as a version)
    """
    # Get the file
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

    # Get the highest version number
    max_version = db.query(FileVersion).filter(
        FileVersion.file_id == file_id
    ).order_by(desc(FileVersion.version_number)).first()

    next_version = (max_version.version_number + 1) if max_version else 1

    # Copy current file to a new blob for versioning
    blob_service = get_storage_service()
    if not blob_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service de stockage non disponible"
        )

    try:
        # Download current file
        current_file_content = blob_service.download_file(file.blob_name)
        
        # Create new blob name for version
        version_blob_name = f"{file.blob_name}_v{next_version}"
        
        # Upload as new version
        blob_service.upload_file(
            file_content=current_file_content,
            blob_name=version_blob_name,
            content_type=file.content_type
        )

        # Create version record
        file_version = FileVersion(
            file_id=file_id,
            version_number=next_version,
            blob_name=version_blob_name,
            file_size=file.file_size,
            content_type=file.content_type,
            created_by=current_user_id,
            change_description=change_description
        )

        db.add(file_version)
        db.commit()
        db.refresh(file_version)

        return FileVersionResponse(
            id=file_version.id,
            file_id=file_version.file_id,
            version_number=file_version.version_number,
            file_size=file_version.file_size,
            content_type=file_version.content_type,
            created_by=file_version.created_by,
            change_description=file_version.change_description,
            created_at=file_version.created_at.isoformat() if file_version.created_at else ""
        )
    except Exception as e:
        logger.error(f"Error creating file version: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de la version: {str(e)}"
        )


@router.get("/files/{file_id}/versions", response_model=List[FileVersionResponse])
def list_file_versions(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    List all versions of a file
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

    versions = db.query(FileVersion).filter(
        FileVersion.file_id == file_id
    ).order_by(desc(FileVersion.version_number)).all()

    return [
        FileVersionResponse(
            id=v.id,
            file_id=v.file_id,
            version_number=v.version_number,
            file_size=v.file_size,
            content_type=v.content_type,
            created_by=v.created_by,
            change_description=v.change_description,
            created_at=v.created_at.isoformat() if v.created_at else ""
        )
        for v in versions
    ]


@router.get("/files/{file_id}/versions/{version_id}/download")
async def download_file_version(
    file_id: int,
    version_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Download a specific version of a file
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

    # Get the version
    version = db.query(FileVersion).filter(
        and_(
            FileVersion.id == version_id,
            FileVersion.file_id == file_id
        )
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version introuvable"
        )

    blob_service = get_storage_service()
    if not blob_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service de stockage non disponible"
        )

    try:
        file_content = blob_service.download_file(version.blob_name)
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=version.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{file.original_filename}_v{version.version_number}"'
            }
        )
    except Exception as e:
        logger.error(f"Error downloading file version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du téléchargement: {str(e)}"
        )


@router.post("/files/{file_id}/versions/{version_id}/restore", response_model=dict)
async def restore_file_version(
    file_id: int,
    version_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Restore a file to a specific version (creates a new version of current state first)
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

    # Get the version to restore
    version = db.query(FileVersion).filter(
        and_(
            FileVersion.id == version_id,
            FileVersion.file_id == file_id
        )
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version introuvable"
        )

    blob_service = get_storage_service()
    if not blob_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service de stockage non disponible"
        )

    try:
        # First, save current state as a version
        max_version = db.query(FileVersion).filter(
            FileVersion.file_id == file_id
        ).order_by(desc(FileVersion.version_number)).first()
        next_version = (max_version.version_number + 1) if max_version else 1

        current_file_content = blob_service.download_file(file.blob_name)
        version_blob_name = f"{file.blob_name}_v{next_version}"
        blob_service.upload_file(
            file_content=current_file_content,
            blob_name=version_blob_name,
            content_type=file.content_type
        )

        backup_version = FileVersion(
            file_id=file_id,
            version_number=next_version,
            blob_name=version_blob_name,
            file_size=file.file_size,
            content_type=file.content_type,
            created_by=current_user_id,
            change_description=f"Backup avant restauration de la version {version.version_number}"
        )
        db.add(backup_version)

        # Now restore the version
        version_content = blob_service.download_file(version.blob_name)
        blob_service.upload_file(
            file_content=version_content,
            blob_name=file.blob_name,
            content_type=version.content_type
        )

        # Update file metadata
        file.file_size = version.file_size
        file.content_type = version.content_type
        file.updated_at = datetime.utcnow()

        db.commit()

        return {
            "message": f"Fichier restauré à la version {version.version_number}",
            "backup_version": next_version
        }
    except Exception as e:
        logger.error(f"Error restoring file version: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la restauration: {str(e)}"
        )

