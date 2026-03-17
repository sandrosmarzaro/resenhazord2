FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    chromium \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system nonroot && adduser --system --ingroup nonroot nonroot

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

USER nonroot

WORKDIR /app

EXPOSE 8000
CMD ["uvicorn", "bot.main:app", "--host", "0.0.0.0", "--port", "8000"]
