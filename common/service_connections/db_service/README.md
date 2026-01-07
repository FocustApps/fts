# Fenrir Database Service Documentation

## Overview

The Fenrir Database Service provides a service-oriented abstraction layer for database connections, table definitions, and data models supporting the multi-application test automation hub. The system follows a dual-environment pattern with Azure deployments (MSSQL) and local development (PostgreSQL).

## Architecture

### Database Structure Hierarchy

The database follows a hierarchical structure designed to support multi-tenant test automation with subscription management, authentication, comprehensive test asset tracking, and row-level security.

```text
┌─────────────────────────────────────────────────────────────┐
│                    TOP LEVEL ENTITIES                       │
├─────────────────────────────────────────────────────────────┤
│  AccountTable (Root entity for multi-tenant architecture)   │
│  AuthUserTable (System access control)                      │
│  SystemUnderTestTable (Test target systems) ✓ IMPLEMENTED  │
│  PurgeTable (Data retention management)                     │
│  AuditLogTable (Audit trail with retention) ✓ NEW          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              AUTHENTICATION & ASSOCIATION LAYER             │
├─────────────────────────────────────────────────────────────┤
│  AuthTokenTable (Multi-device tokens) ✓ NEW                │
│  AuthUserAccountAssociation (Many-to-many) ✓ JUNCTION      │
│  SystemEnvironmentAssociation (Many-to-many) ✓ JUNCTION    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   SUBSCRIPTION LAYER                        │
├─────────────────────────────────────────────────────────────┤
│  AccountSubscriptionTable (Account billing plans)           │
│  AuthUserSubscriptionTable (User-level subscriptions)       │
│  UserSubscriptionTable (Legacy/alternative subscription)    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ENVIRONMENT & TEST EXECUTION LAYER             │
├─────────────────────────────────────────────────────────────┤
│  EnvironmentTable (Deployment environments) ✓ SOFT DELETE  │
│  SystemUnderTestUserTable (Test credentials) ✓ SOFT DELETE │
│  PlanTable (Test execution plans) ✓ SOFT DELETE            │
│  SuiteTable (Test suite collections) ✓ NEW                 │
│  TestCaseTable (Individual test cases) ✓ NEW               │
│  ActionChainTable (Sequential actions) ✓ NEW               │
│  EmailProcessorTable (Email automation queue)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  ASSOCIATION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  PlanSuiteAssociation (Plans↔Suites) ✓ JUNCTION           │
│  SuiteTestCaseAssociation (Suites↔Tests) ✓ JUNCTION       │
│  PageFenrirActionAssociation (Pages↔Actions) ✓ JUNCTION   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SELENIUM AUTOMATION LAYER (UI)                  │
├─────────────────────────────────────────────────────────────┤
│  PageTable (Web pages for automation) ✓ SOFT DELETE        │
│    └─ IdentifierTable (Element locators) ✓ SOFT DELETE     │
│  FenrirActionsTable (SeleniumController methods)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           ACTION TABLES (Partial Implementation)             │
├─────────────────────────────────────────────────────────────┤
│  APIActionTable (API test actions - placeholder)             │
│  InfrastructureActionTable (Infra actions - placeholder)     │
│  RepositoryActionTable (Repo actions - placeholder)          │
│  UserInterfaceActionTable (UI actions - placeholder)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              POLYMORPHIC TAGGING LAYER                      │
├─────────────────────────────────────────────────────────────┤
│  EntityTagTable (Universal tagging with RLS) ✓ NEW         │
│    - Supports all entity types via polymorphic pattern      │
│    - Row-Level Security for multi-tenant isolation          │
│    - 10 optimized indexes for query performance             │
└─────────────────────────────────────────────────────────────┘
```

## Table Definitions and Relationships

### Core Account & Authentication Tables

#### AccountTable

**Purpose**: Top-level organization accounts for multi-tenant architecture  
**Key Relationships**:

- Parent to: `AccountSubscriptionTable` (via `subscription_id`)
- Many-to-many with: `AuthUserTable` via `auth_user_account_association` (✓ NEW)

**Relationships** (✓ NEW):

- `users`: Many-to-many to AuthUserTable via auth_user_account_association

**Fields**:

- `account_id` (PK): UUID identifier
- `account_name`: Unique account name
- `owner_email`: Primary contact email
- `owner_user_id`: Reference to AuthUserTable
- `subscription_id`: Links to AccountSubscriptionTable
- `logo_url`: Cloud storage reference for branding
- `is_active`: Soft delete flag

**Cloud Dependencies**: Yes (logo storage via AWS S3/Azure Blob)

---

#### AuthUserTable

**Purpose**: System authentication and role-based access control  
**Key Relationships**:

- Child of: `AccountTable` (via `account_ids` field)
- Parent to: `AuthUserSubscriptionTable` (via `user_subscription_id`)

**Fields**:

- `auth_user_id` (PK): Auto-increment integer
- `auth_user_email`: Unique email for authentication
- `current_auth_token`: JWT/session token
- `token_expires_at`: Token expiration timestamp
- `is_admin`, `is_super_admin`: Role flags
- `multi_account_user`: Enables cross-account access
- `account_ids`: JSONB array of accessible accounts

