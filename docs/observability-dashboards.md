# Observability — dashboards & alerts (Phase 5)

Ready-to-use PromQL and alert specs for Grafana Cloud, built on the signals shipped
in phases 0–4 ([PRD](prd-observability-otel-lgtm.md)). Metric names below were captured
from the live Alloy pipeline, not guessed.

## Import the dashboard

An importable dashboard covering every signal below lives at
[`observability/grafana/resenhazord2-dashboard.json`](../observability/grafana/resenhazord2-dashboard.json)
(RED by outcome, p50/p95 latency, retries/DLQ, host memory/CPU/swap/load).

Grafana → Dashboards → New → **Import** → upload the JSON → pick your Grafana Cloud
Prometheus data source when prompted. It's a starter — refine panels in the UI. If a
panel shows **"No data"**, confirm the metric name in Grafana's metric browser: OTLP→
Prometheus naming can vary slightly by Grafana version, and the queries here use the
names captured from Alloy (see the table below). The alerts stay manual (below).

## Metric reference

| Signal | Metric | Labels of interest |
|---|---|---|
| Command rate/errors | `traces_span_metrics_calls_total` | `command_outcome` (success/bot_error/external_error), `span_name` (`command.handle`), `service_name` |
| Command latency | `traces_span_metrics_duration_milliseconds_bucket` / `_sum` / `_count` | same |
| Retries scheduled | `command_retries_total` | `service_name` |
| Dead-lettered | `command_dlq_total` | `service_name` |
| Host memory | `node_memory_MemAvailable_bytes`, `node_memory_MemTotal_bytes` | — |
| Host swap | `node_memory_SwapFree_bytes`, `node_memory_SwapTotal_bytes` | — |
| Host CPU | `node_cpu_seconds_total` | `mode` |
| Host load | `node_load1` | — |

`traces_span_metrics_*` come from Alloy's spanmetrics connector on the core (derived from
the `command.handle` span); `command_*` are the manual OTel counters; `node_*` come from
Alloy's node_exporter. All carry `service_name="bot"`.

## Panels

### RED — command throughput (by outcome)
```promql
sum by (command_outcome) (rate(traces_span_metrics_calls_total{span_name="command.handle"}[5m]))
```

### RED — error ratio
```promql
sum(rate(traces_span_metrics_calls_total{span_name="command.handle", command_outcome!="success"}[5m]))
/
sum(rate(traces_span_metrics_calls_total{span_name="command.handle"}[5m]))
```

### RED — p95 latency (ms)
```promql
histogram_quantile(0.95,
  sum by (le) (rate(traces_span_metrics_duration_milliseconds_bucket{span_name="command.handle"}[5m])))
```

### Retries & dead-letters
```promql
sum(rate(command_retries_total[5m]))    # retries/s
sum(rate(command_dlq_total[5m]))         # DLQ/s
```

### Host memory available (%) — the OOM story
```promql
100 * node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
```

### Host swap used (%)
```promql
100 * (1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes)
```

### Host CPU busy (%)
```promql
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

## Alert rules

Grafana → Alerting → Alert rules → New. Sentry keeps error alerting; these cover the
infra/flow gaps that led to the freezes.

| Alert | Expression | For | Why |
|---|---|---|---|
| Core memory low | `100 * node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 10` | 5m | The documented OOM/host-freeze risk on the 1 GB nodes |
| Swap thrashing | `100 * (1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes) > 80` | 10m | Sustained swap pressure precedes the freeze |
| Command error surge | `sum(rate(traces_span_metrics_calls_total{command_outcome!="success"}[5m])) / sum(rate(traces_span_metrics_calls_total[5m])) > 0.3` | 10m | A broad upstream/logic failure, not one bad URL |
| Dead-letters rising | `sum(increase(command_dlq_total[15m])) > 5` | 0m | Commands giving up after the retry ladder |

## Not covered yet — RabbitMQ queue depth

There is no queue-depth metric: nothing scrapes RabbitMQ. `command_retries_total` /
`command_dlq_total` are the current proxy for broker trouble. True depth needs the
RabbitMQ Prometheus plugin (or an exporter) on the **edge**, scraped by an Alloy there —
a follow-up, out of the current hybrid scope (the edge has no collector).

## Cross-linking logs ↔ traces

Logs (Loki) carry `trace_id`/`span_id` from Phase 3, and traces live in Tempo. In the
Loki data source, a derived field on `trace_id` → Tempo turns every log line into a jump
to its trace (and Tempo's "Logs for this span" jumps back).
