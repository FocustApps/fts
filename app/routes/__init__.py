from app.routes import (
    actions,  # Migrated to JWT auth
    audit_logs,  # Read-only audit trail
    auth_routes,
    auth_users,  # Rewritten for JWT auth with account management
    email_processor,  # Email automation queue
    entity_tags,  # Polymorphic tagging
    environments,  # Migrated to JWT auth
    identifiers,  # Migrated to JWT auth
    pages,  # Migrated to JWT auth
    plans,  # Test execution plans
    purge,  # Admin data retention
    suites,  # Test suite organization
    system_under_test,  # Systems being tested
    test_cases,  # Test case management
    users,  # Migrated to JWT auth
)


API_ROUTERS = [
    auth_routes.auth_api_router,  # JWT auth API routes
    environments.env_api_router,
    pages.page_api_router,
    identifiers.identifiers_api_router,
    actions.actions_views_router,
    actions.actions_api_router,
    users.user_api_router,
    auth_users.auth_users_api_router,
    # New model routes
    system_under_test.sut_api_router,
    test_cases.test_case_api_router,
    suites.suite_api_router,
    plans.plan_api_router,
    entity_tags.tag_api_router,
    audit_logs.audit_log_api_router,
    purge.purge_api_router,
    email_processor.email_processor_api_router,
]
