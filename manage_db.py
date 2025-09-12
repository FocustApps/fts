#!/usr/bin/env python3
"""
Database management CLI for Fenrir.

This script provides commands for managing database schema migrations,
initialization, and maintenance using Alembic and SQLAlchemy.

Usage:
    python manage_db.py init         # Initialize Alembic (first time setup)
    python manage_db.py migrate      # Create new migration from model changes
    python manage_db.py upgrade      # Apply pending migrations
    python manage_db.py downgrade    # Rollback last migration
    python manage_db.py current      # Show current migration version
    python manage_db.py history      # Show migration history
    python manage_db.py create-all   # Create all tables (bypass migrations)
    python manage_db.py drop-all     # Drop all tables (DANGEROUS!)
"""

import sys
import subprocess
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from common.service_connections.db_service.database import (
    get_database_url_from_config,
    create_all_tables,
    drop_all_tables,
    create_database_engine,
)


def run_alembic_command(command: list[str]) -> None:
    """Run an Alembic command."""
    try:
        result = subprocess.run(
            ["python", "-m", "alembic"] + command,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        if result.stderr:
            print(f"Warning: {result.stderr}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error running alembic {' '.join(command)}: {e}", file=sys.stderr)
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(
            "Error: Alembic not found. Please install it with: pip install alembic",
            file=sys.stderr,
        )
        sys.exit(1)


def init_alembic() -> None:
    """Initialize Alembic for the first time."""
    print("Initializing Alembic migration environment...")
    # Alembic init was already done by creating the files above
    print("✅ Alembic initialized. You can now create your first migration.")
    print("💡 Next steps:")
    print("   1. Run: python manage_db.py migrate -m 'Initial migration'")
    print("   2. Run: python manage_db.py upgrade")


def create_migration(message: str = None) -> None:
    """Create a new migration from model changes."""
    print("Creating new migration from model changes...")
    cmd = ["revision", "--autogenerate"]
    if message:
        cmd.extend(["-m", message])
    else:
        cmd.extend(["-m", "Auto-generated migration"])

    run_alembic_command(cmd)
    print("✅ Migration created successfully!")


def upgrade_database(revision: str = "head") -> None:
    """Apply pending migrations."""
    print(f"Upgrading database to {revision}...")
    run_alembic_command(["upgrade", revision])
    print("✅ Database upgraded successfully!")


def downgrade_database(revision: str = "-1") -> None:
    """Rollback migrations."""
    print(f"Downgrading database to {revision}...")
    run_alembic_command(["downgrade", revision])
    print("✅ Database downgraded successfully!")


def show_current() -> None:
    """Show current migration version."""
    print("Current database version:")
    run_alembic_command(["current"])


def show_history() -> None:
    """Show migration history."""
    print("Migration history:")
    run_alembic_command(["history"])


def create_tables_directly() -> None:
    """Create all tables directly (bypass migrations)."""
    print("Creating all tables directly from SQLAlchemy models...")
    try:
        database_url = get_database_url_from_config()
        engine = create_database_engine(database_url)
        create_all_tables(engine)
        print("✅ All tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}", file=sys.stderr)
        sys.exit(1)


def drop_tables() -> None:
    """Drop all tables (dangerous operation)."""
    print("⚠️  WARNING: This will DROP ALL TABLES!")
    response = input("Are you sure? Type 'yes' to continue: ")
    if response.lower() != "yes":
        print("Operation cancelled.")
        return

    try:
        database_url = get_database_url_from_config()
        engine = create_database_engine(database_url)
        drop_all_tables(engine)
        print("✅ All tables dropped!")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "init":
        init_alembic()
    elif command == "migrate":
        message = None
        if len(sys.argv) > 2 and sys.argv[2] == "-m" and len(sys.argv) > 3:
            message = sys.argv[3]
        create_migration(message)
    elif command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        upgrade_database(revision)
    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        downgrade_database(revision)
    elif command == "current":
        show_current()
    elif command == "history":
        show_history()
    elif command == "create-all":
        create_tables_directly()
    elif command == "drop-all":
        drop_tables()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
