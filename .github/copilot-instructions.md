# Fenrir Testing System - Copilot Instructions

## Architecture Overview

Fenrir is a **multi-application test automation hub** with a **service-oriented architecture** that abstracts cloud connections, databases, and selenium testing workflows. The system follows a **dual-environment pattern** with Azure deployments (MSSQL) and local development (PostgreSQL).

### Core Components

- **`fenrir_app.py`** - FastAPI application with HTML/API dual routing
- **`focustapps/`** - Individual application test suites (OCR, SafeCheck, TimeTracker, etc.)
- **`services/`** - Shared business logic (database, cloud, reporting, messaging)
- **`common/`** - Selenium automation framework and utilities
- **`scripts/`** - Standalone automation scripts with reporting integration

## Critical Development Patterns

### Import Rules
**NEVER use relative imports** in this codebase. Always use absolute imports starting from the package root:
```python
# ✅ CORRECT - Absolute imports
from common.service_connections.db_service.database import Base, PageTable
from common.service_connections.db_service.database.tables.page import PageTable
from app.config import get_config

# ❌ WRONG - Relative imports (will fail in Docker)
from .database import Base
from ..base import Base
```

### Page Object Model Architecture
Fenrir uses a **structured page object pattern** with inheritance and dataclass locators:
```python
# Standard pattern: Locators as dataclass + Page class + Section classes
@dataclass
class DashboardElements:
    table = (By.XPATH, "//table")
    search_input = (By.XPATH, ".//input[@placeholder='Search']")

class DashboardPage:
    def __init__(self, fenrir: SeleniumController, base_url: str):
        self.fenrir = fenrir
        self.base_url = base_url
```

### Test Structure with Class-Based Fixtures
All tests use **class-scoped fixtures** with shared SeleniumController:
```python
@pytest.mark.usefixtures("login_miner_ocr")  # Uses fixture name constant
class TestDashboard:
    # self.fenrir, self.driver, self.env available from fixture
    def test_something(self):
        dashboard = DashboardPage(fenrir=self.fenrir, base_url=self.env.url)
```

### Database Configuration Pattern
**Critical**: Always convert between config types when using database engines:
```python
# ReportingServiceConfig → DatabaseServiceConfig conversion required
reporting_config = get_reporting_service_config()
database_config = DatabaseServiceConfig(
    database_type=DatabaseTypeEnum.get_database_type(reporting_config.database_type),
    database_server_name=reporting_config.database_server_name,
    # ... other fields
)
```

### SeleniumController Retry Pattern
The framework has **built-in retry logic** for flaky UI interactions:
```python
# SeleniumController automatically retries find_element() with exponential backoff
# Default: 2 retries, 2 second timeout, handles StaleElementReferenceException
fenrir.find_element(By.ID, "element-id")  # Preferred over driver.find_element()
```

## Development Commands

### Package Management (Updated for UV)
```bash
# Use UV for dependency management (replaced Poetry)
uv sync                    # Install dependencies
uv add package-name       # Add new package
uv export --format=requirements-txt --output-file=requirements.txt  # Export for CI

# Local development with containers
sh run-fenrir-app.sh      # Full docker-compose stack with PostgreSQL
sh entrypoint.sh          # Local app only (requires Azure MSSQL access)
```

### Testing Execution Patterns
```bash
# Application-specific test execution
pytest tests/ocr/miner_ocr/          # Miner OCR tests
pytest tests/timetracker/            # TimeTracker tests
pytest -m "requires_data"            # Tests requiring live data

# Selenium Grid for parallel testing
cd docker/grid_compose && sh grid-helpers.sh
```

### FastAPI Route Pattern
Routes follow **dual API/view structure** with HTMX integration:
```python
# In app/routes/*.py - Always create both API and view routers
router_name_api_router = APIRouter(prefix="/api/name", tags=["api"])
router_name_views_router = APIRouter(prefix="/name", tags=["views"]) 
```

