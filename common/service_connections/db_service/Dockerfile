# Use the official Postgres image as the base
FROM postgres:latest

# Set environment variables
ENV POSTGRES_DB=fenrir

# No initialization scripts needed - schema is managed by Alembic migrations
# Database will be created empty and migrations will be applied by the application on startup
