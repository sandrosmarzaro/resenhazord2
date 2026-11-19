# Observability — dashboards & alerts (Phase 5)

Ready-to-use PromQL and alert specs for Grafana Cloud, built on the signals shipped
in phases 0–4 ([PRD](prd-observability-otel-lgtm.md)). Metric names below were captured
from the live Alloy pipeline, not guessed.

## Import the dashboard

An importable dashboard covering every signal below lives at
[`observability/grafana/resenhazord2-dashboard.json`](../observability/grafana/resenhazord2-dashboard.json)
(RED by outcome, p50/p95 latency, retries/DLQ, host memory/CPU/swap/load, agent
natural-language → command mapping).

Grafana → Dashboards → New → **Import** → upload the JSON → pick your Grafana Cloud
Prometheus data source when prompted. It's a starter — refine panels in the UI. If a
panel shows **"No data"**, confirm the metric name in Grafana's metric browser: OTLP→
Prometheus naming can vary slightly by Grafana version, and the queries here use the
names captured from Alloy (see the table below). The alerts are versioned too (below).

## Metric reference

| Signal | Metric | Labels of interest |
|---|---|---|
| Command rate/errors | `traces_span_metrics_calls_total` | `command_outcome` (success/bot_error/external_error/unexpected_error), `span_name` (`command.handle`), `service_name` |
| Command latency | `traces_span_metrics_duration_milliseconds_bucket` / `_sum` / `_count` | same |
| Command run (every platform) | `traces_span_metrics_calls_total` / `_duration_milliseconds_bucket` with `span_name="command.run"` | `command_name`, `platform` (whatsapp/discord/telegram), `chat_type` (group/private), `command_outcome`, `status_code` (`STATUS_CODE_ERROR` for external and unexpected failures) |
| Span self time | `span_self_time_milliseconds_bucket` / `_sum` / `_count` | `span_name`, `work_kind` (io/cpu/fire_and_forget) |
| Upstream calls | `traces_span_metrics_calls_total` / `_duration_milliseconds_bucket` with `span_kind="SPAN_KIND_CLIENT"` | `server_address` (the host, set by the httpx request hook), `http_status_code`, `status_code` |
| Caught upstream failures | `upstream_failures_total` | `upstream` (the name each `upstream_failed` log passes, e.g. `espn`, `google-translate`) |
| Deliveries in flight | `command_in_flight` | none; prefetch caps it at 4 |
| `,dl` lane wait | `command_lane_wait_milliseconds_bucket` | none |
| Event loop lag | `event_loop_lag_milliseconds_bucket` | none; one sample a second |
| Bot process | `process_memory_rss_bytes`, `process_cpu_time_seconds_total` | `service_name` |
| Gate refusals | `command_rejections_total` | `reason` (disabled/dev_only/off_here/nsfw_channel), `command_name`, `command_scope` |
| Minors filter drops | `compliance_minors_dropped_total` | `source` (redgifs/rule34/hentai) |
| Retries scheduled | `command_retries_total` | `service_name` |
| Dead-lettered | `command_dlq_total` | `service_name` |
| Agent NL→command | `agent_mappings_total` | `agent_outcome` (command/direct/confirm/confirmed/denied/clarify/suggest/menu_hint/unresolvable/unavailable/over_budget), `agent_provider` (github/mistral/groq; empty when unavailable), `agent_prompt_version` (LangSmith commit hash; empty for the in-code prompt) |
| Agent retrieval (live) | `agent_retrievals_total` | `agent_outcome` (command/confirmed), `agent_retrieval_hit` (true/false) |
| Agent retrieval (eval) | `agent_eval_recall` | `k`; `job="resenhazord2/prompt-eval"`, pushed by the prompt-eval workflow |
| Agent LLM tokens | `agent_tokens_total` | none; the provider-reported `total_tokens` of each LLM call |
| Agent token budget | `agent_budget_rejections_total` | `agent_budget_scope` (user/group), `agent_budget_enforced` (true/false; false is a dry run) |
| Host memory | `node_memory_MemAvailable_bytes`, `node_memory_MemTotal_bytes` | `instance` (core/edge) |
| Host swap | `node_memory_SwapFree_bytes`, `node_memory_SwapTotal_bytes` | `instance` (core/edge) |
| Host CPU | `node_cpu_seconds_total` | `mode`, `instance` (core/edge) |
| Host load | `node_load1` | `instance` (core/edge) |

