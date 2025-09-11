from app.routes import (
    auth,
    email_processor,
    environments,
    pages,
    users,
)


API_ROUTERS = [
    auth.auth_views_router,
    auth.auth_api_router,
    environments.env_views_router,
    environments.env_api_router,
    users.user_views_router,
    users.user_api_router,
    pages.page_router,
    pages.page_api_router,
    email_processor.email_processor_views_router,
]
