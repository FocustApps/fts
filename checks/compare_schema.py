"""Compare database schema with Python model definitions."""

from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy import inspect

inspector = inspect(DB_ENGINE)

# Get all tables from database
db_tables = set(inspector.get_table_names())

print("=== Checking auth_users table ===")
if "auth_users" in db_tables:
    cols = inspector.get_columns("auth_users")
    pk = inspector.get_pk_constraint("auth_users")
    print(f"Primary key column: {pk['constrained_columns']}")
    print("Columns:")
    for col in cols:
        print(f"  {col['name']}: {col['type']}")
else:
    print("  Table does not exist")

print("\n=== Checking existing enum types ===")
enum_query = """
SELECT n.nspname as schema, t.typname as typename 
FROM pg_type t 
LEFT JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace 
WHERE (t.typrelid = 0 OR (SELECT c.relkind = 'c' FROM pg_catalog.pg_class c WHERE c.oid = t.typrelid)) 
AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_type el WHERE el.oid = t.typelem AND el.typarray = t.oid)
AND t.typtype = 'e'
AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2;
"""
with DB_ENGINE.connect() as conn:
    result = conn.exec_driver_sql(enum_query)
    enums = result.fetchall()
    if enums:
        for schema, typename in enums:
            print(f"  {schema}.{typename}")
    else:
        print("  No custom enum types found")

print("\n=== Checking foreign key references to auth_users ===")
for table_name in sorted(db_tables):
    if table_name in ["alembic_version", "auth_users"]:
        continue
    fks = inspector.get_foreign_keys(table_name)
    for fk in fks:
        if fk["referred_table"] == "auth_users":
            print(
                f"{table_name}.{fk['constrained_columns'][0]} -> auth_users.{fk['referred_columns'][0]}"
            )
