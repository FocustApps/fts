export PYTHONPATH="${PYTHONPATH}:$(pwd)"

sh $(find $(pwd) -name update_static_files.sh) || exit 1

if [ "$ENVIRONMENT" = "local" ]; then
    uvicorn app.fenrir_app:app --host 0.0.0.0 --port 8080 --reload
else
    uvicorn app.fenrir_app:app --host 0.0.0.0 --port 8080
fi
