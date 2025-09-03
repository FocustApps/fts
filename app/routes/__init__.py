from app.routes import (
    email_processor,
    environments,
    pages,
    users,
)


API_ROUTERS = [
    environments.env_views_router,
    environments.env_api_router,
    users.user_views_router,
    users.user_api_router,
    pages.page_router,
    pages.page_api_router,
    email_processor.email_processor_views_router,
]
