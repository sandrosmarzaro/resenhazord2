# PRD — Event-Driven Gateway (WebSocket → AMQP)

**Status:** Draft · **Date:** 2026-06-05 · **Owner:** Sandro

Replace the bidirectional WebSocket transport between the WhatsApp gateway
(`gateway/`, Bun) and the Python core (`bot/`) with a durable AMQP message broker
(RabbitMQ), moving the inbound command and outbound reply paths to fire-and-forget
work queues.

## 1. Problem

The gateway ↔ Python link is a single bidirectional WebSocket
(`gateway/src/bridge/PythonBridge.ts` ↔ `bot/adapters/http/ws_handler.py`). It
couples the two processes tightly:

- **Message loss on restart.** A WS drop rejects every in-flight request
  (`rejectAllPending`) and any command that arrives while Python is redeploying is
  silently skipped (`send_command_skipped_not_connected`). There is no buffer.
- **Lifecycles are entangled.** Deploying or crashing Python tears down in-flight
  work on the gateway. The disconnect path was also the source of the CPU-runaway
  that froze the VPS (see [risks](#9-risks)).
- **No path to horizontal scale.** A second bot worker can't share load; the WS is
  one socket, one peer.

## 2. Goals

1. **No lost commands.** A command published while Python is down is processed when
   Python returns. Durable queue + manual ack.
2. **Decoupled lifecycles.** Gateway and bot deploy, crash, and restart
   independently. Neither blocks on the other being up.
3. **Learning vehicle.** Real broker, real exchanges/queues, real ack semantics —
   an event-driven design done properly, not WS-in-disguise.

## 3. Non-goals

- **Horizontal scale is not a v1 goal** — but the topology must not preclude it
  (single `commands` queue with competing consumers makes adding a worker a
  config change, not a redesign).
- **Pub/sub fan-out is out of scope.** This is a work-queue workload: one command →
  exactly one bot worker. Fan-out only matters if an independent subscriber (e.g.
  analytics) later wants every event; noted as a future extension, not built now.
- **No change to the command surface, `CommandRegistry`, or any `Command`
  subclass.** Only the transport boundary moves.
- **Telegram and Discord adapters are untouched** — they don't use this link.

## 4. Current architecture

Three flows ride the one socket. Only the third is genuinely request/reply.

| Flow | Direction | Shape | Today |
|---|---|---|---|
| Inbound command | GW → Py | fire-and-forget | `sendCommand` blocks on the reply only because WS forces it to |
| Outbound reply | Py → GW | fire-and-forget | returned as `command_response`, GW pushes to Baileys |
| Mid-command gateway call (`wa_call`) | Py → GW | **request/reply** | Python blocks awaiting `wa_result` |

The first two are fire-and-forget at the domain level — they're only synchronous
because a socket round-trip made them so. The correlation they need (`jid`,
`quoted_message_id`, `expiration`) already lives in `CommandData` / `BotMessage`,
not in a pending future. They map cleanly onto two independent queues.

The third flow is the real constraint and §6 deals with it.

## 5. Proposed architecture

A `topic` exchange in front of durable queues. Gateway and bot each publish and
consume; neither holds a connection to the other.

```
                         ┌──────────────────────────────────────────┐
                         │            RabbitMQ  (exchange:           │
                         │              resenha  · topic)            │
                         └──────────────────────────────────────────┘
   command.inbound  │              │ reply.outbound        │ group.event
        ▲           ▼              ▲           │           ▲
        │     ┌───────────┐        │           ▼           │
  publish     │ commands  │   consume     ┌──────────┐  publish
        │     │  queue    │        │       │ replies  │     │
        │     │ (durable) │        │       │  queue   │     │
        │     └─────┬─────┘        │       └────┬─────┘     │
        │           │ consume      │ publish    │ consume   │
   ┌────┴───────────▼──────┐   ┌───┴────────────▼───────────┴────┐
   │       GATEWAY         │   │            BOT (Python)         │
   │  Bun + Baileys        │   │  FastAPI + CommandHandler       │
   │  - publishes command  │   │  - consumes command queue       │
   │  - consumes replies   │   │  - publishes reply              │
   │  - pushes to Baileys   │  │  - consumes group.event         │
   └───────────────────────┘   └─────────────────────────────────┘
```

### Queue topology

| Queue | Producer | Consumer | Routing key | Payload |
|---|---|---|---|---|
| `commands` | Gateway | Bot (competing) | `command.inbound` | `WSCommandData` JSON + media bytes (see §5 media) |
| `replies` | Bot | Gateway | `reply.outbound` | `BotMessage[]` JSON + media bytes |
| `group_events` | Gateway | Bot | `group.event` | steal-group payload → `StealGroupService` |
| `media` | both | both | `media.blob` | raw binary body for **large** media, correlated to its command/reply by id (see media bullet) |
| `wa_rpc` | Bot | Gateway | `wa.call.on_whatsapp` | request/reply, `correlation_id` + `reply_to` — **only** `add`'s `on_whatsapp` lookups (§6) |

- **All queues `durable: true`; all messages `persistent`.** Survive a broker
  restart.
- **Manual ack after the command is *handled*** — success *or* a caught error both
  ack (handling a `BotError` and replying is handling, not failing). Only an actual
  process death before the ack triggers redelivery (the §7 at-least-once case).
  Retryable failures and poison messages are routed through a retry queue + DLQ — see
  §7 and [ADR 0004](./adr/0004-ack-retry-dlq.md).
- **`prefetch = 1` per consumer** initially, so one slow command doesn't starve
  others and a second worker can be added for round-robin with no code change. Only
  `commands` is a competing-consumer queue (the future scale-out point); `replies` stays
  single-consumer — one gateway owns the one Baileys/WhatsApp session, so there is
  nothing to compete.
- **Gateway-local "working" feedback.** Today a Python `command_ack` triggers the
  gateway's emoji reaction + typing indicator (`PythonForwarder.ts:62`). Fire-and-forget
  removes that round-trip, so the gateway drives feedback **itself**: it already mirrors
  the parser (`gateway/src/parsers/CommandParser.ts`), so on a local match it reacts and
  starts typing *immediately* — faster than today — and stops when a reply lands on
  `replies`.
  - **Invariant — every consumed command publishes a terminal reply.** Even commands
    that produce no user output (e.g. `add` returns `[]` on success) must publish a
    terminal signal (an empty "done" reply) so the gateway can stop the typing
    indicator. Without it, no-output commands hang the indicator until timeout.
- **Media split by size — no external store.** AMQP message bodies are binary-native;
  base64 is only needed when bytes are embedded *inside* JSON. So media is moved two
  ways, gated by a size threshold (a few hundred KB; exact value set in implementation):
  - **Small (≤ threshold — stickers, images):** base64 embedded in the command/reply
    JSON. One message, one round-trip. Covers the common case.
  - **Large (> threshold — video):** a **separate message with a raw binary body** (no
    33% inflation — a 16 MB video stays 16 MB) on the dedicated `media` queue,
    correlated to its command/reply by id. Keeps the hot `commands` queue lean.
  - The `media` queue is **disk-backed** (lazy/quorum) so large payloads page to disk
    instead of pegging the 1 GB edge-node broker's RAM. A hard guard rejects media
    over WhatsApp's ~16 MB cap. No object store: media is transient transport, not a
    durable artifact, so nothing accumulates and there is no lifecycle to manage.
  - **Cost accepted:** large media is a *separate* message from its command, so the
    consumer correlates by id and tolerates arrival order (media may land before the
    command). Bounded by `correlation_id` + `prefetch`.

### Why raw AMQP clients (`aio-pika` / `amqplib`), not Celery

Celery is not an alternative to RabbitMQ — it's an alternative to the AMQP *client*,
and it sits *on top of* a broker we'd still run. It's the wrong fit here:

- **Polyglot boundary.** The producer is the TypeScript gateway; Celery is Python-only
  with no real TS client. `aio-pika` (Python) + `amqplib` (TS) both speak raw AMQP, the
  actual cross-language lingua franca — the broker is the polyglot seam ([ADR 0002](./adr/0002-two-node-topology.md)).
- **Bidirectional, topology-heavy.** This design needs direct control Celery abstracts
  away: `wa_rpc` request/reply ([ADR 0003](./adr/0003-wa-rpc-queue.md)), retry-queue +
  DLX + DLQ with `x-death` counting ([ADR 0004](./adr/0004-ack-retry-dlq.md)), raw
  binary media bodies, selective headers, manual ack semantics, and replies consumed by
  a *non-Celery* TS process. Celery fights all of these.
- **Where Celery would fit** (not this): Python-only background jobs (scheduled cleanup,
  Python-to-Python heavy processing). Could be added alongside later; it is not the
  gateway↔bot transport this PRD solves.

## 6. Synchronous holdouts — proactive push

The third flow (§4: `wa_call` request/reply) is the only one that can't simply become
fire-and-forget. The strategy is to shrink it to near-zero rather than reproduce a
synchronous channel.

Decision: **the gateway ships the data it can compute inside the command payload,
so the bot rarely needs to call back.** It already does this for media
(`PythonBridge.ts` downloads before forwarding). Per-call analysis:

| Gateway call | Used by | Can be proactively pushed? | Plan |
|---|---|---|---|
| `group_metadata` | `add`, `ban`, `adm`, `StealGroupService` | ✅ gateway is the authoritative source (holds Baileys + a layered cache) | **Selective attach.** A `{add, ban, adm}` set in the gateway (which already mirrors the parser) gates it — only those commands carry the ~12 KB metadata; the other 95% of group traffic stays lean. Bot reads it from `CommandData`, never round-trips. Trade: a 3-string command set lives in the gateway (a transport hint, not business logic); a 4th metadata-using command means updating it. |
| `download_media` | `sticker`, `drive`, `spit`, `extract` | ✅ already prefetched | Keep prefetch; bytes ride with the command. |
| `send_message`, presence, `update_profile_picture`, `group_update_subject/description` | replies, typing, admin writes | ✅ fire-and-forget | Publish to `replies` (or a `wa_actions` queue). No reply needed. |
| `group_participants_update` | `add`, `ban`, `StealGroupService` | ✅ the code only checks whether the call *threw*, not its return value (`ban.py:60`, `add.py:89`) | **Fire-and-forget, optimistic.** Publish the action; reply assuming success. `ban` needs nothing more. |
| `on_whatsapp` | `add` | ❌ depends on a phone number generated/typed at runtime | **Genuine holdout** — the only one. |

**The single genuine holdout: `on_whatsapp`, used only by `add`.** Code analysis
narrows the field — `ban` needs no request/reply at all, and the participant-update
writes are fire-and-forget (only their *exception* is observed, never their value):

- **`ban`** — picks targets from the pushed metadata / `mentioned_jids`, fires
  `group_participants_update(remove)` optimistically, replies "Se fudeu @x". No
  round-trip. Worst case: a silently-failed remove and a wrongful taunt — tolerated.
- **`add` (specific number)** — one `on_whatsapp` to resolve the JID.
- **`add` (random number)** — a `while` loop calling `on_whatsapp` until a number that
  exists is found. Iterative, runtime-generated — can't be precomputed or
  fired-and-forgotten. This is the one chatty case.

**Decision: a small `wa_rpc` reply-queue (RPC-over-AMQP, `correlation_id` +
`reply_to`) for `add`'s `on_whatsapp` lookups; everything else is fire-and-forget.**
The `add` random-number loop stays on `wa_rpc` despite its N round-trips — it's a rare
admin command and the latency is tolerable, and that price buys keeping **all business
logic in Python** (a structural project principle) instead of bleeding the loop into
the gateway. This keeps the RPC-over-AMQP request/reply pattern in the design. If
`add` random latency ever becomes a real annoyance, the documented alternative is to
relocate the lookup loop to the gateway (see [ADR 0003](./adr/0003-wa-rpc-queue.md)).
Proactive push still covers ~95% of traffic (all reads via the group-metadata cache,
all media via prefetch); `wa_rpc` carries only `add`'s lookups.

## 7. Reliability semantics

- **At-least-once delivery, no dedup (v1).** Manual ack + durable queues mean a
  command can be redelivered after a crash (consumer dies *after* the work, *before*
  the ack). v1 accepts this and adds **no** dedup/outbox (YAGNI). The window is a
  narrow crash gap and almost every command is replay-safe: pure render/reply,
  set-semantic Mongo writes (`$addToSet`, `$pull`), and WhatsApp admin writes
  (re-adding an existing member is a no-op).
  - **Known exceptions — two non-idempotent counters.** `,borges`
    (`commands/borges.py`, `$inc nargas`) and the steal-group counter
    (`services/steal_group.py`, `$inc number`) double-count on redelivery. Worst
    case is a vanity number off by one — explicitly tolerated, not corruption.
  - **Guard rule.** Any *new* non-idempotent command (economy, points, anything
    money- or state-meaningful) must either be made replay-safe or gate on the
    `message_id` idempotency key below. This belongs in `.claude/rules/python.md`
    when implementation starts.
  - **Escape hatch (deferred).** Every inbound WhatsApp message carries a unique
    `CommandData.message_id`. A consumer-side inbox — a Redis `SET` with short TTL
    (Upstash already runs) — turns redelivery into a no-op. Built only when a
    state-meaningful non-idempotent command lands, not before.
- **Failure handling — retry, DLQ, driven by the exception taxonomy.** The bot's
  existing exceptions (`bot/domain/exceptions.py`) already partition retryable from
  not, via a single `isinstance(error, ExternalServiceError)` check:
  - **Non-retryable** (`ValidationError`, `MediaNotFoundError`, bare `CommandError`,
    unknown `Exception`): send the error reply and **ack** immediately. Retrying a bad
    input or a bug only delays the user's error and wastes cycles.
  - **Retryable** (`ExternalServiceError`, incl. `DownloadError`): dead-letter to a
    **retry queue** with backoff TTL (e.g. 5 s → 30 s → 2 m), which dead-letters back
    to the main queue; `x-death` tracks the attempt count. After **N attempts** the
    transient failure has *persisted* → send the error reply and park in a terminal
    **DLQ**. The main queue is never head-of-line blocked: a failing message leaves it
    immediately (nack `requeue=false`), waiting out its backoff in the retry queue.
  - **Poison protection.** The same N-attempt cap + DLQ catches a deterministic crash
    that would otherwise loop forever under at-least-once. (`x-delivery-limit` on a
    quorum queue is the hard backstop.)
  - **Caveat:** `DownloadError` inherits retryable, but yt-dlp failures are often
    permanent (removed/geo-blocked video) — tune it to a low N (e.g. 1) so a permanent
    failure doesn't make the user wait out the full backoff ladder. Decided in
    implementation.
- **Publisher confirms — the other half of "no lost commands."** A durable queue only
  protects a message the broker has *already accepted*. `basic.publish` is fire-and-forget
  by default: the client hands off to the TCP buffer and moves on, so a broker death
  mid-handoff — or a `vm_memory_high_watermark` rejection on the 1 GB edge broker — loses
  the message *silently*, and the WhatsApp message is already consumed from Baileys with
  nowhere to replay from. **Both publishers run in confirm mode** and treat a message as
  sent only after the broker's `basic.ack`. **Synchronous (publish-and-wait):** the
  volume is sporadic commands, not a stream, so the ~1 RTT cost (sub-ms within the VCN)
  is irrelevant, and the simpler model is easier to test than tracking async sequence
  numbers and nacks. This closes Goal 1 at the exact case that matters most: a broker
  under memory pressure on a 1 GB micro.
  - **On a failed confirm (nack / timeout), the gateway retries locally with backoff,
    holding the message in a bounded in-memory buffer.** Broker and gateway are
    co-located (ADR 0002), so broker-unreachable means a same-host container restart —
    seconds, not a network partition — and the retry drains as soon as it returns. The
    buffer is **capped at N messages** so a prolonged broker outage can't exhaust the
    1 GB micro's RAM; at the cap, the oldest is dropped (last resort, logged).
  - **The bot's side is simpler — no buffer.** The bot also publishes (`replies`,
    `wa_rpc`), but a failed reply-confirm means the command isn't done, so the bot
    simply **does not ack the `commands` message** — that unacked message *is* its
    buffer, and §7 redelivery reprocesses it once the broker returns. The asymmetry is
    deliberate: the gateway needs an in-memory buffer because it has no upstream
    redelivery (Baileys already consumed the WhatsApp message), while the bot always
    has the unacked command as its safety net.
  - **Residual risk (accepted): the gateway buffer is in-memory.** If the *gateway process
    itself* dies while holding unconfirmed messages, they're lost — a narrow window,
    since the gateway is the stable long-lived side (Baileys session) that rarely
    restarts. A local disk spool (file/SQLite) would survive even that, but it
    reintroduces a second durability mechanism outside the broker — exactly what the
    broker exists to be. Not worth it for a seconds-wide window; revisit only if gateway
    restarts prove to coincide with broker outages in practice.
- **Connection loss is invisible to the domain.** A broker reconnect doesn't reject
  in-flight commands — they sit in the queue. `rejectAllPending` and the
  `send_command_skipped_not_connected` drop both disappear.
- **Graceful shutdown on redeploy — best-effort drain.** Goal 2 makes the bot the
  frequently-redeployed side, so every deploy SIGTERMs a consumer mid-message. Relying
  on redelivery alone would duplicate on each badly-timed deploy: the bot would
  re-run an in-flight command (double-counting `,borges` / steal-group), and worse, the
  **gateway's `replies` consumer would re-push a reply to Baileys — a user-visible
  duplicate message.** So both consumers handle SIGTERM: **cancel the consumer (stop
  accepting new) → finish the in-flight message and ack → close.** Bounded by a grace
  window (N seconds); if in-flight work outlasts it (a long yt-dlp download), the
  orchestrator SIGKILLs and the message falls back to §7 redelivery — graceful shutdown
  is best-effort, not a guarantee, and the at-least-once machinery is the backstop. At
  `prefetch = 1` only the one in-flight message exists, so no separate requeue of
  prefetched-but-unstarted messages is needed; revisit if workers scale out.

## 8. Migration phases

Each phase ships independently; the WS path stays until the last. **The command path
is one atomic unit** — inbound command and outbound reply are a single synchronous
round-trip today (`PythonBridge.sendAndWait`), so they cannot be migrated separately.
A reply published to a queue while inbound still expects a WS response would just time
the WS request out.

1. **Infra + test seam + node split.** Provision **VM-B (core node) up front** and move
   the bot there, with RabbitMQ introduced on VM-A (edge), so the migration **never runs
   `rabbitmq` + gateway + bot on one 1 GB box** — the §9 OOM risk on the box that already
   froze once is designed out from the start, not deferred. Add the `rabbitmq` service
   (mem-limited, see risks). Wire a `BrokerPort` (Python, `aio-pika`) and broker adapter
   (TS, `amqplib`) as singletons mirroring the existing `HttpClient` / `AxiosClient`
   pattern, plus the two-layer test harness — `MockBrokerPort` for unit tests and a
   testcontainers ephemeral broker for integration ([ADR 0005](./adr/0005-brokerport-two-layer-testing.md)).
   Delivering this first means every later phase has both test layers from the start.
   Health checks. **Cost of splitting early:** the still-live WS path now crosses VMs
   (was localhost), so the `/ws` port is exposed on the VCN private subnet temporarily —
   plumbing for a path that phase 5 deletes, accepted as the price of avoiding OOM.
2. **`group_events` first.** Already fire-and-forget today (`sendGroupEvent` does
   `ws.send` with no awaited response → `StealGroupService`). Lowest-risk first cut:
   proves the broker end-to-end without touching the request/response command path.
3. **Command path, atomically** (behind a flag, parallel-run with WS). Gateway
   publishes to `commands` (selective metadata + media attached); bot consumes and
   publishes to `replies`; gateway consumes and pushes to Baileys. No pending-future
   correlation — the two streams are tied by `jid` + `quoted_message_id` metadata
   (§4). Gateway-local feedback model (§5) takes over from `command_ack`. During this
   parallel-run the WS path is still live but now **inter-VM** (phase 1 split) — the flag
   lets either transport carry a command, preserving easy rollback until the broker path
   is proven.
4. **Holdout.** Add `wa_rpc` for `add`'s `on_whatsapp` (ADR 0003). Retire `wa_call`.
5. **Delete WS.** Remove `PythonBridge` WS code, `ws_handler.py`, `ws_client.py`,
   `/ws` endpoint, the binary-frame correlation, and the `command_ack` path. Rename the
   vestigial `WS`-prefixed types (`WSCommandData` → `CommandData` wire DTO) now that no
   WebSocket remains. Update `docs/architecture.md`.

Each phase: tests alongside (Vitest gateway, pytest bot), commit atomically, verify
before the next.

## 9. Risks

- **RabbitMQ on a 1GB/1CPU Oracle VPS.** The broker idles at ~100–130 MB RSS and the
  bot already plateaus at ~150–360 MB under load (`project-vps-cpu-runaway`). Three
  processes on 1 GB would be tight. **Resolved by distribution, not by transport
  swap** — see §11. The two on-VPS processes (gateway, bot; Mongo and Redis are
  external/cloud) split across two Oracle Always-Free micros, one heavy process each.
  RabbitMQ is the committed transport regardless — chosen as a deliberate résumé /
  ATS stack target (RabbitMQ appears in a large share of backend job specs), not for
  operational fit. `vm_memory_high_watermark` + per-container `mem_limit` still apply.
- **At-least-once duplicates.** Covered in §7 — accepted, not engineered around in v1.
- **Operational surface grows.** A broker is a new thing to monitor, secure, and
  back up. Justified by the decouple/durability/learning goals; would not be
  justified for the CPU-runaway bug alone (that fix already partly landed in
  `ws.py`: task cancellation + compact exception logging + `client_state` send guard).
- **Media size over AMQP.** Handled in §5 by size-split: small media base64-inline,
  large media as raw binary on a disk-backed `media` queue (paged to disk, not broker
  RAM). No external store.

## 10. Open questions

1. ~~Broker placement~~ — **resolved: edge node** ([ADR 0002](./adr/0002-two-node-topology.md)).
2. ~~Media transport~~ — **resolved: size-split, no external store** (§5): small media
   base64-inline, large media raw-binary on a disk-backed `media` queue.
3. ~~`wa_rpc` vs redesign~~ — **resolved: `wa_rpc` for `add`'s `on_whatsapp` only**,
   `ban` fire-and-forget ([ADR 0003](./adr/0003-wa-rpc-queue.md)).

## 11. Deployment topology — two-node split

The 1 GB memory pressure is solved by spreading the two on-VPS processes across two
Oracle Always-Free micros (1 GB / 1 OCPU each) instead of cramming both plus the
broker onto one. Mongo (Atlas) and Redis (Upstash) are already external.

```
        ┌─────────── Oracle VCN (private subnet) ───────────┐
   ┌────┴──── VM-A · edge node ────┐   ┌──────── VM-B · core node ────┴───┐
   │  gateway (Bun + Baileys)      │   │  bot (Python · FastAPI)          │
   │  RabbitMQ  ── 5672 priv IP ───┼───┼──▶ amqps://VM-A_private          │
   │  publishes command.inbound    │   │  consumes commands               │
   │  consumes replies              │  │  publishes replies               │
   └───────────────────────────────┘   └──────────────────────────────────┘
            │ Baileys                        external: Mongo Atlas · Upstash
            ▼ WhatsApp
```

- **Broker lives on the edge node (with the gateway).** The gateway is the stable,
  long-lived process (Baileys session); the bot is the one redeployed often. The
  broker must survive bot restarts, so it sits with the side that doesn't churn. If
  VM-A dies, the gateway dies too → no inbound messages exist to lose; the broker's
  buffering job is for when the *bot* is down, which it still does.
- **Network.** Both VMs in one VCN private subnet. RabbitMQ binds the private IP;
  the security list opens 5672 only from VM-B. No public broker port. The management
  port (15672) stays closed / localhost-only.
- **Auth + encryption.** RabbitMQ's default `guest` user is localhost-only, so the bot
  connecting from VM-B *cannot* use it — a **dedicated user + password is mandatory**,
  stored in `.env` (existing pattern). Because persistent messages put WhatsApp content
  and media **at rest on the broker's disk** (VM-A) and **in transit** across the VCN to
  VM-B — user PII, not anonymous jobs — the inter-VM 5672 link runs **`amqps`/TLS**
  (defense in depth): the security-list isolation is the first boundary, TLS the second,
  so a misconfigured or breached subnet doesn't expose plaintext PII. Cost: cert
  generation/rotation and a small handshake/CPU overhead on the 1 OCPU micros, accepted.
  mTLS (client-cert auth) was considered and rejected as operational overkill for two
  processes — password auth over TLS is sufficient.
- **Compose split.** Today's single `docker-compose.yml` (`depends_on` + healthcheck
  coupling gateway→bot) becomes two host-local composes: `compose.edge.yml`
  (gateway + rabbitmq) and `compose.core.yml` (bot). The cross-service `depends_on`
  disappears — broker durability replaces boot ordering. That is Goal 2 made
  physical. Each VM keeps its own `.env` (edge: gateway + broker server creds; core:
  bot + broker client creds).
