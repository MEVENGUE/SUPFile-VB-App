"""
Folder management endpoints: create, list, update, delete
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.sql import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.middleware import get_current_user_id
from app.models.folder import Folder
from app.models.file import File
from app.services.storage_service import get_storage_service
import logging
import zipfile
import io

logger = logging.getLogger(__name__)

router = APIRouter()


class FolderCreate(BaseModel):
    """Folder creation schema"""
    name: str
    parent_id: Optional[int] = None


class FolderUpdate(BaseModel):
    """Folder update schema"""
    name: Optional[str] = None
    parent_id: Optional[int] = None

class FolderRenameRequest(BaseModel):
    """Request model for renaming a folder"""
    new_name: str

class FolderMoveRequest(BaseModel):
    """Request model for moving a folder"""
    parent_id: Optional[int] = None  # None = root, or folder ID


class FolderResponse(BaseModel):
    """Folder response schema"""
    id: int
    name: str
    user_id: int
    parent_id: Optional[int] = None
    created_at: str
    updated_at: Optional[str] = None
    children_count: int = 0
    files_count: int = 0
    
    class Config:
        from_attributes = True


class FolderListResponse(BaseModel):
    """Folder list response schema"""
    folders: List[FolderResponse]
    total: int


@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_data: FolderCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create a new folder
    """
    # Validate folder name
    if not folder_data.name or not folder_data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nom du dossier ne peut pas être vide"
        )
    
    # Check if parent folder exists and belongs to user
    if folder_data.parent_id:
        parent_folder = db.query(Folder).filter(
            and_(
                Folder.id == folder_data.parent_id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if not parent_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier parent introuvable"
            )
    
    # Check if folder with same name already exists in same parent
    existing_folder = db.query(Folder).filter(
        and_(
            Folder.name == folder_data.name.strip(),
            Folder.user_id == current_user_id,
            Folder.parent_id == folder_data.parent_id,
            Folder.deleted_at.is_(None)
        )
    ).first()
    
    if existing_folder:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un dossier avec ce nom existe déjà dans ce répertoire"
        )
    
    # Create folder
    new_folder = Folder(
        name=folder_data.name.strip(),
        user_id=current_user_id,
        parent_id=folder_data.parent_id
    )
    
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)
    
    # Get counts
    children_count = db.query(Folder).filter(
        and_(
            Folder.parent_id == new_folder.id,
            Folder.deleted_at.is_(None)
        )
    ).count()
    
    files_count = db.query(File).filter(
        and_(
            File.folder_id == new_folder.id,
            File.deleted_at.is_(None)
        )
    ).count()
    
    response = FolderResponse(
        id=new_folder.id,
        name=new_folder.name,
        user_id=new_folder.user_id,
        parent_id=new_folder.parent_id,
        created_at=new_folder.created_at.isoformat() if new_folder.created_at else "",
        updated_at=new_folder.updated_at.isoformat() if new_folder.updated_at else None,
        children_count=children_count,
        files_count=files_count
    )
    
    return response


