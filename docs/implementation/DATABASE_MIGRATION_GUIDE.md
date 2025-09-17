# Database Management with SQLAlchemy + Alembic

This guide explains the new database management approach for Fenrir that replaces manual SQL files with automated migrations.

## 🎯 Benefits of This Approach

### ✅ What We Gained

- **Single Source of Truth**: All schema defined in SQLAlchemy models
- **Automatic Migrations**: Alembic detects model changes and generates migrations
- **Version Control**: Full history of all schema changes
- **Environment Consistency**: Same schema across dev/test/prod
- **Rollback Support**: Can easily revert problematic changes
- **Type Safety**: Full Python type hints and validation

### ❌ What We Eliminated

- **Schema Drift**: No more manual SQL files getting out of sync
- **Dual Maintenance**: No need to update both SQL and Python models
- **Manual Migration Scripts**: No more hand-written migration files
- **Environment Inconsistencies**: Guaranteed same schema everywhere

## 🏗️ Architecture Overview

```text
fts/
├── common/service_connections/db_service/
│   ├── database.py              # 🔥 NEW: Central models & engine config
│   ├── page_model.py           # ✏️  UPDATED: Uses centralized models
│   ├── user_model.py           # ✏️  UPDATED: Uses centralized models
│   └── environment_model.py    # ✏️  UPDATED: Uses centralized models
├── alembic/                     # 🔥 NEW: Migration management
│   ├── env.py                  # Alembic environment config
│   ├── script.py.mako          # Migration template
│   └── versions/               # Generated migration files
├── alembic.ini                  # 🔥 NEW: Alembic configuration
├── manage_db.py                # 🔥 NEW: Database management CLI
└── pyproject.toml              # ✏️  UPDATED: Added Alembic dependency
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd /Users/zachsanders/automation/Fenrir/fts
uv sync  # This will install the new alembic dependency
```

### 2. Create Initial Migration

```bash
# Create migration from current models
python manage_db.py migrate -m "Initial schema from existing models"

# Apply the migration
python manage_db.py upgrade
```

### 3. Verify Setup

```bash
# Check current database version
python manage_db.py current

# Show migration history
python manage_db.py history
```

## 📋 Daily Workflow

### Making Schema Changes

1. **Modify SQLAlchemy Models** in `database.py`:

   ```python
   # Example: Add new column to PageTable
   class PageTable(Base):
       # ... existing fields ...
       new_field: Mapped[Optional[str]] = mapped_column(sql.String(255))
   ```

2. **Generate Migration**:

   ```bash
   python manage_db.py migrate -m "Add new_field to pages"
   ```

3. **Review Generated Migration** in `alembic/versions/`:

   ```python
   # Alembic auto-generates this:
   def upgrade() -> None:
       op.add_column('page', sa.Column('new_field', sa.String(255), nullable=True))

   def downgrade() -> None:
       op.drop_column('page', 'new_field')
   ```

4. **Apply Migration**:

   ```bash
   python manage_db.py upgrade
   ```

### Rolling Back Changes

```bash
# Rollback last migration
python manage_db.py downgrade

# Rollback to specific revision
python manage_db.py downgrade abc123

# Check what changed
python manage_db.py history
```

## 🔧 Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize Alembic (one-time setup) | `python manage_db.py init` |
| `migrate` | Create migration from model changes | `python manage_db.py migrate -m "Add user table"` |
| `upgrade` | Apply pending migrations | `python manage_db.py upgrade` |
| `downgrade` | Rollback migrations | `python manage_db.py downgrade` |
| `current` | Show current version | `python manage_db.py current` |
| `history` | Show migration history | `python manage_db.py history` |
| `create-all` | Create tables directly (bypass migrations) | `python manage_db.py create-all` |
| `drop-all` | Drop all tables ⚠️ DANGEROUS | `python manage_db.py drop-all` |

## 🔄 Migration from Old System

### Phase 1: Immediate (Replace SQL with Alembic)

1. ✅ **DONE**: Created `database.py` with all models
2. ✅ **DONE**: Added Alembic configuration and CLI
3. ✅ **DONE**: Updated `pyproject.toml` with dependencies

### Phase 2: Update Existing Models (Recommended)

```bash
# Update each model file to import from database.py instead of defining locally
# Example for user_model.py:
from common.service_connections.db_service.database import Base, UserTable
```

### Phase 3: Remove Old Files (Optional)

```bash
# After confirming everything works:
rm common/service_connections/db_service/tables/init.sql
rm common/service_connections/db_service/migrations.py
```

## 🐳 Docker Integration

### Update docker-compose.yml

```yaml
# Remove any volume mounts to init.sql
services:
  postgres:
    # Remove: - ./common/service_connections/db_service/tables/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_DB: fenrir
      POSTGRES_USER: fenrir
      POSTGRES_PASSWORD: fenrirpass

  fenrir:
    # Add migration command to entrypoint
    command: >
      sh -c "python manage_db.py upgrade && 
             uvicorn app.fenrir_app:app --host 0.0.0.0 --port 8080"
```

## 🧪 Testing

### Development Database

```bash
# Create test database
python manage_db.py create-all

# Run tests
pytest

# Clean up
python manage_db.py drop-all
```

### Production Deployment

```bash
# Apply migrations
python manage_db.py upgrade

# Check status
python manage_db.py current
```

## 🚨 Common Issues & Solutions

### "Target database is not up to date"

```bash
# Check current version
python manage_db.py current

# Apply pending migrations
python manage_db.py upgrade
```

### "Can't locate revision"

```bash
# Show migration history
python manage_db.py history

# Reset to latest
python manage_db.py upgrade head
```

### "Table already exists"

```bash
# If migrating from existing database, mark current state as migrated:
# This creates a migration without changes, marking current state as baseline
python manage_db.py migrate -m "Baseline from existing database"
```

## 🎯 Best Practices

1. **Always Review Migrations**: Check generated migrations before applying
2. **Use Descriptive Messages**: `python manage_db.py migrate -m "Add user authentication"`
3. **Test Rollbacks**: Ensure `downgrade()` functions work correctly
4. **Backup Before Production**: Always backup before running migrations in production
5. **Keep Models in Sync**: Only modify schema through SQLAlchemy models
6. **Version Control Migrations**: Commit migration files to Git

## 🔗 Integration with Existing Code

Your existing code using models should work with minimal changes:

```python
# OLD: Multiple imports and Base definitions
from common.service_connections.db_service.page_model import PageTable, PageModel

# NEW: Single import from centralized location  
from common.service_connections.db_service.database import PageTable
from common.service_connections.db_service.page_model import PageModel
```

The Pydantic models (like `PageModel`) remain unchanged - only the SQLAlchemy table definitions are centralized.
