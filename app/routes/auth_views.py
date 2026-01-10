"""
Authentication view routes for serving JWT auth HTML pages.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app import TEMPLATE_PATH

# Create router
auth_views_router = APIRouter(
    prefix="/auth", tags=["auth-views"], include_in_schema=False
)

# Initialize templates
templates = Jinja2Templates(directory=str(Path(TEMPLATE_PATH)))


@auth_views_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page."""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@auth_views_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serve registration page."""
    return templates.TemplateResponse("auth/register.html", {"request": request})


@auth_views_router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Serve forgot password page."""
    return templates.TemplateResponse("auth/forgot-password.html", {"request": request})


@auth_views_router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Serve password reset page (with token in query params)."""
    return templates.TemplateResponse("auth/reset-password.html", {"request": request})
