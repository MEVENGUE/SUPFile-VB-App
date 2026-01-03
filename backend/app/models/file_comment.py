"""
File comments model for collaboration
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class FileComment(Base):
    """Comments on files for collaboration"""
    __tablename__ = "file_comments"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    comment = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("file_comments.id", ondelete="CASCADE"), nullable=True)  # For replies
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    # Relationships
    file = relationship("File", back_populates="comments")
    user = relationship("User")
    parent_comment = relationship("FileComment", remote_side=[id], backref="replies")


class FolderComment(Base):
    """Comments on folders for collaboration"""
    __tablename__ = "folder_comments"

    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    comment = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("folder_comments.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    folder = relationship("Folder", back_populates="comments")
    user = relationship("User")
    parent_comment = relationship("FolderComment", remote_side=[id], backref="replies")

