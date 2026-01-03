"""
OAuthAccount model for OAuth2 authentication
Links OAuth providers (Google, GitHub, Microsoft) to users
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class OAuthAccount(Base):
    """
    Model for OAuth2 provider accounts
    Links external OAuth accounts to local users
    """
    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # 'google', 'github', 'microsoft'
    provider_user_id = Column(String, nullable=False)  # User ID from OAuth provider
    provider_email = Column(String, nullable=True)  # Email from OAuth provider
    access_token = Column(String, nullable=True)  # OAuth access token (encrypted)
    refresh_token = Column(String, nullable=True)  # OAuth refresh token (encrypted)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="oauth_accounts")

    # Unique constraint: one OAuth account per provider per user
    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_user'),
    )

    def __repr__(self):
        return f"<OAuthAccount(id={self.id}, provider={self.provider}, user_id={self.user_id})>"

