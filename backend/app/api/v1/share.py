"""
Share endpoints: create, get, delete share links
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid
import logging
import io
import zipfile

from app.core.database import get_db
from app.core.middleware import get_current_user_id
from app.core.security import get_password_hash, verify_password
from app.models.share_link import ShareLink
from app.models.file import File
from app.models.folder import Folder

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class ShareLinkCreate(BaseModel):
    file_id: Optional[int] = None
    folder_id: Optional[int] = None
    password: Optional[str] = None
    expires_in_days: Optional[int] = None  # Number of days until expiration


class ShareLinkResponse(BaseModel):
    id: int
    token: str
    file_id: Optional[int] = None
    folder_id: Optional[int] = None
    share_url: str
    expires_at: Optional[str] = None
    is_active: bool
    access_count: int
    created_at: str
    has_password: bool

    class Config:
        from_attributes = True


class ShareLinkListResponse(BaseModel):
    share_links: List[ShareLinkResponse]
    total: int


class ShareAccessRequest(BaseModel):
    password: Optional[str] = None


class ShareAccessResponse(BaseModel):
    file: Optional[dict] = None
    folder: Optional[dict] = None
    share_link: ShareLinkResponse


@router.post("/", response_model=ShareLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_share_link(
    share_data: ShareLinkCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create a share link for a file or folder
    """
    # Validate that either file_id or folder_id is provided, but not both
    if not share_data.file_id and not share_data.folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file_id or folder_id must be provided"
        )
    
    if share_data.file_id and share_data.folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share both file and folder in the same link"
        )

    # Verify ownership
    if share_data.file_id:
        file = db.query(File).filter(
            and_(
                File.id == share_data.file_id,
                File.user_id == current_user_id,
                File.deleted_at.is_(None)
            )
        ).first()
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or you don't have permission"
            )
    else:  # folder_id
        folder = db.query(Folder).filter(
            and_(
                Folder.id == share_data.folder_id,
                Folder.user_id == current_user_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found or you don't have permission"
            )

    # Generate unique token
    token = str(uuid.uuid4())

    # Calculate expiration date if provided
    expires_at = None
    if share_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=share_data.expires_in_days)

    # Hash password if provided
    password_hash = None
    if share_data.password:
        password_hash = get_password_hash(share_data.password)

    # Create share link
    share_link = ShareLink(
        token=token,
        file_id=share_data.file_id,
        folder_id=share_data.folder_id,
        user_id=current_user_id,
        password_hash=password_hash,
        expires_at=expires_at,
        is_active=True
    )

    db.add(share_link)
    db.commit()
    db.refresh(share_link)

    # Generate share URL (will be constructed on frontend)
    share_url = f"/share/{token}"

    return ShareLinkResponse(
        id=share_link.id,
        token=share_link.token,
        file_id=share_link.file_id,
        folder_id=share_link.folder_id,
        share_url=share_url,
        expires_at=share_link.expires_at.isoformat() if share_link.expires_at else None,
        is_active=share_link.is_active,
        access_count=share_link.access_count,
        created_at=share_link.created_at.isoformat(),
        has_password=password_hash is not None
    )


