"""
FileMetadata model for storing additional file metadata (tags, descriptions, etc.)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class FileMetadata(Base):
    """File metadata model for additional file information"""
    
    __tablename__ = "file_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)  # User-provided description
    tags = Column(String, nullable=True)  # Comma-separated tags
    custom_metadata = Column(JSON, nullable=True)  # Flexible JSON for additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    file = relationship("File", backref="metadata", uselist=False)
    
    def __repr__(self):
        return f"<FileMetadata(id={self.id}, file_id={self.file_id})>"

