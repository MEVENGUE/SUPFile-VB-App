"""
Connexion base de données — MySQL/Galera via ProxySQL (hybride) ou PostgreSQL (dev).
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import make_url
from app.core.config import settings

database_url = settings.DATABASE_URL

# SSL PostgreSQL cloud (Azure / Railway) — ignoré pour MySQL interne
if database_url and not settings.is_mysql:
    if "postgres.database.azure.com" in database_url and "sslmode" not in database_url:
        sep = "&" if "?" in database_url else "?"
        database_url += f"{sep}sslmode=require"
    elif (
        "railway" in database_url.lower() or ".railway.app" in database_url
    ) and "sslmode" not in database_url:
        sep = "&" if "?" in database_url else "?"
        database_url += f"{sep}sslmode=require"

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "echo": settings.DEBUG,
}

if settings.is_mysql:
    engine_kwargs["pool_recycle"] = 3600

engine = create_engine(database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        dialect = "mysql" if settings.is_mysql else "postgresql"
        parsed = make_url(settings.DATABASE_URL)
        return {
            "status": "connected",
            "dialect": dialect,
            "cluster": "galera" if settings.is_mysql else "postgresql",
            "proxysql": settings.is_mysql
            and (parsed.port == 6033 or "proxysql" in (parsed.host or "").lower()),
            "host": parsed.host,
            "port": parsed.port,
            "database": parsed.database,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
