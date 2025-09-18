"""
Authentication routes for login/logout functionality.

Provides web interface for token-based authentication with session management.
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND, HTTP_401_UNAUTHORIZED

from app.config import get_config
from app.dependencies.multi_user_auth_dependency import verify_multi_user_auth_token
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
async def auth_status(
    request: Request, auth_context=Depends(verify_multi_user_auth_token)
):
    """
    Check authentication status.

    Returns user information if authenticated.
    """
    return {
        "authenticated": True,
        "token_valid": True,
        "user_email": auth_context.user_email,
        "username": auth_context.username,
        "is_admin": auth_context.is_admin,
        "client_ip": request.client.host,
    }


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

    # Check multi-user token if we have email context
    if user_email:
        from app.services.multi_user_auth_service import get_multi_user_auth_service

        try:
            multi_user_service = get_multi_user_auth_service()
            if multi_user_service.validate_user_token(user_email, token):
                return token
        except Exception as e:
            logger.error(f"Multi-user token validation error in cookie helper: {e}")

    return None


@auth_views_router.post("/send-token")
async def send_token(request: Request, email: str = Form(...)):
    """
    Send a new authentication token to a user's email.

    Returns generic success message regardless of whether email exists
    to prevent email enumeration attacks.
    """
    try:
        from app.services.multi_user_auth_service import get_multi_user_auth_service

        # Always return generic success message to prevent email enumeration
        success_message = """
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Token Sent!</strong> If your email is registered in the system, you will receive a new authentication token shortly.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

        try:
            multi_user_service = get_multi_user_auth_service()

            # Check if user exists (but don't reveal this information)
            user = multi_user_service.get_user_by_email(email)

            if user and user.is_active:
                # Generate and send new token
                await multi_user_service.generate_user_token(email, send_email=True)
                logger.info(
                    f"New token sent to registered user {email} from {request.client.host}"
                )
            else:
                # User doesn't exist or is inactive - log this but return same message
                logger.warning(
                    f"Token request for non-existent/inactive user {email} from {request.client.host}"
                )

        except Exception as e:
            # Even if there's an error, return success message to prevent info leakage
            logger.error(f"Error during send-token for {email}: {e}")

        return HTMLResponse(content=success_message)

    except Exception as e:
        logger.error(f"Send token error: {e}")
        # Return generic error message
        return HTMLResponse(
            content="""
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <strong>Service Unavailable!</strong> Unable to process token request at this time. Please try again later.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """
        )


@auth_api_router.post("/send-token")
async def api_send_token(request: Request, email: str = Form(...)):
    """
    API endpoint for sending new authentication token.

    Returns JSON response with generic message.
    """
    try:
        from app.services.multi_user_auth_service import get_multi_user_auth_service

        try:
            multi_user_service = get_multi_user_auth_service()

            # Check if user exists (but don't reveal this information in response)
            user = multi_user_service.get_user_by_email(email)

            if user and user.is_active:
                # Generate and send new token
                await multi_user_service.generate_user_token(email, send_email=True)
                logger.info(f"API: New token sent to registered user {email}")
            else:
                # User doesn't exist or is inactive - log this but return same message
                logger.warning(
                    f"API: Token request for non-existent/inactive user {email}"
                )

        except Exception as e:
            # Even if there's an error, return success message to prevent info leakage
            logger.error(f"API: Error during send-token for {email}: {e}")

        # Always return success message
        return {
            "status": "success",
            "message": "If your email is registered, you will receive a new token shortly.",
        }

    except Exception as e:
        logger.error(f"API send token error: {e}")
        raise HTTPException(
            status_code=500, detail="Unable to process token request at this time."
        )


@auth_views_router.post("/logout")
async def logout(request: Request):
    """
    Logout endpoint that invalidates token and clears session cookies.

    Invalidates the current user's token and redirects to login page.
    """
    try:
        # Get current token and email from cookies
        token = request.cookies.get("auth_token")
        user_email = request.cookies.get("user_email")

        if token:
            # Invalidate multi-user token if we have email context
            if user_email:
                try:
                    from app.services.multi_user_auth_service import (
                        get_multi_user_auth_service,
                    )

                    multi_user_service = get_multi_user_auth_service()

                    # Invalidate the token for this specific user
                    multi_user_service.invalidate_user_token(user_email, token)
                    logger.info(
                        f"Token invalidated for user {user_email} from {request.client.host}"
                    )
                except Exception as e:
                    logger.error(f"Error invalidating multi-user token: {e}")

        # Create redirect response to login page
        response = RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)

        # Clear authentication cookies
        response.delete_cookie(key="auth_token", path="/")
        response.delete_cookie(key="user_email", path="/")

        logger.info(f"User logged out from {request.client.host}")
        return response

    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Even if there's an error, still clear cookies and redirect
        response = RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)
        response.delete_cookie(key="auth_token", path="/")
        response.delete_cookie(key="user_email", path="/")
        return response


@auth_api_router.post("/logout")
async def api_logout(request: Request):
    """
    API endpoint for logout that returns JSON response.
    """
    try:
        # Get current token and email from cookies/headers
        token = request.cookies.get("auth_token") or request.headers.get("X-Auth-Token")
        user_email = request.cookies.get("user_email")

        if token and user_email:
            try:
                from app.services.multi_user_auth_service import (
                    get_multi_user_auth_service,
                )

                multi_user_service = get_multi_user_auth_service()

                # Invalidate the token for this specific user
                multi_user_service.invalidate_user_token(user_email, token)
                logger.info(f"API logout: Token invalidated for user {user_email}")
            except Exception as e:
                logger.error(f"Error invalidating token during API logout: {e}")

        # Return success response
        response = Response(
            content='{"status": "success", "message": "Logged out successfully"}',
            media_type="application/json",
        )

        # Clear cookies even for API endpoint
        response.delete_cookie(key="auth_token", path="/")
        response.delete_cookie(key="user_email", path="/")

        return response

    except Exception as e:
        logger.error(f"API logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed due to server error")
