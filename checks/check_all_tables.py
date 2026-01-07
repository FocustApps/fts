"""Check all table primary keys"""

from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy import inspect

inspector = inspect(DB_ENGINE)
tables = inspector.get_table_names()

print("=== Primary Key Columns for All Tables ===")
for table in sorted(tables):
    if table == "alembic_version":
        continue
    pk = inspector.get_pk_constraint(table)
    cols = inspector.get_columns(table)
    col_names = [c["name"] for c in cols]
    print(f"\n{table}:")
    print(f"  Primary Key: {pk['constrained_columns']}")
    print(f"  All Columns: {col_names[:5]}...")  # First 5 columns
