from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy import inspect

inspector = inspect(DB_ENGINE)
existing_tables = set(inspector.get_table_names())

# Tables from model definitions
model_tables = {
    "action_chain",
    "audit_log",
    "entity_tag",
    "plan",
    "plan_suite_association",
    "purgeTable",
    "suite_test_case_association",
    "system_environment_association",
    "auth_user_account_association",
    "auth_tokens",
    "test_case",
    "account_subscription",
    "suite",
    "system_under_test",
    "user",
    "fenrir_actions",
}

print("=== Tables in Database ===")
for table in sorted(existing_tables):
    print(f"  ✓ {table}")

print(f"\n=== Missing Tables ===")
missing = model_tables - existing_tables
for table in sorted(missing):
    print(f"  ✗ {table}")

print(f"\n=== Summary ===")
print(f"Total tables in DB: {len(existing_tables)}")
print(f"Total model tables: {len(model_tables)}")
print(f"Missing: {len(missing)}")
