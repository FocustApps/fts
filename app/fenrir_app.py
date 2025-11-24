"""
Fenrir Fast API application
"""

from fastapi import FastAPI, Request
from pathlib import Path

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app import TEMPLATE_PATH
from app.routes import API_ROUTERS
from app.utils import get_project_root
from app.tasks.token_rotation import auth_scheduler_lifespan
from common.app_logging import create_logging

from app.config import get_base_app_config

from app.routes.auth import get_auth_token_from_cookie
from app.dependencies.multi_user_auth_dependency import verify_multi_user_auth_token
from fastapi.responses import RedirectResponse

BASE_CONFIG = get_base_app_config()

logging = create_logging()


def get_template_folder() -> Path:
    return Path(TEMPLATE_PATH)


app = FastAPI(
    title="FocustApps Fenrir Test Automation",
    description="Fenrir is a test automation tool for web applications.",
    version="0.1",
    lifespan=auth_scheduler_lifespan,
)

app.mount(
    path="/public",
    app=StaticFiles(directory=f"{get_project_root()}/app/static/"),
    name="static",
)
templates = Jinja2Templates(directory=f"{get_template_folder()}")

for router in API_ROUTERS:
    logging.debug(f"Adding router: {router.prefix}")
    # Auth view routes should be at root level (no API version prefix)
    if (router.prefix == "/auth" and "auth-views" in router.tags) or (
        router.prefix == "/auth-users" and "auth-users-views" in router.tags
    ):
        app.include_router(router)
    else:
        app.include_router(prefix=f"/{BASE_CONFIG.api_version}", router=router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Returns basic application status.
    """
    return {"status": "healthy", "application": "fenrir", "version": "0.1"}


@app.get("/", response_class=HTMLResponse)
async def root_page(request: Request):

    # Check if user is authenticated via cookie
    auth_token = get_auth_token_from_cookie(request)
    if not auth_token:
        # Redirect to login page if not authenticated
        return RedirectResponse(url="/auth/login", status_code=302)

    # Get current user context for navbar
    current_user = None
    try:
        auth_context = await verify_multi_user_auth_token(request)
        current_user = {
            "username": auth_context.username
            or (
                auth_context.user_email.split("@")[0]
                if auth_context.user_email
                else "User"
            ),
            "email": auth_context.user_email,
            "is_admin": auth_context.is_admin,
        }
    except Exception as e:
        logging.warning(f"Failed to get user context: {e}")
        # For legacy tokens or errors, create minimal user context
        current_user = {"username": "User", "email": None, "is_admin": False}

    navigation_routes = {
        "Environments": "get_environments",
        "Users": "get_users",
        "Pages": "get_pages",
        "Identifiers": "get_identifiers_view",
        "Actions": "get_actions_view",
        "Email Processing Items": "get_email_processing_items",
        "Auth Users": "get_auth_users_view",
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "navigation": navigation_routes,
            "current_user": current_user,
        },
    )
