"""
Database models package with categorized exports for Fenrir Test System.

This module provides centralized access to all database models, CRUD operations,
query helpers, validators, context managers, and cache management utilities.

Export Categories:
1. Core Models: Pydantic models for entity validation
2. CRUD Functions: Create, Read, Update, Delete operations
3. Multi-Tenant Queries: Account-scoped query functions
4. Soft Delete Operations: Deactivate/reactivate functions
5. Association Helpers: Relationship management utilities
6. Validators & Utilities: Validation config and helper functions
7. Context Managers: RLS and connection management
8. Cache Management: ActionChain reference cache utilities
"""

# ============================================================================
# Core Models
# ============================================================================

from common.service_connections.db_service.models.system_under_test_model import (
    SystemUnderTestModel,
)
from common.service_connections.db_service.models.test_case_model import (
    TestCaseModel,
)
from common.service_connections.db_service.models.suite_model import (
    SuiteModel,
)
from common.service_connections.db_service.models.action_chain_model import (
    ActionChainModel,
    ActionStepModel,
)
from common.service_connections.db_service.models.entity_tag_model import (
    EntityTagModel,
)
from common.service_connections.db_service.models.plan_model import (
    PlanModel,
)
from common.service_connections.db_service.models.suite_test_case_helpers import (
    SuiteTestCaseAssociationModel,
    SuiteWithTestCasesModel,
)
from common.service_connections.db_service.models.plan_suite_helpers import (
    PlanSuiteAssociationModel,
    PlanWithSuitesModel,
)
from common.service_connections.db_service.models.audit_log_model import (
    AuditLogModel,
    AuditChangeModel,
)
from common.service_connections.db_service.models.purge_model import (
    PurgeModel,
)


# ============================================================================
# CRUD Functions - SystemUnderTest
# ============================================================================

from common.service_connections.db_service.models.system_under_test_model import (
    insert_system_under_test,
    query_system_under_test_by_id,
    query_all_systems_under_test,
    update_system_under_test,
    drop_system_under_test,
)


# ============================================================================
# CRUD Functions - TestCase
# ============================================================================

from common.service_connections.db_service.models.test_case_model import (
    insert_test_case,
    query_test_case_by_id,
    query_all_test_cases,
    update_test_case,
    drop_test_case,
)


# ============================================================================
# CRUD Functions - Suite
# ============================================================================

from common.service_connections.db_service.models.suite_model import (
    insert_suite,
    query_suite_by_id,
    query_all_suites,
    update_suite,
    drop_suite,
)


# ============================================================================
# CRUD Functions - Plan
# ============================================================================

from common.service_connections.db_service.models.plan_model import (
    insert_plan,
    query_plan_by_id,
    query_all_plans,
    update_plan,
    drop_plan,
)


# ============================================================================
# CRUD Functions - ActionChain
# ============================================================================

from common.service_connections.db_service.models.action_chain_model import (
    insert_action_chain,
    query_action_chain_by_id,
    query_all_action_chains,
    update_action_chain,
    drop_action_chain,
)


# ============================================================================
# CRUD Functions - EntityTag
# ============================================================================

from common.service_connections.db_service.models.entity_tag_model import (
    insert_entity_tag,
    query_entity_tag_by_id,
    query_all_entity_tags,
    update_entity_tag,
    drop_entity_tag,
)


# ============================================================================
# CRUD Functions - AuditLog (INSERT-ONLY)
# ============================================================================

from common.service_connections.db_service.models.audit_log_model import (
    insert_audit_log,
    bulk_insert_audit_logs,
    query_audit_log_by_id,
)


# ============================================================================
# CRUD Functions - PurgeTable (Admin-Only)
# ============================================================================

from common.service_connections.db_service.models.purge_model import (
    insert_purge_schedule,
    query_purge_schedule_by_id,
    query_all_purge_schedules,
    update_purge_schedule,
    drop_purge_schedule,
)


# ============================================================================
# Multi-Tenant Queries
# ============================================================================

from common.service_connections.db_service.models.system_under_test_model import (
    query_systems_under_test_by_account,
    query_systems_under_test_by_owner,
    query_systems_under_test_by_account_and_owner,
)

from common.service_connections.db_service.models.test_case_model import (
    query_test_cases_by_account,
    query_test_cases_by_sut,
    query_test_cases_by_type,
)

