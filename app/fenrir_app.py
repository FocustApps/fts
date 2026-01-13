"""
Fenrir Fast API application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.routes import API_ROUTERS
from app.utils import get_project_root
from app.middleware.https_middleware import HTTPSEnforcementMiddleware
from common.app_logging import create_logging

from app.config import get_base_app_config


BASE_CONFIG = get_base_app_config()

logging = create_logging()



app = FastAPI(
    title="FocustApps Fenrir Test Automation",
    description="Fenrir is a test automation tool for web applications.",
    version="0.1",
)

# Add CORS middleware
if BASE_CONFIG.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=BASE_CONFIG.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logging.info(f"CORS enabled for origins: {BASE_CONFIG.cors_allow_origins}")

# Add HTTPS enforcement middleware
if BASE_CONFIG.enforce_https:
    app.add_middleware(HTTPSEnforcementMiddleware, enforce=True)
    logging.info("HTTPS enforcement enabled")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Middleware to handle proxy headers from Caddy
class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Trust X-Forwarded-* headers from Caddy for proper URL generation
        if "x-forwarded-proto" in request.headers:
            request.scope["scheme"] = request.headers["x-forwarded-proto"]
        if "x-forwarded-host" in request.headers:
            request.scope["server"] = (
                request.headers["x-forwarded-host"],
                443 if request.scope.get("scheme") == "https" else 80,
            )
        return await call_next(request)


app.add_middleware(ProxyHeadersMiddleware)

app.mount(
    path="/public",
    app=StaticFiles(directory=f"{get_project_root()}/app/static/"),
    name="static",
)

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
    """
    Root page - serves main application.

    Authentication is handled client-side via JavaScript.
    The page will redirect to login if no valid JWT token is found.
    """

    return 
    
