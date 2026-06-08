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
