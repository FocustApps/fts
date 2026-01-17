#!/bin/sh
set -e

echo "=================================="
echo "Running Fenrir Test Suite"
echo "=================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall results
FAILED_GROUPS=""

run_test_group() {
    group_name=$1
    test_path=$2
    
    echo ""
    echo "=================================="
    echo "Running: $group_name"
    echo "=================================="
    
    if pytest "$test_path" -v --tb=short -q; then
        printf "${GREEN}✓ $group_name PASSED${NC}\n"
        return 0
    else
        printf "${RED}✗ $group_name FAILED${NC}\n"
        FAILED_GROUPS="$FAILED_GROUPS|$group_name"
        return 1
    fi
}

# Run test groups
echo "Starting test execution in chunks..."
echo ""

# Auth tests
run_test_group "Auth Routes" "tests/auth/test_auth_routes.py" || true
run_test_group "Auth Service" "tests/auth/test_auth_service.py" || true
run_test_group "Auth User Service" "tests/auth/test_user_auth_service.py" || true
run_test_group "Auth Dependency" "tests/auth/test_auth_dependency.py" || true
run_test_group "Auth Integration" "tests/auth/test_auth_integration.py" || true
run_test_group "Auth Performance" "tests/auth/test_auth_performance.py" || true
run_test_group "Token Rotation" "tests/auth/test_token_rotation.py" || true

# Model tests
run_test_group "Core Models" "tests/models/test_core_models.py" || true
run_test_group "Plan Model" "tests/models/test_plan_model.py" || true
run_test_group "Entity Tag Model" "tests/models/test_entity_tag_model.py" || true
run_test_group "Audit Log Model" "tests/models/test_audit_log_model.py" || true
run_test_group "Action Chain Model" "tests/models/test_action_chain_model.py" || true
run_test_group "Purge Model" "tests/models/test_purge_model.py" || true

# Infrastructure tests
run_test_group "Association Helpers" "tests/infrastructure/test_association_helpers.py" || true
run_test_group "Database Schema" "tests/infrastructure/test_database_schema.py" || true

# Composite/Integration tests
run_test_group "Composite Fixtures" "tests/infrastructure/test_composite_fixtures_examples.py" || true

# Multi-user auth tests (if they exist)
if [ -f "tests/auth/test_multi_user_auth_service.py" ]; then
    run_test_group "Multi-User Auth Service" "tests/auth/test_multi_user_auth_service.py" || true
fi

# Summary
echo ""
echo "=================================="
echo "Test Suite Summary"
echo "=================================="

# Get overall statistics using pytest
echo ""
echo "Running final pytest summary..."
pytest tests/ -v --tb=no -q 2>&1 | tail -10

echo ""
if [ -z "$FAILED_GROUPS" ]; then
    printf "${GREEN}✓ All test groups completed successfully!${NC}\n"
    exit 0
else
    printf "${RED}✗ Failed test groups:${NC}\n"
    echo "$FAILED_GROUPS" | tr '|' '\n' | grep -v '^$' | while read group; do
        printf "  ${RED}- $group${NC}\n"
    done
    echo ""
    echo "Run individual groups for detailed error messages:"
    echo "  pytest tests/path/to/test_file.py -v"
    exit 1
fi
