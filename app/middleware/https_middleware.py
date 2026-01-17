"""
HTTPS enforcement middleware.

Redirects HTTP requests to HTTPS in production when enabled via configuration.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce HTTPS connections.

    Redirects HTTP requests to HTTPS when enabled.
    Skips enforcement for localhost/127.0.0.1 for local development.
    """

    def __init__(self, app, enforce: bool = False):
        super().__init__(app)
        self.enforce = enforce

    async def dispatch(self, request: Request, call_next):
        if self.enforce:
            # Allow localhost without HTTPS
            host = request.headers.get("host", "").split(":")[0]
            if host not in ("localhost", "127.0.0.1"):
                # Check if request is already HTTPS
                if request.url.scheme != "https":
                    # Build HTTPS URL
                    https_url = request.url.replace(scheme="https")
                    return RedirectResponse(url=str(https_url), status_code=301)

        response = await call_next(request)
        return response
