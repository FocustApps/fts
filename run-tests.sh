#!/bin/bash

# Fenrir Test Runner Script
# Runs tests in Docker container against running services

set -e

echo "🧪 Fenrir Test Runner"
echo "===================="
echo ""

# Check if services are running
if ! docker compose ps | grep -q "fenrir.*running"; then
    echo "⚠️  Services not running. Starting services first..."
    docker compose up -d postgres fenrir
    echo "⏳ Waiting for services to be healthy..."
    sleep 5
fi

# Parse command line arguments
PYTEST_ARGS="${PYTEST_ARGS:-tests/ -v --tb=short}"

# Allow passing custom pytest arguments
if [ $# -gt 0 ]; then
    PYTEST_ARGS="$@"
fi

echo "📋 Running tests with: $PYTEST_ARGS"
echo ""

# Run tests with the test profile
PYTEST_ARGS="$PYTEST_ARGS" docker compose --profile test run --rm tests

# Check exit code
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE
