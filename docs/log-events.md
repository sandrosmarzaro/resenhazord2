# Log events

The core's logs reach Loki as structured records: structlog's event dict becomes the OTLP
body, so every field below can be filtered with `| json`. Each record from a traced call
also carries `trace_id` and `span_id`, which open the matching trace in Tempo. This page
lists the events worth querying and the fields that stay stable. An agent investigating
through the Grafana MCP (`query_loki_logs`) or `logcli` should start here instead of
grepping the call sites.

## Correlation

| Field | Where it comes from | Use it to |
|---|---|---|
| `trace_id` | the OTel log bridge, on any record inside a span | open the trace in Tempo (Sentry's trace id is a different one) |
| `correlation_id` | the broker envelope id, bound per delivery in `CommandConsumer` | follow one WhatsApp command across retries, the DLQ and Sentry (`correlation_id` tag) |
| `jid`, `sender` | bound per delivery on the WhatsApp path | every log of a command in that chat |
| `chat` | `command_completed` itself, on every platform | per-chat questions that include Discord and Telegram |

## The canonical event

`command_completed` is logged once per command run, on every platform, from `Command.run`
([`bot/domain/commands/base.py`](../bot/domain/commands/base.py)). It is the event to
count, group or alert on. The other events explain one.

| Field | Values |
|---|---|
| `command` | the command's name (`porno`, `dl`, `fato`) |
| `platform` | `whatsapp`, `discord`, `telegram` |
| `chat_type` | `group`, `private` |
| `chat` | the chat id: the WhatsApp JID, the Discord channel or the Telegram chat |
| `outcome` | `success`, `bot_error` (the user's mistake), `external_error`, `unexpected_error` |
| `error_type` | the exception class on a failure, `null` otherwise. Never its message, which can carry a URL with a secret in it |
| `duration_ms` | the run, as the `command.run` span measures it |

## Events by flow

| Event | Level | Fields | Means |
|---|---|---|---|
| `upstream_failed` | warning, error | `upstream` | a third-party call failed and the command answered around it, a fallback included. Each one also counts `upstream_failures_total{upstream}` |
| `command_unexpected_error` | error | traceback | a command raised something it didn't classify. The user got the generic error reply |
| `command_retry_scheduled` | warning | `attempts`, `error` | an external failure sent the command down the retry ladder |
| `command_retries_exhausted` | error (warning for downloads) | `attempts`, `error` | the ladder ran out and the command went to `commands.dlq` |
| `command_duplicate_skipped`, `command_redelivery_skipped` | info | none | at-least-once delivery handed over a command already running or already answered |
| `agent_routing` | info | `text` | a message went to the natural-language agent |
| `agent_provider_failed` | warning | `error` | an LLM provider failed. The chain tries the next one |
| `agent_over_budget`, `agent_rate_limited` | info | none | the agent refused a call to protect the token budget or the rate limit |
| `platform_up`, `platform_failed`, `platform_retrying` | info, error, warning | `platform` | a platform adapter connected, crashed, or is backing off |
| `birthday_celebration_error` | error | traceback | the midnight birthday job failed. It retries next midnight |

## Queries

```logql
# Every command in the last hour, newest first
{service_name="bot"} | json | event="command_completed"

# Failures only, with what failed
{service_name="bot"} | json | event="command_completed" | outcome=~"external_error|unexpected_error"
  | line_format "{{.command}} {{.platform}} {{.error_type}} {{.duration_ms}}ms"

# Active chats per platform over a day
count by (platform) (sum by (platform, chat) (count_over_time(
  {service_name="bot"} | json | event="command_completed" [1d])))

# Which upstream failed most this week
sum by (upstream) (count_over_time({service_name="bot"} | json | event="upstream_failed" [7d]))

# Everything one WhatsApp command logged, retries included
{service_name="bot"} | json | correlation_id="<envelope id>"
```

From a `command_completed` line, take its `trace_id` to Tempo for the span tree. There,
`span.self_time` (see [observability-dashboards.md](observability-dashboards.md#self-time-vs-total))
shows which call held the time.

## Adding an event

Name it `<flow>_<what happened>` in snake case, pass data as keyword fields rather than
in the event string, and keep secrets and exception messages that may hold URLs out of
it. If it marks a state other code or a dashboard depends on, add it to this table.
