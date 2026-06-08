---
status: accepted
date: 2026-06-08
---

# 0005 — `BrokerPort` abstraction and two-layer testing

Implementation follows TDD (RED → GREEN → REFACTOR), so the broker transport must be
testable without faking what we don't own. The project's testing rule is explicit:
*mock your adapter (`WhatsAppPort`, `AxiosClient`), not the underlying SDK*. Talking to
`aio-pika` / `amqplib` directly from command and orchestration code would force unit
tests to mock those clients' internals — banned by that rule, and brittle on every
client upgrade.

## Decision

**Introduce a `BrokerPort`** (Python) and a broker adapter (TS) that wrap the AMQP
clients, mirroring the existing `WhatsAppPort` / `AxiosClient` / `HttpClient` seams. All
publish/consume goes through the port; no command or service touches `aio-pika` /
`amqplib` directly.

**Test in two layers:**

- **Unit — mock the `BrokerPort`.** Fast, owns the thing being mocked, follows the rule.
  Command and orchestration logic (which command publishes what, how a caught error
  routes) is exercised here. The bot's existing `_reset_singletons` conftest fixture
  gains a `BrokerPort.reset()` alongside `HttpClient` / `MongoDBConnection`; the gateway
  mirrors its `MockWhatsAppPort` with a `MockBrokerPort` factory.
- **Integration — the thin adapter + reliability semantics against a real ephemeral
  RabbitMQ** (testcontainers, or a single compose service). The behaviors that only a
  real broker can prove RED-then-GREEN live here: retry-queue TTL → DLX → DLQ routing,
  `x-death` attempt counting ([ADR 0004](./0004-ack-retry-dlq.md)), publisher confirms
  rejecting on `vm_memory_high_watermark` (§7), `wa_rpc` timeout → retry
  ([ADR 0003](./0003-wa-rpc-queue.md)). A mocked channel "confirms" routing without
  routing — the RED would be theatre exactly where correctness matters most.

## Considered options

- **Integration-only against testcontainers, no `BrokerPort`.** More faithful, but no
  fast unit feedback, and command-logic tests that don't care about the broker would
  drag a container. Slower TDD loop. Rejected — the port is the project's established
  pattern for every other external system, so omitting it for the broker is the
  inconsistency, not the abstraction.
- **Mock `aio-pika` / `amqplib` directly in test setup** (as `gateway/tests/setup.ts`
  already does for `mongodb`). Cheapest, but violates *don't mock what you don't own*
  for the reliability semantics: a mocked channel can't prove TTL/DLX/`x-death` actually
  route. Acceptable only for incidental infra stubbing, never for the semantics under
  test. Rejected as the primary strategy.

## Consequences

- One new abstraction layer — but it matches `WhatsAppPort` / `AxiosClient`, so it is
  pattern-matching, not net-new surface (CLAUDE.md: match existing patterns first).
- Local containers are **not** an impediment: RabbitMQ runs as a single
  `rabbitmq:3-management` container (~100 MB) with no Oracle/cloud dependency. The
  `compose.edge` / `compose.core` split (§11) is production-only; the TDD loop uses one
  ephemeral broker.
- **Backoff/retry tests are timing-dependent.** They must use short TTLs plus
  `vi.waitFor` / event-or-poll waits — never `asyncio.sleep` / `setTimeout` (already a
  `testing.md` rule) — or they flake.
- Phase 1 of the migration (§8) delivers the `BrokerPort` + adapter + their integration
  harness before any flow moves, so every later phase has both test layers available
  from the start.
