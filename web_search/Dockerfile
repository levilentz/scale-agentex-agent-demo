# syntax=docker/dockerfile:1.3
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.4 /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    htop \
    vim \
    curl \
    tar \
    python3-dev \
    postgresql-client \
    build-essential \
    libpq-dev \
    gcc \
    cmake \
    netcat-openbsd \
    nodejs \
    npm \ 
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/**

RUN uv pip --native-tls --allow-insecure-host pypi.org --allow-insecure-host files.pythonhosted.org install --system --upgrade pip setuptools wheel

ENV UV_HTTP_TIMEOUT=1000

# Copy just the pyproject.toml file to optimize caching
COPY web_search /app/web_search

WORKDIR /app/web_search

# Install the required Python packages using uv
RUN uv pip --native-tls --allow-insecure-host pypi.org --allow-insecure-host files.pythonhosted.org install --system .

# Copy the project code
# COPY web_search/project /app/web_search/project

# Set environment variables
ENV PYTHONPATH=/app

# Run the agent using uvicorn
CMD ["uvicorn", "project.acp:acp", "--host", "0.0.0.0", "--port", "8000"] 