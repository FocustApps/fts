from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy import inspect

inspector = inspect(DB_ENGINE)
pk = inspector.get_pk_constraint("auth_users")
print("Primary key:", pk)
print("\nColumns:")
cols = inspector.get_columns("auth_users")
for c in cols:
    print(f'  {c["name"]}: {c["type"]}')
