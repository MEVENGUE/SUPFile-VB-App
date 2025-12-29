"""
File management endpoints: upload, download, list, delete
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import validate_file_extension, validate_file_size
from app.core.middleware import get_current_user_id
from app.core.config import settings
from app.models.file import File
from app.models.user import User
from app.services.azure_blob import azure_blob_service
import io

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
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """File list response schema"""
    files: List[FileResponse]
    total: int


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Upload a file to Azure Blob Storage
    """
    # Validate file extension
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed extensions: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size
    if not validate_file_size(len(file_content)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Generate blob name
    blob_name = azure_blob_service.generate_blob_name(
        current_user_id,
        file.filename
    )
    
    # Upload to Azure Blob Storage
    try:
        blob_url = azure_blob_service.upload_file(
            file_content=file_content,
            blob_name=blob_name,
            content_type=file.content_type,
            metadata={
                "user_id": str(current_user_id),
                "original_filename": file.filename,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file to storage: {str(e)}"
        )
    
    # Save metadata to database
    db_file = File(
        user_id=current_user_id,
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
        upload_region=db_file.upload_region
    )


@router.get("/", response_model=FileListResponse)
async def list_files(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    List all files for the current user
    """
    files = db.query(File).filter(
        File.user_id == current_user_id
    ).offset(skip).limit(limit).all()
    
    total = db.query(File).filter(File.user_id == current_user_id).count()
    
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
        upload_region=file.upload_region
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
        file_content = azure_blob_service.download_file(file.blob_name)
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
    Delete a file from Azure Blob Storage and database
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
    
    # Delete from Azure Blob Storage
    try:
        azure_blob_service.delete_file(file.blob_name)
    except Exception as e:
        # Log error but continue with database deletion
        print(f"Error deleting file from storage: {e}")
    
    # Delete from database
    db.delete(file)
    db.commit()
    
    return None

