"""
OAuth2 authentication endpoints
Supports Google, GitHub, and Microsoft OAuth2
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
import httpx
from urllib.parse import urlencode

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.models.oauth_account import OAuthAccount

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth2 provider configurations
OAUTH_PROVIDERS = {
    'google': {
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'userinfo_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
        'scopes': ['openid', 'email', 'profile'],
    },
    'github': {
        'authorize_url': 'https://github.com/login/oauth/authorize',
        'token_url': 'https://github.com/login/oauth/access_token',
        'userinfo_url': 'https://api.github.com/user',
        'scopes': ['user:email'],
    },
    'microsoft': {
        'authorize_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        'userinfo_url': 'https://graph.microsoft.com/v1.0/me',
        'scopes': ['openid', 'email', 'profile', 'User.Read'],
    },
}


def get_oauth_client_id(provider: str) -> str:
    """Get OAuth client ID for provider"""
    if provider == 'google':
        return settings.OAUTH_GOOGLE_CLIENT_ID
    elif provider == 'github':
        return settings.OAUTH_GITHUB_CLIENT_ID
    elif provider == 'microsoft':
        return settings.OAUTH_MICROSOFT_CLIENT_ID
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_oauth_client_secret(provider: str) -> str:
    """Get OAuth client secret for provider"""
    if provider == 'google':
        return settings.OAUTH_GOOGLE_CLIENT_SECRET
    elif provider == 'github':
        return settings.OAUTH_GITHUB_CLIENT_SECRET
    elif provider == 'microsoft':
        return settings.OAUTH_MICROSOFT_CLIENT_SECRET
    else:
        raise ValueError(f"Unknown provider: {provider}")


@router.get("/{provider}/authorize")
async def oauth_authorize(provider: str, request: Request):
    """
    Initiate OAuth2 authorization flow
    Redirects user to OAuth provider's login page
    """
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )

    client_id = get_oauth_client_id(provider)
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth2 {provider} is not configured. Please set OAUTH_{provider.upper()}_CLIENT_ID and OAUTH_{provider.upper()}_CLIENT_SECRET"
        )

    provider_config = OAUTH_PROVIDERS[provider]
    # Use OAUTH_CALLBACK_BASE_URL if set, otherwise derive from OAUTH_REDIRECT_BASE_URL
    if settings.OAUTH_CALLBACK_BASE_URL:
        callback_base = settings.OAUTH_CALLBACK_BASE_URL
    else:
        # Fallback: try to derive backend URL from frontend URL
        # This is a workaround - OAUTH_CALLBACK_BASE_URL should be set explicitly
        callback_base = settings.OAUTH_REDIRECT_BASE_URL.replace('supfile-webapp.vercel.app', 'supfile-vercel-app-production.up.railway.app').replace('localhost:3000', 'localhost:8000').replace('http://', 'https://')
    redirect_uri = f"{callback_base}/api/v1/auth/{provider}/callback"
    logger.info(f"OAuth authorize - redirect_uri: {redirect_uri}")

    # Build authorization URL
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(provider_config['scopes']),
        'state': provider,  # Simple state for CSRF protection
    }

    if provider == 'microsoft':
        params['response_mode'] = 'query'

    auth_url = f"{provider_config['authorize_url']}?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    OAuth2 callback endpoint
    Handles the redirect from OAuth provider after user authorization
    """
    # Log all query parameters for debugging
    if request:
        logger.info(f"OAuth callback - Full URL: {request.url}")
        logger.info(f"OAuth callback - Query params: {dict(request.query_params)}")
    
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )

    logger.info(f"OAuth callback received - provider: {provider}, code: {code is not None}, error: {error}, state: {state}")
    
    if error:
        logger.error(f"OAuth2 error from {provider}: {error}")
        return RedirectResponse(
            url=f"{settings.OAUTH_REDIRECT_BASE_URL}/login?error=oauth_error"
        )

    if not code:
        logger.error(f"OAuth2 callback missing code - provider: {provider}")
        if request:
            logger.error(f"OAuth2 callback - Query params: {dict(request.query_params)}")
            logger.error(f"OAuth2 callback - Full URL: {request.url}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided. Please initiate OAuth flow from the login page."
        )

    try:
        # Exchange authorization code for access token
        provider_config = OAUTH_PROVIDERS[provider]
        client_id = get_oauth_client_id(provider)
        client_secret = get_oauth_client_secret(provider)
        # Use OAUTH_CALLBACK_BASE_URL if set, otherwise derive from OAUTH_REDIRECT_BASE_URL
        # IMPORTANT: This must match EXACTLY the redirect_uri used in oauth_authorize
        if settings.OAUTH_CALLBACK_BASE_URL:
            callback_base = settings.OAUTH_CALLBACK_BASE_URL
        else:
            # Fallback: try to derive backend URL from frontend URL
            # This is a workaround - OAUTH_CALLBACK_BASE_URL should be set explicitly
            callback_base = settings.OAUTH_REDIRECT_BASE_URL.replace('supfile-webapp.vercel.app', 'supfile-vercel-app-production.up.railway.app').replace('localhost:3000', 'localhost:8000').replace('http://', 'https://')
        redirect_uri = f"{callback_base}/api/v1/auth/{provider}/callback"
        logger.info(f"OAuth callback - redirect_uri: {redirect_uri}")
        logger.info(f"OAuth callback - OAUTH_CALLBACK_BASE_URL: {settings.OAUTH_CALLBACK_BASE_URL}")
        logger.info(f"OAuth callback - OAUTH_REDIRECT_BASE_URL: {settings.OAUTH_REDIRECT_BASE_URL}")

        # Exchange code for token
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
        }

        if provider == 'github':
            token_data['grant_type'] = 'authorization_code'
            headers = {'Accept': 'application/json'}
        else:
            token_data['grant_type'] = 'authorization_code'
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                provider_config['token_url'],
                data=token_data,
                headers=headers
            )
            token_response.raise_for_status()
            token_info = token_response.json()

        access_token = token_info.get('access_token')
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )

        # Get user info from provider
        userinfo_headers = {'Authorization': f'Bearer {access_token}'}
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(
                provider_config['userinfo_url'],
                headers=userinfo_headers
            )
            
            # Log response for debugging
            if userinfo_response.status_code != 200:
                logger.error(f"OAuth2 userinfo error from {provider}: Status {userinfo_response.status_code}, Response: {userinfo_response.text}")
            
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
            
            # Log userinfo for debugging (without sensitive data)
            logger.info(f"OAuth2 userinfo from {provider}: {list(userinfo.keys())}")

        # Extract user information based on provider
        if provider == 'google':
            email = userinfo.get('email')
            username = userinfo.get('email', '').split('@')[0]  # Use email prefix as username
            full_name = userinfo.get('name')
            provider_user_id = userinfo.get('id')
        elif provider == 'github':
            email = userinfo.get('email')
            if not email:
                # GitHub may require additional API call for email
                async with httpx.AsyncClient() as client:
                    email_response = await client.get(
                        'https://api.github.com/user/emails',
                        headers=userinfo_headers
                    )
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        email = next((e['email'] for e in emails if e.get('primary')), emails[0]['email'] if emails else None)
            username = userinfo.get('login')
            full_name = userinfo.get('name')
            provider_user_id = str(userinfo.get('id'))
        elif provider == 'microsoft':
            # Microsoft Graph API returns different fields
            # Try multiple possible email fields
            email = (
                userinfo.get('mail') or 
                userinfo.get('userPrincipalName') or 
                userinfo.get('otherMails', [None])[0] if userinfo.get('otherMails') else None
            )
            
            # Generate username from email or display name
            if email:
                username = email.split('@')[0]
            else:
                username = userinfo.get('displayName', 'user').replace(' ', '_').lower()
                # Remove special characters
                username = ''.join(c for c in username if c.isalnum() or c in ['_', '-'])
            
            full_name = userinfo.get('displayName') or userinfo.get('givenName', '') + ' ' + userinfo.get('surname', '')
            provider_user_id = userinfo.get('id') or userinfo.get('objectId')
            
            # Log extracted info for debugging
            logger.info(f"Microsoft OAuth extracted - email: {email}, username: {username}, id: {provider_user_id}")

        if not email or not provider_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from OAuth provider"
            )

        # Check if OAuth account already exists
        oauth_account = db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id
        ).first()

        if oauth_account:
            # Existing OAuth account - update tokens and return JWT
            user = db.query(User).filter(User.id == oauth_account.user_id).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive"
                )
        else:
            # New OAuth account - check if user exists by email
            user = db.query(User).filter(User.email == email).first()

            if user:
                # User exists - link OAuth account
                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=provider_user_id,
                    provider_email=email,
                    access_token=access_token,  # In production, encrypt this
                )
                db.add(oauth_account)
            else:
                # New user - create account
                # Generate unique username if needed
                base_username = username
                counter = 1
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User(
                    email=email,
                    username=username,
                    hashed_password=None,  # OAuth users don't have passwords
                    full_name=full_name,
                    is_active=True,
                )
                db.add(user)
                db.flush()  # Get user.id

                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=provider_user_id,
                    provider_email=email,
                    access_token=access_token,  # In production, encrypt this
                )
                db.add(oauth_account)

        db.commit()
        db.refresh(user)

        # Generate JWT tokens
        access_token_jwt = create_access_token(data={"sub": str(user.id), "username": user.username})
        refresh_token_jwt = create_refresh_token(data={"sub": str(user.id), "username": user.username})

        # Redirect to frontend with tokens
        redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL}/auth/callback?access_token={access_token_jwt}&refresh_token={refresh_token_jwt}"
        return RedirectResponse(url=redirect_url)

    except httpx.HTTPStatusError as e:
        logger.error(f"OAuth2 HTTP error from {provider}: {e.response.text}")
        return RedirectResponse(
            url=f"{settings.OAUTH_REDIRECT_BASE_URL}/login?error=oauth_http_error"
        )
    except Exception as e:
        logger.error(f"OAuth2 error from {provider}: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.OAUTH_REDIRECT_BASE_URL}/login?error=oauth_error"
        )

