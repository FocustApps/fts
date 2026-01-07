from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy import text

with DB_ENGINE.connect() as conn:
    result = conn.execute(
        text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
    )
    tables = [row[0] for row in result]

print("Existing tables in database:")
for table in tables:
    print(f"  - {table}")

print(f"\nTotal: {len(tables)} tables")
