# App instructions (FastAPI + HTMX + Jinja)

These rules focus on the `/app` web layer so AI tools and contributors follow the same patterns.

## Authentication System

The Fenrir Testing System uses a comprehensive token-based authentication system with the following components:

### Token-Based Authentication

- **64-character cryptographically secure tokens** (256-bit entropy)
- **60-minute rotation interval** (configurable via `AUTH_ROTATION_INTERVAL_MINUTES`)
- **Automatic email notifications** when new tokens are generated
- **Session cookie management** for web interface authentication

### Auth Service (`app/services/auth_service.py`)

- **Global singleton pattern**: Use `get_auth_service()` instead of direct `AuthService()` instantiation
- **Token persistence**: Tokens stored in `/tmp/fenrir_auth_token.txt` with creation/expiration timestamps
- **External sync callback**: Integrates with email service for token notifications
- **Thread-safe operations**: Atomic file operations with proper locking

### Authentication Routes (`app/routes/auth.py`)

- **Login page**: `/auth/login` - Professional HTMX-powered login form
- **Login processing**: POST `/auth/login` - Validates tokens and creates session cookies
- **Logout**: POST `/auth/logout` - Clears session cookies and redirects
- **Token validation**: Validates both header tokens and session cookies

### Authentication Middleware

- **Global protection**: All endpoints require authentication by default
- **Cookie validation**: Automatic session cookie checking
- **Header validation**: Supports `X-Auth-Token` and `Authorization: Bearer` headers
- **Redirect handling**: Unauthenticated requests redirect to login page

### Email Integration (`app/services/email_service.py`)

- **Gmail SMTP_SSL**: Uses port 465 for secure email delivery
- **Automatic notifications**: Sends new tokens to configured recipient
- **Configuration**: Uses `EMAIL_USER`/`EMAIL_PASSWORD` for authentication
- **Error handling**: Graceful degradation if email service unavailable

### Environment Configuration

Required environment variables:

```properties
# Authentication
AUTH_TOKEN_LENGTH=64
AUTH_ROTATION_INTERVAL_MINUTES=60
AUTH_TOKEN_FILE_PATH=/tmp/fenrir_auth_token.txt

# Email Notifications
EMAIL_NOTIFICATION_ENABLED=true
EMAIL_RECIPIENT=admin@company.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
EMAIL_USER=sender@gmail.com
EMAIL_PASSWORD=app-password
EMAIL_SUBJECT=Fenrir Authentication Token Update
```

### Usage Patterns

#### Protecting Routes

All routes are protected by default. For API endpoints that need token validation:

```python
# Token automatically validated by middleware
@router.get("/api/protected-endpoint")
async def protected_endpoint():
    # This endpoint requires valid authentication
    return {"status": "authenticated"}
```

#### Getting Auth Service

Always use the global service pattern:

```python
from app.services.auth_service import get_auth_service

try:
    auth_service = get_auth_service()
    current_token = auth_service.get_current_token()
except RuntimeError:
    # Handle case where auth service not initialized
    return {"error": "Authentication service unavailable"}
```

#### Login Flow

1. User visits protected endpoint → Redirected to `/auth/login`
2. User enters 64-character token → POST `/auth/login`
3. Token validated → Session cookie set → Redirect to dashboard
4. Future requests use session cookie for authentication

#### Token Rotation

- **Automatic**: Tokens rotate every 60 minutes (if APScheduler available)
- **Manual**: Can be triggered by restarting the application
- **Email notification**: New tokens automatically emailed to configured recipient
- **Graceful handling**: Old tokens remain valid briefly during rotation

### Security Features

- **Cryptographically secure**: Uses `secrets.token_bytes()` for token generation
- **HTTPOnly cookies**: Session cookies not accessible via JavaScript
- **Secure headers**: Proper SameSite and security attributes
- **Token expiration**: Tokens automatically expire after configured interval
- **Input validation**: 64-character length validation on login form

### Testing Considerations

- **Development tokens**: Use environment-specific token files
- **Mock email service**: Disable email notifications in test environments
- **Session testing**: Test both cookie and header authentication methods
- **Token rotation**: Test token expiration and renewal flows

## Routers

- Always create dual routers for each feature module:
  - API: `router_name_api_router = APIRouter(prefix="/api/name", tags=["api"])`
  - Views: `router_name_views_router = APIRouter(prefix="/name", tags=["views"], include_in_schema=False)`

