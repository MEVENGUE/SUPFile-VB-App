"""
File modification history model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class ActionType(str, enum.Enum):
    """Types of actions that can be logged"""
    CREATED = "created"
    UPDATED = "updated"
    RENAMED = "renamed"
    MOVED = "moved"
    DELETED = "deleted"
    RESTORED = "restored"
    SHARED = "shared"
    UNSHARED = "unshared"
    DOWNLOADED = "downloaded"
    VIEWED = "viewed"


class FileHistory(Base):
    """History of file modifications"""
    __tablename__ = "file_history"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(SQLEnum(ActionType), nullable=False)
    old_value = Column(Text, nullable=True)  # Previous filename, path, etc.
    new_value = Column(Text, nullable=True)  # New filename, path, etc.
    description = Column(Text, nullable=True)  # Human-readable description
    extra_data = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    file = relationship("File", back_populates="history")
    user = relationship("User")


class FolderHistory(Base):
    """History of folder modifications"""
    __tablename__ = "folder_history"

    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(SQLEnum(ActionType), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    folder = relationship("Folder", back_populates="history")
    user = relationship("User")

