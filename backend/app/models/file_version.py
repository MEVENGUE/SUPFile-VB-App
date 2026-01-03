"""
FileVersion model for tracking file versions
"""
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class FileVersion(Base):
    """File version model for versioning"""
    
    __tablename__ = "file_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    blob_name = Column(String, nullable=False)  # Name in Azure Blob Storage for this version
    file_size = Column(BigInteger, nullable=False)
    content_type = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who created this version
    change_description = Column(Text, nullable=True)  # Optional description of changes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    file = relationship("File", backref="versions")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<FileVersion(id={self.id}, file_id={self.file_id}, version={self.version_number})>"