**Cloud Dependencies**: No (potential future OAuth/SSO integration)

**Relationships** (✓ NEW):

- `tokens`: One-to-many to AuthTokenTable via back_populates
- `accounts`: Many-to-many to AccountTable via auth_user_account_association

**Deprecated Fields**:

- `current_auth_token`: Use AuthTokenTable instead
- `account_ids`: Use accounts relationship via junction table

---

#### AuthTokenTable ✓ NEW

**Purpose**: Multi-device authentication token management with rotation support  
**Key Relationships**:

- Child of: `AuthUserTable` (via `auth_user_id` FK with CASCADE delete)

**Fields**:

- `token_id` (PK): UUID String(36) identifier
- `auth_user_id` (FK): Parent user reference (CASCADE delete)
- `token_value`: String(64) unique token value
- `token_expires_at`: Expiration timestamp (CHECK constraint > created_at)
- `device_info`: Optional device identification
- `ip_address`: Last known IP (String 45 for IPv6)
- `last_used_at`: Token usage tracking
- `is_active`: Soft delete flag for token revocation
- `revoked_at`: Revocation timestamp

**Token Rotation**: Keep 5 newest tokens per user, revoke older tokens automatically

**Indexes**: 4 indexes including partial index on active/non-expired tokens

**Cloud Dependencies**: No (optional Redis integration for distributed caching)

---

#### AuditLogTable ✓ NEW

**Purpose**: Comprehensive audit trail for compliance and security monitoring  
**Key Relationships**:

- References: `AuthUserTable` (via performed_by_user_id, SET NULL on delete)
- References: `AccountTable` (via account_id, SET NULL on delete)

**Fields**:

- `audit_id` (PK): UUID String(36) identifier
- `entity_type`: Type of entity being audited
- `entity_id`: UUID of specific entity
- `action`: AuditActionEnum (create, update, delete, login, logout, etc.)
- `performed_by_user_id` (FK): User who performed action (nullable, SET NULL)
- `account_id` (FK): Account context (nullable, SET NULL)
- `timestamp`: When action occurred (indexed)
- `ip_address`: Source IP (String 45)
- `user_agent`: Browser/client information
- `details`: JSONB field for action-specific metadata
- `is_sensitive`: Boolean flag for retention policy (90-day vs 365-day)

**Data Retention**:

- Non-sensitive logs: 90 days
- Sensitive logs: 365 days

**Indexes**: 6 indexes including composite indexes for entity lookups and timestamp queries

**Cloud Dependencies**: No

---

#### AuthUserAccountAssociation ✓ NEW JUNCTION TABLE

**Purpose**: Many-to-many relationship between users and accounts with role-based access  
**Key Relationships**:

- Links: `AuthUserTable` ↔ `AccountTable`

**Fields**:

- `association_id` (PK): UUID String(36)
- `auth_user_id` (FK): User reference (CASCADE delete)
- `account_id` (FK): Account reference (CASCADE delete)
- `role`: String(64) using AccountRoleEnum (owner, admin, member, viewer)
- `invited_by_user_id` (FK): Optional inviter reference (SET NULL)
- `is_active`: Association status
- `created_at`, `updated_at`: Audit timestamps

**Unique Constraint**: (auth_user_id, account_id) - prevents duplicate associations

**Indexes**: 3 indexes on user_id, account_id, and is_active

**Replaces**: `account_ids` string field in AuthUserTable

---

### Subscription Management Tables

#### AccountSubscriptionTable

**Purpose**: Billing plans and payment configuration for accounts  
**Key Relationships**:

- Child of: `AccountTable` (via reference from AccountTable.subscription_id)

**Fields**:

- `account_subscription_id` (PK): UUID identifier
- `subscription_plan_type`: ENUM(small, medium, large, big_af)
- `payment_term`: ENUM(monthly, yearly, perpetual)
- `payment_type`: ENUM(credit_card, paypal, bank_transfer)

**Cloud Dependencies**: Yes (payment provider integration - Stripe/PayPal)

---

#### AuthUserSubscriptionTable

**Status**: Placeholder (empty file - future implementation)  
**Intended Purpose**: User-level subscription management separate from account subscriptions

---

#### UserSubscriptionTable

**Status**: Placeholder (empty file - future implementation)  
**Intended Purpose**: Alternative/legacy user subscription model

---

### Test Environment & Execution Tables

#### EnvironmentTable ✓ UPDATED WITH SOFT DELETE

**Purpose**: Deployment environments for systems under test  
**Key Relationships**:

- Many-to-many with: `SystemUnderTestTable` via `system_environment_association`
- Parent to: `SystemUnderTestUserTable` (via `environment_id` FK)
- Referenced by: `PageTable`, `IdentifierTable` (via JSONB fields)

**Fields**:

- `environment_id` (PK): UUID String(36) identifier
- `environment_name`: Unique name (e.g., "Prod", "Staging")
- `environment_designation`: Environment type
- `environment_base_url`: Base URL for testing
- `api_base_url`: API endpoint URL
- `environment_status`: Current operational status
- `users_in_environment`: JSONB array of user references
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern (✓ NEW)
- `created_at`, `updated_at`: Audit timestamps

