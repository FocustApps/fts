# React Frontend with Super Admin Dashboard - Implementation Plan

## Overview

Build a React + TypeScript + Vite frontend using Bun locally with hot reload, production Docker deployment, auto-generated types from OpenAPI schema, proactive token refresh, Shadcn/ui components, Zustand state management, super admin dashboard with full account-user association management, role-based authorization enforced across all endpoints, account-scoped query validation, role caching, bulk operations with batched email notifications, email/in-app notifications with user preferences, polling-based notification updates with rate limiting, and comprehensive audit logging with automatic 90-day retention for audit logs and 30-day retention for notifications.

---

## Backend Infrastructure (Tasks 1-15)

### Task 1: ✅ Create backend account infrastructure

- Add `common/service_connections/db_service/models/account_models/account_model.py` with Pydantic AccountModel matching AccountTable
- Implement CRUD functions (insert_account, query_account_by_id, query_all_accounts, query_account_with_owner, update_account, deactivate_account)
- Export in models `__init__.py`

### Task 2: ✅ Build account-user association model with primary account

- Create `common/service_connections/db_service/models/account_models/account_user_association_model.py` with Pydantic model matching AuthUserAccountAssociation table plus is_primary: bool field
- Implement functions (add_user_to_account, update_user_role, set_primary_account, remove_user_from_account, query_users_by_account, query_accounts_by_user, query_user_primary_account, query_user_role_in_account)
- Handle role enum (owner/admin/member/viewer)
- Add bulk operations (bulk_add_users_to_account, bulk_update_roles, bulk_remove_users) returning summary with success/failure counts
- Ensure only one primary account per user

### Task 3: ✅ Create notification preferences model

- Add `common/service_connections/db_service/models/account_models/notification_preference_model.py` with Pydantic model for user notification settings
- Implement CRUD functions (insert_default_preferences, update_preferences, query_user_preferences)
- Create default preferences (all true) on user registration

### Task 4: ✅ Create in-app notifications model

- Add `common/service_connections/db_service/models/account_models/in_app_notification_model.py` with Pydantic model
- Implement functions (insert_notification, mark_as_read, mark_all_read, delete_notification, query_user_notifications with pagination, query_unread_count)
- Add purge_schedule entry for in_app_notifications table with 30-day retention

### Task 5: ✅ Enhance JWT with account context and super admin

- Add is_super_admin: bool, account_id: str, and account_role: str fields to TokenPayload in jwt_auth_dependency.py
- Update create_access_token to accept these parameters
- Update authenticate to query primary account_id and role from associations table and include in token payload
- Create require_super_admin() dependency checking payload.is_super_admin raising 403 if false

### Task 6: ✅ Implement role-based authorization dependencies

- Create require_account_role(min_role: RoleEnum) in jwt_auth_dependency.py extracting account_role from TokenPayload
- Validate against role hierarchy (owner > admin > member > viewer), raise 403 if insufficient
- Create convenience dependencies (require_owner, require_admin, require_member)
- Create validate_account_access(token: TokenPayload, requested_account_id: str) helper raising 403 if token.account_id != requested_account_id (super admins bypass)
- Add tests in test_jwt_dependency.py

### Task 7: ✅ Build comprehensive audit logging for accounts

- Create audit helper functions in `app/services/audit_service.py`
- Methods: log_account_created, log_account_updated, log_user_added_to_account, log_user_removed_from_account, log_role_changed, log_primary_account_changed, log_account_deactivated, log_bulk_operation with summary
- Each inserting to audit_logs with entity_type="account" or "account_association"
- Include before/after values in changes JSONB field
- Add purge_schedule entry for audit_logs table with 90-day retention

### Task 8: ✅ Build account management API with role protection, audit, and tests

- Create `app/routes/accounts.py` with router prefix /v1/api/accounts
- Implement endpoints with role protection and audit logging
- Create tests/api/test_accounts_api.py testing CRUD operations and audit log entry creation
- Add to API_ROUTERS

### Task 9: ✅ Build account association API with bulk operations, batched notifications, and tests

- Add endpoints to accounts.py for user associations
- Single and bulk add/update/remove operations
- Batched email notifications for bulk operations
- Create tests/api/test_account_associations_api.py

### Task 10: ✅ Implement notification service with preferences and batching

- Create `app/services/notification_service.py` with methods for single and bulk operations
- Check user's notification preferences before sending
- Create email templates in app/templates/emails/
- Bulk templates include counts and lists of affected users

### Task 11: ✅ Build notification preferences API

- Add `app/routes/notification_preferences.py` with router prefix /v1/api/notification-preferences
- Implement GET and PATCH endpoints for preferences
- Add tests in tests/api/test_notification_preferences_api.py
- Add to API_ROUTERS

### Task 12: ✅ Build in-app notifications API with rate limiting

- Add `app/routes/notifications.py` with router prefix /v1/api/notifications
- Add rate limiter to all endpoints
- Implement GET list, GET unread-count, PATCH mark read, POST mark-all-read, DELETE endpoints
- Add tests in tests/api/test_notifications_api.py
- Add to API_ROUTERS

### Task 13: ✅ Implement account switching endpoint

- Add POST /api/auth/switch-account to auth_routes.py
- Validates user has association to target account
- Returns TokenResponse with new tokens maintaining same token family
- Log account switch in audit logs

### Task 14: ✅ Implement impersonation with audit logging