## Application-Specific Patterns

### Fixture Configuration Pattern
Each application has environment-specific fixtures:
```python
# Standard conftest.py pattern for all applications
LOGIN_APP_NAME = "login_app_name"  # Constant for fixture name

@pytest.fixture(scope="class")
def login_app_name(request):
    runner = get_test_runner_config()
    envs = query_all_environments(session=Session, engine=DB_ENGINE)
    # Environment selection logic based on runner.target_environment
    fenrir = driver_factory(browser=runner.browser, driver_location=location)
    # Login logic specific to application
    request.cls.fenrir = fenrir  # Makes fenrir available in test classes
```

### Page Object Inheritance Patterns
TimeTracker uses **SharedUIElements** for common components:
```python
class PageLocators(SharedUIElements):  # Inherits loading_bar, calendar_section, etc.
    page_specific_element = (By.XPATH, "//specific-element")
```

SafeCheck/OCR use **section-based composition** within pages:
```python
class AttachmentPage:
    # Base page with common navigation
    
class InputFieldsSection(AttachmentPage):  # Inherits navigation, adds field interactions
    def get_invoice_amount(self) -> WebElement:
        return self.fenrir.find_element(By.ID, "invoice-amount")
```

## Key Files for AI Context

- **`common/selenium_controller.py`** - Core automation framework with retry logic (440 lines)
- **`tests/{app}/conftest.py`** - Application-specific test fixtures and login patterns
- **`focustapps/{app}/`** - Page objects and application-specific automation logic
- **`services/db_service/db_manager.py`** - Database connection patterns and type handling
- **`docker-compose.yml`** - Local development with PostgreSQL setup
- **`azure-pipelines*.yml`** - CI/CD patterns (main: auto-test, dev/prod: manual deploy)

## Database Verification Scripts (`checks/`)

The `checks/` directory contains diagnostic scripts for verifying database schema alignment:

- **`check_missing_tables.py`** - Compare SQLAlchemy models against actual database tables; shows which tables exist vs missing
- **`check_all_tables.py`** - List all tables with their primary keys and first 5 columns
- **`check_auth_schema.py`** - Inspect `auth_users` and `environment` table schemas + list custom enum types
- **`compare_schema.py`** - Detailed schema comparison between database and Python models
- **`check_db_state.py`** - General database state inspection

**When to use**:
- Before creating migrations: Verify which tables need to be created
- After migrations: Confirm tables and enums were created successfully
- Debugging FK errors: Check actual column names and types in database
- Schema mismatches: Compare model definitions with database reality

**Common workflow**:
```bash
python checks/check_missing_tables.py  # See what needs migration
alembic revision --autogenerate -m "description"
python checks/check_all_tables.py      # Verify PKs for FK references
alembic upgrade head
python checks/check_missing_tables.py  # Confirm all tables created
```

## VS Code Integration

The workspace uses specific configurations for the multi-language codebase:
- **PostgreSQL syntax** for .sql files (`"*.sql": "postgres"`)
- **Black formatter** with 90-character line length
- **Pytest discovery** on save with class-based test execution
- **HTMX** and **Bootstrap** integration for FastAPI frontend

## App layer (FastAPI + HTMX + Jinja)

For app-specific guidance under `/app`, see `.github/app-instructions.md`.

Quick rules:
- Always create dual routers per feature: API and Views (Views: `include_in_schema=False`).
- Use `Jinja2Templates`; pass dataclass payloads as primitives or via `.model_dump()`.
- HTMX views render server-side partials; re-init JS behaviors after `htmx:afterSwap`.
- Table partial (`app/templates/table.html`): fixed layout + ellipsis, tooltip on hover, copy icon on truncated cells, re-bind after swaps and on resize.
- Enum dropdowns: pass `[(e.value, label)]` pairs; in templates, handle both enum and string for `selected`.
- WorkItem routes: GET new/edit pass `system_enum` + `work_item`; POST/PATCH parse and persist `system`.