**Indexes**: 2 indexes including partial index on is_active

**Cloud Dependencies**: No (URLs may reference cloud-hosted apps)

---

#### SystemUnderTestUserTable ✓ UPDATED WITH SOFT DELETE

**Purpose**: Test user credentials for automated testing  
**Key Relationships**:

- Child of: `EnvironmentTable` (via `environment_id` FK with CASCADE delete)
- Child of: `SystemUnderTestTable` (via `sut_id` FK with CASCADE delete)
- Child of: `AccountTable` (via `account_id` FK)

**Fields**:

- `sut_user_id` (PK): Auto-increment integer
- `account_id` (FK): Multi-tenant isolation
- `sut_id` (FK): Parent system (CASCADE delete)
- `username`, `email`: Test user credentials
- `password`: Direct password storage (optional)
- `secret_provider`: Cloud secret service name
- `secret_url`, `secret_name`: Cloud credential references
- `environment_id` (FK): Parent environment (CASCADE delete)
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern (✓ NEW)
- `created_at`, `updated_at`: Audit timestamps

**Indexes**: 5 indexes including partial index on is_active

**Cloud Dependencies**: Yes (AWS Secrets Manager, Azure Key Vault for credential storage)

**Cascade Behavior**: Deleted when parent EnvironmentTable or SystemUnderTestTable is deleted

---

#### PlanTable ✓ UPDATED WITH SOFT DELETE

**Purpose**: Test execution plans grouping multiple test suites  
**Key Relationships**:

- Child of: `AccountTable` (via `account_id`)
- Child of: `AuthUserTable` (via `deactivated_by_user_id` FK with SET NULL)
- Many-to-many with: `SuiteTable` via `plan_suite_association` (✓ NEW)

**Fields**:

- `plan_id` (PK): UUID String(36) identifier
- `plan_name`: Unique plan name
- `suites_ids`: String(1024) - **DEPRECATED: Use suites relationship instead**
- `suite_tags`: JSON metadata for suite organization
- `status`: ENUM(active, inactive)
- `owner_user_id`: Creator/owner reference
- `account_id`: Multi-tenant isolation
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern (✓ NEW)
- `created_at`, `updated_at`: Audit timestamps

**Relationships** (✓ NEW):

- `suites`: Many-to-many to SuiteTable via plan_suite_association

**Deprecated Fields**:

- `suites_ids`: Use suites relationship via junction table

**Indexes**: 3 indexes including partial index on is_active

**Cloud Dependencies**: No

---

#### SuiteTable ✓ NEW

**Purpose**: Test suite collections for organizing test cases  
**Key Relationships**:

- Child of: `SystemUnderTestTable` (via `sut_id` FK with CASCADE delete)
- Child of: `AccountTable` (via `account_id` FK with CASCADE delete)
- Child of: `AuthUserTable` (via `owner_user_id` FK with RESTRICT delete)
- Many-to-many with: `TestCaseTable` via `suite_test_case_association`
- Many-to-many with: `PlanTable` via `plan_suite_association`

**Fields**:

- `suite_id` (PK): UUID String(36) identifier
- `suite_name`: Unique suite name
- `description`: Optional suite description
- `sut_id` (FK): Parent system (CASCADE delete)
- `owner_user_id` (FK): Suite owner (RESTRICT delete)
- `account_id` (FK): Multi-tenant isolation (CASCADE delete)
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern
- `created_at`, `updated_at`: Audit timestamps

**Relationships**:

- `test_cases`: Many-to-many via suite_test_case_association
- `plans`: Many-to-many via plan_suite_association

**Indexes**: 4 indexes including partial index on is_active

**Cloud Dependencies**: No

---

#### TestCaseTable ✓ NEW

**Purpose**: Individual test case definitions with type categorization  
**Key Relationships**:

- Child of: `SystemUnderTestTable` (via `sut_id` FK with CASCADE delete)
- Child of: `AccountTable` (via `account_id` FK with CASCADE delete)
- Child of: `AuthUserTable` (via `owner_user_id` FK with RESTRICT delete)
- Many-to-many with: `SuiteTable` via `suite_test_case_association`

**Fields**:

- `test_case_id` (PK): UUID String(36) identifier
- `test_name`: Unique test case name
- `description`: Optional test description
- `test_type`: String(64) using TestTypeEnum (functional, integration, regression, smoke, performance, security)
- `sut_id` (FK): Parent system (CASCADE delete)
- `owner_user_id` (FK): Test owner (RESTRICT delete)
- `account_id` (FK): Multi-tenant isolation (CASCADE delete)
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern
- `created_at`, `updated_at`: Audit timestamps

**Relationships**:

- `suites`: Many-to-many via suite_test_case_association

**Indexes**: 5 indexes including test_type and is_active partial index

**Cloud Dependencies**: No

---

#### ActionChainTable ✓ NEW

**Purpose**: Sequential/parallel action execution workflows  
**Key Relationships**:

