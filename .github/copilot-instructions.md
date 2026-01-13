# Fenrir Testing System - Copilot Instructions

## Architecture Overview

Fenrir is a **multi-application test automation hub** with a **service-oriented architecture** that abstracts cloud connections, databases, and selenium testing workflows. The system follows a **dual-environment pattern** with Azure deployments (MSSQL) and local development (PostgreSQL).

The application uses a **decoupled frontend-backend architecture**:
- **Backend**: FastAPI REST API with JWT authentication
- **Frontend**: React + TypeScript + Vite application in `frontend/` directory
- **Communication**: JSON API calls from React to FastAPI endpoints

## Database Schema - Source of Truth

**CRITICAL: Database tables are the pure source of truth** for all schema definitions. The SQLAlchemy table models in `common/service_connections/db_service/database/tables/` define the authoritative schema.

### Schema Hierarchy
1. **Database Tables** (`database/tables/*.py`) - **SOURCE OF TRUTH**
   - SQLAlchemy ORM models with `Mapped[]` type hints
   - Define actual column types, constraints, indexes, and relationships
   - Only modify tables when there is a confirmed bug
   
2. **Pydantic Models** (`models/*_model.py`) - **MUST MATCH TABLES**
   - Used for API validation, serialization, and business logic
   - Must mirror all fields from corresponding database tables
   - Update models whenever table schemas change
   
3. **Alembic Migrations** (`alembic/versions/*.py`) - Apply table changes to database

### When Making Schema Changes
- **Bug fixes in tables**: Create migration immediately after fixing table definition
- **New features**: Define table first, then update Pydantic model, then create migration
- **Field mismatches**: Always update Pydantic model to match table (never the reverse)

### Session Management and Function Signatures

**CRITICAL: Two distinct patterns for database functions** in `common/service_connections/db_service/models/*.py`:

1. **Insert/Update/Delete Functions** - Session as callable parameter:
   ```python
   from common.service_connections.db_service.database.engine import get_database_session as session
   
   def insert_model(model: Model, engine: Engine) -> str:
       """Insert returns the ID string."""
       with session(engine) as db_session:
           db_obj = ModelTable(**model.model_dump())
           db_session.add(db_obj)
           db_session.commit()
           db_session.refresh(db_obj)
       return db_obj.model_id  # Return ID string
   
   def update_model_by_id(id: str, model: Model, engine: Engine) -> bool:
       """Update returns True if successful."""
       with session(engine) as db_session:
           db_obj = db_session.get(ModelTable, id)
           # ... update logic ...
           db_session.commit()
       return True  # Return bool
   
   def deactivate_model_by_id(id: str, user_id: str, engine: Engine) -> bool:
       """Deactivate returns True if successful."""
       with session(engine) as db_session:
           # ... soft delete logic ...
           db_session.commit()
       return True  # Return bool
   ```

2. **Query Functions** - Session as Session object parameter:
   ```python
   from sqlalchemy.orm import Session
   
   def query_model_by_id(id: str, session: Session, engine: Engine) -> Model:
       """Query functions receive Session object, use it directly."""
       db_obj = session.query(ModelTable).filter(ModelTable.model_id == id).first()
       if not db_obj:
           raise ValueError(f"Model ID {id} not found.")
       return Model(**db_obj.__dict__)
   
   def query_models_by_account(account_id: str, session: Session, engine: Engine) -> List[Model]:
       """Use passed session directly - NOT with session(engine)."""
       models = session.query(ModelTable).filter(ModelTable.account_id == account_id).all()
       return [Model(**m.__dict__) for m in models]
   ```

3. **Test Pattern** - Tests import session as callable, create Session objects for queries:
   ```python
   from common.service_connections.db_service.database.engine import get_database_session as session
   
   def test_something(engine):
       # Insert/update/delete: pass session function (will be called inside function)
       model_id = insert_model(model, engine)
       
       # Query: create Session object with context manager, pass to function
       with session(engine) as db_session:
           result = query_model_by_id(model_id, db_session, engine)
   ```

**Common Errors to Avoid:**
- ❌ Using `with session(engine)` in query functions when session is a parameter (TypeError: 'Session' object is not callable)
- ❌ Using `session.query()` when session is imported globally as callable (AttributeError: 'function' object has no attribute 'query')
- ❌ Returning model objects from insert/update/deactivate functions (should return str/bool)
- ❌ Inconsistent test calling - query functions MUST receive Session object from `with session(engine) as db_session:`

