#!/bin/bash
set -e

docker compose down -v || true
docker rmi fenrir-fenrir fenrir-postgres || true

docker compose build --no-cache

docker compose up -d