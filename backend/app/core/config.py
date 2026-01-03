"""
Application configuration using Pydantic Settings
Supports environment variables for cloud deployment
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "SUPFile"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = ""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database - PostgreSQL (Azure or Railway)
    DATABASE_URL: str = ""
    
    # Azure Blob Storage (optional for local development)
    AZURE_STORAGE_ACCOUNT_NAME: str = ""
    AZURE_STORAGE_ACCOUNT_KEY: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = "supfile-files"
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    
    # JWT Authentication
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    
    # Security
    BCRYPT_ROUNDS: int = 12
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = "txt,pdf,png,jpg,jpeg,gif,doc,docx,xls,xlsx,zip,mp4,avi,mkv,mov,wmv,flv,webm,mp3,wav,ogg,flac,aac,m4a,wma,ppt,pptx,rtf,csv,json,xml,html,css,js,py,java,cpp,c,md,rar,7z,tar,gz"
    
    # Azure Regions
    AZURE_PRIMARY_REGION: str = "eastus"
    AZURE_SECONDARY_REGION: str = "francecentral"
    AZURE_BACKUP_REGION: str = "canadacentral"
    
    # OAuth2 Providers (optional - set in .env)
    OAUTH_GOOGLE_CLIENT_ID: str = ""
    OAUTH_GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_GITHUB_CLIENT_ID: str = ""
    OAUTH_GITHUB_CLIENT_SECRET: str = ""
    OAUTH_MICROSOFT_CLIENT_ID: str = ""
    OAUTH_MICROSOFT_CLIENT_SECRET: str = ""
    
    # OAuth2 Base URL (for redirects to frontend after OAuth)
    # In production, this should be your Vercel frontend URL (e.g., https://supfile-webapp.vercel.app)
    OAUTH_REDIRECT_BASE_URL: str = os.getenv("OAUTH_REDIRECT_BASE_URL", "http://localhost:3000")
    
    # OAuth2 Callback Base URL (backend URL for OAuth callbacks)
    # In production, this should be your Railway backend URL (e.g., https://supfile-vercel-app-production.up.railway.app)
    OAUTH_CALLBACK_BASE_URL: str = os.getenv("OAUTH_CALLBACK_BASE_URL", "http://localhost:8000")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse allowed file extensions"""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
# Validate required settings at startup
settings = Settings()

# Validate required environment variables
if not settings.DATABASE_URL:
    # Try to get from environment directly (for Railway)
    settings.DATABASE_URL = os.getenv("DATABASE_URL", "")
    if not settings.DATABASE_URL:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "On Railway, make sure to reference it as ${{Postgres.DATABASE_URL}}"
        )

if not settings.SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

if not settings.JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required")

# Detect production environment
IS_PRODUCTION = (
    os.getenv("APP_ENV", "development").lower() in ["production", "prod"] 
    or os.getenv("RAILWAY_ENVIRONMENT") is not None
    or os.getenv("VERCEL") is not None
)

# Warn about OAuth URLs in production (but don't block startup)
# This allows the app to start even if OAuth is not fully configured
if IS_PRODUCTION:
    import warnings
    if "localhost" in settings.OAUTH_REDIRECT_BASE_URL:
        warnings.warn(
            f"⚠️ OAUTH_REDIRECT_BASE_URL is set to localhost in production: {settings.OAUTH_REDIRECT_BASE_URL}\n"
            "📝 Configure in Railway: OAUTH_REDIRECT_BASE_URL=https://supfile-webapp.vercel.app",
            UserWarning
        )
    if "localhost" in settings.OAUTH_CALLBACK_BASE_URL:
        warnings.warn(
            f"⚠️ OAUTH_CALLBACK_BASE_URL is set to localhost in production: {settings.OAUTH_CALLBACK_BASE_URL}\n"
            "📝 Configure in Railway: OAUTH_CALLBACK_BASE_URL=https://supfile-vercel-app-production.up.railway.app",
            UserWarning
        )

