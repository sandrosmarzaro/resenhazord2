---
status: accepted
date: 2026-06-06
---

# 0004 — Ack after handled, retry with backoff, DLQ

Consumers **ack a command once it is handled — success or a caught error both ack**,
not "ack only on success". Handling a `BotError` and sending the friendly reply is
handling the command, so it must not be redelivered; only an actual process death
before the ack triggers the at-least-once redelivery of [ADR 0001](./0001-at-least-once-delivery.md).
Failures are routed by the bot's existing exception taxonomy (`bot/domain/exceptions.py`)
via a single `isinstance(error, ExternalServiceError)` check:

- **Non-retryable** (`ValidationError`, `MediaNotFoundError`, bare `CommandError`,
  unknown `Exception`) — error reply + ack now. Retrying a bad input or a bug only
  delays the user's error.
- **Retryable** (`ExternalServiceError`, incl. `DownloadError`) — nack `requeue=false`
  to a **retry queue** with a backoff TTL (e.g. 5 s → 30 s → 2 m) whose dead-letter
  exchange points back to the main queue; `x-death` counts attempts. After **N**
  attempts the failure has persisted → error reply + park in a terminal **DLQ**.

This also defuses poison messages: a deterministic crash that would loop forever under
at-least-once hits the same N-cap and lands in the DLQ instead of head-of-line blocking
the queue (worsened by `prefetch=1`). `x-delivery-limit` on a quorum queue is the hard
backstop.

## Considered options

- **Ack only on success (no DLQ).** Rejected — a deterministic failure is never acked,
  loops forever, and blocks the queue. The original §5 wording, now corrected.
- **No automatic retry — error reply on first transient failure.** Simpler and matches
  today's WebSocket behaviour, but loses recovery from a brief external-API blip. The
  retry ladder was chosen deliberately for that recovery (and as a real
  dead-letter/poison-handling exercise).

## Consequences

- A retry exchange/queue + a terminal DLQ are part of the topology from the start.
- `DownloadError` inherits retryable but yt-dlp failures are often permanent — tuned to
  a low N (e.g. 1) so a permanent failure doesn't make the user wait the full ladder.
- Error replies for retryable failures are deferred until retries are exhausted. The
  user gets no immediate error — but the gateway-local typing indicator is *not* a
  reliable "still working" signal across a long ladder: WhatsApp presence lapses well
  before a multi-minute backoff (5 s → 30 s → 2 m), and the gateway has no signal that a
  retry is even in progress. The terminal reply — success or the exhausted-retry error —
  is the real completion signal, not continuous typing.

## Amended 2026-10-23: bounded queues

The DLQ is no longer unbounded. A broker policy keeps dead letters for a week, at most
500 messages or 32 MiB, dropping the oldest first. `commands` is bounded too: past 100
commands or 64 MiB the oldest is dropped, because in a backlog an old command has lost
its moment and the cap stays under the 256 MiB memory watermark.

The limits are policies (`observability/rabbitmq/policies.sh`, applied by the edge
deploy), not queue arguments. Both nodes declare these durable queues, and redeclaring
one with new arguments fails with `PRECONDITION_FAILED`. A boot-time definitions file
was rejected: importing one skips seeding the default vhost and user, so a fresh volume
would not boot without credentials committed to the repo.

## Amended 2026-10-23: four commands at once

`prefetch` is 4, so a slow command no longer holds every other chat's reply. Memory
is the limit on the 640m core container: a `,dl` reply carries its video as base64
inside the JSON, roughly three copies of up to 50 MB. A command marked
`CommandConfig.exclusive` (today only `,dl`) takes a lane of one from the moment it
matches until its reply is published, so two downloads never overlap.

## Amended 2026-11-27: the ladder as built

