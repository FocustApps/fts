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
from common.utils import get_project_root
from common.app_logging import create_logging

from app.config import get_base_app_config

BASE_CONFIG = get_base_app_config()

logging = create_logging()

def get_template_folder() -> Path:
    return Path(TEMPLATE_PATH)


app = FastAPI(
    title="FocustApps Fenrir Test Automation",
    description="Fenrir is a test automation tool for web applications.",
    version="0.1",
)

app.mount(
    path="/public",
    app=StaticFiles(directory=f"{get_project_root()}/app/static/"),
    name="static",
)
templates = Jinja2Templates(directory=f"{get_template_folder()}")

for router in API_ROUTERS:
    logging.debug(f"Adding router: {router.prefix}")
    app.include_router(prefix=f"/{BASE_CONFIG.api_version}", router=router)


@app.get("/", response_class=HTMLResponse)
async def root_page(request: Request):
    navigation_routes = {
        "Environments": "get_environments",
        "Users": "get_users",
        "Pages": "get_pages",
        "Email Processing Items": "get_email_processing_items",
    }

    return templates.TemplateResponse(
        "index.html", {"request": request, "navigation": navigation_routes}
    )
