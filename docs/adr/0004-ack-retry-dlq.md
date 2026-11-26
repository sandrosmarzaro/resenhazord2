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

## Amended 2026-11-26: one retry queue, attempts in the envelope

The retry path shipped simpler than the decision above. This section records what the
code does ([#388](https://github.com/sandrosmarzaro/resenhazord2/issues/388)).

- A retryable failure is acked like any other handled command. Before the ack,
  `RetryRouter` publishes the envelope to `commands.retry` through the default exchange,
  with publisher confirms. Nothing nacks to a retry exchange.
- `commands.retry` holds a message for 30 s (`CommandConsumer.RETRY_TTL_MS`, set as the
  queue's `x-message-ttl`) and then dead-letters it back to `commands` through
  `x-dead-letter-exchange: ''` and `x-dead-letter-routing-key: commands`. Every wait is
  the same 30 s, so there is no 5 s, 30 s, 2 m ladder.
- The attempt count is the `attempts` field of the JSON envelope, which `RetryRouter`
  raises by one before each retry. The `x-death` header RabbitMQ adds on the way back
  is never read.
- `MAX_ATTEMPTS` is 3, so a command runs at most three times with two 30 s waits in
  between. `DOWNLOAD_MAX_ATTEMPTS` is 1, so a `DownloadError` goes to the DLQ on its
  first failure without any retry.
- When the attempts run out, the user gets the error reply and `RetryRouter` publishes
  the envelope to `commands.dlq`. The DLQ is a plain durable queue that only receives
  direct publishes, and the `dlq-retention` policy above bounds it. `uv run task
  dlq:replay` puts dead letters back on `commands` with `attempts` reset to 0.
- Every queue is a classic durable queue, with no quorum queue and no
  `x-delivery-limit`. The attempt cap covers failures the consumer catches. A command
  that kills the process before its ack has no cap and comes back on every
  redelivery.

The simpler design was kept on purpose. Counting in the envelope avoids parsing
`x-death`, a list of entries per queue and reason that the code would have to search
for the retry queue's count. The whole decision lives in `RetryRouter` behind
`BrokerPort`, so the unit tests cover it with the mocked port
([ADR 0005](./0005-brokerport-two-layer-testing.md)) and the integration tests only
shorten `RETRY_TTL_MS`. The delivery limit was dropped because
both nodes already declare `commands` as a classic queue, and redeclaring it as quorum
fails with `PRECONDITION_FAILED`. Moving to quorum needs a new queue and an
expand/contract migration ([ADR 0006](./0006-two-node-cicd-deploy.md)).

A growing backoff is still possible as one retry queue per step (`commands.retry.5s`,
`commands.retry.30s`, `commands.retry.2m`), each with its own queue TTL and picked by
`attempts`. A single queue with a per-message `expiration` would not work, because
RabbitMQ only expires messages at the head and a 2 m message would hold a 5 s one behind
it. A dedicated dead-letter exchange belongs with the exchange and routing-key work in
[#383](https://github.com/sandrosmarzaro/resenhazord2/issues/383). Both are queue
contract changes and ship expand/contract. The `command_retries_total` metric shows
whether the fixed 30 s needs either.
