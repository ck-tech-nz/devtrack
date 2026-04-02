FROM python:3.14-slim

RUN apt-get update && apt-get install -y git curl postgresql-client && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://opencode.ai/install | bash
ENV PATH="/root/.opencode/bin:/root/.local/bin:${PATH}"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY packages/ /packages/
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ .
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