- Child of: `SystemUnderTestTable` (via `sut_id` FK with CASCADE delete)
- Child of: `AccountTable` (via `account_id` FK with CASCADE delete)
- Child of: `AuthUserTable` (via `owner_user_id` FK with RESTRICT delete)

**Fields**:

- `action_chain_id` (PK): UUID String(36) identifier
- `chain_name`: Unique chain name
- `description`: Optional chain description
- `action_steps`: JSONB array defining execution sequence with dependencies and parallel flags
- `sut_id` (FK): Parent system (CASCADE delete)
- `account_id` (FK): Multi-tenant isolation (CASCADE delete)
- `owner_user_id` (FK): Chain owner (RESTRICT delete)
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern
- `created_at`, `updated_at`: Audit timestamps

**Action Steps JSON Structure**:

```json
[
  {
    "step_name": "Step 1",
    "action_type": "api_action",
    "action_id": "uuid",
    "depends_on": [],
    "parallel": false
  }
]
```

**Indexes**: 4 indexes including partial index on is_active

**Cloud Dependencies**: No

---

#### PlanSuiteAssociation ✓ NEW JUNCTION TABLE

**Purpose**: Links test plans to suites with execution order  
**Key Relationships**:

- Links: `PlanTable` ↔ `SuiteTable`

**Fields**:

- `association_id` (PK): UUID String(36)
- `plan_id` (FK): Plan reference (CASCADE delete)
- `suite_id` (FK): Suite reference (CASCADE delete)
- `execution_order`: Integer for sequential execution
- `is_active`: Association status
- `created_at`: Audit timestamp

**Indexes**: 3 indexes on plan_id, suite_id, and execution order

**Replaces**: `suites_ids` string field in PlanTable

---

#### SuiteTestCaseAssociation ✓ NEW JUNCTION TABLE

**Purpose**: Links test suites to test cases with execution order  
**Key Relationships**:

- Links: `SuiteTable` ↔ `TestCaseTable`

**Fields**:

- `association_id` (PK): UUID String(36)
- `suite_id` (FK): Suite reference (CASCADE delete)
- `test_case_id` (FK): Test case reference (CASCADE delete)
- `execution_order`: Integer for sequential execution
- `is_active`: Association status
- `created_at`: Audit timestamp

**Indexes**: 3 indexes on suite_id, test_case_id, and execution order

---

#### EmailProcessorTable

**Purpose**: Email automation task queue for test workflows  
**Key Relationships**:

- Independent processing queue
- Logical relationship to `SystemUnderTestTable` (via `system` string field)

**Fields**:

- `email_processor_id` (PK): Auto-increment integer
- `email_item_id`: Unique email identifier
- `multi_item_email_ids`: JSONB array for batch processing
- `multi_email_flag`, `multi_attachment_flag`: Processing flags
- `system`: Target system name
- `test_name`: Associated test identifier
- `requires_processing`: Queue status flag
- `last_processed_at`: Processing timestamp

**Cloud Dependencies**: Yes (AWS SES, SendGrid, or email service APIs)

**Data Retention**: Subject to purge operations managed by `PurgeTable`

---

### Selenium Automation Tables

#### PageTable ✓ UPDATED WITH SOFT DELETE

**Purpose**: Web page definitions for Selenium automation  
**Key Relationships**:

- Logical parent: `EnvironmentTable` (via JSONB `environments` field)
- Parent to: `IdentifierTable` (one-to-many with CASCADE delete)
- Many-to-many with: `FenrirActionsTable` via `page_fenrir_action_association`

**Fields**:

- `page_id` (PK): Auto-increment integer
- `page_name`: Unique page identifier
- `page_url`: Page URL pattern
- `environments`: JSONB mapping of environment-specific configurations
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern (✓ NEW)
- `created_at`, `updated_at`: Audit timestamps

**Relationships**:

- `identifiers`: One-to-many to IdentifierTable
- `fenrir_actions`: Many-to-many via page_fenrir_action_association

**Indexes**: 2 indexes including partial index on is_active

**Cloud Dependencies**: No

**Cascade Behavior**: When deleted, all child `IdentifierTable` records are CASCADE deleted

---

#### IdentifierTable ✓ UPDATED WITH SOFT DELETE

**Purpose**: Selenium locators for page elements  
**Key Relationships**:

- Child of: `PageTable` (via `page_id` FK with CASCADE delete)

**Fields**:

- `identifier_id` (PK): Auto-increment integer
- `page_id` (FK): Parent page reference (CASCADE delete)
- `element_name`: Unique element identifier
- `locator_strategy`: Selenium strategy (XPATH, CSS, ID, etc.)
- `locator_query`: Actual locator string
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern (✓ NEW)
- `created_at`, `updated_at`: Audit timestamps

**Relationship**:

- `page`: Many-to-one to PageTable

**Indexes**: 3 indexes including partial index on is_active

**Cloud Dependencies**: No

**Cascade Behavior**: Deleted when parent PageTable record is deleted (enforced by FK and SQLAlchemy cascade)

---

