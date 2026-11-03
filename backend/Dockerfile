FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV PATH="/opt/venv/bin:$PATH"

# Install supervisor
RUN apt-get update && apt-get install -y --no-install-recommends supervisor && rm -rf /var/lib/apt/lists/*

# Copy project specification files
COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Install dependencies using uv sync
RUN uv sync --frozen --no-install-project --no-dev || uv sync --no-install-project --no-dev

# Copy application source code, supervisor config, and entrypoint
COPY src/ ./src/
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose backend REST API port
EXPOSE 8000

# Entrypoint runs migrations and supervisord (Backend + Worker + Scheduler)
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
