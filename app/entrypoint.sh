export PYTHONPATH="${PYTHONPATH}:$(pwd)"

sh $(find $(pwd) -name update_static_files.sh) || exit 1

# Run database migrations before starting the application
echo "Running database migrations..."
python manage_db.py upgrade || {
    echo "Migration failed, attempting to initialize database..."
    python manage_db.py upgrade
}

# Seed admin user after successful migration
echo "Seeding admin user..."
python seed_admin_user.py || {
    echo "Admin user seeding completed (user may already exist)"
}

if [ "$ENVIRONMENT" = "local" ]; then
    uvicorn app.fenrir_app:app --host 0.0.0.0 --port 8080 --reload
else
    uvicorn app.fenrir_app:app --host 0.0.0.0 --port 8080
fi
