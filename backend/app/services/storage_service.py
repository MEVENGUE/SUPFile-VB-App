"""
Abstraction stockage : GlusterFS/local (hybride) ou Azure Blob (cloud legacy).
"""
import logging
from typing import Optional, Union

from app.core.config import settings
from app.services.local_storage import LocalStorageService

logger = logging.getLogger(__name__)

_storage_instance: Optional[Union[LocalStorageService, object]] = None


def get_storage_service():
    """
    Retourne le service de stockage selon STORAGE_BACKEND.
    - local / gluster : fichiers sur UPLOAD_PATH (VM + GlusterFS)
    - azure : Azure Blob Storage
    """
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance

    backend = settings.STORAGE_BACKEND.lower()

    if backend == "azure":
        from app.services.azure_blob import AzureBlobService

        try:
            _storage_instance = AzureBlobService()
        except Exception as e:
            logger.warning("Azure storage unavailable: %s", e)
            return None
    else:
        try:
            _storage_instance = LocalStorageService()
        except Exception as e:
            logger.error("Local storage unavailable: %s", e)
            return None

    return _storage_instance


def storage_health() -> dict:
    storage = get_storage_service()
    if storage is None:
        return {"status": "unavailable", "backend": settings.STORAGE_BACKEND}
    if hasattr(storage, "health_status"):
        return {"status": "ok", **storage.health_status()}
    return {"status": "ok", "backend": settings.STORAGE_BACKEND}


# Compatibilité avec l'ancien nom
def get_azure_blob_service():
    if settings.STORAGE_BACKEND.lower() == "azure":
        return get_storage_service()
    return None
