from app.routes import (
    actions,  # Migrated to JWT auth
    auth_routes,
    auth_users,  # Rewritten for JWT auth with account management
    auth_views,
    email_processor,  # Migrated to JWT auth
    environments,  # Migrated to JWT auth
    identifiers,  # Migrated to JWT auth
    pages,  # Migrated to JWT auth
    users,  # Migrated to JWT auth
)


API_ROUTERS = [
    auth_views.auth_views_router,  # New JWT auth view routes (login, register, etc.)
    auth_routes.auth_api_router,  # New JWT auth API routes
    # All routes migrated to JWT auth:
    environments.env_api_router,  # API router FIRST (more specific paths)
    environments.env_views_router,  # Views router SECOND (less specific paths)
    pages.page_router,
    pages.page_api_router,
    identifiers.identifiers_views_router,
    identifiers.identifiers_api_router,
    actions.actions_views_router,
    actions.actions_api_router,
    users.user_views_router,
    email_processor.email_processor_views_router,
    auth_users.auth_users_views_router,  # JWT-based user management with account assignments
    auth_users.auth_users_api_router,
]
