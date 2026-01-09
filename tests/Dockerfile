FROM python:3.12-slim

# Install system dependencies for MSSQL (if needed) and PostgreSQL client
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    gnupg \
    unixodbc \
    postgresql-client \
    && apt-get -y clean

# Install uv package manager
RUN pip install uv

# Set working directory to project root
WORKDIR /fenrir

# Copy dependency file and install packages
COPY ./pyproject.toml pyproject.toml
RUN uv pip install --system -r pyproject.toml

# Copy entire project (tests need access to common/, app/, etc.)
COPY . .

# Set PYTHONPATH to ensure imports work correctly
ENV PYTHONPATH=/fenrir

# Default command runs all tests
CMD ["pytest", "tests/", "-v", "--tb=short"]