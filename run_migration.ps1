# PowerShell script to run alembic migration
# Usage: .\run_migration.ps1

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run alembic upgrade
python -m alembic upgrade head

Write-Host "Migration complete!"
