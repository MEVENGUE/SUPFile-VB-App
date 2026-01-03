"""
ShareLink model for public file/folder sharing
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class ShareLink(Base):
    """
    Model for public sharing links
    Allows sharing files/folders with unique tokens
    """
    __tablename__ = "share_links"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # Optional password protection
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    is_active = Column(Boolean, default=True)  # Allow disabling without deletion
    access_count = Column(Integer, default=0)  # Track number of accesses
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="share_links")
    file = relationship("File", backref="share_links")
    folder = relationship("Folder", backref="share_links")

    def __repr__(self):
        return f"<ShareLink(id={self.id}, token={self.token[:8]}..., file_id={self.file_id}, folder_id={self.folder_id})>"