#### PageFenrirActionAssociation ✓ NEW JUNCTION TABLE

**Purpose**: Links pages to SeleniumController methods with execution order  
**Key Relationships**:

- Links: `PageTable` ↔ `FenrirActionsTable`

**Fields**:

- `association_id` (PK): UUID String(36)
- `page_id` (FK): Page reference (CASCADE delete)
- `fenrir_action_id` (FK): Action reference (CASCADE delete)
- `action_order`: Integer for sequential execution
- `is_active`: Association status
- `created_at`: Audit timestamp

**Indexes**: 3 indexes on page_id, action_id, and action_order

---

### System Management Tables

#### SystemUnderTestTable ✓ FULLY IMPLEMENTED

**Purpose**: Root entity for systems under test with multi-tenant isolation  
**Key Relationships**:

- Child of: `AccountTable` (via `account_id` FK with CASCADE delete)
- Child of: `AuthUserTable` (via `owner_user_id` FK with RESTRICT delete)
- Parent to: `SystemUnderTestUserTable` (one-to-many)
- Parent to: `PageTable` (one-to-many)
- Many-to-many with: `EnvironmentTable` via `system_environment_association`

**Fields**:

- `sut_id` (PK): UUID String(36) identifier
- `system_name`: Unique system name
- `description`: Optional system description
- `repository_url`: Optional source repository link
- `wiki_url`: Optional documentation link
- `account_id` (FK): Multi-tenant isolation (CASCADE delete)
- `owner_user_id` (FK): System owner (RESTRICT delete)
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern
- `created_at`, `updated_at`: Audit timestamps

**Relationships**:

- `environments`: Many-to-many via system_environment_association
- `users`: One-to-many to SystemUnderTestUserTable
- `pages`: One-to-many to PageTable

**Indexes**: 3 indexes including partial index on is_active

**Cloud Dependencies**: No

---

#### SystemEnvironmentAssociation ✓ NEW JUNCTION TABLE

**Purpose**: Many-to-many relationship between systems and environments  
**Key Relationships**:

- Links: `SystemUnderTestTable` ↔ `EnvironmentTable`

**Fields**:

- `association_id` (PK): UUID String(36)
- `sut_id` (FK): System reference (CASCADE delete)
- `environment_id` (FK): Environment reference (CASCADE delete)
- `is_active`: Association status
- `created_at`: Audit timestamp

**Unique Constraint**: (sut_id, environment_id) - prevents duplicate system-environment pairs

**Indexes**: 3 indexes on sut_id, environment_id, and composite unique

---

#### PurgeTable

**Purpose**: Data retention policy and purge operation tracking  
**Key Relationships**:

- Independent system table
- References other tables via `table_name` string field

**Fields**:

- `purge_id` (PK): UUID identifier
- `table_name`: Target table for purge operations
- `last_purged_at`: Last execution timestamp
- `purge_interval_days`: Retention period
- `created_at`, `updated_at`: Audit timestamps

**Cloud Dependencies**: No

**Managed Tables**: Typically manages `EmailProcessorTable` and test result tables

---

### Polymorphic Tagging System

#### EntityTagTable ✓ NEW WITH ROW-LEVEL SECURITY

**Purpose**: Universal tagging system for all entities with multi-tenant isolation  
**Key Relationships**:

- Child of: `AccountTable` (via `account_id` FK with CASCADE delete)
- Child of: `AuthUserTable` (via `created_by_user_id` FK with RESTRICT delete)
- Polymorphic references to: All entity types via (entity_type, entity_id)

**Fields**:

- `tag_id` (PK): UUID String(36) identifier
- `entity_type`: String(64) from EntityTypeEnum (suite, test_case, plan, action_chain, etc.)
- `entity_id`: UUID String(36) of target entity (polymorphic reference)
- `tag_name`: String(128) tag value (indexed)
- `tag_category`: String(64) from TagCategoryEnum (functional, priority, automation_type, etc.)
- `tag_value`: Optional String(255) additional metadata
- `account_id` (FK): Multi-tenant isolation (CASCADE delete)
- `created_by_user_id` (FK): Tag creator (RESTRICT delete)
- `is_active`, `deactivated_at`, `deactivated_by_user_id`: Soft delete pattern
- `created_at`, `updated_at`: Audit timestamps

**Polymorphic Pattern**:

- No FK constraint on entity_id for flexibility across entity types
- Application validates entity exists and user has access
- Example: `entity_type='suite'`, `entity_id='uuid-of-suite'`

**Row-Level Security (RLS)**:

- PostgreSQL RLS policy filters by account_id
- Policy: `account_id = current_setting('app.current_account_id', true)::uuid`
- Enable: `ALTER TABLE entity_tag ENABLE ROW LEVEL SECURITY;`
- See: `entity_tag_rls_setup.py` for complete setup instructions

**Indexes**: 10 optimized indexes including:

- Composite: (entity_type, entity_id)
- Composite with filter: (entity_type, entity_id, is_active)
- Triple composite: (account_id, entity_type, tag_category)
- Partial index on is_active = true

**Unique Constraint**: (entity_type, entity_id, tag_name, account_id)

