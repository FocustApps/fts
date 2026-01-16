from app.routes import (
    account_associations,  # User-account association management
    account_switching,  # Account switching for multi-account users
    accounts,  # Multi-tenant account management
    actions,  # Migrated to JWT auth
    audit_logs,  # Read-only audit trail
    auth_routes,
    auth_users,  # Rewritten for JWT auth with account management
    email_processor,  # Email automation queue
    entity_tags,  # Polymorphic tagging
    environments,  # Migrated to JWT auth
    identifiers,  # Migrated to JWT auth
    impersonation,  # Super admin impersonation
    me,  # Current user /me endpoints
    notifications,  # In-app notifications and preferences
    pages,  # Migrated to JWT auth
    plans,  # Test execution plans
    purge,  # Admin data retention
    suites,  # Test suite organization
    super_admin_dashboard,  # Super admin dashboard
    system_under_test,  # Systems being tested
    test_cases,  # Test case management
    users,  # Migrated to JWT auth
)


API_ROUTERS = [
    auth_routes.auth_api_router,  # JWT auth API routes
    accounts.accounts_api_router,  # Multi-tenant account management
    account_associations.account_associations_api_router,  # User-account associations
    account_switching.account_switching_api_router,  # Account switching
    impersonation.impersonation_api_router,  # Super admin impersonation
    me.users_me_api_router,  # Current user /me endpoints
    super_admin_dashboard.super_admin_dashboard_api_router,  # Super admin dashboard
    notifications.notification_preferences_api_router,  # Notification preferences
    notifications.notifications_api_router,  # In-app notifications
    notifications.admin_notifications_api_router,  # Admin notification creation
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
