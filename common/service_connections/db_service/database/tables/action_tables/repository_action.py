"""
Docstring for common.service_connections.db_service.database.tables.action_tables.repository_action

A repository action represents operations that can be performed on a code repository.

Enumeration of the values we get from repo actions can help the AI agent better
take actions on what to do with code repositories and understand the system under test.


Repository actions are as follows:
- Connect to a code repository.
- Pull down code from a repository.
    - Support for multiple repository hosting services (e.g., GitHub, GitLab, Bitbucket).
    - Handle authentication and access tokens securely.
    - Support for different repository types (public, private).
- Analyze the tech stack of the repository.
    - Runtime Language Detection
    - Framework Detection
        - Dependency Detection
        - Build Tool Detection
        - Containerization Detection
        - Testing Framework Detection
        - DevOps Tooling Detection
- Perform static code analysis.
    - Code Quality Checks
    - Code Style Enforcement
    - Security Vulnerability Scanning
    - Dependency Analysis
- Generate reports based on the analysis.
    - Summary of Findings
    - Detailed Issue Listings
    - Score based on Code Quality and Security

Attributes:
    repository_action_id: The unique identifier for the repository action.
    action_type: The type of repository action (e.g., connect, pull, analyze, scan).
    repository_url: The URL of the code repository.
    repository_name: The name of the code repository.

    Runtime_language: The primary programming language used in the repository.
    Runtime_version: The version of the runtime environment (e.g., Python 3.8, 
    Node.js 14).

    frameworks: The main frameworks used in the repository (e.g., Django, React).
    dependencies: A list of key dependencies and libraries used in the repository.

    build_tools: The build tools utilized in the repository (e.g., Maven, Webpack
    containerization: Information about containerization (e.g., Docker, Kubernetes).
    dockerfile_present: A boolean indicating if a Dockerfile is present in the
    repository.
    dockerfile_contents: The contents of the Dockerfile if present.
    docker_compose_present: A boolean indicating if a Docker Compose file is present.
    docker_compose_contents: The contents of the Docker Compose file if present.
    
    test_directory_present: The directory where test files are located.
    test_frameworks: The testing frameworks used in the repository (e.g., pytest, Jest).
    devops_tools: The DevOps tools integrated with the repository (e.g., Jenkins,
    GitHub Actions)., CircleCI).
    
    auth_token: The authentication token for accessing the repository.
    analysis_results: A JSON blob containing the results of the code analysis.
    created_at: The timestamp when the repository action was created.
    updated_at: The timestamp when the repository action was last updated.
"""