**Cloud Dependencies**: No

**Usage Example**:

```python
# Tag a test suite
tag = EntityTagTable(
    entity_type="suite",
    entity_id=suite.suite_id,
    tag_name="critical",
    tag_category="priority",
    account_id=user.account_id,
    created_by_user_id=user.auth_user_id
)

# Query with RLS
with AccountContext(connection, user_account_id):
    tags = session.query(EntityTagTable).filter(
        EntityTagTable.entity_type == "test_case",
        EntityTagTable.is_active == True
    ).all()  # RLS automatically filters by account
```

---

### Centralized Enumerations ✓ NEW

**File**: `database/enums.py`

All enums are defined centrally for consistency across the schema:

1. **AccountRoleEnum**: owner, admin, member, viewer
2. **SubscriptionTierEnum**: small, medium, large, big_af
3. **BillingCycleEnum**: monthly, yearly, perpetual
4. **PaymentMethodEnum**: credit_card, paypal, bank_transfer, system
5. **TagCategoryEnum**: functional, priority, automation_type, environment, regression, smoke, api, ui, database, integration, manual, deprecated
6. **EntityTypeEnum**: suite, test_case, action_chain, plan, api_action, database_action, repository_action, infrastructure_action, user_interface_action
7. **HttpMethodEnum**: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
8. **TestTypeEnum**: functional, integration, regression, smoke, performance, security
9. **AnalysisTypeEnum**: code_quality, security_scan, coverage, dependency_check, lint
10. **DatabaseTypeEnum**: postgresql, mssql, mysql, sqlite, oracle (with get_database_type() helper)
11. **CloudProviderEnum**: azure, aws, gcp
12. **InfrastructureOperationEnum**: deploy, destroy, scale, backup, restore
13. **AuditActionEnum**: create, update, delete, login, logout, access, etc.

---

### Action Tables (Future Implementation)

#### APIActionTable

**Status**: Placeholder (empty file)  
**Intended Purpose**: API test action definitions and sequences

#### InfrastructureActionTable

**Status**: Placeholder (empty file)  
**Intended Purpose**: Infrastructure automation actions (Docker, cloud resources)

#### RepositoryActionTable

**Status**: Placeholder (empty file)  
**Intended Purpose**: Source control and repository management actions

#### UserInterfaceActionTable

**Status**: Placeholder (empty file)  
**Intended Purpose**: Higher-level UI action compositions (may supersede direct IdentifierTable usage)

---

## Database Connection Patterns

### Configuration Type Conversion

**Critical Pattern**: Always convert between config types when using database engines:

```python
from common.service_connections.reporting_service.config import get_reporting_service_config
from common.service_connections.db_service.config import DatabaseServiceConfig
from common.service_connections.db_service.database.enums import DatabaseTypeEnum

# Get reporting config
reporting_config = get_reporting_service_config()

# Convert to database service config
database_config = DatabaseServiceConfig(
    database_type=DatabaseTypeEnum.get_database_type(reporting_config.database_type),
    database_server_name=reporting_config.database_server_name,
    database_name=reporting_config.database_name,
    # ... other fields
)
```

### Import Rules

**Always use absolute imports** in this codebase:

```python
# ✅ CORRECT
from common.service_connections.db_service.database import Base, PageTable
from common.service_connections.db_service.database.tables.page import PageTable

# ❌ WRONG - Relative imports fail in Docker
from .database import Base
from ..base import Base
```

## Cloud Service Integration

### Tables Requiring Cloud Connections

| Table | Cloud Service | Purpose |
| ----- | ------------- | ------- |
| `AccountTable` | AWS S3 / Azure Blob | Logo storage (`logo_url`) |
| `AccountSubscriptionTable` | Stripe / PayPal | Payment processing |
| `SystemUnderTestUserTable` | AWS Secrets Manager / Azure Key Vault | Credential storage |
| `EmailProcessorTable` | AWS SES / SendGrid / Email APIs | Email processing |

### Tables Without Cloud Dependencies

- `AuthUserTable` (potential future OAuth integration)
- `EnvironmentTable`
- `PageTable`
- `IdentifierTable`
- `PlanTable`
- `PurgeTable`

## User Access Control Matrix

| Table | Super Admin | Admin | Regular User | Automation Framework |
| ----- | ----------- | ----- | ------------ | -------------------- |
| `AccountTable` | Full CRUD | Read own | Read own | None |
| `AuthUserTable` | Full CRUD | CRUD non-admin users | Read own | None |
| `AccountSubscriptionTable` | Full CRUD | Read own | Read own | None |
| `EnvironmentTable` | Full CRUD | Full CRUD | Read only | Read only |
| `SystemUnderTestUserTable` | Full CRUD | Full CRUD | None | Read only |
| `PlanTable` | Full CRUD | Full CRUD | Read/Execute | Read/Execute |
| `EmailProcessorTable` | Full CRUD | Read only | None | Create/Update |
| `PageTable` | Full CRUD | Full CRUD | Read only | Read only |
| `IdentifierTable` | Full CRUD | Full CRUD | Read only | Read only |
| `PurgeTable` | Full CRUD | None | None | Update (background jobs) |

