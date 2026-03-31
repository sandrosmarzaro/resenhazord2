FROM python:3.13-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    libsodium-dev \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    libpng-dev \
    libwebp-dev \
    openjpeg-dev \
    tiff-dev

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.13-alpine AS production

COPY --from=oven/bun:1.3.9-alpine /usr/local/bin/bun /usr/local/bin/bun

RUN apk add --no-cache \
    ffmpeg \
    opus \
    curl \
    libjpeg-turbo \
    libwebp \
    freetype \
    libpng \
    openjpeg \
    tiff \
    libffi \
    libsodium

RUN addgroup -S nonroot && adduser -S -G nonroot nonroot

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

USER nonroot

WORKDIR /app

EXPOSE 8000
CMD ["uvicorn", "bot.main:app", "--host", "0.0.0.0", "--port", "8000"]
