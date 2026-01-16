#!/usr/bin/env python3
"""
Generate OpenAPI schema from running FastAPI application.

This script fetches the OpenAPI schema from the FastAPI app and outputs it to stdout.
Use it to generate the frontend/openapi.json file for TypeScript type generation.

Usage:
    python app/scripts/generate_openapi_schema.py > frontend/openapi.json

Requirements:
    - FastAPI app must be running on http://localhost:8080
    - CORS must allow the request origin
"""
import sys
import requests
from typing import Dict, Any


def fetch_openapi_schema(base_url: str = "http://localhost:8080") -> Dict[str, Any]:
    """
    Fetch OpenAPI schema from running FastAPI application.

    Args:
        base_url: Base URL of the FastAPI application

    Returns:
        OpenAPI schema as dict

    Raises:
        requests.RequestException: If the request fails
        ValueError: If the response is not valid JSON
    """
    url = f"{base_url}/openapi.json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {base_url}", file=sys.stderr)
        print("Make sure the FastAPI application is running.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP {e.response.status_code} from {url}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Error: Request to {url} timed out", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: Invalid JSON response: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    import json

    schema = fetch_openapi_schema()

    # Output formatted JSON to stdout
    print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