- Add create_impersonation_token to UserAuthService
- Add POST /v1/api/auth/impersonate to auth_routes.py protected by require_super_admin
- Insert audit log record with entity_type="auth_user", action="impersonate"
- Return TokenResponse with temporary impersonation tokens

### Task 15: ✅ Build super admin dashboard routes

- Add `app/routes/super_admin_dashboard.py` with user management endpoints
- GET /api/admin/users - List all users with pagination and filtering
- GET /api/admin/metrics - System-wide statistics
- POST /api/admin/users/{user_id}/status - Suspend/activate users
- Create comprehensive tests
- Add to API_ROUTERS

---

## Frontend Implementation (Tasks 16-26)

### Task 16: ✅ Retrofit role authorization on existing endpoints

- Update all route files (plans.py, test_cases.py, suites.py, systems.py, entity_tags.py)
- Add role dependencies (GET endpoints require require_member, POST/PATCH require require_admin, DELETE requires require_admin)
- Add validate_account_access calls in endpoints accepting account_id parameter
- Update existing tests to create users with proper account associations and roles

### Task 17: ✅ Add account-scoped query validation

- Update all query_*_by_account functions in model files
- Add validation that token.account_id == requested_account_id unless token.is_super_admin
- Raise HTTPException 403 if validation fails
- Update all route handlers to pass token payload to query functions
- Add tests validating cross-account access denial

### Task 18: ✅ Update seed script for super admin

- Modify seed_local_environment.py to set is_super_admin=True on admin user
- Add ensure_super_admin_exists() creating default "Super Admin Account"
- Create association record with owner role and is_primary=True
- Create default notification preferences
- Add purge schedule entries for audit_logs (90 days) and in_app_notifications (30 days)

### Task 19: ⬜ Initialize frontend project with dev workflow

- Run bun create vite . --template react-ts in frontend/
- Install dependencies (React Router v6, TanStack Query, Axios, Zustand, React Hook Form, Zod, openapi-typescript, Shadcn CLI, jwt-decode, zustand persist middleware)
- Configure Tailwind CSS
- Set up Vite proxy in vite.config.ts forwarding /api/*and /v1/* to <http://localhost:8080>
- Add package.json script for dev with OpenAPI type generation
- Create .env.development with VITE_API_URL and VITE_NOTIFICATION_POLL_INTERVAL

### Task 20: ⬜ Build API client with proactive token refresh

- Create frontend/src/lib/axios.ts with request interceptor
- Use jwt-decode checking token expiry (refresh if <5 min)
- Handle 401 with refresh retry, 403 with toast, 429 with exponential backoff
- On refresh failure call adminStore.exitImpersonation() and redirect to login
- Create typed API wrappers in frontend/src/api/ using generated OpenAPI types

### Task 21: ⬜ Create Zustand stores with role caching

- Build frontend/src/stores/authStore.ts with user state, account info, role caching
- accountRolesCache Map<account_id, role> persisted to localStorage
- Token management and switchAccount methods
- Build adminStore.ts with impersonation state
- Build uiStore.ts for toasts/modals/banner
- Build notificationStore.ts with polling methods

### Task 22: ⬜ Set up routing with role protection

- Create frontend/src/router.tsx with public routes
- Protected routes for dashboard, plans, test-cases, systems, notifications, settings
- Super admin routes for /admin/*
- Implement ProtectedRoute, SuperAdminRoute, RoleProtectedRoute components
- Build Login.tsx and Register.tsx with Shadcn Form components

### Task 23: ⬜ Build header with account switcher and notifications

- Create frontend/src/components/layout/Header.tsx with Shadcn DropdownMenu
- Show current account name and role badge (colored by role)
- List of available accounts with cached role indicators
- Add notification bell icon with unread count badge
- Show impersonation banner when impersonating
- Start notification polling on component mount

### Task 24: ⬜ Build notification center with polling

- Create frontend/src/features/notifications/NotificationCenter.tsx
- Display in-app notifications with type icons
- Implement TanStack Query with refetch interval from env
- Handle 429 rate limit errors gracefully
- Build NotificationPreferences.tsx settings page

### Task 25: ⬜ Build super admin account dashboard with bulk operations

- Create frontend/src/features/admin/AccountList.tsx with Shadcn DataTable
- AccountForm.tsx for create/update
- AccountDetail.tsx with tabs for info/users/audit logs
- AccountUserManager.tsx DataTable with bulk operations
- BulkAddUsersModal.tsx and BulkUpdateRolesModal.tsx
- Impersonation modal with user search
- Show success toast with operation summary

### Task 26: ⬜ Build user CRUD features with role-based UI

- Create frontend/src/features/ modules for plans/, test-cases/, systems/
- List.tsx with Shadcn DataTable (account-scoped data)
- Form.tsx with React Hook Form + Zod
- Detail.tsx components
- Conditionally render buttons based on role
- TanStack Query hooks filtering by current account
- Show 403 errors with Shadcn Alert

### Task 27: ⬜ Add production Docker

- Create multi-stage frontend/Dockerfile with bun build stage
- nginx:alpine serve stage with SPA routing
- Add frontend service to docker-compose.yml production profile
- Update CORS_ALLOW_ORIGINS
- Create .env.production

---

## Summary

**Backend Tasks Completed: 15/15** ✅
**Frontend Tasks Remaining: 12/12** ⬜

**Next Task: Task 16 - Retrofit role authorization on existing endpoints**
