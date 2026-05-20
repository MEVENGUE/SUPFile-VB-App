"""
OAuth2 authentication endpoints
Supports Google, GitHub, and Microsoft OAuth2
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict
import logging
import httpx
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.models.oauth_account import OAuthAccount
from app.models.oauth_cache import OAuthProcessedCode, OAuthTemporaryToken

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache persistant pour éviter de traiter le même code OAuth plusieurs fois
# et pour stocker temporairement les tokens JWT avant redirection.
TOKEN_CACHE_EXPIRY = 300  # 5 minutes en secondes
PROCESSED_CODE_EXPIRY = 300  # 5 minutes


def _cleanup_expired_oauth_entries(db: Session):
    now = datetime.utcnow()
    db.query(OAuthProcessedCode).filter(OAuthProcessedCode.expires_at < now).delete(synchronize_session=False)
    db.query(OAuthTemporaryToken).filter(OAuthTemporaryToken.expires_at < now).delete(synchronize_session=False)
    db.commit()


def _is_oauth_code_processed(db: Session, code_key: str) -> bool:
    _cleanup_expired_oauth_entries(db)
    existing = db.query(OAuthProcessedCode).filter(OAuthProcessedCode.code_key == code_key).first()
    return existing is not None


def _mark_oauth_code_processed(db: Session, code_key: str):
    expires_at = datetime.utcnow() + timedelta(seconds=PROCESSED_CODE_EXPIRY)
    entry = OAuthProcessedCode(code_key=code_key, expires_at=expires_at)
    db.merge(entry)
    db.commit()


def _store_temporary_oauth_token(db: Session, temp_token: str, access_token: str, refresh_token: str):
    expires_at = datetime.utcnow() + timedelta(seconds=TOKEN_CACHE_EXPIRY)
    temporary = OAuthTemporaryToken(
        temp_token=temp_token,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    db.merge(temporary)
    db.commit()


def _pop_temporary_oauth_token(db: Session, temp_token: str) -> Optional[OAuthTemporaryToken]:
    _cleanup_expired_oauth_entries(db)
    token_entry = db.query(OAuthTemporaryToken).filter(OAuthTemporaryToken.temp_token == temp_token).first()
    if token_entry:
        db.delete(token_entry)
        db.commit()
    return token_entry

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
        'scopes': ['openid', 'email', 'profile', 'User.Read', 'offline_access'],
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
@limiter.limit("10/minute")
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
    callback_base = settings.backend_public_url
    redirect_uri = f"{callback_base}/api/v1/auth/{provider}/callback"
    logger.info(f"OAuth authorize - provider: {provider}, redirect_uri: {redirect_uri}")
    logger.info(f"OAuth authorize - OAUTH_CALLBACK_BASE_URL: {settings.OAUTH_CALLBACK_BASE_URL}")
    logger.info(f"OAuth authorize - OAUTH_REDIRECT_BASE_URL: {settings.OAUTH_REDIRECT_BASE_URL}")

    # Build authorization URL
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(provider_config['scopes']),
        'state': provider,  # Simple state for CSRF protection
    }

    if provider == 'microsoft':
        # Use form_post to avoid ERR_INVALID_REDIRECT with long URLs
        params['response_mode'] = 'form_post'

    auth_url = f"{provider_config['authorize_url']}?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/{provider}/callback")
@router.post("/{provider}/callback")
@limiter.limit("15/minute")
async def oauth_callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None
):
    """
    OAuth2 callback endpoint
    Handles the redirect from OAuth provider after user authorization
    Supports both GET (query) and POST (form_post) response modes
    """
    # For POST requests (form_post mode, used by Microsoft), get data from form
    if request.method == "POST":
        try:
            form_data = await request.form()
            code = form_data.get("code") or code
            error = form_data.get("error") or error
            state = form_data.get("state") or state
            logger.info(f"OAuth callback - POST request, form data: code={code is not None}, error={error}, state={state}")
        except Exception as e:
            logger.error(f"OAuth callback - Error reading form data: {str(e)}")
    else:
        # For GET requests, get from query parameters
        code = request.query_params.get("code") or code
        error = request.query_params.get("error") or error
        state = request.query_params.get("state") or state
        
        # Special handling for Microsoft: if GET request arrives after POST (form_post mode),
        # it might be a browser redirect/follow-up without the code.
        # Check if this is Microsoft and if we already processed a POST for this session
        if provider == 'microsoft' and not code and not error:
            logger.info(f"OAuth callback - GET request for Microsoft without code (likely follow-up after form_post). Redirecting to frontend.")
            # Redirect to frontend login page - the POST should have already handled the OAuth flow
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login"
            return RedirectResponse(url=redirect_url, status_code=302)
    
    # Log all parameters for debugging
    logger.info(f"OAuth callback - Method: {request.method}, Full URL: {request.url}")
    logger.info(f"OAuth callback - Query params: {dict(request.query_params)}")
    logger.info(f"OAuth callback - Final values: code={code is not None}, error={error}, state={state}")
    
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )

    logger.info(f"OAuth callback received - provider: {provider}, code: {code is not None}, error: {error}, state: {state}")
    
    # Check if this code has already been processed (prevent duplicate processing)
    code_key = None
    if code:
        code_key = f"{provider}:{code}"
        code_key_short = f"{provider}:{code[:30]}..." if len(code) > 30 else code_key
        if _is_oauth_code_processed(db, code_key):
            logger.warning(f"OAuth callback - Code already processed, redirecting to frontend: {code_key_short}")
            error_message = quote("Ce code d'autorisation a déjà été utilisé. Veuillez réessayer.", safe='')
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_code_expired&message={error_message}"
            return RedirectResponse(url=redirect_url, status_code=302)
        _mark_oauth_code_processed(db, code_key)
        logger.info(f"OAuth callback - Added code to persistent cache: {code_key_short}")
    
    if error:
        logger.error(f"OAuth2 error from {provider}: {error}")
        error_param = quote(error, safe='')
        redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_error&message={error_param}"
        return RedirectResponse(url=redirect_url, status_code=302)

    if not code:
        # For Microsoft with form_post, if we get here it means POST already processed
        # For other providers, this is an error
        if provider == 'microsoft' and request.method == 'GET':
            logger.info(f"OAuth callback - Microsoft GET without code (POST already processed). Redirecting to frontend.")
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login"
            return RedirectResponse(url=redirect_url, status_code=302)
        
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
        callback_base = settings.backend_public_url
        redirect_uri = f"{callback_base}/api/v1/auth/{provider}/callback"
        logger.info(f"OAuth callback - provider: {provider}, redirect_uri: {redirect_uri}")
        logger.info(f"OAuth callback - OAUTH_CALLBACK_BASE_URL: {settings.OAUTH_CALLBACK_BASE_URL}")
        logger.info(f"OAuth callback - OAUTH_REDIRECT_BASE_URL: {settings.OAUTH_REDIRECT_BASE_URL}")
        logger.info(f"OAuth callback - code length: {len(code) if code else 0}")

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
                headers=headers,
                timeout=30.0
            )
            
            # Check for errors in response
            # GitHub may return errors even with status 200, so check the response body first
            try:
                token_info = token_response.json()
            except Exception:
                # If response is not JSON, treat as error
                error_text = token_response.text
                logger.error(f"OAuth2 token exchange failed - Invalid JSON response: {error_text}")
                error_message = quote("Réponse invalide du serveur OAuth.", safe='')
                redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_http_error&message={error_message}"
                return RedirectResponse(url=redirect_url, status_code=302)
            
            # Check for errors in JSON response (GitHub may return errors with status 200)
            if 'error' in token_info:
                error_code = token_info.get('error', 'unknown_error')
                error_description = token_info.get('error_description', token_info.get('error_description', 'Erreur OAuth inconnue'))
                logger.error(f"OAuth2 error in response from {provider}: {error_code} - {error_description}")
                
                if error_code == 'invalid_grant' or error_code == 'bad_verification_code':
                    if code and code_key:
                        code_key_full = f"{provider}:{code}"
                        db.query(OAuthProcessedCode).filter(OAuthProcessedCode.code_key == code_key_full).delete()
                        db.commit()
                        logger.info(f"OAuth callback - Removed invalid code from persistent cache: {code_key}")
                    error_message = quote("Le code d'autorisation a expiré ou a déjà été utilisé. Veuillez réessayer.", safe='')
                    redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_code_expired&message={error_message}"
                    logger.info(f"OAuth redirecting to frontend (invalid_grant): {redirect_url}")
                    return RedirectResponse(url=redirect_url, status_code=302)
                elif error_code == 'invalid_client':
                    error_message = quote("Configuration OAuth incorrecte. Contactez l'administrateur.", safe='')
                    redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_config_error&message={error_message}"
                    return RedirectResponse(url=redirect_url, status_code=302)
                else:
                    error_message_encoded = quote(error_description, safe='')
                    redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_error&message={error_message_encoded}"
                    return RedirectResponse(url=redirect_url, status_code=302)
            
            # Check HTTP status code
            if token_response.status_code != 200:
                error_text = token_response.text
                logger.error(f"OAuth2 token exchange failed - Status: {token_response.status_code}, Response: {error_text}")
                
                # Try to parse error response (token_info already parsed above)
                error_code = token_info.get('error', 'unknown_error') if 'error' in token_info else 'http_error'
                error_description = token_info.get('error_description', error_text) if 'error_description' in token_info else error_text
                
                # Handle specific OAuth errors
                if error_code == 'invalid_grant' or error_code == 'bad_verification_code':
                    logger.error(f"OAuth2 invalid_grant error from {provider} - Code may have expired or already been used")
                    if code and code_key:
                        code_key_full = f"{provider}:{code}"
                        db.query(OAuthProcessedCode).filter(OAuthProcessedCode.code_key == code_key_full).delete()
                        db.commit()
                        logger.info(f"OAuth callback - Removed invalid code from persistent cache: {code_key}")
                    error_message = quote("Le code d'autorisation a expiré ou a déjà été utilisé. Veuillez réessayer.", safe='')
                    redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_code_expired&message={error_message}"
                    logger.info(f"OAuth redirecting to frontend (invalid_grant): {redirect_url}")
                    return RedirectResponse(url=redirect_url, status_code=302)
                elif error_code == 'invalid_client':
                    logger.error(f"OAuth2 invalid_client error from {provider} - Client credentials may be incorrect")
                    error_message = quote("Configuration OAuth incorrecte. Contactez l'administrateur.", safe='')
                    redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_config_error&message={error_message}"
                    return RedirectResponse(url=redirect_url, status_code=302)
                else:
                    logger.error(f"OAuth2 error from {provider}: {error_code} - {error_description}")
                    error_message_encoded = quote(error_description, safe='')
                    redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_error&message={error_message_encoded}"
                    return RedirectResponse(url=redirect_url, status_code=302)

        access_token = token_info.get('access_token')
        if not access_token:
            # Check if there's an error in the response
            error = token_info.get('error')
            error_description = token_info.get('error_description', 'Failed to obtain access token')
            logger.error(f"OAuth2 failed to obtain access token from {provider}: {error} - {error_description}")
            error_message_encoded = quote(error_description, safe='')
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_token_error&message={error_message_encoded}"
            return RedirectResponse(url=redirect_url, status_code=302)

        # Get user info from provider
        userinfo_headers = {'Authorization': f'Bearer {access_token}'}
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(
                provider_config['userinfo_url'],
                headers=userinfo_headers,
                timeout=30.0
            )
            
            # Log response for debugging
            if userinfo_response.status_code != 200:
                logger.error(f"OAuth2 userinfo error from {provider}: Status {userinfo_response.status_code}, Response: {userinfo_response.text}")
                error_message_encoded = quote(f"Erreur lors de la récupération des informations utilisateur: {userinfo_response.status_code}", safe='')
                redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_userinfo_error&message={error_message_encoded}"
                return RedirectResponse(url=redirect_url, status_code=302)
            
            try:
                userinfo = userinfo_response.json()
            except Exception as e:
                logger.error(f"OAuth2 userinfo JSON parse error from {provider}: {str(e)}, Response: {userinfo_response.text}")
                error_message_encoded = quote("Réponse invalide du serveur OAuth.", safe='')
                redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_userinfo_error&message={error_message_encoded}"
                return RedirectResponse(url=redirect_url, status_code=302)
            
            # Log userinfo for debugging (without sensitive data)
            logger.info(f"OAuth2 userinfo from {provider}: {list(userinfo.keys())}")
            logger.info(f"OAuth2 userinfo content (sanitized): email={userinfo.get('email') or userinfo.get('mail') or userinfo.get('userPrincipalName')}, id={userinfo.get('id') or userinfo.get('objectId')}")

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
                (userinfo.get('otherMails', [None])[0] if userinfo.get('otherMails') and len(userinfo.get('otherMails', [])) > 0 else None)
            )
            
            # Generate username from email or display name
            if email:
                username = email.split('@')[0]
                # Remove special characters and make lowercase
                username = ''.join(c for c in username if c.isalnum() or c in ['_', '-']).lower()
            else:
                display_name = userinfo.get('displayName') or userinfo.get('givenName', '') or 'user'
                username = display_name.replace(' ', '_').lower()
                # Remove special characters
                username = ''.join(c for c in username if c.isalnum() or c in ['_', '-'])
            
            # Get full name
            full_name = userinfo.get('displayName')
            if not full_name:
                given_name = userinfo.get('givenName', '')
                surname = userinfo.get('surname', '')
                full_name = f"{given_name} {surname}".strip() if given_name or surname else None
            
            # Get provider user ID (can be 'id' or 'objectId' depending on API version)
            provider_user_id = userinfo.get('id') or userinfo.get('objectId')
            
            # Log extracted info for debugging
            logger.info(f"Microsoft OAuth extracted - email: {email}, username: {username}, id: {provider_user_id}, full_name: {full_name}")
            logger.info(f"Microsoft OAuth userinfo keys: {list(userinfo.keys())}")

        if not email:
            logger.error(f"OAuth2 - No email found for {provider}. Userinfo keys: {list(userinfo.keys())}")
            error_message_encoded = quote("Impossible de récupérer l'email depuis le compte Microsoft. Vérifiez que votre compte Microsoft a un email associé.", safe='')
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_no_email&message={error_message_encoded}"
            return RedirectResponse(url=redirect_url, status_code=302)
        
        if not provider_user_id:
            logger.error(f"OAuth2 - No user ID found for {provider}. Userinfo keys: {list(userinfo.keys())}")
            error_message_encoded = quote("Impossible de récupérer l'ID utilisateur depuis le compte Microsoft.", safe='')
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_no_user_id&message={error_message_encoded}"
            return RedirectResponse(url=redirect_url, status_code=302)

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

        # For Microsoft, use temporary token cache to avoid ERR_INVALID_REDIRECT
        # For Google and GitHub, use fragment URL with JavaScript redirect (works well)
        if provider == 'microsoft':
            # Store tokens in temporary cache with short-lived token to avoid long URLs
            temp_token = str(uuid.uuid4())
            _store_temporary_oauth_token(db, temp_token, access_token_jwt, refresh_token_jwt)
            
            # Redirect to frontend with short temporary token
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/auth/callback?token={temp_token}"
            logger.info(f"OAuth success (Microsoft) - redirecting to frontend with temp token (URL length: {len(redirect_url)})")
            
            # Use HTML response with JavaScript redirect to preserve the token in URL
            # This prevents the browser from making a GET request to the callback URL
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Redirection...</title>
            </head>
            <body>
                <p>Connexion réussie! Redirection en cours...</p>
                <script>
                    window.location.replace({repr(redirect_url)});
                </script>
                <noscript>
                    <meta http-equiv="refresh" content="0; url={redirect_url}">
                    <p>Si la redirection ne fonctionne pas, <a href="{redirect_url}">cliquez ici</a>.</p>
                </noscript>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=200)
        else:
            # For Google and GitHub: use fragment URL with JavaScript redirect
            # This avoids ERR_INVALID_REDIRECT while keeping the flow simple
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/auth/callback#access_token={quote(access_token_jwt, safe='')}&refresh_token={quote(refresh_token_jwt, safe='')}"
            logger.info(f"OAuth success ({provider}) - redirecting to frontend with fragment (URL length: {len(redirect_url)})")
            logger.info(f"OAuth success - OAUTH_REDIRECT_BASE_URL: {settings.OAUTH_REDIRECT_BASE_URL}")
            
            # Use HTML response with JavaScript redirect to preserve URL fragment
            # This avoids ERR_INVALID_REDIRECT errors that can occur with HTTP redirects and fragments
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Redirection...</title>
            </head>
            <body>
                <p>Connexion réussie! Redirection en cours...</p>
                <script>
                    window.location.href = {repr(redirect_url)};
                </script>
                <noscript>
                    <meta http-equiv="refresh" content="0; url={redirect_url}">
                    <p>Si la redirection ne fonctionne pas, <a href="{redirect_url}">cliquez ici</a>.</p>
                </noscript>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=200)

    except httpx.HTTPStatusError as e:
        error_text = e.response.text if hasattr(e, 'response') else str(e)
        status_code = e.response.status_code if hasattr(e, 'response') else 500
        logger.error(f"OAuth2 HTTP error from {provider}: Status {status_code}, Response: {error_text}")
        
        # Try to parse error response
        try:
            if hasattr(e, 'response'):
                error_data = e.response.json()
                error_code = error_data.get('error', 'http_error')
                error_description = error_data.get('error_description', error_text)
                
                if error_code == 'invalid_grant':
                    # Remove code from cache if invalid_grant
                    if code:
                        code_key_full = f"{provider}:{code}"
                        db.query(OAuthProcessedCode).filter(OAuthProcessedCode.code_key == code_key_full).delete()
                        db.commit()
                        logger.info("OAuth callback - Removed invalid code from persistent cache")
                    error_message = quote("Le code d'autorisation a expiré. Veuillez réessayer.", safe='')
                    redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_code_expired&message={error_message}"
                    return RedirectResponse(url=redirect_url, status_code=302)
                else:
                    return RedirectResponse(
                        url=f"{settings.OAUTH_REDIRECT_BASE_URL}/login?error=oauth_http_error&message={error_description}"
                    )
        except Exception:
            pass
        
        error_message = quote("Erreur HTTP lors de la connexion OAuth.", safe='')
        redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_http_error&message={error_message}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except httpx.TimeoutException as e:
        logger.error(f"OAuth2 timeout error from {provider}: {str(e)}")
        error_message = quote("Timeout lors de la connexion OAuth. Veuillez réessayer.", safe='')
        redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_timeout&message={error_message}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        logger.error(f"OAuth2 error from {provider}: {str(e)}", exc_info=True)
        error_message = "Une erreur inattendue s'est produite lors de la connexion OAuth."
        if "invalid_grant" in str(e).lower():
            error_message = "Le code d'autorisation a expiré ou a déjà été utilisé. Veuillez réessayer."
            # Remove code from cache if invalid_grant
            if code:
                code_key_full = f"{provider}:{code}"
                db.query(OAuthProcessedCode).filter(OAuthProcessedCode.code_key == code_key_full).delete()
                db.commit()
                logger.info(f"OAuth callback - Removed invalid code from persistent cache")
        error_message_encoded = quote(error_message, safe='')
        redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_error&message={error_message_encoded}"
        return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/exchange-token/{temp_token}")
@limiter.limit("10/minute")
async def exchange_oauth_token(
    temp_token: str,
    db: Session = Depends(get_db)
):
    """
    Exchange temporary OAuth token for JWT tokens
    This endpoint is called by the frontend after OAuth redirect (Microsoft only)
    IMPORTANT: Route name is /exchange-token/ to avoid conflict with /{provider}/callback
    """
    logger.info(f"OAuth token exchange request - temp_token: {temp_token[:20]}...")
    
    # Check if token exists in cache
    token_data = _pop_temporary_oauth_token(db, temp_token)
    if token_data is None:
        logger.warning(f"OAuth token exchange - Token not found in persistent cache: {temp_token[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found or expired"
        )

    if datetime.utcnow() > token_data.expires_at:
        logger.warning(f"OAuth token exchange - Token expired: {temp_token[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Token expired"
        )

    access_token = token_data.access_token
    refresh_token = token_data.refresh_token
    
    logger.info(f"OAuth token exchange - Success, token removed from cache")
    
    return JSONResponse(content={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    })

