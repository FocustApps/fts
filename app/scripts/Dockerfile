# Dockerfile for seeding scripts
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    build-essential \
    libpq-dev \
    ca-certificates && \
    # Add Microsoft repository for ODBC driver
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update -y && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Set working directory
WORKDIR /fenrir

# Copy dependency files
COPY ./pyproject.toml pyproject.toml

# Install Python dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/fenrir:/fenrir/services

# Default command (will be overridden in docker-compose.yml)
CMD ["python", "app/scripts/seed_local_environment.py"]
