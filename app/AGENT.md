# App layer guide for contributors and AI agents

This guide documents conventions for the `/app` layer (FastAPI + HTMX + Jinja) and includes a tiny worked example.

## Conventions

- Dual routers per feature:
  - API: `router_name_api_router = APIRouter(prefix="/api/name", tags=["api"])`
  - Views: `router_name_views_router = APIRouter(prefix="/name", tags=["views"], include_in_schema=False)`
- Templates: use `Jinja2Templates`; pass dataclass payloads via `.model_dump()` (or plain primitives) to templates.
- HTMX: render server-side partials; re-init any client JS after `htmx:afterSwap`.
- Table partial (`app/templates/table.html`): fixed layout, ellipsis truncation, tooltip, copy icon; JS re-binds on resize and swaps.
- Enum dropdowns: build options in routes as `[(e.value, label)]`; templates handle enum or string `selected`.
- WorkItem routes: new/edit GET pass `system_enum` + `email_item`; POST/PATCH read and persist `system`.

## Worked example: Add a simple feature (Teams) with dual routers

1. Create routes file `app/routes/teams.py` with two routers

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

teams_api_router = APIRouter(prefix="/api/teams", tags=["api"])
teams_views_router = APIRouter(prefix="/teams", tags=["views"], include_in_schema=False)

templates = Jinja2Templates(directory="app/templates")

# Views
@teams_views_router.get("/", response_class=HTMLResponse)
def view_teams(request: Request):
    teams = [
        {"name": "QA", "owner": "Alice"},
        {"name": "Dev", "owner": "Bob"},
    ]
    headers = ["name", "owner"]
    return templates.TemplateResponse(
        "teams/index.html",
        {
            "request": request,
            "title": "Teams",
            "headers": headers,
            "table_rows": teams,
            "view_url": "view_teams",
            "add_url": "new_team",
            "view_record_url": "view_team",
            "delete_url": "delete_team",
        },
    )

# API (example) - extend as needed
@teams_api_router.get("/")
def list_teams():
    return [{"name": "QA", "owner": "Alice"}]
```

1. Create template `app/templates/teams/index.html` as a thin wrapper around the table partial

```html
{% extends "index.html" %}
{% block content %}
  {% include "table.html" %}
{% endblock %}
```

1. Register routers in `app/routes/__init__.py` (or wherever you aggregate)

```python
# ...existing imports...
from .teams import teams_api_router, teams_views_router

# ...existing router registrations...
app.include_router(teams_api_router)
app.include_router(teams_views_router)
```

1. JS behaviors after HTMX swaps

If your view uses the table partial or interactive widgets, ensure they re-init after HTMX swaps:

```javascript
// Example hook in a template or a global bundle
document.body.addEventListener('htmx:afterSwap', (evt) => {
  // re-init tooltips/copy buttons/etc.
});
```

That’s it—keep features consistent with these patterns to fit the system’s SSR + HTMX flow.
