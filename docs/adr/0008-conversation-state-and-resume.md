---
status: accepted
date: 2026-06-12
---

# 0008 — Conversation state: Redis checkpointer, thread identity, hybrid resume

The multi-turn clarify/confirm loop ([PRD](../prd-agentic-command-mapping.md)) must remember,
**across separate inbound messages**, that a question is open and what the user already
answered. The current agent is stateless — `data.quoted_text` is its only context — so "iterar
entre dúvidas e opções" is impossible. Adding state raises three coupled questions: where it
lives, what scopes a conversation, and how the user resumes one without a stray "sim" an hour
later resurrecting dead state.

## Decision

- **Persist the LangGraph checkpointer to Redis Cloud** (`REDIS_URL`), not the in-memory
  `MemorySaver`. Amended 2026-10-21: the original choice was Upstash Redis, already in the
  stack, but `AsyncRedisSaver` needs the RediSearch and RedisJSON modules, which Upstash does
  not offer. Redis Cloud's free database ships them (`search`, `ReJSON`).
- **Checkpoints expire after 2 minutes** (`STORAGE_TTL_MINUTES`), just past the resume window.
  Nothing older is ever read, so the store holds only live conversations.
- **Thread identity `plataforma:chat:user`.**
- **Hybrid resume: quote wins, else a short window (~60–90 s).** The loop resumes if the user
  *quotes* the bot's question (via `quoted_message_id`, already in `CommandData`) **or** sends
  free text within the window. Quote takes precedence; the ADR fixes that order.

## Considered options

- **In-memory `MemorySaver`.** Zero new infra. Rejected: the bot is the frequently-redeployed
  side (broker PRD Goal 2), so a redeploy mid-disambiguation drops the state and the user's
  "sim" lands on nothing; and the `commands` queue allows future competing consumers (broker
  [ADR 0002](./0002-two-node-topology.md)) where state written by worker A is invisible to
  worker B. In-memory breaks exactly the redeploy + scale-out the broker design preserves.
- **Thread = `plataforma:user` (chat-agnostic).** Simpler key. Rejected: a user talking to the
  bot in two chats would cross-contaminate, and group concurrency collides.
- **Resume by TTL window only** (any message within N min continues). Rejected alone: inside
  the window an unrelated message gets mis-read as the answer; and too long a window is the
  "sim" ghost.
- **Resume by quote only.** Most foolproof, no ghost. Rejected alone: a user who types "sim"
  without quoting gets nothing — friction for the most natural answer. The hybrid keeps the
  quote's certainty as the primary path and the window as the permissive fallback.
- **Upstash Redis for the checkpointer.** Already in the stack. Rejected on implementation: no
  RediSearch/RedisJSON, so `AsyncRedisSaver.asetup()` cannot create its indexes.
- **Postgres checkpointer on Neon** (`langgraph-checkpoint-postgres`). Drops a vendor. Rejected:
  Postgres has no TTL, so a 2-minute state needs a cleanup job, and every agent turn would pay
  Neon's cross-region round trip and autosuspend cold start
  ([infrastructure](../infrastructure.md)).
- **Move the group-metadata cache from Upstash Redis into Redis Cloud** (one Redis vendor).
  Capacity fits: checkpoints are kilobytes under the TTL and the cache is a few MB against the
  30 MB free database. Rejected: one vendor fewer does not pay for swapping the gateway's REST
  client for a persistent TCP connection on the edge and trading Upstash's larger free tier
  for the smaller one.

## Consequences

- **Conversation state is testable locally with `fakeredis`** (already a dep) — no cloud in the
  TDD loop ([ADR 0011](./0011-agent-port-testing.md)).
- **A resume-window TTL constant** must be calibrated (start ~60–90 s) and lives as a named
  `ClassVar`, not a magic number.
- **At-least-once redelivery meets stateful progression.** A redelivered inbound message could
  re-run a graph turn. `decide` is pure over (state, input), so re-running yields the same
  routing and the executed command inherits ADR 0001 replay-safety; the only residual is a
  duplicate history turn, bounded by the crash gap. Gate on the `message_id` key (the
  [ADR 0001](./0001-at-least-once-delivery.md) escape hatch) only if it ever matters.
- **Redis Cloud free-tier limits** apply: 30 MB, one checkpoint read + one write per turn.
  Measured 2026-10-21: 2.4 MB used, 1 ms round trip from core (same AWS region).
- **The free database can disappear.** In late 2026-09 it vanished (NXDOMAIN) and every agent
  turn died silently for two weeks. Since PR #176 a `RedisError` makes the turn run statelessly and
  logs `agent_checkpointer_unavailable`; only the resume memory is lost.
