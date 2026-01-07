from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy import text

print(f"Database URL: {DB_ENGINE.url}")

with DB_ENGINE.connect() as conn:
    # Check if alembic_version table exists
    result = conn.execute(
        text(
            """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'alembic_version'
        )
    """
        )
    )
    has_alembic = result.scalar()
    print(f"Alembic version table exists: {has_alembic}")

    if has_alembic:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        print(f"Current migration: {version}")

    # List all tables
    result = conn.execute(
        text(
            """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname='public' 
        ORDER BY tablename
    """
        )
    )
    tables = [row[0] for row in result]

    print(f"\nAll tables ({len(tables)}):")
    for table in tables:
        print(f"  - {table}")
