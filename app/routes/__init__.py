from app.routes import (
    auth,
    auth_users,
    email_processor,
    environments,
    identifiers,
    pages,
    users,
)


API_ROUTERS = [
    auth.auth_views_router,
    auth.auth_api_router,
    auth_users.auth_users_views_router,
    auth_users.auth_users_api_router,
    environments.env_views_router,
    environments.env_api_router,
    users.user_views_router,
    users.user_api_router,
    pages.page_router,
    pages.page_api_router,
    identifiers.identifiers_views_router,
    identifiers.identifiers_api_router,
    email_processor.email_processor_views_router,
]
