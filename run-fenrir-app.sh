#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory (where docker-compose.yml is located)
cd "$SCRIPT_DIR"

echo "Running from directory: $PWD"

# Check if ENVIRONMENT is set, default to local for this script
if [ -z "$ENVIRONMENT" ]; then
    export ENVIRONMENT=local
    echo "ENVIRONMENT not set, defaulting to: $ENVIRONMENT"
else
    echo "Using ENVIRONMENT: $ENVIRONMENT"
fi

docker compose down -v || true
docker rmi fts-fenrir fts-postgres || true

docker compose build --no-cache

# Pass environment variable to docker compose
ENVIRONMENT=$ENVIRONMENT docker compose up -d