`traces_span_metrics_*` come from Alloy's spanmetrics connector on the core. `command.handle`
is the broker delivery, so it exists only for WhatsApp and also times the queue hops and the
reply publish. `command.run` wraps `Command.run`, the one call Discord, Telegram and WhatsApp
share, so per-command and per-platform numbers come from it. The histogram buckets run from
100ms to 120s, since `,dl` and the media commands pass the old 15s cap; `command_*` and `agent_mappings_total` are the manual OTel
counters (the agent also stamps `agent.outcome`/`agent.provider`/`agent.prompt.version` on
the enclosing `command.handle` span for trace-level correlation); all of these carry
`service_name="bot"`. `node_*` carry `job="integrations/unix"` and `instance="core"`
(Alloy's built-in node_exporter) or `instance="edge"` (the edge node-exporter, see
[Edge host metrics](#edge-host-metrics)), so every host panel and alert covers both nodes.

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

### Latency percentiles by command (ms)
At a few dozen commands a day a 5m rate is mostly empty, so the table panel takes the
percentiles over the dashboard range. Swap the quantile for p50/75/90/95/99.
```promql
histogram_quantile(0.95,
  sum by (le, command_name) (increase(traces_span_metrics_duration_milliseconds_bucket{span_name="command.run"}[$__range])))
sum by (platform, chat_type) (increase(traces_span_metrics_calls_total{span_name="command.run"}[1h]))
```

### Self time vs total
A span's total (spanmetrics) includes every call it awaited, so adding a parent's latency to
its child's counts the same wait twice. `SelfTimeProcessor`
([`bot/infrastructure/self_time.py`](../bot/infrastructure/self_time.py)) records
`span.self_time`: the duration minus the **union** of the awaited children's intervals.
Concurrent children (task groups, `gather`) overlap, so two 500ms fetches in parallel take
500ms off the parent, not 1s. The span with the large self time is where the wait is.

`work.kind` splits it by the kind of work:

- `io` is the default, any awaited span. A parent's own `io` self time is the uninstrumented
  part: Mongo and Redis calls (no client spans yet) plus whatever it runs on the event loop.
- `cpu` comes from `Work.cpu`, which runs a blocking function on a worker thread
  ([`bot/infrastructure/work.py`](../bot/infrastructure/work.py)).
- `fire_and_forget` comes from `Work.detached`, for unawaited work such as the birthday
  scheduler. It starts its own trace, linked to whatever spawned it, so it never lands on a
  request's latency or self time.

```promql
sum by (span_name) (increase(traces_span_metrics_duration_milliseconds_sum[$__range]))   # total
sum by (span_name) (increase(span_self_time_milliseconds_sum[$__range]))                  # self
sum by (work_kind) (increase(span_self_time_milliseconds_sum[1h]))
```

### Integrations
Two views of each third party. The httpx spans give the transport side per host: calls,
error ratio and latency. `upstream_failures_total` counts the failures a command caught
and logged as `upstream_failed`, including the ones a fallback answered, so a dead primary
behind a working fallback still shows up. A structlog processor in
[`bot/infrastructure/logging.py`](../bot/infrastructure/logging.py) does the counting, so
the call sites stay as they are.
```promql
sum by (server_address) (increase(traces_span_metrics_calls_total{span_kind="SPAN_KIND_CLIENT", status_code="STATUS_CODE_ERROR"}[$__range]))
sum by (upstream) (increase(upstream_failures_total[1h]))
```

### Saturation
The node exporter sees the VM, these see the bot
([`bot/infrastructure/runtime_metrics.py`](../bot/infrastructure/runtime_metrics.py)).
Loop lag is the one that explains a slow command with no slow span: CPU left on the event
loop delays everything else by the same amount. In flight pinned at 4 means the consumer is
saturated and the `commands` queue grows toward its 100 cap.
```promql
histogram_quantile(0.99, sum by (le) (rate(event_loop_lag_milliseconds_bucket[5m])))
sum(command_in_flight)
histogram_quantile(0.95, sum by (le) (rate(command_lane_wait_milliseconds_bucket[1h])))
process_memory_rss_bytes
```

### Flow state, compliance and product
The command flow panel follows a command through its states over the dashboard range:
delivered (WhatsApp broker), refused by the gate, ran, then succeeded, user error or
failed, and finally retried or dead-lettered. The agent panel does the same for the
natural-language state machine, by `agent_outcome`.

For compliance, `command_rejections_total{command_scope="nsfw"}` counts the NSFW commands
refused in a chat that switched them off or in a Discord channel not marked NSFW, and
`compliance_minors_dropped_total` counts what each NSFW feed returned that the minors
denylist (`MinorsFilter`) refused to send.
```promql
sum by (reason, command_scope) (increase(command_rejections_total[$__range]))
sum by (source) (increase(compliance_minors_dropped_total[$__range]))
topk(10, sum by (command_name) (increase(traces_span_metrics_calls_total{span_name="command.run"}[$__range])))
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

### Agent — outcomes (by outcome)
```promql
sum by (agent_outcome) (rate(agent_mappings_total[5m]))
```

### Agent — provider-unavailable ratio (AI health)
```promql
sum(rate(agent_mappings_total{agent_outcome="unavailable"}[5m]))
/
clamp_min(sum(rate(agent_mappings_total[5m])), 0.0001)
```

### Agent — mappings by provider / prompt version
```promql
sum by (agent_provider) (rate(agent_mappings_total[5m]))
sum by (agent_prompt_version) (rate(agent_mappings_total[5m]))   # correlate an outcome shift to a prompt rollout
```

### Agent — retrieval recall@5
```promql
sum(increase(agent_retrievals_total{agent_retrieval_hit="true"}[7d]))
/
clamp_min(sum(increase(agent_retrievals_total[7d])), 1)       # live, labelled by the command that ran
last_over_time(agent_eval_recall{k="5"}[30d])                 # eval dataset, see prompt-management.md
```

### Agent — token budget
```promql
sum(increase(agent_tokens_total[1d]))                                       # tokens per day, all chats
sum(increase(agent_tokens_total[1d])) / sum(increase(agent_mappings_total{agent_provider!=""}[1d]))   # tokens per LLM call
sum by (agent_budget_scope, agent_budget_enforced) (increase(agent_budget_rejections_total[1d]))
```

## Alert rules

Sentry keeps error alerting; these cover the infra/flow gaps that led to the freezes.
They live in [`observability/grafana/alert-rules.json`](../observability/grafana/alert-rules.json)
as Grafana provisioning-API payloads (fixed `uid`s, folder `resenhazord2`), and route
straight to the `resenhazord2-email` contact point via `notification_settings`, so the
root notification policy stays untouched. Applied 2026-10-07.

To re-apply after editing the file, `PUT` each rule (falls back to `POST` on 404) with a
Grafana service-account token (Editor). `X-Disable-Provenance: true` keeps them editable
in the UI:

```bash
jq -c '.[]' observability/grafana/alert-rules.json | while read -r rule; do
  uid=$(jq -r .uid <<<"$rule")
  curl -sf -X PUT "$GRAFANA_URL/api/v1/provisioning/alert-rules/$uid" \
    -H "Authorization: Bearer $GRAFANA_TOKEN" -H 'Content-Type: application/json' \
    -H 'X-Disable-Provenance: true' -d "$rule" \
  || curl -sf -X POST "$GRAFANA_URL/api/v1/provisioning/alert-rules" \
    -H "Authorization: Bearer $GRAFANA_TOKEN" -H 'Content-Type: application/json' \
    -H 'X-Disable-Provenance: true' -d "$rule"
done
```

Every rule but one uses `noDataState: OK`: `command_dlq_total` has no series until the
first dead-letter, and the ratio rules go blank when there is no traffic (~20 commands/day).
The exception is Scrape target down. The core Alloy scrapes the edge and RabbitMQ too, so
when the core dies every series vanishes and the other rules read OK. Its `noDataState:
Alerting` turns that silence into an alert.
And `execErrState: KeepLast`: Grafana Cloud's evaluator sometimes times out reaching its
own Prometheus, and `Error` turned each blip into an email.

| Alert | Expression | For | Why |
|---|---|---|---|
| Node memory low | `100 * node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 10` | 5m | The documented OOM/host-freeze risk on the 1 GB nodes; fires per `instance` (core/edge) |
| Swap thrashing | `100 * (1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes) > 80` | 10m | Sustained swap pressure precedes the freeze |
| Dead-letters rising | `sum(increase(command_dlq_total[15m])) > 5` | 0m | Commands giving up after the retry ladder |
| Commands backlog | `sum(rabbitmq_queue_messages_ready{queue="commands"}) > 80` | 5m | The bot is falling behind / stalled consuming. The `commands` policy caps the queue at 100 and drops the oldest, so the alert has to fire before that |
| Agent provider down | `sum(rate(agent_mappings_total{agent_outcome="unavailable"}[10m])) / clamp_min(sum(rate(agent_mappings_total[10m])), 0.0001) > 0.5` | 10m | Most NL mappings hit no working LLM provider (e.g. GitHub Models retirement) — direct commands still work, but the agent is effectively down |
| Scrape target down | `up < 1`, no data alerts | 5m | Fires per `instance` (core/edge/edge-rabbitmq) when a scrape fails, and with no labels when the core Alloy stops sending anything |
| SLO availability fast burn | 1h and 5m error ratio of `command.run` > 0.72, 3+ runs in the hour | 2m | 14.4× the 95% SLO's burn: the 30-day budget gone in about two days |
| SLO availability slow burn | 6h and 30m error ratio > 0.3, 5+ runs in the 6h | 15m | 6× burn: the budget gone in about five days |
| SLO latency fast burn | 1h and 5m share of non-`,dl` runs over 10s > 0.6, 3+ runs | 2m | 6× the 90%-under-10s SLO's burn |
| SLO latency slow burn | 6h and 30m share over 10s > 0.3, 5+ runs | 15m | 3× burn |
| Upstream failing | `sum by (upstream) (increase(upstream_failures_total[1h])) >= 5` | 0m | One third party keeps failing, even when a fallback hides it from users; fires per `upstream` |
| Event loop lagging | p99 `event_loop_lag_milliseconds` > 500 | 10m | CPU on the loop is holding every command back |

### SLOs and burn rate

Two SLOs over 30 days, both on `command.run`, so every platform counts:

- **Availability, 95%.** A bad run is one whose span has `STATUS_CODE_ERROR`: an external
  or unexpected failure. A `bot_error` (bad argument, group-only command in a DM) is the
  user's mistake and doesn't count.
- **Latency, 90% under 10s**, `,dl` excluded since it downloads whole videos.

Each SLO pages through a pair of multiwindow burn-rate rules, the shape of the
[SRE workbook](https://sre.google/workbook/alerting-on-slos/): the long window says the
budget is burning, the short one says it still is, so a rule clears soon after the
failures stop. The fast pair uses 1h + 5m and the slow pair 6h + 30m. Burn factors are
capped by the budget: a 10% budget can't burn faster than 10×, so latency uses 6× and 3×
where availability uses 14.4× and 6×.

At about 15 commands a day a single failure in a quiet hour is a 100% error ratio, so
each rule also needs a minimum number of runs in its long window. That replaced the old
"Command error surge" rule (error ratio over 30% in 5m), which fired on one isolated
failure and counted `bot_error` as a failure. Backtested on 14 days of `command.handle`
(212 runs, 2 real failures): the burn rules stay quiet and the old rule fired once.

Every ratio divides by `clamp_min(total, 1)`. A window with no runs would otherwise give
`0/0 = NaN`, Grafana's math carries NaN through `&&` past the run-count guard, and a NaN
condition counts as firing. Before the clamp the fast-burn rule emailed after every quiet
hour (six times on 2026-11-11, each with zero runs).

When applying the file, also `DELETE` `rz2-command-error-surge` from Grafana.

## Edge host metrics

The edge has no collector (memory wall, [PRD](prd-observability-otel-lgtm.md)): it runs
only a `node-exporter` container (`compose.edge.yml`, `mem_limit: 32m`, measured at
~9 MiB) that serves `/metrics` on **9100**. The **core** Alloy scrapes it over the VCN
private subnet as `instance="edge"`, exactly like RabbitMQ below. To turn it on:

1. Open **9100 edge → core** on the Oracle security list (like 15692).
2. Set `EDGE_PRIVATE_IP=<edge_private_ip>` in the edge `.env` (node-exporter publishes
   only there; Docker port publishing bypasses the host firewall) and
   `EDGE_NODE_METRICS_ADDR=<edge_private_ip>:9100` in the core `.env`.
3. Redeploy: `docker compose -f compose.edge.yml up -d` (node-exporter) and
   `docker compose -f compose.core.yml up -d` (Alloy scrape).

Empty `EDGE_NODE_METRICS_ADDR` leaves the scrape down with no host impact, and the
memory/swap alerts keep covering the core alone.

## RabbitMQ queue metrics

The edge RabbitMQ runs its bundled `rabbitmq_prometheus` plugin (enabled via
[`observability/rabbitmq/enabled_plugins`](../observability/rabbitmq/enabled_plugins)),
exposing `/metrics` on **15692**. The **core** Alloy scrapes it over the VCN private
subnet — no collector on the memory-tight edge. To turn it on:

1. Open **15692 edge → core** on the Oracle security list (like 5672 already is).
2. Set `RABBITMQ_METRICS_ADDR=<edge_private_ip>:15692` in the core `.env`.
3. Redeploy: `docker compose -f compose.edge.yml up -d` (plugin + port) and
   `docker compose -f compose.core.yml up -d` (Alloy scrape).

Useful metrics: **per-queue** (label `queue`) `rabbitmq_queue_messages_ready` (backlog),
`rabbitmq_queue_messages_unacked`; **global** (broker-wide, no per-queue publish/deliver
counters exist) `rabbitmq_global_messages_received_total` (published in),
`rabbitmq_global_messages_delivered_total` (out to consumers),
`rabbitmq_global_messages_redelivered_total`. Our queues: `commands`, `commands.retry`,
`commands.dlq`, `replies`, `group_events`, `wa_actions`, `wa_rpc`.

### Queue depth (ready) by queue
```promql
sum by (queue) (rabbitmq_queue_messages_ready)
```

### Dead-letter / retry backlog
```promql
rabbitmq_queue_messages{queue=~"commands.dlq|commands.retry"}
```

## Cross-linking logs ↔ traces

Logs (Loki) carry `trace_id`/`span_id` from Phase 3, and traces live in Tempo. In the
Loki data source, a derived field on `trace_id` → Tempo turns every log line into a jump
to its trace (and Tempo's "Logs for this span" jumps back).