@router.get("/", response_model=FolderListResponse)
def list_folders(
    parent_id: Optional[int] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List folders for the current user
    If parent_id is provided, returns only children of that folder
    If parent_id is None, returns root folders (folders without parent)
    """
    query = db.query(Folder).filter(
        and_(
            Folder.user_id == current_user_id,
            Folder.deleted_at.is_(None)
        )
    )
    
    if parent_id is None:
        # Get root folders (no parent)
        query = query.filter(Folder.parent_id.is_(None))
    else:
        # Verify parent belongs to user
        parent = db.query(Folder).filter(
            and_(
                Folder.id == parent_id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier parent introuvable"
            )
        
        query = query.filter(Folder.parent_id == parent_id)
    
    total = query.count()
    folders = query.offset(skip).limit(limit).all()
    
    # Optimize: Get all counts in batch to avoid N+1 queries
    if folders:
        folder_ids = [folder.id for folder in folders]
        
        # Get all children counts in one query
        from sqlalchemy import func
        children_counts = db.query(
            Folder.parent_id,
            func.count(Folder.id).label('count')
        ).filter(
            and_(
                Folder.parent_id.in_(folder_ids),
                Folder.deleted_at.is_(None)
            )
        ).group_by(Folder.parent_id).all()
        
        # Get all files counts in one query
        files_counts = db.query(
            File.folder_id,
            func.count(File.id).label('count')
        ).filter(
            and_(
                File.folder_id.in_(folder_ids),
                File.deleted_at.is_(None)
            )
        ).group_by(File.folder_id).all()
        
        # Create lookup dictionaries
        children_count_map = {parent_id: count for parent_id, count in children_counts}
        files_count_map = {folder_id: count for folder_id, count in files_counts}
    else:
        children_count_map = {}
        files_count_map = {}
    
    # Build responses with pre-calculated counts
    folder_responses = []
    for folder in folders:
        children_count = children_count_map.get(folder.id, 0)
        files_count = files_count_map.get(folder.id, 0)
        
        folder_responses.append(FolderResponse(
            id=folder.id,
            name=folder.name,
            user_id=folder.user_id,
            parent_id=folder.parent_id,
            created_at=folder.created_at.isoformat() if folder.created_at else "",
            updated_at=folder.updated_at.isoformat() if folder.updated_at else None,
            children_count=children_count,
            files_count=files_count
        ))
    
    return FolderListResponse(folders=folder_responses, total=total)


@router.get("/trash", response_model=FolderListResponse)
def list_trash_folders(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List all deleted folders (trash) for the current user
    """
    folders = db.query(Folder).filter(
        and_(
            Folder.user_id == current_user_id,
            Folder.deleted_at.isnot(None)
        )
    ).order_by(Folder.deleted_at.desc()).offset(skip).limit(limit).all()
    
    total = db.query(Folder).filter(
        and_(
            Folder.user_id == current_user_id,
            Folder.deleted_at.isnot(None)
        )
    ).count()
    
    # Get counts for each folder (including deleted children and files)
    folder_responses = []
    for folder in folders:
        # Count deleted children
        children_count = db.query(Folder).filter(
            and_(
                Folder.parent_id == folder.id,
                Folder.deleted_at.isnot(None)
            )
        ).count()
        
        # Count deleted files
        files_count = db.query(File).filter(
            and_(
                File.folder_id == folder.id,
                File.deleted_at.isnot(None)
            )
        ).count()
        
        folder_responses.append(FolderResponse(
            id=folder.id,
            name=folder.name,
            user_id=folder.user_id,
            parent_id=folder.parent_id,
            created_at=folder.created_at.isoformat() if folder.created_at else "",
            updated_at=folder.updated_at.isoformat() if folder.updated_at else None,
            children_count=children_count,
            files_count=files_count
        ))
    
    return FolderListResponse(folders=folder_responses, total=total)


@router.get("/{folder_id}", response_model=FolderResponse)
def get_folder(
    folder_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get a specific folder by ID
    """
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
    
    # Get counts
    children_count = db.query(Folder).filter(
        and_(
            Folder.parent_id == folder.id,
            Folder.deleted_at.is_(None)
        )
    ).count()
    
    files_count = db.query(File).filter(
        and_(
            File.folder_id == folder.id,
            File.deleted_at.is_(None)
        )
    ).count()
    
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        user_id=folder.user_id,
        parent_id=folder.parent_id,
        created_at=folder.created_at.isoformat() if folder.created_at else "",
        updated_at=folder.updated_at.isoformat() if folder.updated_at else None,
        children_count=children_count,
        files_count=files_count
    )


@router.patch("/{folder_id}/rename", response_model=FolderResponse)
def rename_folder(
    folder_id: int,
    rename_request: FolderRenameRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Rename a folder
    """
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
    
    # Validate new name
    if not rename_request.new_name or not rename_request.new_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nom du dossier ne peut pas être vide"
        )
    
    # Check if folder with same name already exists in same parent
    existing_folder = db.query(Folder).filter(
        and_(
            Folder.name == rename_request.new_name.strip(),
            Folder.user_id == current_user_id,
            Folder.parent_id == folder.parent_id,
            Folder.id != folder_id,
            Folder.deleted_at.is_(None)
        )
    ).first()
    
    if existing_folder:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un dossier avec ce nom existe déjà dans ce répertoire"
        )
    
    # Update name
    folder.name = rename_request.new_name.strip()
    db.commit()
    db.refresh(folder)
    
    # Get counts
    children_count = db.query(Folder).filter(
        and_(
            Folder.parent_id == folder.id,
            Folder.deleted_at.is_(None)
        )
    ).count()
    
    files_count = db.query(File).filter(
        and_(
            File.folder_id == folder.id,
            File.deleted_at.is_(None)
        )
    ).count()
    
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        user_id=folder.user_id,
        parent_id=folder.parent_id,
        created_at=folder.created_at.isoformat() if folder.created_at else "",
        updated_at=folder.updated_at.isoformat() if folder.updated_at else None,
        children_count=children_count,
        files_count=files_count
    )


