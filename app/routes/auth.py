"""
Authentication routes for login/logout functionality.

Provides web interface for token-based authentication with session management.
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND, HTTP_401_UNAUTHORIZED

from app.config import get_config
from app.dependencies.auth_dependency import verify_auth_token
from app.services.auth_service import get_auth_service
from common.app_logging import create_logging

logger = create_logging()

# Create routers for API and view endpoints
auth_api_router = APIRouter(prefix="/api/auth", tags=["auth-api"])
auth_views_router = APIRouter(
    prefix="/auth", tags=["auth-views"], include_in_schema=False
)

# Template configuration
templates = Jinja2Templates(directory="app/templates")


@auth_views_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display the login page."""
    config = get_config()
    return templates.TemplateResponse(
        "login.html", {"request": request, "config": config}
    )


@auth_api_router.post("/login")
async def api_login(request: Request, email: str = Form(...), token: str = Form(...)):
    """
    API endpoint for token authentication.

    Sets session cookie on successful authentication.
    """
    try:
        auth_service = get_auth_service()
    except RuntimeError:
        logger.error("Auth service not initialized")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Authentication service not available",
        )

    # For backward compatibility, check if this is a legacy token (no email-specific validation)
    if auth_service.validate_token(token):
        # This is a legacy token - validate it the old way
        logger.info(f"Legacy token login from {request.client.host}")
        response = Response(
            content='{"status": "success", "message": "Authentication successful (legacy)"}'
        )
        response.set_cookie(
            key="auth_token",
            value=token,
            max_age=24 * 60 * 60,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
        )
        return response

    # Try multi-user authentication
    from app.services.multi_user_auth_service import get_multi_user_auth_service

    try:
        multi_user_service = get_multi_user_auth_service()
        if multi_user_service.validate_user_token(email, token):
            logger.info(
                f"Multi-user login successful for {email} from {request.client.host}"
            )

            # Create response with session cookie that includes email context
            response = Response(
                content='{"status": "success", "message": "Authentication successful"}'
            )
            response.set_cookie(
                key="auth_token",
                value=token,
                max_age=24 * 60 * 60,  # 24 hours
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax",
            )
            response.set_cookie(
                key="user_email",
                value=email,
                max_age=24 * 60 * 60,  # 24 hours
                httponly=True,
                secure=False,
                samesite="lax",
            )
            return response
        else:
            logger.warning(
                f"Invalid multi-user login attempt for {email} from {request.client.host}"
            )
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid email or authentication token",
            )
    except Exception as e:
        logger.error(f"Multi-user authentication error: {e}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


@auth_views_router.post("/login")
async def view_login(request: Request, email: str = Form(...), token: str = Form(...)):
    """
    View endpoint for login form submission.

    Returns HTMX-compatible response for form handling.
    """
    try:
        auth_service = get_auth_service()
    except RuntimeError:
        logger.error("Auth service not initialized")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Service Error!</strong> Authentication service not available. Please try again later.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    # For backward compatibility, check if this is a legacy token first
    if auth_service.validate_token(token):
        # This is a legacy token - validate it the old way
        logger.info(f"Legacy token login from {request.client.host}")
        response = HTMLResponse(
            content="""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Authentication successful (legacy mode). Redirecting to dashboard...
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
        )
        response.set_cookie(
            key="auth_token",
            value=token,
            max_age=24 * 60 * 60,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
        )
        return response

    # Try multi-user authentication
    from app.services.multi_user_auth_service import get_multi_user_auth_service

    try:
        multi_user_service = get_multi_user_auth_service()
        if multi_user_service.validate_user_token(email, token):
            logger.info(
                f"Multi-user login successful for {email} from {request.client.host}"
            )

            # Get user info for personalized message
            user = multi_user_service.get_user_by_email(email)
            username = user.username if user and user.username else email.split("@")[0]

            response = HTMLResponse(
                content=f"""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <strong>Welcome back, {username}!</strong> Authentication successful. Redirecting to dashboard...
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """
            )
            response.set_cookie(
                key="auth_token",
                value=token,
                max_age=24 * 60 * 60,  # 24 hours
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax",
            )
            response.set_cookie(
                key="user_email",
                value=email,
                max_age=24 * 60 * 60,  # 24 hours
                httponly=True,
                secure=False,
                samesite="lax",
            )
            return response
        else:
            logger.warning(
                f"Invalid multi-user login attempt for {email} from {request.client.host}"
            )
            return """
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Authentication Failed!</strong> Invalid email or token combination. Please check your credentials.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """
    except Exception as e:
        logger.error(f"Multi-user authentication error: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Authentication Error!</strong> Unable to validate credentials. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@auth_api_router.post("/logout")
async def api_logout(request: Request):
    """API endpoint for logout."""
    response = Response(
        content='{"status": "success", "message": "Logged out successfully"}'
    )
    response.delete_cookie(key="auth_token")
    response.delete_cookie(key="user_email")

    logger.info(f"User logged out from {request.client.host}")
    return response


@auth_views_router.post("/logout")
async def view_logout(request: Request):
    """View endpoint for logout - redirects to login page."""
    response = RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)
    response.delete_cookie(key="auth_token")
    response.delete_cookie(key="user_email")

    logger.info(f"User logged out from {request.client.host}")
    return response


@auth_api_router.get("/status")
async def auth_status(request: Request, current_user: str = Depends(verify_auth_token)):
    """
    Check authentication status.

    Returns user information if authenticated.
    """
    return {"authenticated": True, "token_valid": True, "client_ip": request.client.host}


@auth_views_router.get("/status")
async def view_auth_status(request: Request):
    """
    View endpoint for authentication status check.

    Returns JSON for HTMX status checks.
    """
    try:
        # Try to verify token from cookie
        token = request.cookies.get("auth_token")
        user_email = request.cookies.get("user_email")

        if not token:
            return {"authenticated": False, "reason": "No token cookie"}

        try:
            auth_service = get_auth_service()
        except RuntimeError:
            return {"authenticated": False, "reason": "Auth service not available"}

        # Check legacy token first
        if auth_service.validate_token(token):
            return {
                "authenticated": True,
                "token_valid": True,
                "user_type": "legacy",
                "client_ip": request.client.host,
            }

        # Check multi-user token
        if user_email:
            from app.services.multi_user_auth_service import get_multi_user_auth_service

            try:
                multi_user_service = get_multi_user_auth_service()
                if multi_user_service.validate_user_token(user_email, token):
                    user = multi_user_service.get_user_by_email(user_email)
                    return {
                        "authenticated": True,
                        "token_valid": True,
                        "user_type": "multi_user",
                        "user_email": user_email,
                        "username": user.username if user else None,
                        "is_admin": user.is_admin if user else False,
                        "client_ip": request.client.host,
                    }
            except Exception as e:
                logger.error(f"Multi-user auth status check failed: {e}")

        return {"authenticated": False, "reason": "Invalid token"}

    except Exception as e:
        logger.error(f"Auth status check failed: {e}")
        return {"authenticated": False, "reason": "Validation error"}


# Utility function to check if user is authenticated via cookie
def get_auth_token_from_cookie(request: Request) -> str | None:
    """
    Extract and validate auth token from request cookie.

    Returns:
        Valid token string or None if invalid/missing
    """
    token = request.cookies.get("auth_token")
    user_email = request.cookies.get("user_email")

    if not token:
        return None

    try:
        auth_service = get_auth_service()

        # Check legacy token first
        if auth_service.validate_token(token):
            return token

        # Check multi-user token if we have email context
        if user_email:
            from app.services.multi_user_auth_service import get_multi_user_auth_service

            try:
                multi_user_service = get_multi_user_auth_service()
                if multi_user_service.validate_user_token(user_email, token):
                    return token
            except Exception as e:
                logger.error(f"Multi-user token validation error in cookie helper: {e}")

    except RuntimeError:
        logger.error("Auth service not initialized in get_auth_token_from_cookie")
        return None
    return None
