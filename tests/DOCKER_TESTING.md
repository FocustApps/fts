# Docker Test Execution

Run tests in Docker containers against your services running in docker-compose.

## Quick Start

### Run all tests

```bash
sh run-tests.sh
```

### Run specific test file

```bash
sh run-tests.sh tests/test_purge_model.py
```

### Run specific test class or function

```bash
sh run-tests.sh tests/test_auth_service.py::TestAuthService::test_token_generation
```

### Run with custom pytest options

```bash
sh run-tests.sh tests/ -v -k "auth" --maxfail=3
```

### Run tests with coverage

```bash
sh run-tests.sh tests/ --cov=common --cov=app --cov-report=html
```

## Advanced Usage

### Run tests without the helper script

```bash
# Start services if not running
docker compose up -d postgres fenrir

# Run tests with the test profile
docker compose --profile test run --rm tests

# Or with custom pytest arguments
PYTEST_ARGS="tests/auth/ -v" docker compose --profile test run --rm tests
```

### Run tests in parallel

```bash
sh run-tests.sh tests/ -n auto  # Uses pytest-xdist
```

### Run only failed tests from last run

```bash
sh run-tests.sh tests/ --lf  # Last failed
sh run-tests.sh tests/ --ff  # Failed first
```

### Interactive debugging

```bash
# Run tests with interactive shell on failure
docker compose --profile test run --rm tests sh -c "pytest tests/ -v --pdb"
```

## Architecture

### Services

- **postgres**: PostgreSQL database (always runs)
- **fenrir**: FastAPI application (always runs)
- **tests**: Test container (runs on-demand with `--profile test`)

### Test Container Features

- ✅ Shares same network as application services
- ✅ Uses same database connection settings
- ✅ Has access to full codebase (`/fenrir`)
- ✅ Test results mounted to `./test-results/`
- ✅ Waits for database and application to be healthy

### Environment Variables

All services use matching database configuration:

- `DB_HOST=postgres` (container name)
- `DB_PORT=5432`
- `POSTGRES_DB=fenrir`
- `POSTGRES_USER=fenrir`
- `POSTGRES_PASSWORD=fenrirpass`
- `DATABASE_TYPE=postgres`

## Test Results

Test results and reports are saved to `./test-results/` directory on your host machine.

## Troubleshooting

### Tests can't connect to database

```bash
# Check database is healthy
docker compose ps postgres

# Check database logs
docker compose logs postgres
```

### Tests fail with import errors

```bash
# Rebuild test container
docker compose build tests

# Verify PYTHONPATH
docker compose --profile test run --rm tests sh -c "echo \$PYTHONPATH"
```

### Need fresh database state

```bash
# Stop everything and remove volumes
docker compose down -v

# Start services fresh
docker compose up -d postgres fenrir

# Run migrations
docker compose exec fenrir python manage_db.py upgrade

# Run tests
sh run-tests.sh
```

### View test container logs

```bash
docker compose --profile test logs tests
```

## CI/CD Integration

In CI pipelines, run tests with:

```bash
# Start services in background
docker compose up -d postgres fenrir

# Wait for healthy state
docker compose exec postgres pg_isready -U fenrir -d fenrir

# Run tests and capture exit code
docker compose --profile test run --rm tests
EXIT_CODE=$?

# Cleanup
docker compose down -v

exit $EXIT_CODE
```
