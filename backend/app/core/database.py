"""
Database configuration and session management
Supports Azure Database for PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create database engine
# Azure PostgreSQL requires SSL mode
database_url = settings.DATABASE_URL
if "postgres.database.azure.com" in database_url and "sslmode" not in database_url:
    if "?" in database_url:
        database_url += "&sslmode=require"
    else:
        database_url += "?sslmode=require"

engine = create_engine(
    database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI to get database session
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

