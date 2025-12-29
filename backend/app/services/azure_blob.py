"""
Azure Blob Storage service
Handles file upload, download, and deletion
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, BinaryIO
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import AzureError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AzureBlobService:
    """Service for interacting with Azure Blob Storage"""
    
    def __init__(self):
        """Initialize Azure Blob Storage client"""
        # Use connection string if provided, otherwise use account name and key
        if settings.AZURE_STORAGE_CONNECTION_STRING:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
        elif settings.AZURE_STORAGE_ACCOUNT_NAME and settings.AZURE_STORAGE_ACCOUNT_KEY:
            account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=settings.AZURE_STORAGE_ACCOUNT_KEY
            )
        else:
            raise ValueError("Azure Storage credentials not configured")
        
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Create container if it doesn't exist"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
        except AzureError as e:
            logger.error(f"Error ensuring container exists: {e}")
            raise
    
    def generate_blob_name(self, user_id: int, original_filename: str) -> str:
        """
        Generate a unique blob name for a file
        Format: {user_id}/{uuid}/{original_filename}
        """
        file_uuid = str(uuid.uuid4())
        # Sanitize filename
        safe_filename = "".join(
            c for c in original_filename if c.isalnum() or c in "._- "
        ).strip()
        return f"{user_id}/{file_uuid}/{safe_filename}"
    
    def upload_file(
        self,
        file_content: bytes,
        blob_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to Azure Blob Storage
        Returns the blob URL
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload with content type and metadata
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings={"content_type": content_type} if content_type else None,
                metadata=metadata or {}
            )
            
            blob_url = blob_client.url
            logger.info(f"Uploaded file to blob: {blob_name}")
            return blob_url
            
        except AzureError as e:
            logger.error(f"Error uploading file to Azure Blob Storage: {e}")
            raise
    
    def download_file(self, blob_name: str) -> bytes:
        """
        Download a file from Azure Blob Storage
        Returns file content as bytes
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            if not blob_client.exists():
                raise FileNotFoundError(f"Blob not found: {blob_name}")
            
            download_stream = blob_client.download_blob()
            file_content = download_stream.readall()
            
            logger.info(f"Downloaded file from blob: {blob_name}")
            return file_content
            
        except AzureError as e:
            logger.error(f"Error downloading file from Azure Blob Storage: {e}")
            raise
    
    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a file from Azure Blob Storage
        Returns True if successful
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            if blob_client.exists():
                blob_client.delete_blob()
                logger.info(f"Deleted file from blob: {blob_name}")
                return True
            else:
                logger.warning(f"Blob not found for deletion: {blob_name}")
                return False
                
        except AzureError as e:
            logger.error(f"Error deleting file from Azure Blob Storage: {e}")
            raise
    
    def file_exists(self, blob_name: str) -> bool:
        """Check if a file exists in Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            return blob_client.exists()
        except AzureError:
            return False
    
    def generate_sas_url(
        self,
        blob_name: str,
        expiry_minutes: int = 60
    ) -> str:
        """
        Generate a SAS (Shared Access Signature) URL for temporary access
        Useful for direct downloads without going through the API
        """
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            sas_token = generate_blob_sas(
                account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
            )
            
            return f"{blob_client.url}?{sas_token}"
            
        except Exception as e:
            logger.error(f"Error generating SAS URL: {e}")
            raise


# Global instance
azure_blob_service = AzureBlobService()

