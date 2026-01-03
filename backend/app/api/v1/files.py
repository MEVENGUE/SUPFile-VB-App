"""
File management endpoints: upload, download, list, delete
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Form, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import validate_file_extension, validate_file_size
from app.core.middleware import get_current_user_id
from app.core.config import settings
from app.models.file import File
from app.models.user import User
from app.services.azure_blob import get_azure_blob_service
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class FileResponse(BaseModel):
    """File metadata response schema"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    created_at: str
    upload_region: str = None
    deleted_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """File list response schema"""
    files: List[FileResponse]
    total: int


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    folder_id: Optional[int] = Form(None),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Upload a file to Azure Blob Storage
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    # Extract extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "none"
    
    # Debug logging
    logger.info(f"File upload attempt: {file.filename}, extension: '{ext}'")
    logger.info(f"Allowed extensions list: {settings.allowed_extensions_list}")
    logger.info(f"Is '{ext}' in list? {ext in settings.allowed_extensions_list}")
    
    if not validate_file_extension(file.filename):
        logger.warning(f"File upload rejected: extension '{ext}' not allowed. Filename: {file.filename}")
        logger.warning(f"Allowed extensions: {settings.ALLOWED_EXTENSIONS}")
        logger.warning(f"Parsed extensions list: {settings.allowed_extensions_list}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Extension '{ext}' is not in the allowed list. Allowed extensions: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size
    if not validate_file_size(len(file_content)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Validate folder_id if provided
    if folder_id is not None:
        from app.models.folder import Folder
        from sqlalchemy import and_
        folder = db.query(Folder).filter(
            and_(
                Folder.id == folder_id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable"
            )
    
    # Generate blob name
    blob_service = get_azure_blob_service()
    if not blob_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure Blob Storage is not configured. Please configure Azure Storage credentials."
        )
    
    blob_name = blob_service.generate_blob_name(
        current_user_id,
        file.filename
    )
    
    # Upload to Azure Blob Storage
    try:
        blob_url = blob_service.upload_file(
            file_content=file_content,
            blob_name=blob_name,
            content_type=file.content_type,
            metadata={
                "user_id": str(current_user_id),
                "original_filename": file.filename,
            }
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error uploading file to Azure Blob Storage: {str(e)}\n{error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file to storage: {str(e)}"
        )
    
    # Save metadata to database
    db_file = File(
        user_id=current_user_id,
        folder_id=folder_id,
        filename=blob_name,
        original_filename=file.filename,
        file_size=len(file_content),
        content_type=file.content_type,
        blob_name=blob_name,
        blob_url=blob_url,
        upload_region=settings.AZURE_PRIMARY_REGION,
        is_public=False
    )
    
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return FileResponse(
        id=db_file.id,
        filename=db_file.filename,
        original_filename=db_file.original_filename,
        file_size=db_file.file_size,
        content_type=db_file.content_type,
        created_at=db_file.created_at.isoformat(),
        upload_region=db_file.upload_region,
        deleted_at=db_file.deleted_at.isoformat() if db_file.deleted_at else None
    )


@router.get("/", response_model=FileListResponse)
async def list_files(
    folder_id: Optional[int] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List all files for the current user
    If folder_id is provided, returns only files in that folder
    If folder_id is None, returns files in root (no folder)
    """
    from sqlalchemy import and_
    
    query = db.query(File).filter(
        and_(
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    )
    
    if folder_id is None:
        # Get root files (no folder)
        query = query.filter(File.folder_id.is_(None))
    else:
        # Verify folder belongs to user
        from app.models.folder import Folder
        folder = db.query(Folder).filter(
            and_(
                Folder.id == folder_id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable"
            )
        
        query = query.filter(File.folder_id == folder_id)
    
    files = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return FileListResponse(
        files=[
            FileResponse(
                id=f.id,
                filename=f.filename,
                original_filename=f.original_filename,
                file_size=f.file_size,
                content_type=f.content_type,
                created_at=f.created_at.isoformat(),
                upload_region=f.upload_region
            )
            for f in files
        ],
        total=total
    )


@router.get("/search", response_model=FileListResponse)
async def search_files(
    q: str = Query(..., description="Search query (filename or content type)"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    folder_id: Optional[int] = Query(None, description="Filter by folder ID"),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Search files by name or content type
    Supports partial matching on filename
    """
    from sqlalchemy import and_
    
    # Base query: user's files, not deleted
    query = db.query(File).filter(
        and_(
            File.user_id == current_user_id,
            File.deleted_at.is_(None)
        )
    )
    
    # Search by filename (case-insensitive partial match)
    search_term = f"%{q}%"
    query = query.filter(
        or_(
            File.original_filename.ilike(search_term),
            File.filename.ilike(search_term)
        )
    )
    
    # Filter by content type if provided
    if content_type:
        query = query.filter(File.content_type.ilike(f"%{content_type}%"))
    
    # Filter by folder if provided
    if folder_id is not None:
        if folder_id == 0:
            # Search in root (no folder)
            query = query.filter(File.folder_id.is_(None))
        else:
            # Verify folder belongs to user
            from app.models.folder import Folder
            folder = db.query(Folder).filter(
                and_(
                    Folder.id == folder_id,
                    Folder.user_id == current_user_id,
                    Folder.deleted_at.is_(None)
                )
            ).first()
            
            if not folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dossier introuvable"
                )
            
            query = query.filter(File.folder_id == folder_id)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    files = query.order_by(File.created_at.desc()).offset(skip).limit(limit).all()
    
    return FileListResponse(
        files=[
            FileResponse(
                id=f.id,
                filename=f.filename,
                original_filename=f.original_filename,
                file_size=f.file_size,
                content_type=f.content_type,
                created_at=f.created_at.isoformat(),
                upload_region=f.upload_region,
                deleted_at=f.deleted_at.isoformat() if f.deleted_at else None
            )
            for f in files
        ],
        total=total
    )


@router.get("/trash", response_model=FileListResponse)
async def list_trash_files(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List all deleted files (trash) for the current user
    """
    files = db.query(File).filter(
        and_(
            File.user_id == current_user_id,
            File.deleted_at.isnot(None)
        )
    ).order_by(File.deleted_at.desc()).offset(skip).limit(limit).all()
    
    total = db.query(File).filter(
        and_(
            File.user_id == current_user_id,
            File.deleted_at.isnot(None)
        )
    ).count()
    
    return FileListResponse(
        files=[
            FileResponse(
                id=f.id,
                filename=f.filename,
                original_filename=f.original_filename,
                file_size=f.file_size,
                content_type=f.content_type,
                created_at=f.created_at.isoformat(),
                upload_region=f.upload_region,
                deleted_at=f.deleted_at.isoformat() if f.deleted_at else None
            )
            for f in files
        ],
        total=total
    )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get file metadata by ID
    """
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == current_user_id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(
        id=file.id,
        filename=file.filename,
        original_filename=file.original_filename,
        file_size=file.file_size,
        content_type=file.content_type,
        created_at=file.created_at.isoformat(),
        upload_region=file.upload_region,
        deleted_at=file.deleted_at.isoformat() if file.deleted_at else None
    )


@router.get("/{file_id}/preview")
async def preview_file(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get a preview URL for a file (SAS URL with 1 hour expiry)
    Returns a temporary URL that can be used to preview the file directly
    """
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == current_user_id,
        File.deleted_at.is_(None)
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Generate SAS URL for preview (1 hour expiry)
    try:
        blob_service = get_azure_blob_service()
        if not blob_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Azure Blob Storage is not configured."
            )
        preview_url = blob_service.generate_sas_url(file.blob_name, expiry_minutes=60)
        
        return {
            "preview_url": preview_url,
            "content_type": file.content_type,
            "filename": file.original_filename
        }
    except Exception as e:
        logger.error(f"Error generating preview URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating preview URL: {str(e)}"
        )


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Download a file from Azure Blob Storage
    """
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == current_user_id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Download from Azure Blob Storage
    try:
        blob_service = get_azure_blob_service()
        if not blob_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Azure Blob Storage is not configured."
            )
        file_content = blob_service.download_file(file.blob_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file from storage: {str(e)}"
        )
    
    # Return file as streaming response
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=file.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file.original_filename}"'
        }
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Soft delete a file (move to trash)
    The file is not actually deleted, just marked as deleted
    Use /files/{id}/permanent to permanently delete
    """
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == current_user_id,
        File.deleted_at.is_(None)  # Only delete if not already deleted
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Soft delete: set deleted_at timestamp
    file.deleted_at = datetime.now(timezone.utc)
    db.commit()
    
    return None


@router.post("/{file_id}/restore", response_model=FileResponse)
async def restore_file(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Restore a deleted file from trash
    """
    file = db.query(File).filter(
        and_(
            File.id == file_id,
            File.user_id == current_user_id,
            File.deleted_at.isnot(None)
        )
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable dans la corbeille"
        )
    
    # Check if parent folder exists and is not deleted
    if file.folder_id is not None:
        from app.models.folder import Folder
        parent_folder = db.query(Folder).filter(
            and_(
                Folder.id == file.folder_id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        # If parent folder is deleted, restore file to root (folder_id = None)
        if not parent_folder:
            file.folder_id = None
    
    # Check if a file with the same name exists in the same folder (or root)
    existing_file = db.query(File).filter(
        and_(
            File.user_id == current_user_id,
            File.folder_id == file.folder_id,
            File.original_filename == file.original_filename,
            File.id != file_id,
            File.deleted_at.is_(None)
        )
    ).first()
    
    if existing_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un fichier avec ce nom existe déjà dans l'emplacement d'origine"
        )
    
    # Restore file (set deleted_at to None)
    file.deleted_at = None
    db.commit()
    db.refresh(file)
    
    return FileResponse(
        id=file.id,
        filename=file.filename,
        original_filename=file.original_filename,
        file_size=file.file_size,
        content_type=file.content_type,
        created_at=file.created_at.isoformat(),
        upload_region=file.upload_region,
        deleted_at=file.deleted_at.isoformat() if file.deleted_at else None
    )


@router.delete("/{file_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_permanent(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Permanently delete a file from trash
    This will also delete the file from Azure Blob Storage
    """
    file = db.query(File).filter(
        and_(
            File.id == file_id,
            File.user_id == current_user_id,
            File.deleted_at.isnot(None)  # Only delete files that are already in trash
        )
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable dans la corbeille"
        )
    
    # Delete from Azure Blob Storage
    try:
        blob_service = get_azure_blob_service()
        if blob_service:
            blob_service.delete_file(file.blob_name)
    except Exception as e:
        logger.error(f"Error deleting file from Azure Blob Storage: {str(e)}")
        # Continue with database deletion even if blob deletion fails
    
    # Delete from database
    db.delete(file)
    db.commit()
    
    return None

