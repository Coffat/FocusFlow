FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy project specification files
COPY pyproject.toml README.md ./

# Install dependencies using uv sync
RUN uv sync --frozen --no-install-project --no-dev || uv sync --no-install-project --no-dev

# Copy application source code
COPY src/ ./src/

# Default command to start FastAPI
CMD ["uv", "run", "uvicorn", "src.presentation.main:app", "--host", "0.0.0.0", "--port", "8000"]