## Templates and Context

- Use `Jinja2Templates` from FastAPI.
- Prefer dataclass payloads for views; pass primitives or `.model_dump()` to templates.
- When lists can be empty, derive headers safely and provide defaults.

## HTMX

- Return server-rendered partials for views (SSR-friendly).
- Re-initialize front-end behaviors after HTMX swaps using the `htmx:afterSwap` event.

## Table partial (`app/templates/table.html`)

- Fixed layout: `table-layout: fixed; width: 100%`.
- Truncate long content with ellipsis; show tooltip on hover (title or Bootstrap tooltip).
- Show a copy icon for truncated cells; clicking copies full text. Re-bind copy handlers after swaps and on resize.

## Enum dropdowns in forms

- Build options in routes: `system_enum = [(e.value, e.name.replace("_"," ").title()) for e in SystemEnum]`.
- In templates, handle selected state for both raw string and enum-backed values.

## WorkItem views (`app/routes/work_item.py`)

- GET (new/edit): pass `system_enum` and `work_item` to templates.
- POST/PATCH: parse `system` from forms and persist on the model.

## Testing patterns

- Use class-scoped fixtures to provide `fenrir`, `driver`, `env`.
- Prefer page-object fixtures rather than direct instantiation inside tests.

## Database patterns

- Convert service configs when moving across layers (e.g., ReportingServiceConfig → DatabaseServiceConfig).
- Avoid SQLite-only args with Postgres/MSSQL.

## HTMX patterns and recipes

Use these patterns to build interactive features with server-side rendering while keeping behavior consistent across the app.

### Core request + target + swap

- Any element can issue requests: `hx-get`, `hx-post`, `hx-put`, `hx-patch`, `hx-delete`.
- Point results at a specific element with `hx-target` (supports extended selectors like `closest tr`).
- Control insertion with `hx-swap` (e.g., `innerHTML` default, `outerHTML`, `beforeend`, `afterbegin`).

Example (replace a row after a server update):

```html
<button
  class="btn btn-sm btn-primary"
  hx-post="/api/work-item/{{ row.id }}/reprocess"
  hx-target="closest tr"
  hx-swap="outerHTML">
  Reprocess
  <span class="htmx-indicator spinner-border spinner-border-sm ms-1" role="status"></span>
  </button>
```

FastAPI handler returns a partial row (Jinja template) to swap in.

### Triggers (debounce, throttle, once, custom)

- `hx-trigger="keyup changed delay:500ms"` for active search.
- `once` to fire a single time; `throttle:1s` to limit frequency.

Example (active search):

```html
<input
  class="form-control"
  name="q"
  hx-get="/pages/search"
  hx-trigger="keyup changed delay:400ms"
  hx-target="#search-results"
  hx-indicator="#search-indicator"
  placeholder="Search...">
<div id="search-indicator" class="htmx-indicator spinner-border spinner-border-sm ms-1"></div>
<div id="search-results"></div>
```

In your route, return a small `search_results.html` fragment for the results container.

### Loading indicators and disabling controls

- Add an element with `htmx-indicator` inside the triggering element or point to a different element via `hx-indicator="#selector"`.
- Temporarily disable controls with `hx-disabled-elt="closest form"` or on self.

```html
<button
  hx-post="/api/items"
  hx-disabled-elt="this">
  Save
  <span class="htmx-indicator spinner-border spinner-border-sm ms-1"></span>
</button>
```

### Targets with extended selectors

- Use `closest tr`, `find .detail`, `next .toast`, etc., to avoid brittle IDs.

```html
<button
  hx-delete="/api/work-item/{{ row.id }}"
  hx-target="closest tr"
  hx-swap="outerHTML swap:150ms">
  Delete
</button>
```

### Swap strategies and transitions

- Choose swap strategy per interaction: `outerHTML` to replace a component, `beforeend` to append rows, `none` when you only want to trigger events.
- Optional: enable View Transitions via `hx-swap="outerHTML transition:true"` (browser support varies).

### Polling and load-polling

Use for statuses/progress. Prefer load-polling when the server decides the next interval or termination.

```html
<!-- polls every 2s -->
<div id="status" hx-get="/api/work-item/{{ id }}/status" hx-trigger="every 2s"></div>

<!-- load-polling from server response -->
<div hx-get="/api/work-item/{{ id }}/status" hx-trigger="load delay:1s" hx-swap="outerHTML"></div>
```

