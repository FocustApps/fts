export PYTHONPATH="${PYTHONPATH}:$(pwd)"

sh $(find $(pwd) -name update_static_files.sh) || exit 1

# Wait for database to be fully ready (beyond healthcheck)
echo "Waiting for database to be ready..."
sleep 2

# Run database migrations before starting the application
echo "Running Alembic migrations..."
echo "Current migration status:"
python manage_db.py current || echo "No current migration (fresh database)"

echo "Applying migrations..."
python manage_db.py upgrade || {
    echo "❌ Migration failed! Check database connection and alembic state."
    exit 1
}

echo "✅ Migrations applied successfully!"
python manage_db.py current

# Seed admin user after successful migration
echo "Seeding admin user..."
python seed_admin_user.py || {
    echo "Admin user seeding completed (user may already exist)"
}

# Start the application
uvicorn app.fenrir_app:app --host 0.0.0.0 --port 8080 --reload
