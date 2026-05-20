"""
Stockage fichiers sur système local / GlusterFS (infra privée VirtualBox).
"""
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class LocalStorageService:
    """Fichiers sur disque (GlusterFS monté ou répertoire local)."""

    def __init__(self):
        self.base_path = Path(settings.UPLOAD_PATH).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info("Local storage initialized at %s", self.base_path)

    def generate_blob_name(self, user_id: int, original_filename: str) -> str:
        file_uuid = str(uuid.uuid4())
        safe_filename = "".join(
            c for c in original_filename if c.isalnum() or c in "._- "
        ).strip()
        return f"{user_id}/{file_uuid}/{safe_filename}"

    def _resolve_path(self, blob_name: str) -> Path:
        path = (self.base_path / blob_name).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise ValueError("Invalid storage path")
        return path

    def upload_file(
        self,
        file_content: bytes,
        blob_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        path = self._resolve_path(blob_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_content)
        logger.info("Uploaded file to %s", path)
        return str(path)

    def download_file(self, blob_name: str) -> bytes:
        path = self._resolve_path(blob_name)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {blob_name}")
        return path.read_bytes()

    def delete_file(self, blob_name: str) -> bool:
        path = self._resolve_path(blob_name)
        if path.is_file():
            path.unlink()
            logger.info("Deleted file %s", path)
            return True
        return False

    def file_exists(self, blob_name: str) -> bool:
        return self._resolve_path(blob_name).is_file()

    def get_preview_url(self, file_id: int, user_id: int, blob_name: str) -> str:
        from app.core.security import create_preview_token

        token = create_preview_token(file_id, user_id)
        base = settings.backend_public_url.rstrip("/")
        return f"{base}/api/v1/files/{file_id}/preview/content?token={token}"

    def health_status(self) -> dict:
        test_file = self.base_path / ".healthcheck"
        try:
            test_file.write_text("ok")
            test_file.unlink()
            writable = True
        except OSError:
            writable = False

        mounted = os.path.ismount(self.base_path)
        if self.base_path.exists():
            usage = shutil.disk_usage(self.base_path)
            disk_info = {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
            }
        else:
            disk_info = None

        result = {
            "backend": "local",
            "type": "glusterfs" if "gluster" in str(self.base_path).lower() or mounted else "local",
            "path": str(self.base_path),
            "mounted": mounted,
            "writable": writable,
        }
        if disk_info is not None:
            result["disk"] = disk_info

        return result
