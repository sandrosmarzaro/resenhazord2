# PRD — Observability with OpenTelemetry + Grafana Cloud (LGTM)

Status: **accepted**, phase 0 in progress. Scope closed 2026-09-15.

## Context

The two-node bot ([ADR 0002](adr/0002-two-node-topology.md)) has error tracking
(Sentry, both nodes) but **no metrics or traces**, and logs live only in the
`json-file` docker driver + Sentry breadcrumbs. The edge node has a documented
history of OOM/host-freeze on its ~1 GB VM (gateway 384m + RabbitMQ 400m). We
want distributed traces of the command flow, RED + host metrics, and centralized
logs — without adding memory pressure to the starved nodes.

## Goal

Ship metrics, logs, and traces from both nodes to **Grafana Cloud** (managed
LGTM: Loki, Grafana, Tempo, Mimir/Prometheus) over **OTLP**, correlating the
edge→core command flow into single traces, while Sentry stays the error/alert
tool.

## Non-goals

- Replacing Sentry (it keeps errors + alerting).
- Self-hosting the LGTM stack (memory wall on the nodes; revisit only if Grafana
  Cloud free tier proves insufficient — fallback target is the **core** node, never edge).
- An OTel Collector in the app data path (apps export OTLP direct).

## Decisions

| Dimension | Decision | Why |
|---|---|---|
| Backend | Grafana Cloud free tier, region `prod-sa-east-1` | Zero memory cost on 1 GB nodes; free quotas (10k series, 50 GB logs/traces, 14-day retention) fit this workload |
| Export | OTLP/HTTP direct from each app | No collector to run/maintain on the edge |
| Sentry | Coexists — errors/alerts stay in Sentry; metrics/logs/traces in LGTM | Each tool at its strength; no risky migration |
| Cross-node traces | W3C `traceparent` injected into the RabbitMQ message envelope | The flow crosses the broker, not HTTP; HTTP auto-instrumentation alone can't link the nodes |
| Metrics | App (RED + queue depth + retry/DLQ) **and** host (RAM/CPU/swap) | Directly targets the OOM/freeze history |
| Rollout | Core/Python first, gateway/Bun after a spike | Python OTel SDK is mature; Bun OTel is immature (risk gate) |

## Architecture

```
edge (VM-A)  gateway (Bun) ──publish──▶ RabbitMQ ──▶ bot (Python)  core (VM-B)
                  │   envelope carries traceparent ──────────▶ │
                  └── OTLP/HTTP ─┐                ┌── OTLP/HTTP ─┘
                                 ▼                ▼
                     Grafana Cloud  ·  Tempo / Prometheus / Loki / Grafana
   Sentry ◀── errors (unchanged, in parallel)
```

## Cross-node trace propagation

The command envelope already carries a stable `id` (`correlation_id`) across the
retry/DLQ hops. Add a `traceparent` (and optional `tracestate`) field to the
envelope on publish (edge gateway and any core-side republish), and extract it on
consume in `command_consumer` to continue the trace. This follows the OTel
messaging semantic conventions (context in message metadata) and yields one
continuous trace edge↔core per command.

## Phased plan (PRs ≤ 5 files, per repo convention)

- **Phase 0 — Foundation (core):** OTel SDK + OTLP/HTTP exporter deps; config in
  `Settings`; `bot/infrastructure/otel.py` (tracer/meter/logger providers, resource
  `service.name=bot`, `service.namespace=resenhazord2`, node attr, guarded on
  endpoint like Sentry is on DSN); init in `main.py`. **Gate:** one span, one
  metric, one log visible in Grafana Cloud. Verify OTel↔Sentry coexistence (no
  duplicate/broken spans).
- **Phase 1 — Traces (core):** auto-instrument FastAPI, httpx, aio-pika; inject/
  extract `traceparent` in the broker publish/consume path.
- **Phase 2 — Metrics (core):** RED per command, queue depth, retry/DLQ counters;
  host metrics via a lightweight agent (Grafana Alloy / node-exporter) on the core
  host (`compose.core.yml`).
- **Phase 3 — Logs (core):** structlog → Loki via the OTel logging handler; Sentry
  untouched.
- **Phase 4 — Gateway (edge):** Bun/OTel spike as a gate; if it passes, instrument
  the gateway (publish-side `traceparent`, metrics, logs) with a minimal memory
  footprint; decide edge host-metrics separately.
- **Phase 5 — Dashboards + alerts:** Grafana dashboards (RED, queue, host
  memory/OOM) and infra alerts.

## Risks / open spikes

1. **OTel ↔ Sentry (Python):** possible span/context duplication — validate in Phase 0.
2. **Bun + OTel maturity:** gated by the Phase 4 spike; plan B is gateway via logs/Sentry only.
3. **Host metrics need an agent** (Alloy/node-exporter) — contradicts "no collector";
   it is lightweight but the edge is memory-sensitive, so edge host-metrics is deferred to Phase 4.
4. **Grafana Cloud free quotas** — confirm headroom in Phase 0 (trial converts to Always Free).

## Config & secrets

Per node, in `.env` (git-ignored; slots documented in `.env.example`):

- `OTEL_EXPORTER_OTLP_ENDPOINT` — `https://otlp-gateway-prod-sa-east-1.grafana.net/otlp`
- `OTEL_EXPORTER_OTLP_HEADERS` — `Authorization=Basic <base64(instanceID:token)>`

The token is a Grafana Cloud access-policy token scoped write-only
(`otel-data-write` / metrics+logs+traces write). It never enters source or the
repo; the OTLP exporter reads it from the environment.

## References

- [ADR 0002 — two-node topology](adr/0002-two-node-topology.md),
  [ADR 0006 — two-node CI/CD deploy](adr/0006-two-node-cicd-deploy.md)
- OTel: SDK, OTLP/HTTP exporter, messaging semantic conventions (trace context in message metadata)
- Grafana Cloud: OTLP gateway endpoint + access-policy tokens
