"""
File model for storing file metadata
Binary files are stored in Azure Blob Storage
"""
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class File(Base):
    """File metadata model"""
    
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True, index=True)  # Parent folder
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    content_type = Column(String, nullable=True)
    blob_name = Column(String, nullable=False, unique=True)  # Name in Azure Blob Storage
    blob_url = Column(String, nullable=True)  # Optional: SAS URL if needed
    upload_region = Column(String, nullable=True)  # Azure region where file was uploaded
    is_public = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete for trash
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="files")
    folder = relationship("Folder", back_populates="files")
    history = relationship("FileHistory", back_populates="file", cascade="all, delete-orphan")
    comments = relationship("FileComment", back_populates="file", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<File(id={self.id}, filename={self.original_filename}, user_id={self.user_id})>"

