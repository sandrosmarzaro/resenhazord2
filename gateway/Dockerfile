FROM oven/bun:1.3.9-alpine AS builder

RUN apk add --no-cache git ca-certificates

WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

FROM oven/bun:1.3.9-alpine

RUN apk add --no-cache ca-certificates

RUN addgroup -S nonroot && adduser -S -G nonroot nonroot

WORKDIR /app
COPY --chown=nonroot:nonroot --from=builder /app/node_modules ./node_modules
COPY --chown=nonroot:nonroot . .

USER nonroot

CMD ["bun", "run", "start"]