@router.get("/", response_model=ShareLinkListResponse)
async def list_share_links(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    List all share links created by the current user
    """
    share_links = db.query(ShareLink).filter(
        ShareLink.user_id == current_user_id
    ).offset(skip).limit(limit).all()
    
    total = db.query(ShareLink).filter(
        ShareLink.user_id == current_user_id
    ).count()

    share_link_responses = []
    for link in share_links:
        share_url = f"/share/{link.token}"
        share_link_responses.append(ShareLinkResponse(
            id=link.id,
            token=link.token,
            file_id=link.file_id,
            folder_id=link.folder_id,
            share_url=share_url,
            expires_at=link.expires_at.isoformat() if link.expires_at else None,
            is_active=link.is_active,
            access_count=link.access_count,
            created_at=link.created_at.isoformat(),
            has_password=link.password_hash is not None
        ))

    return ShareLinkListResponse(
        share_links=share_link_responses,
        total=total
    )


@router.get("/{token}", response_model=ShareAccessResponse)
async def access_share_link(
    token: str,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Access a shared file or folder using a share token
    No authentication required - this is a public endpoint
    """
    logger.info(f"Accessing share link with token: {token[:8]}...")
    share_link = db.query(ShareLink).filter(
        ShareLink.token == token
    ).first()
    
    logger.info(f"Share link found: {share_link is not None}")

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lien de partage introuvable"
        )

    # Check if link is active
    if not share_link.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a été désactivé"
        )

    # Check expiration
    if share_link.expires_at and share_link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a expiré"
        )

    # Check password if required
    if share_link.password_hash:
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe requis pour accéder à ce lien"
            )
        
        if not verify_password(password, share_link.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe incorrect"
            )

    # Update access count and last accessed time
    share_link.access_count += 1
    share_link.last_accessed_at = datetime.utcnow()
    db.commit()

    # Get file or folder data
    file_data = None
    folder_data = None

    if share_link.file_id:
        file = db.query(File).filter(
            and_(
                File.id == share_link.file_id,
                File.deleted_at.is_(None)
            )
        ).first()
        
        if file:
            file_data = {
                "id": file.id,
                "filename": file.filename,
                "original_filename": file.original_filename,
                "file_size": file.file_size,
                "content_type": file.content_type,
                "created_at": file.created_at.isoformat()
            }
    else:  # folder_id
        folder = db.query(Folder).filter(
            and_(
                Folder.id == share_link.folder_id,
                Folder.deleted_at.is_(None)
            )
        ).first()
        
        if folder:
            folder_data = {
                "id": folder.id,
                "name": folder.name,
                "created_at": folder.created_at.isoformat()
            }

    share_url = f"/share/{share_link.token}"
    
    return ShareAccessResponse(
        file=file_data,
        folder=folder_data,
        share_link=ShareLinkResponse(
            id=share_link.id,
            token=share_link.token,
            file_id=share_link.file_id,
            folder_id=share_link.folder_id,
            share_url=share_url,
            expires_at=share_link.expires_at.isoformat() if share_link.expires_at else None,
            is_active=share_link.is_active,
            access_count=share_link.access_count,
            created_at=share_link.created_at.isoformat(),
            has_password=share_link.password_hash is not None
        )
    )