- **CI/CD deploy — two targets, not one** ([ADR 0006](./adr/0006-two-node-cicd-deploy.md)).
  Today `pipeline.yml` has a single `deploy`
  job (SSH to `VPS_HOST` → `git pull && docker compose pull && up -d`). It splits into
  **two explicit jobs, `deploy-edge` and `deploy-core`**, each SSHing to its own host and
  running its own compose file — no matrix (only two nodes; "tolerate duplication until
  the third occurrence"). Downstream jobs become `needs: [deploy-edge, deploy-core]`. New
  secrets per node (`VPS_EDGE_HOST` / `VPS_CORE_HOST`, etc.) replace the single
  `VPS_HOST`. `docker compose up -d` is declarative, so a code-only gateway deploy
  recreates only the gateway container — **RabbitMQ on the edge node stays up across
  deploys**, and the bot barely notices.
  - **The two-node deploy is not atomic — handled by contract discipline, not
    orchestration.** Gateway and bot deploy independently, so a release that changed the
    queue *contract* (routing key, payload schema, binding) would have a window where one
    node speaks the new dialect and the other the old. **Rule: queue-contract changes are
    expand/contract** — ship the additive half first (new queue/field/binding coexisting
    with the old), migrate consumers, remove the old in a later release. Then deploy order
    never matters and both jobs run in parallel. This is a guard rule (sibling to the
    [ADR 0001](./adr/0001-at-least-once-delivery.md) idempotency rule) for
    `.claude/rules/git.md` (scope `.github/**`), not built machinery. A code-only deploy
    (no contract change) is unaffected — reconnect + at-least-once + graceful drain (§7)
    cover the blip.
- **Redelivery.** A network partition between bot and broker can redeliver unacked
  messages — slightly more likely than same-host. Covered by §7's guard rule;
  nothing new to decide.

## 12. Observability — tracing across the broker

Today a command is **one** synchronous WS call: a single logical request, trivial to
follow in a log. After migration the same command becomes **four events across two
processes** (gateway publishes `commands` → bot consumes → bot publishes `replies` →
gateway consumes), and retry/DLQ ([ADR 0004](./adr/0004-ack-retry-dlq.md)) can make one
`add` reappear several times. Without a correlation id crossing the broker, answering
*"where did user X's command go?"* turns into archaeology — grepping two logs and
matching timestamps by hand.

- **Correlation id propagated as an AMQP header.** Every inbound WhatsApp message already
  carries a unique `CommandData.message_id` (the same key the §7 idempotency escape hatch
  would use). It rides every message as an AMQP header (`correlation_id` / a custom
  header), set on publish and read on consume — gateway → `commands` → `replies` →
  gateway, and through the retry/DLQ hops.
- **Bound into the existing logging stack, no new dependency.** On consume, each side
  binds the id into its logger context — `structlog.contextvars.bind_contextvars` on the
  bot, the equivalent on the gateway's structured logs — and into the Sentry scope
  (`set_tag`/`set_context`). Every log line and every Sentry event on **both** processes
  then carries the id: grep or filter one id and the whole distributed path appears,
  retries and DLQ included. Reuses `structlog` + `@sentry/bun` / `sentry-sdk` already in
  the project (`docs/logging.md`); full OpenTelemetry distributed tracing is deliberately
  out of scope — a collector + backend is real weight for two processes on a pair of 1 GB
  micros, and the correlation id covers the actual debugging need.
- **Broker health.** RabbitMQ's management plugin / Prometheus endpoint exposes queue
  depth, consumer count, and DLQ size. A non-zero DLQ is the single most important signal
  (a command class is permanently failing) and should surface to Sentry or an alert.
  Detailed alerting thresholds are an implementation concern, not a v1 design fork.

## 13. Testing strategy

Implementation is TDD (RED → GREEN → REFACTOR), so testability is a design constraint,
not an afterthought. Full rationale in [ADR 0005](./adr/0005-brokerport-two-layer-testing.md).

- **`BrokerPort` abstraction.** Command and orchestration code talk to a `BrokerPort`
  (Python) / broker adapter (TS) wrapping `aio-pika` / `amqplib`, never the clients
  directly — so unit tests mock the port we own, honouring `testing.md`'s *don't mock
  what you don't own*. Mirrors `WhatsAppPort` / `AxiosClient`.
- **Two layers.** Unit tests mock `BrokerPort` (fast, command logic). Integration tests
  run the thin adapter and the reliability semantics — retry/DLX/DLQ, `x-death` counting,
  publisher confirms, `wa_rpc` timeout — against a **real ephemeral RabbitMQ**
  (testcontainers / single compose service), because a mocked channel can't prove TTL/DLX
  routing and its RED would be theatre.
- **No local-container impediment.** RabbitMQ runs as one `rabbitmq:3-management`
  container with no cloud dependency (Mongo/Redis are already external). The
  `compose.edge` / `compose.core` split (§11) is production-only.
- **Timing discipline.** Backoff/retry tests use short TTLs + `vi.waitFor` / event-or-poll
  waits, never `sleep` (a `testing.md` rule), to stay deterministic.
