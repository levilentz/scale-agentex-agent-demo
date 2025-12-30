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

RUN uv pip install --system --upgrade pip setuptools wheel

ENV UV_HTTP_TIMEOUT=1000

# Copy just the pyproject.toml file to optimize caching
COPY example_openai_agent/pyproject.toml /app/example_openai_agent/pyproject.toml

WORKDIR /app/example_openai_agent

# Allow PyO3 builds against Python 3.14 using the stable ABI
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Install the required Python packages using uv (as root for system site-packages), then drop privileges
USER root
RUN uv pip install --system .
# Copy the project code
COPY example_openai_agent/project /app/example_openai_agent/project

# Set environment variables
ENV PYTHONPATH=/app

# Run the agent using uvicorn
CMD ["uvicorn", "project.acp:acp", "--host", "0.0.0.0", "--port", "8000"] 
