"""Rate limiting configuration for SUPFile."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

storage_uri = settings.REDIS_URL or "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],
    storage_uri=storage_uri,
)