**Fixing Legacy Model Files:**
When updating model files to conform to the session pattern:
1. Check all function signatures - identify insert/update/delete vs query functions
2. For insert/update/delete: Remove `session` parameter, add global import `from common.service_connections.db_service.database.engine import get_database_session as session`
3. For query functions: Keep `session: Session` parameter, ensure function uses `session.query()` directly (not `with session(engine)`)
4. Verify return types: insert → str (ID), update/deactivate → bool, query → Model object(s)
5. Check tests call functions correctly: insert/update/delete with `(model, engine)`, query with `(params, db_session, engine)` where `db_session` comes from `with session(engine) as db_session:`

**Test Factory Fixtures:**
Factories in `tests/fixtures/db_model_fixtures.py` should accept optional parameters with auto-creation defaults:
- `account_factory(owner_user_id: Optional[str] = None)` - Auto-creates owner via `auth_user_factory()` if not provided
- `system_under_test_factory(account_id: Optional[str] = None, owner_user_id: Optional[str] = None)` - Auto-creates both if needed
- `plan_factory` accepts both `name` and `plan_name` parameters for backward compatibility
- This pattern allows tests to call factories without setup boilerplate while maintaining flexibility

**Writing Tests with Database Functions:**
Tests must follow these patterns:
1. Import session: `from common.service_connections.db_service.database.engine import get_database_session as session`
2. For insert/update/deactivate: Call directly - `insert_model(model, engine)`  
3. For queries: Wrap in session context - `with session(engine) as db_session: result = query_model(id, db_session, engine)`
4. Use factory-created IDs for foreign keys (never hardcoded strings like "admin")
5. Factory parameters use `name` not model-specific names like `plan_name` or `suite_name`

### Core Components

- **`fenrir_app.py`** - FastAPI REST API backend
- **`frontend/`** - React + TypeScript + Vite application
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

# After making changes to app/ directory, copy to container and restart
docker compose cp app/. fenrir:/fenrir/app/ && docker compose restart fenrir
# Then check logs to verify successful restart:
docker compose logs fenrir --tail=50
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

### FastAPI REST API Pattern
Routes follow **pure REST API pattern** for React frontend consumption:
```python
# In app/routes/*.py - API routers serve JSON for frontend
router_name_api_router = APIRouter(prefix="/v1/api/name", tags=["api"])

@router_name_api_router.get("/", response_model=List[ModelResponse])
async def get_items(current_user: TokenPayload = Depends(get_current_user)):
    """All endpoints return JSON, authenticated via JWT."""
    # Return Pydantic models that serialize to JSON
    return items
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
- **Black formatter** with 90-character line length for Python
- **Pytest discovery** on save with class-based test execution
- **ESLint + Prettier** for TypeScript/React formatting
- **TypeScript strict mode** enabled in frontend/

## Frontend Layer (React + TypeScript + Vite)

### Directory Structure
```
frontend/
├── src/
│   ├── api/           # API client functions for backend calls
│   ├── components/    # Reusable React components
│   ├── pages/         # Route-level page components
│   ├── hooks/         # Custom React hooks
│   ├── types/         # TypeScript type definitions
│   ├── utils/         # Utility functions
│   └── App.tsx        # Root application component
├── vite.config.ts     # Vite configuration
└── tsconfig.json      # TypeScript configuration
```

### Best Practices

**API Communication**:
```typescript
// Use dedicated API client with JWT token management
// frontend/src/api/client.ts
export const apiClient = {
  get: async <T>(url: string): Promise<T> => {
    const token = sessionStorage.getItem('access_token');
    const response = await fetch(`/v1/api${url}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.json();
  }
};
```

**Type Safety**:
- Define TypeScript interfaces matching Pydantic models from backend
- Use strict mode: `"strict": true` in tsconfig.json
- Never use `any` - always define proper types
- Generate types from OpenAPI schema when possible

**Component Patterns**:
- Use functional components with hooks (not class components)
- Implement React Query/TanStack Query for data fetching and caching
- Use React Router for client-side routing
- Implement proper error boundaries for error handling

**State Management**:
- Use React Context for global state (auth, theme, user)
- Use React Query for server state (API data)
- Use local state (useState) for component-specific state
- Avoid Redux unless complex state management is absolutely required

**Authentication**:
- Store JWT access token in `sessionStorage` (24-hour expiry)
- Store refresh token in `localStorage` or `sessionStorage` based on remember-me
- Implement token refresh logic before expiry
- Use protected route wrapper components for authenticated pages

**Build & Development**:
```bash
cd frontend
npm run dev          # Development server with HMR
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # ESLint
npm run type-check   # TypeScript type checking
```

**Proxy Configuration**:
```typescript
// vite.config.ts - Proxy API calls to FastAPI backend in development
export default defineConfig({
  server: {
    proxy: {
      '/v1/api': 'http://localhost:8080',
      '/health': 'http://localhost:8080'
    }
  }
});
```