@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share_link(
    share_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Delete a share link (only by the owner)
    """
    share_link = db.query(ShareLink).filter(
        and_(
            ShareLink.id == share_id,
            ShareLink.user_id == current_user_id
        )
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or you don't have permission"
        )

    db.delete(share_link)
    db.commit()
    
    return None


@router.get("/{token}/preview")
async def preview_shared_file(
    token: str,
    password: Optional[str] = Query(None),
    file_id: Optional[int] = Query(None, description="File ID to preview (required if token is for a folder)"),
    db: Session = Depends(get_db)
):
    """
    Get a preview URL for a shared file using a share token
    No authentication required - this is a public endpoint
    If token is for a folder, file_id parameter is required
    """
    from app.services.storage_service import get_storage_service

    logger.info(f"Accessing shared file preview with token: {token[:8]}..., file_id: {file_id}")

    share_link = db.query(ShareLink).filter(
        ShareLink.token == token
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lien de partage introuvable"
        )

    # Check if link is active
    if not share_link.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a été désactivé"
        )

    # Check expiration
    if share_link.expires_at and share_link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a expiré"
        )

    # Check password if required
    if share_link.password_hash:
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe requis pour prévisualiser ce fichier"
            )
        
        if not verify_password(password, share_link.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe incorrect"
            )

    # Determine which file to preview
    target_file_id = None
    if share_link.file_id:
        # Direct file share
        target_file_id = share_link.file_id
    elif share_link.folder_id:
        # Folder share - file_id parameter is required
        if not file_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file_id est requis pour prévisualiser un fichier dans un dossier partagé"
            )
        # Verify that the file belongs to the shared folder
        file = db.query(File).filter(
            and_(
                File.id == file_id,
                File.folder_id == share_link.folder_id,
                File.deleted_at.is_(None)
            )
        ).first()
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier introuvable dans ce dossier partagé"
            )
        target_file_id = file_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de partage invalide"
        )

    # Get file
    file = db.query(File).filter(
        and_(
            File.id == target_file_id,
            File.deleted_at.is_(None)
        )
    ).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable"
        )

    # Generate SAS URL for preview (1 hour expiry)
    try:
        blob_service = get_storage_service()
        if not blob_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stockage non configuré."
            )
        preview_url = blob_service.get_preview_url(file.id, file.user_id, file.blob_name)
        
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


@router.get("/{token}/folder")
async def get_shared_folder_content(
    token: str,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get files and subfolders in a shared folder
    No authentication required - this is a public endpoint
    """
    logger.info(f"Accessing shared folder content with token: {token[:8]}...")
    
    share_link = db.query(ShareLink).filter(
        ShareLink.token == token
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lien de partage introuvable"
        )

    # Check if link is active
    if not share_link.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a été désactivé"
        )

    # Check expiration
    if share_link.expires_at and share_link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a expiré"
        )

    # Check password if required
    if share_link.password_hash:
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe requis pour accéder à ce dossier"
            )
        
        if not verify_password(password, share_link.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe incorrect"
            )

    # Only folders can be browsed
    if not share_link.folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce lien de partage ne correspond pas à un dossier"
        )

    # Get folder
    folder = db.query(Folder).filter(
        and_(
            Folder.id == share_link.folder_id,
            Folder.deleted_at.is_(None)
        )
    ).first()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable"
        )

    # Get files in folder
    files = db.query(File).filter(
        and_(
            File.folder_id == folder.id,
            File.deleted_at.is_(None)
        )
    ).offset(skip).limit(limit).all()
    
    files_total = db.query(File).filter(
        and_(
            File.folder_id == folder.id,
            File.deleted_at.is_(None)
        )
    ).count()

    # Get subfolders
    subfolders = db.query(Folder).filter(
        and_(
            Folder.parent_id == folder.id,
            Folder.deleted_at.is_(None)
        )
    ).offset(skip).limit(limit).all()
    
    subfolders_total = db.query(Folder).filter(
        and_(
            Folder.parent_id == folder.id,
            Folder.deleted_at.is_(None)
        )
    ).count()

    # Update access count
    share_link.access_count += 1
    share_link.last_accessed_at = datetime.utcnow()
    db.commit()

    return {
        "folder": {
            "id": folder.id,
            "name": folder.name,
            "created_at": folder.created_at.isoformat() if folder.created_at else None
        },
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "original_filename": f.original_filename,
                "file_size": f.file_size,
                "content_type": f.content_type,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in files
        ],
        "subfolders": [
            {
                "id": sf.id,
                "name": sf.name,
                "created_at": sf.created_at.isoformat() if sf.created_at else None
            }
            for sf in subfolders
        ],
        "files_total": files_total,
        "subfolders_total": subfolders_total
    }