The decision above is implemented
([#388](https://github.com/sandrosmarzaro/resenhazord2/issues/388)). Both nodes declare
this topology from the data files of [ADR 0017](./0017-broker-exchanges-and-routing-keys.md).

| Queue | Type and arguments | Dead-letters with key |
|---|---|---|
| `commands.quorum` | quorum, `x-delivery-limit: 3`, DLX `resenhazord.dlx` | the key it arrived with |
| `commands.retry.5s` | classic, TTL 5 s, DLX `resenhazord.dlx` | `retry.30s` |
| `commands.retry.30s` | classic, TTL 30 s, DLX `resenhazord.dlx` | `retry.2m` |
| `commands.retry.2m` | classic, TTL 2 min, DLX `resenhazord.dlx` | `retry.dead` |
| `commands.dlq` | classic, bounded by the `dlq-retention` policy | terminal |

`resenhazord.dlx` is a headers exchange that routes a dead letter by its
`x-last-death-reason`, matched with `x-match: all-with-x` because a plain match skips
`x-` headers:

- `rejected` goes to `resenhazord.retry`, a topic exchange that picks the step by routing
  key: `commands.quorum` (a command's first run) to the 5 s step, `retry.30s` to the 30 s
  step, `retry.2m` to the 2 min step and `retry.dead` to `commands.dlq`.
- `expired` goes back to `commands.quorum`, which is how a step ends.
- `delivery_limit` goes to `commands.dlq`.
- Any other reason is dropped. A full queue's oldest command dies with `maxlen` and is
  gone, as the `commands-bounded` policy intends.

A retryable failure (`ExternalServiceError`) below its attempt cap makes `RetryRouter`
raise `DeliveryRejectedError`. The broker adapter lets `message.process()` nack it with
`requeue=false`, so the queue's dead-letter route takes it, and nothing is published. Each
step returns the command with the next step's key, so the routing key counts the attempts
and the exchange picks the wait.

The attempt number comes from `x-death`. RabbitMQ keeps one entry per queue and reason
with a count, and the adapter passes `1 +` the `rejected` count for the consumed queue to
the handler as `Delivery.attempt`. The envelope has no `attempts` field any more.

`MAX_ATTEMPTS` is still 3, so a caught external failure runs at 0 s, 5 s and 35 s and then
gets the error reply while `RetryRouter` publishes it to `commands.dlq`.
`DOWNLOAD_MAX_ATTEMPTS` is 1, so a `DownloadError` goes to the DLQ on its first failure.
The 2 min step is the broker's own cap. Something the code rejects without counting, such
as a bug that raises `DeliveryRejectedError` on every run, gets a fourth run after 2 min
and then lands in the DLQ through `retry.dead` instead of looping.

`x-delivery-limit` is the poison backstop. A command that kills the core before its ack
comes back after every restart, and after three returns the broker dead-letters it with
`delivery_limit` straight to the DLQ. It cannot go through the ladder: back in
`commands.quorum` with no rejection on the way, RabbitMQ would drop it as a dead-letter
cycle. This is why the DLX is a headers exchange and not a topic one, since a dead letter
keeps its routing key and a topic exchange could not tell a poison message from a retry.

`uv run task dlq:replay` publishes each dead letter's body as a new message to
`commands.quorum`. It carries no `x-death`, so it starts again at attempt 1, and
`replayed: true` lets it past the dedup inbox.

### Migration

A classic queue cannot be redeclared as quorum (`PRECONDITION_FAILED`), so
`commands.quorum` is a new queue, shipped expand/contract
([ADR 0006](./0006-two-node-cicd-deploy.md)):

1. **Expand (done).** Both nodes declare the new queues and exchanges and still declare
   the classic `commands` and `commands.retry` with their old arguments. The gateway still
   publishes to `commands`. The core consumes `commands` and republishes each message to
   `commands.quorum` before its ack, and an old core's `commands.retry` dead-letters into
   `commands`, so both drain into the quorum queue. Either node can deploy first. The
   `commands-bounded` policy matches `^commands(\.quorum)?$`.
2. **Migrate (next release).** The gateway publishes to `commands.quorum`. This needs a
   core that consumes it, so it ships only after step 1 is deployed.
3. **Contract (the release after).** Once `rabbitmqctl list_queues name messages` shows
   `commands` and `commands.retry` empty, the nodes stop declaring them, the core stops
   draining `commands`, and the owner runs `rabbitmqctl delete_queue commands` and
   `rabbitmqctl delete_queue commands.retry`. The `command.#` binding of ADR 0017 moves to
   `commands.quorum` then, and `resenhazord.retry` needs a binding for that key to the 5 s
   step, because a command published through that exchange arrives with
   `command.whatsapp` instead of `commands.quorum`.
