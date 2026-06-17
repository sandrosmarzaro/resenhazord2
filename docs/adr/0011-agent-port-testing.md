---
status: accepted
date: 2026-06-12
---

# 0011 — Agent port testing strategy

Implementation follows TDD (RED → GREEN → REFACTOR), so the agent rework must be testable
without faking what we don't own. The project's testing rule is explicit: *mock your adapter,
not the underlying SDK*. The agent now sits on three external systems — LangGraph, LangChain,
and Upstash (Vector + Redis) — and two of them have no local emulator (Upstash is cloud-only,
unlike RabbitMQ's testcontainer). Talking to those clients directly from agent logic would
force unit tests to mock framework internals — banned by that rule, and brittle on every
upgrade. This mirrors [ADR 0005](./0005-brokerport-two-layer-testing.md) for the broker.

## Decision

**Route all three through ports** — `AgentOrchestratorPort`, `LLMProviderPort`,
`ExampleRetrieverPort` ([ADR 0007](./0007-agent-frameworks-behind-ports.md)) — and test by
faking the ports we own:

- **Unit — mock the ports.** `LLMProviderPort` returns canned structured decisions (a command
  tool call, a `clarify`, a `suggest`, each with a confidence); `ExampleRetrieverPort` returns
  canned top-k examples. Graph routing, confidence gating, resume logic, and translation are
  exercised deterministically. The conftest `_reset_singletons` fixture gains resets for the
  new ports alongside `HttpClient` / `BrokerPort`.
- **Conversation state — `fakeredis`** (already a dep). The checkpointer round-trip, `thread_id`
  keying, and the hybrid resume window run locally with no cloud
  ([ADR 0008](./0008-conversation-state-and-resume.md)).
- **Retriever — an in-memory fake** behind `ExampleRetrieverPort` returning deterministic
  similarity order. There is no Upstash container to spin up.

## Considered options

- **Mock LangChain's HTTP with `respx`** (the project's HTTP-mock rule). Rejected: LangChain
  owns its client; intercepting its transport mocks what we don't own and breaks on every
  client change. The port is the seam — mock there, never the framework's wire calls.
- **Real Upstash Vector/Redis in CI.** Most faithful. Rejected as the default: it needs secrets
  in CI, adds network flakiness and free-tier quota pressure to every run, and the port's fake
  already proves the agent logic. A real Upstash run stays optional, manual, and secret-gated.
- **Integration-only, no ports.** Rejected — no fast unit feedback, and it contradicts the
  pattern every other external system in the project already follows.

## Consequences

- **Graph behavior is deterministic in tests** because the LLM's decision is canned at the
  port — the routing/gating logic is what's under test, not the model.
- **No cloud dependency in the TDD loop:** `fakeredis` for state, in-memory fake for retrieval.
  The Upstash split is production-only, like the broker's `compose.edge`/`compose.core`.
- **Resume-window tests are timing-dependent.** They use short TTLs + event-or-poll waits,
  never `asyncio.sleep` (a `testing.md` rule), or they flake.
- **The fakes are real fixtures, not stubs** — they encode the port contract, so a port change
  that breaks the contract breaks the fake, surfacing the drift.
