
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first to improve build caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source and required data
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

# FastAPI and MCP server ports
EXPOSE 8080 8001

# Default: start FastAPI
CMD ["uvicorn", "chatbot.main:app", "--host", "0.0.0.0", "--port", "8080"]