@router.patch("/{folder_id}/move", response_model=FolderResponse)
def move_folder(
    folder_id: int,
    move_request: FolderMoveRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Move a folder to another parent (or root if parent_id is None)
    """
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
    
    # Prevent moving folder into itself
    if move_request.parent_id == folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un dossier ne peut pas être déplacé dans lui-même"
        )
    
    # Check if trying to move into a child (would create cycle)
    def is_descendant(parent_id: int, child_id: int, db: Session) -> bool:
        """Check if child_id is a descendant of parent_id"""
        current = db.query(Folder).filter(Folder.id == child_id).first()
        while current and current.parent_id:
            if current.parent_id == parent_id:
                return True
            current = db.query(Folder).filter(Folder.id == current.parent_id).first()
        return False
    
    if move_request.parent_id is not None and is_descendant(folder_id, move_request.parent_id, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un dossier ne peut pas être déplacé dans un de ses sous-dossiers"
        )
    
    # If moving to a folder, verify it exists and belongs to user
    if move_request.parent_id is not None:
        target_folder = db.query(Folder).filter(
            and_(
                Folder.id == move_request.parent_id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if not target_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier parent introuvable"
            )
        
        # Check if folder with same name already exists in target parent
        existing_folder = db.query(Folder).filter(
            and_(
                Folder.name == folder.name,
                Folder.user_id == current_user_id,
                Folder.parent_id == move_request.parent_id,
                Folder.id != folder_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if existing_folder:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un dossier avec ce nom existe déjà dans le dossier parent"
            )
    
    # Update parent_id
    folder.parent_id = move_request.parent_id
    db.commit()
    db.refresh(folder)
    
    # Get counts
    children_count = db.query(Folder).filter(
        and_(
            Folder.parent_id == folder.id,
            Folder.deleted_at.is_(None)
        )
    ).count()
    
    files_count = db.query(File).filter(
        and_(
            File.folder_id == folder.id,
            File.deleted_at.is_(None)
        )
    ).count()
    
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        user_id=folder.user_id,
        parent_id=folder.parent_id,
        created_at=folder.created_at.isoformat() if folder.created_at else "",
        updated_at=folder.updated_at.isoformat() if folder.updated_at else None,
        children_count=children_count,
        files_count=files_count
    )


@router.post("/{folder_id}/restore", response_model=FolderResponse)
def restore_folder(
    folder_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Restore a deleted folder from trash
    """
    folder = db.query(Folder).filter(
        and_(
            Folder.id == folder_id,
            Folder.user_id == current_user_id,
            Folder.deleted_at.isnot(None)
        )
    ).first()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable dans la corbeille"
        )
    
    # Check if a folder with the same name exists in the original location
    existing_folder = db.query(Folder).filter(
        and_(
            Folder.user_id == current_user_id,
            Folder.parent_id == folder.parent_id,
            Folder.name == folder.name,
            Folder.id != folder_id,
            Folder.deleted_at.is_(None)
        )
    ).first()
    
    if existing_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un dossier avec ce nom existe déjà dans l'emplacement d'origine"
        )
    
    # Check if parent folder exists and is not deleted
    if folder.parent_id is not None:
        parent = db.query(Folder).filter(
            and_(
                Folder.id == folder.parent_id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        # If parent is deleted, restore to root (parent_id = None)
        if not parent:
            folder.parent_id = None
    
    # Restore folder (set deleted_at to None)
    folder.deleted_at = None
    db.commit()
    db.refresh(folder)
    
    # Get counts
    children_count = db.query(Folder).filter(
        and_(
            Folder.parent_id == folder.id,
            Folder.deleted_at.is_(None)
        )
    ).count()
    
    files_count = db.query(File).filter(
        and_(
            File.folder_id == folder.id,
            File.deleted_at.is_(None)
        )
    ).count()
    
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        user_id=folder.user_id,
        parent_id=folder.parent_id,
        created_at=folder.created_at.isoformat() if folder.created_at else "",
        updated_at=folder.updated_at.isoformat() if folder.updated_at else None,
        children_count=children_count,
        files_count=files_count
    )


@router.put("/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: int,
    folder_data: FolderUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update a folder (rename or move)
    """
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
    
    # Update name if provided
    if folder_data.name is not None:
        if not folder_data.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nom du dossier ne peut pas être vide"
            )
        
        # Check if name already exists in same parent
        existing_folder = db.query(Folder).filter(
            and_(
                Folder.name == folder_data.name.strip(),
                Folder.user_id == current_user_id,
                Folder.parent_id == folder.parent_id,
                Folder.id != folder_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if existing_folder:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un dossier avec ce nom existe déjà dans ce répertoire"
            )
        
        folder.name = folder_data.name.strip()
    
    # Update parent if provided
    if folder_data.parent_id is not None:
        # Prevent moving folder into itself or its children
        if folder_data.parent_id == folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un dossier ne peut pas être déplacé dans lui-même"
            )
        
        # Check if trying to move into a child (would create cycle)
        def is_descendant(parent_id: int, child_id: int, db: Session) -> bool:
            """Check if child_id is a descendant of parent_id"""
            current = db.query(Folder).filter(Folder.id == child_id).first()
            while current and current.parent_id:
                if current.parent_id == parent_id:
                    return True
                current = db.query(Folder).filter(Folder.id == current.parent_id).first()
            return False
        
        if is_descendant(folder_id, folder_data.parent_id, db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un dossier ne peut pas être déplacé dans un de ses sous-dossiers"
            )
        
        # Verify new parent exists and belongs to user
        if folder_data.parent_id:
            new_parent = db.query(Folder).filter(
                and_(
                    Folder.id == folder_data.parent_id,
                    Folder.user_id == current_user_id,
                    Folder.deleted_at.is_(None)
                )
            ).first()
            
            if not new_parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dossier parent introuvable"
                )
        
        folder.parent_id = folder_data.parent_id
    
    db.commit()
    db.refresh(folder)
    
    # Get counts
    children_count = db.query(Folder).filter(
        and_(
            Folder.parent_id == folder.id,
            Folder.deleted_at.is_(None)
        )
    ).count()
    
    files_count = db.query(File).filter(
        and_(
            File.folder_id == folder.id,
            File.deleted_at.is_(None)
        )
    ).count()
    
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        user_id=folder.user_id,
        parent_id=folder.parent_id,
        created_at=folder.created_at.isoformat() if folder.created_at else "",
        updated_at=folder.updated_at.isoformat() if folder.updated_at else None,
        children_count=children_count,
        files_count=files_count
    )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    permanent: bool = False
):
    """
    Delete a folder (soft delete by default, permanent if permanent=True)
    If permanent=True, can delete folders that are already in trash
    """
    if permanent:
        # For permanent delete, allow deleting folders that are already in trash
        folder = db.query(Folder).filter(
            and_(
                Folder.id == folder_id,
                Folder.user_id == current_user_id
            )
        ).first()
    else:
        # For soft delete, only allow deleting folders that are not already deleted
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
            detail="Dossier introuvable" if not permanent else "Dossier introuvable dans la corbeille"
        )
    
    if permanent:
        # Permanent delete: also delete all children and files (including deleted ones)
        # This is a recursive operation
        def delete_folder_recursive(folder_id: int, db: Session):
            """Recursively permanently delete folder and all its contents"""
            # Get all children (including deleted ones)
            children = db.query(Folder).filter(
                Folder.parent_id == folder_id
            ).all()
            
            # Recursively delete children
            for child in children:
                delete_folder_recursive(child.id, db)
            
            # Delete files in this folder (including deleted ones)
            files = db.query(File).filter(
                File.folder_id == folder_id
            ).all()
            
            # Permanently delete files from Azure Blob Storage and database
            blob_service = get_storage_service()
            for file in files:
                # Delete from Azure Blob Storage
                if blob_service:
                    try:
                        blob_service.delete_file(file.blob_name)
                    except Exception as e:
                        logger.error(f"Error deleting file {file.blob_name} from Azure Blob Storage: {str(e)}")
                
                # Delete from database
                db.delete(file)
            
            # Delete the folder from database
            db.query(Folder).filter(Folder.id == folder_id).delete()
        
        delete_folder_recursive(folder_id, db)
    else:
        # Soft delete
        folder.deleted_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return None


@router.get("/{folder_id}/download")
async def download_folder(
    folder_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Download a folder as a ZIP file containing all files and subfolders recursively
    """
    # Verify folder exists and belongs to user
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
    
    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()
    
    def add_folder_to_zip(folder_obj: Folder, zip_file: zipfile.ZipFile, base_path: str = ""):
        """
        Recursively add folder contents to ZIP
        """
        # Add all files in this folder
        files = db.query(File).filter(
            and_(
                File.folder_id == folder_obj.id,
                File.user_id == current_user_id,
                File.deleted_at.is_(None)
            )
        ).all()
        
        blob_service = get_storage_service()
        
        for file in files:
            try:
                # Get file content from Azure Blob Storage
                if blob_service:
                    file_content = blob_service.download_file(file.blob_name)
                else:
                    logger.warning(f"Azure Blob Storage not configured, skipping file {file.filename}")
                    continue
                
                # Add file to ZIP with relative path
                file_path = f"{base_path}{file.original_filename}" if base_path else file.original_filename
                zip_file.writestr(file_path, file_content)
            except Exception as e:
                logger.error(f"Error adding file {file.filename} to ZIP: {e}")
                # Continue with other files even if one fails
        
        # Recursively add subfolders
        subfolders = db.query(Folder).filter(
            and_(
                Folder.parent_id == folder_obj.id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).all()
        
        for subfolder in subfolders:
            subfolder_path = f"{base_path}{subfolder.name}/" if base_path else f"{subfolder.name}/"
            add_folder_to_zip(subfolder, zip_file, subfolder_path)
    
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            add_folder_to_zip(folder, zip_file, "")
        
        zip_buffer.seek(0)
        
        # Return ZIP file as streaming response
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{folder.name}.zip"'
            }
        )
    except Exception as e:
        logger.error(f"Error creating ZIP file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création du fichier ZIP: {str(e)}"
        )

