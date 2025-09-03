# Use the official Postgres image as the base
FROM postgres:latest

# Copy any initialization scripts into the Docker image
# Place your .sql or .sh scripts in the same directory as this Dockerfile or adjust the path as needed
COPY common/service_connections/db_service/tables /docker-entrypoint-initdb.d/
# You can copy multiple scripts if needed:
# COPY ./init1.sql ./init2.sql /docker-entrypoint-initdb.d/
ENV POSTGRES_DB=fenrir
# No need to specify CMD or ENTRYPOINT; the base image will run postgres and execute scripts in /docker-entrypoint-initdb.d/