from common.service_connections.db_service.models.suite_model import (
    query_suites_by_account,
    query_suites_by_owner,
    query_suites_by_account_and_owner,
)

from common.service_connections.db_service.models.action_chain_model import (
    query_action_chains_by_account,
    query_action_chains_by_sut,
)

from common.service_connections.db_service.models.plan_model import (
    query_plans_by_account,
    query_plans_by_owner,
    query_plans_by_status,
)

from common.service_connections.db_service.models.audit_log_model import (
    query_audit_logs_by_entity,
    query_audit_logs_by_account,
    query_audit_logs_by_user,
    query_audit_logs_by_action,
    query_sensitive_audit_logs,
    get_audit_log_count,
)


# ============================================================================
# Soft Delete Operations
# ============================================================================

from common.service_connections.db_service.models.system_under_test_model import (
    deactivate_system_under_test,
    reactivate_system_under_test,
)

from common.service_connections.db_service.models.test_case_model import (
    deactivate_test_case,
    reactivate_test_case,
)

from common.service_connections.db_service.models.suite_model import (
    deactivate_suite,
    reactivate_suite,
)

from common.service_connections.db_service.models.action_chain_model import (
    deactivate_action_chain,
    reactivate_action_chain,
)

from common.service_connections.db_service.models.entity_tag_model import (
    deactivate_entity_tag,
    reactivate_entity_tag,
)

from common.service_connections.db_service.models.plan_model import (
    deactivate_plan,
    reactivate_plan,
    update_plan_status,
)


# ============================================================================
# Association Helpers - Suite & TestCase
# ============================================================================

from common.service_connections.db_service.models.suite_test_case_helpers import (
    add_test_case_to_suite,
    remove_test_case_from_suite,
    reorder_suite_test_cases,
    update_test_case_execution_order,
    query_suite_with_test_cases,
    query_test_cases_for_suite,
    query_suites_for_test_case,
    get_suite_test_count,
    bulk_add_test_cases_to_suite,
    replace_suite_test_cases,
)


# ============================================================================
# Association Helpers - Plan & Suite
# ============================================================================

from common.service_connections.db_service.models.plan_suite_helpers import (
    add_suite_to_plan,
    remove_suite_from_plan,
    reorder_plan_suites,
    update_suite_execution_order,
    query_plan_with_suites,
    query_suites_for_plan,
    query_plans_for_suite,
    get_plan_suite_count,
    bulk_add_suites_to_plan,
    replace_plan_suites,
)


# ============================================================================
# Polymorphic Query Helpers - EntityTag
# ============================================================================

from common.service_connections.db_service.models.entity_tag_model import (
    query_tags_for_entity,
    query_entities_by_tag,
    query_tags_by_category,
    query_unique_tag_names,
    add_tags_to_entity,
    replace_entity_tags,
)


# ============================================================================
# JSONB Helpers - ActionChain
# ============================================================================

from common.service_connections.db_service.models.action_chain_model import (
    add_step_to_chain,
    remove_step_from_chain,
    update_step_at_index,
    reorder_steps,
    validate_action_references,
)


# ============================================================================
# Purge Job Helpers
# ============================================================================

from common.service_connections.db_service.models.purge_model import (
    query_purge_schedule_by_table,
    query_tables_due_for_purge,
    update_last_purged_at,
    update_purge_interval,
    get_purge_schedule_summary,
)


# ============================================================================
# Validators & Utilities
# ============================================================================

from common.config import (
    ValidationConfig,
    get_validation_config,
    should_validate_read,
    should_validate_write,
)


# ============================================================================
# Context Managers
# ============================================================================

from common.service_connections.db_service.models.entity_tag_model import (
    AccountRLSContext,
)


# ============================================================================
# Cache Management
# ============================================================================

from common.service_connections.db_service.models.action_chain_model import (
    ActionReferenceCache,
    clear_action_cache,
)


# ============================================================================
# Package Metadata
# ============================================================================

