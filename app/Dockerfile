ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS python-base

ARG ENV DEBIAN_FRONTEND=noninteractive

# install Microsoft SQL Server requirements.
ENV ACCEPT_EULA=Y
RUN apt-get update -y && apt-get install -y --no-install-recommends curl gcc g++ gnupg unixodbc


RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
  && curl https://packages.microsoft.com/config/debian/12/prod.list | tee /etc/apt/sources.list.d/mssql-release.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends --allow-unauthenticated msodbcsql18 \
  && apt-get install -y libgssapi-krb5-2 \
  && apt-get install -y unixodbc-dev

# Install uv as the package manager
RUN pip install uv

# Clean up for smaller image
RUN apt-get -y clean

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /fenrir

# Install the required packages using uv
COPY ./pyproject.toml pyproject.toml
RUN uv pip install --system -r pyproject.toml

COPY . .

RUN chmod +x ./app/entrypoint.sh
ENTRYPOINT ["sh", "./app/entrypoint.sh"]