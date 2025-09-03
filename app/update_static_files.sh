export PYTHONPATH="${PYTHONPATH}:$(pwd)/services"

echo $PYTHONPATH

python $(find $(pwd) -name update_static_files.py) || exit 1