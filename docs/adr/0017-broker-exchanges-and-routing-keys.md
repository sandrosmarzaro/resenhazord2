---
status: accepted
date: 2026-11-26
---

# 0017 — Named exchanges, bindings and routing keys

Every message used to go through the default exchange with the queue name as the
routing key ([#383](https://github.com/sandrosmarzaro/resenhazord2/issues/383)). A
producer had to know the consumer's queue, a second consumer of the same message meant
changing the producer, and renaming a queue broke both nodes at once.

## Decision

Two durable topic exchanges carry the traffic between the nodes. The existing queues
keep their names and arguments and are bound to them.

| Exchange | Routing key | Binding | Queue | Producer → consumer |
|---|---|---|---|---|
| `resenhazord.commands` | `command.whatsapp` | `command.#` | `commands` | edge → core |
| `resenhazord.commands` | `wa.action.<method>` | `wa.action.#` | `wa_actions` | core → edge |
| `resenhazord.commands` | `wa.rpc.<method>` | `wa.rpc.#` | `wa_rpc` | core → edge |
| `resenhazord.events` | `reply.whatsapp` | `reply.whatsapp` | `replies` | core → edge |
| `resenhazord.events` | `group.<action>` | `group.#` | `group_events` | edge → core |

`resenhazord.commands` carries work that exactly one queue takes. `resenhazord.events`
carries facts that more queues may bind to later, such as an audit log or a metrics
consumer. A topic exchange lets a binding take a whole family (`group.#`), so a producer
can add a segment to its key, for example `command.whatsapp.private`, without a
contract change.

Both nodes declare the whole topology (exchanges, queues with their arguments, bindings)
when the broker connects, from one data file per node: `bot/data/broker_topology.py`
and `gateway/src/data/BrokerTopology.json`. A unit test keeps the two equal. Declaring is
idempotent. The core's robust channel replays the declarations after a reconnect, and the
gateway connects again on every WhatsApp reconnect. Each node declares the queues it
only publishes to as well. Otherwise a producer that boots before the consumer's first
start would publish into an exchange with no binding, and the broker would drop the
message.

The queue arguments are unchanged: `commands.retry` keeps `x-message-ttl: 30000`,
`x-dead-letter-exchange: ''` and `x-dead-letter-routing-key: commands`, and every
other queue has none. The `commands-bounded` and `dlq-retention` policies still match
by name, and an old node's redeclare still matches, so no node sees
`PRECONDITION_FAILED`. The broker integration tests on both sides declare the queues as
the old code did, before and after the new topology. Each node's real declaration was
also run against the other's on a fresh broker, in both orders.

RPC replies stay on the default exchange: the caller's `reply_to` names a server-named
exclusive queue, which is the AMQP convention.

## Rollout

Queue contracts ship expand/contract ([ADR 0006](./0006-two-node-cicd-deploy.md)).

1. **Expand (this change).** Both nodes declare the exchanges and bindings. Producers
   still publish through the default exchange by queue name. Nothing routes through the
   exchanges yet, so either node can deploy first.
2. **Migrate.** `BrokerPort.publish` takes an exchange and a routing key on both nodes,
   and `rpc_call` publishes `wa.rpc.<method>` to `resenhazord.commands`. This is safe
   with an old consumer: the producer declared the exchange and the binding itself before
   its first publish, and the old consumer reads the same queue by name. It ships as its
   own change so the live bindings can be checked with `rabbitmqctl list_bindings` before
   any message depends on them.
3. **Contract.** Move retry and dead-lettering off the default exchange. A
   `resenhazord.dlx` exchange routes `command.retry` and `command.dead`. `commands.dlq`
   only gains a binding. `commands.retry` cannot change its dead-letter arguments in
   place, so a new retry queue that dead-letters to `resenhazord.commands` replaces it.
   The old one stops being declared once empty, and the owner deletes it with
   `rabbitmqctl delete_queue commands.retry`. `uv run task dlq:replay` then publishes by
   routing key too.

The `,dl` exclusive lane (`asyncio.Lock` in `CommandConsumer`) is unchanged. A routing
key could send `,dl` to its own queue later, but the gateway would have to know which
commands are exclusive, which only the core knows today.

## Considered options

- **A RabbitMQ definitions file.** Rejected for the reason in the
  [ADR 0004](./0004-ack-retry-dlq.md) amendment: importing one at boot skips seeding
  the default vhost and user.
- **Consumers declare only their own queues and bindings.** Producers would know no
  queue names at all, but a message published before the consumer's first boot would be
  dropped. An alternate exchange could catch those and may replace this later.
- **One shared topology file for both nodes.** The core image excludes `gateway/` and
  the gateway image is built from `gateway/`, so neither sees the other's files. Two data
  files and a parity test cost less than a build step.
- **Direct exchanges.** They take exact keys only, so every new consumer of a family
  of events needs one binding per key.

## Consequences

- Fan-out is a new binding, not a producer change. A second queue bound to `command.#`
  would run every command twice, though. Only something that observes commands, not one
  that answers them, may bind there.
- At-least-once delivery and the dedup inbox ([ADR 0001](./0001-at-least-once-delivery.md))
  are unaffected: each routing key reaches exactly one queue.
- Changing a queue's arguments or a binding is still a contract change, now made in two
  data files that the parity test keeps equal.
