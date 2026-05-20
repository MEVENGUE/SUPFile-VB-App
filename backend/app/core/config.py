"""
Configuration SUPFile — déploiement hybride (Vercel + VM/Tailscale) ou cloud legacy.
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Variables d'environnement (VM /etc/supfile/supfile.env ou .env local)."""

    # Application
    APP_NAME: str = "SUPFile"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = ""

    # hybrid = Vercel frontend + backend VM (Tailscale/HAProxy) + infra privée
    # cloud = Azure/Railway (legacy)
    DEPLOYMENT_MODE: str = "hybrid"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # Base de données — MySQL via ProxySQL (prod) ou PostgreSQL (dev Docker)
    DATABASE_URL: str = ""

    # Stockage : local/gluster (VM) ou azure (cloud)
    STORAGE_BACKEND: str = "local"
    UPLOAD_PATH: str = "/var/lib/supfile/uploads"
    UPLOAD_REGION: str = "paris-dc"

    # URL publique du backend (Tailscale Funnel, HAProxy, ou localhost)
    BACKEND_PUBLIC_URL: str = ""

    # Azure Blob (optionnel, STORAGE_BACKEND=azure)
    AZURE_STORAGE_ACCOUNT_NAME: str = ""
    AZURE_STORAGE_ACCOUNT_KEY: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = "supfile-files"
    AZURE_STORAGE_CONNECTION_STRING: str = ""

    # JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = (
        "https://supfile-webapp.vercel.app,"
        "https://web1-paris.tail69cc44.ts.net,"
        "https://web1-ny.tail69cc44.ts.net,"
        "http://localhost:3000,"
        "http://localhost:5173"
    )

    # Sécurité fichiers
    BCRYPT_ROUNDS: int = 12
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = (
        "txt,pdf,png,jpg,jpeg,gif,doc,docx,xls,xlsx,zip,mp4,avi,mkv,mov,wmv,"
        "flv,webm,mp3,wav,ogg,flac,aac,m4a,wma,ppt,pptx,rtf,csv,json,xml,"
        "html,css,js,py,java,cpp,c,md,rar,7z,tar,gz"
    )

    # Régions (métadonnées / affichage)
    AZURE_PRIMARY_REGION: str = "paris-dc"
    AZURE_SECONDARY_REGION: str = "newyork-dc"
    AZURE_BACKUP_REGION: str = "toronto-dc"

    # OAuth2
    OAUTH_GOOGLE_CLIENT_ID: str = ""
    OAUTH_GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_GITHUB_CLIENT_ID: str = ""
    OAUTH_GITHUB_CLIENT_SECRET: str = ""
    OAUTH_MICROSOFT_CLIENT_ID: str = ""
    OAUTH_MICROSOFT_CLIENT_SECRET: str = ""

    # Frontend OAuth redirect base URL (utilise la première URI de redirection si non fourni)
    OAUTH_REDIRECT_BASE_URL: str = os.getenv("OAUTH_REDIRECT_BASE_URL", "")
    OAUTH_ALLOWED_REDIRECT_URIS: str = (
        "https://supfile-webapp.vercel.app/auth/callback,"
        "https://web1-paris.tail69cc44.ts.net/auth/callback,"
        "https://web1-ny.tail69cc44.ts.net/auth/callback"
    )

    # Backend public (callbacks OAuth — Funnel / HAProxy)
    OAUTH_CALLBACK_BASE_URL: str = os.getenv("OAUTH_CALLBACK_BASE_URL", "http://localhost:8080")

    # Deployment targets
    PRIMARY_DC: str = "PARIS"
    FAILOVER_DC: str = "NEW_YORK"
    ACTIVE_ACTIVE: bool = True

    # Security stack flags
    WAZUH: bool = True
    SURICATA: bool = True
    FAIL2BAN: bool = True
    UFW: bool = True

    # Ingress compatibility
    TRUST_PROXY_HEADERS: bool = True
    HAPROXY_COMPAT: bool = True
    TAILSCALE_FUNNEL_COMPAT: bool = True

    # Chunked uploads
    CHUNK_UPLOAD_ENABLED: bool = True
    CHUNK_SIZE_MB: int = 8
    CHUNK_TMP_PATH: str = "/tmp/supfile-chunks"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def oauth_allowed_redirect_uris_list(self) -> List[str]:
        return [uri.strip() for uri in self.OAUTH_ALLOWED_REDIRECT_URIS.split(",") if uri.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def chunk_size_bytes(self) -> int:
        return self.CHUNK_SIZE_MB * 1024 * 1024

    @property
    def is_hybrid(self) -> bool:
        return self.DEPLOYMENT_MODE.lower() == "hybrid"

    @property
    def is_mysql(self) -> bool:
        url = self.DATABASE_URL.lower()
        return url.startswith("mysql") or "pymysql" in url or "mariadb" in url

    @property
    def backend_public_url(self) -> str:
        if self.BACKEND_PUBLIC_URL:
            return self.BACKEND_PUBLIC_URL.rstrip("/")
        return self.OAUTH_CALLBACK_BASE_URL.rstrip("/")

    @property
    def oauth_redirect_base_url(self) -> str:
        if self.OAUTH_REDIRECT_BASE_URL:
            return self.OAUTH_REDIRECT_BASE_URL.rstrip("/")
        if self.oauth_allowed_redirect_uris_list:
            first_uri = self.oauth_allowed_redirect_uris_list[0]
            return first_uri.rsplit("/auth/callback", 1)[0].rstrip("/")
        return "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

if not settings.OAUTH_REDIRECT_BASE_URL:
    settings.OAUTH_REDIRECT_BASE_URL = settings.oauth_redirect_base_url

if not settings.DATABASE_URL:
    settings.DATABASE_URL = os.getenv("DATABASE_URL", "")
    if not settings.DATABASE_URL:
        raise ValueError(
            "DATABASE_URL est requis. "
            "Hybride : mysql+pymysql://user:pass@10.10.1.32:6033/supfile (ProxySQL)"
        )

if not settings.SECRET_KEY:
    raise ValueError("SECRET_KEY est requis")

if not settings.JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY est requis")

IS_PRODUCTION = (
    os.getenv("APP_ENV", "development").lower() in ("production", "prod")
    or os.getenv("DEPLOYMENT_MODE", "").lower() == "hybrid"
    and settings.APP_ENV.lower() in ("production", "prod")
)

if IS_PRODUCTION and settings.is_hybrid:
    import warnings

    if "localhost" in settings.oauth_redirect_base_url:
        warnings.warn(
            f"OAUTH redirect base URL pointe vers localhost : {settings.oauth_redirect_base_url}\n"
            "Configurer l'URL Vercel du frontend.",
            UserWarning,
        )
    if "localhost" in settings.OAUTH_CALLBACK_BASE_URL:
        warnings.warn(
            f"OAUTH_CALLBACK_BASE_URL pointe vers localhost : {settings.OAUTH_CALLBACK_BASE_URL}\n"
            "Configurer l'URL Tailscale Funnel ou HAProxy.",
            UserWarning,
        )
