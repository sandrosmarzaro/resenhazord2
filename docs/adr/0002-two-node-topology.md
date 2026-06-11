---
status: accepted
date: 2026-06-05
---

# 0002 — Two-node deployment, broker on the edge node

A single 1 GB / 1 OCPU Oracle micro cannot comfortably hold the gateway, the bot, and
RabbitMQ. We split the two on-VPS processes across **two** Oracle Always-Free micros —
an **edge node** (gateway + RabbitMQ) and a **core node** (bot); Mongo (Atlas) and
Redis (Upstash) stay external. The broker is co-located with the gateway because it
must survive the frequently-redeployed bot's restarts, so it lives with the stable,
long-lived Baileys session. If the edge node dies, the gateway dies with it and no
inbound messages exist to lose — the broker's buffering job is for when the *bot* is
down, which it still serves.

## Considered options

- **Broker on the core node (with the bot).** Rejected — every bot redeploy would
  take the buffer down with it, the opposite of what a durable broker is for.
- **Single ARM Ampere A1 VM (up to 24 GB free).** Rejected — ARM free-tier capacity is
  frequently unavailable, and a single fat box undercuts the distributed-systems
  experience this project is meant to demonstrate.

## Consequences

- Two host-local compose files (`compose.edge.yml`, `compose.core.yml`) replace the
  single `docker-compose.yml`; the cross-service `depends_on` disappears as broker
  durability replaces boot ordering.
- RabbitMQ binds the VCN private IP; a security list opens 5672 only from the core
  node. No public broker port.
- A network partition between bot and broker slightly raises redelivery odds —
  covered by [0001](./0001-at-least-once-delivery.md)'s guard rule.
