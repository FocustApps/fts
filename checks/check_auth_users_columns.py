from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy import inspect

inspector = inspect(DB_ENGINE)
print("\nauth_users columns:")
cols = inspector.get_columns("auth_users")
for c in cols:
    print(f"  - {c['name']}: {c['type']}")
