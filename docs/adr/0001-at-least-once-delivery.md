---
status: accepted
date: 2026-06-05
---

# 0001 — At-least-once delivery, no dedup

The gateway ↔ bot transport moves to a durable broker (RabbitMQ) with manual ack,
which gives **at-least-once** delivery: a consumer that crashes after doing the work
but before acking causes the message to be redelivered. v1 accepts this and adds
**no** consumer-side deduplication, because almost every command is replay-safe and
the only non-idempotent ones are two low-stakes counters — `,borges`
(`commands/borges.py`, `$inc nargas`) and the steal-group counter
(`services/steal_group.py`, `$inc number`) — whose worst case is a vanity number off
by one, not data corruption.

## Considered options

- **`message_id` idempotency key (inbox pattern).** Every inbound WhatsApp message
  carries a unique `CommandData.message_id`; a Redis `SET` with short TTL (Upstash
  already runs) would make redelivery a no-op. Deferred as a documented escape hatch,
  built only when a state-meaningful non-idempotent command lands.
- **At-most-once (ack before processing).** Rejected — a crash mid-command loses the
  message, violating the no-lost-commands goal.

## Consequences

Any *new* non-idempotent command (economy, points, anything money- or
state-meaningful) must be made replay-safe or gate on the `message_id` key. This
guard belongs in `.claude/rules/python.md` when implementation starts.
