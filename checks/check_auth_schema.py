"""Check table schemas"""

from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy import inspect, text

inspector = inspect(DB_ENGINE)

# Check auth_users
cols = inspector.get_columns("auth_users")
print("=== auth_users columns in DATABASE ===")
for c in cols:
    print(f"  - {c['name']} ({c['type']})")

# Check environment
cols = inspector.get_columns("environment")
print("\n=== environment columns in DATABASE ===")
for c in cols:
    print(f"  - {c['name']} ({c['type']})")

# Check enum types
conn = DB_ENGINE.connect()
result = conn.execute(
    text(
        """
    SELECT typname FROM pg_type 
    WHERE typtype = 'e' 
    AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
"""
    )
)
enums = result.fetchall()
print("\n=== Custom enum types in DATABASE ===")
if enums:
    for e in enums:
        print(f"  - {e[0]}")
else:
    print("  (none)")
conn.close()