@router.get("/{token}/download")
async def download_shared_file(
    token: str,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Download a shared file or folder using a share token
    - Files are downloaded directly
    - Folders are downloaded as ZIP files
    No authentication required - this is a public endpoint
    """
    from fastapi.responses import StreamingResponse
    from app.services.storage_service import get_storage_service

    logger.info(f"Downloading shared resource with token: {token[:8]}...")

    share_link = db.query(ShareLink).filter(
        ShareLink.token == token
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lien de partage introuvable"
        )

    # Check if link is active
    if not share_link.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a été désactivé"
        )

    # Check expiration
    if share_link.expires_at and share_link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a expiré"
        )

    # Check password if required
    if share_link.password_hash:
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe requis pour télécharger ce fichier"
            )
        
        if not verify_password(password, share_link.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe incorrect"
            )

    # Handle folder download as ZIP
    if share_link.folder_id:
        folder = db.query(Folder).filter(
            and_(
                Folder.id == share_link.folder_id,
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
            zip_content = zip_buffer.read()

            # Update access count
            share_link.access_count += 1
            share_link.last_accessed_at = datetime.utcnow()
            db.commit()

            # Return ZIP file as streaming response
            return StreamingResponse(
                io.BytesIO(zip_content),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{folder.name}.zip"',
                    "Content-Length": str(len(zip_content))
                }
            )
        except Exception as e:
            logger.error(f"Error creating ZIP file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la création du fichier ZIP: {str(e)}"
            )

    # Handle file download (existing logic)
    if not share_link.file_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de partage invalide"
        )

    # Get file
    file = db.query(File).filter(
        and_(
            File.id == share_link.file_id,
            File.deleted_at.is_(None)
        )
    ).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable"
        )

    # Download from Azure Blob Storage
    try:
        blob_service = get_storage_service()
        if not blob_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Le service de stockage Azure Blob n'est pas configuré."
            )
        file_content = blob_service.download_file(file.blob_name)
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement du fichier depuis le stockage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du téléchargement du fichier: {str(e)}"
        )

    # Update access count
    share_link.access_count += 1
    share_link.last_accessed_at = datetime.utcnow()
    db.commit()

    # Return file as streaming response
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=file.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file.original_filename}"',
            "Content-Length": str(len(file_content))
        }
    )


@router.get("/{token}/files/{file_id}/download")
async def download_file_from_shared_folder(
    token: str,
    file_id: int,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Download a specific file from a shared folder
    No authentication required - this is a public endpoint
    """
    from fastapi.responses import StreamingResponse
    from app.services.storage_service import get_storage_service
    import io

    logger.info(f"Downloading file {file_id} from shared folder with token: {token[:8]}...")

    share_link = db.query(ShareLink).filter(
        ShareLink.token == token
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lien de partage introuvable"
        )

    # Check if link is active
    if not share_link.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a été désactivé"
        )

    # Check expiration
    if share_link.expires_at and share_link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien de partage a expiré"
        )

    # Check password if required
    if share_link.password_hash:
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe requis pour télécharger ce fichier"
            )
        
        if not verify_password(password, share_link.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mot de passe incorrect"
            )

    # Must be a folder share
    if not share_link.folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce lien de partage ne correspond pas à un dossier"
        )

    # Verify file belongs to the shared folder
    file = db.query(File).filter(
        and_(
            File.id == file_id,
            File.folder_id == share_link.folder_id,
            File.deleted_at.is_(None)
        )
    ).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable dans ce dossier partagé"
        )

    # Download from Azure Blob Storage
    try:
        blob_service = get_storage_service()
        if not blob_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Le service de stockage Azure Blob n'est pas configuré."
            )
        file_content = blob_service.download_file(file.blob_name)
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement du fichier depuis le stockage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du téléchargement du fichier: {str(e)}"
        )

    # Update access count
    share_link.access_count += 1
    share_link.last_accessed_at = datetime.utcnow()
    db.commit()

    # Return file as streaming response
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=file.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file.original_filename}"',
            "Content-Length": str(len(file_content))
        }
    )


@router.patch("/{share_id}/deactivate", response_model=ShareLinkResponse)
async def deactivate_share_link(
    share_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Deactivate a share link without deleting it
    """
    share_link = db.query(ShareLink).filter(
        and_(
            ShareLink.id == share_id,
            ShareLink.user_id == current_user_id
        )
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or you don't have permission"
        )

    share_link.is_active = False
    db.commit()
    db.refresh(share_link)

    share_url = f"/share/{share_link.token}"
    
    return ShareLinkResponse(
        id=share_link.id,
        token=share_link.token,
        file_id=share_link.file_id,
        folder_id=share_link.folder_id,
        share_url=share_url,
        expires_at=share_link.expires_at.isoformat() if share_link.expires_at else None,
        is_active=share_link.is_active,
        access_count=share_link.access_count,
        created_at=share_link.created_at.isoformat(),
        has_password=share_link.password_hash is not None
    )

