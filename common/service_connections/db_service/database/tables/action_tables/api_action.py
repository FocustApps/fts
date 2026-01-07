"""
Docstring for common.service_connections.db_service.database.tables.action_tables.api_action

An API action is essentially a request made to an API endpoint.

A sequence of API actions can be used to simulate complex workflows or interactions 
with an API.

Storing the details of each API action allows for easy reuse and modification of test 
cases that involve API interactions.

Attributes:
    api_action_id: The unique identifier for the API action.
    base_url: The base URL of the API. (can be inherited from Environment)
    endpoint: The URL endpoint of the API.
    http_method: The HTTP method used for the API action (e.g., GET, POST, PUT, DELETE).
    headers: The headers included in the API request.
    query_params: The query parameters for the API request.
    path_params: The path parameters for the API request.
    payload: The payload or body of the API request.
    response_status: The expected response status code from the API.
    response_body: The expected response body from the API.
    created_at: The timestamp when the API action was created.
    updated_at: The timestamp when the API action was last updated.
"""
