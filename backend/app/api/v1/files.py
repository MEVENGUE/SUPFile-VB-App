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
from pathlib import Path
import shutil
import tempfile
import uuid
from app.core.database import get_db
from app.core.security import validate_file_extension, validate_file_size
from app.core.middleware import get_current_user_id
from app.core.config import settings
from app.models.file import File
from app.models.user import User
from app.services.storage_service import get_storage_service
from app.core.security import verify_token
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


class ChunkInitResponse(BaseModel):
    upload_id: str
    chunk_size: int


class ChunkUploadResponse(BaseModel):
    upload_id: str
    chunk_index: int
    received: bool
    bytes_written: int


class ChunkCompleteRequest(BaseModel):
    upload_id: str
    total_chunks: int
    filename: str
    content_type: Optional[str] = None
    folder_id: Optional[int] = None


def _get_chunk_dir(upload_id: str, user_id: int) -> Path:
    base = Path(settings.CHUNK_TMP_PATH).resolve()
    chunk_dir = (base / str(user_id) / upload_id).resolve()
    if not str(chunk_dir).startswith(str(base)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload id")
    chunk_dir.mkdir(parents=True, exist_ok=True)
    return chunk_dir


def _stream_upload_to_tempfile(file: UploadFile) -> Path:
    temp_dir = Path(settings.CHUNK_TMP_PATH).resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_path = temp_dir / f"upload-{uuid.uuid4().hex}.tmp"
    total_size = 0
    with temp_path.open("wb") as out_file:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if not validate_file_size(total_size):
                out_file.close()
                temp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File size exceeds maximum allowed size: {settings.MAX_FILE_SIZE_MB}MB",
                )
            out_file.write(chunk)

    return temp_path


def _save_file_record(
    *,
    file_path: Path,
    filename: str,
    content_type: Optional[str],
    folder_id: Optional[int],
    current_user_id: int,
    db: Session,
) -> FileResponse:
    storage = get_storage_service()
    if not storage:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stockage non configuré. Vérifier STORAGE_BACKEND et UPLOAD_PATH (ou Azure).",
        )

    blob_name = storage.generate_blob_name(current_user_id, filename)
    blob_url = None
    try:
        blob_url = storage.upload_file(
            file_path=file_path,
            blob_name=blob_name,
            content_type=content_type,
            metadata={
                "user_id": str(current_user_id),
                "original_filename": filename,
            },
        )

        db_file = File(
            user_id=current_user_id,
            folder_id=folder_id,
            filename=blob_name,
            original_filename=filename,
            file_size=file_path.stat().st_size,
            content_type=content_type,
            blob_name=blob_name,
            blob_url=blob_url,
            upload_region=settings.UPLOAD_REGION,
            is_public=False,
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
            deleted_at=db_file.deleted_at.isoformat() if db_file.deleted_at else None,
        )
    except Exception as e:
        db.rollback()
        if blob_url and storage:
            try:
                storage.delete_file(blob_name)
            except Exception:
                logger.warning("Failed to delete orphaned blob after DB error: %s", blob_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'enregistrement du fichier."
        )


@router.post("/upload/init", response_model=ChunkInitResponse)
async def init_chunk_upload(current_user_id: int = Depends(get_current_user_id)):
    if not settings.CHUNK_UPLOAD_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk upload disabled")
    upload_id = f"u{current_user_id}-{datetime.utcnow().timestamp():.0f}"
    _get_chunk_dir(upload_id, current_user_id)
    return ChunkInitResponse(upload_id=upload_id, chunk_size=settings.chunk_size_bytes)


@router.post("/upload/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(..., ge=0),
    chunk: UploadFile = FastAPIFile(...),
    current_user_id: int = Depends(get_current_user_id),
):
    if not settings.CHUNK_UPLOAD_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk upload disabled")

    data = await chunk.read()
    if len(data) > settings.chunk_size_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chunk too large")

    chunk_dir = _get_chunk_dir(upload_id, current_user_id)
    chunk_path = chunk_dir / f"{chunk_index}.part"
    chunk_path.write_bytes(data)
    return ChunkUploadResponse(
        upload_id=upload_id, chunk_index=chunk_index, received=True, bytes_written=len(data)
    )


@router.post("/upload/complete", response_model=FileResponse)
async def complete_chunk_upload(
    payload: ChunkCompleteRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not settings.CHUNK_UPLOAD_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk upload disabled")
    if not validate_file_extension(payload.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")

    chunk_dir = _get_chunk_dir(payload.upload_id, current_user_id)
    temp_path = Path(settings.CHUNK_TMP_PATH).resolve() / f"{payload.upload_id}-complete.tmp"
    temp_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with temp_path.open("wb") as out_file:
            for idx in range(payload.total_chunks):
                part = chunk_dir / f"{idx}.part"
                if not part.is_file():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing chunk {idx}")
                with part.open("rb") as part_file:
                    shutil.copyfileobj(part_file, out_file)

        if not validate_file_size(temp_path.stat().st_size):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size: {settings.MAX_FILE_SIZE_MB}MB",
            )

        response = _save_file_record(
            file_path=temp_path,
            filename=payload.filename,
            content_type=payload.content_type,
            folder_id=payload.folder_id,
            current_user_id=current_user_id,
            db=db,
        )

        return response
    finally:
        shutil.rmtree(chunk_dir, ignore_errors=True)
        temp_path.unlink(missing_ok=True)


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    folder_id: Optional[int] = Form(None),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Upload a file to storage (GlusterFS/local or Azure) using streaming to temporary disk.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "none"

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

    temp_path = _stream_upload_to_tempfile(file)

    try:
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

        return _save_file_record(
            file_path=temp_path,
            filename=file.filename,
            content_type=file.content_type,
            folder_id=folder_id,
            current_user_id=current_user_id,
            db=db,
        )
    finally:
        temp_path.unlink(missing_ok=True)


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
    URL de prévisualisation (SAS Azure ou jeton court pour stockage local/GlusterFS)
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
    
    try:
        storage = get_storage_service()
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stockage non configuré.",
            )
        preview_url = storage.get_preview_url(file.id, current_user_id, file.blob_name)
        return {
            "preview_url": preview_url,
            "content_type": file.content_type,
            "filename": file.original_filename,
        }
    except Exception as e:
        logger.error(f"Error generating preview URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating preview URL: {str(e)}",
        )


@router.get("/{file_id}/preview/content")
async def preview_file_content(
    file_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Flux de prévisualisation avec jeton court (stockage local / GlusterFS)."""
    payload = verify_token(token, token_type="preview")
    if not payload or payload.get("file_id") != file_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    user_id = int(payload.get("sub"))
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == user_id,
        File.deleted_at.is_(None),
    ).first()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    storage = get_storage_service()
    if not storage:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stockage indisponible")

    try:
        content = storage.download_file(file.blob_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading file: {str(e)}",
        )

    return StreamingResponse(
        io.BytesIO(content),
        media_type=file.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{file.original_filename}"'},
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Download a file from storage
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
    
    try:
        storage = get_storage_service()
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stockage non configuré.",
            )
        file_content = storage.download_file(file.blob_name)
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
    Supprime aussi le fichier du stockage (GlusterFS/local ou Azure)
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
    
    try:
        storage = get_storage_service()
        if storage:
            storage.delete_file(file.blob_name)
    except Exception as e:
        logger.error(f"Error deleting file from storage: {str(e)}")
        # Continue with database deletion even if blob deletion fails
    
    # Delete from database
    db.delete(file)
    db.commit()
    
    return None

