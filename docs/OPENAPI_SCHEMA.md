# OpenAPI Schema Generation

## Overview

FastAPI automatically generates an OpenAPI schema at `/openapi.json` for all registered routes. This schema is used by the frontend for TypeScript type generation.

## Configuration

### CORS Configuration

The FastAPI app must allow the Vite dev server origin to fetch the schema:

**File**: `example.env`

```env
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080
```

- `http://localhost:3000` - Legacy frontend port
- `http://localhost:5173` - Vite dev server (default)
- `http://localhost:8080` - FastAPI app self-reference

### Schema Generation Script

**File**: `app/scripts/generate_openapi_schema.py`

**Usage**:

```bash
# Generate and save to frontend directory
python app/scripts/generate_openapi_schema.py > frontend/openapi.json

# Or verify schema without saving
python app/scripts/generate_openapi_schema.py | head -50
```

**Requirements**:

- FastAPI app must be running on `http://localhost:8080`
- CORS must include requesting origin
- `requests` package installed (`uv add requests`)

## Schema Statistics

Current schema includes:

- **135 API endpoints** across 20+ routers
- **Authentication**: JWT with refresh tokens
- **Authorization**: Role-based (super_admin, owner, admin, member, viewer)
- **Multi-tenancy**: Account-scoped resources
- **Security**: HTTPBearer authentication scheme

## Frontend Integration

The generated `openapi.json` is used by `openapi-typescript` to generate TypeScript types:

**package.json** (Task 19):

```json
{
  "scripts": {
    "generate:api": "openapi-typescript openapi.json -o src/types/api.ts",
    "dev": "npm run generate:api && vite",
    "build": "npm run generate:api && tsc && vite build"
  }
}
```

**Generated types** will be available at:

```typescript
import type { paths, components } from './types/api';

// Type-safe API calls
type LoginRequest = components['schemas']['LoginRequest'];
type TokenResponse = components['schemas']['TokenResponse'];
```

## Updating the Schema

The schema should be regenerated whenever:

- New API routes are added
- Request/response models change
- Route parameters or query strings change
- Pydantic models are modified

**Workflow**:

1. Make backend changes
2. Start FastAPI app: `sh run-fenrir-app.sh`
3. Regenerate schema: `python app/scripts/generate_openapi_schema.py > frontend/openapi.json`
4. Commit updated schema with backend changes
5. Frontend TypeScript types will auto-generate on next `npm run dev`

## Troubleshooting

**Error: Could not connect to <http://localhost:8080>**

- Ensure FastAPI app is running: `docker compose ps`
- Check app logs: `docker compose logs fenrir`

**Error: HTTP 403 Forbidden**

- Verify CORS configuration includes requesting origin
- Check `.env` file has `CORS_ALLOW_ORIGINS=...http://localhost:5173...`
- Restart app after env changes: `docker compose restart fenrir`

**Schema missing routes**

- Verify routers are registered in `app/fenrir_app.py`
- Check routes have proper tags and operation IDs
- Ensure Pydantic models are imported (lazy imports may cause issues)

**Invalid JSON response**

- Check FastAPI app started successfully (no import errors)
- Verify `/openapi.json` endpoint works: `curl http://localhost:8080/openapi.json`