Return the same snippet from the server until complete; when done, return a final static block.

### Synchronization (avoid race conditions)

Abort validation calls when a form submits:

```html
<form hx-post="/api/items">
  <input name="title" hx-post="/api/validate/title" hx-trigger="change" hx-sync="closest form:abort">
  <button type="submit">Submit</button>
</form>
```

### Parameters: include/exclude/extra values

- Include other fields: `hx-include="#filters input, #filters select"`.
- Exclude by name: `hx-params="not csrf_token"` or list.
- Add extra values: `hx-vals='{"page": 2, "page_size": 50}'`.

```html
<div id="filters">
  <select name="system"><option value="miner_ocr">Miner OCR</option></select>
</div>
<button hx-get="/pages/work-items" hx-include="#filters *" hx-target="#table-wrapper">Apply</button>
```

### Out-of-band (OOB) swaps for global UI

Update a flash banner or counters alongside any response:

```html
<template>
  <div id="flash" hx-swap-oob="true" class="alert alert-success">Saved!</div>
</template>
```

Place this in the server response; htmx swaps it into `#flash` regardless of the main target.

### Response headers: redirects and events

From FastAPI, you can set headers to drive client behavior without extra JS:

- HX-Redirect or HX-Location: client-side navigation without full reload.
- HX-Trigger / HX-Trigger-After-Swap: fire custom events.

```python
from fastapi import Response

def create_item(...):
    resp = templates.TemplateResponse(...)
    resp.headers["HX-Trigger"] = "items:created"
    return resp
```

On the client:

```html
<script>
  document.body.addEventListener('items:created', () => {
    // e.g., refresh a badge or toast
  });
  // htmx also dispatches htmx:afterSwap, htmx:afterSettle, etc.
</script>
```

### History & navigation

- `hx-push-url="true"` to push the request URL into browser history (ensure the URL returns a full page if loaded directly).
- `hx-boost="true"` on a container to convert links/forms to AJAX swaps (default target is `<body>` unless overridden).

```html
<div id="pageContent" hx-boost="true" hx-target="#pageContent"></div>
```

Recommended config when using partials and history: serve full pages on direct navigation, partials on `HX-Request: true`.

### File uploads

- Use `hx-encoding="multipart/form-data"` on the form.

```html
<form hx-post="/api/files" hx-encoding="multipart/form-data" hx-target="#upload-result">
  <input type="file" name="file" required>
  <button type="submit" class="btn btn-primary">Upload</button>
  <div class="htmx-indicator spinner-border spinner-border-sm ms-1"></div>
  <div id="upload-result"></div>
</form>
```

FastAPI will use `UploadFile`/`File` to receive the file and return a partial.

### Validation

- Built-in HTML5 validation blocks requests for invalid forms.
- For custom rules, handle `htmx:validation:validate` via `hx-on:` or JS; for server-side validation, return partial with errors and use `hx-swap` to refresh the form section.

### Security & headers

- Add CSRF or auth headers from the root element: `<body hx-headers='{"X-CSRF-TOKEN":"..."}'>`.
- Consider `htmx.config.selfRequestsOnly = true` if all requests are same-origin.
- Use `hx-history="false"` on sensitive pages to avoid history snapshots.

### Events you will commonly use

- `htmx:configRequest` to add headers/params programmatically.
- `htmx:beforeSwap` to allow swapping on 422 responses (validation rerender) and to retarget.
- `htmx:afterSwap` to re-initialize tooltips, copy buttons, etc. (pattern already used in `table.html`).

```html
<script>
  document.body.addEventListener('htmx:beforeSwap', (evt) => {
    if (evt.detail.xhr && evt.detail.xhr.status === 422) {
      evt.detail.shouldSwap = true;
      evt.detail.isError = false;
    }
  });
  document.body.addEventListener('htmx:afterSwap', () => {
    // re-init Bootstrap tooltips, copy buttons, etc.
  });
</script>
```

### FastAPI response tips

- Prefer returning `TemplateResponse` fragments for HTMX requests and full pages for normal navigation.
- Detect HTMX via the `HX-Request` header: `if request.headers.get("HX-Request") == "true":`.
- When returning fragments for table updates, return valid, self-contained HTML for the chosen swap target (e.g., a single `<tr>` when swapping a row).
