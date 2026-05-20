"""Persistent OAuth temporary cache models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.core.database import Base


class OAuthProcessedCode(Base):
    __tablename__ = "oauth_processed_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code_key = Column(String(512), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class OAuthTemporaryToken(Base):
    __tablename__ = "oauth_temporary_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    temp_token = Column(String(128), unique=True, index=True, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
