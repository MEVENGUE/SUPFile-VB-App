"""
OAuth2 authentication endpoints
Supports Google, GitHub, and Microsoft OAuth2
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
import httpx
from urllib.parse import urlencode, quote

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.models.oauth_account import OAuthAccount

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache pour éviter de traiter le même code OAuth plusieurs fois
# Les codes sont valides seulement quelques minutes, donc on peut les garder en cache
_processed_oauth_codes = set()

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
        callback_base = settings.OAUTH_CALLBACK_BASE_URL.rstrip('/')
    else:
        # Fallback: try to derive backend URL from frontend URL
        # This is a workaround - OAUTH_CALLBACK_BASE_URL should be set explicitly
        callback_base = settings.OAUTH_REDIRECT_BASE_URL.replace('supfile-webapp.vercel.app', 'supfile-vercel-app-production.up.railway.app').replace('localhost:3000', 'localhost:8000').replace('http://', 'https://').rstrip('/')
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
        if code_key in _processed_oauth_codes:
            logger.warning(f"OAuth callback - Code already processed, redirecting to frontend: {code_key_short}")
            # Code already processed, redirect to frontend with error
            error_message = quote("Ce code d'autorisation a déjà été utilisé. Veuillez réessayer.", safe='')
            redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_code_expired&message={error_message}"
            return RedirectResponse(url=redirect_url, status_code=302)
        # Mark code as being processed (will be removed if invalid_grant error occurs)
        _processed_oauth_codes.add(code_key)
        logger.info(f"OAuth callback - Added code to cache: {code_key_short} (cache size: {len(_processed_oauth_codes)})")
        # Clean old codes (keep only last 1000 to prevent memory leak)
        if len(_processed_oauth_codes) > 1000:
            _processed_oauth_codes.clear()
            logger.info("OAuth callback - Cleared processed codes cache")
    
    if error:
        logger.error(f"OAuth2 error from {provider}: {error}")
        error_param = quote(error, safe='')
        redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_error&message={error_param}"
        return RedirectResponse(url=redirect_url, status_code=302)

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
            callback_base = settings.OAUTH_CALLBACK_BASE_URL.rstrip('/')
        else:
            # Fallback: try to derive backend URL from frontend URL
            # This is a workaround - OAUTH_CALLBACK_BASE_URL should be set explicitly
            callback_base = settings.OAUTH_REDIRECT_BASE_URL.replace('supfile-webapp.vercel.app', 'supfile-vercel-app-production.up.railway.app').replace('localhost:3000', 'localhost:8000').replace('http://', 'https://').rstrip('/')
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
                    # Remove code from cache if invalid_grant (code might be expired, allow retry)
                    if code and code_key:
                        code_key_full = f"{provider}:{code}"
                        _processed_oauth_codes.discard(code_key_full)
                        logger.info(f"OAuth callback - Removed invalid code from cache: {code_key} (cache size: {len(_processed_oauth_codes)})")
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
                    # Remove code from cache if invalid_grant (code might be expired, allow retry)
                    if code and code_key:
                        code_key_full = f"{provider}:{code}"
                        _processed_oauth_codes.discard(code_key_full)
                        logger.info(f"OAuth callback - Removed invalid code from cache: {code_key} (cache size: {len(_processed_oauth_codes)})")
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

        # Redirect to frontend with tokens using URL fragment (#) instead of query params
        # Use JavaScript redirect to ensure fragment is preserved (avoids ERR_INVALID_REDIRECT)
        redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/auth/callback#access_token={quote(access_token_jwt, safe='')}&refresh_token={quote(refresh_token_jwt, safe='')}"
        logger.info(f"OAuth success - redirecting to frontend (URL length: {len(redirect_url)})")
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
                        _processed_oauth_codes.discard(code_key_full)
                        logger.info(f"OAuth callback - Removed invalid code from cache (cache size: {len(_processed_oauth_codes)})")
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
                _processed_oauth_codes.discard(code_key_full)
                logger.info(f"OAuth callback - Removed invalid code from cache (cache size: {len(_processed_oauth_codes)})")
        error_message_encoded = quote(error_message, safe='')
        redirect_url = f"{settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')}/login?error=oauth_error&message={error_message_encoded}"
        return RedirectResponse(url=redirect_url, status_code=302)

