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

- **Persist the LangGraph checkpointer to Upstash Redis** (already in the stack), not the
  in-memory `MemorySaver`.
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
- **Upstash Redis free-tier request limits** apply: one checkpoint read + one write per turn.
  Sporadic command volume keeps this well under cap.