## Data Deletion and Cascade Rules

### CASCADE Deletes (Enforced by Foreign Keys)

1. **PageTable → IdentifierTable**
   - When a page is deleted, all associated identifiers are automatically deleted
   - Enforced by: `ForeignKey(..., ondelete="CASCADE")` + SQLAlchemy `cascade="all, delete-orphan"`

2. **EnvironmentTable → SystemUnderTestUserTable**
   - When an environment is deleted, all test users in that environment are deleted
   - Enforced by: `ForeignKey("environment.environment_id", ondelete="CASCADE")`

3. **SystemUnderTestTable → SystemUnderTestUserTable**
   - When a system is deleted, all associated test users are deleted
   - Enforced by: `ForeignKey("system_under_test.sut_id", ondelete="CASCADE")`

4. **AuthUserTable → AuthTokenTable** ✓ NEW
   - When a user is deleted, all authentication tokens are deleted
   - Enforced by: `ForeignKey(..., ondelete="CASCADE")` + SQLAlchemy `cascade="all, delete-orphan"`

5. **AccountTable → Many Tables** ✓ NEW
   - CASCADE delete to: SystemUnderTestTable, SuiteTable, TestCaseTable, ActionChainTable, EntityTagTable
   - Enforced by: `ForeignKey("account.account_id", ondelete="CASCADE")`

6. **Junction Tables CASCADE on Both Sides** ✓ NEW
   - All association tables delete when either parent is deleted
   - Examples: auth_user_account_association, plan_suite_association, suite_test_case_association

### RESTRICT Deletes (Prevent Accidental Loss)

- **AuthUserTable owner_user_id** in: SystemUnderTestTable, SuiteTable, TestCaseTable, ActionChainTable, EntityTagTable
  - Prevents deleting users who own critical resources
  - Enforced by: `ForeignKey(..., ondelete="RESTRICT")`

### SET NULL Deletes (Preserve Audit Trail)

- **AuditLogTable**: performed_by_user_id and account_id use SET NULL
  - Logs preserved even when user/account deleted
- **Soft Delete Fields**: deactivated_by_user_id uses SET NULL
  - Preserves record of who deactivated even if that user deleted

### Soft Deletes (Implemented Across Schema) ✓ NEW

All major tables now include soft delete pattern:

- **Fields**: `is_active` (Boolean), `deactivated_at` (DateTime), `deactivated_by_user_id` (FK)
- **Tables**: EnvironmentTable, IdentifierTable, PlanTable, PageTable, SystemUnderTestUserTable, SystemUnderTestTable, SuiteTable, TestCaseTable, ActionChainTable, EntityTagTable, AuthTokenTable
- **Indexes**: Partial indexes on `is_active = true` for query optimization
- **Recommended**: Soft delete instead of hard delete for audit trails

### No Automatic Deletes

- **EmailProcessorTable**: Retained for audit, purged by `PurgeTable` schedule
- **PurgeTable**: Manual deletion by Super Admin only
- **AuditLogTable**: Retained per retention policy (90/365 days), purged by schedule

## Development Environment Setup

### Local Development (PostgreSQL)

```bash
# Use UV for dependency management
uv sync

# Run with Docker Compose (PostgreSQL + pgAdmin)
sh run-fenrir-app.sh

# Run local app only (requires Azure MSSQL access)
sh entrypoint.sh
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing Database Operations

```bash
# Run database-specific tests
pytest tests/ -k "database"

# Test table operations
pytest tests/test_auth_users_api.py
```

## File Structure

```text
db_service/
├── README.md                          # This file
├── __init__.py
├── database.py                        # Main database module exports
├── db_ini.py                          # Database initialization utilities
├── db_manager.py                      # Database connection manager
├── Dockerfile                         # Container definition
├── database/
│   ├── __init__.py
│   ├── base.py                        # SQLAlchemy Base class
│   ├── engine.py                      # Database engine configuration
│   ├── enums.py                       # Database-specific enums
│   └── tables/
│       ├── __init__.py
│       ├── account.py                 # AccountTable definition
│       ├── account_subscription.py    # AccountSubscriptionTable
│       ├── auth_user.py               # AuthUserTable definition
│       ├── auth_user_subscription.py  # Placeholder
│       ├── email_processor.py         # EmailProcessorTable
│       ├── environment.py             # EnvironmentTable definition
│       ├── plan_table.py              # PlanTable definition
│       ├── purge_table.py             # PurgeTable definition
│       ├── system_under_test.py       # SystemUnderTestTable (partial)
│       ├── system_under_test_user.py  # SystemUnderTestUserTable
│       ├── user_subscription.py       # Placeholder
│       └── action_tables/
│           ├── __init__.py
│           ├── api_action.py          # Placeholder
│           ├── infrastructure_action.py # Placeholder
│           ├── repository_action.py   # Placeholder
│           └── user_interface_action/
│               ├── identifier.py      # IdentifierTable definition
│               ├── page.py            # PageTable definition
│               └── user_interface_action.py # Placeholder
└── models/
    ├── __init__.py
    ├── auth_user_model.py             # AuthUser data models
    ├── email_processor_model.py       # EmailProcessor data models
    ├── environment_model.py           # Environment data models
    ├── identifier_model.py            # Identifier data models
    ├── page_model.py                  # Page data models
    └── user_model.py                  # User data models
