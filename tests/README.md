# Authentication System Test Suite

This directory contains comprehensive unit and integration tests for the authentication system implemented in the FTS application.

## Test Structure

### Core Component Tests

- **`test_auth_service.py`** - Unit tests for the `AuthService` class
  - Token generation and validation
  - File persistence and loading
  - Token rotation and expiration
  - External sync callback integration
  - Error handling and edge cases
  - Thread safety and concurrent access

- **`test_auth_dependency.py`** - Unit tests for FastAPI authentication dependencies
  - `verify_auth_token()` - Required X-Auth-Token header validation
  - `verify_auth_token_optional()` - Optional authentication (returns None on failure)
  - `verify_auth_token_bearer()` - Bearer token authorization header validation
  - HTTP exception handling and status codes

- **`test_token_rotation.py`** - Unit tests for background token rotation
  - Background scheduler integration with APScheduler
  - FastAPI lifespan management
  - External sync placeholder functionality
  - Graceful handling when APScheduler is unavailable
  - Manual token rotation capabilities

### Configuration Tests

- **`test_auth_config.py`** - Configuration system tests
  - Environment variable loading and validation
  - Default value handling
  - Path, boolean, and interval validation
  - Configuration immutability and type safety

### Integration Tests

- **`test_auth_integration.py`** - End-to-end integration tests
  - Complete FastAPI application with auth-protected routes
  - X-Auth-Token and Bearer token authentication flows
  - Token rotation during active requests
  - Concurrent request handling
  - Service persistence across restarts

### Performance Tests

- **`test_auth_performance.py`** - Performance and stress tests
  - Token generation and validation performance
  - Concurrent access under load
  - Memory usage stability
  - High concurrency stress testing
  - Extended runtime stability
  - Async compatibility

### Test Configuration

- **`conftest.py`** - Shared test fixtures and utilities
  - Temporary file and directory fixtures
  - Mock configuration objects
  - Environment cleanup fixtures
  - Test data constants

## Running the Tests

### Run All Auth Tests

```bash
# From the fts directory
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/test_auth_service.py tests/test_auth_dependency.py tests/test_token_rotation.py -v

# Integration tests
pytest tests/test_auth_integration.py -v

# Performance tests
pytest tests/test_auth_performance.py -v

# Configuration tests
pytest tests/test_auth_config.py -v
```

### Run with Coverage

```bash
# Install coverage if not already available
pip install pytest-cov

# Run with coverage report
pytest tests/ --cov=app.services.auth_service --cov=app.dependencies.auth_dependency --cov=app.tasks.token_rotation --cov-report=html
```

### Run Tests with Markers

```bash
# Run only unit tests (if marked)
pytest -m unit

# Run only integration tests (if marked)
pytest -m integration

# Run only auth-related tests (if marked)
pytest -m auth
```

## Test Dependencies

The tests require the following Python packages:

- `pytest` - Testing framework
- `pytest-asyncio` - For async test support
- `fastapi` - For FastAPI integration tests
- `httpx` or `requests` - For HTTP client testing (via FastAPI TestClient)

Optional dependencies for enhanced testing:

- `pytest-cov` - Coverage reporting
- `pytest-xdist` - Parallel test execution
- `pytest-mock` - Enhanced mocking capabilities

## Test Coverage Areas

### Security Testing

- Cryptographically secure token generation
- Timing-safe token comparison
- File permission validation (600 - owner read/write only)
- Input validation and sanitization

### Reliability Testing

- Atomic file operations with backup mechanisms
- Thread-safe concurrent access
- Graceful error handling and recovery
- Service lifecycle management

### Performance Testing

- Token operations under load
- Memory usage and leak detection
- Concurrent request handling
- File I/O performance

### Integration Testing

- FastAPI dependency injection
- HTTP authentication flows
- Configuration system integration
- Background task scheduling

## Mock Strategy

Tests use comprehensive mocking to:

- Isolate components under test
- Simulate error conditions
- Control timing and environment
- Avoid external dependencies

Key mock points:

- File system operations
- Time/datetime functions
- External sync callbacks
- APScheduler components
- Configuration loading

## Test Data

The test suite uses:

- **Valid tokens**: 16-character hex strings (64-bit)
- **Invalid tokens**: Various malformed inputs
- **Temporary files**: Isolated file system operations
- **Mock configurations**: Controlled environment settings

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

- No external dependencies required
- Deterministic execution
- Comprehensive error reporting
- Performance benchmarking

## Debugging Failed Tests

### Common Issues

1. **File Permission Errors**
   - Ensure test files are created with proper permissions
   - Check temporary directory access

2. **Threading Issues**
   - Look for race conditions in concurrent tests
   - Verify thread-safe operations

3. **Configuration Problems**
   - Check environment variable setup
   - Verify configuration loading

4. **Mock Setup**
   - Ensure mocks are properly configured
   - Check mock call assertions

### Debug Commands

```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific failing test
pytest tests/test_auth_service.py::TestAuthService::test_specific_method -v -s

# Run with debugger on failure
pytest tests/ --pdb

# Run with detailed assertion output
pytest tests/ -vv
```