__all__ = [
    # Core Models
    "SystemUnderTestModel",
    "TestCaseModel",
    "SuiteModel",
    "ActionChainModel",
    "ActionStepModel",
    "EntityTagModel",
    "PlanModel",
    "SuiteTestCaseAssociationModel",
    "SuiteWithTestCasesModel",
    "PlanSuiteAssociationModel",
    "PlanWithSuitesModel",
    "AuditLogModel",
    "AuditChangeModel",
    "PurgeModel",
    # CRUD Functions - SystemUnderTest
    "insert_system_under_test",
    "query_system_under_test_by_id",
    "query_all_systems_under_test",
    "update_system_under_test",
    "drop_system_under_test",
    # CRUD Functions - TestCase
    "insert_test_case",
    "query_test_case_by_id",
    "query_all_test_cases",
    "update_test_case",
    "drop_test_case",
    # CRUD Functions - Suite
    "insert_suite",
    "query_suite_by_id",
    "query_all_suites",
    "update_suite",
    "drop_suite",
    # CRUD Functions - Plan
    "insert_plan",
    "query_plan_by_id",
    "query_all_plans",
    "update_plan",
    "drop_plan",
    # CRUD Functions - ActionChain
    "insert_action_chain",
    "query_action_chain_by_id",
    "query_all_action_chains",
    "update_action_chain",
    "drop_action_chain",
    # CRUD Functions - EntityTag
    "insert_entity_tag",
    "query_entity_tag_by_id",
    "query_all_entity_tags",
    "update_entity_tag",
    "drop_entity_tag",
    # CRUD Functions - AuditLog
    "insert_audit_log",
    "bulk_insert_audit_logs",
    "query_audit_log_by_id",
    # CRUD Functions - PurgeTable
    "insert_purge_schedule",
    "query_purge_schedule_by_id",
    "query_all_purge_schedules",
    "update_purge_schedule",
    "drop_purge_schedule",
    # Multi-Tenant Queries
    "query_systems_under_test_by_account",
    "query_systems_under_test_by_owner",
    "query_systems_under_test_by_account_and_owner",
    "query_test_cases_by_account",
    "query_test_cases_by_sut",
    "query_test_cases_by_type",
    "query_suites_by_account",
    "query_suites_by_owner",
    "query_suites_by_account_and_owner",
    "query_action_chains_by_account",
    "query_action_chains_by_sut",
    "query_plans_by_account",
    "query_plans_by_owner",
    "query_plans_by_status",
    "query_audit_logs_by_entity",
    "query_audit_logs_by_account",
    "query_audit_logs_by_user",
    "query_audit_logs_by_action",
    "query_sensitive_audit_logs",
    "get_audit_log_count",
    # Soft Delete Operations
    "deactivate_system_under_test",
    "reactivate_system_under_test",
    "deactivate_test_case",
    "reactivate_test_case",
    "deactivate_suite",
    "reactivate_suite",
    "deactivate_action_chain",
    "reactivate_action_chain",
    "deactivate_entity_tag",
    "reactivate_entity_tag",
    "deactivate_plan",
    "reactivate_plan",
    "update_plan_status",
    # Association Helpers - Suite & TestCase
    "add_test_case_to_suite",
    "remove_test_case_from_suite",
    "reorder_suite_test_cases",
    "update_test_case_execution_order",
    "query_suite_with_test_cases",
    "query_test_cases_for_suite",
    "query_suites_for_test_case",
    "get_suite_test_count",
    "bulk_add_test_cases_to_suite",
    "replace_suite_test_cases",
    # Association Helpers - Plan & Suite
    "add_suite_to_plan",
    "remove_suite_from_plan",
    "reorder_plan_suites",
    "update_suite_execution_order",
    "query_plan_with_suites",
    "query_suites_for_plan",
    "query_plans_for_suite",
    "get_plan_suite_count",
    "bulk_add_suites_to_plan",
    "replace_plan_suites",
    # Polymorphic Query Helpers - EntityTag
    "query_tags_for_entity",
    "query_entities_by_tag",
    "query_tags_by_category",
    "query_unique_tag_names",
    "add_tags_to_entity",
    "replace_entity_tags",
    # JSONB Helpers - ActionChain
    "add_step_to_chain",
    "remove_step_from_chain",
    "update_step_at_index",
    "reorder_steps",
    "validate_action_references",
    # Purge Job Helpers
    "query_purge_schedule_by_table",
    "query_tables_due_for_purge",
    "update_last_purged_at",
    "update_purge_interval",
    "get_purge_schedule_summary",
    # Validators & Utilities
    "ValidationConfig",
    "get_validation_config",
    "should_validate_read",
    "should_validate_write",
    # Context Managers
    "AccountRLSContext",
    # Cache Management
    "ActionReferenceCache",
    "clear_action_cache",
]