```

## Best Practices

### Table Documentation

Each table includes a comprehensive docstring answering:

1. **High-level purpose**: Goals accomplished by users
2. **User access levels**: Who should interact with this table
3. **Hierarchy position**: Parent/child relationships for architecture diagrams
4. **Deletion dependencies**: Cascade delete rules
5. **Cloud requirements**: External service integrations

### Adding New Tables

1. Create table file in appropriate directory under `database/tables/`
2. Define SQLAlchemy model with typed mappings (`Mapped[type]`)
3. Add comprehensive docstring answering the 5 standard questions
4. Add foreign key constraints with appropriate `ondelete` behavior
5. Create Alembic migration: `alembic revision --autogenerate -m "add_table_name"`
6. Update this README with table documentation
7. Create corresponding data model in `models/` if needed

### Foreign Key Best Practices

```python
# CASCADE delete for parent-child relationships
parent_id: Mapped[int] = mapped_column(
    sql.Integer, 
    sql.ForeignKey("parent.id", ondelete="CASCADE"), 
    nullable=False
)

# RESTRICT delete for reference integrity
account_id: Mapped[str] = mapped_column(
    sql.String(36),
    sql.ForeignKey("account.account_id", ondelete="RESTRICT"),
    nullable=False
)
```

## Future Enhancements

### Planned Tables

1. **TestSuiteTable**: Formal test suite definitions (currently referenced via string IDs)
2. **TestResultTable**: Test execution results and history
3. **Action Tables**: Complete implementation of API, Infrastructure, Repository, and UI action tables
4. **AuditLogTable**: Comprehensive audit trail for all table operations

### Relationship Improvements

1. Formalize `SystemUnderTestTable` → `EnvironmentTable` foreign key
2. Add explicit `AccountTable` → `PlanTable` foreign key via `owner_user_id`
3. Implement formal test suite table and update `PlanTable` relationships
4. Add account-level resource quotas based on `AccountSubscriptionTable.subscription_plan_type`

### Cloud Integration Enhancements

1. Multi-cloud support for secret management (AWS + Azure + GCP)
2. Cloud provider abstraction layer in `common/service_connections/cloud_service/`
3. Encrypted credential storage for local development
4. OAuth/SAML integration for `AuthUserTable`

## Support and Maintenance

For database-related issues or questions:

- Review table docstrings for business logic context
- Check Alembic migrations in `alembic/versions/`
- Consult `docs/implementation/DATABASE_MIGRATION_GUIDE.md`
- Reference FastAPI routes in `app/routes/` for usage examples

---

**Last Updated**: January 6, 2026  
**Database Version**: Schema managed by Alembic migrations  
**Supported Databases**: PostgreSQL (dev), MSSQL (Azure production)  

## Recent Schema Improvements (January 2026)

### Completed Enhancements

1. ✅ **Centralized Enumerations** - All 13 enums in `database/enums.py`
2. ✅ **Audit Logging** - AuditLogTable with 90/365-day retention policies
3. ✅ **Multi-Device Authentication** - AuthTokenTable with token rotation
4. ✅ **System Under Test** - Fully implemented SystemUnderTestTable
5. ✅ **Test Organization** - SuiteTable, TestCaseTable, ActionChainTable
6. ✅ **Junction Tables** - 5 many-to-many association tables
7. ✅ **Soft Delete Pattern** - Implemented across 11 tables with partial indexes
8. ✅ **Polymorphic Tagging** - EntityTagTable with Row-Level Security (RLS)
9. ✅ **Bidirectional Relationships** - All SQLAlchemy relationships with back_populates
10. ✅ **UUID Standardization** - UUID String(36) primary keys across new tables

### Key Architectural Improvements

- **Multi-Tenant Security**: Account-based isolation + RLS on tags
- **Data Integrity**: 50+ indexes, unique constraints, CASCADE/RESTRICT/SET NULL rules
- **Audit Compliance**: Comprehensive logging with retention policies
- **Query Performance**: Partial indexes on soft delete queries, composite indexes on common patterns
- **Flexibility**: Polymorphic tagging, JSONB fields for metadata, junction tables for scalability

### Migration Readiness

All table implementations are production-ready for Alembic migration. Key files:

- `database/enums.py` - Centralized enumerations
- `database/tables/*.py` - Table definitions with comprehensive docstrings
- `database/tables/entity_tag_rls_setup.py` - RLS setup documentation
- Junction tables in respective subdirectories

Next Steps:

1. Create Alembic migration: `alembic revision --autogenerate -m "major_schema_update_jan_2026"`
2. Review migration SQL for correctness
3. Enable RLS on entity_tag table (see entity_tag_rls_setup.py)
4. Update application code to use new relationships (deprecate string fields)
5. Implement token rotation background task
6. Configure audit log retention/purge jobs
