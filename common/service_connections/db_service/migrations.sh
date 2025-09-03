export PYTHONPATH="${PYTHONPATH}:$(pwd)/common"

python $(find $(pwd)/common/service_connections/db_service -name migrations.py) || exit 1