"""
API routes for file and folder comments
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.middleware import get_current_user_id
from app.models.file_comment import FileComment, FolderComment
from app.models.file import File
from app.models.folder import Folder
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class CommentRequest(BaseModel):
    comment: str
    parent_comment_id: Optional[int] = None


class CommentResponse(BaseModel):
    id: int
    file_id: Optional[int] = None
    folder_id: Optional[int] = None
    user_id: int
    username: Optional[str] = None
    comment: str
    parent_comment_id: Optional[int] = None
    replies: List['CommentResponse'] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


CommentResponse.model_rebuild()


@router.post("/files/{file_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_file_comment(
    file_id: int,
    comment_data: CommentRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create a comment on a file
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

    # Verify parent comment if provided
    if comment_data.parent_comment_id:
        parent = db.query(FileComment).filter(
            FileComment.id == comment_data.parent_comment_id,
            FileComment.file_id == file_id,
            FileComment.deleted_at.is_(None)
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commentaire parent introuvable"
            )

    # Create comment
    comment = FileComment(
        file_id=file_id,
        user_id=current_user_id,
        comment=comment_data.comment,
        parent_comment_id=comment_data.parent_comment_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Get user info
    from app.models.user import User
    user = db.query(User).filter(User.id == current_user_id).first()
    
    response = CommentResponse(
        id=comment.id,
        file_id=comment.file_id,
        user_id=comment.user_id,
        username=user.username if user else None,
        comment=comment.comment,
        parent_comment_id=comment.parent_comment_id,
        replies=[],
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )
    return response


@router.get("/files/{file_id}/comments", response_model=List[CommentResponse])
async def get_file_comments(
    file_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get all comments for a file (with replies)
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

    # Get top-level comments (no parent)
    comments = db.query(FileComment).filter(
        FileComment.file_id == file_id,
        FileComment.parent_comment_id.is_(None),
        FileComment.deleted_at.is_(None)
    ).order_by(desc(FileComment.created_at)).all()

    # Get user info
    from app.models.user import User
    users = {u.id: u.username for u in db.query(User).all()}

    def build_comment_response(comment: FileComment) -> CommentResponse:
        # Get replies
        replies = db.query(FileComment).filter(
            FileComment.parent_comment_id == comment.id,
            FileComment.deleted_at.is_(None)
        ).order_by(FileComment.created_at).all()

        return CommentResponse(
            id=comment.id,
            file_id=comment.file_id,
            user_id=comment.user_id,
            username=users.get(comment.user_id),
            comment=comment.comment,
            parent_comment_id=comment.parent_comment_id,
            replies=[build_comment_response(reply) for reply in replies],
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )

    return [build_comment_response(comment) for comment in comments]


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    comment_data: CommentRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update a comment (file or folder)
    """
    # Try file comment first
    comment = db.query(FileComment).filter(
        FileComment.id == comment_id,
        FileComment.user_id == current_user_id,
        FileComment.deleted_at.is_(None)
    ).first()

    if not comment:
        # Try folder comment
        comment = db.query(FolderComment).filter(
            FolderComment.id == comment_id,
            FolderComment.user_id == current_user_id,
            FolderComment.deleted_at.is_(None)
        ).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commentaire introuvable"
        )

    comment.comment = comment_data.comment
    db.commit()
    db.refresh(comment)

    from app.models.user import User
    user = db.query(User).filter(User.id == current_user_id).first()

    if isinstance(comment, FileComment):
        return CommentResponse(
            id=comment.id,
            file_id=comment.file_id,
            user_id=comment.user_id,
            username=user.username if user else None,
            comment=comment.comment,
            parent_comment_id=comment.parent_comment_id,
            replies=[],
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )
    else:
        return CommentResponse(
            id=comment.id,
            folder_id=comment.folder_id,
            user_id=comment.user_id,
            username=user.username if user else None,
            comment=comment.comment,
            parent_comment_id=comment.parent_comment_id,
            replies=[],
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Soft delete a comment
    """
    from datetime import datetime

    # Try file comment first
    comment = db.query(FileComment).filter(
        FileComment.id == comment_id,
        FileComment.user_id == current_user_id,
        FileComment.deleted_at.is_(None)
    ).first()

    if not comment:
        # Try folder comment
        comment = db.query(FolderComment).filter(
            FolderComment.id == comment_id,
            FolderComment.user_id == current_user_id,
            FolderComment.deleted_at.is_(None)
        ).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commentaire introuvable"
        )

    comment.deleted_at = datetime.utcnow()
    db.commit()
    return None


@router.post("/folders/{folder_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_folder_comment(
    folder_id: int,
    comment_data: CommentRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create a comment on a folder
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

    # Verify parent comment if provided
    if comment_data.parent_comment_id:
        parent = db.query(FolderComment).filter(
            FolderComment.id == comment_data.parent_comment_id,
            FolderComment.folder_id == folder_id,
            FolderComment.deleted_at.is_(None)
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commentaire parent introuvable"
            )

    # Create comment
    comment = FolderComment(
        folder_id=folder_id,
        user_id=current_user_id,
        comment=comment_data.comment,
        parent_comment_id=comment_data.parent_comment_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    from app.models.user import User
    user = db.query(User).filter(User.id == current_user_id).first()
    
    response = CommentResponse(
        id=comment.id,
        folder_id=comment.folder_id,
        user_id=comment.user_id,
        username=user.username if user else None,
        comment=comment.comment,
        parent_comment_id=comment.parent_comment_id,
        replies=[],
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )
    return response


@router.get("/folders/{folder_id}/comments", response_model=List[CommentResponse])
async def get_folder_comments(
    folder_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get all comments for a folder
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

    # Get top-level comments
    comments = db.query(FolderComment).filter(
        FolderComment.folder_id == folder_id,
        FolderComment.parent_comment_id.is_(None),
        FolderComment.deleted_at.is_(None)
    ).order_by(desc(FolderComment.created_at)).all()

    from app.models.user import User
    users = {u.id: u.username for u in db.query(User).all()}

    def build_comment_response(comment: FolderComment) -> CommentResponse:
        replies = db.query(FolderComment).filter(
            FolderComment.parent_comment_id == comment.id,
            FolderComment.deleted_at.is_(None)
        ).order_by(FolderComment.created_at).all()

        return CommentResponse(
            id=comment.id,
            folder_id=comment.folder_id,
            user_id=comment.user_id,
            username=users.get(comment.user_id),
            comment=comment.comment,
            parent_comment_id=comment.parent_comment_id,
            replies=[build_comment_response(reply) for reply in replies],
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )

    return [build_comment_response(comment) for comment in comments]

