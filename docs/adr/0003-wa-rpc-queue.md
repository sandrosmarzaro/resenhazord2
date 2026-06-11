---
status: accepted
date: 2026-06-05
---

# 0003 — Keep a `wa_rpc` request/reply queue for `add`'s lookups

After proactive push, the only command that still needs a synchronous answer from the
gateway mid-execution is `add`, via `on_whatsapp` — once to resolve a specific
number's JID, and in a `while` loop for the random-number variant that keeps probing
until it finds a number that exists on WhatsApp. We keep these on a small **`wa_rpc`**
reply-queue (RPC-over-AMQP: `correlation_id` + `reply_to`), the same request/reply
shape as today's WebSocket `wa_call`/`wa_result`, rather than removing the round-trips.
`ban` and all participant-update writes are fire-and-forget (the code observes only
whether the call threw, never its return value), so they do **not** use `wa_rpc`.

## Considered options

- **Relocate the `add` lookup loop to the gateway.** The gateway holds the Baileys
  socket and could run the random-number search locally with zero per-iteration
  round-trips. Rejected for v1 — it bleeds business logic out of Python, violating the
  project's structural principle that the Python core owns all command logic. Kept as
  the documented escape hatch if `add` random latency becomes a real annoyance.
- **Drop `on_whatsapp` and always use the `@lid` fallback.** Removes the round-trip but
  loses JID resolution and cannot serve the random variant, which *needs* the
  existence check. Rejected.

## Timeout — the reply that never comes

A `wa_rpc` request blocks the bot handler on an `await` for the gateway's reply. If the
gateway restarted, lost the request, or was down when it was published, that reply never
arrives. This is more dangerous than an ordinary failure: the `await` runs **while the
bot still holds the original `commands` message unacked**, so with `prefetch = 1` a single
hung `add` stalls the *entire* bot consumer — every command behind it. And §7's
redelivery only fires on **process death**, never on a hung `await` in a live, healthy
process. So the broker-level safety nets do not catch this.

**Decision: `wa_rpc` requests carry an explicit timeout. A timeout raises a retryable
error** (an `ExternalServiceError` subclass — from the bot's view the gateway is an
external service across the broker) **that flows into the [ADR 0004](./0004-ack-retry-dlq.md)
retryable path**: nack → retry queue with backoff → the whole `add` reprocesses once the
gateway is back. `add` is set-semantic (`$addToSet`), so reprocessing is idempotent.
Reuses existing machinery — no new mechanism. (The exact timeout / N may be tuned in
implementation; gateway-down typically resolves in seconds, so it need not use the long
yt-dlp backoff ladder.)

## Consequences

- `add` (random) issues N broker round-trips through `wa_rpc` — accepted as a rare,
  low-priority admin command.
- The RPC-over-AMQP request/reply pattern stays in the design (one reply-queue), used
  by exactly one command.
- A `wa_rpc` timeout must never leave the handler hanging — it raises and reprocesses
  via ADR 0004, so a restarted gateway never deadlocks the bot consumer.
